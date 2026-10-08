"""P3FT.16 — Discover filters on `GET /users/{user_id}/top-matches`.

Three things are covered, in ascending order of how much damage a regression
would do:

  1. Per-filter semantics and their 422 bounds.
  2. Response shape — `filteredOut` is OMITTED when no filter was supplied (so
     the unfiltered response is byte-identical to what shipped before this
     feature) and ALWAYS PRESENT when one was, including the value `0`.
  3. Gate order.  The documented order is

         exclusions (block / skip / pause / deactivate / roommate-found)
           -> P3FT.10 housing
             -> P3FT.16 filters
               -> sort

     A filter that can resurface a blocked or hidden user is a safety failure,
     not a cosmetic bug, so each of those five states gets an explicit test
     *with filters applied that the hidden candidate would otherwise satisfy*.

Bounds are asserted server-side on purpose.  The Discover sheet clamps these
client-side too, but the client is not the enforcement point: a stale
localStorage payload or a hand-written query string reaches the API directly.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ALLOWED_LIFESTYLE_TAGS, GRAD_YEAR_MAX, GRAD_YEAR_MIN
from tests.helpers import auth_header, make_user

client = TestClient(app)
BASE = "/api"

VIEWER = 7000

TAG_A, TAG_B, TAG_C = "Night Owl", "Fitness", "Gaming"


def _seed_viewer(test_db, viewer_id: int = VIEWER, **overrides):
    test_db["users"].insert_one(make_user(viewer_id, **overrides))


def _seed_candidate(test_db, user_id: int, **overrides):
    test_db["users"].insert_one(make_user(user_id, **overrides))


def _seed_recs(test_db, viewer_id: int, entries) -> None:
    """`entries` is [(candidate_id, stored_compatibility_score), ...]."""
    test_db["recommendations"].insert_one({
        "userId": viewer_id,
        "matches": [{"user_id": uid, "compatibilityScore": s} for uid, s in entries],
    })


def _get(viewer_id: int = VIEWER, query: str = ""):
    url = f"{BASE}/users/{viewer_id}/top-matches"
    if query:
        url = f"{url}?{query}"
    return client.get(url, headers=auth_header(viewer_id))


def _ids(resp) -> list:
    return [m["user_id"] for m in resp.json()["matches"]]


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:

    def test_no_filters_omits_filtered_out_entirely(self, test_db):
        """The unfiltered response must be byte-identical to the pre-sprint one."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get()
        assert r.status_code == 200, r.text
        assert set(r.json().keys()) == {"userId", "matches"}
        assert "filteredOut" not in r.json()

    def test_filters_supplied_always_include_filtered_out(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="major=Engineering")
        assert r.status_code == 200, r.text
        assert r.json()["filteredOut"] == 0

    def test_filtered_out_present_even_when_zero(self, test_db):
        """`0` is a value the UI needs, not an absence — it must not be dropped."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        body = _get(query="major=Engineering").json()
        assert "filteredOut" in body
        assert body["filteredOut"] == 0
        assert body["matches"]

    def test_filtering_everything_out_is_200_not_404(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="major=Nursing")
        assert r.status_code == 200, r.text
        assert r.json()["matches"] == []
        assert r.json()["filteredOut"] == 1

    def test_404_preserved_when_no_recommendations_document(self, test_db):
        _seed_viewer(test_db)
        assert _get().status_code == 404

    def test_404_preserved_even_with_filters_supplied(self, test_db):
        """404 must stay the "nothing computed yet" signal, filters or not."""
        _seed_viewer(test_db)
        assert _get(query="major=Nursing").status_code == 404

    def test_results_are_sorted_after_filtering(self, test_db):
        _seed_viewer(test_db)
        for uid in (7001, 7002, 7003):
            _seed_candidate(test_db, uid, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.3), (7002, 0.9), (7003, 0.6)])

        assert _ids(_get(query="major=Engineering")) == [7002, 7003, 7001]


# ---------------------------------------------------------------------------
# Unknown parameters
# ---------------------------------------------------------------------------

class TestUnknownParams:

    def test_unknown_param_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="notAFilter=1").status_code == 422

    def test_unknown_param_alongside_a_valid_one_is_still_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="major=Engineering&sortBy=score").status_code == 422

    def test_misspelled_filter_name_is_rejected_not_ignored(self, test_db):
        """`extra: "forbid"` exists so a typo fails loudly instead of silently
        returning an unfiltered feed the user believes is filtered."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="gradYearMinimum=2026").status_code == 422


