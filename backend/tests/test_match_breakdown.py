"""P3FT.11 — GET /users/{user_id}/match-breakdown/{other_id}.

The privacy guarantee is the point of this endpoint: it explains a
compatibility score category by category without ever returning the other
user's raw preference values. `theirValue` must not appear anywhere in the
payload -- several tests assert that directly.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.matchScore import matchScore
from tests.helpers import auth_header, make_user, pref, prefs

client = TestClient(app)
BASE = "/api"

CATEGORY_KEYS = [
    "sleepScheduleWeekdays", "sleepScheduleWeekends", "cleanliness",
    "noiseTolerance", "guests", "personality", "smoking", "sharedSpace",
    "communication",
]


def _breakdown(user_id: int, other_id: int, as_user: int = None):
    return client.get(
        f"{BASE}/users/{user_id}/match-breakdown/{other_id}",
        headers=auth_header(as_user if as_user is not None else user_id),
    )


class TestBreakdownShape:

    def test_returns_200_with_the_documented_keys(self, test_db):
        test_db["users"].insert_many([make_user(2001), make_user(2002)])
        r = _breakdown(2001, 2002)
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body.keys()) == {"compatibilityScore", "categories"}

    def test_returns_all_nine_categories_from_category_range(self, test_db):
        test_db["users"].insert_many([make_user(2010), make_user(2011)])
        body = _breakdown(2010, 2011).json()
        assert len(body["categories"]) == 9
        assert [c["key"] for c in body["categories"]] == list(matchScore().categoryRange.keys())
        assert [c["key"] for c in body["categories"]] == CATEGORY_KEYS

    def test_every_category_row_has_the_documented_keys(self, test_db):
        test_db["users"].insert_many([make_user(2020), make_user(2021)])
        body = _breakdown(2020, 2021).json()
        expected = {"key", "label", "yourValue", "difference", "score",
                    "isDealBreaker", "dealBreakerTriggered"}
        for row in body["categories"]:
            assert set(row.keys()) == expected

    def test_labels_are_human_readable(self, test_db):
        test_db["users"].insert_many([make_user(2030), make_user(2031)])
        body = _breakdown(2030, 2031).json()
        labels = {c["key"]: c["label"] for c in body["categories"]}
        assert labels["cleanliness"] == "Cleanliness"
        assert labels["sleepScheduleWeekdays"] == "Sleep Schedule (Weekdays)"
        assert all(c["label"] for c in body["categories"])


class TestPrivacyGuarantee:
    """The other user's raw values must never be returned."""

    def test_their_value_key_is_absent_from_every_row(self, test_db):
        test_db["users"].insert_many([
            make_user(2100, **prefs(3.0)),
            make_user(2101, **prefs(9.0)),
        ])
        body = _breakdown(2100, 2101).json()
        for row in body["categories"]:
            assert "theirValue" not in row

    def test_their_value_appears_nowhere_in_the_serialized_payload(self, test_db):
        test_db["users"].insert_many([
            make_user(2110, **prefs(3.0)),
            make_user(2111, **prefs(9.0)),
        ])
        raw = _breakdown(2110, 2111).text
        assert "theirValue" not in raw
        assert "theirvalue" not in raw.lower()

    def test_your_value_is_always_the_callers_own_value(self, test_db):
        test_db["users"].insert_many([
            make_user(2120, **prefs(4.0, cleanlinessScore=7.0)),
            make_user(2121, **prefs(1.0, cleanlinessScore=2.0)),
        ])
        rows = {c["key"]: c for c in _breakdown(2120, 2121).json()["categories"]}
        assert rows["cleanliness"]["yourValue"] == 7.0
        assert rows["noiseTolerance"]["yourValue"] == 4.0

    def test_no_other_profile_field_leaks(self, test_db):
        test_db["users"].insert_many([
            make_user(2130),
            make_user(2131, email="secret@auburn.edu", bio="my secret bio",
                      hashed_password="hash-should-never-appear"),
        ])
        raw = _breakdown(2130, 2131).text
        for leaked in ("secret@auburn.edu", "my secret bio",
                       "hash-should-never-appear", "user2131"):
            assert leaked not in raw


