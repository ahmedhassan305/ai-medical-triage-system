import type {
  PatientProfileResponseDto,
  TriageHistoryItemDto,
  TriageResponseDto,
} from "../api/dto";
import SectionPanel from "./SectionPanel";
import TriageForm from "./TriageForm";

type TriagePanelProps = {
  loading: boolean;
  error: string | null;
  result: TriageResponseDto | null;
  history: TriageHistoryItemDto[];
  historyLoading: boolean;
  patientOptions: PatientProfileResponseDto[];
  patientId: number | null;
  lockPatientSelection: boolean;
  query: string;
  onQueryChange: (value: string) => void;
  onPatientChange: (value: number | null) => void;
  onSubmit: () => void;
};

export default function TriagePanel({
  loading,
  error,
  result,
  history,
  historyLoading,
  patientOptions,
  patientId,
  lockPatientSelection,
  query,
  onQueryChange,
  onPatientChange,
  onSubmit,
}: TriagePanelProps) {
  return (
    <SectionPanel
      eyebrow="Clinical reasoning"
      title="History-aware triage"
      description="Run hybrid triage, inspect structured reasoning, and review recent triage sessions."
    >
      <TriageForm
        query={query}
        patientId={patientId}
        patientOptions={patientOptions.map((patient) => ({
          id: patient.id,
          label: `${patient.full_name} · ${patient.age} · ${patient.sex}`,
        }))}
        lockPatientSelection={lockPatientSelection}
        loading={loading}
        onQueryChange={onQueryChange}
        onPatientChange={onPatientChange}
        onSubmit={onSubmit}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {result ? (
        <div className="result-card">
          <div className="result-card__meta">
            <span className={`badge badge--${result.triage_level}`}>
              {result.triage_level.toUpperCase()}
            </span>
            <span>{result.history_used ? "history_used=true" : "history_used=false"}</span>
            <span>confidence={result.confidence.toFixed(2)}</span>
          </div>

          <div className="triage-grid">
            <div className="stack-md">
              <div>
                <p className="micro-label">Summary</p>
                <p>{result.summary}</p>
              </div>

              <div>
                <p className="micro-label">Risk reasoning</p>
                <p>{result.risk_reasoning}</p>
              </div>

              <div>
                <p className="micro-label">Recommended action</p>
                <p>{result.recommended_action}</p>
              </div>

              <div>
                <p className="micro-label">Decision explanation</p>
                <p>{result.decision.explanation}</p>
              </div>
            </div>

            <div className="stack-md">
              <div className="result-card__sidebar">
                <p className="micro-label">Decision signals</p>
                <ul className="list list--compact">
                  <li>Heuristic: {result.decision.heuristic_level}</li>
                  <li>Embedding: {result.decision.embedding_level}</li>
                  <li>LLM: {result.decision.llm_level ?? "n/a"}</li>
                  <li>Final: {result.decision.final_level}</li>
                </ul>
              </div>

              <div className="result-card__sidebar">
                <p className="micro-label">Red flags</p>
                {result.red_flags.length > 0 ? (
                  <ul className="list list--compact">
                    {result.red_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted-copy">No explicit red flags extracted.</p>
                )}
              </div>

              <div className="result-card__sidebar">
                <p className="micro-label">Sources</p>
                {result.sources.length > 0 ? (
                  <ul className="list list--compact">
                    {result.sources.map((source) => (
                      <li key={source.chunk_id}>
                        <strong>{source.source}</strong>: {source.title}{" "}
                        <span className="muted-copy">({source.score.toFixed(2)})</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted-copy">No knowledge sources were attached.</p>
                )}
              </div>
            </div>
          </div>

          <div className="stack-md">
            <div>
              <p className="micro-label">Recommended actions</p>
              <ul className="list">
                {result.actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>

            <div>
              <p className="micro-label">Disclaimer</p>
              <p className="muted-copy">{result.disclaimer}</p>
            </div>
          </div>
        </div>
      ) : null}

      <div className="history-card">
        <div className="history-card__header">
          <div>
            <p className="micro-label">Recent triage sessions</p>
            <p className="muted-copy">
              Stored server-side for auditability and follow-up review.
            </p>
          </div>
          {historyLoading ? <span className="muted-copy">Refreshing...</span> : null}
        </div>

        {history.length > 0 ? (
          <ul className="history-list">
            {history.map((item) => (
              <li key={item.id} className="history-list__item">
                <div>
                  <strong>{item.triage_level.toUpperCase()}</strong>{" "}
                  <span className="muted-copy">
                    #{item.id} · confidence={item.confidence.toFixed(2)}
                  </span>
                  <p>{item.query}</p>
                </div>
                <span className="muted-copy">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted-copy">No saved triage sessions yet.</p>
        )}
      </div>
    </SectionPanel>
  );
}
