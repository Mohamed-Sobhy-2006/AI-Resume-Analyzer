"""Insert sample jobs and learning resources when the tables are empty (idempotent)."""
import json
import logging

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Job, LearningResource

logger = logging.getLogger(__name__)
JOBS_FILE = settings.BASE_DIR / "data" / "sample_jobs.json"
RESOURCES_FILE = settings.KNOWLEDGE_BASE_DIR / "learning_resources" / "resources.json"


def seed_database() -> dict:
    init_db()
    added = {"jobs": 0, "learning_resources": 0}
    db = SessionLocal()
    try:
        if db.query(Job).count() == 0 and JOBS_FILE.exists():
            for item in json.loads(JOBS_FILE.read_text(encoding="utf-8")):
                db.add(Job(**item))
                added["jobs"] += 1
        if db.query(LearningResource).count() == 0 and RESOURCES_FILE.exists():
            for item in json.loads(RESOURCES_FILE.read_text(encoding="utf-8")):
                db.add(LearningResource(**item))
                added["learning_resources"] += 1
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Seeding failed")
        raise
    finally:
        db.close()
    return added
