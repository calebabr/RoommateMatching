import logging
from datetime import datetime, timedelta, timezone
from app.services.matchScore import matchScore
from app.database import recommendations_collection, users_collection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# P3FT.10 — housing intent filters.
#
# These are applied on top of the stored compatibility scores when serving
# `GET /users/{user_id}/top-matches`; `matchScore.py` category weights are
# deliberately left untouched.
# ---------------------------------------------------------------------------

MOVE_IN_MISMATCH_PENALTY = 0.7
_BUDGET_FLOOR = 0
_BUDGET_CEILING = 5000


def housing_compatible(user_a: dict, user_b: dict) -> bool:
    """Hard filter: on-campus and off-campus never match. 'either' matches both.

    Users who have not set `housingType` are always compatible (backwards compat).
    """
    a = user_a.get("housingType")
    b = user_b.get("housingType")
    if not a or not b:
        return True
    if a == "either" or b == "either":
        return True
    return a == b


def _budget_range(user: dict):
    """Return (low, high) for a user, or None when no budget is set at all."""
    low = user.get("budgetMin")
    high = user.get("budgetMax")
    if low is None and high is None:
        return None
    return (
        _BUDGET_FLOOR if low is None else low,
        _BUDGET_CEILING if high is None else high,
    )


def budget_compatible(user_a: dict, user_b: dict) -> bool:
    """Hard filter: budget ranges that do not overlap cannot match.

    If either user has no budget set the filter does not apply.
    """
    range_a = _budget_range(user_a)
    range_b = _budget_range(user_b)
    if range_a is None or range_b is None:
        return True
    return range_a[0] <= range_b[1] and range_b[0] <= range_a[1]


def move_in_penalty(user_a: dict, user_b: dict) -> float:
    """Soft penalty: a move-in semester mismatch multiplies the score by 0.7.

    Applies only when both users have supplied a full season + year.
    """
    season_a, year_a = user_a.get("moveInSeason"), user_a.get("moveInYear")
    season_b, year_b = user_b.get("moveInSeason"), user_b.get("moveInYear")
    if not season_a or not season_b or year_a is None or year_b is None:
        return 1.0
    if season_a == season_b and year_a == year_b:
        return 1.0
    return MOVE_IN_MISMATCH_PENALTY


def housing_score_multiplier(viewer: dict, candidate: dict):
    """Combined P3FT.10 gate.

    Returns None when the candidate is hard-filtered out, otherwise the score
    multiplier to apply (1.0, or MOVE_IN_MISMATCH_PENALTY on a semester mismatch).
    """
    if not housing_compatible(viewer, candidate):
        return None
    if not budget_compatible(viewer, candidate):
        return None
    return move_in_penalty(viewer, candidate)


# ---------------------------------------------------------------------------
# How many scored candidates are stored per user in `recommendations.matches`.
#
# P3D.7 mitigation: this was 10, which starved the P3FT.16 discover filters.
# The filters run against this stored slice, and the slice is ranked with no
# knowledge of them — so filtering by major could return `matches: []` while
# hundreds of matching users sat just below the cut, and the UI would tell the
# user to widen filters that were never the binding constraint.
#
# Raising it to 100 is storage-only: `recompute_for_user` already scores every
# candidate and sorts them, so `[:n]` changes what is kept, not what is
# computed.  CPU per recompute is unchanged; the stored array grows from
# roughly 0.4 KB to 4 KB per user (~20 MB at 5000 users).
#
# This narrows the starvation window by 10x but does NOT close it — with a
# large enough pool the same failure returns.  The real fix is to stop
# pre-truncating: query candidates directly when filters are active, or push
# the filters into the recompute.  Tracked, deliberately not done here.
RECOMMENDATION_POOL_SIZE = 100

# ---------------------------------------------------------------------------
# P3FT.16 — discover filters.
#
# Applied to candidate user documents *after* the block/pause/deactivate/skip/
# roommate-found exclusions and after the P3FT.10 housing hard filters, and
# before the result is returned, so a narrow filter never starves the page by
# competing with those gates.
# ---------------------------------------------------------------------------


def _norm(value) -> str:
    return str(value).strip().lower() if value is not None else ""


