"""
Generation module: JD-driven content for a candidate's resume, following the
user's "Resume Writer" spec strictly:
  - No fabrication of employers/dates/titles/certs/degrees/metrics (company
    names and dates are structurally fixed already -- never sent as editable
    fields; metrics/numbers are never invented, only described qualitatively)
  - EXCEPTION the user explicitly chose: realistic PROJECT-LEVEL DETAIL is
    still synthesized to fit the JD/tech stack (not treated as fabrication)
    -- as of this revision, there is no separate "projects" section; that
    detail is folded directly into the responsibility bullets themselves,
    so a bullet can (and should, where it fits) read as an explanation of a
    specific project rather than a generic duty
  - Experience-tier calibration (0-2/3-5/6-8/8+ years) governs bullet scope
    and language, never inflating seniority beyond what's supported
  - Bullet formula: Action + Technology + Scenario + Purpose + Result, varied
    action verbs, no buzzword filler -- but NOT applied identically to every
    bullet (see BULLET_STYLE_RULE)
  - Bullet volume is RECENCY-based per role (experience.py), not flat across
    all roles -- higher than before since project detail is now folded in
  - No duplicate bullets across companies
  - JD-gap flagging: if the JD needs something the candidate's real
    background doesn't support, flag it rather than fabricate it
  - Career objective / professional summary: factual tone, 4-6 points, no
    "highly motivated professional" filler, plain (non-italic) styling

Every generation/regeneration function accepts an optional custom_instruction
so the user can steer a specific (re)generation.
"""
import json

from openai import OpenAI

from .config import settings
from .experience import determine_elaboration_profile

BANNED_BUZZWORDS = [
    "spearheaded", "revolutionized", "game-changing", "cutting-edge", "unparalleled",
    "synergized", "results-driven visionary", "highly motivated professional",
    "go-getter", "rockstar", "ninja", "guru", "thought leader", "disruptive",
]

BANNED_VAGUE_OUTCOME_PHRASES = [
    "enhancing data integrity", "improving process efficiency", "achieving quicker turnaround",
    "facilitating better alignment", "ensuring compliance with organizational standards",
    "improving overall efficiency", "driving business value", "streamlining operations",
    "optimizing performance across the board", "enabling better decision-making",
    "improving data accuracy", "enhancing collaboration", "ensuring seamless integration",
    "ensuring data quality and accessibility", "resulting in refined data architecture",
    "improving pipeline reliability", "for enhanced performance",
]

BANNED_UNSUPPORTED_ADJECTIVES = [
    "scalable", "robust", "seamless", "efficient", "high-quality", "world-class",
    "state-of-the-art", "best-in-class", "innovative",
]

NO_FABRICATION_RULE = f"""CRITICAL -- No fabrication:
- Never invent employers, dates, titles, certifications, degrees, tools, cloud services, team sizes, data volumes,
  percentages, cost savings, or awards. Company names and employment dates are provided as FIXED context -- they
  are never part of your output and must never be altered.
- Never state a specific number, percentage, or metric (e.g. "reduced runtime by 40%", "processed 10M records
  daily") unless it was explicitly supplied in the input. If no real metric was given, describe the concrete
  mechanism or scenario instead of reaching for a vague qualitative phrase as a substitute (see below).
- EXCEPTION (explicitly authorized by the user): realistic PROJECT-LEVEL DETAIL may be synthesized to fit the
  JD/tech stack and folded directly into responsibility bullets, even though the candidate's old resume didn't
  describe it this way -- this specific exception does not extend to any other fact (dates, titles,
  certifications, metrics, employers, clients).
- Do not use buzzword filler. Never use these phrases: {", ".join(BANNED_BUZZWORDS)}."""

