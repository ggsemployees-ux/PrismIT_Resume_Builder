"""
Builds a .docx file from resume_data + format settings using python-docx.
Visually mirrors the chosen PDF template (same font, size hierarchy, section
styling, accent usage) but is NOT pixel-identical -- per your earlier
confirmation that isn't required.

Font size hierarchy matches pdf_render.py exactly: name / contact / heading /
body sizes are all derived from FONT_SIZE_RATIOS in templates.py, so the two
output formats stay visually consistent with each other.

There is no separate "projects" section -- project-level detail is folded
directly into the responsibility bullets by the generation step, so this
renderer only ever sees one flat responsibilities list per company.

The "sidebar" template is approximated as a two-column borderless table (a
standard technique for sidebar-style resumes in Word) rather than a true
repeating-per-page sidebar -- Word documents don't support a repeating
side-column the way a browser's fixed-position element does, so this is a
disclosed simplification rather than a silent mismatch.
"""
import io
import re

from docx import Document
from docx.shared import Pt, RGBColor, Mm

from .templates import get_template, FONT_SIZE_RATIOS

BLACK = RGBColor(0x14, 0x18, 0x1F)
MUTED = RGBColor(0x66, 0x66, 0x66)


def _hex_to_rgbcolor(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _sizes(font_size_pt: float) -> dict:
    """Derives the fixed name/contact/heading/body hierarchy from the body
    size the user controls -- mirrors pdf_render.py exactly."""
    return {
        "name": round(font_size_pt * FONT_SIZE_RATIOS["name"], 1),
        "contact": round(font_size_pt * FONT_SIZE_RATIOS["contact"], 1),
        "heading": round(font_size_pt * FONT_SIZE_RATIOS["heading"], 1),
        "body": font_size_pt,
    }


def _set_default_font(document: Document, font_family: str, font_size_pt: float):
    style = document.styles["Normal"]
    style.font.name = font_family
    style.font.size = Pt(font_size_pt)


def _format_date_range(start, end, is_current) -> str:
    end_label = "Present" if is_current else (end or "—")
    return f"{start or '—'} – {end_label}"


def _render_rich_text_into_paragraph(paragraph, text: str, size_pt: float, color=BLACK):
    """Splits **bold** markers into separate bold/non-bold runs within one paragraph."""
    parts = re.split(r"(\*\*[^*]+\*\*)", text or "")
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            run = paragraph.add_run(part)
        run.font.size = Pt(size_pt)
        run.font.color.rgb = color


def _add_section_title(document: Document, text: str, accent_rgb: RGBColor, bold_headers: bool, sizes: dict):
    p = document.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = bold_headers
    run.font.size = Pt(sizes["heading"])
    run.font.color.rgb = accent_rgb
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    return p


def _add_job_header(document: Document, company: str, dates: str, title: str, sizes: dict):
    """Company bold and first, date range on the same line (tab-aligned to
    the right); job title secondary on the line below -- per the requested
    layout swap."""
    p = document.add_paragraph()
    company_run = p.add_run(company or "—")
    company_run.bold = True
    company_run.font.size = Pt(sizes["heading"])
    company_run.font.color.rgb = BLACK
    tab = p.add_run(f"\t{dates}")
    tab.font.size = Pt(sizes["contact"])
    tab.font.color.rgb = MUTED
    p.paragraph_format.tab_stops.add_tab_stop(Mm(160))

    title_p = document.add_paragraph()
    title_run = title_p.add_run(title or "")
    title_run.font.size = Pt(sizes["body"])
    title_run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    title_p.paragraph_format.space_after = Pt(2)


def _build_body(document: Document, resume_data: dict, template: dict, sizes: dict, bold_headers: bool):
    accent_rgb = _hex_to_rgbcolor(template["accent_color"])

    if resume_data.get("career_objective"):
        _add_section_title(document, "Career Objective", accent_rgb, bold_headers, sizes)
        p = document.add_paragraph()
        _render_rich_text_into_paragraph(p, resume_data["career_objective"], sizes["body"])
        p.paragraph_format.space_after = Pt(8)

    if resume_data.get("skill_categories"):
        _add_section_title(document, "Core Technical Skills", accent_rgb, bold_headers, sizes)
        for cat in resume_data["skill_categories"]:
            p = document.add_paragraph()
            label = p.add_run(f"{cat.get('category')}: ")
            label.bold = True
            label.font.size = Pt(sizes["body"])
            label.font.color.rgb = BLACK
            rest = p.add_run(", ".join(cat.get("skills", [])))
            rest.font.size = Pt(sizes["body"])
            rest.font.color.rgb = BLACK
            p.paragraph_format.space_after = Pt(2)

    if resume_data.get("work_experience"):
        _add_section_title(document, "Professional Experience", accent_rgb, bold_headers, sizes)
        jobs = resume_data["work_experience"]
        for i, job in enumerate(jobs):
            _add_job_header(
                document,
                job.get("company"),
                _format_date_range(job.get("start_date"), job.get("end_date"), job.get("is_current")),
                job.get("generated_job_title") or job.get("job_title"),
                sizes,
            )
            for resp in job.get("responsibilities", []):
                p = document.add_paragraph(style="List Bullet")
                _render_rich_text_into_paragraph(p, resp, sizes["body"])
            if i < len(jobs) - 1:
                gap_p = document.add_paragraph()
                gap_p.paragraph_format.space_after = Pt(10)

    if resume_data.get("education"):
        _add_section_title(document, "Education", accent_rgb, bold_headers, sizes)
        for edu in resume_data["education"]:
            p = document.add_paragraph()
            run = p.add_run(edu.get("degree", ""))
            run.bold = True
            run.font.size = Pt(sizes["heading"])
            run.font.color.rgb = BLACK
            tab = p.add_run(f"\t{_format_date_range(edu.get('start_date'), edu.get('end_date'), False)}")
            tab.font.size = Pt(sizes["contact"])
            tab.font.color.rgb = MUTED
            p.paragraph_format.tab_stops.add_tab_stop(Mm(160))
            comp_p = document.add_paragraph()
            comp_run = comp_p.add_run(edu.get("institution", ""))
            comp_run.italic = True
            comp_run.font.size = Pt(sizes["body"])
            comp_run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    for title, items in (("Certifications", resume_data.get("certifications")), ("Languages", resume_data.get("languages_known"))):
        if items:
            _add_section_title(document, title, accent_rgb, bold_headers, sizes)
            p = document.add_paragraph()
            run = p.add_run(", ".join(items))
            run.font.size = Pt(sizes["body"])
            run.font.color.rgb = BLACK


def render_docx_bytes(resume_data: dict, format_settings: dict) -> bytes:
    template = get_template(format_settings.get("template_id"))
    font_family = format_settings.get("font_family", "Arial")
    font_size_pt = format_settings.get("font_size_pt", 12)
    bold_headers = format_settings.get("bold_headers", True)
    sizes = _sizes(font_size_pt)

    document = Document()
    _set_default_font(document, font_family, sizes["body"])
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = section.right_margin = section.top_margin = section.bottom_margin = Mm(15)

    p = resume_data.get("personal_info") or {}
    header_p = document.add_paragraph()
    header_run = header_p.add_run(p.get("full_name", "—"))
    header_run.bold = True
    header_run.font.size = Pt(sizes["name"])
    header_run.font.color.rgb = BLACK
    header_p.paragraph_format.space_after = Pt(2)

    contact_bits = [p.get("mobile"), p.get("email"), p.get("location"), p.get("linkedin_url"), p.get("portfolio_url")]
    contact_line = "   •   ".join(b for b in contact_bits if b)
    contact_p = document.add_paragraph()
    contact_run = contact_p.add_run(contact_line)
    contact_run.font.size = Pt(sizes["contact"])
    contact_run.font.color.rgb = BLACK
    contact_p.paragraph_format.space_after = Pt(8)

    if template["layout"] == "sidebar":
        # Two-column borderless table approximation. Sidebar column holds
        # skills/education/certs/languages; main column holds career
        # objective + experience. See module docstring for the limitation.
        table = document.add_table(rows=1, cols=2)
        table.autofit = False
        table.columns[0].width = Mm(60)
        table.columns[1].width = Mm(120)
        sidebar_cell, main_cell = table.rows[0].cells

        sidebar_data = {
            "skill_categories": resume_data.get("skill_categories"),
            "education": resume_data.get("education"),
            "certifications": resume_data.get("certifications"),
            "languages_known": resume_data.get("languages_known"),
        }
        main_data = {
            "career_objective": resume_data.get("career_objective"),
            "work_experience": resume_data.get("work_experience"),
        }

        _build_into_cell(sidebar_cell, sidebar_data, template, sizes, bold_headers)
        _build_into_cell(main_cell, main_data, template, sizes, bold_headers)
    else:
        _build_body(document, resume_data, template, sizes, bold_headers)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _build_into_cell(cell, data: dict, template: dict, sizes: dict, bold_headers: bool):
    """Mirrors _build_body's section rendering but targets a table cell
    (which has its own paragraph collection) instead of the top-level
    Document -- used only for the sidebar template's two columns."""
    accent_rgb = _hex_to_rgbcolor(template["accent_color"])
    first = True

    def para():
        nonlocal first
        if first:
            first = False
            return cell.paragraphs[0]
        return cell.add_paragraph()

    if data.get("career_objective"):
        p = para()
        run = p.add_run("CAREER OBJECTIVE")
        run.bold = bold_headers
        run.font.color.rgb = accent_rgb
        run.font.size = Pt(sizes["heading"])
        p = para()
        run = p.add_run(data["career_objective"])
        run.font.size = Pt(sizes["body"])
        run.font.color.rgb = BLACK

    if data.get("skill_categories"):
        p = para()
        run = p.add_run("CORE TECHNICAL SKILLS")
        run.bold = bold_headers
        run.font.color.rgb = accent_rgb
        run.font.size = Pt(sizes["heading"])
        for cat in data["skill_categories"]:
            p = para()
            label = p.add_run(f"{cat.get('category')}: ")
            label.bold = True
            label.font.size = Pt(sizes["body"])
            label.font.color.rgb = BLACK
            rest = p.add_run(", ".join(cat.get("skills", [])))
            rest.font.size = Pt(sizes["body"])
            rest.font.color.rgb = BLACK

    if data.get("work_experience"):
        p = para()
        run = p.add_run("PROFESSIONAL EXPERIENCE")
        run.bold = bold_headers
        run.font.color.rgb = accent_rgb
        run.font.size = Pt(sizes["heading"])
        jobs = data["work_experience"]
        for i, job in enumerate(jobs):
            p = para()
            run = p.add_run(job.get("company") or "—")
            run.bold = True
            run.font.size = Pt(sizes["heading"])
            run.font.color.rgb = BLACK
            p2 = para()
            r2 = p2.add_run(
                f"{job.get('generated_job_title') or job.get('job_title') or ''} ({_format_date_range(job.get('start_date'), job.get('end_date'), job.get('is_current'))})"
            )
            r2.font.size = Pt(sizes["contact"])
            r2.font.color.rgb = MUTED
            for resp in job.get("responsibilities", []):
                p3 = para()
                run3 = p3.add_run(f"• {resp}")
                run3.font.size = Pt(sizes["body"])
                run3.font.color.rgb = BLACK
            if i < len(jobs) - 1:
                para()  # blank paragraph for a visible gap between companies

    if data.get("education"):
        p = para()
        run = p.add_run("EDUCATION")
        run.bold = bold_headers
        run.font.color.rgb = accent_rgb
        run.font.size = Pt(sizes["heading"])
        for edu in data["education"]:
            p = para()
            run = p.add_run(f"{edu.get('degree')} — {edu.get('institution')}")
            run.font.size = Pt(sizes["body"])
            run.font.color.rgb = BLACK

    for title, items in (("CERTIFICATIONS", data.get("certifications")), ("LANGUAGES", data.get("languages_known"))):
        if items:
            p = para()
            run = p.add_run(title)
            run.bold = bold_headers
            run.font.color.rgb = accent_rgb
            run.font.size = Pt(sizes["heading"])
            p2 = para()
            run2 = p2.add_run(", ".join(items))
            run2.font.size = Pt(sizes["body"])
            run2.font.color.rgb = BLACK
