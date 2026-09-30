"""Pydantic request/response schemas (validation lives here)."""
import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.skills_catalog import canonical_skill

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
MIN_PASSWORD_LENGTH = 8


# ------------------------------------------------------------------ auth
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        if len(v) > 100:
            raise ValueError("Name is too long.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_PATTERN.match(v) or len(v) > 255:
            raise ValueError("Please enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        return v

    @model_validator(mode="after")
    def _passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Please enter a valid email address.")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageOut(BaseModel):
    message: str


# ------------------------------------------------------------------ resumes / analysis
class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    uploaded_at: Optional[datetime] = None
    word_count: int = 0
    extracted_text: str = ""


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resume_id: int
    candidate_name: str = ""
    candidate_email: str = ""
    candidate_phone: str = ""
    summary: str = ""
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    education: List[str] = []
    experience: List[str] = []
    projects: List[str] = []
    certifications: List[str] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    missing_skills: List[str] = []
    improvements: List[str] = []
    ai_generated: bool = False
    notice: str = ""
    created_at: Optional[datetime] = None


# ------------------------------------------------------------------ jobs
def _clean_skills(values: List[str]) -> List[str]:
    seen, out = set(), []
    for value in values:
        name = canonical_skill(value)
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


class JobBase(BaseModel):
    title: str = Field(..., max_length=200)
    company: str = Field(..., max_length=200)
    location: str = Field("", max_length=200)
    description: str = ""
    required_skills: List[str] = []
    experience_level: str = Field("", max_length=50)
    job_type: str = Field("", max_length=50)

    @field_validator("title", "company")
    @classmethod
    def _required_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title and company are required.")
        return v

    @field_validator("required_skills")
    @classmethod
    def _skills(cls, v: List[str]) -> List[str]:
        return _clean_skills(v)


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(None, max_length=50)
    job_type: Optional[str] = Field(None, max_length=50)

    @field_validator("title", "company")
    @classmethod
    def _not_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Title and company cannot be empty.")
        return v.strip() if v else v

    @field_validator("required_skills")
    @classmethod
    def _skills(cls, v):
        return _clean_skills(v) if v is not None else v


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    company: str
    location: str = ""
    description: str = ""
    required_skills: List[str] = []
    experience_level: str = ""
    job_type: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ------------------------------------------------------------------ recommendations / career
class MatchOut(BaseModel):
    job_id: int
    job_title: str
    company: str
    location: str = ""
    experience_level: str = ""
    job_type: str = ""
    description: str = ""
    match_score: int
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    explanation: str = ""


class CareerRequest(BaseModel):
    resume_id: int
    question: str = Field("", max_length=500)


class CareerResponse(BaseModel):
    answer: str
    recommended_skills: List[str] = []
    certifications: List[Any] = []
    learning_resources: List[Any] = []
    roadmap: List[str] = []
    resume_improvements: List[str] = []
    sources: List[Any] = []
    retrieved_context_count: int = 0
    grounded: bool = False
    ai_generated: bool = False
    notice: str = ""