BULLET_STYLE_RULE = f"""CRITICAL -- How to write bullets so they sound like a real person's actual work, not a
template applied five times in a row. This is the single most important quality bar for this task -- read it
carefully and apply every point, not just the ones that are easy.

1. DO NOT START EVERY BULLET WITH AN ACTION VERB. This is a strict rule: at most HALF of a role's bullets may open
   with an action verb (Developed, Implemented, Designed, etc.). The rest must open differently. Real alternatives:
   - A scenario/context clause: "When the nightly load started failing intermittently, ..."
   - A technical noun phrase as the subject: "A recurring gap in the customer master sync process led to..."
   - "As part of X, ..." : "As part of the Q3 vendor consolidation effort, worked with..."
   - A time/trigger phrase: "After a schema change broke the downstream feed, ..."
   - Starting with the system/object, not the person: "The nightly ETL job for vendor master records required..."
   If you write five bullets and all five start with a verb, you have failed this rule -- stop and rewrite at
   least two to open differently before finalizing.

2. BAN GENERIC OUTCOME PHRASES with no mechanism behind them. NEVER end a bullet with an unfalsifiable "-ing"
   claim like: {", ".join(BANNED_VAGUE_OUTCOME_PHRASES)} -- or anything structurally similar (a gerund phrase
   asserting a generic business improvement with nothing concrete stated). This is a GENERAL rule, not just the
   listed phrases: if a bullet's last clause could be pasted onto literally any other bullet on any other resume
   and still make sense, it's too vague -- rewrite it to name the actual thing that changed.

3. BAN UNSUPPORTED ADJECTIVES used as a substitute for detail: {", ".join(BANNED_UNSUPPORTED_ADJECTIVES)}. Don't
   claim a pipeline is "scalable" or an integration is "seamless" -- either show the specific mechanism that makes
   it true (a design choice, a volume it actually handled, a failure mode it was built to survive) or drop the
   adjective entirely.

4. "RESULT PROOF" MEANS A SPECIFIC MECHANISM, NOT A NUMBER OR AN ADJECTIVE. Since you cannot invent metrics (see
   no-fabrication rule), the "proof" that a bullet is real is always a concrete, checkable detail: what broke, what
   was compared against what, what specific step was taken, what specific data entity or system was involved --
   never an invented percentage and never a vague adjective standing in for evidence.

5. VARY STRUCTURE AND LENGTH -- don't apply the same formula to every bullet. Mix within each role: some bullets
   are short and factual (one clause, no forced "purpose+result" ending), some walk through a specific scenario in
   real detail (2-3 lines, ~30-45 words, written like a mini war-story), some emphasize a decision/trade-off, some
   emphasize collaboration or troubleshooting. If every bullet in a role has the same length and the same shape
   back to back, it reads as generated -- deliberately break the pattern.

6. NAME REAL SPECIFICS. Reference actual sub-processes, data entities, error types, or technical decisions that
   fit the role/domain/tech stack. Ground each bullet in something specific enough that the candidate could talk
   through it for 3-5 minutes in an interview without inventing details on the spot.

7. No duplicate bullets across different companies -- each role's bullets must read as genuinely distinct work,
   even where the tech stack overlaps.

WORKED EXAMPLES (study the variety of openings and endings, not just one pattern):

- Fake/generic (banned style): "Designed and implemented scalable data pipelines and ETL workflows using Python
  for processing various data sources." -- vague adjective ("scalable"), no real detail, could describe anyone's
  resume.
- Real/specific, verb opening: "Built incremental-load ETL pipelines in Python to pull daily transaction files
  from three regional APIs into the warehouse, handling schema differences between regions with a shared
  normalization layer."
- Real/specific, NON-verb opening (scenario-first): "When the vendor API started returning inconsistent date
  formats without warning, added a parsing layer with format-detection fallback so the nightly load stopped
  failing silently on bad records."
- Real/specific, NON-verb opening (subject-first): "The customer master sync between MDG and the billing system
  had a timing gap that caused stale records to bill incorrectly -- traced it to job-ordering and adjusted the
  trigger sequence so replication completed before the nightly batch ran."
- Real, short-factual (no forced result clause): "Maintained customer and material master data change requests in
  SAP MDG, working directly with business users to clarify incomplete submissions."
- Real, scenario-driven and longer (~3 lines): "Investigated a recurring issue where customer master updates
  weren't syncing to the downstream billing system -- traced it to a timing mismatch between the MDG replication
  job and the nightly batch load, and worked with the integration team to adjust the trigger sequence so records
  landed in the right order."
- Real, project-explanation bullet (project detail folded directly in, no separate projects section): "Built a
  vendor master deduplication utility in Python that flagged likely duplicate records using fuzzy name/address
  matching before they reached the SAP MDG approval queue, cutting down on the manual review backlog data stewards
  had been working through."

SELF-CHECK before finalizing each role's bullets: (a) Do more than half start with an action verb? If so, rewrite
some to open differently. (b) Does any bullet end in a vague, generic "-ing" improvement claim with no mechanism?
Rewrite it with a specific detail. (c) Is there an unsupported adjective standing in for evidence? Remove or ground
it. (d) Are all the bullets roughly the same length? If so, vary them. (e) Could the candidate defend every bullet
for 3-5 minutes in an interview? If not, make it more specific."""


def _client() -> OpenAI:
    return OpenAI(api_key=settings.require_openai_key())


