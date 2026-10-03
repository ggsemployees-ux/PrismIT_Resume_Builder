import { Routes, Route, Navigate } from "react-router-dom";
import { StaffProvider, useStaff } from "./StaffContext";
import NamePicker from "./pages/NamePicker";
import Dashboard from "./pages/Dashboard";
import NewCandidate from "./pages/NewCandidate";
import CandidateGenerate from "./pages/CandidateGenerate";
import WizardEditor from "./pages/WizardEditor";
import FinalizeExport from "./pages/FinalizeExport";

function Gate({ children }) {
  const { staffName } = useStaff();
  if (!staffName) return <NamePicker />;
  return children;
}

export default function App() {
  return (
    <StaffProvider>
      <Gate>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<NewCandidate />} />
          <Route path="/candidate/:candidateId/generate" element={<CandidateGenerate />} />
          <Route path="/candidate/:candidateId/edit" element={<WizardEditor />} />
          <Route path="/candidate/:candidateId/finalize" element={<FinalizeExport />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Gate>
    </StaffProvider>
  );
}
