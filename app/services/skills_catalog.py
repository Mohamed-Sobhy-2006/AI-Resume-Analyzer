"""Skill vocabulary used for keyword extraction and for normalising skill names.

Each canonical skill maps to a list of aliases (lower-case). Job required skills,
resume skills and missing skills are all compared using the canonical names.
"""
import re

TECHNICAL_SKILLS = {
    "Python": ["python"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "REST APIs": ["rest api", "rest apis", "restful", "restful api", "restful apis"],
    "Git": ["git", "github", "gitlab"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Cloud": ["cloud", "cloud computing"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Linux": ["linux", "ubuntu", "bash"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "github actions", "jenkins"],
    "Testing": ["pytest", "unit testing", "unittest", "test automation"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "neural network", "neural networks"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "image processing"],
    "OpenCV": ["opencv"],
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "Keras": ["keras"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Data Visualization": ["data visualization", "data visualisation", "matplotlib", "seaborn"],
    "Statistics": ["statistics", "statistical analysis"],
    "Excel": ["Excel"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "LLMs": ["llm", "llms", "large language model", "large language models"],
    "RAG": ["rag", "retrieval-augmented generation", "retrieval augmented generation"],
    "Prompt Engineering": ["prompt engineering"],
    "Hugging Face": ["hugging face", "huggingface", "transformers"],
    "LangChain": ["langchain"],
    "MLOps": ["mlops"],
    "MLflow": ["mlflow"],
    "Spark": ["Spark", "PySpark"],
    "Airflow": ["airflow"],
    "MongoDB": ["mongodb"],
    "Redis": ["redis"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Java": ["java"],
    "C++": ["c++"],
    "C#": ["c#"],
    "Agile": ["agile", "scrum"],
}

SOFT_SKILLS = {
    "Communication": ["communication", "communicating"],
    "Teamwork": ["teamwork", "team player", "collaboration", "collaborative"],
    "Leadership": ["leadership", "led a team", "team lead"],
    "Problem Solving": ["problem solving", "problem-solving"],
    "Critical Thinking": ["critical thinking", "analytical thinking", "analytical skills"],
    "Time Management": ["time management"],
    "Adaptability": ["adaptability", "adaptable", "fast learner", "quick learner"],
    "Creativity": ["creativity", "creative"],
    "Presentation": ["presentation skills", "public speaking", "presenting"],
    "Project Management": ["project management"],
}

# A specific cloud provider satisfies a generic "Cloud" requirement.
IMPLIED_SKILLS = {"Cloud": {"AWS", "Azure", "GCP"}}

# Typical skills for common target roles - used by the keyword fallback to find missing skills.
ROLE_PROFILES = {
    "Backend Developer": ["Python", "FastAPI", "SQL", "REST APIs", "Git", "Docker", "Testing", "Linux"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "scikit-learn", "Deep Learning", "PyTorch",
                                  "Pandas", "NumPy", "Docker", "MLOps"],
    "Data Scientist": ["Python", "Statistics", "Pandas", "NumPy", "Machine Learning", "SQL",
                       "Data Visualization", "scikit-learn"],
    "Data Analyst": ["SQL", "Excel", "Data Analysis", "Data Visualization", "Power BI", "Tableau",
                     "Python", "Statistics"],
    "AI Engineer": ["Python", "LLMs", "RAG", "NLP", "Prompt Engineering", "FastAPI", "Docker", "Deep Learning"],
    "Software Engineer": ["Python", "Git", "SQL", "Testing", "Docker", "REST APIs", "Agile"],
}

_ALIAS_TO_CANONICAL = {}
for _canon, _aliases in list(TECHNICAL_SKILLS.items()) + list(SOFT_SKILLS.items()):
    _ALIAS_TO_CANONICAL[_canon.lower()] = _canon
    for _a in _aliases:
        _ALIAS_TO_CANONICAL.setdefault(_a, _canon)


def canonical_skill(name: str) -> str:
    """Map any alias ('sklearn', 'FASTAPI') to its canonical name; unknown skills are kept trimmed."""
    cleaned = " ".join(str(name).split())
    return _ALIAS_TO_CANONICAL.get(cleaned.lower(), cleaned)


# Common English words that are also skill names: match them case-sensitively ("Excel", not "excel in ...").
CASE_SENSITIVE = {"Excel", "Spark"}


def _pattern(alias: str, ignore_case: bool = True):
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", flags)


def _build_patterns(catalog: dict) -> dict:
    result = {}
    for canon, aliases in catalog.items():
        if canon in CASE_SENSITIVE:
            result[canon] = [_pattern(a, False) for a in aliases]
        else:
            result[canon] = [_pattern(a) for a in aliases + [canon.lower()]]
    return result


_TECH_PATTERNS = _build_patterns(TECHNICAL_SKILLS)
_SOFT_PATTERNS = _build_patterns(SOFT_SKILLS)


def _extract(text: str, patterns: dict) -> list:
    return [canon for canon, pats in patterns.items() if any(p.search(text) for p in pats)]


def extract_technical_skills(text: str) -> list:
    return _extract(text, _TECH_PATTERNS)


def extract_soft_skills(text: str) -> list:
    return _extract(text, _SOFT_PATTERNS)


def infer_target_role(skills: list) -> str:
    """Pick the role profile that overlaps most with the candidate's skills."""
    have = {canonical_skill(s) for s in skills}
    best_role, best_score = "Software Engineer", 0
    for role, needed in ROLE_PROFILES.items():
        score = sum(1 for s in needed if s in have)
        if score > best_score:
            best_role, best_score = role, score
    return best_role


def role_missing_skills(skills: list, role: str) -> list:
    have = {canonical_skill(s) for s in skills}
    return [s for s in ROLE_PROFILES.get(role, []) if s not in have]
