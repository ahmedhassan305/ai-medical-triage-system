import { useState } from "react";

import { triage, type TriageResponse } from "../api/triage";
import TriageForm from "../components/TriageForm";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TriageResponse | null>(null);

  async function onSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await triage(query.trim());
      setResult(res);
    } catch {
      setError("Failed to fetch triage result. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1 className="title">AI Medical Triage System</h1>
      <p className="subtitle">Local dev stub for triage requests.</p>

      <TriageForm
        query={query}
        onQueryChange={setQuery}
        onSubmit={onSubmit}
        loading={loading}
      />

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="card">
          <p className="muted">Triage Level</p>
          <p className="row">
            <span className="pill">{result.triage_level.toUpperCase()}</span>
          </p>
          <p className="muted">Summary</p>
          <p>{result.summary}</p>
          <p className="muted">Recommended Actions</p>
          <ul>
            {result.actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <p className="muted">Disclaimer</p>
          <p className="muted">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
