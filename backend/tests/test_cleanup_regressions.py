"""Regression coverage for the Phase 3 backend cleanup.

This sprint deleted `matchRoutes.py`, `chatRoutes.py`, `clusterService.py`,
`userProfiles.py` and the `ConfirmedMatch` model, and moved several behaviours
that those modules only *claimed* to provide onto endpoints that are actually
mounted.  The tests here pin the replacements so a future revert cannot quietly
put the dead code back or drop the capability it was standing in for.

Covered:
  * the deleted modules stay deleted, and `ConfirmedMatch` stays gone
  * `GET /users/{id}/chat/{partner_id}?after=` — the timestamp pagination
    `chatRoutes.py` advertised by calling a kwarg that did not exist
  * `POST /users/{id}/notifications/{notification_id}/mark-read` (P3B.6)
  * `matches.compatibilityScore` (P3D.2) — forward-only, never backfilled
  * P3B.8 / P3B.9 — background, conditional, rate-limited recompute
  * P3B.10 — the APScheduler maintenance jobs and their non-fatal startup
"""
import importlib
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_header, declared_rate_limits, make_user, pref, prefs

client = TestClient(app)
BASE = "/api"


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Deleted modules stay deleted
# ---------------------------------------------------------------------------

class TestDeletedModulesStayDeleted:

    @pytest.mark.parametrize("module", [
        "app.routers.matchRoutes",
        "app.routers.chatRoutes",
        "app.services.clusterService",
        "app.services.userProfiles",
    ])
    def test_module_is_gone(self, module):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)

    def test_confirmed_match_model_is_gone(self):
        import app.models as models
        assert not hasattr(models, "ConfirmedMatch"), (
            "ConfirmedMatch modelled `matches` documents with a required "
            "compatibilityScore that no stored document had; it was removed in "
            "P3D.2 and must not come back."
        )

    def test_no_router_references_the_deleted_modules(self):
        import app.main
        mounted = {
            getattr(r, "endpoint", None).__module__
            for r in app.main.app.routes
            if getattr(r, "endpoint", None) is not None
        }
        for dead in ("app.routers.matchRoutes", "app.routers.chatRoutes"):
            assert dead not in mounted


# ---------------------------------------------------------------------------
# GET /users/{id}/chat/{partner_id} — the new `after` parameter
# ---------------------------------------------------------------------------

