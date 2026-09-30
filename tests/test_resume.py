import pytest

from app.config import settings
from app.services.resume_analyzer import keyword_analysis
from app.services.resume_parser import ResumeParseError, extract_text
from tests.helpers import SAMPLE_RESUME_LINES, make_docx_bytes, make_pdf_bytes

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---- parser (no web server needed)
def test_extract_text_from_docx_and_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    (tmp_path / "a.docx").write_bytes(make_docx_bytes())
    (tmp_path / "b.pdf").write_bytes(make_pdf_bytes())
    assert "FastAPI" in extract_text("a.docx", ".docx")
    assert "FastAPI" in extract_text("b.pdf", ".pdf")


def test_corrupted_file_gives_friendly_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(ResumeParseError) as info:
        extract_text("bad.pdf", ".pdf")
    assert "Unable to read this file" in str(info.value)


def test_keyword_analysis_extracts_information():
    result = keyword_analysis("\n".join(SAMPLE_RESUME_LINES))
    assert result["candidate_name"] == "Ahmed Hassan"
    assert result["candidate_email"] == "ahmed.hassan@example.com"
    assert "Python" in result["technical_skills"] and "FastAPI" in result["technical_skills"]
    assert "Teamwork" in result["soft_skills"]
    assert result["education"] and result["experience"] and result["projects"] and result["certifications"]
    assert result["strengths"] and result["missing_skills"] and result["improvements"]


# ---- API
def upload(client, headers, name, content, ctype="application/octet-stream"):
    return client.post("/api/resumes/upload", headers=headers, files={"file": (name, content, ctype)})


def test_upload_docx_and_pdf(client, auth_headers):
    docx = upload(client, auth_headers, "cv.docx", make_docx_bytes(), DOCX_TYPE)
    assert docx.status_code == 201 and "Python" in docx.json()["extracted_text"]
    pdf = upload(client, auth_headers, "cv.pdf", make_pdf_bytes(), "application/pdf")
    assert pdf.status_code == 201
    assert len(client.get("/api/resumes", headers=auth_headers).json()) == 2


def test_upload_rejects_invalid_files(client, auth_headers):
    wrong_type = upload(client, auth_headers, "notes.txt", b"hello world")
    assert wrong_type.status_code == 400 and wrong_type.json()["detail"] == "Only PDF and DOCX files are supported."
    empty = upload(client, auth_headers, "cv.pdf", b"")
    assert empty.status_code == 400 and "empty" in empty.json()["detail"]
    corrupted = upload(client, auth_headers, "cv.pdf", b"%PDF-1.4 broken broken broken")
    assert corrupted.status_code == 400 and "Unable to read this file" in corrupted.json()["detail"]
    fake_docx = upload(client, auth_headers, "cv.docx", b"this is plain text pretending to be docx")
    assert fake_docx.status_code == 400


def test_upload_rejects_large_file(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    response = upload(client, auth_headers, "cv.docx", make_docx_bytes())
    assert response.status_code == 413 and "too large" in response.json()["detail"]


def test_upload_requires_login(client):
    assert upload(client, {}, "cv.docx", make_docx_bytes()).status_code == 401


def test_resume_files_are_stored_with_safe_unique_names(client, auth_headers):
    upload(client, auth_headers, "../../evil name.docx", make_docx_bytes())
    stored = list(settings.UPLOAD_DIR.iterdir())
    assert len(stored) == 1 and stored[0].suffix == ".docx" and "evil" not in stored[0].name


def test_analysis_is_stored_and_uses_fallback_without_api_key(client, auth_headers):
    resume = upload(client, auth_headers, "cv.docx", make_docx_bytes()).json()
    created = client.post(f"/api/analysis/resume/{resume['id']}", headers=auth_headers)
    assert created.status_code == 201
    data = created.json()
    assert "Python" in data["technical_skills"] and data["ai_generated"] is False
    assert "not configured" in data["notice"]
    stored = client.get(f"/api/analysis/resume/{resume['id']}", headers=auth_headers).json()
    assert stored["id"] == data["id"] and stored["candidate_name"] == "Ahmed Hassan"


def test_user_cannot_read_another_users_resume(client, auth_headers):
    from tests.conftest import register_and_login
    resume = upload(client, auth_headers, "cv.docx", make_docx_bytes()).json()
    other = register_and_login(client, email="other@example.com")
    assert client.get(f"/api/resumes/{resume['id']}", headers=other).status_code == 404
