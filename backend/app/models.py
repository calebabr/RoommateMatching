from pydantic import BaseModel, field_validator, Field
from typing import Optional, List, Literal
from datetime import datetime

MAX_MATCHES = 5

ALLOWED_LIFESTYLE_TAGS = frozenset({
    "Early Bird", "Night Owl", "Fitness", "Studying", "Gaming",
    "Greek Life", "Homebody", "Outdoors", "Music", "Pet Lover",
    "Sports", "Art", "Reading", "Party/Going Out", "Film/TV",
})

# --- Preference ---

class Preference(BaseModel):
    value: float = Field(..., ge=0.0, le=24.0)  # sleep scores go 0-24; other scores 0-10
    isDealBreaker: bool

# --- User Models ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, pattern=r'^[A-Za-z0-9_-]+$')
    email: Optional[str] = None
    password: Optional[str] = None
    gender: Literal["male", "female"]
    bio: Optional[str] = Field("", max_length=500)
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[List[str]] = Field(default_factory=list, max_length=10)
    sleepScoreWD: Preference
    sleepScoreWE: Preference
    cleanlinessScore: Preference
    noiseToleranceScore: Preference
    guestsScore: Preference
    personalityScore: Preference
    smokingScore: Preference
    sharedSpaceScore: Preference
    communicationScore: Preference

    @field_validator("bio", mode="before")
    @classmethod
    def strip_bio_html(cls, v):
        if v is None:
            return ""
        import nh3
        return nh3.clean(str(v), tags=set())

    @field_validator("lifestyleTags", mode="before")
    @classmethod
    def validate_lifestyle_tags(cls, v):
        if v is None:
            return []
        import nh3
        cleaned = []
        for tag in v:
            tag = nh3.clean(str(tag), tags=set()).strip()
            if tag not in ALLOWED_LIFESTYLE_TAGS:
                raise ValueError(f"Invalid lifestyle tag: {tag}")
            cleaned.append(tag)
        return cleaned

class UserResponse(BaseModel):
    id: int
    username: str = Field(..., max_length=30)
    email: Optional[str] = ""
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
    bio: Optional[str] = Field("", max_length=500)
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
    username: str = Field(..., max_length=30)
    email: Optional[str] = ""
    hashed_password: Optional[str] = ""
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
    bio: Optional[str] = Field("", max_length=500)
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
        def _pref(p, default=5.0):
            if p is None:
                return [default, False]
            return [p.value, p.isDealBreaker]

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
            "personality": _pref(self.personalityScore),
            "smoking": _pref(self.smokingScore, default=0.0),
            "sharedSpace": _pref(self.sharedSpaceScore),
            "communication": _pref(self.communicationScore),
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
    content: str = Field(..., min_length=1, max_length=1000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content_html(cls, v):
        import nh3
        return nh3.clean(str(v), tags=set())

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
