"""
Thin wrapper around Supabase so the rest of the app doesn't need to know
Supabase-specific details. Two responsibilities:
  1. `candidates` table -- structured data (extracted fields, JD, staff name, etc.)
  2. Storage bucket -- the raw uploaded resume file + (in later phases) generated PDFs/DOCX

Run the SQL in supabase_schema.sql (see project root) once in your Supabase
project's SQL editor before using this.
"""
import uuid
from typing import Optional

from supabase import create_client, Client

from .config import settings

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url, key = settings.require_supabase()
        _client = create_client(url, key)
    return _client


def upload_original_file(file_bytes: bytes, filename: str, candidate_id: str) -> str:
    """Uploads the originally-submitted resume file to Supabase Storage and
    returns the storage path (not a public URL -- these files are treated as
    private candidate data)."""
    client = get_client()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    storage_path = f"originals/{candidate_id}/{uuid.uuid4().hex}.{ext}"
    client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        storage_path, file_bytes
    )
    return storage_path


def create_candidate_record(
    *,
    created_by: str,
    role_title: Optional[str],
    extracted_fields: dict,
    jd_data: dict,
    original_resume_path: str,
) -> dict:
    """Inserts a new candidate row after the extraction step. Content
    generation (Phase 2) will update this same row with generated sections."""
    client = get_client()
    candidate_id = str(uuid.uuid4())
    row = {
        "id": candidate_id,
        "created_by": created_by,
        "role_title": role_title,
        "full_name": (extracted_fields.get("personal_info") or {}).get("full_name"),
        "extracted_fields": extracted_fields,
        "jd_data": jd_data,
        "original_resume_path": original_resume_path,
        "status": "extracted",  # -> "generated" -> "finalized" in later phases
    }
    result = client.table("candidates").insert(row).execute()
    return result.data[0]


def update_candidate_fields(candidate_id: str, extracted_fields: dict) -> dict:
    """Used when the user edits the extraction-confirmation screen."""
    client = get_client()
    result = (
        client.table("candidates")
        .update({"extracted_fields": extracted_fields})
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def save_generated_content(candidate_id: str, generated_content: dict) -> dict:
    """Phase 2: saves the JD-driven generated titles/skills/responsibilities/
    projects onto the candidate row and flips status to 'generated'."""
    client = get_client()
    result = (
        client.table("candidates")
        .update({"generated_content": generated_content, "status": "generated"})
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def save_resume_content(candidate_id: str, extracted_fields: dict, generated_content: dict) -> dict:
    """Phase 3: the split-screen editor edits a unified view of both the
    Phase 1 extracted fields (personal info/education/etc, possibly touched
    up) and the Phase 2 generated content (titles/skills/responsibilities/
    projects, possibly hand-edited or reordered). This saves both in one
    call so the editor doesn't need two round trips per autosave."""
    client = get_client()
    result = (
        client.table("candidates")
        .update(
            {
                "extracted_fields": extracted_fields,
                "generated_content": generated_content,
                "status": "edited",
            }
        )
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def save_format_settings(candidate_id: str, format_settings: dict) -> dict:
    """Phase 4: saves the chosen template + font settings. template_id is
    kept in its own column too (for the dashboard's "Template used" filter/
    column) as well as inside format_settings (for font family/size/bold)."""
    client = get_client()
    result = (
        client.table("candidates")
        .update(
            {
                "template_id": format_settings.get("template_id"),
                "format_settings": format_settings,
            }
        )
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def upload_generated_file(file_bytes: bytes, candidate_id: str, extension: str) -> str:
    """Uploads a rendered PDF/DOCX to Supabase Storage and returns the
    storage path. Overwrites any previous export of the same type for this
    candidate (upsert) so re-exporting doesn't pile up old files."""
    client = get_client()
    storage_path = f"generated/{candidate_id}/resume.{extension}"
    client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        storage_path, file_bytes, {"upsert": "true"}
    )
    return storage_path


def save_export_path(candidate_id: str, extension: str, path: str) -> dict:
    client = get_client()
    column = "generated_pdf_path" if extension == "pdf" else "generated_docx_path"
    result = (
        client.table("candidates")
        .update({column: path, "status": "finalized"})
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def increment_export_count(candidate_id: str) -> int:
    """Bumps the export counter and returns the new value, used to build
    versioned filenames (name_role.pdf, then name_role(2).pdf, etc.) instead
    of leaving that to the browser's own download-collision handling. Not
    perfectly atomic (read-then-write) but this is a single-user-at-a-time
    internal tool, so a race here is not a practical concern."""
    client = get_client()
    record = client.table("candidates").select("export_count").eq("id", candidate_id).execute()
    current = record.data[0]["export_count"] if record.data else 0
    new_count = current + 1
    client.table("candidates").update({"export_count": new_count}).eq("id", candidate_id).execute()
    return new_count


def save_ats_score(candidate_id: str, ats_result: dict) -> dict:
    """Saves the overall ATS score (surfaced in the dashboard column) plus
    the full breakdown (for the Templates & Export page's detail view)."""
    client = get_client()
    result = (
        client.table("candidates")
        .update({"ats_score": ats_result["overall_score"], "ats_breakdown": ats_result})
        .eq("id", candidate_id)
        .execute()
    )
    return result.data[0]


def get_download_url(path: str, expires_in: int = 3600) -> str:
    """Returns a temporary signed URL for a private storage object -- used
    for the dashboard's download links and the share-via-link feature."""
    client = get_client()
    result = client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_url(path, expires_in)
    return result["signedURL"] if "signedURL" in result else result.get("signed_url")


def list_candidates(created_by: Optional[str] = None) -> list[dict]:
    client = get_client()
    query = client.table("candidates").select("*").order("created_at", desc=True)
    if created_by:
        query = query.eq("created_by", created_by)
    return query.execute().data


def get_candidate(candidate_id: str) -> Optional[dict]:
    client = get_client()
    result = (
        client.table("candidates").select("*").eq("id", candidate_id).execute()
    )
    return result.data[0] if result.data else None