class TestChatAfterParameter:

    A, B = 8100, 8101

    def _seed(self, test_db):
        test_db["users"].insert_one(make_user(self.A))
        test_db["users"].insert_one(make_user(self.B))
        test_db["matches"].insert_one(
            {"user1_id": self.A, "user2_id": self.B, "status": "confirmed"}
        )
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(3):
            test_db["chat_messages"].insert_one({
                "fromUser": self.A, "toUser": self.B,
                "content": f"msg{i}",
                "createdAt": base + timedelta(minutes=i),
            })
        return base

    def _get(self, after=None):
        """`params=` rather than a hand-built query string on purpose: an
        ISO-8601 offset contains `+`, which a raw query string decodes as a
        space.  Callers must percent-encode it (axios `params` does)."""
        params = {} if after is None else {"after": after}
        return client.get(
            f"{BASE}/users/{self.A}/chat/{self.B}",
            params=params,
            headers=auth_header(self.A),
        )

    def test_without_after_returns_every_message(self, test_db):
        self._seed(test_db)
        r = self._get()
        assert r.status_code == 200, r.text
        assert [m["content"] for m in r.json()["messages"]] == ["msg0", "msg1", "msg2"]

    def test_after_returns_only_strictly_newer_messages(self, test_db):
        base = self._seed(test_db)
        r = self._get(_iso(base))
        assert r.status_code == 200, r.text
        assert [m["content"] for m in r.json()["messages"]] == ["msg1", "msg2"]

    def test_after_is_exclusive_of_the_supplied_timestamp(self, test_db):
        base = self._seed(test_db)
        r = self._get(_iso(base + timedelta(minutes=1)))
        assert [m["content"] for m in r.json()["messages"]] == ["msg2"]

    def test_after_beyond_the_newest_message_returns_empty(self, test_db):
        base = self._seed(test_db)
        r = self._get(_iso(base + timedelta(days=1)))
        assert r.status_code == 200, r.text
        assert r.json()["messages"] == []

    def test_after_accepts_a_z_suffixed_timestamp(self, test_db):
        base = self._seed(test_db)
        r = self._get(base.strftime('%Y-%m-%dT%H:%M:%S') + 'Z')
        assert r.status_code == 200, r.text
        assert [m["content"] for m in r.json()["messages"]] == ["msg1", "msg2"]

    def test_after_accepts_a_naive_timestamp_as_utc(self, test_db):
        base = self._seed(test_db)
        r = self._get(base.replace(tzinfo=None).isoformat())
        assert r.status_code == 200, r.text
        assert [m["content"] for m in r.json()["messages"]] == ["msg1", "msg2"]

    @pytest.mark.parametrize("bad", ["yesterday", "2026-13-45", "1700000000", "--"])
    def test_unparseable_after_is_400(self, test_db, bad):
        self._seed(test_db)
        assert self._get(bad).status_code == 400

    def test_empty_after_is_treated_as_absent(self, test_db):
        self._seed(test_db)
        r = self._get("")
        assert r.status_code == 200, r.text
        assert len(r.json()["messages"]) == 3

    def test_response_still_carries_partner_last_read_at(self, test_db):
        """The `after` addition must not change the envelope."""
        base = self._seed(test_db)
        body = self._get(_iso(base)).json()
        assert set(body.keys()) == {"messages", "partner_last_read_at"}

    def test_unencoded_plus_offset_is_rejected(self, test_db):
        """A `+` that reached the server unencoded arrived as a space, so the
        timestamp no longer parses.  Clients must percent-encode the offset (or
        use the `Z` form); this pins the 400 so the behaviour is not mistaken
        for a server-side parsing bug."""
        self._seed(test_db)
        r = client.get(
            f"{BASE}/users/{self.A}/chat/{self.B}?after=2026-01-01T12:00:00+00:00",
            headers=auth_header(self.A),
        )
        assert r.status_code == 400

    def test_after_does_not_bypass_the_match_requirement(self, test_db):
        test_db["users"].insert_one(make_user(self.A))
        test_db["users"].insert_one(make_user(self.B))
        # deliberately no match document
        r = self._get("2020-01-01T00:00:00+00:00")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /users/{id}/notifications/{notification_id}/mark-read  (P3B.6)
# ---------------------------------------------------------------------------