class TestDifferenceBuckets:

    @pytest.mark.parametrize("mine,theirs,expected", [
        # cleanliness range is 10, so normalized delta = |a-b| / 10
        (5.0, 5.0, "same"),        # 0.0   <= 0.05
        (5.0, 5.5, "same"),        # 0.05  <= 0.05 (boundary is inclusive)
        (5.0, 5.6, "close"),       # 0.06
        (5.0, 7.5, "close"),       # 0.25  <= 0.25 (boundary is inclusive)
        (5.0, 7.6, "different"),   # 0.26
        (1.0, 10.0, "different"),  # 0.9
    ])
    def test_cleanliness_buckets(self, test_db, mine, theirs, expected):
        test_db["users"].insert_many([
            make_user(2200, **prefs(5.0, cleanlinessScore=mine)),
            make_user(2201, **prefs(5.0, cleanlinessScore=theirs)),
        ])
        rows = {c["key"]: c for c in _breakdown(2200, 2201).json()["categories"]}
        assert rows["cleanliness"]["difference"] == expected

    def test_sleep_categories_normalize_over_a_24_hour_range(self, test_db):
        # A 2-hour gap on a 24 range is 0.083 -> "close", where the same raw gap
        # on a 10-point category would be 0.2, also "close"; 5 hours -> 0.208 close,
        # 7 hours -> 0.29 different.
        test_db["users"].insert_many([
            make_user(2210, **prefs(5.0, sleepScoreWD=pref(10.0), sleepScoreWE=pref(10.0))),
            make_user(2211, **prefs(5.0, sleepScoreWD=pref(12.0), sleepScoreWE=pref(17.0))),
        ])
        rows = {c["key"]: c for c in _breakdown(2210, 2211).json()["categories"]}
        assert rows["sleepScheduleWeekdays"]["difference"] == "close"
        assert rows["sleepScheduleWeekends"]["difference"] == "different"

    def test_bucket_is_symmetric(self, test_db):
        test_db["users"].insert_many([
            make_user(2220, **prefs(5.0, guestsScore=2.0)),
            make_user(2221, **prefs(5.0, guestsScore=9.0)),
        ])
        forward = {c["key"]: c for c in _breakdown(2220, 2221).json()["categories"]}
        backward = {c["key"]: c for c in _breakdown(2221, 2220).json()["categories"]}
        assert forward["guests"]["difference"] == backward["guests"]["difference"] == "different"

    def test_difference_is_only_ever_one_of_three_values(self, test_db):
        test_db["users"].insert_many([
            make_user(2230, **prefs(2.0)),
            make_user(2231, **prefs(8.0)),
        ])
        for row in _breakdown(2230, 2231).json()["categories"]:
            assert row["difference"] in {"same", "close", "different"}


class TestScoreConsistency:

    def test_mean_of_category_scores_equals_compatibility_score(self, test_db):
        test_db["users"].insert_many([
            make_user(2300, **prefs(4.0, cleanlinessScore=8.0, guestsScore=3.0)),
            make_user(2301, **prefs(6.0, cleanlinessScore=5.0, guestsScore=4.0)),
        ])
        body = _breakdown(2300, 2301).json()
        scores = [c["score"] for c in body["categories"]]
        assert len(scores) == 9
        assert sum(scores) / 9 == pytest.approx(body["compatibilityScore"], abs=1e-5)

    def test_identical_profiles_score_one(self, test_db):
        test_db["users"].insert_many([make_user(2310), make_user(2311)])
        body = _breakdown(2310, 2311).json()
        assert body["compatibilityScore"] == pytest.approx(1.0)
        assert all(c["score"] == pytest.approx(1.0) for c in body["categories"])
        assert all(c["difference"] == "same" for c in body["categories"])

    def test_scores_are_bounded_between_zero_and_one(self, test_db):
        test_db["users"].insert_many([
            make_user(2320, **prefs(0.0)),
            make_user(2321, **prefs(10.0, sleepScoreWD=pref(24.0), sleepScoreWE=pref(24.0))),
        ])
        body = _breakdown(2320, 2321).json()
        for row in body["categories"]:
            assert 0.0 <= row["score"] <= 1.0

    def test_breakdown_score_matches_the_scorer(self, test_db):
        from app.models import UserInDB
        a = make_user(2330, **prefs(3.0, personalityScore=9.0))
        b = make_user(2331, **prefs(7.0, personalityScore=2.0))
        test_db["users"].insert_many([dict(a), dict(b)])
        expected = matchScore().compatibilityScore(
            UserInDB(**a).toMatchDict(), UserInDB(**b).toMatchDict()
        )
        assert _breakdown(2330, 2331).json()["compatibilityScore"] == pytest.approx(expected)


