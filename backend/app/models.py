from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Preference ---

class Preference(BaseModel):
    value: float
    isDealBreaker: bool

# --- User Models ---

class UserCreate(BaseModel):
    username: str
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference

class UserResponse(BaseModel):
    id: int
    username: str
    matched: bool
    matchedWith: Optional[int] = None
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference

class UserInDB(BaseModel):
    id: int
    username: str
    matched: bool = False
    matchedWith: Optional[int] = None
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference

    def toMatchDict(self):
        return {
            "id": self.id,
            "sleepScheduleWeekdays": [self.sleepScoreWD.value, self.sleepScoreWD.isDealBreaker],
            "sleepScheduleWeekends": [self.sleepScoreWE.value, self.sleepScoreWE.isDealBreaker],
            "cleanliness": [self.cleanlinessScore.value, self.cleanlinessScore.isDealBreaker],
            "noiseTolerance": [self.noiseToleranceScore.value, self.noiseToleranceScore.isDealBreaker],
            "guests": [self.guestsScore.value, self.guestsScore.isDealBreaker],
        }

class UserDB(BaseModel):
    users: list[UserInDB]

    def toDict(self):
        return {user.id: user.toMatchDict() for user in self.users}

# --- Match Score Models ---

class MatchScoreRequest(BaseModel):
    user1_id: int
    user2_id: int

class MatchResult(BaseModel):
    user1_id: int
    user2_id: int
    compatibilityScore: float

class MatchRequest(BaseModel):
    user1: UserInDB
    user2: UserInDB

class MatchListResult(BaseModel):
    matches: list[MatchResult]
    unmatched_users: list[int]

# --- Like Models ---

class LikeRequest(BaseModel):
    toUser: int

class LikeResponse(BaseModel):
    status: str
    matchedWith: Optional[int] = None
    likedUser: Optional[int] = None

class Like(BaseModel):
    fromUser: int
    toUser: int
    createdAt: Optional[datetime] = None

# --- Confirmed Match Models ---

class ConfirmedMatch(BaseModel):
    user1_id: int
    user2_id: int
    compatibilityScore: float
    confirmedAt: Optional[datetime] = None

# --- Recommendation Models ---

class TopMatchesResponse(BaseModel):
    userId: int
    matches: list[MatchResult]

class RecommendationMatch(BaseModel):
    user_id: int
    compatibilityScore: float

