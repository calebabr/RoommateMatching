#!/usr/bin/env python3
"""
Run once against a fresh MongoDB instance (local or Atlas) to create all
production indexes. Safe to re-run — existing indexes are skipped.

Usage:
    cd backend
    python migrate_indexes.py
"""
import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient, ASCENDING, DESCENDING
import pymongo.errors

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME   = os.environ.get("MONGO_DB_NAME", "roommatch")


def _create(collection, keys, name, **kwargs):
    try:
        collection.create_index(keys, name=name, **kwargs)
        print(f"  [ok] {name}")
    except pymongo.errors.OperationFailure as e:
        if e.details and e.details.get("codeName") in ("IndexOptionsConflict", "IndexKeySpecsConflict"):
            print(f"  [skip] {name} (already exists with different options)")
        else:
            raise


def create_indexes(db_name=None):
    client = MongoClient(MONGO_URL)
    db = client[db_name or DB_NAME]

    print("users:")
    _create(db.users, [("id", ASCENDING)],    "users_id_unique",    unique=True)
    _create(db.users, [("email", ASCENDING)],  "users_email_unique", unique=True, sparse=True)
    # P3D.7 — both of these were full COLLSCANs of the users collection.
    # `username` backs the register duplicate-check. Left NON-unique deliberately:
    # it should be unique, but a unique build would abort on any pre-existing
    # duplicate in production. Verify with a $group dupe-check, then tighten.
    _create(db.users, [("username", ASCENDING)], "users_username")
    # `refresh_token_hash` backs POST /auth/refresh, which every active session hits
    # on every token rotation - the hottest unindexed query in the app. Sparse
    # because the field only exists while a refresh token is outstanding.
    _create(db.users, [("refresh_token_hash", ASCENDING)], "users_refresh_token_hash", sparse=True)
    # No index on the P3FT.10 housing fields or on P3FT.12 `roommateFound`: housing
    # compatibility and budget overlap are evaluated in Python on docs already fetched
    # by `id` $in, and the `roommateFound` exclusions are $ne/$or residuals on queries
    # that lead with `id` $in or scan anyway (as `is_paused`/`is_deactivated` do today).
    # Both would be pure write overhead on the hottest collection. Revisit if a query
    # ever filters on these fields with an equality prefix.

    print("likes:")
    _create(db.likes, [("fromUser", ASCENDING)],                                   "likes_from_user")
    _create(db.likes, [("toUser",   ASCENDING)],                                   "likes_to_user")
    _create(db.likes, [("fromUser", ASCENDING), ("toUser", ASCENDING)],            "likes_from_to_unique", unique=True)
    # P3D.4 — expire stale PENDING likes after 180 days.
    # Safe against deleting a like that produced a match: likeService deletes both
    # direction rows the moment a match is confirmed ("Clean up like records"), so
    # every surviving row is pending by construction. 180d (one academic year) is
    # deliberately conservative — a like is user intent that cannot be regenerated,
    # and expiry silently removes it from the recipient's likes-received list.
    _create(db.likes, [("createdAt", ASCENDING)], "likes_ttl", expireAfterSeconds=15552000)

    print("matches:")
    _create(db.matches, [("user1_id", ASCENDING)],                                  "matches_user1")
    _create(db.matches, [("user2_id", ASCENDING)],                                  "matches_user2")
    _create(db.matches, [("user1_id", ASCENDING), ("user2_id", ASCENDING)],         "matches_pair")

    print("recommendations:")
    _create(db.recommendations, [("userId", ASCENDING)], "recommendations_user_unique", unique=True)
    # P3D.6 — 7-day TTL on `computedAt`. ENABLED as of P3B.10, which added the
    # `nightly_recompute` APScheduler job (04:00 UTC, RecommendationService.
    # recompute_all_active): anything this expires is rebuilt within 24h. In practice
    # an active user's doc is refreshed nightly and never reaches 7 days, so the TTL
    # mainly garbage-collects orphaned docs for users who left the active pool.
    #
    # DEPLOY REQUIREMENT: this index's safety DEPENDS on that scheduler running.
    # _start_scheduler() is deliberately non-fatal — a missing APScheduler logs a
    # warning and the app serves on with no jobs. A deployment without APScheduler
    # installed would therefore expire recommendations with nothing rebuilding them,
    # emptying discover feeds. Verify APScheduler is installed and the process is
    # long-lived (not serverless/multi-process-without-a-leader) before shipping this.
    _create(db.recommendations, [("computedAt", ASCENDING)], "recommendations_ttl",
            expireAfterSeconds=604800)

    print("notifications:")
    _create(db.notifications, [("toUser", ASCENDING)],                              "notifications_to_user")
    _create(db.notifications, [("toUser", ASCENDING), ("read", ASCENDING)],         "notifications_to_user_read")
    # P3D.7 — serves the toUser equality AND the createdAt sort in one index. Without
    # it the planner picked `notifications_ttl` (createdAt order) and filtered by
    # toUser, which at scale walks other users' notifications newest-first to fill one
    # user's page. This supersedes `notifications_to_user` above (same prefix); that
    # one is kept only to avoid a drop in this migration - remove it once verified.
    _create(db.notifications, [("toUser", ASCENDING), ("createdAt", DESCENDING)], "notifications_to_user_created")
    # P3D.3 — expire notifications after 90 days. They are purely informational, the UI
    # reads them sorted by createdAt desc with a limit, and nothing aggregates over old
    # ones. 90d covers a full semester so a user returning from break keeps their history.
    _create(db.notifications, [("createdAt", ASCENDING)], "notifications_ttl", expireAfterSeconds=7776000)

    print("chat_messages:")
    _create(db.chat_messages, [("fromUser", ASCENDING)],                            "chat_from_user")
    _create(db.chat_messages, [("toUser",   ASCENDING)],                            "chat_to_user")
    _create(db.chat_messages, [("fromUser", ASCENDING), ("toUser", ASCENDING), ("createdAt", ASCENDING)], "chat_conversation")

    print("swipes:")
    _create(db.swipes, [("user_id", ASCENDING), ("skipped_user_id", ASCENDING)], "swipes_user_skipped", unique=True)
    _create(db.swipes, [("user_id", ASCENDING)],                                  "swipes_user_id")
    _create(db.swipes, [("skipped_at", ASCENDING)],                               "swipes_ttl", expireAfterSeconds=2592000)

    print("groups:")
    _create(db.groups, [("id", ASCENDING)],        "groups_id_unique", unique=True)
    _create(db.groups, [("memberIds", ASCENDING)], "groups_memberIds")
    _create(db.groups, [("status", ASCENDING)],    "groups_status")

    print("group_invites:")
    _create(db.group_invites, [("toUserId", ASCENDING), ("status", ASCENDING)], "group_invites_toUser_status")
    _create(db.group_invites, [("groupId",  ASCENDING)],                        "group_invites_groupId")
    # Partial TTL: only *pending* invites expire (14 days). Once an invite is accepted or
    # declined it leaves the partial index and is retained as a permanent record.
    _create(db.group_invites, [("createdAt", ASCENDING)],                       "group_invites_ttl",
            expireAfterSeconds=1209600, partialFilterExpression={"status": "pending"})

    print("blocks:")
    # P3D.7 — the blocks collection had NO indexes at all, yet get_blocked_ids()
    # runs an $or over both fields on every discover request.
    _create(db.blocks, [("blockerId", ASCENDING)], "blocks_blocker")
    _create(db.blocks, [("blockedId", ASCENDING)], "blocks_blocked")
    # NOT unique, deliberately: blockService already dedupes before insert, but a
    # unique build ABORTS on any pre-existing duplicate pair in production (unlike an
    # options conflict, _create cannot skip that). Same reasoning as users_username.
    # Recommend tightening to unique after a $group dupe-check at deploy time.
    _create(db.blocks, [("blockerId", ASCENDING), ("blockedId", ASCENDING)], "blocks_pair")

    print("chat_read_status:")
    # P3D.7 — read per conversation open, and once per partner in the unread-count
    # loop. Unique: one row per (user, partner) pair, which is how it is upserted.
    _create(db.chat_read_status, [("user_id", ASCENDING), ("partner_id", ASCENDING)],
            "chat_read_status_pair")

    print("reports:")
    _create(db.reports, [("status", ASCENDING), ("createdAt", DESCENDING)], "reports_status_created")
    _create(db.conversation_reports, [("status", ASCENDING), ("createdAt", DESCENDING)],
            "conversation_reports_status_created")

    print("outcomes:")
    _create(db.outcomes, [("userId",     ASCENDING)], "outcomes_userId")
    _create(db.outcomes, [("recordedAt", ASCENDING)], "outcomes_recordedAt")

    client.close()
    print("\nAll indexes created successfully.")


if __name__ == "__main__":
    create_indexes()
