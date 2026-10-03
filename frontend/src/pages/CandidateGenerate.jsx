import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import Header from "../components/Header";
import {
  fetchCandidate,
  generateContent,
  regenerateSection,
  regenerateSkills,
  regenerateCareerObjective,
} from "../api";
import "./CandidateGenerate.css";

export default function CandidateGenerate() {
  const { candidateId } = useParams();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regeneratingKey, setRegeneratingKey] = useState(null); // "skills" | "career_objective" | company name
  const [error, setError] = useState(null);
  const [instructions, setInstructions] = useState({}); // key -> custom instruction text

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCandidate(candidateId);
      setCandidate(data.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  function setInstruction(key, value) {
    setInstructions((prev) => ({ ...prev, [key]: value }));
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateContent(candidateId);
      setCandidate(data.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleRegenerateCompany(company) {
    setRegeneratingKey(company);
    setError(null);
    try {
      const data = await regenerateSection(candidateId, company, instructions[company]);
      setCandidate(data.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingKey(null);
    }
  }

  async function handleRegenerateSkills() {
    setRegeneratingKey("skills");
    setError(null);
    try {
      const data = await regenerateSkills(candidateId, instructions.skills);
      setCandidate(data.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingKey(null);
    }
  }

  async function handleRegenerateObjective() {
    setRegeneratingKey("career_objective");
    setError(null);
    try {
      const data = await regenerateCareerObjective(candidateId, instructions.career_objective);
      setCandidate(data.candidate);
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingKey(null);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <Header />
        <main className="generate-page">
          <p className="muted">Loading candidate...</p>
        </main>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="page">
        <Header />
        <main className="generate-page">
          <p className="error-text">{error || "Candidate not found."}</p>
        </main>
      </div>
    );
  }

  const generated = candidate.generated_content;

  return (
    <div className="page">
      <Header
        rightSlot={{
          action: (
            <button className="btn btn-ghost" onClick={() => navigate("/")}>
              ← Dashboard
            </button>
          ),
        }}
      />
      <main className="generate-page">
        <div className="generate-page__intro">
          <div>
            <h1>{candidate.full_name || "Untitled candidate"}</h1>
            <p>
              Target role: <strong>{candidate.jd_data?.role_title || "—"}</strong>
            </p>
          </div>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : generated ? "Regenerate everything" : "Generate resume content →"}
          </button>
          {generated && (
            <Link to={`/candidate/${candidateId}/edit`} className="btn btn-accent">
              Open in editor →
            </Link>
          )}
        </div>

        {error && <p className="error-text">{error}</p>}

        {!generated && !generating && (
          <div className="empty-state">
            <h2>No content generated yet</h2>
            <p>
              Click "Generate resume content" to create a career objective, JD-aligned job titles, categorized
              skills, and detailed responsibilities for this candidate.
            </p>
          </div>
        )}

        {generated && (
          <>
            {generated.jd_gaps?.length > 0 && (
              <div className="jd-gaps-banner">
                <strong>JD Gap — candidate confirmation required:</strong>
                <ul>
                  {generated.jd_gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
                <p className="jd-gaps-note">This is internal staff-only information — it never appears on the candidate's resume.</p>
              </div>
            )}

            <RegenerateCard
              title="Career Objective"
              regenKey="career_objective"
              isRegenerating={regeneratingKey === "career_objective"}
              instruction={instructions.career_objective || ""}
              onInstructionChange={(v) => setInstruction("career_objective", v)}
              onRegenerate={handleRegenerateObjective}
            >
              <p className="career-objective-text">{generated.career_objective}</p>
            </RegenerateCard>

            <RegenerateCard
              title="Core Technical Skills"
              regenKey="skills"
              isRegenerating={regeneratingKey === "skills"}
              instruction={instructions.skills || ""}
              onInstructionChange={(v) => setInstruction("skills", v)}
              onRegenerate={handleRegenerateSkills}
            >
              {generated.skill_categories?.map((cat, i) => (
                <div className="skill-category-row" key={i}>
                  <strong>{cat.category}:</strong> {cat.skills.join(", ")}
                </div>
              ))}
            </RegenerateCard>

            <section className="gen-card gen-card--profile">
              <h2>Elaboration profile used</h2>
              <div className="profile-grid">
                <ProfileStat label="Seniority tier" value={generated.elaboration_profile?.seniority_tier} />
                <ProfileStat label="Companies" value={generated.elaboration_profile?.company_count} />
                <ProfileStat
                  label="Est. total experience"
                  value={
                    generated.elaboration_profile?.estimated_total_years != null
                      ? `${generated.elaboration_profile.estimated_total_years} yrs`
                      : "Unknown"
                  }
                />
                <ProfileStat label="Page guidance" value={generated.elaboration_profile?.target_page_guidance} />
              </div>
              {generated.elaboration_profile?.per_role_guidance?.length > 0 && (
                <div className="per-role-guidance-list">
                  {generated.elaboration_profile.per_role_guidance.map((g) => (
                    <div className="per-role-guidance-row" key={g.company}>
                      <strong>{g.company}</strong> (rank #{g.recency_rank}): {g.responsibilities_range} bullets — {g.detail}
                    </div>
                  ))}
                </div>
              )}
            </section>

            {generated.companies?.map((company) => (
              <RegenerateCard
                key={company.company}
                title={company.company}
                subtitle={company.generated_job_title}
                regenKey={company.company}
                isRegenerating={regeneratingKey === company.company}
                instruction={instructions[company.company] || ""}
                onInstructionChange={(v) => setInstruction(company.company, v)}
                onRegenerate={() => handleRegenerateCompany(company.company)}
                buttonLabel="Regenerate this company"
              >
                <h3>Responsibilities</h3>
                <ul>
                  {company.responsibilities?.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </RegenerateCard>
            ))}
          </>
        )}
      </main>
    </div>
  );
}

function RegenerateCard({
  title,
  subtitle,
  regenKey,
  isRegenerating,
  instruction,
  onInstructionChange,
  onRegenerate,
  buttonLabel = "Regenerate",
  children,
}) {
  return (
    <section className="gen-card">
      <div className="gen-card__header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="generated-title">{subtitle}</p>}
        </div>
      </div>
      {children}
      <div className="regen-instruction-row">
        <input
          type="text"
          placeholder='Optional instruction, e.g. "add 3 more points like this"'
          value={instruction}
          onChange={(e) => onInstructionChange(e.target.value)}
        />
        <button className="btn btn-ghost btn-sm" onClick={onRegenerate} disabled={isRegenerating}>
          {isRegenerating ? "Regenerating..." : buttonLabel}
        </button>
      </div>
    </section>
  );
}

function ProfileStat({ label, value }) {
  return (
    <div className="profile-stat">
      <span className="profile-stat__label">{label}</span>
      <span className="profile-stat__value">{value ?? "—"}</span>
    </div>
  );
}
