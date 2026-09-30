"""Database tables (SQLAlchemy ORM). See ER_DIAGRAM.md for the diagram."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)      # original name shown to the user
    file_path = Column(String(500), nullable=False)     # safe unique name stored in uploads/
    extracted_text = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="resumes")
    analyses = relationship("ResumeAnalysis", back_populates="resume", cascade="all, delete-orphan",
                            order_by="ResumeAnalysis.id")
    matches = relationship("JobMatch", back_populates="resume", cascade="all, delete-orphan")


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_name = Column(String(200), default="")
    candidate_email = Column(String(255), default="")
    candidate_phone = Column(String(50), default="")
    summary = Column(Text, default="")
    technical_skills = Column(JSON, default=list)
    soft_skills = Column(JSON, default=list)
    education = Column(JSON, default=list)
    experience = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    improvements = Column(JSON, default=list)
    ai_generated = Column(Boolean, default=False)   # True when Gemini produced the analysis
    notice = Column(String(300), default="")        # e.g. "AI service is not configured..."
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="analyses")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    company = Column(String(200), nullable=False)
    location = Column(String(200), default="")
    description = Column(Text, default="")
    required_skills = Column(JSON, default=list)
    experience_level = Column(String(50), default="")
    job_type = Column(String(50), default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")


class JobMatch(Base):
    __tablename__ = "job_matches"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Integer, nullable=False)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    explanation = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    resume = relationship("Resume", back_populates="matches")
    job = relationship("Job", back_populates="matches")


class LearningResource(Base):
    __tablename__ = "learning_resources"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    type = Column(String(50), default="course")     # course | documentation | certification | tutorial
    skill = Column(String(100), default="", index=True)
    description = Column(Text, default="")
    url = Column(String(500), default="")
