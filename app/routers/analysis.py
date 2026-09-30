"""FR-3: run the Resume Analyzer Agent and store / read the analysis."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.resume_agent import ResumeAnalyzerAgent
from app.auth import get_current_user
from app.database import get_db
from app.models import JobMatch, Resume, ResumeAnalysis, User
from app.routers.resumes import get_owned_resume
from app.schemas import AnalysisOut

router = APIRouter(prefix="/api/analysis", tags=["Resume Analysis"])

STORED_FIELDS = ["candidate_name", "candidate_email", "candidate_phone", "summary", "technical_skills",
                 "soft_skills", "education", "experience", "projects", "certifications", "strengths",
                 "weaknesses", "missing_skills", "improvements", "ai_generated", "notice"]


def latest_analysis(db: Session, resume_id: int):
    return (db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id)
            .order_by(ResumeAnalysis.id.desc()).first())


def run_and_store_analysis(db: Session, resume: Resume) -> ResumeAnalysis:
    """Run the agent, save the result and drop job matches that were based on the old analysis."""
    result = ResumeAnalyzerAgent().run(resume.extracted_text)
    analysis = ResumeAnalysis(resume_id=resume.id, **{k: result.get(k) for k in STORED_FIELDS})
    db.query(JobMatch).filter(JobMatch.resume_id == resume.id).delete()
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/resume/{resume_id}", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED,
             summary="Analyze a resume with the Resume Analyzer Agent")
def analyze_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Uses Gemini when configured, otherwise the keyword-based fallback. The result is stored in SQLite."""
    resume = get_owned_resume(db, resume_id, user)
    return run_and_store_analysis(db, resume)


@router.get("/resume/{resume_id}", response_model=AnalysisOut, summary="Get the latest stored analysis")
def get_analysis(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_owned_resume(db, resume_id, user)
    analysis = latest_analysis(db, resume_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="This resume has not been analyzed yet.")
    return analysis
