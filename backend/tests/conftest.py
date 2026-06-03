"""
Conftest for the backend/tests/ directory.

Applies to all test files in this directory and subdirectories.
"""
import os
import pytest
from pymongo import MongoClient
from unittest.mock import AsyncMock, MagicMock
import app.database
import app.routers.authRoutes
import app.auth.dependencies

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory slowapi storage before each test.

    Without this, successful register/login calls in one test file exhaust the
    per-IP rate limit budget and cause 429 failures in later tests that run in
    the same pytest session.
    """
    from app.limiter import limiter
    storage = limiter._storage
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "_storage") and isinstance(storage._storage, dict):
        storage._storage.clear()
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_test_db_session():
    """Setup test database cleanup for the entire session."""
    # Clean up test database at the start
    sync_client = MongoClient(TEST_MONGO_URL)
    try:
        sync_client.drop_database(TEST_DB_NAME)
    except:
        pass
    sync_client.close()

    yield

    # Cleanup after all tests
    sync_client = MongoClient(TEST_MONGO_URL)
    try:
        sync_client.drop_database(TEST_DB_NAME)
    except:
        pass
    sync_client.close()


class AsyncMongoWrapper:
    """Wraps a sync pymongo collection to work with async code."""

    def __init__(self, collection):
        self._collection = collection

    async def find_one(self, filter=None, **kwargs):
        return self._collection.find_one(filter, **kwargs)

    async def insert_one(self, document):
        return self._collection.insert_one(document)

    async def find(self, filter=None, **kwargs):
        """Return an async iterable wrapper."""

        class AsyncCursorWrapper:
            def __init__(self, cursor):
                self._cursor = cursor

            async def __aiter__(self):
                for doc in self._cursor:
                    yield doc

        return AsyncCursorWrapper(self._collection.find(filter, **kwargs))

    async def delete_many(self, filter):
        return self._collection.delete_many(filter)

    async def update_one(self, filter, update, **kwargs):
        return self._collection.update_one(filter, update, **kwargs)

    async def create_index(self, key_or_list, **kwargs):
        return self._collection.create_index(key_or_list, **kwargs)

    def __getattr__(self, name):
        # Fallback for other methods
        return getattr(self._collection, name)


@pytest.fixture(autouse=True)
def setup_test_db_per_test():
    """Setup test database for each test."""
    # Create sync client for this test
    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    # Wrap sync collection with async interface
    users_collection = AsyncMongoWrapper(sync_db["users"])

    # Patch app to use wrapped sync collection
    app.database.users_collection = users_collection
    app.routers.authRoutes.users_collection = users_collection
    app.auth.dependencies.users_collection = users_collection

    # Clean before test
    sync_db["users"].delete_many({})

    yield

    # Clean after test
    sync_db["users"].delete_many({})
    sync_client.close()
