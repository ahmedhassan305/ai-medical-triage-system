import type { PatientProfileResponseDto, TriageResponseDto } from "../api/dto";
import SectionPanel from "./SectionPanel";
import TriageForm from "./TriageForm";

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
  onReserveAppointment?: (doctorId: number, specialty: string, reason: string) => void;
};

const LIKELIHOOD_LABELS: Record<
  TriageResponseDto["suspected_conditions"][number]["likelihood"],
  string
> = {
  more_likely: "More likely",
  possible: "Possible",
  less_likely: "Less likely",
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
  onReserveAppointment,
}: TriagePanelProps) {
  return (
    <SectionPanel
      eyebrow="AI-supported triage"
      title="Understand urgency, possible causes, and next steps"
      description="Describe symptoms in your own words. If you are signed in with a linked patient profile, the system can also consider previous visits and chronic conditions."
    >
      <TriageForm
        query={query}
        patientId={patientId}
        patientOptions={patientOptions.map((patient) => ({
          id: patient.id,
          label: `${patient.full_name} · ${patient.age} years · ${patient.sex}`,
        }))}
        lockPatientSelection={lockPatientSelection}
        loading={loading}
        onQueryChange={onQueryChange}
        onPatientChange={onPatientChange}
        onSubmit={onSubmit}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {result ? (
        <div className="result-layout">
          <section className="result-card result-card--hero">
            <div className="result-card__meta">
              <span className={`badge badge--${result.urgency_level}`}>
                {result.urgency_level.toUpperCase()}
              </span>
              <span className="muted-copy">
                {result.history_used
                  ? "Past visits and profile data were used."
                  : "No linked patient history was used."}
              </span>
            </div>

            <div className="stack-md">
              <div>
                <p className="micro-label">Urgency</p>
                <h3 className="result-title">{result.urgency_label}</h3>
                <p>{result.patient_friendly_explanation}</p>
              </div>

              {result.red_flags.length > 0 ? (
                <div className="callout callout--warning">
                  <p className="micro-label">Warning signs to watch for</p>
                  <ul className="list">
                    {result.red_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </section>

          <div className="result-grid">
            <section className="result-card">
              <p className="micro-label">Clinical summary</p>
              <p>{result.clinical_summary}</p>
            </section>

            <section className="result-card">
              <p className="micro-label">Recommended specialty</p>
              <p>{result.recommended_specialty ?? "General Practice"}</p>
            </section>
          </div>

          <section className="result-card">
            <p className="micro-label">Possible conditions</p>
            {result.suspected_conditions.length === 0 ? (
              <p className="muted-copy">
                The system could not rank likely conditions confidently from the current symptoms alone.
              </p>
            ) : (
              <div className="condition-list">
                {result.suspected_conditions.map((condition) => (
                  <article key={condition.name} className="condition-card">
                    <div className="condition-card__header">
                      <strong>{condition.name}</strong>
                      <span className="badge badge--neutral">
                        {LIKELIHOOD_LABELS[condition.likelihood]}
                      </span>
                    </div>
                    <p>{condition.explanation}</p>
                  </article>
                ))}
              </div>
            )}
          </section>

          <div className="result-grid">
            <section className="result-card">
              <p className="micro-label">Suggested doctors</p>
              {result.suggested_doctors.length === 0 ? (
                <p className="muted-copy">
                  No doctors matched this specialty yet. You can still book through appointments.
                </p>
              ) : (
                <div className="stack-md">
                  {result.suggested_doctors.map((doctor) => (
                    <article key={doctor.id} className="doctor-suggestion-card">
                      <div className="doctor-suggestion-card__header">
                        <div>
                          <strong>{doctor.full_name}</strong>
                          <p className="muted-copy">
                            {doctor.specialty} · {doctor.clinic}
                          </p>
                          {doctor.area && (
                            <p className="muted-copy">
                              {doctor.area}
                              {doctor.city && `, ${doctor.city}`}
                            </p>
                          )}
                        </div>
                      </div>
                      {onReserveAppointment && (
                        <button
                          type="button"
                          className="button button--primary button--small"
                          onClick={() =>
                            onReserveAppointment(
                              doctor.id,
                              result.recommended_specialty || "General Practice",
                              query,
                            )
                          }
                        >
                          Reserve Appointment
                        </button>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="result-card">
              <p className="micro-label">Recommended next steps</p>
              <ul className="list">
                {result.recommended_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </section>
          </div>

          {result.supporting_references.length > 0 ? (
            <section className="result-card">
              <p className="micro-label">Supporting medical references</p>
              <div className="reference-list">
                {result.supporting_references.map((reference) => (
                  <article key={`${reference.source}-${reference.title}`} className="reference-card">
                    <p>
                      <strong>{reference.title}</strong>
                    </p>
                    <p className="muted-copy">{reference.source}</p>
                    <p>{reference.snippet}</p>
                    {reference.url ? (
                      <a
                        className="reference-link"
                        href={reference.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open source
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          <section className="result-card">
            <p className="micro-label">Safety note</p>
            <p className="muted-copy">{result.disclaimer}</p>
          </section>
        </div>
      ) : null}
    </SectionPanel>
  );
}