def candidate_matches_filters(candidate: dict, filters) -> bool:
    """True when `candidate` survives every supplied discover filter.

    Semantics, per filter:
      * `major`   — OR across the supplied majors, case-insensitive.  A
                    candidate with no major set is excluded.
      * `gradYearMin` / `gradYearMax` — inclusive bounds on `graduationYear`.
                    A candidate with no graduation year is excluded.
      * `tags`    — OR: the candidate must carry at least one requested tag.
      * `religion`— exact match on `religionTag`, case-insensitive.
      * `housingType` — the candidate's own `housingType`, where `"either"`
                    satisfies any request (mirrors `housing_compatible`).
                    A candidate with no housing type set is excluded.
      * `budgetMax` — the candidate's floor (`budgetMin`, defaulting to 0) must
                    sit at or below the requested ceiling.

    `minScore` is not evaluated here: it applies to the post-housing-multiplier
    score, which lives on the recommendation entry rather than on the user doc.
    """
    if filters is None:
        return True

    if filters.major is not None:
        wanted = {_norm(m) for m in filters.major}
        if _norm(candidate.get("major")) not in wanted:
            return False

    if filters.gradYearMin is not None or filters.gradYearMax is not None:
        grad_year = candidate.get("graduationYear")
        if not isinstance(grad_year, int) or isinstance(grad_year, bool):
            return False
        if filters.gradYearMin is not None and grad_year < filters.gradYearMin:
            return False
        if filters.gradYearMax is not None and grad_year > filters.gradYearMax:
            return False

    if filters.tags is not None:
        candidate_tags = {_norm(t) for t in (candidate.get("lifestyleTags") or [])}
        if not candidate_tags & {_norm(t) for t in filters.tags}:
            return False

    if filters.religion is not None:
        if _norm(candidate.get("religionTag")) != _norm(filters.religion):
            return False

    if filters.housingType is not None:
        candidate_housing = candidate.get("housingType")
        if not candidate_housing:
            return False
        if candidate_housing != "either" and candidate_housing != filters.housingType:
            return False

    if filters.budgetMax is not None:
        candidate_floor = candidate.get("budgetMin")
        if candidate_floor is None:
            candidate_floor = _BUDGET_FLOOR
        if candidate_floor > filters.budgetMax:
            return False

    return True


def score_passes_min(score: float, filters) -> bool:
    """`minScore` is expressed 0-100; stored compatibility scores are 0-1."""
    if filters is None or filters.minScore is None:
        return True
    return score * 100.0 >= filters.minScore


# ---------------------------------------------------------------------------
# P3B.9 — significant-change detection and recompute rate limiting.
# ---------------------------------------------------------------------------

# The nine scored preference fields, as they are stored on the user document.
PREFERENCE_FIELDS = (
    "sleepScoreWD",
    "sleepScoreWE",
    "cleanlinessScore",
    "noiseToleranceScore",
    "guestsScore",
    "personalityScore",
    "smokingScore",
    "sharedSpaceScore",
    "communicationScore",
)

# A preference has to move at least this far (on its own scale) to be worth an
# O(N) recompute.
SIGNIFICANT_SHIFT = 2.0

# At most one profile-save-triggered recompute per user per hour.
RECOMPUTE_COOLDOWN = timedelta(hours=1)


def _pref_parts(raw):
    """Return (value, isDealBreaker) from a stored preference, or (None, None)."""
    if isinstance(raw, dict):
        value = raw.get("value")
        flag = raw.get("isDealBreaker")
    elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
        value, flag = raw[0], raw[1]
    else:
        return None, None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        value = None
    return value, bool(flag)


def preferences_changed_significantly(before: dict, after: dict) -> bool:
    """True when any preference shifted by >= SIGNIFICANT_SHIFT or a deal-breaker toggled."""
    before = before or {}
    after = after or {}
    for field in PREFERENCE_FIELDS:
        old_value, old_flag = _pref_parts(before.get(field))
        new_value, new_flag = _pref_parts(after.get(field))
        if new_value is None and new_flag is None:
            continue  # field absent from the update — nothing changed
        if old_value is None and old_flag is None:
            return True  # newly supplied preference
        if old_flag != new_flag:
            return True  # deal-breaker toggled
        if (
            old_value is not None
            and new_value is not None
            and abs(new_value - old_value) >= SIGNIFICANT_SHIFT
        ):
            return True
    return False


def _late_bound_services():
    """Build a `(UserProfileService, RecommendationService)` pair bound to the
    collections `app.database` exposes *right now*.

    Both services capture their collections at import time
    (`self.collection = users_collection`).  That is fine for a request handler,
    which is created and used inside one consistent process, but it is wrong for
    a background task: anything that rebinds `app.database.*` afterwards — the
    test suite does exactly this — leaves the captured handle pointing at a
    different client than the rest of the request is using.  Running two clients
    against one database from the same event loop produced genuinely
    nondeterministic behaviour.  Fresh instances are returned so nothing mutates
    shared service state.
    """
    import app.database as _db
    from app.services.userProfileService import UserProfileService

    profile_service = UserProfileService()
    profile_service.collection = _db.users_collection

    service = RecommendationService()
    service.recommendations = _db.recommendations_collection
    return profile_service, service