class TestMarkSingleNotificationRead:

    OWNER, OTHER = 8200, 8201

    def _seed_notification(self, test_db, to_user: int, read: bool = False):
        test_db["users"].insert_one(make_user(to_user))
        result = test_db["notifications"].insert_one({
            "type": "like_received", "fromUser": 9999, "toUser": to_user,
            "message": "someone liked you", "read": read,
            "createdAt": datetime.now(timezone.utc),
        })
        return str(result.inserted_id)

    def _post(self, user_id: int, notif_id: str, headers=None):
        return client.post(
            f"{BASE}/users/{user_id}/notifications/{notif_id}/mark-read",
            headers=headers if headers is not None else auth_header(user_id),
        )

    def test_marks_own_unread_notification(self, test_db):
        nid = self._seed_notification(test_db, self.OWNER)
        r = self._post(self.OWNER, nid)
        assert r.status_code == 200, r.text
        assert r.json() == {"marked": 1}

    def test_the_document_is_actually_flagged_read(self, test_db):
        from bson import ObjectId
        nid = self._seed_notification(test_db, self.OWNER)
        self._post(self.OWNER, nid)
        doc = test_db["notifications"].find_one({"_id": ObjectId(nid)})
        assert doc["read"] is True

    def test_malformed_id_is_400(self, test_db):
        self._seed_notification(test_db, self.OWNER)
        assert self._post(self.OWNER, "not-an-object-id").status_code == 400

    def test_unknown_but_well_formed_id_is_404(self, test_db):
        self._seed_notification(test_db, self.OWNER)
        assert self._post(self.OWNER, "0" * 24).status_code == 404

    def test_already_read_notification_is_404(self, test_db):
        nid = self._seed_notification(test_db, self.OWNER, read=True)
        assert self._post(self.OWNER, nid).status_code == 404

    def test_marking_twice_returns_404_the_second_time(self, test_db):
        nid = self._seed_notification(test_db, self.OWNER)
        assert self._post(self.OWNER, nid).status_code == 200
        assert self._post(self.OWNER, nid).status_code == 404

    def test_someone_elses_notification_is_404_not_200(self, test_db):
        """The service scopes its update to `toUser`, so another user's valid id
        is indistinguishable from a missing one — and, critically, is NOT
        marked read."""
        from bson import ObjectId
        nid = self._seed_notification(test_db, self.OTHER)
        test_db["users"].insert_one(make_user(self.OWNER))

        r = self._post(self.OWNER, nid)
        assert r.status_code == 404
        assert test_db["notifications"].find_one({"_id": ObjectId(nid)})["read"] is False

    def test_cannot_mark_read_on_another_users_path(self, test_db):
        nid = self._seed_notification(test_db, self.OTHER)
        test_db["users"].insert_one(make_user(self.OWNER))
        r = self._post(self.OTHER, nid, headers=auth_header(self.OWNER))
        assert r.status_code == 403

    def test_unauthenticated_is_rejected(self, test_db):
        nid = self._seed_notification(test_db, self.OWNER)
        r = client.post(f"{BASE}/users/{self.OWNER}/notifications/{nid}/mark-read")
        assert r.status_code in (401, 403)

    def test_rate_limit_is_60_per_minute(self):
        assert declared_rate_limits(
            "app.routers.userRoutes.mark_notification_read"
        ) == ["60 per 1 minute"]

    def test_bulk_mark_read_endpoint_still_works(self, test_db):
        """The single-notification route must not have shadowed the bulk one."""
        self._seed_notification(test_db, self.OWNER)
        self._seed_notification(test_db, self.OWNER)
        r = client.post(
            f"{BASE}/users/{self.OWNER}/notifications/mark-read",
            headers=auth_header(self.OWNER),
        )
        assert r.status_code == 200, r.text
        assert r.json()["marked"] == 2


# ---------------------------------------------------------------------------
# matches.compatibilityScore  (P3D.2) — forward-only, never backfilled
# ---------------------------------------------------------------------------

