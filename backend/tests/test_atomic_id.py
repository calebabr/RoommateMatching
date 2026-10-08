"""
Tests for P1.1 — atomic user ID generation via MongoDB findOneAndUpdate counter.

Uses a real Motor client pointed at roommatch_test so that concurrent async
registrations exercise the actual atomic counter rather than a mock.
"""

import asyncio
import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient, ASGITransport

TEST_MONGO_URL = "mongodb://localhost:27017/"
# The test database name is per-process (see tests/conftest.py); importing it
# rather than hard-coding "roommatch_test" keeps this file pointed at the same
# database the app collections were bound to.
from tests.conftest import TEST_DB_NAME  # noqa: E402

_STRONG_PASSWORD = "Tr0ub4dor&3"


def _make_motor_collection(collection_name: str):
    client = AsyncIOMotorClient(TEST_MONGO_URL)
    return client[TEST_DB_NAME][collection_name]


@pytest_asyncio.fixture(autouse=True)
async def clean_test_db():
    """Drop and re-create the test collections before and after each test."""
    motor_client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = motor_client[TEST_DB_NAME]
    await db["users"].drop()
    await db["counters"].drop()
    yield
    await db["users"].drop()
    await db["counters"].drop()
    motor_client.close()


@pytest_asyncio.fixture()
async def client():
    import app.database
    import app.routers.authRoutes
    import app.auth.dependencies

    motor_client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = motor_client[TEST_DB_NAME]

    users_col = db["users"]
    counters_col = db["counters"]

    # Save originals. Without this the Motor collections below leaked into every
    # test module that ran after this one; motor_client.close() at teardown then
    # left them bound to a closed client, so ~40 later tests died with
    # "pymongo.errors.InvalidOperation: Cannot use MongoClient after close".
    orig = {
        "db.users": app.database.users_collection,
        "ar.users": app.routers.authRoutes.users_collection,
        "ar.counters": app.routers.authRoutes.counters_collection,
        "deps.users": app.auth.dependencies.users_collection,
    }

    app.database.users_collection = users_col
    app.routers.authRoutes.users_collection = users_col
    app.routers.authRoutes.counters_collection = counters_col
    app.auth.dependencies.users_collection = users_col

    # Reset rate limiter so the 3/hour register limit doesn't block tests
    from app.limiter import limiter
    storage = limiter._storage
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "_storage") and isinstance(storage._storage, dict):
        storage._storage.clear()

    from app.main import app as fastapi_app
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.database.users_collection = orig["db.users"]
    app.routers.authRoutes.users_collection = orig["ar.users"]
    app.routers.authRoutes.counters_collection = orig["ar.counters"]
    app.auth.dependencies.users_collection = orig["deps.users"]

    motor_client.close()


@pytest.mark.asyncio
async def test_concurrent_registrations_unique_ids(client: AsyncClient):
    """10 simultaneous registrations must produce 10 distinct integer user IDs."""

    async def register(i: int):
        # The rate limiter keys on the first 32 chars of the Bearer token;
        # put the unique index at the start so each request gets its own bucket
        fake_token = f"t{i:02d}_bypass_ratelimit_for_atomicid_tests_padding"
        return await client.post(
            "/api/auth/register",
            headers={"Authorization": f"Bearer {fake_token}"},
            json={
                "email": f"concurrent{i}@test.com",
                "password": _STRONG_PASSWORD,
                "username": f"concurrent{i}",
                "gender": "male",
            },
        )

    responses = await asyncio.gather(*[register(i) for i in range(10)])

    failures = [r.text for r in responses if r.status_code != 201]
    assert not failures, f"Some registrations failed: {failures}"

    ids = [r.json()["user"]["id"] for r in responses]
    assert len(set(ids)) == 10, f"Duplicate IDs produced: {ids}"


@pytest.mark.asyncio
async def test_sequential_registrations_increment(client: AsyncClient):
    """Sequential registrations produce monotonically increasing IDs."""

    async def register(i: int):
        fake_token = f"s{i:02d}_bypass_ratelimit_for_sequential_tests_padd"
        return await client.post(
            "/api/auth/register",
            headers={"Authorization": f"Bearer {fake_token}"},
            json={
                "email": f"seq{i}@test.com",
                "password": _STRONG_PASSWORD,
                "username": f"sequser{i}",
                "gender": "female",
            },
        )

    responses = []
    for i in range(5):
        r = await register(i)
        assert r.status_code == 201, r.text
        responses.append(r)

    ids = [r.json()["user"]["id"] for r in responses]
    assert ids == sorted(ids), f"IDs are not in ascending order: {ids}"
    assert len(set(ids)) == 5, f"Duplicate IDs: {ids}"
