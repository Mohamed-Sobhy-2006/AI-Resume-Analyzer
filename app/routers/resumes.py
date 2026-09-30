"""FR-2: resume upload, list, view, delete."""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Resume, User
from app.schemas import MessageOut, ResumeOut
from app.services.resume_parser import ResumeParseError, extract_text
from app.utils.file_utils import (
    FileValidationError, delete_file, display_name, get_extension, save_file, validate_content,
)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])
logger = logging.getLogger(__name__)


def resume_to_out(resume: Resume) -> ResumeOut:
    return ResumeOut(id=resume.id, filename=resume.filename, uploaded_at=resume.uploaded_at,
                     word_count=len(resume.extracted_text.split()), extracted_text=resume.extracted_text)


def get_owned_resume(db: Session, resume_id: int, user: User) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED,
             summary="Upload a PDF or DOCX resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Validates extension, size and content, stores the file under a unique name, extracts the text."""
    try:
        ext = get_extension(file.filename)
        content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
        validate_content(content, ext)
    except FileValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    stored_name = save_file(content, ext)
    try:
        text = extract_text(stored_name, ext)
    except ResumeParseError as exc:
        delete_file(stored_name)
        raise HTTPException(status_code=400, detail=str(exc))

    resume = Resume(user_id=user.id, filename=display_name(file.filename), file_path=stored_name,
                    extracted_text=text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume_to_out(resume)


@router.get("", response_model=list[ResumeOut], summary="List my resumes")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.id.desc()).all()
    return [resume_to_out(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeOut, summary="View one resume and its extracted text")
def get_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return resume_to_out(get_owned_resume(db, resume_id, user))


@router.delete("/{resume_id}", response_model=MessageOut, summary="Delete a resume")
def delete_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    delete_file(resume.file_path)
    db.delete(resume)
    db.commit()
    return MessageOut(message="Resume deleted.")