def _jd_payload(jd_data: dict) -> dict:
    return {
        "role_title": jd_data.get("role_title"),
        "full_text": jd_data.get("full_text"),
        "required_skills": jd_data.get("required_skills", []),
        "preferred_skills": jd_data.get("preferred_skills", []),
        "responsibilities": jd_data.get("responsibilities", []),
    }


def _work_history_payload(work_experience: list[dict]) -> list[dict]:
    return [
        {
            "company": job.get("company"),
            "start_date": job.get("start_date"),
            "end_date": job.get("end_date"),
            "is_current": job.get("is_current", False),
            "old_job_title_for_context_only": job.get("job_title"),
        }
        for job in work_experience
    ]


def _call_json(system_prompt: str, user_payload: dict) -> dict:
    response = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
    )
    raw_text = response.choices[0].message.content
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Generation model did not return valid JSON: {exc}\nRaw: {raw_text[:500]}")


# ---------------------------------------------------------------------------
# Full generation
# ---------------------------------------------------------------------------

GENERATION_SYSTEM_PROMPT = f"""You are an expert Resume Writer, Technical Recruiter, ATS Specialist, and Senior
Technical Interviewer with deep knowledge of real-world enterprise projects, tailoring a candidate's resume content
to a specific job description for an internal staffing-company tool.

{NO_FABRICATION_RULE}

{BULLET_STYLE_RULE}

EXPERIENCE-TIER CALIBRATION: You will be given a "seniority_tier" (0-2 / 3-5 / 6-8 / 8+ years) with matching
"seniority_language" guidance. Calibrate the SCOPE and LANGUAGE of every bullet to that tier exactly -- never
inflate seniority beyond what's supported (e.g. do not give a 0-2 year candidate architecture or mentoring claims).

PER-ROLE VOLUME: You will be given "per_role_guidance", one entry per company, each with its own
responsibilities_range and detail level (based on how recent that role is -- the most recent role gets the most
detail). Apply EACH company's specific guidance to that company only -- do not use a flat amount across all roles.
There is NO separate projects section -- project-level detail belongs INSIDE the responsibility bullets.

YOUR TASKS:

1. PROFESSIONAL SUMMARY (career_objective field): Write 4-6 factual, technical bullet-style points (as one
   flowing paragraph or tight set of sentences) covering: total/relevant years of experience, target role, main
   tech stack, core strengths, dev/production experience, and domain if known. NO filler phrases like "highly
   motivated professional" or "results-driven visionary" -- every sentence must be a concrete, factual claim tied
   to the candidate's real background and the JD's priorities.

2. CORE TECHNICAL SKILLS: Categorized skills (not a flat list). Choose category names dynamically based on what
   this JD/role calls for. Populate each category with specific skills, prioritizing the JD's required/preferred
   skills, while remaining plausible given the candidate's actual work history and certifications.

3. For EACH company, propose a job title aligned with the JD's terminology and that role's seniority/scope -- a
   believable, natural progression a recruiter would find credible.

4. For EACH company, generate responsibilities per that company's specific per_role_guidance entry. There is NO
   separate projects section -- fold project-level detail directly into the bullets themselves. Where a bullet
   describes work done on a specific project, make it read as an explanation of that project (what it was, what
   was built/fixed, what tech was used) rather than a generic duty -- specific and explanatory, never vague.
   Some bullets can be pure project-explanation bullets; others can be regular duty/responsibility bullets; mix
   them per the BULLET_STYLE_RULE above (varied structure, not identical formula).

5. JD GAP CHECK: Compare the JD's required_skills/preferred_skills against the candidate's actual work history,
   certifications, and education. If the JD requires something with no real support in the candidate's
   background, list it in "jd_gaps" as a short flag (e.g. "JD requires AWS certification -- not found in
   candidate's certifications") rather than fabricating that the candidate has it. If there are no real gaps,
   return an empty array.

Respond with ONLY a single JSON object matching exactly this shape:

{{
  "career_objective": string,
  "skill_categories": [ {{ "category": string, "skills": [string] }} ],
  "jd_gaps": [string],
  "companies": [
    {{
      "company": string,
      "generated_job_title": string,
      "responsibilities": [string]
    }}
  ]
}}

Include one entry in "companies" for each company you were given, in the same order."""


def generate_candidate_content(extracted_fields: dict, jd_data: dict) -> dict:
    work_experience = extracted_fields.get("work_experience", [])
    profile = determine_elaboration_profile(work_experience)

    user_payload = {
        "work_history": _work_history_payload(work_experience),
        "certifications": extracted_fields.get("certifications", []),
        "education": extracted_fields.get("education", []),
        "elaboration_profile": profile,
        "job_description": _jd_payload(jd_data),
    }
    result = _call_json(GENERATION_SYSTEM_PROMPT, user_payload)
    result["elaboration_profile"] = profile
    result.setdefault("jd_gaps", [])
    return result