class TestDealBreakers:

    def test_is_deal_breaker_reflects_either_side(self, test_db):
        test_db["users"].insert_many([
            make_user(2400, **prefs(5.0, guestsScore=pref(5.0, deal_breaker=True))),
            make_user(2401, **prefs(5.0)),
        ])
        rows = {c["key"]: c for c in _breakdown(2400, 2401).json()["categories"]}
        assert rows["guests"]["isDealBreaker"] is True
        assert rows["cleanliness"]["isDealBreaker"] is False

    def test_deal_breaker_flag_without_a_wide_enough_gap_does_not_trigger(self, test_db):
        # guests threshold is 10 * 1.0 = 10, so nothing short of a 10-point gap fires.
        test_db["users"].insert_many([
            make_user(2410, **prefs(5.0, guestsScore=pref(1.0, deal_breaker=True))),
            make_user(2411, **prefs(5.0, guestsScore=pref(9.0))),
        ])
        body = _breakdown(2410, 2411).json()
        rows = {c["key"]: c for c in body["categories"]}
        assert rows["guests"]["isDealBreaker"] is True
        assert rows["guests"]["dealBreakerTriggered"] is False
        assert body["compatibilityScore"] > 0

    def test_triggered_deal_breaker_zeroes_the_score_and_flags_its_row(self, test_db):
        # cleanliness threshold is 10 * 0.2 = 2, so a 7-point gap fires it.
        test_db["users"].insert_many([
            make_user(2420, **prefs(5.0, cleanlinessScore=pref(2.0, deal_breaker=True))),
            make_user(2421, **prefs(5.0, cleanlinessScore=pref(9.0))),
        ])
        body = _breakdown(2420, 2421).json()
        assert body["compatibilityScore"] == 0.0
        rows = {c["key"]: c for c in body["categories"]}
        assert rows["cleanliness"]["dealBreakerTriggered"] is True
        assert rows["cleanliness"]["isDealBreaker"] is True

    def test_only_the_offending_row_is_flagged(self, test_db):
        test_db["users"].insert_many([
            make_user(2430, **prefs(5.0, cleanlinessScore=pref(2.0, deal_breaker=True))),
            make_user(2431, **prefs(5.0, cleanlinessScore=pref(9.0))),
        ])
        rows = _breakdown(2430, 2431).json()["categories"]
        triggered = [r["key"] for r in rows if r["dealBreakerTriggered"]]
        assert triggered == ["cleanliness"]

    def test_mean_does_not_equal_score_when_a_deal_breaker_fires(self, test_db):
        """The documented mean==score identity holds only when nothing fires."""
        test_db["users"].insert_many([
            make_user(2440, **prefs(5.0, cleanlinessScore=pref(2.0, deal_breaker=True))),
            make_user(2441, **prefs(5.0, cleanlinessScore=pref(9.0))),
        ])
        body = _breakdown(2440, 2441).json()
        mean = sum(c["score"] for c in body["categories"]) / 9
        assert body["compatibilityScore"] == 0.0
        assert mean > 0.0  # the per-category scores are still reported


class TestBreakdownAccessControl:

    def test_403_when_user_id_is_not_the_caller(self, test_db):
        test_db["users"].insert_many([make_user(2500), make_user(2501), make_user(2502)])
        r = _breakdown(2501, 2502, as_user=2500)
        assert r.status_code == 403

    def test_401_without_a_token(self, test_db):
        test_db["users"].insert_many([make_user(2510), make_user(2511)])
        r = client.get(f"{BASE}/users/2510/match-breakdown/2511")
        assert r.status_code in (401, 403)

    def test_403_when_the_caller_blocked_the_other_user(self, test_db):
        test_db["users"].insert_many([make_user(2520), make_user(2521)])
        test_db["blocks"].insert_one({"blockerId": 2520, "blockedId": 2521})
        assert _breakdown(2520, 2521).status_code == 403

    def test_403_when_the_other_user_blocked_the_caller(self, test_db):
        test_db["users"].insert_many([make_user(2530), make_user(2531)])
        test_db["blocks"].insert_one({"blockerId": 2531, "blockedId": 2530})
        assert _breakdown(2530, 2531).status_code == 403

    def test_404_for_an_unknown_other_user(self, test_db):
        test_db["users"].insert_one(make_user(2540))
        assert _breakdown(2540, 999999).status_code == 404

    def test_404_for_a_soft_deleted_other_user(self, test_db):
        from datetime import datetime, timezone
        test_db["users"].insert_many([
            make_user(2550),
            make_user(2551, deletedAt=datetime.now(timezone.utc)),
        ])
        assert _breakdown(2550, 2551).status_code == 404

    def test_400_when_comparing_a_user_with_themselves(self, test_db):
        test_db["users"].insert_one(make_user(2560))
        r = _breakdown(2560, 2560)
        assert r.status_code == 400
        assert "themselves" in r.json()["detail"].lower()

    def test_400_when_the_other_profile_is_missing_preference_data(self, test_db):
        test_db["users"].insert_one(make_user(2570))
        legacy = make_user(2571)
        for field in ("sleepScoreWD", "cleanlinessScore"):
            legacy.pop(field)
        test_db["users"].insert_one(legacy)
        r = _breakdown(2570, 2571)
        assert r.status_code == 400
        assert "preference" in r.json()["detail"].lower()


class TestBreakdownRateLimit:

    def test_documented_limit_is_sixty_per_minute(self):
        """Guard the declared limit so a change to it is a deliberate edit."""
        from tests.helpers import declared_rate_limits
        assert declared_rate_limits(
            "app.routers.userRoutes.get_match_breakdown"
        ) == ["60 per 1 minute"]