# ---------------------------------------------------------------------------
# major
# ---------------------------------------------------------------------------

class TestMajorFilter:

    def test_matches_exact_major(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_candidate(test_db, 7002, major="Nursing")
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])

        r = _get(query="major=Engineering")
        assert _ids(r) == [7001]
        assert r.json()["filteredOut"] == 1

    def test_is_case_insensitive(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="major=eNgInEeRiNg")) == [7001]

    def test_repeatable_param_is_or_within_itself(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_candidate(test_db, 7002, major="Nursing")
        _seed_candidate(test_db, 7003, major="History")
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8), (7003, 0.7)])

        r = _get(query="major=Engineering&major=Nursing")
        assert sorted(_ids(r)) == [7001, 7002]
        assert r.json()["filteredOut"] == 1

    def test_comma_joined_value_is_not_split(self, test_db):
        """A comma-joined string is one literal major, not two — this is why the
        client must send repeatable params."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="major=Engineering,Nursing")) == []

    def test_candidate_with_no_major_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)  # no major
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="major=Engineering")
        assert _ids(r) == []
        assert r.json()["filteredOut"] == 1

    def test_candidate_with_null_major_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major=None)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="major=Engineering")) == []

    def test_twenty_majors_allowed(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="m0")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        query = "&".join(f"major=m{i}" for i in range(20))
        assert _get(query=query).status_code == 200

    def test_twenty_one_majors_is_422(self, test_db):
        """Client-side clamping is defence in depth; the server is the gate."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="m0")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        query = "&".join(f"major=m{i}" for i in range(21))
        assert _get(query=query).status_code == 422


# ---------------------------------------------------------------------------
# gradYearMin / gradYearMax
# ---------------------------------------------------------------------------

class TestGradYearFilter:

    def test_min_and_max_are_inclusive(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_candidate(test_db, 7002, graduationYear=2028)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])

        r = _get(query="gradYearMin=2026&gradYearMax=2028")
        assert sorted(_ids(r)) == [7001, 7002]

    def test_min_only_excludes_earlier_years(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2025)
        _seed_candidate(test_db, 7002, graduationYear=2027)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query="gradYearMin=2026")) == [7002]

    def test_max_only_excludes_later_years(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2025)
        _seed_candidate(test_db, 7002, graduationYear=2027)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query="gradYearMax=2026")) == [7001]

    def test_candidate_with_no_grad_year_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)  # no graduationYear
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="gradYearMin=2020")
        assert _ids(r) == []
        assert r.json()["filteredOut"] == 1

    def test_candidate_with_non_integer_grad_year_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear="2026")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="gradYearMin=2020")) == []

    @pytest.mark.parametrize("year,expected", [
        (GRAD_YEAR_MIN - 1, 422),
        (GRAD_YEAR_MIN, 200),
        (GRAD_YEAR_MAX, 200),
        (GRAD_YEAR_MAX + 1, 422),
    ])
    def test_grad_year_min_bounds(self, test_db, year, expected):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"gradYearMin={year}").status_code == expected

    @pytest.mark.parametrize("year,expected", [
        (GRAD_YEAR_MIN - 1, 422),
        (GRAD_YEAR_MIN, 200),
        (GRAD_YEAR_MAX, 200),
        (GRAD_YEAR_MAX + 1, 422),
    ])
    def test_grad_year_max_bounds(self, test_db, year, expected):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"gradYearMax={year}").status_code == expected

    def test_inverted_range_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="gradYearMin=2028&gradYearMax=2026").status_code == 422

    def test_equal_min_and_max_is_allowed(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="gradYearMin=2026&gradYearMax=2026")) == [7001]

    def test_non_numeric_grad_year_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="gradYearMin=soon").status_code == 422


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------

