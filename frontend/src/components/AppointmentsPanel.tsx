import { useEffect, useMemo, useRef, useState } from "react";

import { listDoctorSlots } from "../api/doctors";
import type {
  AppointmentResponseDto,
  AppointmentSlotDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
} from "../api/dto";
import { findPatientByNationalId } from "../api/patients";
import { useLanguage } from "../i18n/useLanguage";
import type { AppointmentPrefill } from "../lib/appointmentPrefill";
import SectionPanel from "./SectionPanel";

const ADMIN_APPOINTMENTS_PAGE_SIZE = 6;

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
    clinic_id?: number | null;
    slot_id?: number | null;
  }) => Promise<void>;
  onUpdateStatus: (
    appointmentId: number,
    payload: { status: "approved" | "rejected"; notes?: string },
  ) => Promise<void>;
  preFill?: AppointmentPrefill | null;
  onClearPreFill?: () => void;
};

function renderStatusLabel(
  status: AppointmentResponseDto["status"],
  t: ReturnType<typeof useLanguage>["t"],
): string {
  switch (status) {
    case "requested":
      return t("pendingReview");
    case "approved":
      return t("confirmed");
    case "completed":
      return t("completed");
    case "rejected":
      return t("rejected");
    default:
      return status;
  }
}

function formatDateTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not scheduled yet";
}

function formatClinic(appointment: AppointmentResponseDto): string {
  const clinic = appointment.clinic ?? appointment.slot?.clinic;
  if (!clinic) {
    return "Clinic not assigned";
  }
  return [clinic.name, clinic.area, clinic.city].filter(Boolean).join(" · ");
}

