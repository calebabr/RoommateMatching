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
    # Original 5 preference categories
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference
    # New survey-driven preference categories
    personalityScore: Preference        # 0 = very introverted, 10 = very extroverted
    smokingScore: Preference             # 0 = no smoking/substances at all, 10 = frequent use is fine
    sharedSpaceScore: Preference         # 0 = very private / strict boundaries, 10 = fully communal
    communicationScore: Preference       # 0 = avoid confrontation, 10 = direct and upfront
    # Profile and lifestyle tags
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[list[str]] = []

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
    personalityScore: Preference
    smokingScore: Preference
    sharedSpaceScore: Preference
    communicationScore: Preference
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[list[str]] = []

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
    personalityScore: Preference = Preference(value=5, isDealBreaker=False)
    smokingScore: Preference = Preference(value=0, isDealBreaker=False)
    sharedSpaceScore: Preference = Preference(value=5, isDealBreaker=False)
    communicationScore: Preference = Preference(value=5, isDealBreaker=False)
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[list[str]] = []

    def toMatchDict(self):
        return {
            "id": self.id,
            "sleepScheduleWeekdays": [self.sleepScoreWD.value, self.sleepScoreWD.isDealBreaker],
            "sleepScheduleWeekends": [self.sleepScoreWE.value, self.sleepScoreWE.isDealBreaker],
            "cleanliness": [self.cleanlinessScore.value, self.cleanlinessScore.isDealBreaker],
            "noiseTolerance": [self.noiseToleranceScore.value, self.noiseToleranceScore.isDealBreaker],
            "guests": [self.guestsScore.value, self.guestsScore.isDealBreaker],
            "personality": [self.personalityScore.value, self.personalityScore.isDealBreaker],
            "smoking": [self.smokingScore.value, self.smokingScore.isDealBreaker],
            "sharedSpace": [self.sharedSpaceScore.value, self.sharedSpaceScore.isDealBreaker],
            "communication": [self.communicationScore.value, self.communicationScore.isDealBreaker],
            "lifestyleTags": self.lifestyleTags or [],
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

class RecommendationMatch(BaseModel):
    user_id: int
    compatibilityScore: float

class TopMatchesResponse(BaseModel):
    userId: int
    matches: list[RecommendationMatch]