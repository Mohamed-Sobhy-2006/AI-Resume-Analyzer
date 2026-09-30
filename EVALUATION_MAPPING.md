# Evaluation Mapping (100 marks)

## Backend Development - 20 marks
* **Files:** `app/main.py`, `app/routers/*.py`, `app/schemas.py`, `app/auth.py`, `app/utils/*.py`, `app/config.py`
* **Features:** REST API under `/api/auth`, `/resumes`, `/analysis`, `/jobs`, `/recommendations`, `/career`; JWT authentication; Pydantic request/response models; correct HTTP codes (201, 400, 401, 404, 409, 413, 422); job CRUD + 6 search filters; upload handling; auto docs.
* **Demonstrate:** open `/docs` and `/redoc`; use *Authorize* with a token; run `POST /api/jobs`, `GET /api/jobs?title=python&location=cairo`; show a 401 without token and the 409 duplicate-email message.

## Frontend Development - 10 marks
* **Files:** `frontend/*.html`, `frontend/css/style.css`, `frontend/js/api.js` (reusable fetch functions), `auth.js`, `dashboard.js`, `resume.js`, `analysis.js`, `jobs.js`, `career.js`
* **Features:** 8 pages, vanilla JS only, cards/tables/forms/progress bars/alerts/loading spinners, 401 redirect to login, search filters, job add/edit/delete, served by FastAPI.
* **Demonstrate:** walk through the pages; open browser DevTools -> Network to show `fetch()` calls to `/api/...`; stop the server to show the friendly "Cannot reach the server" message.

## Database Design - 10 marks
* **Files:** `app/models.py`, `app/database.py`, `ER_DIAGRAM.md`, `app/services/seed_service.py`, `scripts/seed_data.py`
* **Features:** six tables with primary/foreign keys, unique email, cascade deletes, JSON columns, timestamps; SQLite + SQLAlchemy ORM; seed data (12 jobs, 19 learning resources).
* **Demonstrate:** show `ER_DIAGRAM.md` (Mermaid preview), open `resume_analyzer.db` in DB Browser for SQLite, delete a job and show its `job_matches` removed.

## Resume Analysis - 15 marks
* **Files:** `app/services/resume_parser.py` (pypdf + python-docx), `app/services/resume_analyzer.py` (rule-based fallback), `app/services/skills_catalog.py`, `app/utils/file_utils.py`, `app/routers/resumes.py`, `app/routers/analysis.py`
* **Features:** PDF/DOCX validation and text extraction; name, email, phone, technical and soft skills, education, experience, projects, certifications, summary, strengths, weaknesses, missing skills, improvements; results stored in `resume_analyses`; graceful errors for wrong/empty/corrupted files.
* **Demonstrate:** upload a PDF and a DOCX; try a `.txt` and a broken PDF to show the messages; show the *Analysis* page and the stored row in SQLite.

## AI Agents - 20 marks
* **Files:** `app/agents/resume_agent.py`, `app/agents/job_matching_agent.py`, `app/agents/career_advisor_agent.py`, `app/services/llm_service.py`, `app/services/job_matcher.py`
* **Features:** three separate agents with defined inputs/outputs; Gemini path + fallback path; JSON validation of LLM output; deterministic score (LLM only writes the explanation); handling of missing key, invalid key, timeout, malformed response.
* **Demonstrate:** run without a key (yellow "AI service is not configured" notice, app still works); add a key and re-run for AI output; show `job_matcher.calculate_match` and the test `test_agent_score_never_comes_from_llm`.

## RAG Implementation - 10 marks
* **Files:** `app/services/rag_service.py`, `scripts/build_rag.py`, `data/knowledge_base/**`, `app/agents/career_advisor_agent.py`
* **Features:** loader, chunking with overlap, embeddings, local vector store, cosine similarity, top-K retrieval, relevance guard, context injected into the prompt, grounded answer, exact "not enough information" response, sources shown in the UI.
* **Demonstrate:** run `python scripts\build_rag.py` (document/chunk counts); ask a career question and show the retrieval table; ask an off-topic question to show the refusal; edit a knowledge-base file, rebuild, ask again.

## Code Quality & Error Handling - 10 marks
* **Files:** whole `app/` (routers -> agents -> services separation), `app/main.py` (global handlers), `tests/`, `app/utils/security.py`
* **Features:** modular structure, docstrings, friendly validation messages, no stack traces to users, server-side logging, environment-based secrets, pytest suite for auth, resume, jobs, matching, RAG and agent fallbacks.
* **Demonstrate:** run `pytest`; submit invalid forms; show `.env.example` and `.gitignore`; show the logs in the `run.bat` window when an error happens.

## Documentation - 5 marks
* **Files:** `README.md`, `ER_DIAGRAM.md`, `EVALUATION_MAPPING.md`, `.env.example`, FastAPI `/docs`
* **Features:** beginner installation, troubleshooting, demo workflow, agents and RAG explanations, ER diagram, mapping.
* **Demonstrate:** open README sections and `/docs`.

---

## DEMO CHECKLIST
- [ ] `setup.bat` finished with [SUCCESS]; `run.bat` running
- [ ] (Optional) `GEMINI_API_KEY` set in `.env` and server restarted
- [ ] Open http://127.0.0.1:8000 and register, then log in
- [ ] Upload a sample resume (PDF and/or DOCX) - show extracted text
- [ ] Show analysis: skills (technical/soft), education, experience, strengths, weaknesses, missing skills, improvements
- [ ] Jobs -> Recommendations: scores, matched/missing skills, explanations
- [ ] Career Advisor: ask a question, show RAG retrieval table, skills, certifications, learning resources, roadmap
- [ ] Ask an off-topic question -> "The available knowledge base does not contain enough information..."
- [ ] Jobs -> Manage: add, edit, delete a job; Search Jobs with filters
- [ ] Open `/docs` and try an endpoint; show `ER_DIAGRAM.md`; run `pytest`
- [ ] Log out
