import { useMemo, useState } from "react";

import type {
  DoctorSuggestionDto,
  ManagedPatientProfileCreateDto,
  PatientProfileResponseDto,
  RoleType,
  TriageResponseDto,
  VisitResponseDto,
} from "../api/dto";
import { parseEgyptianNationalId } from "../lib/egyptianNationalId";
import ClarificationPanel from "./ClarificationPanel";
import SectionPanel from "./SectionPanel";
import TriageForm from "./TriageForm";

type TriagePanelProps = {
  role: RoleType;
  loading: boolean;
  error: string | null;
  result: TriageResponseDto | null;
  patientProfile: PatientProfileResponseDto | null;
  linkedPatient: PatientProfileResponseDto | null;
  linkedPatientLatestVisit: VisitResponseDto | null;
  patientLookupNationalId: string;
  patientLookupLoading: boolean;
  patientLookupError: string | null;
  patientCreateLoading: boolean;
  patientCreateError: string | null;
  query: string;
  onQueryChange: (value: string) => void;
  onLookupNationalIdChange: (value: string) => void;
  onLookupPatient: (nationalId: string) => Promise<void>;
  onClearLinkedPatient: () => void;
  onCreatePatientProfile: (
    payload: ManagedPatientProfileCreateDto,
  ) => Promise<void>;
  onSubmit: () => void;
  onClarificationComplete: (result: TriageResponseDto) => void;
  onReserveAppointment?: (
    doctor: DoctorSuggestionDto,
    specialty: string,
    reason: string,
  ) => void;
};

type ManagedPatientFormState = {
  full_name: string;
  sex: "" | "Male" | "Female";
  national_id: string;
  current_governorate: string;
  smoker: boolean;
  alcoholic: boolean;
  chronic_conditions: string;
};

const EMPTY_PATIENT_FORM: ManagedPatientFormState = {
  full_name: "",
  sex: "",
  national_id: "",
  current_governorate: "",
  smoker: false,
  alcoholic: false,
  chronic_conditions: "",
};

const LIKELIHOOD_LABELS: Record<
  TriageResponseDto["suspected_conditions"][number]["likelihood"],
  string
> = {
  "more likely": "More likely",
  more_likely: "More likely",
  possible: "Possible",
  "less likely": "Less likely",
  less_likely: "Less likely",
};

function summarize(text?: string | null, fallback = "No summary available."): string {
  if (!text) {
    return fallback;
  }
  const normalized = text.trim();
  if (normalized.length <= 160) {
    return normalized;
  }
  return `${normalized.slice(0, 157).trimEnd()}...`;
}

function formatDateTime(dateValue?: string | null): string {
  if (!dateValue) {
    return "Not recorded";
  }
  try {
    return new Date(dateValue).toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateValue;
  }
}