function describeSlot(slot?: AppointmentSlotDto | null): string {
  if (!slot) {
    return "No slot selected";
  }
  return `${formatDateTime(slot.start_at)} - ${formatDateTime(slot.end_at)} (${slot.status})`;
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
  const { t } = useLanguage();
  const formRef = useRef<HTMLFormElement | null>(null);
  const [doctorId, setDoctorId] = useState<number | "">(preFill?.doctorId ?? "");
  const [patientId, setPatientId] = useState<number | "">(currentPatientId ?? "");
  const [resolvedPatient, setResolvedPatient] = useState<PatientProfileResponseDto | null>(null);
  const [patientNationalId, setPatientNationalId] = useState("");
  const [patientLookupLoading, setPatientLookupLoading] = useState(false);
  const [patientLookupError, setPatientLookupError] = useState<string | null>(null);
  const [selectedSpecialty, setSelectedSpecialty] = useState(preFill?.specialty ?? "");
  const [availableSlots, setAvailableSlots] = useState<AppointmentSlotDto[]>([]);
  const [selectedSlotId, setSelectedSlotId] = useState<number | "">("");
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotError, setSlotError] = useState<string | null>(null);
  const [reason, setReason] = useState(preFill?.reason ?? "");
  const [notes, setNotes] = useState(preFill?.notes ?? "");
  const [sortBy, setSortBy] = useState<"date" | "id">("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [activePage, setActivePage] = useState(1);
  const [previousPage, setPreviousPage] = useState(1);
  const [selectedAppointment, setSelectedAppointment] =
    useState<AppointmentResponseDto | null>(null);
  const [statusNotes, setStatusNotes] = useState("");

  const specialties = useMemo(
    () => Array.from(new Set(doctors.map((doctor) => doctor.specialty).filter(Boolean))).sort(),
    [doctors],
  );
  const filteredDoctors = selectedSpecialty
    ? doctors.filter((doctor) => doctor.specialty === selectedSpecialty)
    : doctors;
  const selectedDoctor = doctors.find((doctor) => doctor.id === Number(doctorId));
  const selectedSlot = availableSlots.find((slot) => slot.id === Number(selectedSlotId));

  useEffect(() => {
    if (!preFill) {
      return;
    }
    setDoctorId(preFill.doctorId);
    setSelectedSpecialty(preFill.specialty);
    setReason(preFill.reason);
    setNotes(preFill.notes ?? "");
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [preFill]);

  useEffect(() => {
    if (!doctorId) {
      setAvailableSlots([]);
      setSelectedSlotId("");
      return;
    }

    let cancelled = false;
    setSlotLoading(true);
    setSlotError(null);
    setSelectedSlotId("");
    listDoctorSlots(Number(doctorId))
      .then((slots) => {
        if (!cancelled) {
          setAvailableSlots(slots.filter((slot) => slot.status === "open"));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAvailableSlots([]);
          setSlotError("Could not load this doctor's available times.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSlotLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [doctorId]);

  async function handleLookupPatient() {
    const nationalId = patientNationalId.trim();
    if (!nationalId) {
      setPatientLookupError("Enter a patient national ID first.");
      return;
    }

    setPatientLookupLoading(true);
    setPatientLookupError(null);
    setResolvedPatient(null);
    setPatientId("");
    try {
      const patient = await findPatientByNationalId(nationalId);
      setResolvedPatient(patient);
      setPatientId(patient.id);
    } catch {
      setPatientLookupError("No patient profile was found for this national ID.");
    } finally {
      setPatientLookupLoading(false);
    }
  }

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetPatientId = Number(patientId || currentPatientId);
    if (!doctorId || !targetPatientId || !selectedSlotId) {
      return;
    }

    await onCreate({
      patient_id: targetPatientId,
      doctor_id: Number(doctorId),
      reason: reason.trim(),
      notes: notes.trim() || undefined,
      scheduled_for: selectedSlot?.start_at ?? null,
      clinic_id: selectedSlot?.clinic?.id ?? null,
      slot_id: Number(selectedSlotId),
    });
    setReason("");
    setNotes("");
    setSelectedSlotId("");
    if (role !== "patient") {
      setPatientNationalId("");
      setResolvedPatient(null);
      setPatientId("");
    }
    if (onClearPreFill) {
      onClearPreFill();
    }
  }

  async function handleAdminStatusUpdate(status: "approved" | "rejected") {
    if (!selectedAppointment) {
      return;
    }
    await onUpdateStatus(selectedAppointment.id, {
      status,
      notes: statusNotes.trim() || undefined,
    });
    setSelectedAppointment(null);
    setStatusNotes("");
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
  const activeAppointments = [...pendingAppointments, ...confirmedAppointments];
  const previousAppointments = [...completedAppointments, ...rejectedAppointments];

  useEffect(() => {
    setActivePage(1);
    setPreviousPage(1);
  }, [appointments.length, sortBy, sortDirection]);

  function paginateAppointments(
    items: AppointmentResponseDto[],
    page: number,
  ): AppointmentResponseDto[] {
    if (role !== "admin") {
      return items;
    }
    const start = (page - 1) * ADMIN_APPOINTMENTS_PAGE_SIZE;
    return items.slice(start, start + ADMIN_APPOINTMENTS_PAGE_SIZE);
  }

  function renderPaginationControls(
    items: AppointmentResponseDto[],
    page: number,
    setPage: (page: number) => void,
  ) {
    if (role !== "admin" || items.length <= ADMIN_APPOINTMENTS_PAGE_SIZE) {
      return null;
    }

    const pageCount = Math.ceil(items.length / ADMIN_APPOINTMENTS_PAGE_SIZE);
    const safePage = Math.min(page, pageCount);
    const startItem = (safePage - 1) * ADMIN_APPOINTMENTS_PAGE_SIZE + 1;
    const endItem = Math.min(
      safePage * ADMIN_APPOINTMENTS_PAGE_SIZE,
      items.length,
    );

    return (
      <div className="pagination-strip">
        <span>
          Showing {startItem}-{endItem} of {items.length}
        </span>
        <div className="button-row">
          <button
            type="button"
            className="button button--ghost button--small"
            disabled={safePage === 1}
            onClick={() => setPage(Math.max(1, safePage - 1))}
          >
            Previous
          </button>
          <span className="pagination-strip__page">
            Page {safePage} / {pageCount}
          </span>
          <button
            type="button"
            className="button button--ghost button--small"
            disabled={safePage === pageCount}
            onClick={() => setPage(Math.min(pageCount, safePage + 1))}
          >
            Next
          </button>
        </div>
      </div>
    );
  }

  function getPatientName(appointment: AppointmentResponseDto): string {
    return (
      patients.find((patient) => patient.id === appointment.patient_id)?.full_name ??
      `Patient #${appointment.patient_id}`
    );
  }

  function getDoctorName(appointment: AppointmentResponseDto): string {
    return (
      doctors.find((doctor) => doctor.id === appointment.doctor_id)?.full_name ??
      `Doctor #${appointment.doctor_id}`
    );
  }

  function getDoctorSpecialty(appointment: AppointmentResponseDto): string {
    return (
      doctors.find((doctor) => doctor.id === appointment.doctor_id)?.specialty ??
      "Specialty not recorded"
    );
  }

  function openDetails(appointment: AppointmentResponseDto) {
    setSelectedAppointment(appointment);
    setStatusNotes(appointment.notes ?? "");
  }

  function renderAppointmentCard(
    appointment: AppointmentResponseDto,
    options?: { showWorkflowActions?: boolean; showDetailsAction?: boolean },
  ) {
    return (
      <article key={appointment.id} className="entity-card entity-card--appointment">
        <div className="entity-card__header">
          <div>
            <h3>Appointment #{appointment.id}</h3>
            <p>{appointment.reason}</p>
          </div>
          <span className={`badge badge--status-${appointment.status}`}>
            {renderStatusLabel(appointment.status, t)}
          </span>
        </div>

        <div className="detail-list">
          <div>
            <strong>{t("patient")}</strong>
            <span>{getPatientName(appointment)}</span>
          </div>
          <div>
            <strong>{t("doctor")}</strong>
            <span>{getDoctorName(appointment)}</span>
          </div>
          <div>
            <strong>{t("scheduled")}</strong>
            <span>{formatDateTime(appointment.scheduled_for)}</span>
          </div>
          <div>
            <strong>{t("clinicReview")}</strong>
            <span>{formatClinic(appointment)}</span>
          </div>
        </div>

        <p className="muted-copy">
          Requested: {new Date(appointment.requested_at).toLocaleString()}
        </p>
        {appointment.notes ? <p className="muted-copy">Notes: {appointment.notes}</p> : null}

        {options?.showWorkflowActions || options?.showDetailsAction ? (
          <div className="button-row">
            {options.showDetailsAction ? (
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => openDetails(appointment)}
              >
                View details
              </button>
            ) : null}
            {options.showWorkflowActions && appointment.status === "requested" ? (
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

  function renderAdminAppointmentTable(
    label: string,
    items: AppointmentResponseDto[],
    page: number,
    setPage: (page: number) => void,
    emptyMessage: string,
  ) {
    const pageItems = paginateAppointments(items, page);

    return (
      <div className="appointment-page-block">
        <div className="appointment-page-block__header">
          <div>
            <p className="micro-label">{label}</p>
            <h4>{items.length} appointments</h4>
          </div>
          {renderPaginationControls(items, page, setPage)}
        </div>

        {items.length === 0 ? (
          <div className="empty-state">{emptyMessage}</div>
        ) : (
          <div className="appointment-table">
            <div className="appointment-table__header">
              <span>ID</span>
              <span>Patient</span>
              <span>{t("doctor")}</span>
              <span>Date</span>
              <span>Status</span>
              <span>Action</span>
            </div>
            {pageItems.map((appointment) => (
              <div key={appointment.id} className="appointment-table__row">
                <strong>#{appointment.id}</strong>
                <span>{getPatientName(appointment)}</span>
                <span>{getDoctorName(appointment)}</span>
                <span>{formatDateTime(appointment.scheduled_for)}</span>
                <span className={`badge badge--status-${appointment.status}`}>
                  {renderStatusLabel(appointment.status, t)}
                </span>
                <button
                  type="button"
                  className="button button--ghost button--small"
                  onClick={() => openDetails(appointment)}
                >
                  View details
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderAppointmentDetails() {
    if (!selectedAppointment) {
      return null;
    }
    const patient = patients.find((item) => item.id === selectedAppointment.patient_id);

    return (
      <div className="detail-drawer" role="dialog" aria-modal="true">
        <div className="detail-drawer__panel">
          <div className="entity-card__header">
            <div>
              <p className="micro-label">Appointment details</p>
              <h3>Appointment #{selectedAppointment.id}</h3>
            </div>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => setSelectedAppointment(null)}
            >
              Close
            </button>
          </div>

          <div className="detail-list detail-list--dense">
            <div>
              <strong>{t("status")}</strong>
              <span>{renderStatusLabel(selectedAppointment.status, t)}</span>
            </div>
            <div>
              <strong>{t("patient")}</strong>
              <span>{getPatientName(selectedAppointment)}</span>
            </div>
            <div>
              <strong>{t("patientNationalId")}</strong>
              <span>{patient?.national_id ?? "Not available"}</span>
            </div>
            <div>
              <strong>{t("doctor")}</strong>
              <span>{getDoctorName(selectedAppointment)}</span>
            </div>
            <div>
              <strong>{t("specialty")}</strong>
              <span>{getDoctorSpecialty(selectedAppointment)}</span>
            </div>
            <div>
              <strong>{t("clinicReview")}</strong>
              <span>{formatClinic(selectedAppointment)}</span>
            </div>
            <div>
              <strong>{t("scheduled")}</strong>
              <span>{formatDateTime(selectedAppointment.scheduled_for)}</span>
            </div>
            <div>
              <strong>{t("scheduled")}</strong>
              <span>{describeSlot(selectedAppointment.slot)}</span>
            </div>
            <div>
              <strong>{t("reason")}</strong>
              <span>{selectedAppointment.reason}</span>
            </div>
            <div>
              <strong>{t("notes")}</strong>
              <span>{selectedAppointment.notes ?? "No notes recorded"}</span>
            </div>
            <div>
              <strong>Created</strong>
              <span>{formatDateTime(selectedAppointment.requested_at)}</span>
            </div>
            <div>
              <strong>Last updated</strong>
              <span>Not separately recorded</span>
            </div>
          </div>

          {role === "admin" ? (
            <div className="appointment-admin-actions">
              <label htmlFor="appointment-status-notes">Admin status notes</label>
              <textarea
                id="appointment-status-notes"
                rows={3}
                value={statusNotes}
                onChange={(event) => setStatusNotes(event.target.value)}
                placeholder="Optional reason for status change"
              />
              <div className="button-row">
                <button
                  type="button"
                  className="button button--primary"
                  disabled={loading || selectedAppointment.status === "approved"}
                  onClick={() => handleAdminStatusUpdate("approved")}
                >
                  Mark confirmed
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  disabled={loading || selectedAppointment.status === "rejected"}
                  onClick={() => handleAdminStatusUpdate("rejected")}
                >
                  Mark rejected
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <SectionPanel
      eyebrow={t("coordination")}
      title={t("appointmentsTitle")}
      description="Patients request available slots, doctors review requests, and admins can inspect or update reservation status."
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
                        {preFill.specialty}. Review the details below and choose an available slot.
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
                <div className="field field--full patient-lookup-card">
                  <label htmlFor="appointment-patient-national-id">{t("patientNationalId")}</label>
                  <div className="inline-filter">
                    <input
                      id="appointment-patient-national-id"
                      type="text"
                      value={patientNationalId}
                      onChange={(event) => setPatientNationalId(event.target.value)}
                      placeholder="Enter Egyptian national ID"
                    />
                    <button
                      type="button"
                      className="button button--ghost button--small"
                      disabled={patientLookupLoading}
                      onClick={handleLookupPatient}
                    >
                      {patientLookupLoading ? "Searching..." : "Find patient"}
                    </button>
                  </div>
                  {resolvedPatient ? (
                    <small className="field__hint">
                      Found {resolvedPatient.full_name} · #{resolvedPatient.id} ·{" "}
                      {resolvedPatient.sex}
                    </small>
                  ) : null}
                  {patientLookupError ? (
                    <small className="field__error">{patientLookupError}</small>
                  ) : null}
                </div>
              ) : null}

              <div className="field">
                <label htmlFor="appointment-specialty">{t("specialty")}</label>
                <select
                  id="appointment-specialty"
                  value={selectedSpecialty}
                  onChange={(event) => {
                    setSelectedSpecialty(event.target.value);
                    setDoctorId("");
                  }}
                >
                  <option value="">All specialties</option>
                  {specialties.map((specialty) => (
                    <option key={specialty} value={specialty}>
                      {specialty}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="appointment-doctor">{t("doctor")}</label>
                <select
                  id="appointment-doctor"
                  value={doctorId}
                  onChange={(event) =>
                    setDoctorId(event.target.value ? Number(event.target.value) : "")
                  }
                >
                  <option value="">{t("selectDoctor")}</option>
                  {filteredDoctors.map((doctor) => (
                    <option key={doctor.id} value={doctor.id}>
                      {doctor.full_name} · {doctor.specialty} · {doctor.area ?? doctor.city ?? doctor.clinic}
                      {preFill?.doctorId === doctor.id ? " · Recommended" : ""}
                    </option>
                  ))}
                </select>
                {selectedDoctor ? (
                  <small className="field__hint">
                    {preFill?.doctorId === selectedDoctor.id
                      ? "Preselected from the triage recommendation so the patient does not need to search again. "
                      : ""}
                    {selectedDoctor.clinic} · {selectedDoctor.area ?? "Area not listed"}
                  </small>
                ) : null}
              </div>

              <div className="field field--full">
                <label htmlFor="appointment-slot">Available slot</label>
                <select
                  id="appointment-slot"
                  value={selectedSlotId}
                  onChange={(event) =>
                    setSelectedSlotId(event.target.value ? Number(event.target.value) : "")
                  }
                  disabled={!doctorId || slotLoading}
                >
                  <option value="">
                    {slotLoading ? "Loading slots..." : "Select an available time"}
                  </option>
                  {availableSlots.map((slot) => (
                    <option key={slot.id} value={slot.id}>
                      {formatDateTime(slot.start_at)} · {slot.clinic?.name ?? "Clinic"}
                    </option>
                  ))}
                </select>
                {slotError ? <small className="field__error">{slotError}</small> : null}
                {!slotLoading && doctorId && availableSlots.length === 0 ? (
                  <small className="field__hint">
                    No open slots are currently available for this doctor.
                  </small>
                ) : null}
              </div>

              <div className="field field--full">
                <label htmlFor="appointment-reason">{t("reason")}</label>
                <textarea
                  id="appointment-reason"
                  rows={3}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Follow-up, consult, medication review..."
                />
              </div>

              <div className="field field--full">
                <label htmlFor="appointment-notes">{t("notes")}</label>
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
                  !selectedSlotId ||
                  !(patientId || currentPatientId)
                }
              >
                {loading ? "Saving..." : "Request appointment"}
              </button>
            </form>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("appointmentHistory")}</p>
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
                  {sortDirection === "asc" ? "Ascending" : "Descending"}
                </button>
              </div>
            ) : null}

            {role === "admin" ? (
              <div className="appointment-page-grid">
                {renderAdminAppointmentTable(
                  "Active and upcoming",
                  activeAppointments,
                  activePage,
                  setActivePage,
                  "No current appointment requests.",
                )}
                {renderAdminAppointmentTable(
                  "Previous decisions",
                  previousAppointments,
                  previousPage,
                  setPreviousPage,
                  "Completed and rejected appointments will appear here.",
                )}
              </div>
            ) : (
              <div className="stack-md">
                <div>
                  <p className="micro-label">{t("upcomingAppointments")}</p>
                  <div className="stack-md">
                    {activeAppointments.length === 0 ? (
                      <div className="empty-state">
                        No current appointment requests. Start with a new booking above.
                      </div>
                    ) : (
                      activeAppointments.map((appointment) =>
                        renderAppointmentCard(appointment, {
                          showDetailsAction: true,
                        }),
                      )
                    )}
                  </div>
                </div>

                <div>
                  <p className="micro-label">Previous decisions</p>
                  <div className="stack-md">
                    {previousAppointments.length === 0 ? (
                      <div className="empty-state">
                        Completed and rejected appointments will appear here for reference.
                      </div>
                    ) : (
                      previousAppointments.map((appointment) =>
                        renderAppointmentCard(appointment, {
                          showDetailsAction: true,
                        }),
                      )
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      ) : null}

      {error ? <div className="notice notice--error">{error}</div> : null}

      {role === "doctor" ? (
        <div className="stack-md">
          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("pendingApprovals")}</p>
                <h3>{pendingAppointments.length} requests need a decision</h3>
              </div>
            </div>
            <div className="stack-md">
              {pendingAppointments.length === 0 ? (
                <div className="empty-state">No pending approvals right now.</div>
              ) : (
                pendingAppointments.map((appointment) =>
                  renderAppointmentCard(appointment, {
                    showWorkflowActions: true,
                    showDetailsAction: true,
                  }),
                )
              )}
            </div>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("confirmedAppointments")}</p>
                <h3>{confirmedAppointments.length} upcoming bookings</h3>
              </div>
            </div>
            <div className="stack-md">
              {confirmedAppointments.length === 0 ? (
                <div className="empty-state">
                  Confirmed appointments will appear here once requests are approved.
                </div>
              ) : (
                confirmedAppointments.map((appointment) =>
                  renderAppointmentCard(appointment, { showDetailsAction: true }),
                )
              )}
            </div>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("completed")}</p>
                <h3>{t("completed")}</h3>
              </div>
            </div>
            <div className="stack-md">
              {[...completedAppointments, ...rejectedAppointments].length === 0 ? (
                <div className="empty-state">
                  Past completed and rejected appointment decisions will appear here.
                </div>
              ) : (
                [...completedAppointments, ...rejectedAppointments].map((appointment) =>
                  renderAppointmentCard(appointment, { showDetailsAction: true }),
                )
              )}
            </div>
          </section>
        </div>
      ) : null}

      {renderAppointmentDetails()}
    </SectionPanel>
  );
}

