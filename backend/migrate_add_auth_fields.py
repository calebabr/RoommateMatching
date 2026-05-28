"""
Migration: add hashed_password and email to existing users.

Existing users get a placeholder hashed_password (empty string) and an
auto-generated email derived from their username so the unique index can
be created without conflicts. Run once before deploying JWT auth.

Usage:
    cd backend
    python migrate_add_auth_fields.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "roommatch"


async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]

    cursor = users.find({"hashed_password": {"$exists": False}})
    updated = 0
    async for user in cursor:
        user_id = user["id"]
        username = user.get("username", f"user{user_id}")
        placeholder_email = f"{username.lower().replace(' ', '_')}_{user_id}@placeholder.roommatch"
        await users.update_one(
            {"id": user_id},
            {"$set": {
                "hashed_password": "",
                "email": placeholder_email,
            }}
        )
        updated += 1

    print(f"Migrated {updated} user(s).")

    # Create unique sparse index (no-op if it already exists)
    await users.create_index("email", unique=True, sparse=True)
    print("Unique index on 'email' ensured.")

    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
