"""
Unit tests for backend/app/services/matchScore.py (P3T.1).

These are pure function tests — no HTTP, no database.

matchScore internal data format (from UserInDB.toMatchDict):
  Each preference key maps to a list: [value, isDealBreaker]

categoryRange (used internally by matchScore):
  "sleepScheduleWeekdays": range=24, dealBreaker threshold factor=0.125
  "sleepScheduleWeekends": range=24, dealBreaker threshold factor=0.125
  "cleanliness":           range=10, dealBreaker threshold factor=0.2
  "noiseTolerance":        range=10, dealBreaker threshold factor=0.2
  "guests":                range=10, dealBreaker threshold factor=1.0
  "personality":           range=10, dealBreaker threshold factor=0.2
  "smoking":               range=10, dealBreaker threshold factor=0.1
  "sharedSpace":           range=10, dealBreaker threshold factor=0.2
  "communication":         range=10, dealBreaker threshold factor=0.2

dealBreak fires when:
  (user1[cat][1] OR user2[cat][1]) AND abs(diff) > range * factor

preferenceScore(cat, v1, v2) = 1 - (abs(v1 - v2) / range) ** 2
matchScore = mean(preferenceScore over all categories)  (0 if any deal-breaker)
"""

import math
import pytest

from app.services.matchScore import matchScore as MatchScore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(
    gender: str = "male",
    sleep_wd: float = 8.0,
    sleep_we: float = 10.0,
    cleanliness: float = 5.0,
    noise: float = 5.0,
    guests: float = 5.0,
    personality: float = 5.0,
    smoking: float = 0.0,
    shared_space: float = 5.0,
    communication: float = 5.0,
    db_wd: bool = False,
    db_we: bool = False,
    db_clean: bool = False,
    db_noise: bool = False,
    db_guests: bool = False,
    db_personality: bool = False,
    db_smoking: bool = False,
    db_shared: bool = False,
    db_comm: bool = False,
) -> dict:
    """Build a matchDict-shaped user dict."""
    return {
        "id": 0,
        "gender": gender,
        "matchedWith": [],
        "matchCount": 0,
        "sleepScheduleWeekdays": [sleep_wd, db_wd],
        "sleepScheduleWeekends": [sleep_we, db_we],
        "cleanliness": [cleanliness, db_clean],
        "noiseTolerance": [noise, db_noise],
        "guests": [guests, db_guests],
        "personality": [personality, db_personality],
        "smoking": [smoking, db_smoking],
        "sharedSpace": [shared_space, db_shared],
        "communication": [communication, db_comm],
    }


_scorer = MatchScore()


# ---------------------------------------------------------------------------
# Tests — identical preferences → max score
# ---------------------------------------------------------------------------

