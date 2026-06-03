"""Shared test helpers: a full-featured sync→async MongoDB wrapper for new collections."""


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

    async def find_one_and_update(self, filter, update, return_document=None, **kwargs):
        """Simulate find_one_and_update with return_document=True behaviour."""
        self._collection.update_one(filter, update)
        return self._collection.find_one(filter)

    # --- synchronous find() → async cursor ---

    def find(self, filter=None, **kwargs):
        """Return an AsyncCursor directly (no await needed by callers)."""
        return AsyncCursor(self._collection.find(filter, **kwargs))

    # --- fallback ---

    def __getattr__(self, name):
        return getattr(self._collection, name)
