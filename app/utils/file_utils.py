"""Upload validation and safe file storage."""
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

MSG_UNSUPPORTED = "Only PDF and DOCX files are supported."
MSG_EMPTY = "The uploaded file is empty."
MSG_CORRUPTED = "Unable to read this file. Please upload a valid resume."


class FileValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_extension(filename: Optional[str]) -> str:
    if not filename:
        raise FileValidationError(MSG_UNSUPPORTED)
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(MSG_UNSUPPORTED)
    return ext


def validate_content(content: bytes, ext: str) -> None:
    """Check size, emptiness and the file signature (magic bytes)."""
    if len(content) == 0:
        raise FileValidationError(MSG_EMPTY)
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise FileValidationError(f"File is too large. Maximum size is {settings.MAX_UPLOAD_MB} MB.", 413)
    if ext == ".pdf" and not content.lstrip().startswith(b"%PDF"):
        raise FileValidationError(MSG_CORRUPTED)
    if ext == ".docx" and not content.startswith(b"PK"):
        raise FileValidationError(MSG_CORRUPTED)


def display_name(filename: str) -> str:
    """Original file name cleaned for display (no path parts or odd characters)."""
    base = os.path.basename(filename.replace("\\", "/"))
    return re.sub(r"[^A-Za-z0-9._ \-()]", "_", base)[:200] or "resume"


def save_file(content: bytes, ext: str) -> str:
    """Store the file under a random unique name and return that name."""
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    (settings.UPLOAD_DIR / stored_name).write_bytes(content)
    return stored_name


def delete_file(stored_name: str) -> None:
    try:
        (settings.UPLOAD_DIR / os.path.basename(stored_name)).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Could not delete %s: %s", stored_name, exc)
