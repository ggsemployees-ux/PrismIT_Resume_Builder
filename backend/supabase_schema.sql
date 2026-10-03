-- Run this once in your Supabase project's SQL editor (Project -> SQL Editor -> New query).
-- This creates the one table Phase 1 needs. Later phases will add columns
-- (generated_content, ats_score, template_id, versions, etc.) via ALTER TABLE
-- statements rather than recreating this table.

create table if not exists candidates (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  created_by text not null,               -- staff member name from the name-picker
  role_title text,                        -- e.g. "Software Developer", "Data Engineer"
  full_name text,                         -- candidate's name, pulled up for dashboard display
  extracted_fields jsonb not null,        -- personal_info / education / work_experience / certifications / languages
  jd_data jsonb not null,                 -- role_title / full_text / required_skills / preferred_skills / responsibilities
  original_resume_path text not null,     -- path inside the Supabase Storage bucket
  status text not null default 'extracted', -- extracted -> generated -> finalized (later phases)
  ats_score numeric,                      -- filled in Phase 5
  template_id text                        -- filled in Phase 4
);

create index if not exists candidates_created_by_idx on candidates (created_by);
create index if not exists candidates_created_at_idx on candidates (created_at desc);

-- Phase 2 addition: run this once in the SQL editor to add the column for
-- generated content (job titles, skills, responsibilities, projects).
alter table candidates add column if not exists generated_content jsonb;

-- Also create a Storage bucket named "resumes" (Project -> Storage -> New bucket,
-- name it exactly "resumes", keep it private/not public) before uploading files.
-- (You should have already done this in Phase 1 -- no action needed if so.)

-- Phase 4 addition: run this once in the SQL editor to add columns for the
-- chosen template/font settings and the generated file paths.
alter table candidates add column if not exists format_settings jsonb;
alter table candidates add column if not exists generated_pdf_path text;
alter table candidates add column if not exists generated_docx_path text;

-- Phase 5-ish addition (post-launch refinement): export filename versioning.
alter table candidates add column if not exists export_count integer not null default 0;
alter table candidates add column if not exists ats_breakdown jsonb;
