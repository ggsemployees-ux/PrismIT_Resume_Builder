import { useState } from "react";
import { extractCandidate } from "../api";
import "./UploadStep.css";

export default function UploadStep({ onExtracted }) {
  const [resumeFile, setResumeFile] = useState(null);
  const [jdMode, setJdMode] = useState("text"); // "text" | "image"
  const [jdText, setJdText] = useState("");
  const [jdImageFile, setJdImageFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const canSubmit =
    resumeFile && ((jdMode === "text" && jdText.trim()) || (jdMode === "image" && jdImageFile));

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      const result = await extractCandidate({
        resumeFile,
        jdText: jdMode === "text" ? jdText : undefined,
        jdImageFile: jdMode === "image" ? jdImageFile : undefined,
      });
      onExtracted(resumeFile, result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="upload-step" onSubmit={handleSubmit}>
      <section className="upload-card">
        <h2>1. Candidate's existing resume</h2>
        <p>Upload a PDF or DOCX. We'll pull personal info, education, and work history from it.</p>
        <FileDrop
          accept=".pdf,.docx"
          file={resumeFile}
          onFile={setResumeFile}
          label="Drop resume here or click to browse"
          hint="PDF or DOCX"
        />
      </section>

      <section className="upload-card">
        <h2>2. Job description</h2>
        <p>Paste the JD text, or upload a screenshot/image of the posting.</p>
        <div className="jd-mode-toggle">
          <button
            type="button"
            className={jdMode === "text" ? "active" : ""}
            onClick={() => setJdMode("text")}
          >
            Paste text
          </button>
          <button
            type="button"
            className={jdMode === "image" ? "active" : ""}
            onClick={() => setJdMode("image")}
          >
            Upload image
          </button>
        </div>

        {jdMode === "text" ? (
          <textarea
            rows={8}
            placeholder="Paste the full job description here..."
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
          />
        ) : (
          <FileDrop
            accept="image/png,image/jpeg,image/webp"
            file={jdImageFile}
            onFile={setJdImageFile}
            label="Drop JD screenshot here or click to browse"
            hint="PNG, JPG, or WEBP"
          />
        )}
      </section>

      {error && <p className="error-text">{error}</p>}

      <div className="upload-actions">
        <button type="submit" className="btn btn-primary" disabled={!canSubmit || loading}>
          {loading ? "Extracting..." : "Extract details →"}
        </button>
      </div>
    </form>
  );
}

function FileDrop({ accept, file, onFile, label, hint }) {
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) onFile(dropped);
  }

  return (
    <label
      className={`file-drop ${dragOver ? "file-drop--over" : ""} ${file ? "file-drop--filled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={accept}
        onChange={(e) => onFile(e.target.files?.[0] || null)}
        hidden
      />
      {file ? (
        <span className="file-drop__filename">{file.name}</span>
      ) : (
        <>
          <span>{label}</span>
          <span className="file-drop__hint">{hint}</span>
        </>
      )}
    </label>
  );
}