class TestTagsFilter:

    def test_single_tag_matches(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_candidate(test_db, 7002, lifestyleTags=[TAG_B])
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query=f"tags={TAG_A}")) == [7001]

    def test_tags_are_or_not_and(self, test_db):
        """A candidate needs only ONE of the requested tags."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_candidate(test_db, 7002, lifestyleTags=[TAG_B])
        _seed_candidate(test_db, 7003, lifestyleTags=[TAG_C])
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8), (7003, 0.7)])

        r = _get(query=f"tags={TAG_A}&tags={TAG_B}")
        assert sorted(_ids(r)) == [7001, 7002]
        assert r.json()["filteredOut"] == 1

    def test_candidate_with_no_tags_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[])
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query=f"tags={TAG_A}")) == []

    def test_unknown_tag_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="tags=Skydiving").status_code == 422

    def test_one_bad_tag_rejects_the_whole_request(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"tags={TAG_A}&tags=Skydiving").status_code == 422

    def test_ten_tags_allowed(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        tags = sorted(ALLOWED_LIFESTYLE_TAGS)[:10]
        query = "&".join(f"tags={t}" for t in tags)
        assert _get(query=query).status_code == 200

    def test_eleven_tags_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, lifestyleTags=[TAG_A])
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        tags = sorted(ALLOWED_LIFESTYLE_TAGS)[:11]
        query = "&".join(f"tags={t}" for t in tags)
        assert _get(query=query).status_code == 422


# ---------------------------------------------------------------------------
# religion
# ---------------------------------------------------------------------------

class TestReligionFilter:

    def test_exact_match(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, religionTag="Christian")
        _seed_candidate(test_db, 7002, religionTag="Jewish")
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query="religion=Christian")) == [7001]

    def test_is_case_insensitive(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, religionTag="Christian")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="religion=cHrIsTiAn")) == [7001]

    def test_candidate_with_no_religion_is_excluded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="religion=Christian")) == []

    def test_partial_match_does_not_count(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, religionTag="Christian")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="religion=Christ")) == []

    def test_sixty_chars_allowed(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, religionTag="x" * 60)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"religion={'x' * 60}").status_code == 200

    def test_sixty_one_chars_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, religionTag="x")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"religion={'x' * 61}").status_code == 422


# ---------------------------------------------------------------------------
# housingType
# ---------------------------------------------------------------------------

class TestHousingTypeFilter:

    def test_matches_same_housing_type(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, housingType="on-campus")
        _seed_candidate(test_db, 7002, housingType="off-campus")
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query="housingType=on-campus")) == [7001]

    @pytest.mark.parametrize("requested", ["on-campus", "off-campus", "either"])
    def test_candidate_either_satisfies_any_request(self, test_db, requested):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, housingType="either")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query=f"housingType={requested}")) == [7001]

    def test_candidate_with_unset_housing_type_is_excluded(self, test_db):
        """Unlike the P3FT.10 compatibility gate, an unset housingType does NOT
        satisfy an explicit discover filter."""
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="housingType=on-campus")
        assert _ids(r) == []
        assert r.json()["filteredOut"] == 1

    def test_unknown_housing_type_is_422(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, housingType="either")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query="housingType=off-planet").status_code == 422


# ---------------------------------------------------------------------------
# budgetMax
# ---------------------------------------------------------------------------

class TestBudgetMaxFilter:

    def test_candidate_floor_at_or_below_ceiling_passes(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, budgetMin=800)
        _seed_candidate(test_db, 7002, budgetMin=1500)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8)])
        assert _ids(_get(query="budgetMax=1000")) == [7001]

    def test_boundary_is_inclusive(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, budgetMin=1000)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="budgetMax=1000")) == [7001]

    def test_candidate_with_no_budget_min_defaults_to_zero_and_passes(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _ids(_get(query="budgetMax=100")) == [7001]

    @pytest.mark.parametrize("budget,expected", [
        (-1, 422), (0, 200), (5000, 200), (5001, 422),
    ])
    def test_budget_max_bounds(self, test_db, budget, expected):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, budgetMin=0)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"budgetMax={budget}").status_code == expected


# ---------------------------------------------------------------------------
# minScore
# ---------------------------------------------------------------------------

class TestMinScoreFilter:

    def test_filters_on_percentage_scale(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_candidate(test_db, 7002)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.4)])

        r = _get(query="minScore=50")
        assert _ids(r) == [7001]
        assert r.json()["filteredOut"] == 1

    def test_boundary_is_inclusive(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.5)])
        assert _ids(_get(query="minScore=50")) == [7001]

    def test_compared_against_the_post_housing_multiplier_score(self, test_db):
        """The 0.7 move-in penalty is applied BEFORE minScore.

        Stored score 0.9 reads as 90%, but the move-in mismatch drops it to 63%,
        so a 70% floor must exclude the candidate.  If minScore were compared
        against the raw stored score this candidate would survive.
        """
        _seed_viewer(test_db, moveInSeason="Fall", moveInYear=2026)
        _seed_candidate(test_db, 7001, moveInSeason="Spring", moveInYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="minScore=70")
        assert _ids(r) == [], "minScore was compared against the pre-penalty score"
        assert r.json()["filteredOut"] == 1

    def test_penalised_candidate_survives_a_floor_below_the_penalised_score(self, test_db):
        _seed_viewer(test_db, moveInSeason="Fall", moveInYear=2026)
        _seed_candidate(test_db, 7001, moveInSeason="Spring", moveInYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        r = _get(query="minScore=60")
        assert _ids(r) == [7001]
        assert r.json()["matches"][0]["compatibilityScore"] == pytest.approx(0.63)

    @pytest.mark.parametrize("score,expected", [
        (-1, 422), (0, 200), (100, 200), (101, 422),
    ])
    def test_min_score_bounds(self, test_db, score, expected):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001)
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])
        assert _get(query=f"minScore={score}").status_code == expected


# ---------------------------------------------------------------------------
# Filter composition
# ---------------------------------------------------------------------------

class TestFilterComposition:

    def test_different_filters_are_anded(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(test_db, 7001, major="Engineering", graduationYear=2026)
        _seed_candidate(test_db, 7002, major="Engineering", graduationYear=2030)
        _seed_candidate(test_db, 7003, major="Nursing", graduationYear=2026)
        _seed_recs(test_db, VIEWER, [(7001, 0.9), (7002, 0.8), (7003, 0.7)])

        r = _get(query="major=Engineering&gradYearMax=2027")
        assert _ids(r) == [7001]
        assert r.json()["filteredOut"] == 2

    def test_every_filter_at_once(self, test_db):
        _seed_viewer(test_db)
        _seed_candidate(
            test_db, 7001,
            major="Engineering", graduationYear=2026, lifestyleTags=[TAG_A],
            religionTag="Christian", housingType="either", budgetMin=500,
        )
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        query = (
            "major=Engineering&gradYearMin=2025&gradYearMax=2027"
            f"&tags={TAG_A}&religion=Christian&housingType=on-campus"
            "&budgetMax=900&minScore=50"
        )
        r = _get(query=query)
        assert r.status_code == 200, r.text
        assert _ids(r) == [7001]
        assert r.json()["filteredOut"] == 0


# ---------------------------------------------------------------------------
# GATE ORDER — the safety-critical block.
#
# Filters run LAST.  None of them may resurface a candidate that an earlier gate
# removed.  Each test below hides a candidate one way and then applies a filter
# that the hidden candidate satisfies perfectly, so a filter evaluated before
# the exclusions would put them straight back on the page.
# ---------------------------------------------------------------------------

class TestFiltersNeverResurfaceExcludedUsers:

    HIDDEN = 7500
    VISIBLE = 7501

    def _seed_pair(self, test_db, hidden_overrides=None):
        """A hidden candidate and a visible one, both satisfying every filter."""
        shared = dict(
            major="Engineering", graduationYear=2026, lifestyleTags=[TAG_A],
            religionTag="Christian", housingType="either", budgetMin=100,
        )
        _seed_viewer(test_db)
        _seed_candidate(test_db, self.HIDDEN, **{**shared, **(hidden_overrides or {})})
        _seed_candidate(test_db, self.VISIBLE, **shared)
        _seed_recs(test_db, VIEWER, [(self.HIDDEN, 0.99), (self.VISIBLE, 0.5)])

    #: Filters the hidden candidate satisfies on every axis, including the
    #: highest score in the feed — nothing here can legitimately exclude them.
    FULL_QUERY = (
        "major=Engineering&gradYearMin=2000&gradYearMax=2100"
        f"&tags={TAG_A}&religion=Christian&housingType=on-campus"
        "&budgetMax=5000&minScore=0"
    )

    def test_blocked_user_stays_hidden_under_filters(self, test_db):
        self._seed_pair(test_db)
        test_db["blocks"].insert_one({"blockerId": VIEWER, "blockedId": self.HIDDEN})

        r = _get(query=self.FULL_QUERY)
        assert r.status_code == 200, r.text
        assert self.HIDDEN not in _ids(r), "a discover filter resurfaced a blocked user"
        assert _ids(r) == [self.VISIBLE]

    def test_user_who_blocked_the_viewer_stays_hidden_under_filters(self, test_db):
        """Blocking is bidirectional — the reverse direction must hold too."""
        self._seed_pair(test_db)
        test_db["blocks"].insert_one({"blockerId": self.HIDDEN, "blockedId": VIEWER})

        r = _get(query=self.FULL_QUERY)
        assert self.HIDDEN not in _ids(r)

    def test_skipped_user_stays_hidden_under_filters(self, test_db):
        self._seed_pair(test_db)
        test_db["swipes"].insert_one(
            {"user_id": VIEWER, "skipped_user_id": self.HIDDEN}
        )

        r = _get(query=self.FULL_QUERY)
        assert self.HIDDEN not in _ids(r), "a discover filter resurfaced a skipped user"
        assert _ids(r) == [self.VISIBLE]

    def test_paused_user_stays_hidden_under_filters(self, test_db):
        self._seed_pair(test_db, {"is_paused": True})

        r = _get(query=self.FULL_QUERY)
        assert self.HIDDEN not in _ids(r), "a discover filter resurfaced a paused user"
        assert _ids(r) == [self.VISIBLE]

    def test_deactivated_user_stays_hidden_under_filters(self, test_db):
        self._seed_pair(test_db, {"is_deactivated": True})

        r = _get(query=self.FULL_QUERY)
        assert self.HIDDEN not in _ids(r), \
            "a discover filter resurfaced a deactivated user"
        assert _ids(r) == [self.VISIBLE]

    def test_roommate_found_user_stays_hidden_under_filters(self, test_db):
        self._seed_pair(test_db, {"roommateFound": True})

        r = _get(query=self.FULL_QUERY)
        assert self.HIDDEN not in _ids(r), \
            "a discover filter resurfaced a roommate-found user"
        assert _ids(r) == [self.VISIBLE]

    @pytest.mark.parametrize("hide", [
        "block", "skip", "pause", "deactivate", "roommate_found",
    ])
    def test_excluded_users_are_not_counted_as_filtered_out(self, test_db, hide):
        """They were removed by an earlier gate, so they never reach the filter
        stage — counting them would tell the UI "widen your filters" about a
        user no filter change can ever reveal."""
        overrides = {
            "pause": {"is_paused": True},
            "deactivate": {"is_deactivated": True},
            "roommate_found": {"roommateFound": True},
        }.get(hide)
        self._seed_pair(test_db, overrides)
        if hide == "block":
            test_db["blocks"].insert_one({"blockerId": VIEWER, "blockedId": self.HIDDEN})
        elif hide == "skip":
            test_db["swipes"].insert_one(
                {"user_id": VIEWER, "skipped_user_id": self.HIDDEN}
            )

        r = _get(query=self.FULL_QUERY)
        assert r.json()["filteredOut"] == 0

    def test_housing_gate_still_runs_before_filters(self, test_db):
        """P3FT.10's hard filter sits between the exclusions and the user's own
        filters; a permissive user filter must not undo it."""
        _seed_viewer(test_db, housingType="on-campus")
        _seed_candidate(test_db, 7001, housingType="off-campus", major="Engineering")
        _seed_recs(test_db, VIEWER, [(7001, 0.9)])

        # The user asks for off-campus, which the candidate is — but the viewer's
        # own on-campus intent already ruled them out.
        r = _get(query="housingType=off-campus&major=Engineering")
        assert _ids(r) == []
