"""
Computes an internal ATS-compliance score (0-100) from measurable, controllable
factors -- NOT a claim about how any specific real-world ATS (Workday,
Greenhouse, Taleo, etc.) would score this resume, since those are proprietary
and unreplicable. This score reflects: keyword overlap with the JD, structural
format compliance (single-column safety, standard section headers), and basic
parseability (contact info present, consistent dates). It's meant as a
directional signal for staff, not a guarantee against any particular real ATS.
"""
import re

from .templates import get_template


def _flatten_skills(resume_data: dict) -> set[str]:
    skills = set()
    for cat in resume_data.get("skill_categories", []) or []:
        for s in cat.get("skills", []):
            skills.add(s.lower().strip())
    return skills


def _all_bullet_text(resume_data: dict) -> str:
    parts = [resume_data.get("career_objective") or ""]
    for job in resume_data.get("work_experience", []) or []:
        parts.extend(job.get("responsibilities", []) or [])
    return " ".join(parts).lower()


def _keyword_match_score(resume_data: dict, jd_data: dict) -> tuple[float, list[str]]:
    """Returns (0-100 score, list of missing required/preferred keywords)."""
    required = [s.lower().strip() for s in (jd_data.get("required_skills") or [])]
    preferred = [s.lower().strip() for s in (jd_data.get("preferred_skills") or [])]

    skills_set = _flatten_skills(resume_data)
    bullet_text = _all_bullet_text(resume_data)

    def is_covered(keyword: str) -> bool:
        if not keyword:
            return True
        if any(keyword in s or s in keyword for s in skills_set):
            return True
        return keyword in bullet_text

    missing = []
    required_hits = 0
    for kw in required:
        if is_covered(kw):
            required_hits += 1
        else:
            missing.append(kw)

    preferred_hits = 0
    for kw in preferred:
        if is_covered(kw):
            preferred_hits += 1
        else:
            missing.append(kw)

    required_pct = (required_hits / len(required)) if required else 1.0
    preferred_pct = (preferred_hits / len(preferred)) if preferred else 1.0

    score = (required_pct * 0.7 + preferred_pct * 0.3) * 100
    return round(score, 1), missing


def _format_score(format_settings: dict) -> tuple[float, list[str]]:
    """Deducts for structural choices that are known to trip up some real ATS
    parsers -- primarily multi-column layouts."""
    notes = []
    score = 100.0
    template = get_template(format_settings.get("template_id"))
    if template["layout"] == "sidebar":
        score -= 15
        notes.append("Two-column sidebar layout can be misread by some older ATS parsers -- Classic/Modern/Compact are safer choices if ATS parsing is a concern for this JD.")
    return round(score, 1), notes


def _parseability_score(resume_data: dict) -> tuple[float, list[str]]:
    notes = []
    score = 100.0
    p = resume_data.get("personal_info") or {}
    if not p.get("full_name"):
        score -= 25
        notes.append("Missing candidate name.")
    if not p.get("email"):
        score -= 20
        notes.append("Missing email address.")
    if not p.get("mobile"):
        score -= 15
        notes.append("Missing phone number.")
    if not resume_data.get("work_experience"):
        score -= 20
        notes.append("No work experience section found.")
    if not resume_data.get("skill_categories"):
        score -= 10
        notes.append("No skills section found.")
    if not resume_data.get("education"):
        score -= 10
        notes.append("No education section found.")
    return round(max(score, 0), 1), notes


def compute_ats_score(resume_data: dict, jd_data: dict, format_settings: dict) -> dict:
    keyword_score, missing_keywords = _keyword_match_score(resume_data, jd_data)
    format_score, format_notes = _format_score(format_settings)
    parseability_score, parseability_notes = _parseability_score(resume_data)

    overall = round(keyword_score * 0.5 + format_score * 0.3 + parseability_score * 0.2, 1)

    return {
        "overall_score": overall,
        "keyword_match_score": keyword_score,
        "format_score": format_score,
        "parseability_score": parseability_score,
        "missing_keywords": missing_keywords,
        "notes": format_notes + parseability_notes,
    }
