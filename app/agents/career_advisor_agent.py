"""AGENT 3 - Career Advisor Agent (RAG-grounded).

Input : resume analysis + missing skills + question
Steps : 1) RETRIEVE top-K context from the knowledge base (RAG)
        2) if nothing relevant is found -> return the "not enough information" message
        3) otherwise GENERATE the answer from that context only
           (Gemini if available, otherwise a fallback built directly from the retrieved chunks)
"""
import logging
import re

from app.services.llm_service import LLMError, llm_service
from app.services.rag_service import NO_CONTEXT_MESSAGE, RAGService, rag_service
from app.services.skills_catalog import canonical_skill, infer_target_role

logger = logging.getLogger(__name__)

DEFAULT_QUESTION = "What should I learn next to improve my career prospects?"
# Skills whose certifications are usually valuable for each target role (matched against the learning_resources table).
ROLE_CERT_SKILLS = {
    "Backend Developer": ["cloud", "python"], "Software Engineer": ["python", "cloud"],
    "Machine Learning Engineer": ["machine learning", "deep learning", "cloud"],
    "Data Scientist": ["machine learning", "data analysis", "python"],
    "Data Analyst": ["data analysis", "power bi"], "AI Engineer": ["machine learning", "cloud"],
}
STAGE_RE = re.compile(r"^(Stage|Step|Phase)\s*\d", re.IGNORECASE)

SYSTEM_PROMPT = (
    "You are a Career Advisor Agent. Answer ONLY with information found in the CONTEXT. "
    "If the context does not contain the answer, set answer to exactly: " + NO_CONTEXT_MESSAGE + " "
    "Never invent courses, certifications or links. Reply with ONE JSON object only."
)

USER_PROMPT = """CONTEXT (retrieved from the knowledge base):
{context}

CANDIDATE PROFILE:
Target role: {role}
Technical skills: {skills}
Missing skills: {missing}

QUESTION: {question}

Return JSON with keys: answer (short helpful paragraph), recommended_skills (list of strings),
certifications (list of certification titles that appear in the context),
learning_resources (list of resource titles that appear in the context),
roadmap (list of step strings taken from the context), resume_improvements (list of strings)."""


def _empty_response(answer, notice="", ai=False):
    return {"answer": answer, "recommended_skills": [], "certifications": [], "learning_resources": [],
            "roadmap": [], "resume_improvements": [], "sources": [], "retrieved_context_count": 0,
            "grounded": False, "ai_generated": ai, "notice": notice}


