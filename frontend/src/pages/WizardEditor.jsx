import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import AccordionSection from "../components/wizard/AccordionSection";
import BulletListEditor from "../components/wizard/BulletListEditor";
import ResumePreview from "../components/wizard/ResumePreview";
import ZoomBar from "../components/wizard/ZoomBar";
import { regenerateCareerObjective, regenerateSection, regenerateSkills, fetchCandidate, saveResumeContent } from "../api";
import { PAGE_WIDTH } from "../utils/pagination";
import "./WizardEditor.css";

const AUTOSAVE_DELAY_MS = 2000;

function mergeIntoResumeData(candidate) {
  const extracted = candidate.extracted_fields || {};
  const generated = candidate.generated_content || {};
  const generatedByCompany = Object.fromEntries(
    (generated.companies || []).map((c) => [c.company, c])
  );

  return {
    personal_info: extracted.personal_info || {},
    education: extracted.education || [],
    certifications: extracted.certifications || [],
    languages_known: extracted.languages_known || [],
    career_objective: generated.career_objective || "",
    skill_categories: generated.skill_categories || [],
    elaboration_profile: generated.elaboration_profile || null,
    work_experience: (extracted.work_experience || []).map((job) => {
      const gen = generatedByCompany[job.company] || {};
      return {
        ...job,
        generated_job_title: gen.generated_job_title || "",
        responsibilities: gen.responsibilities || [],
      };
    }),
  };
}

function splitForSave(resumeData) {
  const extracted_fields = {
    personal_info: resumeData.personal_info,
    education: resumeData.education,
    certifications: resumeData.certifications,
    languages_known: resumeData.languages_known,
    work_experience: resumeData.work_experience.map((job) => ({
      company: job.company,
      job_title: job.job_title,
      start_date: job.start_date,
      end_date: job.end_date,
      is_current: job.is_current,
    })),
  };
  const generated_content = {
    career_objective: resumeData.career_objective,
    skill_categories: resumeData.skill_categories,
    elaboration_profile: resumeData.elaboration_profile,
    companies: resumeData.work_experience.map((job) => ({
      company: job.company,
      generated_job_title: job.generated_job_title,
      responsibilities: job.responsibilities,
    })),
  };
  return { extracted_fields, generated_content };
}