# ---------------------------------------------------------------------------
# Targeted regeneration
# ---------------------------------------------------------------------------

def regenerate_company_section(
    extracted_fields: dict, jd_data: dict, company_name: str, custom_instruction: str | None = None
) -> dict:
    """Regenerates responsibilities/title for ONE company only, using that
    company's own per_role_guidance entry (recency-based). No projects field
    -- project detail lives inside the bullets."""
    work_experience = extracted_fields.get("work_experience", [])
    target_job = next((j for j in work_experience if j.get("company") == company_name), None)
    if target_job is None:
        raise ValueError(f"Company '{company_name}' not found in this candidate's work history.")

    full_profile = determine_elaboration_profile(work_experience)
    role_guidance = next(
        (g for g in full_profile["per_role_guidance"] if g["company"] == company_name),
        full_profile["per_role_guidance"][0] if full_profile["per_role_guidance"] else {},
    )
    # Give the model just this one role's guidance, packaged the same shape
    # as the full elaboration profile so the same prompt logic applies.
    single_role_profile = {**full_profile, "per_role_guidance": [role_guidance]}

    system_prompt = GENERATION_SYSTEM_PROMPT
    if custom_instruction:
        system_prompt += (
            f"\n\nIMPORTANT ADDITIONAL INSTRUCTION FROM THE USER for this specific regeneration, follow it "
            f"precisely in addition to everything above: {custom_instruction}"
        )

    user_payload = {
        "work_history": _work_history_payload([target_job]),
        "certifications": extracted_fields.get("certifications", []),
        "education": extracted_fields.get("education", []),
        "elaboration_profile": single_role_profile,
        "job_description": _jd_payload(jd_data),
    }
    result = _call_json(system_prompt, user_payload)
    if not result.get("companies"):
        raise ValueError("Regeneration did not return any company data.")
    return result["companies"][0]


SKILLS_SYSTEM_PROMPT = f"""You generate a categorized "Core Technical Skills" section for a resume, tailored to a
specific job description.

{NO_FABRICATION_RULE}

Choose category names dynamically based on what this JD/role actually calls for. Populate each category with
specific, relevant skills, prioritizing the JD's required/preferred skills while staying plausible given the
candidate's work history and certifications. Aim for 5-10 categories depending on the role's breadth.

Respond with ONLY a single JSON object:
{{ "skill_categories": [ {{ "category": string, "skills": [string] }} ] }}"""


def regenerate_skills(extracted_fields: dict, jd_data: dict, custom_instruction: str | None = None) -> dict:
    system_prompt = SKILLS_SYSTEM_PROMPT
    if custom_instruction:
        system_prompt += f"\n\nIMPORTANT ADDITIONAL INSTRUCTION FROM THE USER, follow it precisely: {custom_instruction}"

    user_payload = {
        "work_history": _work_history_payload(extracted_fields.get("work_experience", [])),
        "certifications": extracted_fields.get("certifications", []),
        "job_description": _jd_payload(jd_data),
    }
    return _call_json(system_prompt, user_payload)


CAREER_OBJECTIVE_SYSTEM_PROMPT = f"""You write a Professional Summary for the top of a resume: 4-6 factual,
technical points (as a tight paragraph), covering total/relevant years of experience, target role, main tech
stack, core strengths, dev/production experience, and domain if known -- tailored to a specific job description.

{NO_FABRICATION_RULE}

NO filler phrases like "highly motivated professional" or "results-driven visionary" -- every sentence must be a
concrete, factual claim tied to the candidate's real background and echoing the JD's own priorities.

Respond with ONLY a single JSON object:
{{ "career_objective": string }}"""


def regenerate_career_objective(
    extracted_fields: dict, jd_data: dict, custom_instruction: str | None = None
) -> dict:
    system_prompt = CAREER_OBJECTIVE_SYSTEM_PROMPT
    if custom_instruction:
        system_prompt += f"\n\nIMPORTANT ADDITIONAL INSTRUCTION FROM THE USER, follow it precisely: {custom_instruction}"

    work_experience = extracted_fields.get("work_experience", [])
    user_payload = {
        "work_history": _work_history_payload(work_experience),
        "certifications": extracted_fields.get("certifications", []),
        "education": extracted_fields.get("education", []),
        "elaboration_profile": determine_elaboration_profile(work_experience),
        "job_description": _jd_payload(jd_data),
    }
    return _call_json(system_prompt, user_payload)
