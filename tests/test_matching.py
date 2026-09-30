from app.agents.job_matching_agent import JobMatchingAgent
from app.services.job_matcher import calculate_match, normalize_skills, template_explanation
from app.services.llm_service import LLMUnavailable


def test_score_formula_is_matched_over_required():
    result = calculate_match(["Python", "FastAPI", "SQL"], ["Python", "FastAPI", "SQL", "Docker"])
    assert result["match_score"] == 75
    assert result["matched_skills"] == ["Python", "FastAPI", "SQL"]
    assert result["missing_skills"] == ["Docker"]


def test_score_boundaries():
    assert calculate_match(["Python"], ["Python"])["match_score"] == 100
    assert calculate_match([], ["Python", "SQL"])["match_score"] == 0
    assert calculate_match(["Python"], [])["match_score"] == 0
    assert calculate_match(["Python"], ["Python", "SQL", "Docker"])["match_score"] == 33
    assert calculate_match(["Python", "SQL"], ["Python", "SQL", "Docker"])["match_score"] == 67


def test_skill_names_are_normalised():
    assert normalize_skills(["python", "PYTHON", " sklearn ", "fastapi", ""]) == ["Python", "scikit-learn", "FastAPI"]
    assert calculate_match(["sklearn", "PYTHON"], ["scikit-learn", "Python"])["match_score"] == 100


def test_specific_cloud_provider_satisfies_generic_cloud():
    assert calculate_match(["AWS"], ["Cloud"])["match_score"] == 100
    assert calculate_match(["Cloud"], ["AWS"])["match_score"] == 0


def test_explanation_mentions_matched_and_missing_skills():
    text = template_explanation("Backend Dev", 75, ["Python"], ["Docker"])
    assert "75%" in text and "Python" in text and "Docker" in text


class FakeLLM:
    """Pretends to be Gemini and tries to cheat by inventing a different score."""
    def is_configured(self):
        return True

    def generate(self, prompt, **kwargs):
        return "This job fits because of Python. The real score is 99%."


class BrokenLLM(FakeLLM):
    def generate(self, prompt, **kwargs):
        raise LLMUnavailable("AI service is unavailable (network problem or timeout).")


ANALYSIS = {"technical_skills": ["Python", "SQL"], "summary": "Junior developer."}
JOB = {"title": "Backend Developer", "company": "Acme", "required_skills": ["Python", "SQL", "Docker", "Git"]}


def test_agent_score_never_comes_from_llm():
    result = JobMatchingAgent(llm=FakeLLM()).run(ANALYSIS, JOB)
    assert result["match_score"] == 50                    # deterministic, not 99
    assert result["ai_generated"] is True and "Python" in result["explanation"]


def test_agent_falls_back_when_llm_fails_or_is_missing():
    broken = JobMatchingAgent(llm=BrokenLLM()).run(ANALYSIS, JOB)
    assert broken["match_score"] == 50 and broken["ai_generated"] is False
    assert "Docker" in broken["explanation"]
    no_llm = JobMatchingAgent(llm=FakeLLM()).run(ANALYSIS, JOB, use_llm=False)
    assert no_llm["ai_generated"] is False
