"""Deterministic job matching. The score NEVER comes from an LLM.

    match_score = matched_required_skills / total_required_skills * 100
"""
from app.services.skills_catalog import IMPLIED_SKILLS, canonical_skill


def normalize_skills(skills) -> list:
    """Canonical names, no blanks, no duplicates, original order preserved."""
    seen, result = set(), []
    for skill in skills or []:
        name = canonical_skill(str(skill))
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


def _expand_with_implied(skills: list) -> set:
    have = {s.lower() for s in skills}
    for generic, specifics in IMPLIED_SKILLS.items():
        if any(s.lower() in have for s in specifics):
            have.add(generic.lower())
    return have


def calculate_match(resume_skills, required_skills) -> dict:
    required = normalize_skills(required_skills)
    if not required:
        return {"match_score": 0, "matched_skills": [], "missing_skills": []}
    have = _expand_with_implied(normalize_skills(resume_skills))
    matched = [s for s in required if s.lower() in have]
    missing = [s for s in required if s.lower() not in have]
    score = int(len(matched) / len(required) * 100 + 0.5)
    return {"match_score": score, "matched_skills": matched, "missing_skills": missing}


def template_explanation(job_title: str, score: int, matched: list, missing: list) -> str:
    """Rule-based explanation (used when the LLM is unavailable)."""
    if score >= 75:
        opening = f"You are a strong match for {job_title}"
    elif score >= 50:
        opening = f"You are a partial match for {job_title}"
    else:
        opening = f"{job_title} is a stretch role for you right now"
    parts = [f"{opening} ({score}%)."]
    if matched:
        parts.append(f"You already have {len(matched)} required skill(s): {', '.join(matched)}.")
    if missing:
        parts.append(f"Learning {', '.join(missing)} would improve your chances.")
    else:
        parts.append("You cover every required skill listed for this job.")
    return " ".join(parts)