function StaffPatientLookup({
  linkedPatient,
  latestVisit,
  lookupNationalId,
  lookupLoading,
  lookupError,
  createLoading,
  createError,
  onLookupNationalIdChange,
  onLookupPatient,
  onClearLinkedPatient,
  onCreatePatientProfile,
}: {
  linkedPatient: PatientProfileResponseDto | null;
  latestVisit: VisitResponseDto | null;
  lookupNationalId: string;
  lookupLoading: boolean;
  lookupError: string | null;
  createLoading: boolean;
  createError: string | null;
  onLookupNationalIdChange: (value: string) => void;
  onLookupPatient: (nationalId: string) => Promise<void>;
  onClearLinkedPatient: () => void;
  onCreatePatientProfile: (
    payload: ManagedPatientProfileCreateDto,
  ) => Promise<void>;
}) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] =
    useState<ManagedPatientFormState>(EMPTY_PATIENT_FORM);

  const parsedNationalId = useMemo(
    () =>
      createForm.national_id
        ? parseEgyptianNationalId(createForm.national_id)
        : null,
    [createForm.national_id],
  );
  const nationalIdInvalid =
    createForm.national_id.trim().length > 0 && parsedNationalId === null;

  function handleToggleCreateForm() {
    setShowCreateForm((current) => {
      const nextValue = !current;
      if (nextValue) {
        setCreateForm((form) => ({
          ...form,
          national_id: lookupNationalId || form.national_id,
        }));
      }
      return nextValue;
    });
  }

  async function submitCreateForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (createForm.sex !== "Male" && createForm.sex !== "Female") {
      return;
    }
    await onCreatePatientProfile({
      full_name: createForm.full_name.trim(),
      sex: createForm.sex,
      national_id: createForm.national_id,
      current_governorate:
        createForm.current_governorate.trim() ||
        parsedNationalId?.governorate ||
        null,
      smoker: createForm.smoker,
      alcoholic: createForm.alcoholic,
      chronic_conditions: createForm.chronic_conditions
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
    setShowCreateForm(false);
    setCreateForm(EMPTY_PATIENT_FORM);
  }

  return (
    <div className="stack-lg">
      <section className="result-card">
        <div className="result-card__meta">
          <span className="badge badge--neutral">Staff patient lookup</span>
          <span className="muted-copy">
            Use the Egyptian national ID to link triage with the correct patient
            history.
          </span>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="triage-patient-national-id">Patient national ID</label>
            <input
              id="triage-patient-national-id"
              inputMode="numeric"
              maxLength={14}
              value={lookupNationalId}
              onChange={(event) =>
                onLookupNationalIdChange(
                  event.target.value.replace(/\D/g, "").slice(0, 14),
                )
              }
              placeholder="14-digit Ø§Ù„Ø±Ù‚Ù… Ø§Ù„Ù‚ÙˆÙ…ÙŠ"
            />
          </div>

          <div className="button-row button-row--align-end">
            <button
              type="button"
              className="button button--primary"
              disabled={lookupLoading || lookupNationalId.trim().length !== 14}
              onClick={() => onLookupPatient(lookupNationalId)}
            >
              {lookupLoading ? "Looking up..." : "Find patient"}
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={handleToggleCreateForm}
            >
              {showCreateForm ? "Close new patient form" : "Create new patient profile"}
            </button>
            {linkedPatient ? (
              <button
                type="button"
                className="button button--ghost"
                onClick={onClearLinkedPatient}
              >
                Clear linked patient
              </button>
            ) : null}
          </div>
        </div>

        {lookupError ? <div className="notice notice--error">{lookupError}</div> : null}

        {linkedPatient ? (
          <div className="patient-lookup-card">
            <div className="patient-lookup-card__header">
              <div>
                <p className="micro-label">Matched patient</p>
                <h3>{linkedPatient.full_name}</h3>
                <p className="muted-copy">
                  {linkedPatient.sex} · {linkedPatient.age} years ·{" "}
                  {linkedPatient.current_governorate ||
                    linkedPatient.inferred_governorate ||
                    "Governorate pending"}
                </p>
              </div>
              <span className="badge badge--neutral">
                National ID linked
              </span>
            </div>

            <div className="detail-list">
              <div>
                <span>Chronic conditions</span>
                <strong>
                  {linkedPatient.chronic_conditions.length > 0
                    ? linkedPatient.chronic_conditions.join(", ")
                    : "None recorded"}
                </strong>
              </div>
              <div>
                <span>Most recent visit</span>
                <strong>
                  {latestVisit
                    ? formatDateTime(latestVisit.created_at)
                    : "No visit history yet"}
                </strong>
              </div>
            </div>

            {latestVisit ? (
              <div className="callout">
                <p className="micro-label">Latest visit summary</p>
                <p>
                  <strong>{latestVisit.diagnosis || "Visit note"}</strong>
                </p>
                <p>{summarize(latestVisit.notes || latestVisit.symptoms)}</p>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="empty-state">
            No patient is currently linked. You can still run anonymous triage, or
            enter an SSN to use patient history.
          </div>
        )}
      </section>

      {showCreateForm ? (
        <section className="result-card">
          <div className="result-card__meta">
            <span className="badge badge--neutral">New patient profile</span>
            <span className="muted-copy">
              Doctors and admins can register an unlinked patient profile directly
              from triage when a new case arrives.
            </span>
          </div>

          <form className="form-grid" onSubmit={submitCreateForm}>
            <div className="field">
              <label htmlFor="triage-create-full-name">Full name</label>
              <input
                id="triage-create-full-name"
                value={createForm.full_name}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="triage-create-sex">Gender</label>
              <select
                id="triage-create-sex"
                value={createForm.sex}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    sex: event.target.value as ManagedPatientFormState["sex"],
                  }))
                }
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="triage-create-national-id">Egyptian national ID</label>
              <input
                id="triage-create-national-id"
                inputMode="numeric"
                maxLength={14}
                value={createForm.national_id}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    national_id: event.target.value.replace(/\D/g, "").slice(0, 14),
                  }))
                }
              />
              <small className="field__hint">
                The system derives date of birth and inferred governorate from this
                ID.
              </small>
            </div>

            <div className="field">
              <label htmlFor="triage-create-governorate">
                Current governorate / residence
              </label>
              <input
                id="triage-create-governorate"
                value={createForm.current_governorate}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    current_governorate: event.target.value,
                  }))
                }
                placeholder={parsedNationalId?.governorate || "Optional override"}
              />
            </div>

            <div className="field field--full">
              <label htmlFor="triage-create-conditions">Chronic conditions</label>
              <input
                id="triage-create-conditions"
                value={createForm.chronic_conditions}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    chronic_conditions: event.target.value,
                  }))
                }
                placeholder="hypertension, asthma, diabetes"
              />
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={createForm.smoker}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    smoker: event.target.checked,
                  }))
                }
              />
              Smoker
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={createForm.alcoholic}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    alcoholic: event.target.checked,
                  }))
                }
              />
              Alcohol use
            </label>

            {nationalIdInvalid ? (
              <div className="notice notice--error">
                Enter a valid 14-digit Egyptian national ID.
              </div>
            ) : null}

            {createError ? (
              <div className="notice notice--error">{createError}</div>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={
                createLoading ||
                !createForm.full_name.trim() ||
                !createForm.national_id ||
                !createForm.sex ||
                nationalIdInvalid
              }
            >
              {createLoading ? "Creating..." : "Create patient profile"}
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}

export default function TriagePanel({
  role,
  loading,
  error,
  result,
  patientProfile,
  linkedPatient,
  linkedPatientLatestVisit,
  patientLookupNationalId,
  patientLookupLoading,
  patientLookupError,
  patientCreateLoading,
  patientCreateError,
  query,
  onQueryChange,
  onLookupNationalIdChange,
  onLookupPatient,
  onClearLinkedPatient,
  onCreatePatientProfile,
  onSubmit,
  onClarificationComplete,
  onReserveAppointment,
}: TriagePanelProps) {
  return (
    <SectionPanel
      eyebrow="AI-supported triage"
      title="Understand urgency, possible causes, and next steps"
      description="Describe symptoms in your own words. Patient-linked triage can also incorporate previous visits and chronic conditions."
    >
      {role === "patient" ? (
        <div className="result-card">
          <div className="result-card__meta">
            <span className="badge badge--neutral">Linked patient profile</span>
            <span className="muted-copy">
              {patientProfile
                ? "Your own profile and history will be used automatically."
                : "Complete your patient profile to let triage use your history."}
            </span>
          </div>
          {patientProfile ? (
            <div className="detail-list">
              <div>
                <span>Patient</span>
                <strong>{patientProfile.full_name}</strong>
              </div>
              <div>
                <span>Current governorate</span>
                <strong>
                  {patientProfile.current_governorate ||
                    patientProfile.inferred_governorate ||
                    "Governorate pending"}
                </strong>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              No patient profile is linked yet. You can still run triage, but visit
              history will not be considered until the profile is complete.
            </div>
          )}
        </div>
      ) : (
        <StaffPatientLookup
          linkedPatient={linkedPatient}
          latestVisit={linkedPatientLatestVisit}
          lookupNationalId={patientLookupNationalId}
          lookupLoading={patientLookupLoading}
          lookupError={patientLookupError}
          createLoading={patientCreateLoading}
          createError={patientCreateError}
          onLookupNationalIdChange={onLookupNationalIdChange}
          onLookupPatient={onLookupPatient}
          onClearLinkedPatient={onClearLinkedPatient}
          onCreatePatientProfile={onCreatePatientProfile}
        />
      )}

      <TriageForm
        query={query}
        loading={loading}
        onQueryChange={onQueryChange}
        onSubmit={onSubmit}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {result && result.needs_clarification ? (
        <ClarificationPanel
          originalQuery={query}
          questions={result.questions}
          patientId={patientProfile?.id ?? linkedPatient?.id ?? null}
          onComplete={onClarificationComplete}
        />
      ) : result ? (
        <div className="result-layout">
          <section className="result-card result-card--hero">
            <div className="result-card__meta">
              <span className={`badge badge--${result.triage_level}`}>
                {result.triage_level.toUpperCase()}
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

              {result.urgency_reason ? (
                <div className="callout callout--next-step">
                  <p className="micro-label">Why this needs attention</p>
                  <p>{result.urgency_reason}</p>
                </div>
              ) : null}

              {result.recommended_actions[0] ? (
                <div className="callout">
                  <p className="micro-label">What to do now</p>
                  <p>{result.recommended_actions[0]}</p>
                </div>
              ) : null}

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
              {result.specialty_reason ? (
                <p className="muted-copy">{result.specialty_reason}</p>
              ) : (
                <p className="muted-copy">
                  The leading possible conditions and supporting references fit this
                  specialty best.
                </p>
              )}
            </section>
          </div>

          <section className="result-card">
            <p className="micro-label">Possible conditions</p>
            {result.suspected_conditions.length === 0 ? (
              <p className="muted-copy">
                The system could not rank likely conditions confidently from the
                current symptoms alone.
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
                  No doctors matched this specialty yet. You can still book through
                  appointments.
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
                          {doctor.source_name ? (
                            <p className="muted-copy">
                              Public listing: {doctor.source_name}
                            </p>
                          ) : null}
                        </div>
                      </div>
                      <div className="doctor-suggestion-card__actions">
                        {(doctor.booking_url || doctor.source_url) && (
                          <a
                            className="button button--ghost button--small"
                            href={doctor.booking_url || doctor.source_url || "#"}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open public listing
                          </a>
                        )}
                        {onReserveAppointment ? (
                          <button
                            type="button"
                            className="button button--primary button--small"
                            onClick={() =>
                              onReserveAppointment(
                                doctor,
                                result.recommended_specialty || "General Practice",
                                query,
                              )
                            }
                          >
                            Reserve Appointment
                          </button>
                        ) : null}
                      </div>
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
                  <article
                    key={`${reference.source}-${reference.title}`}
                    className="reference-card"
                  >
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


