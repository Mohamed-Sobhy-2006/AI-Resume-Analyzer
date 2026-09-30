"""Career Advisor endpoints (RAG-grounded)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.career_advisor_agent import CareerAdvisorAgent
from app.auth import get_current_user
from app.database import get_db
from app.models import LearningResource, User
from app.routers.analysis import latest_analysis, run_and_store_analysis
from app.routers.recommendations import quick_matches
from app.routers.resumes import get_owned_resume
from app.schemas import CareerRequest, CareerResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/career", tags=["Career Advisor"])


@router.post("/advice", response_model=CareerResponse, summary="Ask the Career Advisor Agent")
def career_advice(data: CareerRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Retrieves top-K knowledge-base chunks (RAG) first, then answers using only that context."""
    resume = get_owned_resume(db, data.resume_id, user)
    analysis = latest_analysis(db, resume.id) or run_and_store_analysis(db, resume)
    missing = list(analysis.missing_skills or [])
    for match in quick_matches(db, analysis)[:3]:
        missing += [s for s in match.missing_skills if s not in missing]
    resources = [{"id": r.id, "title": r.title, "type": r.type, "skill": r.skill,
                  "description": r.description, "url": r.url} for r in db.query(LearningResource).all()]
    profile = {"technical_skills": analysis.technical_skills or [], "improvements": analysis.improvements or [],
               "summary": analysis.summary or ""}
    return CareerAdvisorAgent().run(profile, missing[:10], data.question, resources)


@router.get("/status", summary="AI and RAG status")
def career_status(user: User = Depends(get_current_user)):
    return {"ai_configured": llm_service.is_configured(), "rag": rag_service.status()}