class RecommendationService:
    def __init__(self):
        self.scorer = matchScore()
        self.recommendations = recommendations_collection

    async def recompute_for_user(self, target_user: dict, candidate_users: list[dict], n=RECOMMENDATION_POOL_SIZE):
        already_matched = target_user.get("matchedWith") or []
        if isinstance(already_matched, int):
            already_matched = [already_matched]
        already_matched_set = set(already_matched)

        scores = []
        for user in candidate_users:
            if user["id"] == target_user["id"]:
                continue
            # Skip users already matched with
            if user["id"] in already_matched_set:
                continue
            # Gender filter: only same-gender candidates
            if not self.scorer.genderCompatible(target_user, user):
                continue
            score = self.scorer.compatibilityScore(target_user, user)
            if score > 0:
                scores.append({
                    "user_id": user["id"],
                    "compatibilityScore": round(score, 6)
                })

        scores.sort(key=lambda x: x["compatibilityScore"], reverse=True)
        top_matches = scores[:n]

        await self.recommendations.update_one(
            {"userId": target_user["id"]},
            {"$set": {"matches": top_matches, "computedAt": datetime.now(timezone.utc)}},
            upsert=True
        )

    async def get_top_matches(self, user_id: int) -> list[dict]:
        result = await self.recommendations.find_one({"userId": user_id})
        if not result:
            return []
        return result.get("matches", [])

    async def on_new_user(self, new_user: dict, all_users: list[dict]):
        await self.recompute_for_user(new_user, all_users)
        for user in all_users:
            if user["id"] != new_user["id"]:
                await self.recompute_for_user(user, all_users)

    async def on_user_matched(self, matched_user_id: int):
        await self.recommendations.update_many(
            {},
            {"$pull": {"matches": {"user_id": matched_user_id}}}
        )
        await self.recommendations.delete_one({"userId": matched_user_id})

    async def on_user_unmatched(self, user_id: int, all_users: list[dict]):
        user_dict = None
        for u in all_users:
            if u["id"] == user_id:
                user_dict = u
                break
        if user_dict:
            await self.recompute_for_user(user_dict, all_users)
            for user in all_users:
                if user["id"] != user_id:
                    await self.recompute_for_user(user, all_users)

    async def recompute_all(self, all_users: list[dict]):
        for user in all_users:
            await self.recompute_for_user(user, all_users)

    # -----------------------------------------------------------------------
    # P3B.8 / P3B.9 — background recompute entry points.
    # -----------------------------------------------------------------------

    async def should_recompute_on_profile_save(
        self, user_id: int, before: dict, after: dict
    ) -> bool:
        """Gate a profile-save recompute (P3B.9).

        Returns True only when a preference moved by >= SIGNIFICANT_SHIFT or a
        deal-breaker toggled, AND this user has not already triggered a
        recompute within RECOMPUTE_COOLDOWN.  Claims the cooldown slot as a
        side effect when it returns True, so two rapid saves cannot both fire.
        """
        if not preferences_changed_significantly(before, after):
            return False

        now = datetime.now(timezone.utc)
        last = (before or {}).get("lastRecomputeAt")
        if isinstance(last, datetime):
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if now - last < RECOMPUTE_COOLDOWN:
                return False

        await users_collection.update_one(
            {"id": user_id}, {"$set": {"lastRecomputeAt": now}}
        )
        return True

    async def recompute_for_user_id(self, user_id: int) -> None:
        """Background-task entry point (P3B.8).

        Re-reads the active user pool itself rather than closing over a list
        captured before the response was sent, and never raises — a failed
        background recompute must not surface anywhere, and `/admin/recompute`
        can always repair the state.
        """
        try:
            from app.models import UserInDB

            profile_service, service = _late_bound_services()
            users = await profile_service.get_all_active_users()
            if len(users) < 2:
                return
            user_dicts = []
            for u in users:
                try:
                    user_dicts.append(UserInDB(**u).toMatchDict())
                except Exception:
                    continue  # a malformed profile must not abort the whole pass
            target = next((d for d in user_dicts if d["id"] == user_id), None)
            if target is None:
                return
            await service.on_new_user(target, user_dicts)
        except Exception:
            logger.exception("Background recompute failed for user %s", user_id)

    async def recompute_single_user(self, user_id: int) -> bool:
        """Rebuild ONE user's feed. O(N) reads but a single write.

        Used on unpause (P3D.7): `recompute_all_active` skips paused users, so
        a paused user's recommendations document expires under the 7-day TTL
        and they would face an empty discover page for up to 24 hours until the
        next nightly job. This restores it immediately without paying for the
        full O(N)-write `on_new_user`.
        """
        try:
            from app.models import UserInDB

            profile_service, service = _late_bound_services()
            users = await profile_service.get_all_active_users()
            if len(users) < 2:
                return False
            user_dicts = []
            for u in users:
                try:
                    user_dicts.append(UserInDB(**u).toMatchDict())
                except Exception:
                    continue
            target = next((d for d in user_dicts if d["id"] == user_id), None)
            if target is None:
                return False
            await service.recompute_for_user(target, user_dicts)
            return True
        except Exception:
            logger.exception("Single-user recompute failed for user %s", user_id)
            return False

    async def recompute_all_active(self) -> int:
        """Full recompute over every active user.  Used by the daily scheduled job."""
        from app.models import UserInDB

        profile_service, service = _late_bound_services()
        users = await profile_service.get_all_active_users()
        if len(users) < 2:
            return 0
        user_dicts = []
        for u in users:
            try:
                user_dicts.append(UserInDB(**u).toMatchDict())
            except Exception:
                continue
        await service.recompute_all(user_dicts)
        return len(user_dicts)