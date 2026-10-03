"""
Phase 1 API surface:

  GET  /api/staff-names            -> names for the "who are you" picker
  GET  /api/candidates             -> dashboard list (optionally filtered by staff member)
  POST /api/extract                -> upload resume + JD, get back extracted fields for confirmation
  POST /api/candidates              -> save a confirmed/edited candidate record
  PATCH /api/candidates/{id}        -> update fields after user edits on the confirmation screen

Run with: uvicorn app.main:app --reload --port 8000
"""
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
import traceback
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import extraction, file_parsing, generation, storage
from . import docx_render, pdf_render, ats_score
from .config import settings
from .templates import DEFAULT_FORMAT_SETTINGS, RECOMMENDED_FONTS, list_templates

app = FastAPI(title="Prism IT Hub Resume Builder API")

# Wide-open CORS for local development. Tighten this to your actual deployed
# frontend origin before this goes anywhere near production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/staff-names")
def get_staff_names():
    return {"staff_names": settings.STAFF_NAMES}


@app.get("/api/candidates")
def get_candidates(created_by: Optional[str] = None):
    try:
        return {"candidates": storage.list_candidates(created_by=created_by)}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/extract")
async def extract(
    resume_file: UploadFile = File(...),
    jd_text: Optional[str] = Form(None),
    jd_image: Optional[UploadFile] = File(None),
):
    """Takes the uploaded resume + JD (text OR image, not both) and returns
    structured, editable fields for the confirmation checkpoint. Does NOT
    save anything yet -- saving happens in POST /api/candidates once the
    user confirms/edits."""
    if not jd_text and not jd_image:
        raise HTTPException(status_code=400, detail="Provide either jd_text or jd_image.")

    resume_bytes = await resume_file.read()
    try:
        resume_text = file_parsing.extract_text_from_upload(resume_file.filename, resume_bytes)
    except file_parsing.UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        extracted_fields = extraction.extract_resume_fields(resume_text)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Resume extraction failed: {exc}")

    try:
        if jd_image is not None:
            image_bytes = await jd_image.read()
            media_type = jd_image.content_type or "image/png"
            jd_data = extraction.extract_jd_from_image(image_bytes, media_type)
        else:
            jd_data = extraction.extract_jd_from_text(jd_text)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"JD extraction failed: {exc}")

    return {
        "extracted_fields": extracted_fields,
        "jd_data": jd_data,
        # The frontend needs to hold onto the raw resume bytes to eventually
        # save them; simplest Phase 1 approach is to re-upload the same file
        # alongside the confirmed data in POST /api/candidates.
    }


class SaveCandidateFields(BaseModel):
    created_by: str
    extracted_fields: dict
    jd_data: dict


@app.post("/api/candidates")
async def save_candidate(
    created_by: str = Form(...),
    extracted_fields_json: str = Form(...),
    jd_data_json: str = Form(...),
    resume_file: UploadFile = File(...),
):
    """Saves the user-confirmed (possibly edited) extraction result, along
    with the original resume file, as a new candidate row."""
    import json

    try:
        extracted_fields = json.loads(extracted_fields_json)
        jd_data = json.loads(jd_data_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")

    resume_bytes = await resume_file.read()

    try:
        # Upload first so we have a path even if the DB insert path changes later.
        import uuid as _uuid
        temp_id = str(_uuid.uuid4())
        original_resume_path = storage.upload_original_file(
            resume_bytes, resume_file.filename, temp_id
        )
        record = storage.create_candidate_record(
            created_by=created_by,
            role_title=jd_data.get("role_title"),
            extracted_fields=extracted_fields,
            jd_data=jd_data,
            original_resume_path=original_resume_path,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": record}


@app.patch("/api/candidates/{candidate_id}")
def update_candidate(candidate_id: str, extracted_fields: dict):
    try:
        record = storage.update_candidate_fields(candidate_id, extracted_fields)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"candidate": record}


@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: str):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"candidate": record}


