"""
Defines the 4 selectable resume templates. Each is a set of design tokens
(colors, spacing density, layout) rather than raw CSS -- both pdf_render.py
(HTML/CSS -> Playwright) and docx_render.py (python-docx) read from the same
token set so the two output formats stay visually aligned without needing
byte-identical styling (per your call that pixel-perfect PDF/DOCX parity
isn't required).

"classic" and "modern" and "compact" are single-column, ATS-safe layouts --
differing in density and accent styling only. "sidebar" is a genuine
two-column layout: a narrow left sidebar (contact, skills, education,
certifications, languages) alongside a main column (career objective +
experience), but ONLY on page 1 -- pages 2+ fall back to a full-width single
column for the overflowing experience content, since sidebar content is
short and reliably fits on page 1 in practice. This is a common structural
pattern in real two-column resume templates, and avoids the unreliable
alternative of trying to paginate two independent columns simultaneously.
"""

TEMPLATES = {
    "classic": {
        "id": "classic",
        "name": "Classic Single-Column",
        "description": "Plain reverse-chronological layout, no tables or columns -- maximum ATS compatibility.",
        "layout": "single",
        "accent_color": "#0b1220",
        "section_title_style": "underline",
        "density": "normal",
    },
    "modern": {
        "id": "modern",
        "name": "Modern Accent",
        "description": "Clean single-column layout with a subtle color accent on section headers.",
        "layout": "single",
        "accent_color": "#2f96da",
        "section_title_style": "accent-bar",
        "density": "normal",
    },
    "sidebar": {
        "id": "sidebar",
        "name": "Two-Column Sidebar",
        "description": "Contact, skills, and education in a sidebar; experience in the main column.",
        "layout": "sidebar",
        "accent_color": "#1c2740",
        "section_title_style": "underline",
        "density": "normal",
    },
    "compact": {
        "id": "compact",
        "name": "Compact Dense",
        "description": "Tighter spacing and smaller headers -- fits more content per page for senior candidates.",
        "layout": "single",
        "accent_color": "#0b1220",
        "section_title_style": "underline",
        "density": "compact",
    },
}

DEFAULT_TEMPLATE_ID = "classic"

RECOMMENDED_FONTS = [
    "Arial", "Calibri", "Georgia", "Garamond", "Helvetica",
    "Roboto", "Open Sans", "Lato", "Merriweather", "Montserrat",
    "Poppins", "Source Sans Pro", "PT Serif", "Inter", "Tinos",
]

DEFAULT_FORMAT_SETTINGS = {
    "template_id": DEFAULT_TEMPLATE_ID,
    "font_family": "Arial",
    "font_size_pt": 12,
    "bold_headers": True,
}

# Fixed size hierarchy, expressed as ratios against the body-text size
# (font_size_pt is the body size the user actually controls; everything
# else scales proportionally so the hierarchy always holds together).
# Base values: name 20 / contact 14 / heading 14 / body 12.
FONT_SIZE_RATIOS = {
    "name": 20 / 12,
    "contact": 14 / 12,
    "heading": 14 / 12,  # section titles, company names, job titles
    "body": 1.0,          # bullets, body text
}


def get_template(template_id: str) -> dict:
    return TEMPLATES.get(template_id, TEMPLATES[DEFAULT_TEMPLATE_ID])


def list_templates() -> list[dict]:
    return list(TEMPLATES.values())