class TestIdenticalPreferences:
    """Two users with the exact same preference values should score 1.0."""

    def test_identical_male_users_score_1(self):
        u = _user(gender="male")
        score = _scorer.matchScore(u, u)
        assert math.isclose(score, 1.0, abs_tol=1e-9), f"Expected 1.0, got {score}"

    def test_identical_female_users_score_1(self):
        u = _user(gender="female")
        score = _scorer.matchScore(u, u)
        assert math.isclose(score, 1.0, abs_tol=1e-9), f"Expected 1.0, got {score}"

    def test_compatibility_score_identical_users_is_1(self):
        """compatibilityScore is min(matchScore(a,b), matchScore(b,a)); identical → 1.0."""
        u = _user()
        score = _scorer.compatibilityScore(u, u)
        assert math.isclose(score, 1.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Tests — preference distance reduces score
# ---------------------------------------------------------------------------

class TestPreferenceDistance:
    """Larger differences → lower score; closer → higher score."""

    def test_small_difference_scores_higher_than_large(self):
        base = _user()
        close = _user(cleanliness=5.5)
        far = _user(cleanliness=9.0)
        score_close = _scorer.matchScore(base, close)
        score_far = _scorer.matchScore(base, far)
        assert score_close > score_far, (
            f"Close pair ({score_close:.4f}) should outscore far pair ({score_far:.4f})"
        )

    def test_max_cleanliness_diff_gives_lower_score(self):
        a = _user(cleanliness=0.0)
        b = _user(cleanliness=10.0)
        score = _scorer.matchScore(a, b)
        # preferenceScore for cleanliness = 1 - (10/10)^2 = 0; others = 1.0
        # overall = (0 + 8 * 1.0) / 9 ≈ 0.888...
        assert score < 1.0
        assert score > 0.0

    def test_asymmetric_preferences_direction(self):
        """User A prefers cleanliness=9, user B is 2 — score should be low."""
        a = _user(cleanliness=9.0)
        b = _user(cleanliness=2.0)
        score = _scorer.matchScore(a, b)
        # diff=7, range=10 → 1 - (0.7)^2 = 0.51 for that category
        # expected mean ≈ (0.51 + 8*1.0) / 9 ≈ 0.946
        assert score < 1.0
        expected_clean = 1.0 - (7.0 / 10.0) ** 2  # 0.51
        expected_mean = (expected_clean + 8 * 1.0) / 9
        assert math.isclose(score, expected_mean, abs_tol=1e-6), (
            f"Expected ~{expected_mean:.4f}, got {score:.4f}"
        )

    def test_preference_score_formula_smoke_test(self):
        """preferenceScore for a known diff verifies the quadratic formula."""
        raw = _scorer.preferenceScore("cleanliness", 3.0, 7.0)
        expected = 1.0 - (4.0 / 10.0) ** 2  # 1 - 0.16 = 0.84
        assert math.isclose(raw, expected, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Tests — deal-breaker logic
# ---------------------------------------------------------------------------

class TestDealBreakers:
    """Deal-breakers above the threshold → matchScore returns 0.0."""

    def test_single_dealbreaker_triggered_returns_zero(self):
        """smoking isDealBreaker=True; threshold=10*0.1=1.0; diff=5 triggers it."""
        a = _user(smoking=0.0, db_smoking=True)
        b = _user(smoking=5.0)
        score = _scorer.matchScore(a, b)
        assert score == 0.0, f"Expected 0.0 (deal-breaker triggered), got {score}"

    def test_dealbreaker_on_either_user_triggers(self):
        """Deal-breaker flag on user2 (not user1) still fires."""
        a = _user(smoking=0.0)
        b = _user(smoking=5.0, db_smoking=True)
        score = _scorer.matchScore(a, b)
        assert score == 0.0

    def test_dealbreaker_within_threshold_does_not_trigger(self):
        """smoking isDealBreaker=True; threshold=1.0; diff=0.5 is within threshold."""
        a = _user(smoking=0.0, db_smoking=True)
        b = _user(smoking=0.5)
        score = _scorer.matchScore(a, b)
        assert score > 0.0, "Within-threshold deal-breaker should not zero the score"

    def test_multiple_dealbreakers_triggered(self):
        """Two separate deal-breakers triggered simultaneously → 0.0."""
        a = _user(smoking=0.0, db_smoking=True, cleanliness=0.0, db_clean=True)
        b = _user(smoking=5.0, cleanliness=9.0)
        score = _scorer.matchScore(a, b)
        assert score == 0.0

    def test_dealbreaker_cleanliness_threshold(self):
        """cleanliness threshold = 10*0.2 = 2.0; diff=3 triggers it."""
        a = _user(cleanliness=5.0, db_clean=True)
        b = _user(cleanliness=8.5)  # diff = 3.5 > 2.0
        score = _scorer.matchScore(a, b)
        assert score == 0.0

    def test_dealbreaker_sleep_weekdays_threshold(self):
        """sleepScheduleWeekdays threshold = 24*0.125 = 3.0; diff=5 triggers it."""
        a = _user(sleep_wd=6.0, db_wd=True)
        b = _user(sleep_wd=11.0)  # diff = 5 > 3.0
        score = _scorer.matchScore(a, b)
        assert score == 0.0

    def test_dealbreaker_guests_threshold(self):
        """guests threshold = 10*1.0 = 10.0; diff must exceed 10 which is impossible (range 0-10).
        So guests deal-breaker can never trigger in practice."""
        a = _user(guests=0.0, db_guests=True)
        b = _user(guests=10.0)  # diff = 10, threshold = 10 — NOT strictly greater
        score = _scorer.matchScore(a, b)
        # diff (10) is not > threshold (10), so deal-breaker should NOT fire
        assert score > 0.0, "guests deal-breaker at exactly range should not fire"


# ---------------------------------------------------------------------------
# Tests — boundary values
# ---------------------------------------------------------------------------

class TestBoundaryValues:
    """min (0.0) and max (10.0) preference values."""

    def test_both_at_min_value_scores_1(self):
        a = _user(
            cleanliness=0.0, noise=0.0, guests=0.0,
            personality=0.0, smoking=0.0, shared_space=0.0, communication=0.0,
        )
        b = _user(
            cleanliness=0.0, noise=0.0, guests=0.0,
            personality=0.0, smoking=0.0, shared_space=0.0, communication=0.0,
        )
        score = _scorer.matchScore(a, b)
        assert math.isclose(score, 1.0, abs_tol=1e-9)

    def test_both_at_max_value_scores_1(self):
        a = _user(
            cleanliness=10.0, noise=10.0, guests=10.0,
            personality=10.0, smoking=10.0, shared_space=10.0, communication=10.0,
        )
        b = _user(
            cleanliness=10.0, noise=10.0, guests=10.0,
            personality=10.0, smoking=10.0, shared_space=10.0, communication=10.0,
        )
        score = _scorer.matchScore(a, b)
        assert math.isclose(score, 1.0, abs_tol=1e-9)

    def test_score_is_in_range_zero_to_one(self):
        """matchScore always returns a value in [0.0, 1.0]."""
        a = _user(cleanliness=0.0, noise=10.0)
        b = _user(cleanliness=10.0, noise=0.0)
        score = _scorer.matchScore(a, b)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Tests — gender gating
# ---------------------------------------------------------------------------

class TestGenderGating:
    """Males can only match males; females only females."""

    def test_male_female_pair_returns_zero(self):
        m = _user(gender="male")
        f = _user(gender="female")
        score = _scorer.matchScore(m, f)
        assert score == 0.0

    def test_female_male_pair_returns_zero(self):
        f = _user(gender="female")
        m = _user(gender="male")
        score = _scorer.matchScore(f, m)
        assert score == 0.0

    def test_compatibility_score_cross_gender_returns_zero(self):
        m = _user(gender="male")
        f = _user(gender="female")
        assert _scorer.compatibilityScore(m, f) == 0.0

    def test_missing_gender_allows_matching(self):
        """Backwards compat: users with empty gender string can match anyone."""
        a = _user(gender="")
        b = _user(gender="female")
        score = _scorer.matchScore(a, b)
        assert score > 0.0

    def test_same_gender_female_scores_normally(self):
        f1 = _user(gender="female")
        f2 = _user(gender="female")
        score = _scorer.matchScore(f1, f2)
        assert score > 0.0


# ---------------------------------------------------------------------------
# Tests — symmetry and special cases
# ---------------------------------------------------------------------------

class TestSymmetryAndEdgeCases:
    """matchScore may be asymmetric due to which user holds the deal-breaker flag."""

    def test_compatibility_score_symmetric(self):
        """compatibilityScore(a, b) == compatibilityScore(b, a) for same deal-breakers."""
        a = _user(cleanliness=3.0)
        b = _user(cleanliness=7.0)
        assert math.isclose(
            _scorer.compatibilityScore(a, b),
            _scorer.compatibilityScore(b, a),
            abs_tol=1e-9,
        )

    def test_compatibility_score_is_min_of_both_directions(self):
        """compatibilityScore uses min(matchScore(a,b), matchScore(b,a))."""
        a = _user(smoking=0.0, db_smoking=True)   # A has deal-breaker on smoking
        b = _user(smoking=0.4)                     # diff=0.4, threshold=1.0 — does NOT fire
        s_ab = _scorer.matchScore(a, b)
        s_ba = _scorer.matchScore(b, a)
        expected = min(s_ab, s_ba)
        got = _scorer.compatibilityScore(a, b)
        assert math.isclose(got, expected, abs_tol=1e-9)

    def test_score_is_not_negative(self):
        """Worst-case difference should never produce a negative score."""
        a = _user(
            sleep_wd=0.0, sleep_we=0.0,
            cleanliness=0.0, noise=0.0, guests=0.0,
            personality=0.0, smoking=0.0, shared_space=0.0, communication=0.0,
        )
        b = _user(
            sleep_wd=24.0, sleep_we=24.0,
            cleanliness=10.0, noise=10.0, guests=10.0,
            personality=10.0, smoking=10.0, shared_space=10.0, communication=10.0,
        )
        score = _scorer.matchScore(a, b)
        assert score >= 0.0
