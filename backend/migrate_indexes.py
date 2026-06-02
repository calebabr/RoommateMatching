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
from pymongo import MongoClient, ASCENDING
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

    print("likes:")
    _create(db.likes, [("fromUser", ASCENDING)],                                   "likes_from_user")
    _create(db.likes, [("toUser",   ASCENDING)],                                   "likes_to_user")
    _create(db.likes, [("fromUser", ASCENDING), ("toUser", ASCENDING)],            "likes_from_to_unique", unique=True)

    print("matches:")
    _create(db.matches, [("user1_id", ASCENDING)],                                  "matches_user1")
    _create(db.matches, [("user2_id", ASCENDING)],                                  "matches_user2")
    _create(db.matches, [("user1_id", ASCENDING), ("user2_id", ASCENDING)],         "matches_pair")

    print("recommendations:")
    _create(db.recommendations, [("userId", ASCENDING)], "recommendations_user_unique", unique=True)

    print("notifications:")
    _create(db.notifications, [("toUser", ASCENDING)],                              "notifications_to_user")
    _create(db.notifications, [("toUser", ASCENDING), ("read", ASCENDING)],         "notifications_to_user_read")

    print("chat_messages:")
    _create(db.chat_messages, [("fromUser", ASCENDING)],                            "chat_from_user")
    _create(db.chat_messages, [("toUser",   ASCENDING)],                            "chat_to_user")
    _create(db.chat_messages, [("fromUser", ASCENDING), ("toUser", ASCENDING), ("createdAt", ASCENDING)], "chat_conversation")

    client.close()
    print("\nAll indexes created successfully.")


if __name__ == "__main__":
    create_indexes()
