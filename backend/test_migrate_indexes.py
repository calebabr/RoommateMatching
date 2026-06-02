"""
Tests for the migrate_indexes.py migration script (P1.6).

Runs create_indexes() against a dedicated test DB and verifies that the
expected indexes exist. A second run confirms idempotency.
"""

import os
import pytest
from pymongo import MongoClient

_TEST_DB = "roommatch_migrate_test"
_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")


def _drop_test_db():
    client = MongoClient(_MONGO_URL)
    client.drop_database(_TEST_DB)
    client.close()


@pytest.fixture(autouse=True, scope="module")
def clean_test_db():
    _drop_test_db()
    yield
    _drop_test_db()


def test_indexes_created(monkeypatch):
    monkeypatch.setenv("MONGO_DB_NAME", _TEST_DB)
    monkeypatch.setenv("MONGO_URL", _MONGO_URL)

    from migrate_indexes import create_indexes
    create_indexes(db_name=_TEST_DB)

    client = MongoClient(_MONGO_URL)
    db = client[_TEST_DB]

    users_idx = db.users.index_information()
    assert "users_id_unique" in users_idx
    assert users_idx["users_id_unique"].get("unique") is True

    likes_idx = db.likes.index_information()
    assert "likes_from_to_unique" in likes_idx
    assert likes_idx["likes_from_to_unique"].get("unique") is True

    recs_idx = db.recommendations.index_information()
    assert "recommendations_user_unique" in recs_idx
    assert recs_idx["recommendations_user_unique"].get("unique") is True

    chat_idx = db.chat_messages.index_information()
    assert "chat_conversation" in chat_idx

    client.close()


def test_indexes_idempotent(monkeypatch):
    monkeypatch.setenv("MONGO_DB_NAME", _TEST_DB)
    monkeypatch.setenv("MONGO_URL", _MONGO_URL)

    from migrate_indexes import create_indexes
    # Second run must not raise
    create_indexes(db_name=_TEST_DB)
