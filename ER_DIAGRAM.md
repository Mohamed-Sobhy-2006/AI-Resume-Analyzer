# Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ RESUMES : "uploads"
    RESUMES ||--o{ RESUME_ANALYSES : "has"
    RESUMES ||--o{ JOB_MATCHES : "is matched in"
    JOBS ||--o{ JOB_MATCHES : "is matched in"

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        datetime created_at
    }
    RESUMES {
        int id PK
        int user_id FK
        string filename
        string file_path
        text extracted_text
        datetime uploaded_at
    }
    RESUME_ANALYSES {
        int id PK
        int resume_id FK
        string candidate_name
        string candidate_email
        string candidate_phone
        text summary
        json technical_skills
        json soft_skills
        json education
        json experience
        json projects
        json certifications
        json strengths
        json weaknesses
        json missing_skills
        json improvements
        boolean ai_generated
        string notice
        datetime created_at
    }
    JOBS {
        int id PK
        string title
        string company
        string location
        text description
        json required_skills
        string experience_level
        string job_type
        datetime created_at
        datetime updated_at
    }
    JOB_MATCHES {
        int id PK
        int resume_id FK
        int job_id FK
        int match_score
        json matched_skills
        json missing_skills
        text explanation
        datetime created_at
    }
    LEARNING_RESOURCES {
        int id PK
        string title
        string type
        string skill
        text description
        string url
    }
```

## Notes
* One user has many resumes; one resume can be analysed several times (history is kept, the latest is shown).
* `JOB_MATCHES` is the link table between resumes and jobs and stores the deterministic score.
* Deleting a user, resume or job cascades to its dependent rows (`ON DELETE CASCADE` + ORM cascade).
* `LEARNING_RESOURCES` is a reference table (also indexed by the RAG pipeline); it is linked to skills by the
  `skill` name, not by a foreign key, because skills are a vocabulary and not a table in this project.
* List-like fields (skills, strengths ...) use SQLAlchemy's `JSON` type, which SQLite stores as text.
