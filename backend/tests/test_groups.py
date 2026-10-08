"""P3FT.13 — Roommate groups: creation, invites, membership, compatibility, cascades.

Notes on what these tests deliberately pin down:

  * Ownership comes from the bearer token, never a path parameter. The only
    `{user_id}` in a group path is the *invitee* on POST /groups/{gid}/invite/{uid}.
  * Group and invite ids are ints allocated from `counters_collection`, not ObjectIds.
  * "At most one active group per user" is enforced in application code, not by a
    unique index, so it is tested directly through the API.
  * Group membership must not consume the MAX_MATCHES cap.
  * Block / unmatch / deactivate / soft delete / hard delete all have to eject the
    user from their group and cancel their pending invites.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import GROUP_MAX_SIZE, GROUP_MIN_SIZE, MAX_MATCHES
from tests.helpers import (
    auth_header,
    declared_rate_limits,
    make_match,
    make_user,
    prefs,
)

client = TestClient(app)
BASE = "/api"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _seed_users(test_db, ids, gender="male", **overrides):
    test_db["users"].insert_many([make_user(i, gender=gender, **overrides) for i in ids])


def _seed_mutual_match(test_db, a, b):
    test_db["matches"].insert_one(make_match(a, b))
    for x, y in ((a, b), (b, a)):
        test_db["users"].update_one(
            {"id": x},
            {"$addToSet": {"matchedWith": y}, "$set": {"matched": True}},
        )


def _create_group(user_id, name=None, max_size=None):
    body = {}
    if name is not None:
        body["name"] = name
    if max_size is not None:
        body["maxSize"] = max_size
    return client.post(f"{BASE}/groups", json=body, headers=auth_header(user_id))


def _invite(group_id, inviter, invitee):
    return client.post(f"{BASE}/groups/{group_id}/invite/{invitee}",
                       headers=auth_header(inviter))


def _respond(group_id, invite_id, user_id, action):
    return client.post(f"{BASE}/groups/{group_id}/invites/{invite_id}/respond",
                       json={"action": action}, headers=auth_header(user_id))


def _block(blocker, blocked):
    return client.post(f"{BASE}/users/{blocker}/block",
                       json={"userId": blocked}, headers=auth_header(blocker))


def _mine(user_id):
    return client.get(f"{BASE}/groups/mine", headers=auth_header(user_id))


def _group_of(test_db, gid):
    return test_db["groups"].find_one({"id": gid})


def _build_group(test_db, member_ids, max_size=GROUP_MAX_SIZE):
    """Create a group via the API with `member_ids[0]` as creator, matching all
    members pairwise first so the invite rules are satisfied."""
    creator = member_ids[0]
    for other in member_ids[1:]:
        _seed_mutual_match(test_db, creator, other)
    gid = _create_group(creator).json()["id"]
    if max_size != GROUP_MAX_SIZE:
        test_db["groups"].update_one({"id": gid}, {"$set": {"maxSize": max_size}})
    for other in member_ids[1:]:
        invite_id = _invite(gid, creator, other).json()["id"]
        _respond(gid, invite_id, other, "accept")
    return gid


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

class TestCreateGroup:

    def test_creates_a_group_with_the_caller_as_sole_member(self, test_db):
        _seed_users(test_db, [4001])
        r = _create_group(4001)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["memberIds"] == [4001]
        assert body["createdBy"] == 4001
        assert body["status"] == "open"
        assert body["maxSize"] == GROUP_MAX_SIZE

    def test_ownership_comes_from_the_token_not_a_path_param(self, test_db):
        _seed_users(test_db, [4010, 4011])
        gid = _create_group(4011).json()["id"]
        assert _group_of(test_db, gid)["createdBy"] == 4011

    def test_group_id_is_an_int_from_the_counters_collection(self, test_db):
        _seed_users(test_db, [4020])
        gid = _create_group(4020).json()["id"]
        assert isinstance(gid, int)
        assert not isinstance(gid, bool)
        assert test_db["counters"].find_one({"_id": "group_id"})["seq"] == gid

    def test_group_ids_increment(self, test_db):
        _seed_users(test_db, [4030, 4031])
        first = _create_group(4030).json()["id"]
        second = _create_group(4031).json()["id"]
        assert second == first + 1

    def test_response_never_contains_a_mongo_id(self, test_db):
        _seed_users(test_db, [4040])
        assert "_id" not in _create_group(4040).json()

    def test_name_is_optional(self, test_db):
        _seed_users(test_db, [4050])
        r = _create_group(4050)
        assert r.status_code == 200, r.text
        assert r.json()["name"] is None

    def test_name_over_40_chars_is_422(self, test_db):
        _seed_users(test_db, [4060])
        assert _create_group(4060, name="x" * 41).status_code == 422

    def test_name_of_exactly_40_chars_is_accepted(self, test_db):
        _seed_users(test_db, [4070])
        r = _create_group(4070, name="x" * 40)
        assert r.status_code == 200, r.text

    def test_name_html_is_stripped(self, test_db):
        _seed_users(test_db, [4080])
        r = _create_group(4080, name="<b>Toomer</b> Crew")
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Toomer Crew"

    @pytest.mark.parametrize("size,expected", [
        (1, 422), (2, 200), (3, 200), (4, 200), (5, 422),
    ])
    def test_max_size_bounds(self, test_db, size, expected):
        _seed_users(test_db, [4090])
        assert _create_group(4090, max_size=size).status_code == expected

    def test_max_size_defaults_to_four(self, test_db):
        _seed_users(test_db, [4100])
        assert _create_group(4100).json()["maxSize"] == GROUP_MAX_SIZE == 4

    def test_group_size_constants(self):
        assert (GROUP_MIN_SIZE, GROUP_MAX_SIZE) == (2, 4)

    def test_rate_limit_is_ten_per_hour(self):
        assert declared_rate_limits("app.routers.groupRoutes.create_group") == ["10 per 1 hour"]


class TestOneActiveGroupPerUser:
    """Application-level invariant — not enforceable with a unique index."""

    def test_creating_a_second_group_is_400(self, test_db):
        _seed_users(test_db, [4200])
        assert _create_group(4200).status_code == 200
        r = _create_group(4200)
        assert r.status_code == 400
        assert "already in a group" in r.json()["detail"].lower()

    def test_only_one_group_document_exists_after_the_rejected_attempt(self, test_db):
        _seed_users(test_db, [4210])
        _create_group(4210)
        _create_group(4210)
        assert test_db["groups"].count_documents({"memberIds": 4210}) == 1

    def test_a_full_group_also_blocks_creating_another(self, test_db):
        _seed_users(test_db, [4220, 4221])
        gid = _build_group(test_db, [4220, 4221], max_size=2)
        assert _group_of(test_db, gid)["status"] == "full"
        assert _create_group(4220).status_code == 400

    def test_leaving_frees_the_user_to_create_a_new_group(self, test_db):
        _seed_users(test_db, [4230])
        gid = _create_group(4230).json()["id"]
        assert client.post(f"{BASE}/groups/{gid}/leave",
                           headers=auth_header(4230)).status_code == 200
        assert _create_group(4230).status_code == 200

    def test_accepting_an_invite_while_already_grouped_is_400(self, test_db):
        _seed_users(test_db, [4240, 4241, 4242])
        _seed_mutual_match(test_db, 4240, 4242)
        gid_a = _create_group(4240).json()["id"]

        # 4242 joins a different group first
        _seed_mutual_match(test_db, 4241, 4242)
        _build_group(test_db, [4241, 4242])

        # Seeded directly: POST /invite would already reject with "already in a
        # group", and accepting an invite cancels every other pending one -- so
        # this is the only way to exercise the guard inside respond_to_invite.
        test_db["group_invites"].insert_one({
            "id": 98001, "groupId": gid_a, "fromUserId": 4240, "toUserId": 4242,
            "status": "pending", "createdAt": datetime.now(timezone.utc),
        })

        r = _respond(gid_a, 98001, 4242, "accept")
        assert r.status_code == 400
        assert "already in a group" in r.json()["detail"].lower()
        assert _group_of(test_db, gid_a)["memberIds"] == [4240]


# ---------------------------------------------------------------------------
# GET /groups/mine
# ---------------------------------------------------------------------------

class TestGetMyGroup:

    def test_null_group_and_no_invites_for_a_fresh_user(self, test_db):
        _seed_users(test_db, [4300])
        r = _mine(4300)
        assert r.status_code == 200, r.text
        assert r.json() == {"group": None, "pendingInvites": []}

    def test_returns_the_users_group(self, test_db):
        _seed_users(test_db, [4310])
        gid = _create_group(4310, name="Crew").json()["id"]
        body = _mine(4310).json()
        assert body["group"]["id"] == gid
        assert body["group"]["name"] == "Crew"
        assert [m["id"] for m in body["group"]["members"]] == [4310]

    def test_invites_are_returned_even_when_group_is_null(self, test_db):
        """An invitee with no group of their own still has to see the invite --
        this is their only in-app path into a group."""
        _seed_users(test_db, [4320, 4321])
        _seed_mutual_match(test_db, 4320, 4321)
        gid = _create_group(4320).json()["id"]
        _invite(gid, 4320, 4321)

        body = _mine(4321).json()
        assert body["group"] is None
        assert len(body["pendingInvites"]) == 1
        assert body["pendingInvites"][0]["groupId"] == gid
        assert body["pendingInvites"][0]["fromUserId"] == 4320

    def test_invite_summary_carries_display_context(self, test_db):
        _seed_users(test_db, [4330, 4331])
        _seed_mutual_match(test_db, 4330, 4331)
        gid = _create_group(4330, name="Magnolia").json()["id"]
        _invite(gid, 4330, 4331)

        invite = _mine(4331).json()["pendingInvites"][0]
        assert invite["groupName"] == "Magnolia"
        assert invite["memberCount"] == 1
        assert invite["maxSize"] == GROUP_MAX_SIZE
        assert invite["fromUsername"] == "user4330"
        assert "_id" not in invite

    def test_answered_invites_are_not_listed(self, test_db):
        _seed_users(test_db, [4340, 4341])
        _seed_mutual_match(test_db, 4340, 4341)
        gid = _create_group(4340).json()["id"]
        invite_id = _invite(gid, 4340, 4341).json()["id"]
        _respond(gid, invite_id, 4341, "decline")
        assert _mine(4341).json()["pendingInvites"] == []

    def test_invites_for_a_closed_group_are_not_listed(self, test_db):
        _seed_users(test_db, [4350, 4351])
        _seed_mutual_match(test_db, 4350, 4351)
        gid = _create_group(4350).json()["id"]
        _invite(gid, 4350, 4351)
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4350))
        assert _group_of(test_db, gid)["status"] == "closed"
        assert _mine(4351).json()["pendingInvites"] == []

    def test_rate_limit_is_sixty_per_minute(self):
        assert declared_rate_limits("app.routers.groupRoutes.get_my_group") == ["60 per 1 minute"]


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

class TestInvite:

    def test_member_can_invite_a_match(self, test_db):
        _seed_users(test_db, [4400, 4401])
        _seed_mutual_match(test_db, 4400, 4401)
        gid = _create_group(4400).json()["id"]
        r = _invite(gid, 4400, 4401)
        assert r.status_code == 200, r.text
        assert r.json()["toUserId"] == 4401
        assert r.json()["status"] == "pending"

    def test_invite_id_is_an_int_from_the_counters_collection(self, test_db):
        _seed_users(test_db, [4410, 4411])
        _seed_mutual_match(test_db, 4410, 4411)
        gid = _create_group(4410).json()["id"]
        iid = _invite(gid, 4410, 4411).json()["id"]
        assert isinstance(iid, int) and not isinstance(iid, bool)
        assert test_db["counters"].find_one({"_id": "group_invite_id"})["seq"] == iid

    def test_invite_response_has_no_mongo_id(self, test_db):
        _seed_users(test_db, [4420, 4421])
        _seed_mutual_match(test_db, 4420, 4421)
        gid = _create_group(4420).json()["id"]
        assert "_id" not in _invite(gid, 4420, 4421).json()

    def test_403_when_the_caller_is_not_a_member(self, test_db):
        _seed_users(test_db, [4430, 4431, 4432])
        _seed_mutual_match(test_db, 4431, 4432)
        gid = _create_group(4430).json()["id"]
        r = _invite(gid, 4431, 4432)
        assert r.status_code == 403
        assert "not a member" in r.json()["detail"].lower()

    def test_403_when_the_invitee_is_not_a_match_of_any_member(self, test_db):
        _seed_users(test_db, [4440, 4441])
        gid = _create_group(4440).json()["id"]
        r = _invite(gid, 4440, 4441)
        assert r.status_code == 403
        assert "matches" in r.json()["detail"].lower()

    def test_a_match_with_any_member_is_enough(self, test_db):
        _seed_users(test_db, [4450, 4451, 4452])
        gid = _build_group(test_db, [4450, 4451])
        # 4452 matches only the second member
        _seed_mutual_match(test_db, 4451, 4452)
        assert _invite(gid, 4450, 4452).status_code == 200

    def test_403_on_gender_mismatch(self, test_db):
        test_db["users"].insert_many([
            make_user(4460, gender="male"),
            make_user(4461, gender="female"),
        ])
        _seed_mutual_match(test_db, 4460, 4461)
        gid = _create_group(4460).json()["id"]
        r = _invite(gid, 4460, 4461)
        assert r.status_code == 403
        assert "gender" in r.json()["detail"].lower()

    def test_403_when_a_block_exists(self, test_db):
        _seed_users(test_db, [4470, 4471])
        _seed_mutual_match(test_db, 4470, 4471)
        gid = _create_group(4470).json()["id"]
        test_db["blocks"].insert_one({"blockerId": 4471, "blockedId": 4470})
        # verify_match_exists treats a block as "not matched"
        assert _invite(gid, 4470, 4471).status_code == 403

    def test_400_when_the_group_is_full(self, test_db):
        _seed_users(test_db, [4480, 4481, 4482])
        gid = _build_group(test_db, [4480, 4481], max_size=2)
        _seed_mutual_match(test_db, 4480, 4482)
        r = _invite(gid, 4480, 4482)
        assert r.status_code == 400
        assert "full" in r.json()["detail"].lower()

    def test_400_when_the_group_is_closed(self, test_db):
        _seed_users(test_db, [4490, 4491])
        _seed_mutual_match(test_db, 4490, 4491)
        gid = _create_group(4490).json()["id"]
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4490))
        # re-add so the caller passes the membership check but the group is closed
        test_db["groups"].update_one({"id": gid}, {"$set": {"memberIds": [4490]}})
        r = _invite(gid, 4490, 4491)
        assert r.status_code == 400
        assert "closed" in r.json()["detail"].lower()

    def test_400_when_the_invitee_is_already_a_member(self, test_db):
        _seed_users(test_db, [4500, 4501])
        gid = _build_group(test_db, [4500, 4501])
        r = _invite(gid, 4500, 4501)
        assert r.status_code == 400
        assert "already a member" in r.json()["detail"].lower()

    def test_400_when_the_invitee_already_belongs_to_another_group(self, test_db):
        _seed_users(test_db, [4510, 4511, 4512])
        _seed_mutual_match(test_db, 4510, 4512)
        gid_a = _create_group(4510).json()["id"]
        _build_group(test_db, [4511, 4512])
        r = _invite(gid_a, 4510, 4512)
        assert r.status_code == 400
        assert "already in a group" in r.json()["detail"].lower()

    def test_400_on_a_duplicate_pending_invite(self, test_db):
        _seed_users(test_db, [4520, 4521])
        _seed_mutual_match(test_db, 4520, 4521)
        gid = _create_group(4520).json()["id"]
        assert _invite(gid, 4520, 4521).status_code == 200
        r = _invite(gid, 4520, 4521)
        assert r.status_code == 400
        assert "already pending" in r.json()["detail"].lower()

    def test_400_when_inviting_yourself(self, test_db):
        _seed_users(test_db, [4530])
        gid = _create_group(4530).json()["id"]
        r = _invite(gid, 4530, 4530)
        assert r.status_code == 400

    def test_404_for_an_unknown_group(self, test_db):
        _seed_users(test_db, [4540, 4541])
        assert _invite(999999, 4540, 4541).status_code == 404

    def test_404_for_an_unknown_invitee(self, test_db):
        _seed_users(test_db, [4550])
        gid = _create_group(4550).json()["id"]
        assert _invite(gid, 4550, 999999).status_code == 404

    def test_404_for_a_deactivated_invitee(self, test_db):
        _seed_users(test_db, [4560])
        test_db["users"].insert_one(make_user(4561, is_deactivated=True))
        _seed_mutual_match(test_db, 4560, 4561)
        gid = _create_group(4560).json()["id"]
        assert _invite(gid, 4560, 4561).status_code == 404

    def test_404_for_a_soft_deleted_invitee(self, test_db):
        _seed_users(test_db, [4570])
        test_db["users"].insert_one(
            make_user(4571, deletedAt=datetime.now(timezone.utc)))
        _seed_mutual_match(test_db, 4570, 4571)
        gid = _create_group(4570).json()["id"]
        assert _invite(gid, 4570, 4571).status_code == 404

    def test_invite_creates_a_notification(self, test_db):
        _seed_users(test_db, [4580, 4581])
        _seed_mutual_match(test_db, 4580, 4581)
        gid = _create_group(4580).json()["id"]
        _invite(gid, 4580, 4581)
        notif = test_db["notifications"].find_one({"toUser": 4581, "type": "group_invite"})
        assert notif is not None

    def test_rate_limit_is_ten_per_hour(self):
        assert declared_rate_limits("app.routers.groupRoutes.invite_to_group") == ["10 per 1 hour"]


class TestRespondToInvite:

    def _pending(self, test_db, host, guest):
        _seed_users(test_db, [host, guest])
        _seed_mutual_match(test_db, host, guest)
        gid = _create_group(host).json()["id"]
        iid = _invite(gid, host, guest).json()["id"]
        return gid, iid

    def test_accept_adds_the_member_and_returns_the_group(self, test_db):
        gid, iid = self._pending(test_db, 4600, 4601)
        r = _respond(gid, iid, 4601, "accept")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "accepted"
        assert sorted(body["group"]["memberIds"]) == [4600, 4601]

    def test_decline_returns_a_null_group(self, test_db):
        gid, iid = self._pending(test_db, 4610, 4611)
        r = _respond(gid, iid, 4611, "decline")
        assert r.status_code == 200, r.text
        assert r.json() == {"status": "declined", "group": None}
        assert _group_of(test_db, gid)["memberIds"] == [4610]

    def test_403_when_the_invite_is_not_addressed_to_you(self, test_db):
        gid, iid = self._pending(test_db, 4620, 4621)
        test_db["users"].insert_one(make_user(4622))
        r = _respond(gid, iid, 4622, "accept")
        assert r.status_code == 403
        assert "not addressed to you" in r.json()["detail"].lower()

    def test_404_for_an_unknown_invite(self, test_db):
        gid, _ = self._pending(test_db, 4630, 4631)
        assert _respond(gid, 999999, 4631, "accept").status_code == 404

    def test_404_when_the_invite_belongs_to_another_group(self, test_db):
        gid, iid = self._pending(test_db, 4640, 4641)
        assert _respond(gid + 500, iid, 4641, "accept").status_code == 404

    def test_400_when_answering_twice(self, test_db):
        gid, iid = self._pending(test_db, 4650, 4651)
        assert _respond(gid, iid, 4651, "decline").status_code == 200
        r = _respond(gid, iid, 4651, "accept")
        assert r.status_code == 400
        assert "already been answered" in r.json()["detail"].lower()

    def test_422_for_an_unknown_action(self, test_db):
        gid, iid = self._pending(test_db, 4660, 4661)
        assert _respond(gid, iid, 4661, "maybe").status_code == 422

    def test_accept_marks_the_group_full_at_max_size(self, test_db):
        _seed_users(test_db, [4670, 4671])
        gid = _build_group(test_db, [4670, 4671], max_size=2)
        assert _group_of(test_db, gid)["status"] == "full"

    def test_accepting_cancels_the_users_other_pending_invites(self, test_db):
        _seed_users(test_db, [4680, 4681, 4682])
        _seed_mutual_match(test_db, 4680, 4682)
        _seed_mutual_match(test_db, 4681, 4682)
        gid_a = _create_group(4680).json()["id"]
        gid_b = _create_group(4681).json()["id"]
        iid_a = _invite(gid_a, 4680, 4682).json()["id"]
        iid_b = _invite(gid_b, 4681, 4682).json()["id"]

        _respond(gid_a, iid_a, 4682, "accept")

        assert test_db["group_invites"].find_one({"id": iid_b})["status"] == "declined"
        assert _mine(4682).json()["pendingInvites"] == []

    def test_accept_notifies_existing_members(self, test_db):
        gid, iid = self._pending(test_db, 4690, 4691)
        _respond(gid, iid, 4691, "accept")
        assert test_db["notifications"].find_one(
            {"toUser": 4690, "type": "group_invite_accepted"}) is not None

    def test_rate_limit_is_thirty_per_minute(self):
        assert declared_rate_limits(
            "app.routers.groupRoutes.respond_to_group_invite") == ["30 per 1 minute"]


# ---------------------------------------------------------------------------
# Leave / disband
# ---------------------------------------------------------------------------

class TestLeaveGroup:

    def test_member_can_leave(self, test_db):
        _seed_users(test_db, [4700, 4701])
        gid = _build_group(test_db, [4700, 4701])
        r = client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4701))
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid)["memberIds"] == [4700]

    def test_creator_role_hands_off_to_the_first_remaining_member(self, test_db):
        _seed_users(test_db, [4710, 4711, 4712])
        gid = _build_group(test_db, [4710, 4711, 4712])
        assert _group_of(test_db, gid)["createdBy"] == 4710

        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4710))

        group = _group_of(test_db, gid)
        assert group["createdBy"] == group["memberIds"][0] == 4711

    def test_group_closes_when_the_last_member_leaves(self, test_db):
        _seed_users(test_db, [4720])
        gid = _create_group(4720).json()["id"]
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4720))
        group = _group_of(test_db, gid)
        assert group["memberIds"] == []
        assert group["status"] == "closed"

    def test_a_full_group_reopens_when_someone_leaves(self, test_db):
        _seed_users(test_db, [4730, 4731])
        gid = _build_group(test_db, [4730, 4731], max_size=2)
        assert _group_of(test_db, gid)["status"] == "full"
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4731))
        assert _group_of(test_db, gid)["status"] == "open"

    def test_leaving_cancels_invites_the_leaver_sent(self, test_db):
        _seed_users(test_db, [4740, 4741, 4742])
        gid = _build_group(test_db, [4740, 4741])
        _seed_mutual_match(test_db, 4741, 4742)
        iid = _invite(gid, 4741, 4742).json()["id"]

        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4741))

        assert test_db["group_invites"].find_one({"id": iid})["status"] == "declined"

    def test_403_when_not_a_member(self, test_db):
        _seed_users(test_db, [4750, 4751])
        gid = _create_group(4750).json()["id"]
        r = client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4751))
        assert r.status_code == 403

    def test_404_for_an_unknown_group(self, test_db):
        _seed_users(test_db, [4760])
        assert client.post(f"{BASE}/groups/999999/leave",
                           headers=auth_header(4760)).status_code == 404

    def test_remaining_members_are_notified(self, test_db):
        _seed_users(test_db, [4770, 4771])
        gid = _build_group(test_db, [4770, 4771])
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4771))
        assert test_db["notifications"].find_one(
            {"toUser": 4770, "type": "group_member_left"}) is not None


class TestDisbandGroup:

    def test_creator_can_disband(self, test_db):
        _seed_users(test_db, [4800, 4801])
        gid = _build_group(test_db, [4800, 4801])
        r = client.delete(f"{BASE}/groups/{gid}", headers=auth_header(4800))
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid) is None

    def test_last_member_can_disband_even_if_not_the_creator(self, test_db):
        _seed_users(test_db, [4810, 4811])
        gid = _build_group(test_db, [4810, 4811])
        client.post(f"{BASE}/groups/{gid}/leave", headers=auth_header(4810))
        assert _group_of(test_db, gid)["memberIds"] == [4811]
        r = client.delete(f"{BASE}/groups/{gid}", headers=auth_header(4811))
        assert r.status_code == 200, r.text

    def test_403_for_a_non_creator_while_others_remain(self, test_db):
        _seed_users(test_db, [4820, 4821])
        gid = _build_group(test_db, [4820, 4821])
        r = client.delete(f"{BASE}/groups/{gid}", headers=auth_header(4821))
        assert r.status_code == 403
        assert "creator" in r.json()["detail"].lower()

    def test_403_for_a_non_member(self, test_db):
        _seed_users(test_db, [4830, 4831])
        gid = _create_group(4830).json()["id"]
        assert client.delete(f"{BASE}/groups/{gid}",
                             headers=auth_header(4831)).status_code == 403

    def test_404_for_an_unknown_group(self, test_db):
        _seed_users(test_db, [4840])
        assert client.delete(f"{BASE}/groups/999999",
                             headers=auth_header(4840)).status_code == 404

    def test_disband_deletes_the_groups_invites(self, test_db):
        _seed_users(test_db, [4850, 4851, 4852])
        gid = _build_group(test_db, [4850, 4851])
        _seed_mutual_match(test_db, 4850, 4852)
        _invite(gid, 4850, 4852)
        assert test_db["group_invites"].count_documents({"groupId": gid}) >= 1

        client.delete(f"{BASE}/groups/{gid}", headers=auth_header(4850))
        assert test_db["group_invites"].count_documents({"groupId": gid}) == 0

    def test_disband_frees_every_member_to_create_a_new_group(self, test_db):
        _seed_users(test_db, [4860, 4861])
        gid = _build_group(test_db, [4860, 4861])
        client.delete(f"{BASE}/groups/{gid}", headers=auth_header(4860))
        assert _create_group(4861).status_code == 200


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

class TestGroupCompatibility:

    def test_returns_the_documented_shape(self, test_db):
        _seed_users(test_db, [4900, 4901])
        gid = _build_group(test_db, [4900, 4901])
        r = client.get(f"{BASE}/groups/{gid}/compatibility", headers=auth_header(4900))
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body.keys()) == {
            "groupId", "memberIds", "matrix", "pairs", "mean", "weakestPair"
        }
        assert body["groupId"] == gid
        assert sorted(body["memberIds"]) == [4900, 4901]

    def test_matrix_is_symmetric(self, test_db):
        test_db["users"].insert_many([
            make_user(4910, **prefs(3.0, cleanlinessScore=9.0)),
            make_user(4911, **prefs(7.0, guestsScore=2.0)),
            make_user(4912, **prefs(5.0, personalityScore=1.0)),
        ])
        gid = _build_group(test_db, [4910, 4911, 4912])
        matrix = client.get(f"{BASE}/groups/{gid}/compatibility",
                            headers=auth_header(4910)).json()["matrix"]
        assert set(matrix.keys()) == {"4910", "4911", "4912"}
        for a, row in matrix.items():
            assert a not in row  # no self-entries
            for b, score in row.items():
                assert matrix[b][a] == score

    def test_pairs_cover_every_unordered_pair_once(self, test_db):
        _seed_users(test_db, [4920, 4921, 4922])
        gid = _build_group(test_db, [4920, 4921, 4922])
        pairs = client.get(f"{BASE}/groups/{gid}/compatibility",
                           headers=auth_header(4920)).json()["pairs"]
        assert len(pairs) == 3  # C(3,2)
        seen = {frozenset((p["userA"], p["userB"])) for p in pairs}
        assert seen == {frozenset((4920, 4921)), frozenset((4920, 4922)),
                        frozenset((4921, 4922))}
        for p in pairs:
            assert set(p.keys()) == {"userA", "userB", "compatibilityScore"}

    def test_mean_is_the_average_of_the_pair_scores(self, test_db):
        test_db["users"].insert_many([
            make_user(4930, **prefs(2.0)),
            make_user(4931, **prefs(6.0)),
            make_user(4932, **prefs(9.0)),
        ])
        gid = _build_group(test_db, [4930, 4931, 4932])
        body = client.get(f"{BASE}/groups/{gid}/compatibility",
                          headers=auth_header(4930)).json()
        scores = [p["compatibilityScore"] for p in body["pairs"]]
        assert body["mean"] == pytest.approx(sum(scores) / len(scores), abs=1e-5)

    def test_weakest_pair_has_the_lowest_score(self, test_db):
        test_db["users"].insert_many([
            make_user(4940, **prefs(1.0)),
            make_user(4941, **prefs(2.0)),
            make_user(4942, **prefs(10.0)),
        ])
        gid = _build_group(test_db, [4940, 4941, 4942])
        body = client.get(f"{BASE}/groups/{gid}/compatibility",
                          headers=auth_header(4940)).json()
        lowest = min(p["compatibilityScore"] for p in body["pairs"])
        assert body["weakestPair"]["compatibilityScore"] == lowest

    def test_single_member_group_has_no_pairs(self, test_db):
        _seed_users(test_db, [4950])
        gid = _create_group(4950).json()["id"]
        body = client.get(f"{BASE}/groups/{gid}/compatibility",
                          headers=auth_header(4950)).json()
        assert body["pairs"] == []
        assert body["mean"] == 0.0
        assert body["weakestPair"] is None

    def test_403_for_a_non_member(self, test_db):
        _seed_users(test_db, [4960, 4961])
        gid = _create_group(4960).json()["id"]
        assert client.get(f"{BASE}/groups/{gid}/compatibility",
                          headers=auth_header(4961)).status_code == 403

    def test_404_for_an_unknown_group(self, test_db):
        _seed_users(test_db, [4970])
        assert client.get(f"{BASE}/groups/999999/compatibility",
                          headers=auth_header(4970)).status_code == 404

    def test_identical_members_score_one(self, test_db):
        _seed_users(test_db, [4980, 4981])
        gid = _build_group(test_db, [4980, 4981])
        body = client.get(f"{BASE}/groups/{gid}/compatibility",
                          headers=auth_header(4980)).json()
        assert body["mean"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Group membership vs the MAX_MATCHES cap
# ---------------------------------------------------------------------------

class TestGroupsDoNotConsumeTheMatchCap:

    def test_joining_a_group_does_not_change_match_count(self, test_db):
        _seed_users(test_db, [5000, 5001])
        before = test_db["users"].find_one({"id": 5001})["matchCount"]
        _build_group(test_db, [5000, 5001])
        after = test_db["users"].find_one({"id": 5001})
        # the single mutual match seeded by the fixture is the only change
        assert after["matchCount"] == before
        assert after["matchedWith"] == [5000]

    def test_a_user_at_the_match_cap_can_still_join_a_group(self, test_db):
        test_db["users"].insert_one(
            make_user(5010, matched=True, matchCount=MAX_MATCHES,
                      matchedWith=[9001, 9002, 9003, 9004, 9005]))
        test_db["users"].insert_one(make_user(5011))
        _seed_mutual_match(test_db, 5010, 5011)
        gid = _create_group(5011).json()["id"]
        iid = _invite(gid, 5011, 5010).json()["id"]
        r = _respond(gid, iid, 5010, "accept")
        assert r.status_code == 200, r.text
        assert 5010 in _group_of(test_db, gid)["memberIds"]

    def test_a_full_group_of_four_leaves_the_cap_untouched(self, test_db):
        _seed_users(test_db, [5020, 5021, 5022, 5023])
        gid = _build_group(test_db, [5020, 5021, 5022, 5023])
        assert len(_group_of(test_db, gid)["memberIds"]) == 4
        for uid in (5021, 5022, 5023):
            user = test_db["users"].find_one({"id": uid})
            assert user["matchCount"] <= MAX_MATCHES
            assert user["matchedWith"] == [5020]

    def test_max_matches_constant_is_five(self):
        assert MAX_MATCHES == 5


# ---------------------------------------------------------------------------
# Cascades
# ---------------------------------------------------------------------------

class TestBlockCascade:

    def test_block_removes_the_blocked_user_from_the_shared_group(self, test_db):
        _seed_users(test_db, [5100, 5101])
        gid = _build_group(test_db, [5100, 5101])
        r = _block(5100, 5101)
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid)["memberIds"] == [5100]

    def test_the_blocker_keeps_the_group(self, test_db):
        _seed_users(test_db, [5110, 5111])
        gid = _build_group(test_db, [5110, 5111])
        _block(5110, 5111)
        assert _mine(5110).json()["group"]["id"] == gid
        assert _mine(5111).json()["group"] is None

    def test_block_cancels_pending_invites_in_both_directions(self, test_db):
        _seed_users(test_db, [5120, 5121])
        _seed_mutual_match(test_db, 5120, 5121)
        gid = _create_group(5120).json()["id"]
        iid = _invite(gid, 5120, 5121).json()["id"]

        _block(5121, 5120)

        assert test_db["group_invites"].find_one({"id": iid})["status"] == "declined"

    def test_block_leaves_unrelated_groups_alone(self, test_db):
        _seed_users(test_db, [5130, 5131, 5132, 5133])
        gid_a = _build_group(test_db, [5130, 5131])
        gid_b = _build_group(test_db, [5132, 5133])
        _block(5130, 5131)
        assert sorted(_group_of(test_db, gid_b)["memberIds"]) == [5132, 5133]
        assert _group_of(test_db, gid_a)["memberIds"] == [5130]


class TestUnmatchCascade:

    def test_unmatch_removes_the_partner_from_the_shared_group(self, test_db):
        _seed_users(test_db, [5200, 5201])
        gid = _build_group(test_db, [5200, 5201])
        r = client.post(f"{BASE}/users/5200/unmatch/5201", headers=auth_header(5200))
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid)["memberIds"] == [5200]

    def test_unmatch_cancels_a_pending_invite_between_the_pair(self, test_db):
        _seed_users(test_db, [5210, 5211])
        _seed_mutual_match(test_db, 5210, 5211)
        gid = _create_group(5210).json()["id"]
        iid = _invite(gid, 5210, 5211).json()["id"]

        client.post(f"{BASE}/users/5210/unmatch/5211", headers=auth_header(5210))
        assert test_db["group_invites"].find_one({"id": iid})["status"] == "declined"

    def test_the_initiator_keeps_their_group(self, test_db):
        _seed_users(test_db, [5220, 5221])
        gid = _build_group(test_db, [5220, 5221])
        client.post(f"{BASE}/users/5220/unmatch/5221", headers=auth_header(5220))
        assert _mine(5220).json()["group"]["id"] == gid


class TestDeactivateCascade:

    def _deactivate(self, test_db, user_id, password="Deactivate123!"):
        from app.auth.utils import hash_password
        test_db["users"].update_one({"id": user_id},
                                    {"$set": {"hashed_password": hash_password(password)}})
        return client.post(f"{BASE}/users/{user_id}/deactivate",
                           json={"password": password}, headers=auth_header(user_id))

    def test_deactivating_removes_the_user_from_their_group(self, test_db):
        _seed_users(test_db, [5300, 5301])
        gid = _build_group(test_db, [5300, 5301])
        r = self._deactivate(test_db, 5301)
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid)["memberIds"] == [5300]

    def test_deactivating_the_creator_hands_the_group_over(self, test_db):
        _seed_users(test_db, [5310, 5311])
        gid = _build_group(test_db, [5310, 5311])
        self._deactivate(test_db, 5310)
        group = _group_of(test_db, gid)
        assert group["memberIds"] == [5311]
        assert group["createdBy"] == 5311

    def test_deactivating_cancels_pending_invites(self, test_db):
        _seed_users(test_db, [5320, 5321])
        _seed_mutual_match(test_db, 5320, 5321)
        gid = _create_group(5320).json()["id"]
        iid = _invite(gid, 5320, 5321).json()["id"]
        self._deactivate(test_db, 5321)
        assert test_db["group_invites"].find_one({"id": iid})["status"] == "declined"

    def test_deactivating_the_only_member_closes_the_group(self, test_db):
        _seed_users(test_db, [5330])
        gid = _create_group(5330).json()["id"]
        self._deactivate(test_db, 5330)
        assert _group_of(test_db, gid)["status"] == "closed"


class TestSoftDeleteCascade:

    def _soft_delete(self, test_db, user_id, password="Delete123!"):
        from app.auth.utils import hash_password
        test_db["users"].update_one({"id": user_id},
                                    {"$set": {"hashed_password": hash_password(password)}})
        return client.request("DELETE", f"{BASE}/users/{user_id}",
                              json={"password": password}, headers=auth_header(user_id))

    def test_soft_delete_removes_the_user_from_their_group(self, test_db):
        _seed_users(test_db, [5400, 5401])
        gid = _build_group(test_db, [5400, 5401])
        r = self._soft_delete(test_db, 5401)
        assert r.status_code == 200, r.text
        assert _group_of(test_db, gid)["memberIds"] == [5400]

    def test_soft_delete_cancels_pending_invites(self, test_db):
        _seed_users(test_db, [5410, 5411])
        _seed_mutual_match(test_db, 5410, 5411)
        gid = _create_group(5410).json()["id"]
        iid = _invite(gid, 5410, 5411).json()["id"]
        self._soft_delete(test_db, 5411)
        assert test_db["group_invites"].find_one({"id": iid})["status"] == "declined"


class TestHardDeleteCascade:

    async def _hard_delete(self, user_id):
        from app.services.deletionService import DeletionService
        await DeletionService().hard_delete_user(user_id)

    @pytest.mark.asyncio
    async def test_hard_delete_removes_the_user_from_their_group(self, test_db):
        _seed_users(test_db, [5500, 5501])
        gid = _build_group(test_db, [5500, 5501])
        await self._hard_delete(5501)
        assert _group_of(test_db, gid)["memberIds"] == [5500]

    @pytest.mark.asyncio
    async def test_hard_delete_hands_off_the_creator_role(self, test_db):
        _seed_users(test_db, [5510, 5511])
        gid = _build_group(test_db, [5510, 5511])
        await self._hard_delete(5510)
        group = _group_of(test_db, gid)
        assert group["memberIds"] == [5511]
        assert group["createdBy"] == 5511

    @pytest.mark.asyncio
    async def test_hard_delete_cancels_invites_in_both_directions(self, test_db):
        _seed_users(test_db, [5520, 5521, 5522])
        gid = _build_group(test_db, [5520, 5521])
        _seed_mutual_match(test_db, 5521, 5522)
        outgoing = _invite(gid, 5521, 5522).json()["id"]

        _seed_users(test_db, [5523])
        _seed_mutual_match(test_db, 5523, 5521)
        other_gid = _create_group(5523).json()["id"]
        # 5521 already belongs to a group, so seed the inbound invite directly
        test_db["group_invites"].insert_one({
            "id": 99001, "groupId": other_gid, "fromUserId": 5523,
            "toUserId": 5521, "status": "pending",
            "createdAt": datetime.now(timezone.utc),
        })

        await self._hard_delete(5521)

        assert test_db["group_invites"].find_one({"id": outgoing})["status"] == "declined"
        assert test_db["group_invites"].find_one({"id": 99001})["status"] == "declined"

    @pytest.mark.asyncio
    async def test_hard_delete_closes_a_group_the_user_was_alone_in(self, test_db):
        _seed_users(test_db, [5530])
        gid = _create_group(5530).json()["id"]
        await self._hard_delete(5530)
        group = _group_of(test_db, gid)
        assert group["memberIds"] == []
        assert group["status"] == "closed"

    @pytest.mark.asyncio
    async def test_remaining_members_can_still_use_the_group(self, test_db):
        _seed_users(test_db, [5540, 5541])
        gid = _build_group(test_db, [5540, 5541])
        await self._hard_delete(5541)
        r = client.get(f"{BASE}/groups/{gid}/compatibility", headers=auth_header(5540))
        assert r.status_code == 200, r.text
        assert r.json()["memberIds"] == [5540]
