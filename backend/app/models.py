from pydantic import BaseModel, Field
from typing import List, Tuple

class Preference(BaseModel):
    value: float
    isDealBreaker: bool

class User(BaseModel):
    id: int
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference

    def toDict(self):
        return {
            "id": self.id,
            "sleepScheduleWeekdays": [self.sleepScoreWD.value, self.sleepScoreWD.isDealBreaker],
            "sleepScheduleWeekends": [self.sleepScoreWE.value, self.sleepScoreWE.isDealBreaker],
            "cleanliness": [self.cleanlinessScore.value, self.cleanlinessScore.isDealBreaker],
            "noiseTolerance": [self.noiseToleranceScore.value, self.noiseToleranceScore.isDealBreaker],
            "guests": [self.guestsScore.value, self.guestsScore.isDealBreaker],
        }

class UserDB(BaseModel):
    users: list[User]

    def toDict(self):
        return {user.id: user.toDict() for user in self.users}

class MatchScoreRequest(BaseModel):
    user1_id: int
    user2_id: int

class MatchResult(BaseModel):
    user1_id: int
    user2_id: int
    compatibilityScore: float

class MatchListResult(BaseModel):
    matches: list[MatchResult]
    unmatched_users: list[int]