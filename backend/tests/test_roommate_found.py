"""P3FT.12 — "Found a roommate" status, its side effects, and the outcomes ledger.

The two things easiest to get wrong, and therefore asserted hardest:

  * marking found must NOT sever matches or chats -- the user is done searching,
    not gone. Only discovery surfaces hide them.
  * on hard delete, `outcomes` rows are anonymized, never deleted, and only the
    deleted user's own side is nulled.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, declared_rate_limits, make_match, make_user

client = TestClient(app)
BASE = "/api"


def _mark_found(user_id: int, partner_ids=None, via_app=None, as_user=None):
    body = {}
    if partner_ids is not None:
        body["partnerIds"] = partner_ids
    if via_app is not None:
        body["viaApp"] = via_app
    return client.post(
        f"{BASE}/users/{user_id}/roommate-found",
        json=body,
        headers=auth_header(as_user if as_user is not None else user_id),
    )


def _seed_matched_pair(test_db, a: int, b: int):
    test_db["users"].insert_many([
        make_user(a, matched=True, matchCount=1, matchedWith=[b]),
        make_user(b, matched=True, matchCount=1, matchedWith=[a]),
    ])
    test_db["matches"].insert_one(make_match(a, b))


class TestMarkRoommateFound:

    def test_returns_the_documented_payload(self, test_db):
        _seed_matched_pair(test_db, 3001, 3002)
        r = _mark_found(3001, [3002])
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body.keys()) == {
            "roommateFound", "roommateFoundAt", "roommateFoundWith", "outcomesRecorded"
        }
        assert body["roommateFound"] is True
        assert body["roommateFoundWith"] == [3002]
        assert body["outcomesRecorded"] == 1
        assert body["roommateFoundAt"]

    def test_persists_the_status_fields(self, test_db):
        _seed_matched_pair(test_db, 3010, 3011)
        _mark_found(3010, [3011])
        stored = test_db["users"].find_one({"id": 3010})
        assert stored["roommateFound"] is True
        assert stored["roommateFoundWith"] == [3011]
        assert isinstance(stored["roommateFoundAt"], datetime)

    def test_via_app_defaults_to_true(self, test_db):
        _seed_matched_pair(test_db, 3020, 3021)
        _mark_found(3020, [3021])
        assert test_db["outcomes"].find_one({"userId": 3020})["viaApp"] is True

    def test_via_app_false_is_recorded(self, test_db):
        _seed_matched_pair(test_db, 3030, 3031)
        _mark_found(3030, [3031], via_app=False)
        assert test_db["outcomes"].find_one({"userId": 3030})["viaApp"] is False

    def test_empty_partner_ids_is_allowed(self, test_db):
        test_db["users"].insert_one(make_user(3040))
        r = _mark_found(3040, [])
        assert r.status_code == 200, r.text
        assert r.json()["outcomesRecorded"] == 0

    def test_partner_ids_are_deduplicated(self, test_db):
        _seed_matched_pair(test_db, 3050, 3051)
        r = _mark_found(3050, [3051, 3051, 3051])
        assert r.status_code == 200, r.text
        assert r.json()["roommateFoundWith"] == [3051]
        assert test_db["outcomes"].count_documents({"userId": 3050}) == 1

    def test_more_than_five_partner_ids_is_422(self, test_db):
        test_db["users"].insert_one(make_user(3060))
        r = _mark_found(3060, [1, 2, 3, 4, 5, 6])
        assert r.status_code == 422

    def test_exactly_five_partner_ids_is_accepted(self, test_db):
        test_db["users"].insert_one(make_user(3070))
        r = _mark_found(3070, [1, 2, 3, 4, 5])
        assert r.status_code == 200, r.text

    @pytest.mark.parametrize("bad", [["x"], [1.5], [None], [True], "notalist"])
    def test_non_integer_partner_ids_is_422(self, test_db, bad):
        test_db["users"].insert_one(make_user(3080))
        r = _mark_found(3080, bad)
        assert r.status_code == 422

    def test_404_for_an_unknown_user(self, test_db):
        r = client.post(f"{BASE}/users/999999/roommate-found",
                        json={"partnerIds": []},
                        headers=auth_header(999999))
        # No such user -> the bearer token itself cannot resolve
        assert r.status_code in (401, 404)

    def test_403_when_marking_someone_else(self, test_db):
        test_db["users"].insert_many([make_user(3090), make_user(3091)])
        assert _mark_found(3091, [], as_user=3090).status_code == 403

    def test_rate_limit_is_ten_per_hour(self):
        assert declared_rate_limits(
            "app.routers.userRoutes.mark_roommate_found") == ["10 per 1 hour"]


class TestOutcomesRecording:

    def test_outcome_row_has_the_documented_fields(self, test_db):
        _seed_matched_pair(test_db, 3100, 3101)
        _mark_found(3100, [3101])
        row = test_db["outcomes"].find_one({"userId": 3100})
        assert row["partnerId"] == 3101
        assert row["viaApp"] is True
        assert isinstance(row["recordedAt"], datetime)
        assert 0.0 <= row["compatibilityScore"] <= 1.0

    def test_no_outcome_for_a_partner_who_is_not_a_current_match(self, test_db):
        test_db["users"].insert_many([make_user(3110), make_user(3111)])
        # no matches document between them
        r = _mark_found(3110, [3111])
        assert r.json()["outcomesRecorded"] == 0
        assert test_db["outcomes"].count_documents({}) == 0

    def test_only_real_matches_produce_outcomes_in_a_mixed_list(self, test_db):
        _seed_matched_pair(test_db, 3120, 3121)
        test_db["users"].insert_one(make_user(3122))  # not a match
        r = _mark_found(3120, [3121, 3122])
        assert r.json()["outcomesRecorded"] == 1
        assert {d["partnerId"] for d in test_db["outcomes"].find({})} == {3121}
        # roommateFoundWith still records what the user claimed
        assert r.json()["roommateFoundWith"] == [3121, 3122]

    def test_self_in_partner_ids_produces_no_outcome(self, test_db):
        test_db["users"].insert_one(make_user(3130))
        r = _mark_found(3130, [3130])
        assert r.json()["outcomesRecorded"] == 0

    def test_partner_who_no_longer_exists_produces_no_outcome(self, test_db):
        test_db["users"].insert_one(make_user(3140))
        test_db["matches"].insert_one(make_match(3140, 3141))  # 3141 has no user doc
        r = _mark_found(3140, [3141])
        assert r.json()["outcomesRecorded"] == 0


class TestRoommateFoundSideEffects:

    def test_hidden_from_top_matches(self, test_db):
        _seed_matched_pair(test_db, 3200, 3201)
        test_db["users"].insert_one(make_user(3202))
        test_db["recommendations"].insert_one({
            "userId": 3202,
            "matches": [{"user_id": 3200, "compatibilityScore": 0.9},
                        {"user_id": 3201, "compatibilityScore": 0.5}],
        })
        _mark_found(3200, [3201])
        r = client.get(f"{BASE}/users/3202/top-matches", headers=auth_header(3202))
        assert 3200 not in [m["user_id"] for m in r.json()["matches"]]

    def test_hidden_from_likes_received(self, test_db):
        test_db["users"].insert_many([make_user(3210), make_user(3211)])
        test_db["likes"].insert_one({"fromUser": 3210, "toUser": 3211})
        before = client.get(f"{BASE}/users/3211/likes-received", headers=auth_header(3211))
        assert any(l["fromUser"] == 3210 for l in before.json())

        _mark_found(3210, [])
        after = client.get(f"{BASE}/users/3211/likes-received", headers=auth_header(3211))
        assert all(l["fromUser"] != 3210 for l in after.json())

    def test_pending_sent_likes_are_deleted(self, test_db):
        test_db["users"].insert_many([make_user(3220), make_user(3221), make_user(3222)])
        test_db["likes"].insert_many([
            {"fromUser": 3220, "toUser": 3221},
            {"fromUser": 3220, "toUser": 3222},
            {"fromUser": 3221, "toUser": 3220},  # inbound, must survive
        ])
        _mark_found(3220, [])
        assert test_db["likes"].count_documents({"fromUser": 3220}) == 0
        assert test_db["likes"].count_documents({"toUser": 3220}) == 1

    def test_own_recommendations_document_is_deleted(self, test_db):
        test_db["users"].insert_one(make_user(3230))
        test_db["recommendations"].insert_one({"userId": 3230, "matches": []})
        _mark_found(3230, [])
        assert test_db["recommendations"].find_one({"userId": 3230}) is None

    def test_pulled_from_other_users_recommendations(self, test_db):
        test_db["users"].insert_many([make_user(3240), make_user(3241)])
        test_db["recommendations"].insert_one({
            "userId": 3241,
            "matches": [{"user_id": 3240, "compatibilityScore": 0.9},
                        {"user_id": 3299, "compatibilityScore": 0.4}],
        })
        _mark_found(3240, [])
        others = test_db["recommendations"].find_one({"userId": 3241})
        assert [m["user_id"] for m in others["matches"]] == [3299]

    def test_matches_remain_accessible(self, test_db):
        _seed_matched_pair(test_db, 3250, 3251)
        _mark_found(3250, [3251])

        assert test_db["matches"].count_documents(
            {"$or": [{"user1_id": 3250}, {"user2_id": 3250}]}) == 1
        r = client.get(f"{BASE}/users/3250/matches", headers=auth_header(3250))
        assert r.status_code == 200, r.text
        partners = [m["user2_id"] if m["user1_id"] == 3250 else m["user1_id"]
                    for m in r.json()]
        assert 3251 in partners

    def test_the_partner_can_still_see_the_match(self, test_db):
        _seed_matched_pair(test_db, 3260, 3261)
        _mark_found(3260, [3261])
        r = client.get(f"{BASE}/users/3261/matches", headers=auth_header(3261))
        assert r.status_code == 200, r.text
        partners = [m["user2_id"] if m["user1_id"] == 3261 else m["user1_id"]
                    for m in r.json()]
        assert 3260 in partners

    def test_chats_remain_accessible(self, test_db):
        _seed_matched_pair(test_db, 3270, 3271)
        test_db["chat_messages"].insert_one({
            "fromUser": 3270, "toUser": 3271, "message": "see you in august",
            "timestamp": datetime.now(timezone.utc), "read": False,
        })
        _mark_found(3270, [3271])

        r = client.get(f"{BASE}/users/3270/chat/3271", headers=auth_header(3270))
        assert r.status_code == 200, r.text
        messages = r.json()["messages"]
        assert any(m["message"] == "see you in august" for m in messages)

    def test_can_still_send_a_chat_after_marking_found(self, test_db):
        _seed_matched_pair(test_db, 3280, 3281)
        _mark_found(3280, [3281])
        r = client.post(f"{BASE}/users/3280/chat/3281",
                        json={"content": "lease signed"},
                        headers=auth_header(3280))
        assert r.status_code in (200, 201), r.text


class TestUndoRoommateFound:

    def test_undo_clears_the_flag(self, test_db):
        _seed_matched_pair(test_db, 3300, 3301)
        _mark_found(3300, [3301])
        r = client.post(f"{BASE}/users/3300/roommate-found/undo", headers=auth_header(3300))
        assert r.status_code == 200, r.text
        assert r.json() == {"roommateFound": False}

    def test_undo_unsets_the_metadata_fields(self, test_db):
        _seed_matched_pair(test_db, 3310, 3311)
        _mark_found(3310, [3311])
        client.post(f"{BASE}/users/3310/roommate-found/undo", headers=auth_header(3310))
        stored = test_db["users"].find_one({"id": 3310})
        assert stored["roommateFound"] is False
        assert "roommateFoundAt" not in stored
        assert "roommateFoundWith" not in stored

    def test_undo_makes_the_user_visible_again(self, test_db):
        test_db["users"].insert_many([make_user(3320), make_user(3321)])
        test_db["recommendations"].insert_one({
            "userId": 3321, "matches": [{"user_id": 3320, "compatibilityScore": 0.9}],
        })
        _mark_found(3320, [])
        client.post(f"{BASE}/users/3320/roommate-found/undo", headers=auth_header(3320))

        # Rebuild the recommendation entry the way the app would, then confirm
        # the visibility gate no longer excludes them.
        test_db["recommendations"].update_one(
            {"userId": 3321},
            {"$set": {"matches": [{"user_id": 3320, "compatibilityScore": 0.9}]}},
        )
        r = client.get(f"{BASE}/users/3321/top-matches", headers=auth_header(3321))
        assert 3320 in [m["user_id"] for m in r.json()["matches"]]

    def test_undo_does_not_delete_the_outcome_rows(self, test_db):
        _seed_matched_pair(test_db, 3330, 3331)
        _mark_found(3330, [3331])
        client.post(f"{BASE}/users/3330/roommate-found/undo", headers=auth_header(3330))
        assert test_db["outcomes"].count_documents({"userId": 3330}) == 1

    def test_403_when_undoing_for_someone_else(self, test_db):
        test_db["users"].insert_many([make_user(3340), make_user(3341)])
        r = client.post(f"{BASE}/users/3341/roommate-found/undo", headers=auth_header(3340))
        assert r.status_code == 403


class TestRoommateFoundImmutableViaProfileUpdate:

    def _body(self, **extra):
        from tests.helpers import prefs
        body = {"username": "immutable1", "gender": "male"}
        body.update(prefs())
        body.update(extra)
        return body

    def test_put_cannot_set_roommate_found(self, test_db):
        test_db["users"].insert_one(make_user(3400))
        r = client.put(f"{BASE}/users/3400", json=self._body(roommateFound=True),
                       headers=auth_header(3400))
        assert r.status_code in (200, 422), r.text
        stored = test_db["users"].find_one({"id": 3400})
        assert not stored.get("roommateFound")

    def test_put_cannot_set_roommate_found_at_or_with(self, test_db):
        test_db["users"].insert_one(make_user(3410))
        client.put(
            f"{BASE}/users/3410",
            json=self._body(roommateFoundAt="2026-01-01T00:00:00Z",
                            roommateFoundWith=[999]),
            headers=auth_header(3410),
        )
        stored = test_db["users"].find_one({"id": 3410})
        assert "roommateFoundAt" not in stored
        assert "roommateFoundWith" not in stored

    def test_put_cannot_clear_an_existing_roommate_found(self, test_db):
        _seed_matched_pair(test_db, 3420, 3421)
        _mark_found(3420, [3421])
        client.put(f"{BASE}/users/3420", json=self._body(roommateFound=False),
                   headers=auth_header(3420))
        assert test_db["users"].find_one({"id": 3420})["roommateFound"] is True

    def test_the_three_fields_are_in_immutable_fields(self):
        from app.routers.userRoutes import _IMMUTABLE_FIELDS
        assert {"roommateFound", "roommateFoundAt", "roommateFoundWith"} <= _IMMUTABLE_FIELDS


class TestAdminListExposesRoommateFound:

    def _as_admin(self, monkeypatch, admin_id):
        monkeypatch.setenv("ADMIN_USER_IDS", str(admin_id))

    def test_rows_carry_roommate_found(self, test_db, monkeypatch):
        self._as_admin(monkeypatch, 3500)
        _seed_matched_pair(test_db, 3501, 3502)
        test_db["users"].insert_one(make_user(3500))
        _mark_found(3501, [3502])

        r = client.get(f"{BASE}/admin/users", headers=auth_header(3500))
        assert r.status_code == 200, r.text
        rows = {u["id"]: u for u in r.json()}
        assert rows[3501]["roommateFound"] is True

    def test_field_is_always_present_even_when_never_set(self, test_db, monkeypatch):
        self._as_admin(monkeypatch, 3510)
        test_db["users"].insert_many([make_user(3510), make_user(3511)])
        r = client.get(f"{BASE}/admin/users", headers=auth_header(3510))
        rows = {u["id"]: u for u in r.json()}
        assert rows[3511]["roommateFound"] is False
        assert all("roommateFound" in u for u in r.json())


class TestOutcomesAnonymizedOnHardDelete:
    """Hard delete anonymizes outcome rows instead of removing them.

    The analytical value lives in compatibilityScore + viaApp + recordedAt;
    deleting rows would bias weight tuning toward users who never left.
    """

    async def _hard_delete(self, user_id: int):
        from app.services.deletionService import DeletionService
        await DeletionService().hard_delete_user(user_id)

    @pytest.mark.asyncio
    async def test_row_survives_with_the_deleted_side_nulled(self, test_db):
        _seed_matched_pair(test_db, 3600, 3601)
        _mark_found(3600, [3601])
        original = test_db["outcomes"].find_one({"userId": 3600})
        assert original is not None

        await self._hard_delete(3600)

        assert test_db["outcomes"].count_documents({}) == 1
        row = test_db["outcomes"].find_one({})
        assert row["userId"] is None
        assert row["partnerId"] == 3601

    @pytest.mark.asyncio
    async def test_analytical_fields_are_preserved_unchanged(self, test_db):
        _seed_matched_pair(test_db, 3610, 3611)
        _mark_found(3610, [3611], via_app=False)
        before = test_db["outcomes"].find_one({"userId": 3610})

        await self._hard_delete(3610)

        after = test_db["outcomes"].find_one({})
        assert after["compatibilityScore"] == before["compatibilityScore"]
        assert after["viaApp"] == before["viaApp"] is False
        assert after["recordedAt"] == before["recordedAt"]

    @pytest.mark.asyncio
    async def test_deleting_the_partner_keeps_the_active_users_side_intact(self, test_db):
        _seed_matched_pair(test_db, 3620, 3621)
        _mark_found(3620, [3621])

        await self._hard_delete(3621)  # the partner leaves, not the recorder

        row = test_db["outcomes"].find_one({})
        assert row is not None
        assert row["userId"] == 3620          # active side untouched
        assert row["partnerId"] is None       # deleted side nulled

    @pytest.mark.asyncio
    async def test_both_sides_null_when_both_users_are_deleted(self, test_db):
        _seed_matched_pair(test_db, 3630, 3631)
        _mark_found(3630, [3631])

        await self._hard_delete(3630)
        await self._hard_delete(3631)

        row = test_db["outcomes"].find_one({})
        assert row is not None
        assert row["userId"] is None
        assert row["partnerId"] is None
        assert row["compatibilityScore"] is not None

    @pytest.mark.asyncio
    async def test_unrelated_outcome_rows_are_untouched(self, test_db):
        _seed_matched_pair(test_db, 3640, 3641)
        _mark_found(3640, [3641])
        test_db["outcomes"].insert_one({
            "userId": 7001, "partnerId": 7002, "compatibilityScore": 0.5,
            "viaApp": True, "recordedAt": datetime.now(timezone.utc),
        })

        await self._hard_delete(3640)

        untouched = test_db["outcomes"].find_one({"userId": 7001})
        assert untouched["partnerId"] == 7002

    @pytest.mark.asyncio
    async def test_other_collections_are_still_hard_deleted(self, test_db):
        """Anonymization applies to `outcomes` only, not to the rest of the cascade."""
        _seed_matched_pair(test_db, 3650, 3651)
        test_db["chat_messages"].insert_one({
            "fromUser": 3650, "toUser": 3651, "message": "hi",
            "timestamp": datetime.now(timezone.utc),
        })
        _mark_found(3650, [3651])

        await self._hard_delete(3650)

        assert test_db["users"].find_one({"id": 3650}) is None
        assert test_db["chat_messages"].count_documents({"fromUser": 3650}) == 0
        assert test_db["matches"].count_documents(
            {"$or": [{"user1_id": 3650}, {"user2_id": 3650}]}) == 0
        assert test_db["outcomes"].count_documents({}) == 1


class TestExportIncludesPhase3Collections:

    def test_export_has_the_three_new_keys(self, test_db):
        test_db["users"].insert_one(make_user(3700, hashed_password="x"))
        r = client.get(f"{BASE}/users/3700/export", headers=auth_header(3700))
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("groups", "group_invites", "outcomes"):
            assert key in body
            assert isinstance(body[key], list)

    def test_export_includes_the_users_outcomes(self, test_db):
        _seed_matched_pair(test_db, 3710, 3711)
        _mark_found(3710, [3711])
        body = client.get(f"{BASE}/users/3710/export", headers=auth_header(3710)).json()
        assert len(body["outcomes"]) == 1
        assert body["outcomes"][0]["partnerId"] == 3711

    def test_export_omits_mongo_ids(self, test_db):
        _seed_matched_pair(test_db, 3720, 3721)
        _mark_found(3720, [3721])
        test_db["groups"].insert_one({
            "id": 1, "name": "g", "memberIds": [3720, 3721], "createdBy": 3720,
            "createdAt": datetime.now(timezone.utc), "maxSize": 4, "status": "open",
        })
        test_db["group_invites"].insert_one({
            "id": 1, "groupId": 1, "fromUserId": 3720, "toUserId": 3721,
            "status": "pending", "createdAt": datetime.now(timezone.utc),
        })
        body = client.get(f"{BASE}/users/3720/export", headers=auth_header(3720)).json()
        for key in ("groups", "group_invites", "outcomes"):
            assert body[key], f"{key} should not be empty for this fixture"
            for doc in body[key]:
                assert "_id" not in doc

    def test_export_groups_carry_ids_only_not_member_profiles(self, test_db):
        test_db["users"].insert_many([
            make_user(3730, hashed_password="x"),
            make_user(3731, username="secretmate", email="mate@auburn.edu"),
        ])
        test_db["groups"].insert_one({
            "id": 2, "name": "Toomer Crew", "memberIds": [3730, 3731],
            "createdBy": 3730, "createdAt": datetime.now(timezone.utc),
            "maxSize": 4, "status": "open",
        })
        r = client.get(f"{BASE}/users/3730/export", headers=auth_header(3730))
        assert r.status_code == 200, r.text
        group = r.json()["groups"][0]
        assert group["memberIds"] == [3730, 3731]
        assert "members" not in group
        assert "secretmate" not in r.text
        assert "mate@auburn.edu" not in r.text

    def test_export_invites_carry_ids_only(self, test_db):
        test_db["users"].insert_many([
            make_user(3740, hashed_password="x"),
            make_user(3741, username="inviteeuser"),
        ])
        test_db["group_invites"].insert_one({
            "id": 3, "groupId": 9, "fromUserId": 3740, "toUserId": 3741,
            "status": "pending", "createdAt": datetime.now(timezone.utc),
        })
        r = client.get(f"{BASE}/users/3740/export", headers=auth_header(3740))
        invite = r.json()["group_invites"][0]
        assert invite["fromUserId"] == 3740
        assert invite["toUserId"] == 3741
        assert "toUsername" not in invite
        assert "fromUsername" not in invite
        assert "inviteeuser" not in r.text

    def test_export_never_includes_the_password_hash(self, test_db):
        _seed_matched_pair(test_db, 3750, 3751)
        test_db["users"].update_one({"id": 3750},
                                    {"$set": {"hashed_password": "super-secret-hash"}})
        r = client.get(f"{BASE}/users/3750/export", headers=auth_header(3750))
        assert "super-secret-hash" not in r.text
        assert "hashed_password" not in r.json()["user"]
