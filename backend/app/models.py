from pydantic import BaseModel, field_validator, model_validator, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

MAX_MATCHES = 5

# --- P3FT.13: roommate group sizing ---
GROUP_MIN_SIZE = 2
GROUP_MAX_SIZE = 4

ALLOWED_LIFESTYLE_TAGS = frozenset({
    "Early Bird", "Night Owl", "Fitness", "Studying", "Gaming",
    "Greek Life", "Homebody", "Outdoors", "Music", "Pet Lover",
    "Sports", "Art", "Reading", "Party/Going Out", "Film/TV",
})

# --- P3FT.14: prompt-style profile answers ---
#
# SINGLE SOURCE OF TRUTH.  The frontend must not hardcode a second copy of this
# list — it is served verbatim by `GET /api/profile-prompts`.  Ids are stable
# snake_case strings and must never be renamed or reused; add new prompts by
# appending, and retire one by removing it from this list (stored answers whose
# promptId is no longer present are simply not rendered).
PROFILE_PROMPTS = [
    {"id": "ideal_saturday", "text": "My ideal Saturday looks like…"},
    {"id": "need_in_roommate", "text": "The one thing I need in a roommate is…"},
    {"id": "usually_find_me", "text": "You'll usually find me…"},
    {"id": "biggest_pet_peeve", "text": "My biggest pet peeve at home is…"},
    {"id": "roommate_would_describe_me", "text": "A roommate would describe me as…"},
    {"id": "my_study_style", "text": "My study style is…"},
    {"id": "guests_policy_view", "text": "My view on having people over is…"},
    {"id": "morning_or_night", "text": "Morning person or night owl? Honestly…"},
    {"id": "cleaning_style", "text": "When it comes to cleaning, I'm the type who…"},
    {"id": "shared_food_view", "text": "On sharing food and groceries, I think…"},
    {"id": "weekend_plans", "text": "A typical weekend for me is…"},
    {"id": "music_taste", "text": "What's always playing in my room…"},
    {"id": "stress_relief", "text": "When I'm stressed during finals, I…"},
    {"id": "favorite_spot_on_campus", "text": "My favorite spot on campus is…"},
    {"id": "cooking_habits", "text": "In the kitchen, I'm usually…"},
    {"id": "noise_when_studying", "text": "When I study I need…"},
    {"id": "pet_situation", "text": "My situation with pets is…"},
    {"id": "thermostat_preference", "text": "I keep the thermostat at…"},
    {"id": "conflict_style", "text": "When something's bothering me, I…"},
    {"id": "one_thing_to_know", "text": "One thing you should know about me is…"},
]

PROFILE_PROMPT_IDS = frozenset(p["id"] for p in PROFILE_PROMPTS)

MAX_PROMPT_ANSWERS = 3
PROMPT_ANSWER_MAX_LENGTH = 150

# --- Preference ---

class Preference(BaseModel):
    value: float = Field(..., ge=0.0, le=24.0)  # sleep scores go 0-24; other scores 0-10
    isDealBreaker: bool

# --- P3FT.10: Housing intent ---

HousingType = Literal["on-campus", "off-campus", "either"]
LeaseTerm = Literal["fall", "spring", "summer", "full-year"]
MoveInSeason = Literal["Spring", "Summer", "Fall"]

BUDGET_MIN_USD = 0
BUDGET_MAX_USD = 5000


class HousingIntentFields(BaseModel):
    """P3FT.10 — optional housing-intent profile fields.

    Mixed into both `UserCreate` (used by `POST /users` and `PUT /users/{id}`)
    and `RegisterRequest`.  Every field is optional so existing profiles and
    signup flows that do not send them keep working.
    """
    housingType: Optional[HousingType] = None
    preferredLocation: Optional[str] = Field(None, max_length=60)
    budgetMin: Optional[int] = Field(None, ge=BUDGET_MIN_USD, le=BUDGET_MAX_USD)
    budgetMax: Optional[int] = Field(None, ge=BUDGET_MIN_USD, le=BUDGET_MAX_USD)
    leaseTerm: Optional[LeaseTerm] = None
    moveInSeason: Optional[MoveInSeason] = None
    moveInYear: Optional[int] = Field(None, ge=2025, le=2035)

    @field_validator("preferredLocation", mode="before")
    @classmethod
    def strip_preferred_location_html(cls, v):
        # None means "not supplied" (dropped by exclude_none on update);
        # an explicit empty string clears the stored value.
        if v is None:
            return None
        import nh3
        return nh3.clean(str(v), tags=set()).strip()

    @model_validator(mode="after")
    def validate_budget_range(self):
        if (
            self.budgetMin is not None
            and self.budgetMax is not None
            and self.budgetMin > self.budgetMax
        ):
            raise ValueError("budgetMin cannot be greater than budgetMax")
        return self

