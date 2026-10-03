import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Header from "../components/Header";
import ResumePreview, { TEMPLATE_THEMES } from "../components/wizard/ResumePreview";
import ZoomBar from "../components/wizard/ZoomBar";
import { fetchCandidate, fetchTemplates, saveFormatSettings, exportPdf, exportDocx, downloadBlob, checkAtsScore } from "../api";
import "./FinalizeExport.css";

function mergeIntoResumeData(candidate) {
  const extracted = candidate.extracted_fields || {};
  const generated = candidate.generated_content || {};
  const generatedByCompany = Object.fromEntries((generated.companies || []).map((c) => [c.company, c]));
  return {
    personal_info: extracted.personal_info || {},
    education: extracted.education || [],
    certifications: extracted.certifications || [],
    languages_known: extracted.languages_known || [],
    career_objective: generated.career_objective || "",
    skill_categories: generated.skill_categories || [],
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

export default function FinalizeExport() {
  const { candidateId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [recommendedFonts, setRecommendedFonts] = useState([]);
  const [templateId, setTemplateId] = useState("classic");
  const [fontFamily, setFontFamily] = useState("Arial");
  const [customFont, setCustomFont] = useState("");
  const [fontSizePt, setFontSizePt] = useState(12);
  const [boldHeaders, setBoldHeaders] = useState(true);
  const [zoom, setZoom] = useState(90);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exporting, setExporting] = useState(null);
  const [saveMessage, setSaveMessage] = useState("");
  const [atsResult, setAtsResult] = useState(null);
  const [checkingAts, setCheckingAts] = useState(false);

  useEffect(() => {
    Promise.all([fetchCandidate(candidateId), fetchTemplates()])
      .then(([candidateData, templateData]) => {
        setResumeData(mergeIntoResumeData(candidateData.candidate));
        setTemplates(templateData.templates);
        setRecommendedFonts(templateData.recommended_fonts);
        if (candidateData.candidate.ats_breakdown) {
          setAtsResult(candidateData.candidate.ats_breakdown);
        }
        const existing = candidateData.candidate.format_settings;
        if (existing) {
          setTemplateId(existing.template_id || "classic");
          setFontFamily(existing.font_family || "Arial");
          setFontSizePt(existing.font_size_pt || 12);
          setBoldHeaders(existing.bold_headers ?? true);
        } else {
          setTemplateId(templateData.defaults.template_id);
          setFontFamily(templateData.defaults.font_family);
          setFontSizePt(templateData.defaults.font_size_pt);
          setBoldHeaders(templateData.defaults.bold_headers);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [candidateId]);

  const effectiveFont = customFont.trim() || fontFamily;

  function currentFormatSettings() {
    return { template_id: templateId, font_family: effectiveFont, font_size_pt: fontSizePt, bold_headers: boldHeaders };
  }

  async function persistFormatSettings() {
    await saveFormatSettings(candidateId, currentFormatSettings());
  }

  async function handleCheckAts() {
    setCheckingAts(true);
    setError(null);
    try {
      await persistFormatSettings();
      const data = await checkAtsScore(candidateId);
      setAtsResult(data.ats_result);
    } catch (err) {
      setError(err.message);
    } finally {
      setCheckingAts(false);
    }
  }

  async function handleExport(kind) {
    setExporting(kind);
    setExportMenuOpen(false);
    setError(null);
    try {
      await persistFormatSettings();
      setSaveMessage("Saved");
      const { blob, filename } = kind === "pdf" ? await exportPdf(candidateId) : await exportDocx(candidateId);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(null);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <Header />
        <p className="muted" style={{ padding: 32 }}>Loading...</p>
      </div>
    );
  }

  if (error && !resumeData) {
    return (
      <div className="page">
        <Header />
        <p className="error-text" style={{ padding: 32 }}>{error}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Header
        rightSlot={{
          center: <span className="wizard-status">Templates &amp; Export</span>,
          action: (
            <>
              {saveMessage && <span className="wizard-save-indicator">{saveMessage}</span>}
              <button className="btn btn-ghost" onClick={() => navigate(`/candidate/${candidateId}/edit`)}>
                ← Back to editor
              </button>
              <button className="btn btn-ghost" onClick={handleCheckAts} disabled={checkingAts}>
                {checkingAts ? "Checking..." : "Check ATS"}
              </button>
              <div className="export-split-button">
                <button className="btn btn-accent" onClick={() => handleExport("pdf")} disabled={!!exporting}>
                  {exporting === "pdf" ? "Exporting..." : "Export PDF"}
                </button>
                <button
                  type="button"
                  className="btn btn-accent export-split-button__arrow"
                  onClick={() => setExportMenuOpen((v) => !v)}
                  disabled={!!exporting}
                >
                  ▾
                </button>
                {exportMenuOpen && (
                  <div className="export-dropdown-menu">
                    <button onClick={() => handleExport("docx")} disabled={!!exporting}>
                      {exporting === "docx" ? "Exporting..." : "Download as Word (.docx)"}
                    </button>
                  </div>
                )}
              </div>
            </>
          ),
        }}
      />

      {error && <p className="error-text" style={{ padding: "8px 24px 0" }}>{error}</p>}

      <div className="finalize-body">
        <div className="finalize-controls">
          {atsResult && (
            <section className="finalize-card ats-card">
              <div className="ats-card__score-row">
                <div className={`ats-score-badge ${atsResult.overall_score >= 75 ? "ats-score-badge--good" : atsResult.overall_score >= 50 ? "ats-score-badge--ok" : "ats-score-badge--low"}`}>
                  {Math.round(atsResult.overall_score)}%
                </div>
                <div>
                  <h2>ATS Score</h2>
                  <p className="ats-card__subtitle">
                    Directional signal based on keyword match, format, and parseability — not a guarantee for any
                    specific real ATS system.
                  </p>
                </div>
              </div>
              <div className="ats-breakdown">
                <span>Keyword match: {Math.round(atsResult.keyword_match_score)}%</span>
                <span>Format: {Math.round(atsResult.format_score)}%</span>
                <span>Parseability: {Math.round(atsResult.parseability_score)}%</span>
              </div>
              {atsResult.missing_keywords?.length > 0 && (
                <div className="ats-missing">
                  <strong>Missing from JD:</strong> {atsResult.missing_keywords.join(", ")}
                </div>
              )}
              {atsResult.notes?.length > 0 && (
                <ul className="ats-notes">
                  {atsResult.notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <section className="finalize-card">
            <h2>Choose a template</h2>
            <div className="template-gallery">
              {templates.map((t) => (
                <button
                  key={t.id}
                  className={`template-card ${templateId === t.id ? "template-card--selected" : ""}`}
                  onClick={() => setTemplateId(t.id)}
                >
                  <div
                    className="template-card__swatch"
                    style={{
                      background:
                        (TEMPLATE_THEMES[t.id]?.layout === "sidebar")
                          ? `linear-gradient(90deg, ${t.accent_color}22 0 34%, white 34%)`
                          : "white",
                      borderColor: t.accent_color,
                    }}
                  >
                    <span style={{ background: t.accent_color }} className="template-card__swatch-bar" />
                  </div>
                  <div className="template-card__name">{t.name}</div>
                  <div className="template-card__desc">{t.description}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="finalize-card">
            <h2>Font</h2>
            <label className="text-field">
              <span>Font family</span>
              <select value={fontFamily} onChange={(e) => { setFontFamily(e.target.value); setCustomFont(""); }}>
                {recommendedFonts.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </label>
            <label className="text-field">
              <span>Or type any font name</span>
              <input
                type="text"
                placeholder="e.g. Cambria, Futura, any font you like"
                value={customFont}
                onChange={(e) => setCustomFont(e.target.value)}
              />
            </label>
            <label className="text-field">
              <span>Font size (pt) — body text size; name/headings scale proportionally</span>
              <input
                type="number"
                min={8}
                max={16}
                step={0.5}
                value={fontSizePt}
                onChange={(e) => setFontSizePt(parseFloat(e.target.value) || 12)}
              />
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={boldHeaders} onChange={(e) => setBoldHeaders(e.target.checked)} />
              Bold section headers
            </label>
          </section>
        </div>

        <div className="finalize-preview-panel">
          <ZoomBar zoom={zoom} onZoomChange={setZoom} onFitToWindow={() => setZoom(90)} isFitted={false} pageCount={1} />
          <ResumePreview
            resumeData={resumeData}
            zoom={zoom}
            templateId={templateId}
            fontFamily={effectiveFont}
            fontSizePt={fontSizePt}
            boldHeaders={boldHeaders}
          />
        </div>
      </div>
    </div>
  );
}
