"""
Turns the confirmed work_experience list into what the generation prompt
needs, per the Resume Writer spec:
  1. A best-effort total years of experience (dates in resumes are messy free
     text, so this is deliberately forgiving and falls back gracefully)
  2. A seniority tier (0-2 / 3-5 / 6-8 / 8+ years) that calibrates the SCOPE
     and LANGUAGE of generated content (execution-only vs ownership vs
     architecture/leadership) -- never inflated beyond what the input supports
  3. Per-role bullet/project guidance based on RECENCY, not company count:
     the most recent role gets the most detail (8-12 bullets), the next most
     recent gets moderate detail (6-9), older roles get concise detail (5-8)
     -- scaled down further for any role shorter than a year, regardless of
     its recency rank, since a 3-month stint shouldn't get 12 bullets.

This does NOT enforce a page count -- that happens later once content is
actually laid out in a template. This module only turns experience data into
concrete generation guidance the LLM prompt follows.
"""
import re
from datetime import datetime
from typing import Optional

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date_fragment(text: Optional[str]) -> Optional[datetime]:
    """Best-effort parse of resume date fragments like 'Jan 2021', '2019',
    '06/2020', 'Present', 'Current'. Returns None if it can't confidently
    parse -- callers must handle that gracefully rather than crashing."""
    if not text:
        return None
    cleaned = text.strip().lower()
    if cleaned in ("present", "current", "till date", "ongoing", "now"):
        return datetime.now()

    m = re.match(r"^(\d{1,2})[/-](\d{4})$", cleaned)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return datetime(year, month, 1)

    m = re.match(r"^([a-z]{3,9})[\s-]+(\d{4})$", cleaned)
    if m:
        month_key = m.group(1)[:4].rstrip(".")[:3] if len(m.group(1)) > 4 else m.group(1)[:3]
        month = MONTH_MAP.get(month_key[:3])
        if month:
            return datetime(int(m.group(2)), month, 1)

    m = re.match(r"^(\d{4})$", cleaned)
    if m:
        return datetime(int(m.group(1)), 1, 1)

    return None


def _job_end_sort_key(job: dict) -> datetime:
    """For ranking by recency: 'Present'/is_current sorts as latest."""
    if job.get("is_current"):
        return datetime.max
    end = _parse_date_fragment(job.get("end_date"))
    return end or datetime.min


def _job_duration_years(job: dict) -> Optional[float]:
    start = _parse_date_fragment(job.get("start_date"))
    end = _parse_date_fragment(job.get("end_date")) or (datetime.now() if job.get("is_current") else None)
    if not start or not end:
        return None
    days = (end - start).days
    return round(days / 365.25, 2) if days > 0 else None


def estimate_total_years_experience(work_experience: list[dict]) -> Optional[float]:
    """Looks at the earliest start date and latest end date (or 'present')
    across all jobs. Returns None if no dates were parseable at all."""
    starts, ends = [], []
    for job in work_experience:
        start = _parse_date_fragment(job.get("start_date"))
        end = _parse_date_fragment(job.get("end_date")) or (datetime.now() if job.get("is_current") else None)
        if start:
            starts.append(start)
        if end:
            ends.append(end)

    if not starts or not ends:
        return None

    span_days = (max(ends) - min(starts)).days
    if span_days <= 0:
        return None
    return round(span_days / 365.25, 1)


def _seniority_tier(total_years: Optional[float]) -> str:
    """0-2 / 3-5 / 6-8 / 8+ per the Resume Writer spec's experience calibration.
    Falls back to '3-5' (a neutral middle tier) when dates can't be parsed,
    rather than guessing junior or senior."""
    if total_years is None:
        return "3-5"
    if total_years <= 2:
        return "0-2"
    if total_years <= 5:
        return "3-5"
    if total_years <= 8:
        return "6-8"
    return "8+"


_TIER_LANGUAGE = {
    "0-2": "execution-level only: development, testing, monitoring, bug fixing, documentation, working under guidance. Do NOT claim architecture, ownership, or mentoring.",
    "3-5": "independent contributor: independent development, requirement analysis, production support, optimization, deployment, troubleshooting, team coordination, code review.",
    "6-8": "technical ownership: design discussions, mentoring, complex troubleshooting, solution recommendations, cross-team coordination.",
    "8+": "architecture/leadership: architecture/design, technical leadership, standards/governance, solution strategy, stakeholder management, mentoring, delivery ownership.",
}


def _per_role_guidance(work_experience: list[dict]) -> list[dict]:
    """Ranks roles by recency and assigns bullet volume accordingly. Bullet
    counts are higher than in earlier versions because project-level detail
    now lives INSIDE the bullets themselves (no separate projects section) --
    per the spec: most recent ~10-14 bullets, next ~8-11, older ~6-9, capped
    lower for any role under a year regardless of rank."""
    indexed = list(enumerate(work_experience))
    ranked = sorted(indexed, key=lambda pair: _job_end_sort_key(pair[1]), reverse=True)

    guidance_by_index = {}
    for rank, (original_index, job) in enumerate(ranked, start=1):
        duration = _job_duration_years(job)
        short_stint = duration is not None and duration < 1

        if rank == 1:
            resp, detail = "10-14", "vary bullet length and structure -- mix short factual bullets with several detailed, scenario-driven ones (~3 lines each) that include real project-level specifics; no invented numbers, no generic outcome phrases"
        elif rank == 2:
            resp, detail = "8-11", "vary bullet length and structure -- mostly moderate detail, a few can run longer if there's a real project scenario to describe"
        else:
            resp, detail = "6-9", "mostly short and specific, avoid padding with generic outcome phrases"

        if short_stint:
            resp = "4-6"
            detail = "concise -- this was a short stint, keep it tight and specific"

        guidance_by_index[original_index] = {
            "company": job.get("company"),
            "recency_rank": rank,
            "responsibilities_range": resp,
            "detail": detail,
            "duration_years": duration,
        }

    return [guidance_by_index[i] for i in range(len(work_experience))]


def determine_elaboration_profile(work_experience: list[dict]) -> dict:
    """Combines seniority tier (scope/language calibration) with per-role,
    recency-based bullet/project volume guidance."""
    total_years = estimate_total_years_experience(work_experience)
    tier = _seniority_tier(total_years)
    company_count = len(work_experience)
    per_role = _per_role_guidance(work_experience)

    target_page_guidance = "1-2 pages"
    if tier == "8+":
        target_page_guidance = "up to 4 pages -- this candidate has 8+ years of experience, so more space is warranted"
    elif tier == "6-8":
        target_page_guidance = "2-3 pages"
    elif company_count >= 3:
        target_page_guidance = "2 pages"

    return {
        "seniority_tier": tier,
        "seniority_language": _TIER_LANGUAGE[tier],
        "estimated_total_years": total_years,
        "company_count": company_count,
        "target_page_guidance": target_page_guidance,
        "per_role_guidance": per_role,
    }
