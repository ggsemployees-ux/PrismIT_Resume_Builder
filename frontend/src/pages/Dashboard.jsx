import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import { fetchCandidates } from "../api";
import { useStaff } from "../StaffContext";
import "./Dashboard.css";

export default function Dashboard() {
  const { staffName } = useStaff();
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scope, setScope] = useState("mine"); // "mine" | "all"

  const [filters, setFilters] = useState({ name: "", role: "", date: "", createdBy: "" });

  function load() {
    setLoading(true);
    fetchCandidates(scope === "mine" ? staffName : undefined)
      .then((data) => setCandidates(data.candidates || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [scope, staffName]);

  const filtered = useMemo(() => {
    return candidates.filter((c) => {
      if (filters.name && !(c.full_name || "").toLowerCase().includes(filters.name.toLowerCase())) {
        return false;
      }
      if (filters.role && !(c.role_title || "").toLowerCase().includes(filters.role.toLowerCase())) {
        return false;
      }
      if (filters.createdBy && !(c.created_by || "").toLowerCase().includes(filters.createdBy.toLowerCase())) {
        return false;
      }
      if (filters.date && !(c.created_at || "").startsWith(filters.date)) {
        return false;
      }
      return true;
    });
  }, [candidates, filters]);

  return (
    <div className="page">
      <Header
        rightSlot={{
          action: (
            <Link to="/new" className="btn btn-accent">
              + New candidate resume
            </Link>
          ),
        }}
      />

      <main className="dashboard">
        <div className="dashboard__toolbar">
          <div className="scope-toggle">
            <button
              className={scope === "mine" ? "active" : ""}
              onClick={() => setScope("mine")}
            >
              My candidates
            </button>
            <button
              className={scope === "all" ? "active" : ""}
              onClick={() => setScope("all")}
            >
              All candidates
            </button>
          </div>

          <div className="filters">
            <input
              placeholder="Filter by name"
              value={filters.name}
              onChange={(e) => setFilters((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              placeholder="Filter by role"
              value={filters.role}
              onChange={(e) => setFilters((f) => ({ ...f, role: e.target.value }))}
            />
            <input
              type="date"
              value={filters.date}
              onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
            />
            {scope === "all" && (
              <input
                placeholder="Filter by staff"
                value={filters.createdBy}
                onChange={(e) => setFilters((f) => ({ ...f, createdBy: e.target.value }))}
              />
            )}
          </div>
        </div>

        {loading && <p className="muted">Loading candidates...</p>}
        {error && (
          <p className="error-text">
            Couldn't load candidates: {error}. Check your backend .env (Supabase keys) and that
            the API server is running.
          </p>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="empty-state">
            <h2>No candidate resumes yet</h2>
            <p>Upload a candidate's resume and a job description to generate the first one.</p>
            <Link to="/new" className="btn btn-primary">
              Create your first resume
            </Link>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <table className="candidate-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Role</th>
                <th>Date</th>
                <th>ATS Score</th>
                <th>Template</th>
                <th>Created by</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td className="candidate-name">
                    <Link to={`/candidate/${c.id}/generate`}>{c.full_name || "Untitled candidate"}</Link>
                  </td>
                  <td>{c.role_title || "—"}</td>
                  <td>{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
                  <td>{c.ats_score != null ? `${c.ats_score}%` : "—"}</td>
                  <td>{c.template_id || "—"}</td>
                  <td>{c.created_by}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