export default function WizardEditor() {
  const { candidateId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [candidateName, setCandidateName] = useState("");
  const [openSection, setOpenSection] = useState("personal");
  const [zoom, setZoom] = useState(100);
  const [isFitted, setIsFitted] = useState(false);
  const [saveState, setSaveState] = useState("idle"); // idle | saving | saved
  const [regeneratingCompany, setRegeneratingCompany] = useState(null);
  const [regeneratingKey, setRegeneratingKey] = useState(null); // "skills" | "career_objective"
  const [instructions, setInstructions] = useState({}); // company/"skills"/"career_objective" -> instruction text

  const previewRef = useRef(null);
  const previewPanelRef = useRef(null);
  const autosaveTimer = useRef(null);
  const isFirstLoad = useRef(true);

  useEffect(() => {
    fetchCandidate(candidateId)
      .then((data) => {
        setResumeData(mergeIntoResumeData(data.candidate));
        setCandidateName(data.candidate.full_name || "");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [candidateId]);

  // Autosave: 2s after the user stops editing. Skips the very first load
  // (when resumeData is set from the fetch, not from an actual edit).
  useEffect(() => {
    if (!resumeData) return;
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
      return;
    }
    setSaveState("saving");
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(async () => {
      try {
        const { extracted_fields, generated_content } = splitForSave(resumeData);
        await saveResumeContent(candidateId, {
          extractedFields: extracted_fields,
          generatedContent: generated_content,
        });
        setSaveState("saved");
      } catch {
        setSaveState("idle");
      }
    }, AUTOSAVE_DELAY_MS);
    return () => clearTimeout(autosaveTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeData]);

  function handleOpenSection(id) {
    setOpenSection(id);
    if (id) {
      requestAnimationFrame(() => previewRef.current?.scrollToSection(id));
    }
  }

  function updatePersonal(key, value) {
    setResumeData((d) => ({ ...d, personal_info: { ...d.personal_info, [key]: value } }));
  }

  function updateSkillCategories(newCategories) {
    setResumeData((d) => ({ ...d, skill_categories: newCategories }));
  }

  function updateCareerObjective(value) {
    setResumeData((d) => ({ ...d, career_objective: value }));
  }

  function setInstruction(key, value) {
    setInstructions((prev) => ({ ...prev, [key]: value }));
  }

  function updateJob(index, key, value) {
    setResumeData((d) => {
      const work = [...d.work_experience];
      work[index] = { ...work[index], [key]: value };
      return { ...d, work_experience: work };
    });
  }

  async function handleRegenerateCompany(companyName) {
    setRegeneratingCompany(companyName);
    try {
      const data = await regenerateSection(candidateId, companyName, instructions[companyName]);
      setResumeData(mergeIntoResumeData(data.candidate));
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingCompany(null);
    }
  }

  async function handleRegenerateSkills() {
    setRegeneratingKey("skills");
    try {
      const data = await regenerateSkills(candidateId, instructions.skills);
      setResumeData(mergeIntoResumeData(data.candidate));
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingKey(null);
    }
  }

  async function handleRegenerateObjective() {
    setRegeneratingKey("career_objective");
    try {
      const data = await regenerateCareerObjective(candidateId, instructions.career_objective);
      setResumeData(mergeIntoResumeData(data.candidate));
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingKey(null);
    }
  }

  const handleFitToWindow = useCallback(() => {
    const container = previewPanelRef.current;
    if (!container) return;
    const available = container.clientWidth - 64;
    const fitted = Math.min(150, Math.max(50, Math.round((available / PAGE_WIDTH) * 100)));
    setZoom(fitted);
    setIsFitted(true);
  }, []);

  function handleZoomChange(z) {
    setZoom(z);
    setIsFitted(false);
  }

  useEffect(() => {
    handleFitToWindow();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="page">
        <Header />
        <p className="muted" style={{ padding: 32 }}>
          Loading editor...
        </p>
      </div>
    );
  }

  if (error && !resumeData) {
    return (
      <div className="page">
        <Header />
        <p className="error-text" style={{ padding: 32 }}>
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <Header
        rightSlot={{
          center: <span className="wizard-status">Editing resume for {candidateName || "candidate"}</span>,
          action: (
            <>
              <span className="wizard-save-indicator">
                {saveState === "saving" ? "Saving..." : saveState === "saved" ? "Saved" : ""}
              </span>
              <div className="export-split-button" title="Choose a template and font, then export">
                <button className="btn btn-accent" onClick={() => navigate(`/candidate/${candidateId}/finalize`)}>
                  Continue to Templates & Export →
                </button>
              </div>
            </>
          ),
        }}
      />

      <div className="wizard-body">
        <div className="wizard-input-panel">
          <AccordionSection
            id="personal"
            title="Personal Information"
            isOpen={openSection === "personal"}
            onOpen={handleOpenSection}
            onContinue={() => handleOpenSection("career_objective")}
            continueLabel="Career Objective"
          >
            <div className="field-grid">
              <LabeledInput label="Full name" value={resumeData.personal_info.full_name} onChange={(v) => updatePersonal("full_name", v)} />
              <LabeledInput label="Mobile" value={resumeData.personal_info.mobile} onChange={(v) => updatePersonal("mobile", v)} />
              <LabeledInput label="Email" value={resumeData.personal_info.email} onChange={(v) => updatePersonal("email", v)} />
              <LabeledInput label="Location" value={resumeData.personal_info.location} onChange={(v) => updatePersonal("location", v)} />
              <LabeledInput label="LinkedIn" value={resumeData.personal_info.linkedin_url} onChange={(v) => updatePersonal("linkedin_url", v)} />
              <LabeledInput label="Portfolio" value={resumeData.personal_info.portfolio_url} onChange={(v) => updatePersonal("portfolio_url", v)} />
            </div>
          </AccordionSection>

          <AccordionSection
            id="career_objective"
            title="Career Objective"
            isOpen={openSection === "career_objective"}
            onOpen={handleOpenSection}
            onContinue={() => handleOpenSection("skills")}
            continueLabel="Skills"
          >
            <label className="text-field">
              <span>Objective text</span>
              <textarea
                rows={4}
                value={resumeData.career_objective || ""}
                onChange={(e) => updateCareerObjective(e.target.value)}
              />
            </label>
            <RegenerateRow
              instruction={instructions.career_objective || ""}
              onInstructionChange={(v) => setInstruction("career_objective", v)}
              onRegenerate={handleRegenerateObjective}
              isRegenerating={regeneratingKey === "career_objective"}
            />
          </AccordionSection>

          <AccordionSection
            id="skills"
            title="Core Technical Skills"
            isOpen={openSection === "skills"}
            onOpen={handleOpenSection}
            onContinue={() =>
              handleOpenSection(resumeData.work_experience[0] ? `experience-${resumeData.work_experience[0].company}` : "education")
            }
            continueLabel="Work Experience"
          >
            <SkillCategoriesEditor categories={resumeData.skill_categories} onChange={updateSkillCategories} />
            <RegenerateRow
              instruction={instructions.skills || ""}
              onInstructionChange={(v) => setInstruction("skills", v)}
              onRegenerate={handleRegenerateSkills}
              isRegenerating={regeneratingKey === "skills"}
            />
          </AccordionSection>

          {resumeData.work_experience.map((job, jobIndex) => {
            const sectionId = `experience-${job.company}`;
            const nextId = resumeData.work_experience[jobIndex + 1]
              ? `experience-${resumeData.work_experience[jobIndex + 1].company}`
              : "education";
            return (
              <AccordionSection
                key={sectionId}
                id={sectionId}
                title={job.company}
                isOpen={openSection === sectionId}
                onOpen={handleOpenSection}
                onContinue={() => handleOpenSection(nextId)}
                continueLabel={jobIndex === resumeData.work_experience.length - 1 ? "Education" : "next company"}
              >
                <div className="job-editor__meta">
                  <span>
                    {job.start_date} – {job.is_current ? "Present" : job.end_date}
                  </span>
                </div>
                <RegenerateRow
                  instruction={instructions[job.company] || ""}
                  onInstructionChange={(v) => setInstruction(job.company, v)}
                  onRegenerate={() => handleRegenerateCompany(job.company)}
                  isRegenerating={regeneratingCompany === job.company}
                  buttonLabel="Regenerate this company"
                />
                <LabeledInput
                  label="Job title (shown on resume)"
                  value={job.generated_job_title}
                  onChange={(v) => updateJob(jobIndex, "generated_job_title", v)}
                />
                <div>
                  <span className="field-label">Responsibilities</span>
                  <BulletListEditor items={job.responsibilities} onChange={(v) => updateJob(jobIndex, "responsibilities", v)} />
                </div>
              </AccordionSection>
            );
          })}

          <AccordionSection id="education" title="Education" isOpen={openSection === "education"} onOpen={handleOpenSection}>
            {resumeData.education.map((edu, i) => (
              <div className="edu-readonly" key={i}>
                <strong>{edu.degree}</strong> — {edu.institution} ({edu.start_date} – {edu.end_date})
              </div>
            ))}
            <p className="hint-text">Education, certifications, and languages were confirmed in the previous step.</p>
          </AccordionSection>
        </div>

        <div className="wizard-preview-panel" ref={previewPanelRef}>
          <ZoomBar zoom={zoom} onZoomChange={handleZoomChange} onFitToWindow={handleFitToWindow} isFitted={isFitted} pageCount={1} />
          <ResumePreview ref={previewRef} resumeData={resumeData} zoom={zoom} />
        </div>
      </div>
    </div>
  );
}

function LabeledInput({ label, value, onChange }) {
  return (
    <label className="text-field">
      <span>{label}</span>
      <input type="text" value={value || ""} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function SkillCategoriesEditor({ categories, onChange }) {
  const cats = categories || [];

  function updateCategory(index, key, value) {
    const next = [...cats];
    if (key === "skills") {
      next[index] = { ...next[index], skills: value.split(",").map((s) => s.trim()).filter(Boolean) };
    } else {
      next[index] = { ...next[index], [key]: value };
    }
    onChange(next);
  }

  function addCategory() {
    onChange([...cats, { category: "", skills: [] }]);
  }

  function removeCategory(index) {
    onChange(cats.filter((_, i) => i !== index));
  }

  return (
    <div className="skill-categories-editor">
      {cats.map((cat, i) => (
        <div className="skill-category-editor-row" key={i}>
          <input
            type="text"
            className="skill-category-editor-row__name"
            placeholder="Category name"
            value={cat.category}
            onChange={(e) => updateCategory(i, "category", e.target.value)}
          />
          <textarea
            rows={2}
            placeholder="Comma-separated skills"
            value={(cat.skills || []).join(", ")}
            onChange={(e) => updateCategory(i, "skills", e.target.value)}
          />
          <button type="button" className="remove-row" onClick={() => removeCategory(i)}>
            Remove category
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-ghost btn-sm" onClick={addCategory}>
        + Add category
      </button>
    </div>
  );
}

function RegenerateRow({ instruction, onInstructionChange, onRegenerate, isRegenerating, buttonLabel = "Regenerate" }) {
  return (
    <div className="regen-instruction-row">
      <input
        type="text"
        placeholder='Optional instruction, e.g. "add 3 more points like this"'
        value={instruction}
        onChange={(e) => onInstructionChange(e.target.value)}
      />
      <button type="button" className="btn btn-ghost btn-sm" onClick={onRegenerate} disabled={isRegenerating}>
        {isRegenerating ? "Regenerating..." : buttonLabel}
      </button>
    </div>
  );
}
