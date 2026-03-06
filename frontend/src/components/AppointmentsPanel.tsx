import { useState } from "react";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
} from "../api/dto";
import SectionPanel from "./SectionPanel";

type AppointmentsPanelProps = {
  role: RoleType;
  doctors: DoctorProfileResponseDto[];
  patients: PatientProfileResponseDto[];
  currentPatientId: number | null;
  appointments: AppointmentResponseDto[];
  loading: boolean;
  error: string | null;
  onCreate: (payload: {
    patient_id: number;
    doctor_id: number;
    reason: string;
    notes?: string;
    scheduled_for?: string | null;
  }) => Promise<void>;
  onUpdateStatus: (
    appointmentId: number,
    payload: { status: "approved" | "rejected"; notes?: string },
  ) => Promise<void>;
};

export default function AppointmentsPanel({
  role,
  doctors,
  patients,
  currentPatientId,
  appointments,
  loading,
  error,
  onCreate,
  onUpdateStatus,
}: AppointmentsPanelProps) {
  const [doctorId, setDoctorId] = useState<number | "">("");
  const [patientId, setPatientId] = useState<number | "">(currentPatientId ?? "");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!doctorId || !(patientId || currentPatientId)) {
      return;
    }

    await onCreate({
      patient_id: Number(patientId || currentPatientId),
      doctor_id: Number(doctorId),
      reason: reason.trim(),
      notes: notes.trim() || undefined,
      scheduled_for: scheduledFor || null,
    });
    setReason("");
    setNotes("");
    setScheduledFor("");
  }

  return (
    <SectionPanel
      eyebrow="Coordination"
      title="Appointments"
      description="Patients and admins can request appointments. Doctors and admins can approve or reject requests."
    >
      {role !== "doctor" ? (
        <form className="form-grid" onSubmit={handleCreate}>
          {role === "admin" ? (
            <div className="field">
              <label htmlFor="appointment-patient">Patient</label>
            <select
              id="appointment-patient"
              value={patientId}
              onChange={(event) =>
                setPatientId(
                  event.target.value ? Number(event.target.value) : "",
                )
              }
            >
                <option value="">Select patient</option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.full_name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="field">
            <label htmlFor="appointment-doctor">Doctor</label>
            <select
              id="appointment-doctor"
              value={doctorId}
              onChange={(event) =>
                setDoctorId(
                  event.target.value ? Number(event.target.value) : "",
                )
              }
            >
              <option value="">Select doctor</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.full_name} · {doctor.specialty}
                </option>
              ))}
            </select>
          </div>

          <div className="field field--full">
            <label htmlFor="appointment-reason">Reason</label>
            <textarea
              id="appointment-reason"
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Follow-up, consult, medication review..."
            />
          </div>

          <div className="field">
            <label htmlFor="appointment-date">Requested time</label>
            <input
              id="appointment-date"
              type="datetime-local"
              value={scheduledFor}
              onChange={(event) => setScheduledFor(event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="appointment-notes">Notes</label>
            <input
              id="appointment-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Optional extra context"
            />
          </div>

          <button
            type="submit"
            className="button button--primary"
            disabled={
              loading ||
              !reason.trim() ||
              !doctorId ||
              !(patientId || currentPatientId)
            }
          >
            {loading ? "Saving..." : "Request appointment"}
          </button>
        </form>
      ) : null}

      {error ? <div className="notice notice--error">{error}</div> : null}

      <div className="stack-md">
        {appointments.length === 0 ? (
          <div className="empty-state">No appointments yet.</div>
        ) : (
          appointments.map((appointment) => (
            <article key={appointment.id} className="entity-card">
              <div className="entity-card__header">
                <div>
                  <h3>Appointment #{appointment.id}</h3>
                  <p>
                    Patient:{" "}
                    {patients.find((patient) => patient.id === appointment.patient_id)
                      ?.full_name ?? appointment.patient_id}
                  </p>
                  <p>
                    Doctor:{" "}
                    {doctors.find((doctor) => doctor.id === appointment.doctor_id)
                      ?.full_name ?? appointment.doctor_id}
                  </p>
                </div>
                <span className={`badge badge--status-${appointment.status}`}>
                  {appointment.status}
                </span>
              </div>

              <p>{appointment.reason}</p>
              <p className="muted-copy">
                Requested: {new Date(appointment.requested_at).toLocaleString()}
              </p>
              {appointment.scheduled_for ? (
                <p className="muted-copy">
                  Scheduled for: {new Date(appointment.scheduled_for).toLocaleString()}
                </p>
              ) : null}

              {role === "doctor" || role === "admin" ? (
                <div className="button-row">
                  <button
                    type="button"
                    className="button button--primary"
                    onClick={() =>
                      onUpdateStatus(appointment.id, { status: "approved" })
                    }
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="button button--ghost"
                    onClick={() =>
                      onUpdateStatus(appointment.id, { status: "rejected" })
                    }
                  >
                    Reject
                  </button>
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>
    </SectionPanel>
  );
}
