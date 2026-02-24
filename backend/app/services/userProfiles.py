from motor.motor_asyncio import AsyncIOMotorClient
from app.models import User, Preference
from bson import ObjectId

class userProfile():
    def __init__(self):
        self.i = 0

    def getUserID(self, user):
        return user["id"]

    def initDB(self):
        return []

    def addUser(self, userDB, name, passW, sleep, cleanliness, noiseTolerance, guests):
        newUser = {
            "id": self.i,
            "username": name,
            "password": passW,
            "sleepScheduleWeekdays": sleep[0],
            "sleepScheduleWeekends": sleep[1],
            "cleanliness": cleanliness,
            "noiseTolerance": noiseTolerance,
            "guests": guests
        }
        userDB.append(newUser)
        self.i += 1
        return newUser["id"]