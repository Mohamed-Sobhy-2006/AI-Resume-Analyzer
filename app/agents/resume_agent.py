"""AGENT 1 - Resume Analyzer Agent.

Input : resume text
Output: structured analysis dict (summary, skills, education, experience, projects,
        certifications, strengths, weaknesses, missing skills, improvements ...)

Path A (Gemini configured): the LLM analyses the resume and returns JSON.
Path B (fallback)         : keyword/rule based analysis (services/resume_analyzer.py).
The result is always validated so the rest of the app receives a clean structure.
"""
import logging

from app.services.llm_service import LLMError, llm_service
from app.services.resume_analyzer import keyword_analysis
from app.services.skills_catalog import canonical_skill

logger = logging.getLogger(__name__)

LIST_FIELDS = ["technical_skills", "soft_skills", "education", "experience", "projects", "certifications",
               "strengths", "weaknesses", "missing_skills", "improvements"]
MAX_RESUME_CHARS = 12000

SYSTEM_PROMPT = (
    "You are a Resume Analyzer Agent. Analyse the resume text and answer with ONE JSON object only. "
    "Use only facts that appear in the resume. Never invent employers, degrees or skills."
)

USER_PROMPT = """Analyse this resume and return JSON with exactly these keys:
candidate_name (string), candidate_email (string), candidate_phone (string), summary (2-3 sentences),
technical_skills (list of strings), soft_skills (list), education (list of short strings),
experience (list of short strings), projects (list), certifications (list),
strengths (list), weaknesses (list),
missing_skills (list of skills commonly required for the candidate's most likely target job that are NOT in the resume),
improvements (list of concrete resume improvement suggestions).
Use empty lists/strings when information is absent.

RESUME:
\"\"\"
{resume}
\"\"\""""


def _clean_list(value, limit=15):
    if not isinstance(value, list):
        return []
    out, seen = [], set()
    for item in value:
        text = str(item).strip() if not isinstance(item, dict) else ", ".join(str(v) for v in item.values() if v)
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
        if len(out) >= limit:
            break
    return out


class ResumeAnalyzerAgent:
    def __init__(self, llm=None):
        self.llm = llm or llm_service

    def run(self, resume_text: str) -> dict:
        baseline = keyword_analysis(resume_text)     # always computed: deterministic facts + fallback
        result = dict(baseline)
        result["ai_generated"] = False
        result["notice"] = ""
        try:
            ai = self.llm.generate_json(USER_PROMPT.format(resume=resume_text[:MAX_RESUME_CHARS]),
                                        system=SYSTEM_PROMPT)
            result = self._merge(baseline, ai)
        except LLMError as exc:
            logger.warning("Resume analysis fallback used: %s", exc)
            result["notice"] = f"{exc.user_message} Showing keyword-based analysis instead."
        except Exception as exc:  # any unexpected LLM-side problem must not break the API
            logger.exception("Unexpected error in Resume Analyzer Agent: %s", exc)
            result["notice"] = "AI service is unavailable. Showing keyword-based analysis instead."
        return result

    @staticmethod
    def _merge(baseline: dict, ai: dict) -> dict:
        merged = {"ai_generated": True, "notice": "", "target_role": baseline.get("target_role", "")}
        # Contact facts: prefer the deterministic regex values, fall back to the LLM values.
        merged["candidate_name"] = baseline["candidate_name"] or str(ai.get("candidate_name") or "").strip()
        merged["candidate_email"] = baseline["candidate_email"] or str(ai.get("candidate_email") or "").strip()
        merged["candidate_phone"] = baseline["candidate_phone"] or str(ai.get("candidate_phone") or "").strip()
        merged["summary"] = str(ai.get("summary") or "").strip() or baseline["summary"]
        for field in LIST_FIELDS:
            values = _clean_list(ai.get(field))
            if field == "technical_skills":      # union: LLM skills + keyword-detected skills
                values = _clean_list([canonical_skill(v) for v in values + baseline[field]], 30)
            merged[field] = values or baseline[field]
        have = {s.lower() for s in merged["technical_skills"]}
        merged["missing_skills"] = [s for s in merged["missing_skills"] if canonical_skill(s).lower() not in have]
        merged["missing_skills"] = [canonical_skill(s) for s in merged["missing_skills"]] or baseline["missing_skills"]
        return merged
