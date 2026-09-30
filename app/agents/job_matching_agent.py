"""AGENT 2 - Job Matching Agent.

Input : resume analysis + job description
Output: {"match_score", "matched_skills", "missing_skills", "explanation"}

The numeric score is ALWAYS calculated by deterministic code
(matched_required_skills / total_required_skills * 100). The LLM is only allowed to
write the human-readable explanation and can never change the numbers.
"""
import logging

from app.services.job_matcher import calculate_match, template_explanation
from app.services.llm_service import LLMError, llm_service

logger = logging.getLogger(__name__)


class JobMatchingAgent:
    def __init__(self, llm=None):
        self.llm = llm or llm_service

    def run(self, analysis: dict, job: dict, use_llm: bool = True) -> dict:
        result = calculate_match(analysis.get("technical_skills", []), job.get("required_skills", []))
        score, matched, missing = result["match_score"], result["matched_skills"], result["missing_skills"]
        explanation = template_explanation(job["title"], score, matched, missing)
        ai_generated = False
        if use_llm and self.llm.is_configured():
            prompt = (
                f"Job: {job['title']} at {job.get('company', '')}.\n"
                f"Match score (already calculated, do not change): {score}%.\n"
                f"Matched skills: {', '.join(matched) or 'none'}.\n"
                f"Missing skills: {', '.join(missing) or 'none'}.\n"
                f"Candidate summary: {analysis.get('summary', '')}\n\n"
                "Write a 2-3 sentence plain-text explanation of why this job does or does not fit the candidate "
                "and what to learn next. Mention only the skills listed above. Do not state a different percentage."
            )
            try:
                text = self.llm.generate(prompt, temperature=0.4).strip()
                if text:
                    explanation, ai_generated = text, True
            except LLMError as exc:
                logger.warning("Match explanation fallback used: %s", exc)
            except Exception as exc:
                logger.exception("Unexpected error in Job Matching Agent: %s", exc)
        return {"match_score": score, "matched_skills": matched, "missing_skills": missing,
                "explanation": explanation, "ai_generated": ai_generated}
