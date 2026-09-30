import json

import pytest

from app.agents.career_advisor_agent import DEFAULT_QUESTION, CareerAdvisorAgent
from app.agents.resume_agent import ResumeAnalyzerAgent
from app.config import settings
from app.services.llm_service import LLMBadResponse, parse_json_text
from app.services.rag_service import NO_CONTEXT_MESSAGE, RAGService, chunk_text, load_documents
from tests.helpers import SAMPLE_RESUME_LINES

RESOURCES = json.loads((settings.KNOWLEDGE_BASE_DIR / "learning_resources" / "resources.json").read_text())
ANALYSIS = {"technical_skills": ["Python", "SQL", "Git"], "improvements": ["Add a Projects section."]}


@pytest.fixture(scope="module")
def rag(tmp_path_factory):
    service = RAGService(index_path=tmp_path_factory.mktemp("rag") / "index.json")
    service.build_index()
    return service


def test_knowledge_base_has_all_categories():
    categories = {d["category"] for d in load_documents()}
    assert {"jobs", "skills", "career_roadmaps", "learning_resources", "resume_guidelines"} <= categories


def test_chunking_splits_long_text_with_overlap():
    text = "\n".join(f"line {i} " + "word " * 9 for i in range(40))
    chunks = chunk_text(text, max_words=50, overlap_words=12)
    assert len(chunks) > 3 and all(len(c.split()) <= 60 for c in chunks)
    assert chunks[0].splitlines()[-1] in chunks[1]           # overlap between neighbouring chunks


def test_similarity_search_returns_relevant_top_k(rag):
    docker = rag.retrieve("How do I learn Docker containers?", top_k=3)
    assert docker and docker[0]["title"].startswith("Docker") and len(docker) <= 3
    roadmap = rag.retrieve("machine learning engineer roadmap", top_k=2)
    assert "Machine Learning Engineer" in roadmap[0]["title"]
    ats = rag.retrieve("How do I write an ATS friendly resume?")
    assert ats[0]["category"] == "resume_guidelines"


def test_irrelevant_question_retrieves_nothing(rag):
    assert rag.retrieve("what is the capital of France") == []
    assert rag.retrieve("recipe for chocolate cake") == []


def test_career_advisor_is_grounded_and_uses_retrieved_context(rag):
    agent = CareerAdvisorAgent(rag=rag, llm=type("Off", (), {"is_configured": lambda self: False})())
    result = agent.run(ANALYSIS, ["FastAPI", "Docker"], "How do I become a backend developer?", RESOURCES)
    assert result["grounded"] and result["retrieved_context_count"] > 0 and result["sources"]
    assert result["recommended_skills"] == ["FastAPI", "Docker"]
    assert result["roadmap"] and result["learning_resources"]
    assert all(r["url"].startswith("https://") for r in result["learning_resources"])
    assert "not configured" in result["notice"]


def test_career_advisor_refuses_to_hallucinate(rag):
    agent = CareerAdvisorAgent(rag=rag, llm=type("Off", (), {"is_configured": lambda self: False})())
    result = agent.run(ANALYSIS, ["Docker"], "Who won the football world cup?", RESOURCES)
    assert result["answer"] == NO_CONTEXT_MESSAGE and result["grounded"] is False and result["roadmap"] == []


def test_career_advisor_generic_question_uses_missing_skills(rag):
    agent = CareerAdvisorAgent(rag=rag, llm=type("Off", (), {"is_configured": lambda self: False})())
    result = agent.run(ANALYSIS, ["Docker", "FastAPI"], DEFAULT_QUESTION, RESOURCES)
    assert result["grounded"] and result["retrieved_context_count"] > 0


class BadJsonLLM:
    def is_configured(self):
        return True

    def generate_json(self, prompt, system=""):
        raise LLMBadResponse("The AI service returned an unreadable answer.")


def test_malformed_llm_output_falls_back_gracefully(rag):
    resume = ResumeAnalyzerAgent(llm=BadJsonLLM()).run("\n".join(SAMPLE_RESUME_LINES))
    assert resume["ai_generated"] is False and "Python" in resume["technical_skills"] and "unreadable" in resume["notice"]
    advice = CareerAdvisorAgent(rag=rag, llm=BadJsonLLM()).run(ANALYSIS, ["Docker"], "How do I learn Docker?", RESOURCES)
    assert advice["grounded"] and advice["ai_generated"] is False


class GoodJsonLLM:
    def is_configured(self):
        return True

    def generate_json(self, prompt, system=""):
        return {"candidate_name": "Someone Else", "summary": "AI summary.", "technical_skills": ["python", "Rust"],
                "soft_skills": ["Teamwork"], "education": ["BSc"], "experience": [], "projects": [],
                "certifications": [], "strengths": ["Good"], "weaknesses": ["Short"], "missing_skills": ["Docker", "Python"],
                "improvements": ["Add metrics"]}


def test_ai_result_is_validated_and_merged_with_deterministic_facts():
    result = ResumeAnalyzerAgent(llm=GoodJsonLLM()).run("\n".join(SAMPLE_RESUME_LINES))
    assert result["ai_generated"] is True and result["summary"] == "AI summary."
    assert result["candidate_name"] == "Ahmed Hassan"            # regex fact wins over the LLM
    assert "Rust" in result["technical_skills"] and "FastAPI" in result["technical_skills"]
    assert "Python" not in result["missing_skills"]               # already owned skills are removed
    assert result["experience"]                                   # empty AI list -> keyword fallback


def test_json_parsing_handles_code_fences_and_garbage():
    assert parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_text('Here you go: {"a": 2} thanks') == {"a": 2}
    with pytest.raises(LLMBadResponse):
        parse_json_text("not json at all")