@app.post("/api/candidates/{candidate_id}/generate")
def generate_content(candidate_id: str):
    """Phase 2: runs JD-driven generation (titles, skills, responsibilities,
    projects) for a saved candidate and persists the result."""
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    try:
        generated = generation.generate_candidate_content(
            record["extracted_fields"], record["jd_data"]
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}")

    try:
        updated = storage.save_generated_content(candidate_id, generated)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": updated}


class RegenerateSectionRequest(BaseModel):
    company: str
    custom_instruction: Optional[str] = None


@app.post("/api/candidates/{candidate_id}/regenerate-section")
def regenerate_section(candidate_id: str, body: RegenerateSectionRequest):
    """Phase 2 backend support for the future 'regenerate this section only'
    button (Phase 3 UI): regenerates just one company's title/responsibilities/
    projects and merges it back into the candidate's already-generated content
    without touching any other company."""
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not record.get("generated_content"):
        raise HTTPException(
            status_code=400,
            detail="This candidate has no generated content yet. Run /generate first.",
        )

    try:
        new_company_section = generation.regenerate_company_section(
            record["extracted_fields"], record["jd_data"], body.company, body.custom_instruction
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}")

    generated_content = record["generated_content"]
    companies = generated_content.get("companies", [])
    replaced = False
    for i, company_entry in enumerate(companies):
        if company_entry.get("company") == body.company:
            companies[i] = new_company_section
            replaced = True
            break
    if not replaced:
        companies.append(new_company_section)
    generated_content["companies"] = companies

    try:
        updated = storage.save_generated_content(candidate_id, generated_content)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": updated}


class SaveResumeContentRequest(BaseModel):
    extracted_fields: dict
    generated_content: dict


@app.patch("/api/candidates/{candidate_id}/resume-content")
def save_resume_content(candidate_id: str, body: SaveResumeContentRequest):
    """Phase 3: the split-screen editor's autosave/save-draft endpoint. Saves
    both the (possibly hand-edited) extracted fields and generated content in
    one call."""
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    try:
        updated = storage.save_resume_content(
            candidate_id, body.extracted_fields, body.generated_content
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": updated}


class RegenerateSkillsRequest(BaseModel):
    custom_instruction: Optional[str] = None


@app.post("/api/candidates/{candidate_id}/regenerate-skills")
def regenerate_skills(candidate_id: str, body: RegenerateSkillsRequest):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not record.get("generated_content"):
        raise HTTPException(status_code=400, detail="This candidate has no generated content yet. Run /generate first.")

    try:
        result = generation.regenerate_skills(
            record["extracted_fields"], record["jd_data"], body.custom_instruction
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}")

    generated_content = record["generated_content"]
    generated_content["skill_categories"] = result.get("skill_categories", [])

    try:
        updated = storage.save_generated_content(candidate_id, generated_content)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": updated}


class RegenerateCareerObjectiveRequest(BaseModel):
    custom_instruction: Optional[str] = None


@app.post("/api/candidates/{candidate_id}/regenerate-career-objective")
def regenerate_career_objective(candidate_id: str, body: RegenerateCareerObjectiveRequest):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not record.get("generated_content"):
        raise HTTPException(status_code=400, detail="This candidate has no generated content yet. Run /generate first.")

    try:
        result = generation.regenerate_career_objective(
            record["extracted_fields"], record["jd_data"], body.custom_instruction
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"Regeneration failed: {exc}")

    generated_content = record["generated_content"]
    generated_content["career_objective"] = result.get("career_objective", "")

    try:
        updated = storage.save_generated_content(candidate_id, generated_content)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"candidate": updated}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/templates")
def get_templates():
    return {"templates": list_templates(), "recommended_fonts": RECOMMENDED_FONTS, "defaults": DEFAULT_FORMAT_SETTINGS}


