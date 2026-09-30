"""Central configuration. All secrets come from environment variables (.env)."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PLACEHOLDER_KEYS = {"", "your_api_key_here", "changeme", "change_me"}


def _load_secret_key() -> str:
    """Use SECRET_KEY from env, otherwise create and reuse a random key file."""
    key = os.getenv("SECRET_KEY", "").strip()
    if key and key not in PLACEHOLDER_KEYS:
        return key
    key_file = BASE_DIR / "data" / ".secret_key"
    try:
        if key_file.exists():
            return key_file.read_text().strip()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_hex(32)
        key_file.write_text(key)
        return key
    except OSError:
        return secrets.token_hex(32)


class Settings:
    BASE_DIR = BASE_DIR
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'resume_analyzer.db').as_posix()}")
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
    FRONTEND_DIR = BASE_DIR / "frontend"
    KNOWLEDGE_BASE_DIR = BASE_DIR / "data" / "knowledge_base"
    VECTOR_STORE_PATH = Path(os.getenv("VECTOR_STORE_PATH", str(BASE_DIR / "data" / "vector_store" / "index.json")))

    SECRET_KEY = _load_secret_key()
    TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "120"))

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}

    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.12"))

    CORS_ORIGINS = [
        "http://127.0.0.1:8000", "http://localhost:8000",
        "http://127.0.0.1:5500", "http://localhost:5500",
    ]

    @property
    def MAX_UPLOAD_BYTES(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


settings = Settings()
