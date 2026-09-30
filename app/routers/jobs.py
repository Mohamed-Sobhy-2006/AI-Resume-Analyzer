"""FR-6 / FR-7: job CRUD and search. Reading is public; writing requires login."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Job, User
from app.schemas import JobCreate, JobOut, JobUpdate, MessageOut
from app.services.skills_catalog import canonical_skill

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, summary="Add a job")
def create_job(data: JobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = Job(**data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut], summary="List / search jobs")
def list_jobs(
    title: Optional[str] = Query(None, description="Partial title, e.g. python"),
    company: Optional[str] = None,
    location: Optional[str] = Query(None, description="Partial location, e.g. cairo"),
    skill: Optional[str] = Query(None, description="A required skill, e.g. docker"),
    experience_level: Optional[str] = None,
    job_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """All filters are optional, case-insensitive and can be combined."""
    query = db.query(Job)
    for column, value in ((Job.title, title), (Job.company, company), (Job.location, location),
                          (Job.experience_level, experience_level), (Job.job_type, job_type)):
        if value and value.strip():
            query = query.filter(column.ilike(f"%{value.strip()}%"))
    jobs = query.order_by(Job.id.desc()).all()
    if skill and skill.strip():
        wanted = canonical_skill(skill).lower()
        jobs = [j for j in jobs if any(wanted in s.lower() for s in (j.required_skills or []))]
    return jobs


@router.get("/{job_id}", response_model=JobOut, summary="View one job")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.put("/{job_id}", response_model=JobOut, summary="Edit a job")
def update_job(job_id: int, data: JobUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", response_model=MessageOut, summary="Delete a job")
def delete_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    db.delete(job)
    db.commit()
    return MessageOut(message="Job deleted.")
