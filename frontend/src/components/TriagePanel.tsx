import type { PatientProfileResponseDto, TriageResponseDto } from "../api/dto";
import TriageForm from "./TriageForm";
import SectionPanel from "./SectionPanel";

type TriagePanelProps = {
  loading: boolean;
  error: string | null;
  result: TriageResponseDto | null;
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
      description="Send the current complaint to the backend and attach a patient profile when available."
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
          </div>

          <div className="stack-md">
            <div>
              <p className="micro-label">Summary</p>
              <p>{result.summary}</p>
            </div>

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
    </SectionPanel>
  );
}