# --- P3FT.14: prompt answers ---

class PromptAnswer(BaseModel):
    """One answered profile prompt.  Display-only — never scored."""
    promptId: str = Field(..., max_length=64)
    answer: str = Field(..., min_length=1, max_length=PROMPT_ANSWER_MAX_LENGTH)

    @field_validator("promptId", mode="before")
    @classmethod
    def validate_prompt_id(cls, v):
        if not isinstance(v, str):
            raise ValueError("promptId must be a string")
        v = v.strip()
        if v not in PROFILE_PROMPT_IDS:
            raise ValueError(f"Unknown promptId: {v}")
        return v

    @field_validator("answer", mode="before")
    @classmethod
    def strip_answer_html(cls, v):
        if v is None:
            raise ValueError("answer is required")
        import nh3
        cleaned = nh3.clean(str(v), tags=set()).strip()
        if not cleaned:
            raise ValueError("answer cannot be empty")
        if len(cleaned) > PROMPT_ANSWER_MAX_LENGTH:
            raise ValueError(
                f"answer cannot exceed {PROMPT_ANSWER_MAX_LENGTH} characters"
            )
        return cleaned


class ProfilePromptOut(BaseModel):
    """Shape returned by `GET /api/profile-prompts`."""
    id: str
    text: str


class PromptAnswerFields(BaseModel):
    """P3FT.14 mixin — optional `promptAnswers` on create/register/update.

    `None` means "not supplied" (dropped by `exclude_none` on profile update, so
    an omitted field never wipes stored answers).  An explicit `[]` clears them.
    """
    promptAnswers: Optional[List[PromptAnswer]] = None

    @field_validator("promptAnswers", mode="after")
    @classmethod
    def validate_prompt_answers(cls, v):
        if v is None:
            return None
        if len(v) > MAX_PROMPT_ANSWERS:
            raise ValueError(
                f"At most {MAX_PROMPT_ANSWERS} prompt answers are allowed"
            )
        seen = set()
        for answer in v:
            if answer.promptId in seen:
                raise ValueError(f"Duplicate promptId: {answer.promptId}")
            seen.add(answer.promptId)
        return v


# --- User Models ---

class UserCreate(HousingIntentFields, PromptAnswerFields):
    username: str = Field(..., min_length=1, max_length=30, pattern=r'^[A-Za-z0-9_-]+$')
    email: Optional[str] = None
    password: Optional[str] = None
    gender: Literal["male", "female"]
    bio: Optional[str] = Field("", max_length=500)
    photoUrl: Optional[str] = ""
    lifestyleTags: Optional[List[str]] = Field(default_factory=list, max_length=10)
    religionTag: Optional[str] = None
    major: Optional[str] = None
    graduationSeason: Optional[str] = None
    graduationYear: Optional[int] = None
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
#
# `ConfirmedMatch` was removed here (P3D.2).  It modelled the `matches`
# collection but had no importer, no route, and no test — and it declared
# `compatibilityScore` as a required float while every stored document lacked
# the field, so the first code to actually use it would have raised
# ValidationError on real data.  A model that has never validated the schema it
# claims to describe is a trap rather than documentation.  The authoritative
# shape of a `matches` document now lives in the schema notes in `database.py`;
# `likeService.send_like` is what writes those documents.

# --- Recommendation Models ---

class RecommendationMatch(BaseModel):
    user_id: int
    compatibilityScore: float

class TopMatchesResponse(BaseModel):
    userId: int
    matches: list[RecommendationMatch]
    # P3FT.16 — how many candidates the discover filters removed.  Only present
    # when at least one filter query param was supplied (the route is declared
    # with `response_model_exclude_none=True`), so the unfiltered response shape
    # is byte-for-byte what it always was.
    filteredOut: Optional[int] = None


# --- P3FT.16: Discover filters ---

GRAD_YEAR_MIN = 2000
GRAD_YEAR_MAX = 2100


