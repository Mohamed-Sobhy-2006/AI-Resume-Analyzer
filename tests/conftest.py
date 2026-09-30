import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["GEMINI_API_KEY"] = ""          # tests must never call the real AI service

from app.config import settings  # noqa: E402

settings.GEMINI_API_KEY = ""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI test client with a fresh in-memory SQLite database and a temporary upload folder."""
    for module in ("fastapi", "sqlalchemy", "httpx", "multipart"):
        pytest.importorskip(module)
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import models  # noqa: F401
    from app.database import Base, get_db
    from app.main import app

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(client, email="student@example.com", password="secret123", name="Test Student"):
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password,
                                            "confirm_password": password})
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture()
def auth_headers(client):
    return register_and_login(client)