class TestMatchCompatibilityScore:

    A, B = 8300, 8301

    def _seed_pair(self, test_db):
        test_db["users"].insert_one(make_user(self.A, gender="male"))
        test_db["users"].insert_one(make_user(self.B, gender="male"))

    def test_a_new_match_carries_a_compatibility_score(self, test_db):
        self._seed_pair(test_db)
        assert client.post(f"{BASE}/users/{self.A}/like", json={"toUser": self.B},
                           headers=auth_header(self.A)).status_code == 200
        assert client.post(f"{BASE}/users/{self.B}/like", json={"toUser": self.A},
                           headers=auth_header(self.B)).status_code == 200

        match = test_db["matches"].find_one({})
        assert match is not None, "mutual like did not create a match"
        assert "compatibilityScore" in match
        assert isinstance(match["compatibilityScore"], float)
        assert 0.0 <= match["compatibilityScore"] <= 1.0

    def test_score_is_none_when_a_profile_cannot_be_scored(self, test_db):
        """A malformed profile must never block a match — the field goes null."""
        test_db["users"].insert_one(make_user(self.A))
        broken = make_user(self.B)
        del broken["sleepScoreWD"]
        test_db["users"].insert_one(broken)

        client.post(f"{BASE}/users/{self.A}/like", json={"toUser": self.B},
                    headers=auth_header(self.A))
        r = client.post(f"{BASE}/users/{self.B}/like", json={"toUser": self.A},
                        headers=auth_header(self.B))
        assert r.status_code == 200, r.text

        match = test_db["matches"].find_one({})
        assert match is not None
        assert match["compatibilityScore"] is None

    def test_legacy_match_without_the_field_still_lists(self, test_db):
        """Old documents were deliberately NOT backfilled; reading them must work."""
        self._seed_pair(test_db)
        test_db["matches"].insert_one({
            "user1_id": self.A, "user2_id": self.B, "status": "confirmed",
        })
        r = client.get(f"{BASE}/users/{self.A}/matches", headers=auth_header(self.A))
        assert r.status_code == 200, r.text

    def test_legacy_match_with_explicit_null_still_lists(self, test_db):
        self._seed_pair(test_db)
        test_db["matches"].insert_one({
            "user1_id": self.A, "user2_id": self.B, "status": "confirmed",
            "compatibilityScore": None,
        })
        r = client.get(f"{BASE}/users/{self.A}/matches", headers=auth_header(self.A))
        assert r.status_code == 200, r.text

    def test_existing_documents_are_not_backfilled(self, test_db):
        """Nothing may retroactively invent a score for a pre-P3D.2 match."""
        self._seed_pair(test_db)
        test_db["matches"].insert_one({
            "user1_id": self.A, "user2_id": self.B, "status": "confirmed",
        })
        client.get(f"{BASE}/users/{self.A}/matches", headers=auth_header(self.A))
        assert "compatibilityScore" not in test_db["matches"].find_one({})


# ---------------------------------------------------------------------------
# P3B.8 / P3B.9 — background, conditional, rate-limited recompute
# ---------------------------------------------------------------------------

class TestSignificantChangeDetection:

    def test_no_change_is_not_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        doc = {"cleanlinessScore": {"value": 5.0, "isDealBreaker": False}}
        assert preferences_changed_significantly(doc, dict(doc)) is False

    def test_shift_below_two_is_not_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        before = {"cleanlinessScore": {"value": 5.0, "isDealBreaker": False}}
        after = {"cleanlinessScore": {"value": 6.9, "isDealBreaker": False}}
        assert preferences_changed_significantly(before, after) is False

    def test_shift_of_exactly_two_is_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        before = {"cleanlinessScore": {"value": 5.0, "isDealBreaker": False}}
        after = {"cleanlinessScore": {"value": 7.0, "isDealBreaker": False}}
        assert preferences_changed_significantly(before, after) is True

    def test_downward_shift_of_two_is_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        before = {"cleanlinessScore": {"value": 7.0, "isDealBreaker": False}}
        after = {"cleanlinessScore": {"value": 5.0, "isDealBreaker": False}}
        assert preferences_changed_significantly(before, after) is True

    def test_deal_breaker_toggle_alone_is_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        before = {"guestsScore": {"value": 5.0, "isDealBreaker": False}}
        after = {"guestsScore": {"value": 5.0, "isDealBreaker": True}}
        assert preferences_changed_significantly(before, after) is True

    def test_newly_supplied_preference_is_significant(self):
        from app.services.recommendationService import preferences_changed_significantly
        after = {"guestsScore": {"value": 5.0, "isDealBreaker": False}}
        assert preferences_changed_significantly({}, after) is True

    def test_field_absent_from_the_update_is_ignored(self):
        from app.services.recommendationService import preferences_changed_significantly
        before = {"guestsScore": {"value": 1.0, "isDealBreaker": False}}
        assert preferences_changed_significantly(before, {}) is False

    def test_significant_shift_constant_is_two(self):
        from app.services.recommendationService import SIGNIFICANT_SHIFT
        assert SIGNIFICANT_SHIFT == 2.0

    def test_cooldown_is_one_hour(self):
        from app.services.recommendationService import RECOMPUTE_COOLDOWN
        assert RECOMPUTE_COOLDOWN == timedelta(hours=1)


