import { useState } from "react";
import { saveCandidate } from "../api";
import "./ExtractionConfirmStep.css";

const emptyEducation = () => ({ degree: "", institution: "", start_date: "", end_date: "" });
const emptyWork = () => ({ company: "", job_title: "", start_date: "", end_date: "", is_current: false });

export default function ExtractionConfirmStep({ resumeFile, initialFields, jdData, createdBy, onBack, onSaved }) {
  const [fields, setFields] = useState(() => normalizeFields(initialFields));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function updatePersonal(key, value) {
    setFields((f) => ({ ...f, personal_info: { ...f.personal_info, [key]: value } }));
  }

  function updateListItem(listKey, index, key, value) {
    setFields((f) => {
      const list = [...f[listKey]];
      list[index] = { ...list[index], [key]: value };
      return { ...f, [listKey]: list };
    });
  }

  function addListItem(listKey, factory) {
    setFields((f) => ({ ...f, [listKey]: [...f[listKey], factory()] }));
  }

  function removeListItem(listKey, index) {
    setFields((f) => ({ ...f, [listKey]: f[listKey].filter((_, i) => i !== index) }));
  }

  function updateSimpleList(listKey, index, value) {
    setFields((f) => {
      const list = [...f[listKey]];
      list[index] = value;
      return { ...f, [listKey]: list };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const result = await saveCandidate({ createdBy, extractedFields: fields, jdData, resumeFile });
      onSaved(result.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="confirm-step">
      {fields.missing_sections?.length > 0 && (
        <div className="missing-banner">
          <strong>Heads up:</strong> we couldn't find {formatList(fields.missing_sections)} in this resume.
          Please fill {fields.missing_sections.length > 1 ? "them" : "it"} in manually below.
        </div>
      )}

      <section className="confirm-card">
        <h2>Personal information</h2>
        <div className="field-grid">
          <TextField label="Full name" value={fields.personal_info.full_name} onChange={(v) => updatePersonal("full_name", v)} />
          <TextField label="Mobile" value={fields.personal_info.mobile} onChange={(v) => updatePersonal("mobile", v)} />
          <TextField label="Email" value={fields.personal_info.email} onChange={(v) => updatePersonal("email", v)} />
          <TextField label="Location" value={fields.personal_info.location} onChange={(v) => updatePersonal("location", v)} />
          <TextField label="LinkedIn URL" value={fields.personal_info.linkedin_url} onChange={(v) => updatePersonal("linkedin_url", v)} />
          <TextField label="Portfolio URL" value={fields.personal_info.portfolio_url} onChange={(v) => updatePersonal("portfolio_url", v)} />
        </div>
      </section>

      <section className="confirm-card">
        <div className="confirm-card__header">
          <h2>Education</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => addListItem("education", emptyEducation)}>
            + Add education
          </button>
        </div>
        {fields.education.map((edu, i) => (
          <div className="repeatable-row" key={i}>
            <TextField label="Degree" value={edu.degree} onChange={(v) => updateListItem("education", i, "degree", v)} />
            <TextField label="Institution" value={edu.institution} onChange={(v) => updateListItem("education", i, "institution", v)} />
            <TextField label="Start date" value={edu.start_date} onChange={(v) => updateListItem("education", i, "start_date", v)} />
            <TextField label="End date" value={edu.end_date} onChange={(v) => updateListItem("education", i, "end_date", v)} />
            <button type="button" className="remove-row" onClick={() => removeListItem("education", i)}>Remove</button>
          </div>
        ))}
        {fields.education.length === 0 && <p className="muted">No education entries yet.</p>}
      </section>

      <section className="confirm-card">
        <div className="confirm-card__header">
          <h2>Work experience</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => addListItem("work_experience", emptyWork)}>
            + Add company
          </button>
        </div>
        <p className="hint-text">
          Company names and dates stay fixed as your reference; job titles will be adjusted to match the JD in the
          next phase.
        </p>
        {fields.work_experience.map((job, i) => (
          <div className="repeatable-row" key={i}>
            <TextField label="Company" value={job.company} onChange={(v) => updateListItem("work_experience", i, "company", v)} />
            <TextField label="Job title (as in old resume)" value={job.job_title} onChange={(v) => updateListItem("work_experience", i, "job_title", v)} />
            <TextField label="Start date" value={job.start_date} onChange={(v) => updateListItem("work_experience", i, "start_date", v)} />
            <TextField label="End date" value={job.end_date} onChange={(v) => updateListItem("work_experience", i, "end_date", v)} />
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={job.is_current}
                onChange={(e) => updateListItem("work_experience", i, "is_current", e.target.checked)}
              />
              Current role
            </label>
            <button type="button" className="remove-row" onClick={() => removeListItem("work_experience", i)}>Remove</button>
          </div>
        ))}
        {fields.work_experience.length === 0 && <p className="muted">No work experience entries yet.</p>}
      </section>

      <section className="confirm-card">
        <div className="confirm-card__header">
          <h2>Certifications</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => addListItem("certifications", () => "")}>
            + Add certification
          </button>
        </div>
        {fields.certifications.map((cert, i) => (
          <div className="repeatable-row repeatable-row--single" key={i}>
            <input
              type="text"
              value={cert}
              onChange={(e) => updateSimpleList("certifications", i, e.target.value)}
              placeholder="e.g. AWS Certified Solutions Architect"
            />
            <button type="button" className="remove-row" onClick={() => removeListItem("certifications", i)}>Remove</button>
          </div>
        ))}
      </section>

      <section className="confirm-card">
        <div className="confirm-card__header">
          <h2>Languages known</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => addListItem("languages_known", () => "")}>
            + Add language
          </button>
        </div>
        {fields.languages_known.map((lang, i) => (
          <div className="repeatable-row repeatable-row--single" key={i}>
            <input
              type="text"
              value={lang}
              onChange={(e) => updateSimpleList("languages_known", i, e.target.value)}
              placeholder="e.g. Telugu, English, Hindi"
            />
            <button type="button" className="remove-row" onClick={() => removeListItem("languages_known", i)}>Remove</button>
          </div>
        ))}
      </section>

      <section className="confirm-card confirm-card--jd">
        <h2>Job description ({jdData.role_title || "role not detected"})</h2>
        <p className="jd-preview">{jdData.full_text?.slice(0, 400)}{jdData.full_text?.length > 400 ? "…" : ""}</p>
      </section>

      {error && <p className="error-text">{error}</p>}

      <div className="confirm-actions">
        <button type="button" className="btn btn-ghost" onClick={onBack} disabled={saving}>
          ← Back
        </button>
        <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Confirm & save candidate"}
        </button>
      </div>
    </div>
  );
}

function TextField({ label, value, onChange }) {
  return (
    <label className="text-field">
      <span>{label}</span>
      <input type="text" value={value || ""} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function formatList(items) {
  if (items.length === 1) return items[0].replace(/_/g, " ");
  return items.map((i) => i.replace(/_/g, " ")).join(", ");
}

function normalizeFields(raw) {
  return {
    personal_info: {
      full_name: "",
      mobile: "",
      email: "",
      location: "",
      linkedin_url: "",
      portfolio_url: "",
      ...(raw.personal_info || {}),
    },
    education: raw.education?.length ? raw.education : [],
    work_experience: raw.work_experience?.length ? raw.work_experience : [],
    certifications: raw.certifications || [],
    languages_known: raw.languages_known || [],
    missing_sections: raw.missing_sections || [],
  };
}