def _merge_resume_data(record: dict) -> dict:
    """Mirrors the frontend's mergeIntoResumeData: combines Phase 1 extracted
    fields with Phase 2/3 generated content into one flat shape for rendering."""
    extracted = record.get("extracted_fields") or {}
    generated = record.get("generated_content") or {}
    generated_by_company = {c["company"]: c for c in generated.get("companies", [])}

    work_experience = []
    for job in extracted.get("work_experience", []):
        gen = generated_by_company.get(job.get("company"), {})
        work_experience.append(
            {
                **job,
                "generated_job_title": gen.get("generated_job_title", ""),
                "responsibilities": gen.get("responsibilities", []),
            }
        )

    return {
        "personal_info": extracted.get("personal_info", {}),
        "education": extracted.get("education", []),
        "certifications": extracted.get("certifications", []),
        "languages_known": extracted.get("languages_known", []),
        "career_objective": generated.get("career_objective", ""),
        "skill_categories": generated.get("skill_categories", []),
        "work_experience": work_experience,
    }


class SaveFormatSettingsRequest(BaseModel):
    template_id: str
    font_family: str
    font_size_pt: float
    bold_headers: bool


@app.patch("/api/candidates/{candidate_id}/format")
def save_format(candidate_id: str, body: SaveFormatSettingsRequest):
    try:
        updated = storage.save_format_settings(candidate_id, body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"candidate": updated}


def _build_export_filename(record: dict, export_count: int, extension: str) -> str:
    """name_role.pdf on the first export, then name_role(2).pdf, (3), etc.
    on subsequent exports of the same candidate -- tracked by us via
    export_count rather than left to the browser's own download-collision
    "(1), (2)" renaming."""
    name = (record.get("full_name") or "resume").strip().replace(" ", "_")
    role = (record.get("role_title") or "").strip().replace(" ", "_")
    base = f"{name}_{role}" if role else name
    suffix = "" if export_count <= 1 else f"({export_count})"
    return f"{base}{suffix}.{extension}"


@app.post("/api/candidates/{candidate_id}/export/pdf")
def export_pdf(candidate_id: str):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    format_settings = record.get("format_settings") or DEFAULT_FORMAT_SETTINGS
    resume_data = _merge_resume_data(record)

    try:
        pdf_bytes = pdf_render.render_pdf_bytes_isolated(resume_data, format_settings)
    except Exception as exc:  # noqa: BLE001 -- surface any Playwright/render error clearly to the user
        print("---- PDF RENDER ERROR ----")
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"PDF rendering failed: {type(exc).__name__}: {exc}")

    try:
        path = storage.upload_generated_file(pdf_bytes, candidate_id, "pdf")
        storage.save_export_path(candidate_id, "pdf", path)
        export_count = storage.increment_export_count(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    filename = _build_export_filename(record, export_count, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/candidates/{candidate_id}/export/docx")
def export_docx(candidate_id: str):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    format_settings = record.get("format_settings") or DEFAULT_FORMAT_SETTINGS
    resume_data = _merge_resume_data(record)

    try:
        docx_bytes = docx_render.render_docx_bytes(resume_data, format_settings)
    except Exception as exc:  # noqa: BLE001
        print("---- DOCX RENDER ERROR ----")
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"DOCX rendering failed: {type(exc).__name__}: {exc}")

    try:
        path = storage.upload_generated_file(docx_bytes, candidate_id, "docx")
        storage.save_export_path(candidate_id, "docx", path)
        export_count = storage.increment_export_count(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    filename = _build_export_filename(record, export_count, "docx")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/candidates/{candidate_id}/ats-score")
def check_ats_score(candidate_id: str):
    try:
        record = storage.get_candidate(candidate_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    format_settings = record.get("format_settings") or DEFAULT_FORMAT_SETTINGS
    resume_data = _merge_resume_data(record)
    jd_data = record.get("jd_data") or {}

    result = ats_score.compute_ats_score(resume_data, jd_data, format_settings)

    try:
        updated = storage.save_ats_score(candidate_id, result)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"ats_result": result, "candidate": updated}
