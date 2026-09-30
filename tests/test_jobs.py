from tests.helpers import make_docx_bytes

JOB = {"title": "Python Developer", "company": "Acme", "location": "Cairo, Egypt", "description": "Build APIs.",
       "required_skills": ["python", "FastAPI", "sql"], "experience_level": "Junior", "job_type": "Full-time"}


def test_job_crud(client, auth_headers):
    created = client.post("/api/jobs", json=JOB, headers=auth_headers)
    assert created.status_code == 201
    job = created.json()
    assert job["required_skills"] == ["Python", "FastAPI", "SQL"]      # normalised names
    assert client.get(f"/api/jobs/{job['id']}").json()["title"] == "Python Developer"

    updated = client.put(f"/api/jobs/{job['id']}", json={"title": "Senior Python Developer"}, headers=auth_headers)
    assert updated.status_code == 200 and updated.json()["title"] == "Senior Python Developer"
    assert updated.json()["company"] == "Acme"

    assert client.delete(f"/api/jobs/{job['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404
    assert client.delete(f"/api/jobs/{job['id']}", headers=auth_headers).status_code == 404


def test_job_write_requires_login_and_validation(client, auth_headers):
    assert client.post("/api/jobs", json=JOB).status_code == 401
    assert client.post("/api/jobs", json={**JOB, "title": "  "}, headers=auth_headers).status_code == 422
    assert client.post("/api/jobs", json={"company": "X"}, headers=auth_headers).status_code == 422


def test_job_search_filters(client, auth_headers):
    client.post("/api/jobs", json=JOB, headers=auth_headers)
    client.post("/api/jobs", json={**JOB, "title": "Data Analyst", "location": "Riyadh", "company": "Gulf Data",
                                   "required_skills": ["SQL", "Excel"], "job_type": "Remote"}, headers=auth_headers)
    titles = lambda **params: [j["title"] for j in client.get("/api/jobs", params=params).json()]
    assert titles(title="python", location="cairo") == ["Python Developer"]
    assert titles(company="gulf") == ["Data Analyst"]
    assert titles(skill="fastapi") == ["Python Developer"]
    assert sorted(titles(skill="sql")) == ["Data Analyst", "Python Developer"]
    assert titles(job_type="remote") == ["Data Analyst"]
    assert len(titles(experience_level="junior")) == 2
    assert titles(title="does-not-exist") == []


def test_recommendations_use_deterministic_scores(client, auth_headers):
    client.post("/api/jobs", json={**JOB, "required_skills": ["Python", "FastAPI", "SQL", "Kubernetes"]}, headers=auth_headers)
    resume = client.post("/api/resumes/upload", headers=auth_headers,
                         files={"file": ("cv.docx", make_docx_bytes(), "application/octet-stream")}).json()
    matches = client.get(f"/api/recommendations/resume/{resume['id']}", headers=auth_headers).json()
    assert len(matches) == 1
    match = matches[0]
    assert match["match_score"] == 75                       # 3 of 4 required skills
    assert match["matched_skills"] == ["Python", "FastAPI", "SQL"] and match["missing_skills"] == ["Kubernetes"]
    assert "Kubernetes" in match["explanation"]


def test_dashboard_summary(client, auth_headers):
    empty = client.get("/api/recommendations/dashboard", headers=auth_headers).json()
    assert empty["resume_count"] == 0
    client.post("/api/jobs", json=JOB, headers=auth_headers)
    client.post("/api/resumes/upload", headers=auth_headers,
                files={"file": ("cv.docx", make_docx_bytes(), "application/octet-stream")})
    resume_id = client.get("/api/resumes", headers=auth_headers).json()[0]["id"]
    client.post(f"/api/analysis/resume/{resume_id}", headers=auth_headers)
    data = client.get("/api/recommendations/dashboard", headers=auth_headers).json()
    assert data["resume_count"] == 1 and data["highest_match_score"] == 100 and data["top_matches"]