class CareerAdvisorAgent:
    def __init__(self, rag: RAGService = None, llm=None):
        self.rag = rag or rag_service
        self.llm = llm or llm_service

    # ---------------------------------------------------------------- retrieval
    def retrieve_context(self, analysis: dict, missing_skills: list, question: str) -> tuple:
        role = infer_target_role(analysis.get("technical_skills", []))
        generic = question.strip().lower() == DEFAULT_QUESTION.lower()
        query = question + (" " + " ".join(missing_skills[:4]) + " " + role if generic else "")
        chunks = self.rag.retrieve(query)
        if chunks:   # add the roadmap of the candidate's likely role
            seen = {c["id"] for c in chunks}
            for extra in self.rag.retrieve(f"{role} roadmap", top_k=1, category="career_roadmaps"):
                if extra["id"] not in seen:
                    chunks.append(extra)
        return chunks, role

    # ---------------------------------------------------------------- main entry
    def run(self, analysis: dict, missing_skills: list, question: str, learning_resources: list) -> dict:
        question = (question or DEFAULT_QUESTION).strip()
        chunks, role = self.retrieve_context(analysis, missing_skills, question)
        if not chunks:
            return _empty_response(NO_CONTEXT_MESSAGE, "No relevant knowledge-base documents were found.")

        response = self._fallback(analysis, missing_skills, chunks, learning_resources, role)
        if self.llm.is_configured():
            try:
                self._apply_llm(response, analysis, missing_skills, question, chunks, learning_resources, role)
            except LLMError as exc:
                logger.warning("Career advice fallback used: %s", exc)
                response["notice"] = f"{exc.user_message} Showing an answer built directly from the knowledge base."
            except Exception as exc:
                logger.exception("Unexpected error in Career Advisor Agent: %s", exc)
                response["notice"] = "AI service is unavailable. Showing an answer built directly from the knowledge base."
        else:
            response["notice"] = "AI service is not configured. Showing an answer built directly from the knowledge base."
        return response

    # ---------------------------------------------------------------- LLM path
    def _apply_llm(self, response, analysis, missing_skills, question, chunks, resources, role):
        prompt = USER_PROMPT.format(
            context=self.rag.format_context(chunks), role=role,
            skills=", ".join(analysis.get("technical_skills", [])) or "none listed",
            missing=", ".join(missing_skills) or "none", question=question)
        data = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
        answer = str(data.get("answer") or "").strip()
        if not answer:
            return
        if NO_CONTEXT_MESSAGE.lower() in answer.lower():
            response.update(_empty_response(NO_CONTEXT_MESSAGE, "The knowledge base could not answer this question.", True))
            return
        response["answer"], response["ai_generated"], response["notice"] = answer, True, ""
        skills = [canonical_skill(s) for s in data.get("recommended_skills", []) if isinstance(s, str)]
        response["recommended_skills"] = skills[:8] or response["recommended_skills"]
        roadmap = [str(s) for s in data.get("roadmap", []) if isinstance(s, str)]
        response["roadmap"] = roadmap[:8] or response["roadmap"]
        improvements = [str(s) for s in data.get("resume_improvements", []) if isinstance(s, str)]
        response["resume_improvements"] = improvements[:6] or response["resume_improvements"]
        # Only keep certifications/resources that really exist in our data (prevents invented links).
        for key, wanted_cert in (("certifications", True), ("learning_resources", False)):
            names = [str(n).lower() for n in data.get(key, []) if isinstance(n, str)]
            matched = [r for r in resources if (r["type"] == "certification") == wanted_cert
                       and any(r["title"].lower() in n or n in r["title"].lower() for n in names)]
            response[key] = matched[:5] or response[key]

    # ---------------------------------------------------------------- fallback path
    def _fallback(self, analysis, missing_skills, chunks, resources, role) -> dict:
        have = {s.lower() for s in analysis.get("technical_skills", [])}
        recommended = [canonical_skill(s) for s in missing_skills if canonical_skill(s).lower() not in have][:6]
        context_text = " ".join(c["text"] + " " + c["title"] for c in chunks).lower()
        wanted = {s.lower() for s in recommended}
        relevant = [r for r in resources if r["skill"].lower() in wanted or r["title"].lower() in context_text]
        if not relevant:
            relevant = [r for r in resources if r["skill"].lower() in context_text]
        certs = [r for r in relevant if r["type"] == "certification"][:4]
        if not certs:   # suggest role-typical certifications from the learning_resources data
            role_skills = ROLE_CERT_SKILLS.get(role, [])
            certs = [r for r in resources if r["type"] == "certification" and r["skill"].lower() in role_skills][:3]
        learning = [r for r in relevant if r["type"] != "certification"][:6]

        roadmap = []
        for chunk in chunks:
            if chunk["category"] == "career_roadmaps":
                roadmap = [ln.strip() for ln in chunk["text"].splitlines() if STAGE_RE.match(ln.strip())]
                if roadmap:
                    break
        guidelines = [ln.strip()[2:] for c in chunks if c["category"] == "resume_guidelines"
                      for ln in c["text"].splitlines() if ln.strip().startswith("- ")][:3]
        improvements = list(analysis.get("improvements", []))[:3] + guidelines

        excerpts = []
        for chunk in chunks[:2]:
            sentences = re.split(r"(?<=[.!?])\s+", " ".join(chunk["text"].split()))
            excerpts.append(f"{chunk['title']}: {' '.join(sentences[:2])}")
        answer = "Based on the knowledge base - " + " ".join(excerpts)
        if recommended:
            answer += f" Skills to focus on for your profile ({role}): {', '.join(recommended)}."

        return {
            "answer": answer, "recommended_skills": recommended, "certifications": certs,
            "learning_resources": learning, "roadmap": roadmap, "resume_improvements": improvements,
            "sources": [{"title": c["title"], "category": c["category"], "source": c["source"], "score": c["score"]}
                        for c in chunks],
            "retrieved_context_count": len(chunks), "grounded": True, "ai_generated": False, "notice": "",
        }
