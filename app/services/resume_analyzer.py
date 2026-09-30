"""Keyword/rule-based resume analysis.

This is the FALLBACK used when Gemini is unavailable. It is also used by the
Resume Analyzer Agent to double-check the LLM output (contact details, skills).
"""
import re

from app.services.skills_catalog import (
    extract_soft_skills, extract_technical_skills, infer_target_role, role_missing_skills,
)

SECTION_HEADINGS = {
    "summary": ["summary", "professional summary", "profile", "objective", "career objective", "about me"],
    "skills": ["skills", "technical skills", "core competencies", "key skills"],
    "experience": ["experience", "work experience", "professional experience", "employment history",
                   "work history", "internship", "internships"],
    "education": ["education", "academic background", "academic qualifications", "qualifications"],
    "projects": ["projects", "personal projects", "academic projects", "selected projects"],
    "certifications": ["certifications", "certificates", "licenses", "licenses certifications", "courses", "training"],
}
DEGREE_WORDS = re.compile(r"\b(bachelor|b\.?sc|b\.?eng|b\.?tech|master|m\.?sc|m\.?eng|phd|diploma|university|college|faculty)\b", re.I)
ROLE_WORDS = re.compile(r"\b(engineer|developer|intern|analyst|manager|assistant|consultant|specialist|scientist)\b", re.I)
CERT_WORDS = re.compile(r"\b(certified|certificate|certification)\b", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
METRIC_RE = re.compile(r"\d+\s?%|\$\s?\d|\b(increased|reduced|improved|decreased|saved)\b[^.\n]{0,40}\bby\b\s?\d", re.I)


def clean_line(line: str) -> str:
    return re.sub(r"^[\s•\-*–▪●·►]+", "", line).strip()


def heading_of(line: str):
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped) > 40:
        return None
    normalized = re.sub(r"[^a-z ]", "", stripped.lower().replace("&", " ")).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    for key, names in SECTION_HEADINGS.items():
        if normalized in names:
            return key
    return None


def split_sections(text: str) -> dict:
    sections, current = {}, None
    for line in text.splitlines():
        key = heading_of(line)
        if key:
            current = key
            sections.setdefault(current, [])
        elif current and line.strip():
            sections[current].append(clean_line(line))
    return sections


def extract_contact(text: str) -> dict:
    email = EMAIL_RE.search(text)
    phone = ""
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(1))
        if 9 <= len(digits) <= 15:
            phone = match.group(1).strip()
            break
    name = ""
    for line in [l.strip() for l in text.splitlines() if l.strip()][:5]:
        words = line.split()
        if "@" in line or re.search(r"\d", line) or heading_of(line):
            continue
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            name = line
            break
    return {"candidate_name": name, "candidate_email": email.group(0) if email else "", "candidate_phone": phone}


def _first(items, limit):
    seen, out = set(), []
    for item in items:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out


def keyword_analysis(text: str) -> dict:
    """Return the full analysis dictionary using only rules and keywords."""
    contact = extract_contact(text)
    sections = split_sections(text)
    lines = [clean_line(l) for l in text.splitlines() if l.strip()]

    education = _first(sections.get("education") or [l for l in lines if DEGREE_WORDS.search(l)], 6)
    experience = _first(sections.get("experience") or [l for l in lines if ROLE_WORDS.search(l)], 8)
    projects = _first(sections.get("projects", []), 8)
    certifications = _first(sections.get("certifications") or [l for l in lines if CERT_WORDS.search(l)], 6)

    technical = extract_technical_skills(text)
    soft = extract_soft_skills(text)
    role = infer_target_role(technical)
    missing = role_missing_skills(technical, role)[:8]
    word_count = len(text.split())
    has_metrics = bool(METRIC_RE.search(text))

    strengths, weaknesses, improvements = [], [], []
    if len(technical) >= 8:
        strengths.append(f"Broad technical skill set ({len(technical)} technologies detected).")
    elif len(technical) >= 4:
        strengths.append(f"Solid technical foundation ({len(technical)} technologies detected).")
    if projects:
        strengths.append(f"Practical experience shown through {len(projects)} listed project line(s).")
    if experience and sections.get("experience"):
        strengths.append("Work or internship experience is included.")
    if certifications:
        strengths.append("Certifications demonstrate commitment to learning.")
    if has_metrics:
        strengths.append("Achievements are quantified with numbers.")
    if not strengths:
        strengths.append("Resume contains readable content that can be improved step by step.")

    if not projects:
        weaknesses.append("No projects section found.")
        improvements.append("Add a Projects section with 2-3 projects, the technologies used and the result.")
    if not certifications:
        weaknesses.append("No certifications listed.")
        improvements.append("Consider adding a relevant certification or completed online course.")
    if not has_metrics:
        weaknesses.append("Achievements are not quantified.")
        improvements.append("Add numbers to your bullet points (e.g. 'reduced load time by 30%').")
    if len(soft) < 2:
        weaknesses.append("Few soft skills are mentioned.")
        improvements.append("Show teamwork, communication or leadership through short examples.")
    if "summary" not in sections:
        weaknesses.append("No professional summary at the top of the resume.")
        improvements.append("Start with a 2-3 line professional summary tailored to your target role.")
    if word_count < 150:
        weaknesses.append("The resume is very short.")
        improvements.append("Expand experience and project descriptions with concrete details.")
    if not contact["candidate_email"] or not contact["candidate_phone"]:
        weaknesses.append("Contact details are incomplete.")
        improvements.append("Include a professional email address and phone number in the header.")
    if missing:
        improvements.append(f"Learn and showcase: {', '.join(missing[:4])} (common for {role} roles).")

    who = contact["candidate_name"] or "The candidate"
    top = ", ".join(technical[:5]) if technical else "no clearly listed technologies"
    summary = (f"{who} has a profile closest to a {role} role, with skills in {top}. "
               f"The resume lists {len(education)} education item(s), {len(experience)} experience item(s) "
               f"and {len(projects)} project item(s).")

    return {
        **contact,
        "summary": summary,
        "technical_skills": technical,
        "soft_skills": soft,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_skills": missing,
        "improvements": improvements,
        "target_role": role,
    }
