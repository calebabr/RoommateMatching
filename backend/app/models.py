from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

MAX_MATCHES = 5

# --- Preference ---

class Preference(BaseModel):
    value: float
    isDealBreaker: bool

# --- User Models ---

class UserCreate(BaseModel):
    username: str
    gender: str  # "male" or "female"
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[List[str]] = []
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference
    personalityScore: Optional[Preference] = None
    smokingScore: Optional[Preference] = None
    sharedSpaceScore: Optional[Preference] = None
    communicationScore: Optional[Preference] = None

class UserResponse(BaseModel):
    id: int
    username: str
    gender: str
    matched: bool
    matchCount: int = 0
    matchedWith: List[int] = []

    @field_validator('matchedWith', mode='before')
    @classmethod
    def normalize_matched_with(cls, v):
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        if isinstance(v, list):
            return [x for x in v if x is not None]
        return []

    @field_validator('matchCount', mode='before')
    @classmethod
    def normalize_match_count(cls, v):
        if v is None:
            return 0
        return v
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[List[str]] = []
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference
    personalityScore: Optional[Preference] = None
    smokingScore: Optional[Preference] = None
    sharedSpaceScore: Optional[Preference] = None
    communicationScore: Optional[Preference] = None

class UserInDB(BaseModel):
    id: int
    username: str
    gender: str = "male"
    matched: bool = False
    matchCount: int = 0
    matchedWith: List[int] = []

    @field_validator('matchedWith', mode='before')
    @classmethod
    def normalize_matched_with(cls, v):
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        if isinstance(v, list):
            return [x for x in v if x is not None]
        return []

    @field_validator('matchCount', mode='before')
    @classmethod
    def normalize_match_count(cls, v):
        if v is None:
            return 0
        return v
    bio: Optional[str] = ""
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[List[str]] = []
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference
    personalityScore: Optional[Preference] = None
    smokingScore: Optional[Preference] = None
    sharedSpaceScore: Optional[Preference] = None
    communicationScore: Optional[Preference] = None

    def toMatchDict(self):
        return {
            "id": self.id,
            "gender": self.gender,
            "matchedWith": self.matchedWith,
            "matchCount": self.matchCount,
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

class RecommendationMatch(BaseModel):
    user_id: int
    compatibilityScore: float

class TopMatchesResponse(BaseModel):
    userId: int
    matches: list[RecommendationMatch]

# --- Chat Models ---

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: str
    fromUser: int
    toUser: int
    content: str
    createdAt: datetime

# --- Notification Models ---

class NotificationResponse(BaseModel):
    id: str
    type: str  # "like_received", "match_created", "unmatch"
    fromUser: int
    toUser: int
    message: str
    read: bool
    createdAt: datetime
