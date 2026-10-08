"""P3FT.10 — housing intent fields, hard filters and the move-in soft penalty.

Two layers are covered:

  * validation of the optional profile fields on register / POST /users /
    PUT /users/{id}
  * their effect on GET /users/{user_id}/top-matches — housingType and budget
    are hard filters, a move-in mismatch is a 0.7 multiplier, and the list is
    re-sorted afterwards.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.recommendationService import (
    MOVE_IN_MISMATCH_PENALTY,
    budget_compatible,
    housing_compatible,
    housing_score_multiplier,
    move_in_penalty,
)
from tests.helpers import auth_header, make_user, prefs

client = TestClient(app)
BASE = "/api"


def _register_body(tag: str, **extra) -> dict:
    body = {
        "email": f"housing_{tag}@auburn.edu",
        "password": "TestPass123!",
        "username": f"housing{tag}",
        "gender": "male",
    }
    body.update(prefs())
    body.update(extra)
    return body


def _seed_recommendations(test_db, user_id: int, entries: list) -> None:
    test_db["recommendations"].insert_one({
        "userId": user_id,
        "matches": [
            {"user_id": uid, "compatibilityScore": score} for uid, score in entries
        ],
    })


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------

class TestHousingFieldValidation:

    @pytest.mark.parametrize("housing_type", ["on-campus", "off-campus", "either"])
    def test_register_accepts_each_housing_type(self, housing_type):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(housing_type.replace("-", ""),
                                            housingType=housing_type))
        assert r.status_code == 201, r.text
        assert r.json()["user"].get("housingType", housing_type) == housing_type

    def test_register_rejects_unknown_housing_type(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("bad", housingType="off-planet"))
        assert r.status_code == 422

    @pytest.mark.parametrize("lease_term", ["fall", "spring", "summer", "full-year"])
    def test_register_accepts_each_lease_term(self, lease_term):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(lease_term.replace("-", ""), leaseTerm=lease_term))
        assert r.status_code == 201, r.text

    def test_register_rejects_unknown_lease_term(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("lease", leaseTerm="decade"))
        assert r.status_code == 422

    @pytest.mark.parametrize("season", ["Spring", "Summer", "Fall"])
    def test_register_accepts_each_move_in_season(self, season):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(season, moveInSeason=season))
        assert r.status_code == 201, r.text

    def test_move_in_season_is_case_sensitive(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("lower", moveInSeason="fall"))
        assert r.status_code == 422

    @pytest.mark.parametrize("year,expected", [
        (2024, 422), (2025, 201), (2035, 201), (2036, 422),
    ])
    def test_move_in_year_bounds(self, year, expected):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(f"y{year}", moveInYear=year))
        assert r.status_code == expected, r.text

    @pytest.mark.parametrize("budget,expected", [
        (-1, 422), (0, 201), (5000, 201), (5001, 422),
    ])
    def test_budget_bounds(self, budget, expected):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(f"b{budget}", budgetMin=budget, budgetMax=5000))
        assert r.status_code == expected, r.text

    def test_budget_min_greater_than_max_is_422(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("inverted", budgetMin=1200, budgetMax=800))
        assert r.status_code == 422

    def test_budget_min_equal_to_max_is_allowed(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("equal", budgetMin=900, budgetMax=900))
        assert r.status_code == 201, r.text

    def test_preferred_location_over_60_chars_is_422(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("long", preferredLocation="x" * 61))
        assert r.status_code == 422

    def test_preferred_location_html_is_stripped(self, test_db):
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body("html", preferredLocation="<script>alert(1)</script>Toomer"),
        )
        assert r.status_code == 201, r.text
        stored = test_db["users"].find_one({"id": r.json()["user"]["id"]})
        assert stored["preferredLocation"] == "Toomer"
        assert "<script>" not in stored["preferredLocation"]

    def test_housing_fields_are_optional(self, test_db):
        r = client.post(f"{BASE}/auth/register", json=_register_body("bare"))
        assert r.status_code == 201, r.text
        stored = test_db["users"].find_one({"id": r.json()["user"]["id"]})
        assert stored.get("housingType") is None
        assert stored.get("budgetMin") is None


class TestHousingFieldsOnUpdate:

    def _seed(self, test_db, user_id=901):
        test_db["users"].insert_one(make_user(user_id))
        return user_id, auth_header(user_id)

    def _update_body(self, **extra):
        body = {"username": "updated1", "gender": "male"}
        body.update(prefs())
        body.update(extra)
        return body

    def test_put_persists_housing_fields(self, test_db):
        uid, hdr = self._seed(test_db)
        r = client.put(
            f"{BASE}/users/{uid}",
            json=self._update_body(
                housingType="off-campus", preferredLocation="South College",
                budgetMin=600, budgetMax=1100, leaseTerm="full-year",
                moveInSeason="Fall", moveInYear=2026,
            ),
            headers=hdr,
        )
        assert r.status_code == 200, r.text
        stored = test_db["users"].find_one({"id": uid})
        assert stored["housingType"] == "off-campus"
        assert stored["preferredLocation"] == "South College"
        assert stored["budgetMin"] == 600
        assert stored["budgetMax"] == 1100
        assert stored["leaseTerm"] == "full-year"
        assert stored["moveInSeason"] == "Fall"
        assert stored["moveInYear"] == 2026

    def test_put_rejects_inverted_budget(self, test_db):
        uid, hdr = self._seed(test_db, 902)
        r = client.put(f"{BASE}/users/{uid}",
                       json=self._update_body(budgetMin=2000, budgetMax=100),
                       headers=hdr)
        assert r.status_code == 422

    def test_put_strips_html_from_preferred_location(self, test_db):
        uid, hdr = self._seed(test_db, 903)
        r = client.put(f"{BASE}/users/{uid}",
                       json=self._update_body(preferredLocation="<b>Magnolia</b>"),
                       headers=hdr)
        assert r.status_code == 200, r.text
        assert test_db["users"].find_one({"id": uid})["preferredLocation"] == "Magnolia"


# ---------------------------------------------------------------------------
# Pure filter helpers
# ---------------------------------------------------------------------------

class TestHousingCompatible:

    @pytest.mark.parametrize("a,b,expected", [
        ("on-campus", "on-campus", True),
        ("off-campus", "off-campus", True),
        ("on-campus", "off-campus", False),
        ("off-campus", "on-campus", False),
        ("either", "on-campus", True),
        ("either", "off-campus", True),
        ("on-campus", "either", True),
        ("either", "either", True),
    ])
    def test_pairs(self, a, b, expected):
        assert housing_compatible({"housingType": a}, {"housingType": b}) is expected

    def test_unset_is_always_compatible(self):
        assert housing_compatible({}, {"housingType": "on-campus"}) is True
        assert housing_compatible({"housingType": "off-campus"}, {}) is True
        assert housing_compatible({}, {}) is True


class TestBudgetCompatible:

    def test_overlapping_ranges_match(self):
        assert budget_compatible({"budgetMin": 500, "budgetMax": 900},
                                 {"budgetMin": 850, "budgetMax": 1200}) is True

    def test_touching_ranges_match(self):
        assert budget_compatible({"budgetMin": 500, "budgetMax": 900},
                                 {"budgetMin": 900, "budgetMax": 1200}) is True

    def test_disjoint_ranges_do_not_match(self):
        assert budget_compatible({"budgetMin": 300, "budgetMax": 500},
                                 {"budgetMin": 900, "budgetMax": 1200}) is False

    def test_only_min_set_defaults_max_to_ceiling(self):
        # budgetMin=4000 becomes [4000, 5000], which overlaps [4500, 4800]
        assert budget_compatible({"budgetMin": 4000},
                                 {"budgetMin": 4500, "budgetMax": 4800}) is True
        # ...and does not overlap [100, 300]
        assert budget_compatible({"budgetMin": 4000},
                                 {"budgetMin": 100, "budgetMax": 300}) is False

    def test_only_max_set_defaults_min_to_floor(self):
        # budgetMax=400 becomes [0, 400]
        assert budget_compatible({"budgetMax": 400},
                                 {"budgetMin": 100, "budgetMax": 300}) is True
        assert budget_compatible({"budgetMax": 400},
                                 {"budgetMin": 900, "budgetMax": 1200}) is False

    def test_no_bounds_at_all_is_exempt(self):
        assert budget_compatible({}, {"budgetMin": 900, "budgetMax": 1200}) is True
        assert budget_compatible({"budgetMin": 900, "budgetMax": 1200}, {}) is True


class TestMoveInPenalty:

    def test_same_semester_is_no_penalty(self):
        a = {"moveInSeason": "Fall", "moveInYear": 2026}
        assert move_in_penalty(a, dict(a)) == 1.0

    def test_different_season_same_year_is_penalized(self):
        assert move_in_penalty(
            {"moveInSeason": "Fall", "moveInYear": 2026},
            {"moveInSeason": "Spring", "moveInYear": 2026},
        ) == MOVE_IN_MISMATCH_PENALTY

    def test_same_season_different_year_is_penalized(self):
        assert move_in_penalty(
            {"moveInSeason": "Fall", "moveInYear": 2026},
            {"moveInSeason": "Fall", "moveInYear": 2027},
        ) == MOVE_IN_MISMATCH_PENALTY

    def test_penalty_value_is_zero_point_seven(self):
        assert MOVE_IN_MISMATCH_PENALTY == 0.7

    @pytest.mark.parametrize("partial", [
        {"moveInSeason": "Fall"},
        {"moveInYear": 2026},
        {},
    ])
    def test_penalty_needs_both_fields_on_both_users(self, partial):
        full = {"moveInSeason": "Spring", "moveInYear": 2027}
        assert move_in_penalty(full, partial) == 1.0
        assert move_in_penalty(partial, full) == 1.0


class TestHousingScoreMultiplier:

    def test_hard_filter_returns_none(self):
        assert housing_score_multiplier(
            {"housingType": "on-campus"}, {"housingType": "off-campus"}) is None
        assert housing_score_multiplier(
            {"budgetMin": 300, "budgetMax": 400},
            {"budgetMin": 900, "budgetMax": 1200}) is None

    def test_compatible_with_matching_move_in_is_one(self):
        viewer = {"housingType": "either", "moveInSeason": "Fall", "moveInYear": 2026}
        assert housing_score_multiplier(viewer, dict(viewer)) == 1.0

    def test_compatible_with_mismatched_move_in_is_penalty(self):
        viewer = {"housingType": "either", "moveInSeason": "Fall", "moveInYear": 2026}
        candidate = {"housingType": "either", "moveInSeason": "Spring", "moveInYear": 2026}
        assert housing_score_multiplier(viewer, candidate) == MOVE_IN_MISMATCH_PENALTY


# ---------------------------------------------------------------------------
# top-matches integration
# ---------------------------------------------------------------------------

class TestTopMatchesHousingFilters:

    def test_response_shape_is_unchanged(self, test_db):
        test_db["users"].insert_many([make_user(1001), make_user(1002)])
        _seed_recommendations(test_db, 1001, [(1002, 0.9)])
        r = client.get(f"{BASE}/users/1001/top-matches", headers=auth_header(1001))
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body.keys()) == {"userId", "matches"}
        assert body["userId"] == 1001
        assert set(body["matches"][0].keys()) == {"user_id", "compatibilityScore"}

    def test_incompatible_housing_type_is_hard_filtered(self, test_db):
        test_db["users"].insert_many([
            make_user(1010, housingType="on-campus"),
            make_user(1011, housingType="off-campus"),
            make_user(1012, housingType="on-campus"),
        ])
        _seed_recommendations(test_db, 1010, [(1011, 0.95), (1012, 0.5)])
        r = client.get(f"{BASE}/users/1010/top-matches", headers=auth_header(1010))
        assert r.status_code == 200, r.text
        ids = [m["user_id"] for m in r.json()["matches"]]
        assert 1011 not in ids
        assert ids == [1012]

    def test_either_matches_both_sides(self, test_db):
        test_db["users"].insert_many([
            make_user(1020, housingType="either"),
            make_user(1021, housingType="on-campus"),
            make_user(1022, housingType="off-campus"),
        ])
        _seed_recommendations(test_db, 1020, [(1021, 0.8), (1022, 0.7)])
        r = client.get(f"{BASE}/users/1020/top-matches", headers=auth_header(1020))
        ids = {m["user_id"] for m in r.json()["matches"]}
        assert ids == {1021, 1022}

    def test_unset_housing_type_is_not_filtered(self, test_db):
        test_db["users"].insert_many([
            make_user(1030),  # no housingType
            make_user(1031, housingType="on-campus"),
        ])
        _seed_recommendations(test_db, 1030, [(1031, 0.8)])
        r = client.get(f"{BASE}/users/1030/top-matches", headers=auth_header(1030))
        assert [m["user_id"] for m in r.json()["matches"]] == [1031]

    def test_non_overlapping_budgets_are_hard_filtered(self, test_db):
        test_db["users"].insert_many([
            make_user(1040, budgetMin=300, budgetMax=500),
            make_user(1041, budgetMin=900, budgetMax=1200),
            make_user(1042, budgetMin=450, budgetMax=700),
        ])
        _seed_recommendations(test_db, 1040, [(1041, 0.99), (1042, 0.4)])
        r = client.get(f"{BASE}/users/1040/top-matches", headers=auth_header(1040))
        assert [m["user_id"] for m in r.json()["matches"]] == [1042]

    def test_one_bound_user_gets_the_other_defaulted(self, test_db):
        # viewer has only budgetMax=400 -> [0, 400]; 1051 at [900,1200] cannot overlap
        test_db["users"].insert_many([
            make_user(1050, budgetMax=400),
            make_user(1051, budgetMin=900, budgetMax=1200),
            make_user(1052, budgetMin=100, budgetMax=350),
        ])
        _seed_recommendations(test_db, 1050, [(1051, 0.99), (1052, 0.4)])
        r = client.get(f"{BASE}/users/1050/top-matches", headers=auth_header(1050))
        assert [m["user_id"] for m in r.json()["matches"]] == [1052]

    def test_user_with_no_budget_is_exempt_from_the_filter(self, test_db):
        test_db["users"].insert_many([
            make_user(1060),  # no budget at all
            make_user(1061, budgetMin=4500, budgetMax=5000),
        ])
        _seed_recommendations(test_db, 1060, [(1061, 0.8)])
        r = client.get(f"{BASE}/users/1060/top-matches", headers=auth_header(1060))
        assert [m["user_id"] for m in r.json()["matches"]] == [1061]

    def test_move_in_mismatch_multiplies_score_by_zero_point_seven(self, test_db):
        test_db["users"].insert_many([
            make_user(1070, moveInSeason="Fall", moveInYear=2026),
            make_user(1071, moveInSeason="Spring", moveInYear=2027),
        ])
        _seed_recommendations(test_db, 1070, [(1071, 0.8)])
        r = client.get(f"{BASE}/users/1070/top-matches", headers=auth_header(1070))
        match = r.json()["matches"][0]
        assert match["user_id"] == 1071
        assert match["compatibilityScore"] == pytest.approx(0.8 * 0.7)

    def test_matching_move_in_leaves_score_untouched(self, test_db):
        test_db["users"].insert_many([
            make_user(1080, moveInSeason="Fall", moveInYear=2026),
            make_user(1081, moveInSeason="Fall", moveInYear=2026),
        ])
        _seed_recommendations(test_db, 1080, [(1081, 0.8)])
        r = client.get(f"{BASE}/users/1080/top-matches", headers=auth_header(1080))
        assert r.json()["matches"][0]["compatibilityScore"] == pytest.approx(0.8)

    def test_partial_move_in_data_is_not_penalized(self, test_db):
        test_db["users"].insert_many([
            make_user(1090, moveInSeason="Fall", moveInYear=2026),
            make_user(1091, moveInSeason="Spring"),  # no year -> penalty not applied
        ])
        _seed_recommendations(test_db, 1090, [(1091, 0.8)])
        r = client.get(f"{BASE}/users/1090/top-matches", headers=auth_header(1090))
        assert r.json()["matches"][0]["compatibilityScore"] == pytest.approx(0.8)

    def test_list_is_resorted_after_the_penalty(self, test_db):
        # 1101 starts ahead of 1102 but is penalized below it.
        test_db["users"].insert_many([
            make_user(1100, moveInSeason="Fall", moveInYear=2026),
            make_user(1101, moveInSeason="Spring", moveInYear=2026),   # 0.90 * 0.7 = 0.63
            make_user(1102, moveInSeason="Fall", moveInYear=2026),     # 0.70 * 1.0 = 0.70
        ])
        _seed_recommendations(test_db, 1100, [(1101, 0.90), (1102, 0.70)])
        r = client.get(f"{BASE}/users/1100/top-matches", headers=auth_header(1100))
        matches = r.json()["matches"]
        assert [m["user_id"] for m in matches] == [1102, 1101]
        scores = [m["compatibilityScore"] for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_roommate_found_users_are_excluded(self, test_db):
        test_db["users"].insert_many([
            make_user(1110),
            make_user(1111, roommateFound=True),
            make_user(1112),
        ])
        _seed_recommendations(test_db, 1110, [(1111, 0.95), (1112, 0.4)])
        r = client.get(f"{BASE}/users/1110/top-matches", headers=auth_header(1110))
        assert [m["user_id"] for m in r.json()["matches"]] == [1112]

    def test_paused_and_deactivated_users_still_excluded(self, test_db):
        test_db["users"].insert_many([
            make_user(1120),
            make_user(1121, is_paused=True),
            make_user(1122, is_deactivated=True),
            make_user(1123),
        ])
        _seed_recommendations(test_db, 1120, [(1121, 0.9), (1122, 0.8), (1123, 0.1)])
        r = client.get(f"{BASE}/users/1120/top-matches", headers=auth_header(1120))
        assert [m["user_id"] for m in r.json()["matches"]] == [1123]

    def test_hard_filters_and_penalty_combine(self, test_db):
        test_db["users"].insert_many([
            make_user(1130, housingType="off-campus", budgetMin=500, budgetMax=900,
                      moveInSeason="Fall", moveInYear=2026),
            # filtered: wrong housing type
            make_user(1131, housingType="on-campus"),
            # filtered: budget does not overlap
            make_user(1132, housingType="off-campus", budgetMin=1500, budgetMax=2000),
            # kept, penalized
            make_user(1133, housingType="either", budgetMin=800, budgetMax=1000,
                      moveInSeason="Spring", moveInYear=2026),
        ])
        _seed_recommendations(test_db, 1130, [(1131, 0.99), (1132, 0.98), (1133, 0.6)])
        r = client.get(f"{BASE}/users/1130/top-matches", headers=auth_header(1130))
        matches = r.json()["matches"]
        assert [m["user_id"] for m in matches] == [1133]
        assert matches[0]["compatibilityScore"] == pytest.approx(0.6 * 0.7)
