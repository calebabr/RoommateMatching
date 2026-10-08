import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("MONGO_DB_NAME", "roommatch")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_collection = db["users"]
likes_collection = db["likes"]
matches_collection = db["matches"]
recommendations_collection = db["recommendations"]
chat_collection = db["chat_messages"]
notifications_collection = db["notifications"]
counters_collection = db["counters"]
blocks_collection = db["blocks"]
reports_collection = db["reports"]
feedback_collection = db["feedback"]
conversation_reports_collection = db["conversation_reports"]
chat_read_status_collection = db["chat_read_status"]
swipes_collection = db["swipes"]
groups_collection = db["groups"]
group_invites_collection = db["group_invites"]
outcomes_collection = db["outcomes"]

# ---------------------------------------------------------------------------
# Retention (TTL indexes live in migrate_indexes.py)
#   swipes          30 days  on skipped_at
#   notifications   90 days  on createdAt   (P3D.3 — informational, one semester)
#   likes          180 days  on createdAt   (P3D.4 — PENDING likes only: likeService
#                                            deletes both rows when a match confirms)
#   group_invites   14 days  on createdAt   (partial: status == "pending" only)
#   recommendations  7 days  on computedAt   (P3D.6 — safe ONLY because the
#                                            nightly_recompute scheduler job rebuilds
#                                            them; see migrate_indexes.py)
#
# matchedWith invariant (P3D.1): users.matchedWith is ALWAYS a list of ints — never
# None, never a bare int. matchCount == len(matchedWith) and matched == matchCount > 0.
# Enforced by backend/migrate_matched_with.py; do not reintroduce defensive coercion.
#
# matches (P3D.2): compatibilityScore was declared on the ConfirmedMatch model long
# before anything wrote it, and is populated going forward only from 2026-09-03 — rows
# confirmed before that date have no score and were deliberately NOT backfilled, since
# recomputing from today's preferences would fabricate history. A null here therefore
# means "not measured", which is the OPPOSITE of a null in outcomes.compatibilityScore
# ("not a real in-app match"). See the outcomes notes below before doing weight tuning.
# ---------------------------------------------------------------------------
# Schema notes for the collections added in Phase 3 (P3FT.10 / P3FT.12 / P3FT.13)
#
# groups (P3FT.13) — a roommate group of 2-4 same-gender users.
#   id         int                          atomic counter id (counters collection)
#   name       str | None                   optional label, 40-char max
#   memberIds  [int]                        user ids; len(memberIds) <= maxSize
#   createdBy  int                          user id of the creator
#   createdAt  datetime
#   maxSize    int                          2-4
#   status     "open" | "full" | "closed"   a user may belong to at most one "open" group
#
# group_invites (P3FT.13) — pending invitation from a group member to a match.
#   id          int                                   atomic counter id
#   groupId     int                                   groups.id
#   fromUserId  int                                   inviting member
#   toUserId    int                                   invited user
#   status      "pending" | "accepted" | "declined"
#   createdAt   datetime                              partial TTL: only "pending" invites expire,
#                                                     14 days after this. Once accepted/declined an
#                                                     invite leaves the TTL index and is retained.
#
# outcomes (P3FT.12) — record of a successful roommate pairing, for weight tuning.
#   userId              int | None     None once that user was hard-deleted (see below)
#   partnerId           int | None     None once that user was hard-deleted (see below)
#   compatibilityScore  float | None   None when the pair was not a real in-app match
#   viaApp              bool
#   recordedAt          datetime
#
#   Null compatibilityScore is AMBIGUOUS ACROSS COLLECTIONS — do not treat it as one
#   category. Here it means "this pair was not a real in-app match" (a user who reported
#   finding a roommate elsewhere): a genuine negative. In `matches` the same null means
#   "this match predates the field": a missing measurement. Opposite facts. Weight-tuning
#   work must filter on a POSITIVE signal — `viaApp: true` here, or `confirmedAt` after
#   the field's ship date (2026-09-03) for `matches` — never on `compatibilityScore is
#   not None`, which pools the two and biases the result toward pairs that never used
#   the app.
#
#   Erasure: hard_delete_user ANONYMIZES these rows rather than removing them — userId and
#   partnerId are independently set to None wherever they match the deleted user, while
#   compatibilityScore / viaApp / recordedAt are preserved. Nulling both ids makes a row
#   genuinely anonymous while keeping the tuning signal, which lives entirely in the score
#   and channel fields. So BOTH id fields are nullable: any reader, query or pipeline over
#   this collection must not assume non-null ids. (outcomes_userId is a plain ascending,
#   non-unique, non-sparse index, so nulls index and query normally.)
#
# users — new optional fields (P3FT.10 housing intent, P3FT.12 found-a-roommate):
#   housingType        "on-campus" | "off-campus" | "either"
#   preferredLocation  str    free text, 60-char max, HTML-stripped
#   budgetMin          int    monthly USD, 0-5000, off-campus only
#   budgetMax          int    monthly USD, 0-5000, off-campus only
#   leaseTerm          "fall" | "spring" | "summer" | "full-year"
#   moveInSeason       str    season half of the move-in semester
#   moveInYear         int    year half of the move-in semester
#   roommateFound      bool   when true the user is hidden from discover / likes / top-matches
#                             (filtered in Python or as a $ne residual — deliberately unindexed,
#                             same as is_paused / is_deactivated)
#   roommateFoundAt    datetime
#   roommateFoundWith  [int]  partner user ids
# ---------------------------------------------------------------------------