from motor.motor_asyncio import AsyncIOMotorClient
from app.models import User, Preference
from bson import ObjectId

class userProfile():
    def __init__(self):
        self.i = 0

    def getUserID(self, user):
        """
        Extracts the user ID from a user object.

        Parameters:
            user (dict): User profile object.

        Returns:
            int: The user's ID.
        """
        return user["id"]

    def initDB(self):
        """
        Initializes an empty user database.

        Parameters:
            None

        Returns:
            list: An empty list to store user records.
        """
        return []

    def addUser(self, userDB, name, passW, sleep, cleanliness, noiseTolerance, guests):
        """
        Adds a new user to the user database with preference information.

        Parameters:
            userDB (list): The user database list to add the user to.
            name (str): Username for the new user.
            passW (str): Password for the new user.
            sleep (tuple): Sleep schedule as [weekday_hours, weekend_hours].
            cleanliness (int): Cleanliness preference (0-10 scale).
            noiseTolerance (int): Noise tolerance preference (0-10 scale).
            guests (int): Guests frequency preference (0-10 scale).

        Returns:
            int: The ID assigned to the newly created user.

        Notes:
            Internally maintains an incrementing counter (self.i) for user IDs.
        """
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