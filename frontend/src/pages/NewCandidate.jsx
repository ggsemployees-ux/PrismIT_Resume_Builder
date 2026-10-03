import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import UploadStep from "../components/UploadStep";
import ExtractionConfirmStep from "../components/ExtractionConfirmStep";
import { useStaff } from "../StaffContext";
import "./NewCandidate.css";

// Phase 1 covers exactly two steps: upload -> confirm & save.
// Phase 3 will insert the full split-screen generation wizard between
// "confirm" and a final "done" step.
export default function NewCandidate() {
  const { staffName } = useStaff();
  const navigate = useNavigate();
  const [step, setStep] = useState("upload"); // "upload" | "confirm"
  const [resumeFile, setResumeFile] = useState(null);
  const [extractionResult, setExtractionResult] = useState(null); // { extracted_fields, jd_data }

  function handleExtracted(file, result) {
    setResumeFile(file);
    setExtractionResult(result);
    setStep("confirm");
  }

  function handleSaved(candidate) {
    navigate(`/candidate/${candidate.id}/generate`);
  }

  return (
    <div className="page">
      <Header
        rightSlot={{
          center: <StepIndicator step={step} />,
        }}
      />
      <main className="new-candidate">
        {step === "upload" && <UploadStep onExtracted={handleExtracted} />}
        {step === "confirm" && extractionResult && (
          <ExtractionConfirmStep
            resumeFile={resumeFile}
            initialFields={extractionResult.extracted_fields}
            jdData={extractionResult.jd_data}
            createdBy={staffName}
            onBack={() => setStep("upload")}
            onSaved={handleSaved}
          />
        )}
      </main>
    </div>
  );
}

function StepIndicator({ step }) {
  return (
    <div className="step-indicator">
      <span className={step === "upload" ? "step-indicator__item active" : "step-indicator__item done"}>
        1. Upload
      </span>
      <span className="step-indicator__sep">→</span>
      <span className={step === "confirm" ? "step-indicator__item active" : "step-indicator__item"}>
        2. Confirm details
      </span>
    </div>
  );
}
