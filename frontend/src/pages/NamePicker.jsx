import { useEffect, useState } from "react";
import { fetchStaffNames } from "../api";
import { useStaff } from "../StaffContext";
import PrismLogo from "../components/PrismLogo";
import "./NamePicker.css";

export default function NamePicker() {
  const { setStaffName } = useStaff();
  const [names, setNames] = useState([]);
  const [customName, setCustomName] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStaffNames()
      .then((data) => setNames(data.staff_names || []))
      .catch(() => setError("Couldn't reach the server. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  function handlePick(name) {
    setStaffName(name);
  }

  function handleCustomSubmit(e) {
    e.preventDefault();
    const trimmed = customName.trim();
    if (trimmed) setStaffName(trimmed);
  }

  return (
    <div className="name-picker-screen">
      <div className="name-picker-card">
        <PrismLogo size="lg" />
        <h1>Who's working today?</h1>
        <p>Pick your name so your candidates stay separate from your teammates'.</p>

        {loading && <p className="muted">Loading staff list...</p>}
        {error && <p className="error-text">{error}</p>}

        {!loading && !error && (
          <div className="name-grid">
            {names.map((name) => (
              <button key={name} className="name-chip" onClick={() => handlePick(name)}>
                {name}
              </button>
            ))}
          </div>
        )}

        <form className="custom-name-form" onSubmit={handleCustomSubmit}>
          <input
            type="text"
            placeholder="Not on the list? Type your name"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
          />
          <button type="submit" className="btn btn-accent" disabled={!customName.trim()}>
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