class TestRecomputeGating:
    """`should_recompute_on_profile_save` plus its effect on PUT /users/{id}."""

    UID = 8400

    @pytest.fixture
    def spy(self, monkeypatch):
        import app.routers.userRoutes as rv
        calls = []

        async def _fake(user_id):
            calls.append(user_id)

        monkeypatch.setattr(rv.recommendationService, "recompute_for_user_id", _fake)
        return calls

    def _put(self, test_db, uid, **pref_overrides):
        body = {"username": f"user{uid}", "gender": "male"}
        body.update(prefs(5.0, **pref_overrides))
        return client.put(f"{BASE}/users/{uid}", json=body, headers=auth_header(uid))

    def test_small_change_does_not_queue_a_recompute(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        assert self._put(test_db, self.UID, cleanlinessScore=5.5).status_code == 200
        assert spy == []

    def test_significant_change_queues_a_recompute(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        assert self._put(test_db, self.UID, cleanlinessScore=9.0).status_code == 200
        assert spy == [self.UID]

    def test_deal_breaker_toggle_queues_a_recompute(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        r = self._put(test_db, self.UID,
                      guestsScore=pref(5.0, deal_breaker=True))
        assert r.status_code == 200, r.text
        assert spy == [self.UID]

    def test_second_significant_save_within_the_hour_is_rate_limited(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        assert self._put(test_db, self.UID, cleanlinessScore=9.0).status_code == 200
        assert self._put(test_db, self.UID, cleanlinessScore=1.0).status_code == 200
        assert spy == [self.UID], "the cooldown did not suppress the second recompute"

    def test_cooldown_expires(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        test_db["users"].update_one(
            {"id": self.UID},
            {"$set": {"lastRecomputeAt": datetime.now(timezone.utc) - timedelta(hours=2)}},
        )
        assert self._put(test_db, self.UID, cleanlinessScore=9.0).status_code == 200
        assert spy == [self.UID]

    def test_the_cooldown_slot_is_claimed_on_the_first_save(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        self._put(test_db, self.UID, cleanlinessScore=9.0)
        assert isinstance(
            test_db["users"].find_one({"id": self.UID}).get("lastRecomputeAt"),
            datetime,
        )

    def test_create_user_always_queues_a_recompute(self, test_db, spy):
        test_db["users"].insert_one(make_user(self.UID))
        body = {"username": "brandnew", "gender": "female"}
        body.update(prefs())
        r = client.post(f"{BASE}/users", json=body, headers=auth_header(self.UID))
        assert r.status_code == 200, r.text
        assert len(spy) == 1

    def test_a_failing_recompute_does_not_fail_the_save(self, test_db, monkeypatch):
        """Scheduling is best-effort; the profile write is the contract."""
        import app.routers.userRoutes as rv

        async def _boom(user_id, before, after):
            raise RuntimeError("gate exploded")

        monkeypatch.setattr(
            rv.recommendationService, "should_recompute_on_profile_save", _boom
        )
        test_db["users"].insert_one(make_user(self.UID))
        assert self._put(test_db, self.UID, cleanlinessScore=9.0).status_code == 200


# ---------------------------------------------------------------------------
# P3B.10 — scheduled maintenance
# ---------------------------------------------------------------------------

class _FakeScheduler:
    instances = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.jobs = []
        self.started = False
        _FakeScheduler.instances.append(self)

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def start(self):
        self.started = True


class TestScheduler:

    @pytest.fixture
    def fake_scheduler(self, monkeypatch):
        import apscheduler.schedulers.asyncio as aio
        _FakeScheduler.instances = []
        monkeypatch.setattr(aio, "AsyncIOScheduler", _FakeScheduler)
        monkeypatch.setenv("ROOMMATCH_ENV", "production")
        return _FakeScheduler

    def test_skipped_under_the_test_environment(self, monkeypatch):
        """The suite must never get a live scheduler thread against the test DB."""
        import app.main as main
        monkeypatch.setenv("ROOMMATCH_ENV", "test")
        assert main._start_scheduler() is None

    def test_registers_both_jobs(self, fake_scheduler):
        import app.main as main
        sched = main._start_scheduler()
        assert sched is not None
        assert {j["id"] for j in sched.jobs} == {"retention_cleanup", "nightly_recompute"}

    def test_scheduler_runs_in_utc(self, fake_scheduler):
        import app.main as main
        assert main._start_scheduler().kwargs.get("timezone") == "UTC"

    def test_retention_cleanup_runs_at_0300(self, fake_scheduler):
        import app.main as main
        job = next(j for j in main._start_scheduler().jobs
                   if j["id"] == "retention_cleanup")
        assert job["func"] is main._run_retention_cleanup
        assert job["trigger"].fields is not None
        assert "hour='3'" in str(job["trigger"])
        assert "minute='0'" in str(job["trigger"])

    def test_nightly_recompute_runs_at_0400(self, fake_scheduler):
        import app.main as main
        job = next(j for j in main._start_scheduler().jobs
                   if j["id"] == "nightly_recompute")
        assert job["func"] is main._run_nightly_recompute
        assert "hour='4'" in str(job["trigger"])
        assert "minute='0'" in str(job["trigger"])

    @pytest.mark.parametrize("job_id", ["retention_cleanup", "nightly_recompute"])
    def test_jobs_do_not_overlap_and_coalesce(self, fake_scheduler, job_id):
        """A slow run must not stack a second copy on top of itself."""
        import app.main as main
        job = next(j for j in main._start_scheduler().jobs if j["id"] == job_id)
        assert job["max_instances"] == 1
        assert job["coalesce"] is True
        assert job["replace_existing"] is True

    def test_scheduler_is_started(self, fake_scheduler):
        import app.main as main
        assert main._start_scheduler().started is True

    def test_missing_apscheduler_degrades_instead_of_crashing(self, monkeypatch, caplog):
        """A missing APScheduler must log and return None, never raise — the app
        falls back to startup-only cleanup rather than failing to boot."""
        import logging
        import app.main as main
        monkeypatch.setenv("ROOMMATCH_ENV", "production")
        monkeypatch.setitem(sys.modules, "apscheduler.schedulers.asyncio", None)

        with caplog.at_level(logging.WARNING):
            assert main._start_scheduler() is None
        assert any("APScheduler" in rec.message for rec in caplog.records)

    def test_a_scheduler_that_refuses_to_start_is_non_fatal(self, monkeypatch):
        import apscheduler.schedulers.asyncio as aio
        import app.main as main

        class _Exploding(_FakeScheduler):
            def start(self):
                raise RuntimeError("no thread for you")

        monkeypatch.setenv("ROOMMATCH_ENV", "production")
        monkeypatch.setattr(aio, "AsyncIOScheduler", _Exploding)
        assert main._start_scheduler() is None

    async def test_retention_cleanup_swallows_failures(self, monkeypatch):
        import app.main as main
        import app.services.deletionService as ds

        class _Boom:
            async def cleanup_expired_deletions(self):
                raise RuntimeError("mongo down")

        monkeypatch.setattr(ds, "DeletionService", _Boom)
        await main._run_retention_cleanup()  # must not raise

    async def test_nightly_recompute_swallows_failures(self, monkeypatch):
        import app.main as main
        import app.services.recommendationService as rs

        class _Boom:
            async def recompute_all_active(self):
                raise RuntimeError("mongo down")

        monkeypatch.setattr(rs, "RecommendationService", _Boom)
        await main._run_nightly_recompute()  # must not raise

    async def test_retention_cleanup_hard_deletes_stale_deactivated_accounts(self, test_db):
        import app.main as main
        old = datetime.now(timezone.utc) - timedelta(days=31)
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        test_db["users"].insert_one(
            make_user(8500, is_deactivated=True, deactivatedAt=old))
        test_db["users"].insert_one(
            make_user(8501, is_deactivated=True, deactivatedAt=recent))
        test_db["users"].insert_one(make_user(8502))

        await main._run_retention_cleanup()

        remaining = {d["id"] for d in test_db["users"].find({}, {"id": 1})}
        assert 8500 not in remaining
        assert {8501, 8502} <= remaining
