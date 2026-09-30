"""FR-4: job recommendations (deterministic score + Job Matching Agent) and dashboard summary."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.job_matching_agent import JobMatchingAgent
from app.auth import get_current_user
from app.database import get_db
from app.models import Job, JobMatch, Resume, User
from app.routers.analysis import latest_analysis, run_and_store_analysis
from app.routers.resumes import get_owned_resume
from app.schemas import MatchOut
from app.services.job_matcher import calculate_match, template_explanation
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api/recommendations", tags=["Job Recommendations"])
AI_EXPLAIN_TOP_N = 3     # only the best jobs get a Gemini explanation (keeps the page fast)


def _to_out(job: Job, score, matched, missing, explanation) -> MatchOut:
    return MatchOut(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        location=job.location or "",
        experience_level=job.experience_level or "",
        job_type=job.job_type or "",
        description=job.description or "",
        match_score=score,
        matched_skills=matched,
        missing_skills=missing,
        explanation=explanation
    )


def quick_matches(db: Session, analysis) -> list:
    """Deterministic matches for all jobs WITHOUT saving anything (used by dashboard and career advisor)."""
    outs = []
    for job in db.query(Job).all():
        r = calculate_match(analysis.technical_skills or [], job.required_skills or [])
        outs.append(_to_out(job, r["match_score"], r["matched_skills"], r["missing_skills"],
                            template_explanation(job.title, r["match_score"], r["matched_skills"], r["missing_skills"])))
    return sorted(outs, key=lambda m: (-m.match_score, m.job_title))


def compute_and_store_matches(db: Session, resume: Resume, analysis) -> list:
    """Run the Job Matching Agent for every job and save the results in job_matches."""
    agent = JobMatchingAgent()
    profile = {"technical_skills": analysis.technical_skills or [], "summary": analysis.summary or ""}
    jobs = db.query(Job).all()
    results = []
    for job in jobs:
        job_data = {"title": job.title, "company": job.company, "required_skills": job.required_skills or []}
        results.append([job, job_data, agent.run(profile, job_data, use_llm=False)])
    results.sort(key=lambda item: (-item[2]["match_score"], item[0].title))
    if llm_service.is_configured():        # AI explanation for the best jobs; the score never changes
        for item in results[:AI_EXPLAIN_TOP_N]:
            ai = agent.run(profile, item[1], use_llm=True)
            item[2]["explanation"] = ai["explanation"]
            if not ai["ai_generated"]:
                break                       # AI failed once: stop calling it for the remaining jobs
    db.query(JobMatch).filter(JobMatch.resume_id == resume.id).delete()
    for job, _data, r in results:
        db.add(JobMatch(resume_id=resume.id, job_id=job.id, match_score=r["match_score"],
                        matched_skills=r["matched_skills"], missing_skills=r["missing_skills"],
                        explanation=r["explanation"]))
    db.commit()
    return [_to_out(job, r["match_score"], r["matched_skills"], r["missing_skills"], r["explanation"])
            for job, _data, r in results]


def stored_matches(db: Session, resume_id: int) -> list:
    rows = (db.query(JobMatch, Job).join(Job, Job.id == JobMatch.job_id)
            .filter(JobMatch.resume_id == resume_id).order_by(JobMatch.match_score.desc(), Job.title).all())
    return [_to_out(job, m.match_score, m.matched_skills or [], m.missing_skills or [], m.explanation or "")
            for m, job in rows]


@router.get("/resume/{resume_id}", response_model=list[MatchOut], summary="Recommended jobs for a resume")
def recommend_jobs(resume_id: int, refresh: bool = Query(False, description="Recalculate all matches"),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Score = matched required skills / total required skills x 100 (deterministic, never from the LLM)."""
    resume = get_owned_resume(db, resume_id, user)
    analysis = latest_analysis(db, resume.id) or run_and_store_analysis(db, resume)
    existing = [] if refresh else stored_matches(db, resume.id)
    if existing and len(existing) == db.query(Job).count():
        return existing
    return compute_and_store_matches(db, resume, analysis)


@router.get("/dashboard", summary="Summary numbers for the dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.id.desc()).all()
    data = {"resume_count": len(resumes), "latest_resume": None, "latest_analysis": None, "top_matches": [],
            "highest_match_score": 0, "missing_skills": [], "career_recommendations": [],
            "ai_configured": llm_service.is_configured()}
    if not resumes:
        return data
    resume = resumes[0]
    data["latest_resume"] = {"id": resume.id, "filename": resume.filename, "uploaded_at": resume.uploaded_at}
    analysis = latest_analysis(db, resume.id)
    if not analysis:
        return data
    data["latest_analysis"] = {"summary": analysis.summary, "technical_skills": analysis.technical_skills,
                               "strengths": analysis.strengths, "weaknesses": analysis.weaknesses,
                               "ai_generated": analysis.ai_generated}
    matches = stored_matches(db, resume.id) or quick_matches(db, analysis)
    data["top_matches"] = [m.model_dump() for m in matches[:3]]
    data["highest_match_score"] = matches[0].match_score if matches else 0
    missing = list(analysis.missing_skills or [])
    for m in matches[:3]:
        missing += [s for s in m.missing_skills if s not in missing]
    data["missing_skills"] = missing[:10]
    recs = list(analysis.improvements or [])[:3]
    recs += [f"Learn {s} to improve your job matches." for s in data["missing_skills"][:3]]
    data["career_recommendations"] = recs
    return data
