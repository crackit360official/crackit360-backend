# models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from typing import Literal
# =========================================================
# USER MODELS
# =========================================================

class UserBase(BaseModel):
    """Base fields shared across user schemas."""
    name: str
    email: EmailStr


class EmailRequest(BaseModel):
    user_email: str


class UserRegister(UserBase):
    """Model for user registration."""
    password: str


class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr
    password: str


class UserInDB(UserBase):
    """Model stored inside MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    password: str
    email_verified: bool = False
    refresh_tokens: Optional[List[dict]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# =========================================================
# AUTH RESPONSE MODELS
# =========================================================

class AuthUser(BaseModel):
    """Returned in Login & Google Login responses."""
    id: str
    name: str
    email: EmailStr
    auth_provider: str
    avatar: Optional[str] = ""


class TokenResponse(BaseModel):
    """Standard Authentication Response."""
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class MessageOnly(BaseModel):
    message: str


class PasswordResetResponse(BaseModel):
    message: str


# =========================================================
# PROFILE MODEL
# =========================================================

class Profile(BaseModel):
    name: str
    age: int


# =========================================================
# GENERIC RESPONSE
# =========================================================

class MessageResponse(BaseModel):
    message: str
    data: Optional[Any] = None


# =========================================================
# QUIZ SUBMISSION MODELS
# =========================================================

class QuizSubmissionPayload(BaseModel):
    userId: str
    userTrack: str  # If you remove track, tell me—I will update backend too
    answers: List[Optional[int]]
    timeTaken: int


class DailyQuizStudent(BaseModel):
    user_id: str
    user_name: str
    user_email: str
    track: str   # Same here—can be removed if not needed
    question_ids: List[str]
    selected_answers: List[int]
    correct_answers: List[int]
    score: float
    accuracy: float
    total_questions: int
    time_taken: int
    date: datetime = Field(default_factory=datetime.utcnow)


# =========================================================
# TECHNICAL QUESTIONS
# =========================================================

class Question(BaseModel):
    id: str
    title: str
    difficulty: str
    category: str
    description: str
    inputFormat: str
    outputFormat: str
    sampleInput: str
    sampleOutput: str
    explanation: str
    constraints: Optional[str]
    templates: Dict[str, str]


# =========================================================
# QUANTITATIVE QUESTIONS
# =========================================================

class SpeedTestQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    correctAnswer: str
    topic: str
    level: str
    difficulty: Optional[str] = None


class SubmitRequest(BaseModel):
    user_id: Optional[str]
    topic: str
    level: str
    answers: List[int]

# =========================================================
#                       Discussion                        #
# =========================================================
class DiscussionCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=10)
    category: str

class ReplyCreate(BaseModel):
    discussionId: str
    content: str




class VoteCreate(BaseModel):
    type: Literal["UPVOTE", "DOWNVOTE"]