"""Shared test helpers: a sync→async MongoDB wrapper plus user-document builders."""

# --- Preference / user-document builders (Phase 3) --------------------------

#: The nine scored categories as they are stored on a user document, keyed by
#: the field name UserInDB expects.
PREF_FIELDS = (
    "sleepScoreWD", "sleepScoreWE", "cleanlinessScore", "noiseToleranceScore",
    "guestsScore", "personalityScore", "smokingScore", "sharedSpaceScore",
    "communicationScore",
)


def pref(value: float, deal_breaker: bool = False) -> dict:
    return {"value": float(value), "isDealBreaker": bool(deal_breaker)}


def prefs(value: float = 5.0, deal_breaker: bool = False, **overrides) -> dict:
    """All nine preferences at `value`, with named per-field overrides.

    Overrides take either a raw number or an already-built {"value", ...} dict:
        prefs(5.0, cleanlinessScore=9.0)
        prefs(5.0, guestsScore=pref(1.0, deal_breaker=True))
    """
    out = {f: pref(value, deal_breaker) for f in PREF_FIELDS}
    out["smokingScore"] = pref(0.0, deal_breaker)
    for field, v in overrides.items():
        if field not in out:
            raise KeyError(f"{field} is not a preference field")
        out[field] = v if isinstance(v, dict) else pref(v)
    return out


def make_user(user_id: int, gender: str = "male", **overrides) -> dict:
    """A minimal but fully valid user document (passes UserInDB validation)."""
    doc = {
        "id": user_id,
        "username": f"user{user_id}",
        "email": f"user{user_id}@auburn.edu",
        "hashed_password": "",
        "gender": gender,
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
    }
    doc.update(prefs())
    doc.update(overrides)
    return doc


def auth_header(user_id: int) -> dict:
    """Bearer header for `user_id`. Also the slowapi rate-limit key, so distinct
    users get distinct limit buckets."""
    from app.auth.utils import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user_id)})}"}


def make_match(user_a: int, user_b: int) -> dict:
    return {"user1_id": user_a, "user2_id": user_b, "status": "confirmed"}


def declared_rate_limits(qualified_endpoint: str) -> list:
    """The slowapi limits declared on a route, e.g. "60 per 1 minute".

    `qualified_endpoint` is "<module>.<function>", the key slowapi uses in
    `limiter._route_limits` (e.g. "app.routers.groupRoutes.create_group").
    """
    from app.limiter import limiter
    import app.main  # noqa: F401 — ensures every router has been registered

    limits = limiter._route_limits.get(qualified_endpoint)
    if limits is None:
        raise AssertionError(
            f"No rate limit registered for {qualified_endpoint}; "
            f"known keys: {sorted(limiter._route_limits)}"
        )
    return [str(item.limit) for item in limits]




class AsyncCursor:
    """Async-iterable cursor wrapper over a synchronous pymongo cursor.

    Supports .sort(), .limit(), and .to_list() so it works with every
    service that calls:
        async for doc in collection.find(...)
        await collection.find(...).to_list(length=None)
        collection.find(...).sort(field, direction)
    """

    def __init__(self, sync_cursor):
        self._cursor = sync_cursor

    def sort(self, key_or_list, direction=None):
        if direction is not None:
            self._cursor = self._cursor.sort(key_or_list, direction)
        else:
            self._cursor = self._cursor.sort(key_or_list)
        return self

    def limit(self, n):
        self._cursor = self._cursor.limit(n)
        return self

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for doc in self._cursor:
            yield doc

    async def to_list(self, length=None):
        return list(self._cursor)


class FullAsyncMongoWrapper:
    """Drop-in async wrapper for a synchronous pymongo collection.

    Covers every method used by BlockService, ReportService, and DeletionService.
    find() is a *synchronous* method (not async def) so that
       async for doc in self.col.find({})
    works directly without an extra await.
    """

    def __init__(self, collection):
        self._collection = collection

    # --- async CRUD ---

    async def find_one(self, filter=None, **kwargs):
        return self._collection.find_one(filter, **kwargs)

    async def insert_one(self, document):
        return self._collection.insert_one(document)

    async def update_one(self, filter, update, **kwargs):
        return self._collection.update_one(filter, update, **kwargs)

    async def update_many(self, filter, update, **kwargs):
        return self._collection.update_many(filter, update, **kwargs)

    async def delete_many(self, filter):
        return self._collection.delete_many(filter)

    async def delete_one(self, filter):
        return self._collection.delete_one(filter)

    async def create_index(self, key_or_list, **kwargs):
        return self._collection.create_index(key_or_list, **kwargs)

    async def count_documents(self, filter=None, **kwargs):
        return self._collection.count_documents(filter or {}, **kwargs)

    async def find_one_and_update(self, filter, update, **kwargs):
        """Delegate to pymongo so `upsert` and `return_document` behave for real.

        The previous shim dropped both kwargs, which broke the atomic int-id
        counters in authRoutes._get_next_id and GroupService._next_id: with no
        upsert the first allocation found nothing to update and returned None.
        """
        return self._collection.find_one_and_update(filter, update, **kwargs)

    async def bulk_write(self, requests, **kwargs):
        return self._collection.bulk_write(requests, **kwargs)

    async def insert_many(self, documents, **kwargs):
        return self._collection.insert_many(documents, **kwargs)

    async def distinct(self, key, filter=None, **kwargs):
        return self._collection.distinct(key, filter, **kwargs)

    # --- synchronous find() → async cursor ---

    def find(self, filter=None, projection=None, **kwargs):
        """Return an AsyncCursor directly (no await needed by callers).

        Accepts an optional projection argument (second positional param in
        pymongo's Collection.find signature) so that routes calling
        collection.find({}, {"_id": 0}) work correctly.
        """
        if projection is not None:
            return AsyncCursor(self._collection.find(filter, projection, **kwargs))
        return AsyncCursor(self._collection.find(filter, **kwargs))

    def aggregate(self, pipeline, **kwargs):
        """Motor's aggregate() is synchronous and returns an async cursor."""
        return AsyncCursor(self._collection.aggregate(pipeline, **kwargs))

    # --- fallback ---

    def __getattr__(self, name):
        return getattr(self._collection, name)
