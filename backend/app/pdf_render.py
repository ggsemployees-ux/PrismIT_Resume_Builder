"""
Builds a full standalone HTML document from resume_data + format settings,
then renders it to PDF bytes using a headless Chromium browser (Playwright).

Using a real browser for this means Chromium's native print engine handles
page breaks via standard CSS (@page, break-inside: avoid) -- we don't need
to reimplement the frontend's JS measurement-based pagination here. Every
content block gets break-inside: avoid so a bullet/project/job-header is
never split across a page boundary, matching the live preview's behavior.

Fonts: arbitrary font families are supported by loading them from Google
Fonts at render time (the user's own machine has full internet access, even
though this sandbox's network is restricted) -- if a font name isn't on
Google Fonts, Chromium silently falls back to a default sans-serif, which is
an acceptable degradation rather than a hard failure.
"""
import html as html_lib
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from .templates import get_template, FONT_SIZE_RATIOS

PAGE_PADDING_MM = 15  # ~0.6in, matches the frontend preview's page padding


def _esc(text) -> str:
    return html_lib.escape(str(text or ""))


def _render_rich_text(text: str) -> str:
    """Minimal **bold** markdown support, mirroring the frontend's richText.jsx."""
    if not text:
        return ""
    import re

    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    out = []
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(f"<strong>{_esc(part[2:-2])}</strong>")
        else:
            out.append(_esc(part))
    return "".join(out)


def _format_date_range(start, end, is_current) -> str:
    end_label = "Present" if is_current else (end or "—")
    return f"{_esc(start or '—')} &ndash; {_esc(end_label)}"


def _google_font_link(font_family: str) -> str:
    family_param = quote(font_family.strip())
    return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={family_param}:wght@400;700&display=swap">'


def _build_skills_html(resume_data: dict) -> str:
    categories = resume_data.get("skill_categories") or []
    if not categories:
        return ""
    rows = "".join(
        f'<div class="block skill-cat"><strong>{_esc(cat.get("category"))}:</strong> '
        f'{_esc(", ".join(cat.get("skills", [])))}</div>'
        for cat in categories
    )
    return f'<div class="block section-title">Core Technical Skills</div>{rows}'


def _build_experience_html(resume_data: dict) -> str:
    jobs = resume_data.get("work_experience") or []
    if not jobs:
        return ""
    parts = ['<div class="block section-title">Professional Experience</div>']
    for i, job in enumerate(jobs):
        parts.append(
            f'<div class="block job-header">'
            f'<div class="job-header-top"><strong class="job-company-name">{_esc(job.get("company"))}</strong>'
            f'<span class="job-dates">{_format_date_range(job.get("start_date"), job.get("end_date"), job.get("is_current"))}</span></div>'
            f'<div class="job-title">{_esc(job.get("generated_job_title") or job.get("job_title"))}</div>'
            f"</div>"
        )
        for resp in job.get("responsibilities", []):
            parts.append(f'<div class="block bullet"><span>&bull;</span><p>{_render_rich_text(resp)}</p></div>')
        if i < len(jobs) - 1:
            parts.append('<div class="company-gap"></div>')
    return "".join(parts)


def _build_education_html(resume_data: dict) -> str:
    edu = resume_data.get("education") or []
    if not edu:
        return ""
    parts = ['<div class="block section-title">Education</div>']
    for e in edu:
        parts.append(
            f'<div class="block edu-entry">'
            f'<div class="edu-top"><strong>{_esc(e.get("degree"))}</strong>'
            f'<span class="job-dates">{_format_date_range(e.get("start_date"), e.get("end_date"), False)}</span></div>'
            f'<div class="job-company">{_esc(e.get("institution"))}</div>'
            f"</div>"
        )
    return "".join(parts)


def _build_inline_list_html(title: str, items: list) -> str:
    if not items:
        return ""
    return (
        f'<div class="block section-title">{_esc(title)}</div>'
        f'<div class="block inline-list">{_esc(",  ".join(items))}</div>'
    )


