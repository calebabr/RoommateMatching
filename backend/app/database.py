from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "roommatch"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_collection = db["users"]
likes_collection = db["likes"]
matches_collection = db["matches"]
recommendations_collection = db["recommendations"]
clusters_collection = db["clusters"]
messages_collection = db["messages"]