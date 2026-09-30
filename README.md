# AI Resume Analyzer

A web application that analyzes uploaded resumes, recommends jobs with an explainable score, and gives
career advice grounded in a knowledge base. It uses **three AI agents** and a **real RAG pipeline**.
Backend: Python + FastAPI + SQLite (SQLAlchemy). Frontend: plain HTML, CSS and JavaScript (no frameworks).

## 1. Features
* Register / login / logout (JWT, PBKDF2-hashed passwords)
* Upload PDF or DOCX resumes (type, size, empty and corrupted-file checks, safe unique file names)
* **Resume Analyzer Agent** - skills, education, experience, projects, certifications, strengths, weaknesses, missing skills, improvements
* **Job Matching Agent** - deterministic score `matched required skills / total required skills x 100`, matched/missing skills, explanation
* **Career Advisor Agent** - RAG retrieval first, then recommended skills, certifications, learning resources, roadmap, resume tips, free-form questions
* Job CRUD + search (title, company, location, skill, experience level, job type)
* Dashboard with resume count, latest analysis, top matches, missing skills and recommendations
* Works **without** a Gemini API key (clear "AI service is not configured" messages + fallback logic)

## 2. Architecture
```
Browser (HTML/CSS/JS)  ->  FastAPI routers  ->  Agents  ->  Services  ->  SQLite / Knowledge base
                                              |- ResumeAnalyzerAgent  -> Gemini or keyword fallback
                                              |- JobMatchingAgent     -> deterministic score (+ Gemini explanation)
                                              '- CareerAdvisorAgent   -> RAG retrieval -> Gemini or KB fallback
```
FastAPI also serves the frontend, so you only run one program.

## 3. Technologies
Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2, pypdf, python-docx, python-dotenv, pytest, httpx,
Google Gemini (called through its REST API with the standard library - no SDK that could break), HTML/CSS/vanilla JS.

## 4. Project structure
```
app/            main.py, config.py, database.py, models.py, schemas.py, auth.py
  routers/      auth, resumes, analysis, jobs, recommendations, career   (REST endpoints)
  agents/       resume_agent.py, job_matching_agent.py, career_advisor_agent.py
  services/     resume_parser, resume_analyzer (fallback), job_matcher, rag_service, llm_service, skills_catalog, seed_service
  utils/        security.py (hashing + JWT), file_utils.py
frontend/       index, login, register, dashboard, resume, analysis, jobs, career (.html) + css/ + js/
data/           sample_jobs.json and knowledge_base/{jobs,skills,career_roadmaps,learning_resources,resume_guidelines}
scripts/        seed_data.py, build_rag.py
tests/          pytest tests
setup.bat  run.bat  requirements.txt  .env.example
```

## 5. Installation (Windows)
1. Install **Python 3.10 or newer** from python.org (tick *Add python.exe to PATH*).
2. Extract the ZIP, open the folder `AI-Resume-Analyzer`.
3. Double-click **setup.bat**. It creates the virtual environment (`venv`), installs `requirements.txt`, creates `.env`, the database, sample data and the RAG index.
4. Double-click **run.bat**.
5. Open http://127.0.0.1:8000 (API docs: http://127.0.0.1:8000/docs, ReDoc: /redoc).

