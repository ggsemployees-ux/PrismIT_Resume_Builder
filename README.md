# Prism IT Hub — Resume Builder (Phase 1)

This is Phase 1 of the resume generator: **upload → extract → confirm/edit → save**.
It does NOT yet do JD-driven content generation, templates, PDF/DOCX export, or ATS
scoring — those are Phases 2–5, built on top of this foundation once you approve it.

## What's included in this phase

- No-password "who's working today?" name picker (staff identity, stored per-browser)
- Dashboard shell with a candidate table, "My candidates" / "All candidates" toggle,
  and filters (name, role, date, staff member) — shows an empty state until you add
  your first candidate
- Upload screen: candidate's old resume (PDF or DOCX) + JD (pasted text or an image)
- OpenAI-powered extraction of personal info, education, work experience (company +
  dates), certifications, LinkedIn/portfolio links, and languages — with a prompt if
  any expected section is missing from the resume
- A fully editable confirmation screen for everything extracted, before it's saved
- Saving writes the candidate record to Supabase (database) and the original resume
  file to Supabase Storage

## Stack

- **Frontend**: React + Vite, plain CSS (no Tailwind), React Router
- **Backend**: Python + FastAPI
- **Database & file storage**: Supabase (one free account covers both)
- **AI extraction**: OpenAI API (`gpt-4o-mini` by default), including vision for image JDs

## One-time setup

### 1. Supabase

1. Create a free project at https://supabase.com
2. In the SQL Editor, run everything in `backend/supabase_schema.sql`
3. Go to Storage → New bucket → name it exactly `resumes` → keep it private (not public)
4. Go to Project Settings → API → copy your Project URL and the `service_role` secret key
   (NOT the `anon` key — the backend needs the service role key to write on behalf of
   any staff member without per-user Supabase accounts)

### 2. OpenAI API key

1. Go to https://platform.openai.com/api-keys
2. Log in / sign up, click "Create new secret key"
3. Copy it immediately — it's shown only once
4. Make sure there's a payment method on the account (Settings → Billing) — the API
   won't work on a brand-new account with $0 credit
