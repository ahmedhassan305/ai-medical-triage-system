import { useEffect, useRef, useState } from "react";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
} from "../api/dto";
import type { AppointmentPrefill } from "../lib/appointmentPrefill";
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
  preFill?: AppointmentPrefill | null;
  onClearPreFill?: () => void;
};

function renderStatusLabel(status: AppointmentResponseDto["status"]): string {
  switch (status) {
    case "requested":
      return "Pending review";
    case "approved":
      return "Confirmed";
    case "completed":
      return "Completed";
    case "rejected":
      return "Rejected";
    default:
      return status;
  }
}

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
  preFill,
  onClearPreFill,
}: AppointmentsPanelProps) {
  const formRef = useRef<HTMLFormElement | null>(null);
  const [doctorId, setDoctorId] = useState<number | "">(preFill?.doctorId ?? "");
  const [patientId, setPatientId] = useState<number | "">(currentPatientId ?? "");
  const [patientSearch, setPatientSearch] = useState("");
  const [reason, setReason] = useState(preFill?.reason ?? "");
  const [notes, setNotes] = useState(preFill?.notes ?? "");
  const [scheduledFor, setScheduledFor] = useState("");
  const [sortBy, setSortBy] = useState<"date" | "id">("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    if (!preFill) {
      return;
    }
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [preFill]);

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
    if (onClearPreFill) {
      onClearPreFill();
    }
  }

  const sortedAppointments = [...appointments].sort((left, right) => {
    let comparison = 0;

    if (sortBy === "date") {
      const leftDate = new Date(left.scheduled_for || left.requested_at).getTime();
      const rightDate = new Date(right.scheduled_for || right.requested_at).getTime();
      comparison = leftDate - rightDate;
    } else if (sortBy === "id") {
      comparison = left.id - right.id;
    }

    return sortDirection === "desc" ? -comparison : comparison;
  });
  const pendingAppointments = sortedAppointments.filter(
    (appointment) => appointment.status === "requested",
  );
  const confirmedAppointments = sortedAppointments.filter(
    (appointment) => appointment.status === "approved",
  );
  const completedAppointments = sortedAppointments.filter(
    (appointment) => appointment.status === "completed",
  );
  const rejectedAppointments = sortedAppointments.filter(
    (appointment) => appointment.status === "rejected",
  );

  const filteredPatients = patients.filter((patient) => {
    const search = patientSearch.trim();
    if (!search) {
      return true;
    }
    const nationalId = patient.national_id?.toLowerCase() ?? "";
    return nationalId.includes(search.toLowerCase()) ||
      patient.full_name.toLowerCase().includes(search.toLowerCase());
  });

  function renderAppointmentCard(
    appointment: AppointmentResponseDto,
    options?: { showWorkflowActions?: boolean; showDetailsAction?: boolean },
  ) {
    const patientName =
      patients.find((patient) => patient.id === appointment.patient_id)?.full_name ??
      `Patient #${appointment.patient_id}`;
    const doctorName =
      doctors.find((doctor) => doctor.id === appointment.doctor_id)?.full_name ??
      `Doctor #${appointment.doctor_id}`;

    return (
      <article key={appointment.id} className="entity-card entity-card--appointment">
        <div className="entity-card__header">
          <div>
            <h3>Appointment #{appointment.id}</h3>
            <p>{appointment.reason}</p>
          </div>
          <span className={`badge badge--status-${appointment.status}`}>
            {renderStatusLabel(appointment.status)}
          </span>
        </div>

        <div className="detail-list">
          <div>
            <strong>Patient</strong>
            <span>{patientName}</span>
          </div>
          <div>
            <strong>Doctor</strong>
            <span>{doctorName}</span>
          </div>
          <div>
            <strong>Scheduled</strong>
            <span>
              {appointment.scheduled_for
                ? new Date(appointment.scheduled_for).toLocaleString()
                : "Awaiting clinic confirmation"}
            </span>
          </div>
        </div>

        <p className="muted-copy">
          Requested: {new Date(appointment.requested_at).toLocaleString()}
        </p>
        {appointment.notes ? <p className="muted-copy">Notes: {appointment.notes}</p> : null}

        {options?.showWorkflowActions || options?.showDetailsAction ? (
          <div className="button-row">
            {options.showDetailsAction ? (
              <button type="button" className="button button--ghost button--small">
                View details
              </button>
            ) : null}
            {options.showWorkflowActions ? (
              <>
                <button
                  type="button"
                  className="button button--primary"
                  onClick={() => onUpdateStatus(appointment.id, { status: "approved" })}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => onUpdateStatus(appointment.id, { status: "rejected" })}
                >
                  Reject
                </button>
              </>
            ) : null}
          </div>
        ) : null}
      </article>
    );
  }

  return (
    <SectionPanel
      eyebrow="Coordination"
      title="Appointments"
      description="Patients and admins create bookings here. Doctors handle request decisions from a focused scheduling workspace."
    >
      {role !== "doctor" ? (
        <div className="stack-md">
          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">New booking</p>
                <h3>
                  {role === "admin"
                    ? "Create appointment request"
                    : "Book a follow-up appointment"}
                </h3>
              </div>
            </div>
            <form ref={formRef} className="form-grid" onSubmit={handleCreate}>
              {preFill ? (
                <div className="field field--full">
                  <div className="appointment-prefill">
                    <div>
                      <p className="micro-label">Ready from triage</p>
                      <h3>Dr. {preFill.doctorName} is preselected</h3>
                      <p>
                        The appointment request was prepared from the triage result for{" "}
                        {preFill.specialty}. Review the details below, adjust them if needed,
                        and submit the booking request.
                      </p>
                    </div>
                    {onClearPreFill ? (
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        onClick={onClearPreFill}
                      >
                        Clear recommendation
                      </button>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {role === "admin" ? (
                <>
                  <div className="field">
                    <label htmlFor="appointment-patient-search">Patient national ID</label>
                    <input
                      id="appointment-patient-search"
                      type="text"
                      value={patientSearch}
                      onChange={(event) => setPatientSearch(event.target.value)}
                      placeholder="Enter patient national ID"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="appointment-patient">Patient</label>
                    <select
                      id="appointment-patient"
                      value={patientId}
                      onChange={(event) =>
                        setPatientId(event.target.value ? Number(event.target.value) : "")
                      }
                    >
                      <option value="">Select patient</option>
                      {filteredPatients.map((patient) => (
                        <option key={patient.id} value={patient.id}>
                          {patient.national_id ? `${patient.national_id} — ${patient.full_name}` : `#${patient.id} — ${patient.full_name}`}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              ) : null}

              <div className="field">
                <label htmlFor="appointment-doctor">Doctor</label>
                <select
                  id="appointment-doctor"
                  value={doctorId}
                  onChange={(event) =>
                    setDoctorId(event.target.value ? Number(event.target.value) : "")
                  }
                >
                  <option value="">Select doctor</option>
                  {doctors.map((doctor) => (
                    <option key={doctor.id} value={doctor.id}>
                      {doctor.full_name} · {doctor.specialty}
                      {preFill?.doctorId === doctor.id ? " · Recommended" : ""}
                    </option>
                  ))}
                </select>
                {preFill ? (
                  <small className="field__hint">
                    Preselected from the triage recommendation so the patient does not
                    need to search again.
                  </small>
                ) : null}
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
                {preFill ? (
                  <small className="field__hint">
                    The notes were prefilled from the triage handoff and can be edited
                    before submission.
                  </small>
                ) : null}
              </div>

              <button
                type="submit"
                className="button button--primary"
                disabled={loading || !reason.trim() || !doctorId || !(patientId || currentPatientId)}
              >
                {loading ? "Saving..." : "Request appointment"}
              </button>
            </form>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">Appointment history</p>
                <h3>{appointments.length} tracked bookings</h3>
              </div>
            </div>

            {role === "admin" ? (
              <div className="inline-filter">
                <div className="segmented-control">
                  <button
                    type="button"
                    className={sortBy === "date" ? "is-active" : ""}
                    onClick={() => setSortBy("date")}
                  >
                    Sort by date
                  </button>
                  <button
                    type="button"
                    className={sortBy === "id" ? "is-active" : ""}
                    onClick={() => setSortBy("id")}
                  >
                    Sort by number
                  </button>
                </div>
                <button
                  type="button"
                  className="button button--ghost button--small"
                  onClick={() => setSortDirection(sortDirection === "asc" ? "desc" : "asc")}
                >
                  {sortDirection === "asc" ? "↑ Ascending" : "↓ Descending"}
                </button>
              </div>
            ) : null}

            <div className="stack-md">
              <div>
                <p className="micro-label">Active and upcoming</p>
                <div className="stack-md">
                  {[...pendingAppointments, ...confirmedAppointments].length === 0 ? (
                    <div className="empty-state">
                      No current appointment requests. Start with a new booking above.
                    </div>
                  ) : (
                    [...pendingAppointments, ...confirmedAppointments].map((appointment) =>
                      renderAppointmentCard(appointment, { showDetailsAction: true }),
                    )
                  )}
                </div>
              </div>

              <div>
                <p className="micro-label">Previous decisions</p>
                <div className="stack-md">
                  {[...completedAppointments, ...rejectedAppointments].length === 0 ? (
                    <div className="empty-state">
                      Completed and rejected appointments will appear here for reference.
                    </div>
                  ) : (
                    [...completedAppointments, ...rejectedAppointments].map((appointment) =>
                      renderAppointmentCard(appointment, { showDetailsAction: true }),
                    )
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : null}

      {error ? <div className="notice notice--error">{error}</div> : null}

      {role === "doctor" ? (
        <div className="stack-md">
          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">Pending approvals</p>
                <h3>{pendingAppointments.length} requests need a decision</h3>
              </div>
            </div>
            <div className="stack-md">
              {pendingAppointments.length === 0 ? (
                <div className="empty-state">No pending approvals right now.</div>
              ) : (
                pendingAppointments.map((appointment) =>
                  renderAppointmentCard(appointment, { showWorkflowActions: true }),
                )
              )}
            </div>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">Confirmed appointments</p>
                <h3>{confirmedAppointments.length} upcoming bookings</h3>
              </div>
            </div>
            <div className="stack-md">
              {confirmedAppointments.length === 0 ? (
                <div className="empty-state">
                  Confirmed appointments will appear here once requests are approved.
                </div>
              ) : (
                confirmedAppointments.map((appointment) => renderAppointmentCard(appointment))
              )}
            </div>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">Past items</p>
                <h3>Completed and rejected decisions</h3>
              </div>
            </div>
            <div className="stack-md">
              {[...completedAppointments, ...rejectedAppointments].length === 0 ? (
                <div className="empty-state">
                  Past completed and rejected appointment decisions will appear here.
                </div>
              ) : (
                [...completedAppointments, ...rejectedAppointments].map((appointment) =>
                  renderAppointmentCard(appointment),
                )
              )}
            </div>
          </section>
        </div>
      ) : null}
    </SectionPanel>
  );
}