class DiscoverFilters(BaseModel):
    """Optional query params on `GET /users/{id}/top-matches`.

    Bound as a FastAPI query-parameter model, so any invalid value is a 422
    before the handler body runs.  `major` and `tags` are repeatable and use OR
    semantics within themselves; every filter ANDs with every other filter.
    """
    model_config = {"extra": "forbid"}

    major: Optional[List[str]] = Field(None, max_length=20)
    gradYearMin: Optional[int] = Field(None, ge=GRAD_YEAR_MIN, le=GRAD_YEAR_MAX)
    gradYearMax: Optional[int] = Field(None, ge=GRAD_YEAR_MIN, le=GRAD_YEAR_MAX)
    tags: Optional[List[str]] = Field(None, max_length=10)
    religion: Optional[str] = Field(None, max_length=60)
    housingType: Optional[HousingType] = None
    budgetMax: Optional[int] = Field(None, ge=BUDGET_MIN_USD, le=BUDGET_MAX_USD)
    minScore: Optional[float] = Field(None, ge=0, le=100)

    @field_validator("major", mode="before")
    @classmethod
    def clean_majors(cls, v):
        if v is None:
            return None
        import nh3
        cleaned = [nh3.clean(str(m), tags=set()).strip() for m in v]
        cleaned = [m for m in cleaned if m]
        return cleaned or None

    @field_validator("religion", mode="before")
    @classmethod
    def clean_religion(cls, v):
        if v is None:
            return None
        import nh3
        cleaned = nh3.clean(str(v), tags=set()).strip()
        return cleaned or None

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        if v is None:
            return None
        import nh3
        cleaned = []
        for tag in v:
            tag = nh3.clean(str(tag), tags=set()).strip()
            if not tag:
                continue
            if tag not in ALLOWED_LIFESTYLE_TAGS:
                raise ValueError(f"Invalid lifestyle tag: {tag}")
            cleaned.append(tag)
        return cleaned or None

    @model_validator(mode="after")
    def validate_grad_year_range(self):
        if (
            self.gradYearMin is not None
            and self.gradYearMax is not None
            and self.gradYearMin > self.gradYearMax
        ):
            raise ValueError("gradYearMin cannot be greater than gradYearMax")
        return self

    def is_active(self) -> bool:
        """True when at least one filter was supplied."""
        return any(
            getattr(self, name) is not None for name in self.__class__.model_fields
        )

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

# --- Block / Report Models ---

class ReportReason(str, Enum):
    harassment = "harassment"
    inappropriate_content = "inappropriate_content"
    fake_profile = "fake_profile"
    spam = "spam"
    underage = "underage"
    other = "other"


class ReportCreate(BaseModel):
    reason: ReportReason
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("description", mode="before")
    @classmethod
    def strip_description_html(cls, v):
        if v is None:
            return None
        import nh3
        return nh3.clean(str(v), tags=set())


# --- Deletion Models ---

class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=128)


class DeactivateRequest(BaseModel):
    password: str = Field(..., max_length=128)


class RestoreAccountRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=128)


class ResolveReportRequest(BaseModel):
    resolution: str = Field(..., min_length=1, max_length=500)
    status: Literal["actioned", "dismissed"] = "actioned"


# --- Age Verification Models ---

class SubmitAgeRequest(BaseModel):
    dateOfBirth: str = Field(..., description="ISO date string YYYY-MM-DD")


# --- Terms of Service Models ---

class AcceptTermsRequest(BaseModel):
    termsVersion: str  # e.g. "2026-06-03"


# --- Feedback Models ---

class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


# --- Conversation Report Models ---

class ConversationReportCreate(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ResolveConversationReport(BaseModel):
    action: Literal["dismiss", "ban"]  # "ban" bans the reported user


# --- P3FT.11: Compatibility Score Breakdown ---

class MatchBreakdownCategory(BaseModel):
    key: str
    label: str
    yourValue: float
    # Bucketed distance instead of the other user's raw value (privacy).
    difference: Literal["same", "close", "different"]
    score: float
    isDealBreaker: bool
    dealBreakerTriggered: bool


class MatchBreakdownResponse(BaseModel):
    compatibilityScore: float
    categories: List[MatchBreakdownCategory]


# --- P3FT.12: "Found a roommate" ---

class RoommateFoundRequest(BaseModel):
    partnerIds: List[int] = Field(default_factory=list, max_length=MAX_MATCHES)
    viaApp: bool = True

    @field_validator("partnerIds", mode="before")
    @classmethod
    def normalize_partner_ids(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("partnerIds must be a list of integers")
        seen = []
        for pid in v:
            if isinstance(pid, bool) or not isinstance(pid, int):
                raise ValueError("partnerIds must be a list of integers")
            if pid not in seen:
                seen.append(pid)
        return seen


# --- P3FT.13: Roommate Groups ---

class GroupCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=40)
    maxSize: int = Field(GROUP_MAX_SIZE, ge=GROUP_MIN_SIZE, le=GROUP_MAX_SIZE)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name_html(cls, v):
        if v is None:
            return None
        import nh3
        cleaned = nh3.clean(str(v), tags=set()).strip()
        return cleaned or None


class GroupInviteRespondRequest(BaseModel):
    action: Literal["accept", "decline"]


# --- Notification Models ---

class NotificationResponse(BaseModel):
    id: str
    type: str  # "like_received", "match_created", "unmatch"
    fromUser: int
    toUser: int
    message: str
    read: bool
    createdAt: datetime
