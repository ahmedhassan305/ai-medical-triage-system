import { useState } from "react";

import type {
  PatientProfileResponseDto,
  RoleType,
  VisitResponseDto,
} from "../api/dto";
import SectionPanel from "./SectionPanel";

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
  const [patientId, setPatientId] = useState<number | "">(selectedPatientId ?? "");
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

  return (
    <SectionPanel
      eyebrow="Clinical records"
      title="Visits"
      description="Create visits as a clinician or inspect the visit timeline for the active patient."
    >
      {role === "doctor" || role === "admin" ? (
        <form className="form-grid" onSubmit={handleCreate}>
          <div className="field">
            <label htmlFor="visit-patient">Patient</label>
            <select
              id="visit-patient"
              value={patientId}
              onChange={(event) => {
                const nextValue = event.target.value ? Number(event.target.value) : null;
                setPatientId(nextValue ?? "");
                onSelectPatient(nextValue);
              }}
            >
              <option value="">Select patient</option>
              {patientOptions.map((patient) => (
                <option key={patient.id} value={patient.id}>
                  {patient.full_name}
                </option>
              ))}
            </select>
          </div>

          <div className="field field--full">
            <label htmlFor="visit-symptoms">Symptoms</label>
            <textarea
              id="visit-symptoms"
              rows={4}
              value={symptoms}
              onChange={(event) => setSymptoms(event.target.value)}
              placeholder="Document presenting symptoms and severity..."
            />
          </div>

          <div className="field">
            <label htmlFor="visit-diagnosis">Diagnosis</label>
            <input
              id="visit-diagnosis"
              value={diagnosis}
              onChange={(event) => setDiagnosis(event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="visit-prescriptions">Prescriptions</label>
            <input
              id="visit-prescriptions"
              value={prescriptions}
              onChange={(event) => setPrescriptions(event.target.value)}
            />
          </div>

          <div className="field field--full">
            <label htmlFor="visit-notes">Notes</label>
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
      ) : null}

      {role === "patient" ? (
        <div className="inline-filter">
          <span>Your visit history is shown below.</span>
        </div>
      ) : null}

      {error ? <div className="notice notice--error">{error}</div> : null}

      <div className="stack-md">
        {visits.length === 0 ? (
          <div className="empty-state">No visits found for the active patient.</div>
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
                <strong>Symptoms:</strong> {visit.symptoms}
              </p>
              {visit.diagnosis ? (
                <p>
                  <strong>Diagnosis:</strong> {visit.diagnosis}
                </p>
              ) : null}
              {visit.notes ? (
                <p>
                  <strong>Notes:</strong> {visit.notes}
                </p>
              ) : null}
              {visit.prescriptions ? (
                <p>
                  <strong>Prescriptions:</strong> {visit.prescriptions}
                </p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </SectionPanel>
  );
}