5. The backend defaults to `gpt-4o-mini` (cheap, supports both JSON output and image
   input for JD screenshots). OpenAI renames/replaces models often — if `gpt-4o-mini`
   has been retired by the time you set this up, check
   https://platform.openai.com/docs/models for their current cost-effective
   vision-capable model and put its name in `OPENAI_MODEL` in your `.env` file instead

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# now open .env and fill in OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# also edit STAFF_NAMES to your actual staff members, comma-separated
uvicorn app.main:app --reload --port 8000
```

Leave this running. Visit http://localhost:8000/api/health — you should see `{"status":"ok"}`.

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 — you should see the "Who's working today?" screen.

## Trying it end to end

1. Pick or type your name
2. Click "+ New candidate resume"
3. Upload a real resume (PDF/DOCX) and paste a JD (or upload a JD screenshot)
4. Click "Extract details" — this calls OpenAI twice (once for the resume, once for
   the JD) and returns editable fields
5. Review/correct anything the extraction got wrong, then "Confirm & save candidate"
6. You'll land back on the dashboard and see the new row

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Frontend loads but names/candidates never load, spinner forever | Backend terminal isn't running, or crashed — check that terminal window |
| "Couldn't reach the server" on the name picker | Backend isn't running on port 8000, or `.env` has a typo |
| Extraction fails with a 502 error | Check `OPENAI_API_KEY` in `.env` is correct and has billing enabled |
| Saving a candidate fails | Check `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` in `.env`, and that you ran the SQL schema + created the `resumes` bucket |
| "model not found" / "model has been deprecated" error | OpenAI retired the model in `OPENAI_MODEL` — check https://platform.openai.com/docs/models and update the value in `.env` |

## Phase 2 — JD-driven content generation

Adds:
- A generation step that takes the confirmed Phase 1 data and produces, per your spec:
  - Job titles per company, adjusted to align with the JD (company names and dates are
    never sent to the model as editable fields, so they cannot change)
  - A skills list rewritten to match the JD's required/preferred skills
  - Per-company responsibilities and realistic, JD-aligned projects (not copied from
    the old resume)
- An elaboration profile that automatically decides how much detail to generate per
  company: 1-2 companies get more elaborate content; 3+ companies get more concise
  content per company; 15+ years of estimated total experience gets more overall room
  regardless of company count
- A "regenerate this company only" action, so one section can be redone without
  affecting the rest (backend support for the button Phase 3's UI will add)
- A simple review page (`/candidate/:id/generate`) showing the raw generated content so
  you can judge generation quality before Phase 3 builds the polished split-screen
  editor around it — this page is intentionally plain, not the final wizard UI

**Before running Phase 2**, re-run the ALTER TABLE statement now in
`backend/supabase_schema.sql` (the new `generated_content` column) in your Supabase
SQL editor — it's additive, so re-running the whole file is safe even though you ran
part of it already in Phase 1.

To try it: from the dashboard, click any candidate's name → "Generate resume content".

## Phase 3 — Split-screen wizard editor

Adds the real editing experience, at `/candidate/:id/edit` (reach it via "Open in editor"
after generating content):

- **Left panel (40%)**: accordion sections — Personal Info, Skills, one section per
  company (job title, responsibilities, projects, plus a "Regenerate this company"
  button wired to Phase 2's per-section regeneration), and Education. Collapsed by
  default, single-expand mode, with "Continue to [next]" buttons guiding progression
- **Right panel (60%)**: a live multi-page print preview. Pages are rendered at real A4
  proportions with a light-gray backdrop, white page canvases with drop shadows, a
  "Page X of Y" badge on each, and a gap between pages. Pagination is done by actually
  measuring each content block's rendered height and never splitting a block (a bullet,
  a project, a job header) across a page boundary — if it doesn't fit, the whole block
  moves to the next page
- **Ghost placeholder state**: before any real data exists, the preview shows a dimmed
  placeholder resume so you can see the shape of the output immediately
- **Zoom bar**: sticky `[ − ] 100% [ + ]` plus "Fit to window", which measures the
  actual panel width and scales the page to match
- **Auto-scroll sync**: opening an accordion section scrolls the preview to that
  section, even if it's on page 2
- **Rich text**: responsibility bullets support a bold toggle (select text, click "B")
  without pulling in a heavy rich-text editor dependency
- **Autosave**: edits save automatically 2 seconds after you stop typing (small "Saving
  .../Saved" indicator in the header)
- **Export button**: present in the header per the agreed layout, but intentionally
  disabled with a tooltip — actual PDF/DOCX generation is Phase 4

**Known Phase 3 scope limits (by design):**
- Only one template look is used for the preview right now (a clean ATS-safe single
  column) — the 4 selectable templates and font freedom are Phase 4
- "Overflow" detection currently just outlines a block that's too tall to fit any page
  cleanly (dashed red outline) — a friendlier warning banner can be added once templates
  exist to warn against in Phase 4
- The Export button is a visual placeholder only

## Phase 3.5 — Career objective, categorized skills, seniority-aware detail, prompt-steered regeneration

- **Career Objective**: a new, JD-targeted paragraph generated for the top of the resume,
  written to make a specific, persuasive case for why the candidate fits the target role
  (not generic filler)
- **Core Technical Skills**: restructured from a flat list into named categories (e.g.
  "Programming & Coding: Java, Python..."), with the AI choosing category names
  dynamically based on what the JD/role actually calls for
- **Elaboration profile now combines company count AND years of experience**: a
  13-year candidate gets meaningfully more detail per project even across several
  companies, not just when they've stayed at 1-2 companies (see `experience.py`'s
  seniority tiers: junior/mid/senior/veteran)
- **Regenerate with a custom instruction**: every regenerate action (career objective,
  skills, or any individual company) now has an optional text field next to it — type
  something like "add 3 more points like this" or "emphasize cloud experience" and it
  steers that specific regeneration

No new Supabase schema changes needed — this only changes the JSON shape stored inside
the existing `generated_content` column.

## Phase 4 — Templates, fonts, and real PDF/DOCX export

This is the final phase. Adds:

- **4 real templates**: Classic (single-column, ATS-safe), Modern (accent-highlighted
  section headers), Two-Column Sidebar (contact/skills/education in a sidebar that
  repeats on every page, experience in the main column), and Compact (tighter spacing
  for senior candidates with a lot of content)
- **Free font choice**: pick from a curated list of common resume fonts, or type any
  font name you want — plus font size and a bold-headers toggle
- **A live preview that matches the real export**: the template/font picker screen
  (`/candidate/:id/finalize`) shows the actual chosen template and font live, using the
  same preview engine as the editor
- **Real PDF export**: rendered server-side using a headless Chromium browser
  (Playwright) from the exact same content — so what you see in the preview is what
  you get in the PDF, not an approximation
- **Real DOCX export**: built with python-docx, visually mirroring the chosen template
  (same fonts, structure, accent color) but not byte-identical, per your call that
  pixel-perfect parity isn't required. The sidebar template's DOCX version uses a
  two-column table (a standard Word technique) rather than a true repeating sidebar,
  since Word documents don't support a per-page-repeating side column the way a
  browser can — this is a disclosed simplification, not a silent gap
- **Export UI**: "Export PDF" as the primary button in the header, with a small
  dropdown arrow next to it for "Download as Word (.docx)" — matches your split-button
  spec exactly. Clicking either saves your template/font choice first, then downloads
  the file
- **Storage**: every export is also saved to Supabase Storage under
  `generated/<candidate_id>/resume.pdf` / `.docx`, so it persists for later (full
  dashboard download/history wiring is Phase 6, but the files are being saved now)

### New one-time setup step for Phase 4

Playwright needs its own browser binary (separate from the pip package) to actually
render PDFs:

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

This downloads Chromium (~150-300MB) — only needs to run once. If it fails on your
network, try again on a less restrictive connection; corporate firewalls sometimes
block the download.

Re-run `backend/supabase_schema.sql` in the Supabase SQL editor before using Phase 4 —
it adds `format_settings`, `generated_pdf_path`, and `generated_docx_path` columns
(additive, safe to re-run in full).

### Try it end to end

Dashboard → candidate → Generate → Open in editor → "Continue to Templates & Export" →
pick a template and font → "Export PDF" (or the dropdown arrow for DOCX).

## Resume Writer content spec — strict generation rules

Generation now follows a detailed content-quality spec, layered on top of everything
else:

- **No fabrication**: never invents certifications, degrees, or specific numbers/
  percentages/metrics unless they were actually supplied. The one explicit exception:
  **projects are still synthesized** to fit the JD/tech stack (your call) — everything
  else in the no-fabrication rule is strict.
- **Experience-tier calibration**: 0-2 / 3-5 / 6-8 / 8+ years, each with matching
  language (0-2 stays execution-level; 8+ can claim architecture/leadership) — never
  inflated beyond what the dates support.
- **Bullet formula**: Action + Technology + Scenario + Purpose + Result, varied action
  verbs, no buzzword filler ("spearheaded," "revolutionized," etc. are explicitly banned
  in the prompt).
- **Recency-based bullet/project volume per role** (replaces the old flat company-count
  rule): most recent role gets 8-12 bullets / 2-3 projects, next-most-recent gets 6-9 /
  2, older roles get 5-8 / 1-2 — automatically capped lower for any role under a year,
  regardless of how recent it is.
- **No duplicate bullets across companies.**
- **JD Gap flagging**: if the JD needs something the candidate's real background
  doesn't support, it's flagged as "JD Gap – Candidate confirmation required" on the
  generation review screen (staff-only — this never appears on the candidate's actual
  resume, PDF, or DOCX).
- **Professional Summary tone**: factual, 4-6 concrete points, no "highly motivated
  professional" filler.

No schema or endpoint changes for this — it's entirely inside the existing generation
prompts (`backend/app/generation.py`, `backend/app/experience.py`) and one new
`jd_gaps` field inside the existing `generated_content` JSON.

## Post-launch refinements

A round of polish requested after trying the full build end to end:

1. **Career Objective styling** — no longer italic; matches the rest of the resume's
   body font style
2. **Projects folded into bullets** — there is no longer a separate Projects section
   under each company. Project-level detail (what was built, what tech was used, what
   problem it solved) is now generated directly inside the responsibility bullets
   themselves — more explanatory, not vague. Bullet counts per role went up
   accordingly (10-14 / 8-11 / 6-9 by recency, instead of the old 8-12 / 6-9 / 5-8)
   since that detail has to live somewhere
3. **Bullet text color** — fixed to solid black, matching Core Technical Skills,
   instead of a lighter/muted tone
4. **Gap between companies** — added visible spacing between each company block in
   Professional Experience for easier scanning
5. **Job header layout swap** — company name is now bold and shown first, with the
   date range on the same line, right-aligned. Job title is now the secondary line
   underneath (previously title was first/bold and company was secondary)
6. **Font-size control actually works now** — this was a real bug: the number field
   changed nothing visible before. Now it's a functional hierarchy: the number you set
   is the body-text size; Name (20/12 ratio), contact info and section
   headings/company names (14/12 ratio) all scale proportionally around it, in both the
   live preview and the exported PDF/DOCX. This replaced an earlier idea of "select
   text and resize just that selection," which the user confirmed wasn't needed once
   the standard control was fixed
7. **Export filename versioning** — exports are now named `Name_Role.pdf` on the first
   export, then `Name_Role(2).pdf`, `(3)`, etc. on repeat exports of the same
   candidate — tracked server-side via a new `export_count` column, rather than left to
   the browser's own download-collision renaming
8. **ATS Score** — new "Check ATS" button on the Templates & Export page, next to
   Export PDF. Scores 0-100 based on three measurable factors: JD keyword match (50%),
   structural format compliance (30% — e.g. flags the sidebar template's multi-column
   layout as a minor risk for some ATS parsers), and parseability (20% — contact info
   present, core sections present). This is an internal directional signal, not a claim
   about how any specific real-world ATS (Workday, Greenhouse, etc.) would score the
   resume, since those are proprietary. The score also now populates the Dashboard's
   "ATS Score" column, which had been sitting empty since Phase 1

**New Supabase columns for this round**: `export_count` (integer, defaults to 0) and
`ats_breakdown` (jsonb, stores the full score breakdown). Re-run the full
`backend/supabase_schema.sql` in the SQL editor — additive, safe to re-run.

## Known Phase 1 limitations (by design — later phases handle these)

- No JD-driven title/skills/project generation yet (Phase 2)
- No template selection or PDF/DOCX export yet (Phase 4)
- No ATS scoring yet (Phase 5)
- No resume versioning UI yet (Phase 6) — each save currently creates one row
- CORS is wide open (`*`) for local development — tighten this before any real deployment
- The `service_role` Supabase key bypasses Row Level Security entirely. That's fine for
  an internal tool called only from your own backend, but never expose this key to the
  frontend or commit it to git.

## Project structure

```
backend/
  app/
    main.py          FastAPI routes
    config.py         env var loading
    file_parsing.py   PDF/DOCX -> plain text
    extraction.py      OpenAI calls for structured extraction
    storage.py         Supabase reads/writes
  supabase_schema.sql
  requirements.txt
  .env.example

frontend/
  src/
    App.jsx
    StaffContext.jsx
    api.js
    pages/            Dashboard, NamePicker, NewCandidate
    components/        Header, UploadStep, ExtractionConfirmStep, PrismLogo
    styles/            tokens.css (brand colors), global.css
  public/
    prism-logo.jpeg   your actual logo
```

## Next up (once you approve this phase)

**Phase 2** — JD-driven generation: job titles, skills, and realistic projects per
company, with the 1–4 page flex logic based on experience/company count.