Manual equivalent (Command Prompt):
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts\seed_data.py
python scripts\build_rag.py
uvicorn app.main:app --reload
```

## 6. Environment variables (`.env`)
| Variable | Meaning |
|---|---|
| `GEMINI_API_KEY` | Optional. Get a key at https://aistudio.google.com/apikey and paste it after `=`. Restart `run.bat`. |
| `GEMINI_MODEL` | Gemini model name (default `gemini-2.5-flash`; change it if Google retires that name). |
| `SECRET_KEY` | JWT signing secret. Leave empty: a random one is created in `data/.secret_key`. |
| `MAX_UPLOAD_MB` | Upload limit (default 5). |

Never commit `.env`; the ZIP contains only `.env.example`.

## 7. Database
SQLite file `resume_analyzer.db` in the project folder, created automatically. Tables: `users`, `resumes`, `resume_analyses`, `jobs`, `job_matches`, `learning_resources` (see `ER_DIAGRAM.md`). Delete the file to reset everything.

## 8. Seed data
`python scripts\seed_data.py` inserts 12 sample jobs and 19 learning resources if the tables are empty (safe to run repeatedly). The app also does this automatically on start-up.

## 9. RAG setup
`python scripts\build_rag.py` rebuilds the vector store (`data/vector_store/index.json`). The index is also built automatically if missing. Re-run it after editing knowledge-base files.

## 10. Running the tests
```
venv\Scripts\activate
pytest
```
Tests cover registration, duplicate registration, login, invalid login, resume upload, invalid/corrupted files, job CRUD, job search, deterministic matching, RAG retrieval, and fallback behaviour of the agents. Tests never call Gemini.

## 11. Troubleshooting
| Problem | Fix |
|---|---|
| `Python was not found` | Reinstall Python and tick *Add to PATH*, or use the `py` launcher. |
| `Address already in use` | Another program uses port 8000: close it or run `uvicorn app.main:app --port 8001`. |
| Pages say *AI service is not configured* | Normal without a key. Add `GEMINI_API_KEY` to `.env` and restart. |
| *AI service rejected the request* | Wrong key or model name. Check `GEMINI_API_KEY` / `GEMINI_MODEL`. |
| Upload says *Unable to read this file* | The file is corrupted, password-protected or a scanned image. Export a fresh PDF/DOCX. |
| Weird login state | Click Logout, or clear the browser's local storage. |
| Changed knowledge-base files | Run `python scripts\build_rag.py`. |

## 12. Demo workflow (5-10 minutes)
1. Open http://127.0.0.1:8000 -> **Register** -> you are logged in.
2. **Resume** -> upload a sample PDF/DOCX -> automatic analysis opens.
3. **Analysis**: contact info, technical/soft skills, education, experience, strengths, weaknesses, missing skills, improvements.
4. **Jobs -> Recommendations**: scores, matched/missing skills, explanations.
5. **Career Advisor**: click *Suggest what to learn*, then ask e.g. "How do I become a machine learning engineer?". Show the retrieved documents table (RAG), skills, certifications, resources, roadmap. Ask "What is the capital of France?" to show the safe no-context answer.
6. **Jobs -> Manage Jobs**: add, edit, delete a job. **Search Jobs**: filter by title/location/skill.
7. Open `/docs`, then `ER_DIAGRAM.md` and `EVALUATION_MAPPING.md`.

## 13. AI agents
* **Resume Analyzer Agent** (`app/agents/resume_agent.py`): asks Gemini for a JSON analysis, validates and merges it with deterministic facts (email, phone, name, keyword-detected skills). If Gemini is missing/failing/returns bad JSON it uses the keyword analysis in `services/resume_analyzer.py` and the UI shows a notice.
* **Job Matching Agent** (`app/agents/job_matching_agent.py`): the score comes only from `services/job_matcher.py`. Gemini may write the explanation for the top jobs; it can never change the numbers (proved by `test_agent_score_never_comes_from_llm`).
* **Career Advisor Agent** (`app/agents/career_advisor_agent.py`): retrieves knowledge-base chunks first. No relevant chunk -> returns *"The available knowledge base does not contain enough information to answer this question."* Otherwise Gemini answers using only that context; without Gemini the answer is assembled directly from the retrieved chunks and the learning-resources table.

## 14. RAG explanation
`Documents -> loading -> chunking -> embeddings -> vector store -> similarity search -> top-K -> LLM -> grounded answer`
* Documents: `data/knowledge_base/` (jobs, skills, career roadmaps, learning resources, resume guidelines).
* Loader/chunker/embedder/store/search: `app/services/rag_service.py`. Chunks are ~110 words with 20-word overlap.
* **Embeddings:** local TF-IDF vectors with hashed unigrams + bigrams (4096 dimensions), compared with cosine similarity. Titles are weighted higher.
* **Vector store:** one JSON file with sparse vectors. **Why not ChromaDB?** Chroma downloads an embedding model at first use, which needs internet and often fails on university networks; the local store has no downloads, is easy to explain and is unit-testable. The design (embed -> store -> similarity search -> top-K) is identical, so Chroma or Gemini embeddings could replace it later.
* Relevance guard: a chunk must reach a minimum similarity **and** contain at least half of the question's words, otherwise nothing is returned (no hallucination).
* Learning-resource URLs point to official documentation/certification pages. Please open them once before your demo, since websites change.

## 15. Evaluation mapping
See `EVALUATION_MAPPING.md` (mark-by-mark mapping and demo checklist).

## 16. Security notes
PBKDF2-SHA256 password hashing, HS256 JWT with expiry and logout revocation (in memory), Pydantic validation, ORM queries (no raw SQL), random file names, extension + signature + size checks, CORS limited to localhost, secrets only from environment variables, no stack traces returned to users. Job write endpoints require login; any logged-in user may manage jobs (kept simple on purpose).
