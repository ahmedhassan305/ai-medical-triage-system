// Force recompile with new doctor suggestions feature
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
            {result.simple_reasoning ? (
              <div>
                <p className="micro-label">Simple reasoning</p>
                <p>{result.simple_reasoning}</p>
              </div>
            ) : null}

            {result.suspected_condition ? (
              <div>
                <p className="micro-label">Suspected condition</p>
                <p>{result.suspected_condition}</p>
              </div>
            ) : null}

            {result.recommended_specialty ? (
              <div>
                <p className="micro-label">Recommended specialty</p>
                <p>{result.recommended_specialty}</p>
              </div>
            ) : null}

            {result.suggested_doctors && result.suggested_doctors.length > 0 ? (
              <div>
                <p className="micro-label">Suggested doctors</p>
                <ul className="list">
                  {result.suggested_doctors.map((doctor) => (
                    <li key={doctor.id}>
                      <strong>{doctor.full_name}</strong> ({doctor.specialty}) - {doctor.clinic}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

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
