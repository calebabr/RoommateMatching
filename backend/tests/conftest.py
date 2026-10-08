"""
Conftest for the backend/tests/ directory.

Applies to all test files in this directory and subdirectories.

Two things happen here that the whole suite depends on, in this order:

1. MONGO_URL / MONGO_DB_NAME are forced to the isolated `roommatch_test`
   database *before* `app.database` is imported. That module builds its
   AsyncIOMotorClient at import time, so anything set later is too late and
   every collection resolves to the production `roommatch` database.

2. Every `*_collection` object on `app.database` is replaced with a
   synchronous pymongo collection behind an async-looking facade
   (`tests.helpers.FullAsyncMongoWrapper`) *before* any `app.routers.*` /
   `app.services.*` module is imported. Those modules use
   `from app.database import X`, which copies the reference at import time,
   so patching after the fact does not reach them.

   This is what keeps the suite off Motor entirely. A module-level Motor
   client binds itself to whichever event loop first touches it; FastAPI's
   sync `TestClient` creates and closes a fresh loop per instantiation, so
   the second test to run would hit `RuntimeError: Event loop is closed`.
   With no Motor in the picture there is no loop to close.
"""
import os
import sys

TEST_MONGO_URL = "mongodb://localhost:27017/"

# The test database is PER PROCESS.
#
# It used to be the single hard-coded name `roommatch_test`, shared by every
# pytest process on the machine -- including a teammate agent running their own
# subset at the same time. `setup_test_db_per_test` below empties EVERY
# collection before and after each test, so two concurrent runs delete each
# other's seeded fixtures mid-test. The symptom is a scattered spray of
# `401 {"detail": "User not found"}` and vanishing counter documents
# (`test_atomic_id` seeing ids [1, 1, 2, 2, 3]) whose count and identity change
# on every run: 11, 17, 24, 42, 59 and 65 failures were all observed from the
# same unmodified tree within a few minutes of each other.
#
# Proof it was cross-process and not flakiness inside the suite: a run of a
# single block-test file found users 1701/1702 in the database, and those ids
# are seeded only by `test_report.py`, which that run never executed.
#
# `ROOMMATCH_TEST_DB` overrides the name (must still be a `roommatch_test`
# prefix -- see the assertion below, which refuses to run against anything
# else and in particular against the real `roommatch` database).
TEST_DB_NAME = os.environ.get("ROOMMATCH_TEST_DB") or f"roommatch_test_{os.getpid()}"

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ["MONGO_URL"] = TEST_MONGO_URL
os.environ["MONGO_DB_NAME"] = TEST_DB_NAME

import pytest
import pytest_asyncio
from pymongo import MongoClient

# pytest.ini sets asyncio_default_fixture_loop_scope (needs >= 0.24) and
# asyncio_default_test_loop_scope (needs >= 0.26). pytest only *warns* about ini
# keys it does not recognise, so on an older pytest-asyncio the suite would run
# with per-test event loops and fail in confusing ways. Fail loudly instead.
_ASYNCIO_VERSION = tuple(
    int(p) for p in pytest_asyncio.__version__.split(".")[:2] if p.isdigit()
)
assert _ASYNCIO_VERSION >= (0, 26), (
    f"pytest-asyncio {pytest_asyncio.__version__} does not support the loop-scope "
    f"options in pytest.ini; install >= 0.26 (see requirements.txt)."
)

import app.database as _dbmod
from tests.helpers import FullAsyncMongoWrapper

# Hard stop: never let the suite touch the production database.
# The prefix check is a second gate on the `ROOMMATCH_TEST_DB` override -- the
# production database is `roommatch`, which does not carry this prefix.
assert TEST_DB_NAME.startswith("roommatch_test"), (
    f"Refusing to run: the test database name '{TEST_DB_NAME}' does not start "
    f"with 'roommatch_test'."
)
assert _dbmod.db.name == TEST_DB_NAME, (
    f"Tests are bound to the '{_dbmod.db.name}' database; refusing to run "
    f"against anything but '{TEST_DB_NAME}'."
)