def build_html(resume_data: dict, format_settings: dict) -> str:
    template = get_template(format_settings.get("template_id"))
    font_family = format_settings.get("font_family", "Arial")
    font_size_pt = format_settings.get("font_size_pt", 12)
    bold_headers = format_settings.get("bold_headers", True)

    # Fixed size hierarchy (ratios against the body size the user controls):
    # name 20/12, contact 14/12, heading 14/12, body 1.0 -- see templates.py.
    name_size = round(font_size_pt * FONT_SIZE_RATIOS["name"], 1)
    contact_size = round(font_size_pt * FONT_SIZE_RATIOS["contact"], 1)
    heading_size = round(font_size_pt * FONT_SIZE_RATIOS["heading"], 1)
    body_size = font_size_pt

    p = resume_data.get("personal_info") or {}
    contact_bits = [p.get("mobile"), p.get("email"), p.get("location"), p.get("linkedin_url"), p.get("portfolio_url")]
    contact_line = "&nbsp;&nbsp;&bull;&nbsp;&nbsp;".join(_esc(b) for b in contact_bits if b)

    career_objective_html = (
        f'<div class="block section-title">Career Objective</div>'
        f'<div class="block objective">{_render_rich_text(resume_data.get("career_objective"))}</div>'
        if resume_data.get("career_objective")
        else ""
    )

    header_html = f'<div class="block header"><h1>{_esc(p.get("full_name"))}</h1><p class="contact">{contact_line}</p></div>'

    skills_html = _build_skills_html(resume_data)
    experience_html = _build_experience_html(resume_data)
    education_html = _build_education_html(resume_data)
    certs_html = _build_inline_list_html("Certifications", resume_data.get("certifications") or [])
    langs_html = _build_inline_list_html("Languages", resume_data.get("languages_known") or [])

    section_title_css = (
        f"border-bottom: 1.5px solid {template['accent_color']}; padding-bottom: 3px;"
        if template["section_title_style"] == "underline"
        else f"background: {template['accent_color']}18; border-left: 3px solid {template['accent_color']}; padding: 3px 8px;"
    )
    density_scale = 0.75 if template["density"] == "compact" else 1.0

    if template["layout"] == "sidebar":
        sidebar_width_mm = 62
        body_html = f"""
        <div class="sidebar" style="width:{sidebar_width_mm}mm; background:{template['accent_color']}0d;">
          {header_html}
          {skills_html}
          {education_html}
          {certs_html}
          {langs_html}
        </div>
        <div class="main-col" style="margin-left:{sidebar_width_mm}mm;">
          {career_objective_html}
          {experience_html}
        </div>
        """
    else:
        body_html = f"""
        <div class="main-col">
          {header_html}
          {career_objective_html}
          {skills_html}
          {experience_html}
          {education_html}
          {certs_html}
          {langs_html}
        </div>
        """

    google_font_link = _google_font_link(font_family)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
{google_font_link}
<style>
  @page {{ size: A4; margin: {PAGE_PADDING_MM}mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "{font_family}", Arial, sans-serif;
    font-size: {body_size}pt;
    color: #14181f;
    margin: 0;
  }}
  .block {{ break-inside: avoid; margin-bottom: {8 * density_scale}pt; }}
  .header h1 {{ font-size: {name_size}pt; margin: 0 0 4pt; color: #14181f; }}
  .contact {{ font-size: {contact_size}pt; color: #14181f; }}
  .objective {{ font-size: {body_size}pt; line-height: 1.5; color: #14181f; }}
  .section-title {{
    font-size: {heading_size}pt; font-weight: {"700" if bold_headers else "600"};
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: {10 * density_scale}pt;
    {section_title_css}
  }}
  .job-header-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .edu-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .job-company-name {{ font-size: {heading_size}pt; font-weight: {"700" if bold_headers else "600"}; color: #14181f; }}
  .job-title {{ font-size: {body_size}pt; color: #444; margin-top: 1pt; }}
  .job-company {{ font-style: italic; font-size: {body_size}pt; color: #555; }}
  .job-dates {{ font-size: {contact_size}pt; color: #666; white-space: nowrap; }}
  .skill-cat {{ font-size: {body_size}pt; line-height: 1.5; color: #14181f; }}
  .bullet {{ display: flex; gap: 6pt; line-height: 1.45; font-size: {body_size}pt; }}
  .bullet span {{ color: #14181f; }}
  .bullet p {{ margin: 0; color: #14181f; }}
  .inline-list {{ font-size: {body_size}pt; color: #14181f; }}
  .sidebar {{ position: fixed; top: 0; left: 0; height: 100%; padding: {PAGE_PADDING_MM}mm; }}
  .main-col {{ padding-top: 0; }}
  .company-gap {{ height: {14 * density_scale}pt; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def render_pdf_bytes(resume_data: dict, format_settings: dict) -> bytes:
    html_content = build_html(resume_data, format_settings)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
    return pdf_bytes


# --- Windows + uvicorn --reload compatibility -----------------------------
# On Windows, `uvicorn --reload` forces asyncio onto an event loop type that
# does not support subprocess creation, which Playwright needs to launch
# Chromium -- calling render_pdf_bytes() directly from a FastAPI request
# handler then fails with a bare "NotImplementedError". Running the render in
# a fresh child process sidesteps this entirely, since the child process
# gets its own default event loop policy, unaffected by uvicorn's reload
# settings in the parent process. This works identically on macOS/Linux too,
# just with a small (harmless) process-startup overhead.
import concurrent.futures


def _render_pdf_worker(resume_data: dict, format_settings: dict) -> bytes:
    return render_pdf_bytes(resume_data, format_settings)


def render_pdf_bytes_isolated(resume_data: dict, format_settings: dict) -> bytes:
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_render_pdf_worker, resume_data, format_settings)
        return future.result()
