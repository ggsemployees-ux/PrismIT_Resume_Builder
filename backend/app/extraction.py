"""
Phase 1 extraction: turn raw resume text (and a JD, which may be text or an
image) into the structured fields the confirmation checkpoint screen shows
the user for review/editing.

Uses OpenAI's Chat Completions API with JSON mode (response_format=
{"type": "json_object"}), which every current OpenAI chat model supports and
reliably returns parseable JSON without needing to strip markdown fences.
"""
import base64
import json

from openai import OpenAI

from .config import settings

RESUME_EXTRACTION_SYSTEM_PROMPT = """You are a precise resume-parsing assistant used inside an internal staffing-company tool. \
You will be given the raw extracted text of a candidate's resume (formatting/line breaks may be imperfect because it \
came from a PDF/DOCX text extractor). Your job is ONLY to extract what is already present in the text -- \
never invent, guess, or embellish anything. If a field is not present, use null (for single fields) or an empty \
array (for list fields). Do not summarize or rephrase -- copy values as close to verbatim as reasonable.

Respond with ONLY a single JSON object matching exactly this shape:

{
  "personal_info": {
    "full_name": string or null,
    "mobile": string or null,
    "email": string or null,
    "location": string or null,
    "linkedin_url": string or null,
    "portfolio_url": string or null
  },
  "education": [
    {
      "degree": string,
      "institution": string,
      "start_date": string or null,
      "end_date": string or null
    }
  ],
  "work_experience": [
    {
      "company": string,
      "job_title": string or null,
      "start_date": string or null,
      "end_date": string or null,
      "is_current": boolean
    }
  ],
  "certifications": [string],
  "languages_known": [string],
  "missing_sections": [string]
}

For "missing_sections": list any of these section names that appear to be entirely absent from the resume, so the \
tool can prompt the user to fill them in manually: "education", "work_experience", "personal_info". Only list a \
section as missing if you truly found nothing for it -- do not list "certifications" or "languages_known" as \
missing since those are optional and commonly absent.

Preserve dates exactly as written in the resume (e.g. "Jan 2021", "2019", "06/2020") -- do not reformat or infer \
missing day/month information."""


def _client() -> OpenAI:
    return OpenAI(api_key=settings.require_openai_key())


def extract_resume_fields(resume_text: str) -> dict:
    """Sends raw resume text to OpenAI and gets back structured fields.
    Raises ValueError if the model's response isn't valid JSON."""
    response = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RESUME_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": resume_text},
        ],
    )
    raw_text = response.choices[0].message.content
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extraction model did not return valid JSON: {exc}\nRaw: {raw_text[:500]}")


JD_EXTRACTION_SYSTEM_PROMPT = """You are given a job description, either as plain text or as an image of a job \
posting. Extract the following as plain text, staying faithful to what's actually written -- do not invent \
requirements that aren't there.

Respond with ONLY a single JSON object matching exactly this shape:

{
  "role_title": string or null,
  "full_text": string,
  "required_skills": [string],
  "preferred_skills": [string],
  "responsibilities": [string]
}

"full_text" should be the complete JD content transcribed as plain text (if the input was an image, this is your \
transcription of it). "role_title" is the job title being hired for, if stated."""


def extract_jd_from_text(jd_text: str) -> dict:
    response = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JD_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": jd_text},
        ],
    )
    raw_text = response.choices[0].message.content
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JD extraction model did not return valid JSON: {exc}\nRaw: {raw_text[:500]}")


def extract_jd_from_image(image_bytes: bytes, media_type: str) -> dict:
    """Same as extract_jd_from_text but for a JD that arrived as a screenshot
    / photo of a job posting. Uses OpenAI's vision input (image passed as a
    base64 data URL) instead of a separate OCR step. Requires OPENAI_MODEL to
    be a vision-capable model (e.g. gpt-4o-mini, gpt-4o) -- see .env.example."""
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{media_type};base64,{b64_image}"
    response = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JD_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": "Extract the job description from this image as specified."},
                ],
            },
        ],
    )
    raw_text = response.choices[0].message.content
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JD image extraction model did not return valid JSON: {exc}\nRaw: {raw_text[:500]}")