_sync_client = MongoClient(TEST_MONGO_URL)
_sync_db = _sync_client[TEST_DB_NAME]

# Discovered from app.database rather than hard-coded, so a collection added by
# the Database Agent is picked up automatically instead of silently staying Motor.
COLLECTION_ATTRS = sorted(a for a in dir(_dbmod) if a.endswith("_collection"))
COLLECTION_NAMES = []

for _attr in COLLECTION_ATTRS:
    _motor_col = getattr(_dbmod, _attr)
    _name = getattr(_motor_col, "name", None)
    if _name is None:
        continue
    COLLECTION_NAMES.append(_name)
    setattr(_dbmod, _attr, FullAsyncMongoWrapper(_sync_db[_name]))

# Only now may modules that do `from app.database import ...` be imported.
import app.main  # noqa: E402  (pulls in every router and service)
import app.routers.authRoutes  # noqa: E402
import app.auth.dependencies  # noqa: E402

# Back-compat alias: several test modules refer to conftest.users_collection.
users_collection = _dbmod.users_collection

# Snapshot of every module-level `*_collection` alias across the app package,
# taken once the wrappers above are in place. Test modules routinely monkeypatch
# these; a fixture that forgets to restore one (or restores it after closing its
# own client) used to poison every test module that ran later. The autouse
# fixture below re-pins them before each test so a leak stays local.
_COLLECTION_SNAPSHOT = []
for _modname, _mod in list(sys.modules.items()):
    if _modname != "app" and not _modname.startswith("app."):
        continue
    for _a in dir(_mod):
        if _a.endswith("_collection"):
            _COLLECTION_SNAPSHOT.append((_mod, _a, getattr(_mod, _a)))

# test_api.py / test_api_v2.py are standalone manual scripts, not pytest
# modules: they read `sys.argv[1]` as a base URL and drive a *live* server over
# `requests`. Under pytest they collect as ~49 tests that all fail with
# MissingSchema because argv[1] is a pytest flag. Per .claude/agents/tests.md
# ("no tests that depend on external services being up") they are excluded from
# automated collection; run them by hand with
#     python tests/test_api.py http://localhost:8000/api
collect_ignore = ["test_api.py", "test_api_v2.py"]


@pytest.fixture
def test_db():
    """The synchronous `roommatch_test` database the app's collections point at.

    Every `app.database.*_collection` is a FullAsyncMongoWrapper over a
    collection in this database, so a test can seed and assert with plain
    pymongo and the API under test sees the same documents. No per-file
    monkeypatching required.
    """
    return _sync_db


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
    """Drop the test database once at session start and once at session end."""
    sync_client = MongoClient(TEST_MONGO_URL)
    try:
        sync_client.drop_database(TEST_DB_NAME)
    except Exception:
        pass
    sync_client.close()

    yield

    sync_client = MongoClient(TEST_MONGO_URL)
    try:
        sync_client.drop_database(TEST_DB_NAME)
    except Exception:
        pass
    sync_client.close()


@pytest.fixture(autouse=True)
def setup_test_db_per_test():
    """Empty *every* collection before and after each test.

    Previously this cleaned only `users`, so likes, matches, chat_messages,
    notifications, blocks, recommendations -- and now groups, group_invites
    and outcomes -- leaked between tests and between runs, making some tests
    alternate pass/fail depending on execution order and on leftover state
    from a previous process.

    Contents are deleted rather than the database dropped, so indexes created
    by migrate_indexes / app startup survive.
    """
    for _mod, _a, _orig in _COLLECTION_SNAPSHOT:
        if getattr(_mod, _a, None) is not _orig:
            setattr(_mod, _a, _orig)

    for name in COLLECTION_NAMES:
        _sync_db[name].delete_many({})

    yield

    for name in COLLECTION_NAMES:
        _sync_db[name].delete_many({})
