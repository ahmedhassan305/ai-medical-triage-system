import { useState } from "react";

import type {
  PatientProfileResponseDto,
  RoleType,
  VisitResponseDto,
} from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";
import SectionPanel from "./SectionPanel";
import CustomSelect from "./CustomSelect";

type VisitsPanelProps = {
  role: RoleType;
  patientOptions: PatientProfileResponseDto[];
  selectedPatientId: number | null;
  currentDoctorId: number | null;
  visits: VisitResponseDto[];
  loading: boolean;
  error: string | null;
  onSelectPatient: (patientId: number | null) => void;
  onCreateVisit: (payload: {
    patient_id: number;
    doctor_id?: number | null;
    symptoms: string;
    diagnosis?: string;
    notes?: string;
    prescriptions?: string;
  }) => Promise<void>;
};

export default function VisitsPanel({
  role,
  patientOptions,
  selectedPatientId,
  currentDoctorId,
  visits,
  loading,
  error,
  onSelectPatient,
  onCreateVisit,
}: VisitsPanelProps) {
  const { t } = useLanguage();
  const [patientId, setPatientId] = useState<number | "">(selectedPatientId ?? "");
  const [patientSearch, setPatientSearch] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [notes, setNotes] = useState("");
  const [prescriptions, setPrescriptions] = useState("");

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patientId) {
      return;
    }

    await onCreateVisit({
      patient_id: Number(patientId),
      doctor_id: currentDoctorId,
      symptoms: symptoms.trim(),
      diagnosis: diagnosis.trim() || undefined,
      notes: notes.trim() || undefined,
      prescriptions: prescriptions.trim() || undefined,
    });

    setSymptoms("");
    setDiagnosis("");
    setNotes("");
    setPrescriptions("");
  }

  const filteredPatientOptions = patientOptions.filter((patient) => {
    const search = patientSearch.trim();
    if (!search) {
      return true;
    }
    const nationalId = patient.national_id?.toLowerCase() ?? "";
    return nationalId.includes(search.toLowerCase()) ||
      patient.full_name.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <SectionPanel
      eyebrow="Clinical records"
      title={t("visitsTitle")}
      description="Create visits as a clinician or inspect the visit timeline for the active patient."
    >
      {role === "doctor" || role === "admin" ? (
        <div className="stack-md">
          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("createVisit")}</p>
                <h3>{t("visitsDescription")}</h3>
              </div>
            </div>
            <form className="form-grid" onSubmit={handleCreate}>
              <div className="field">
                <label htmlFor="visit-patient-search">{t("patientNationalId")}</label>
                <input
                  id="visit-patient-search"
                  type="text"
                  value={patientSearch}
                  onChange={(event) => setPatientSearch(event.target.value)}
                  placeholder="Enter patient national ID"
                />
              </div>
              <div className="field">
                <label htmlFor="visit-patient">{t("patient")}</label>
                <CustomSelect
                  id="visit-patient"
                  value={patientId}
                  onChange={(value) => {
                    const nextValue = value ? Number(value) : null;
                    setPatientId(nextValue ?? "");
                    onSelectPatient(nextValue);
                  }}
                  options={[
                    { value: "", label: t("selectPatient") },
                    ...filteredPatientOptions.map((patient) => ({
                      value: String(patient.id),
                      label: patient.national_id
                        ? `${patient.national_id} — ${patient.full_name}`
                        : `#${patient.id} — ${patient.full_name}`,
                    })),
                  ]}
                />
              </div>

              <div className="field field--full">
                <label htmlFor="visit-symptoms">{t("symptomLabel")}</label>
                <textarea
                  id="visit-symptoms"
                  rows={4}
                  value={symptoms}
                  onChange={(event) => setSymptoms(event.target.value)}
                  placeholder="Document presenting symptoms and severity..."
                />
              </div>

              <div className="field">
                <label htmlFor="visit-diagnosis">{t("diagnosis")}</label>
                <input
                  id="visit-diagnosis"
                  value={diagnosis}
                  onChange={(event) => setDiagnosis(event.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="visit-prescriptions">{t("notes")}</label>
                <input
                  id="visit-prescriptions"
                  value={prescriptions}
                  onChange={(event) => setPrescriptions(event.target.value)}
                />
              </div>

              <div className="field field--full">
                <label htmlFor="visit-notes">{t("notes")}</label>
                <textarea
                  id="visit-notes"
                  rows={3}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                />
              </div>

              <button
                type="submit"
                className="button button--primary"
                disabled={loading || !patientId || !symptoms.trim()}
              >
                {loading ? "Saving..." : "Create visit"}
              </button>
            </form>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("visitHistory")}</p>
                <h3>{t("recentVisitNotes")}</h3>
              </div>
            </div>
            {error ? <div className="notice notice--error">{error}</div> : null}

            <div className="stack-md">
              {visits.length === 0 ? (
                <div className="empty-state">
                  Select a patient and create the first visit entry to start the medical
                  history timeline.
                </div>
              ) : (
                visits.map((visit) => (
                  <article key={visit.id} className="entity-card">
                    <div className="entity-card__header">
                      <div>
                        <h3>Visit #{visit.id}</h3>
                        <p className="muted-copy">
                          {new Date(visit.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <p>
                      <strong>{t("symptomLabel")}:</strong> {visit.symptoms}
                    </p>
                    {visit.diagnosis ? (
                      <p>
                        <strong>{t("diagnosis")}:</strong> {visit.diagnosis}
                      </p>
                    ) : null}
                    {visit.notes ? (
                      <p>
                        <strong>{t("notes")}:</strong> {visit.notes}
                      </p>
                    ) : null}
                    {visit.prescriptions ? (
                      <p>
                        <strong>{t("notes")}:</strong> {visit.prescriptions}
                      </p>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      ) : null}

      {role === "patient" ? (
        <div className="inline-filter">
          <span>
            Visit history helps you remember diagnoses, follow-up plans, and prescribed
            treatment after each consultation.
          </span>
        </div>
      ) : null}

      {role === "patient" ? (
        <>
          {error ? <div className="notice notice--error">{error}</div> : null}

          <div className="stack-md">
            {visits.length === 0 ? (
              <div className="empty-state">
                No visit records are linked to your profile yet. After your first
                consultation, diagnoses, notes, and prescriptions will appear here.
              </div>
            ) : (
              visits.map((visit) => (
                <article key={visit.id} className="entity-card">
                  <div className="entity-card__header">
                    <div>
                      <h3>Visit #{visit.id}</h3>
                      <p className="muted-copy">
                        {new Date(visit.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <p>
                    <strong>{t("symptomLabel")}:</strong> {visit.symptoms}
                  </p>
                  {visit.diagnosis ? (
                    <p>
                      <strong>{t("diagnosis")}:</strong> {visit.diagnosis}
                    </p>
                  ) : null}
                  {visit.notes ? (
                    <p>
                      <strong>{t("notes")}:</strong> {visit.notes}
                    </p>
                  ) : null}
                  {visit.prescriptions ? (
                    <p>
                      <strong>{t("notes")}:</strong> {visit.prescriptions}
                    </p>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </>
      ) : null}
    </SectionPanel>
  );
}