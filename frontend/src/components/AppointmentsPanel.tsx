import { useEffect, useMemo, useRef, useState } from "react";

import { listDoctorSlots, submitDoctorReview } from "../api/doctors";
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
import {
  formatLocalizedDateTime,
  formatLocalizedSlotLabel,
  localizeAppointmentStatus,
} from "../lib/localizedDisplay";
import SectionPanel from "./SectionPanel";
import CustomSelect from "./CustomSelect";

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
  return localizeAppointmentStatus(status, t);
}

function formatDateTime(
  value: string | null | undefined,
  language: ReturnType<typeof useLanguage>["language"],
): string {
  return formatLocalizedDateTime(value, language);
}

function formatClinic(
  appointment: AppointmentResponseDto,
  t: ReturnType<typeof useLanguage>["t"],
): string {
  const clinic = appointment.clinic ?? appointment.slot?.clinic;
  if (!clinic) {
    return t("clinicNotAssigned");
  }
  return [clinic.name, clinic.area, clinic.city].filter(Boolean).join(" · ");
}

function describeSlot(
  slot: AppointmentSlotDto | null | undefined,
  t: ReturnType<typeof useLanguage>["t"],
  language: ReturnType<typeof useLanguage>["language"],
): string {
  if (!slot) {
    return t("noSlotSelected");
  }
  return `${formatDateTime(slot.start_at, language)} - ${formatDateTime(slot.end_at, language)} (${localizeAppointmentStatus(slot.status, t)})`;
}

function formatRequestedAt(
  value: string,
  language: ReturnType<typeof useLanguage>["language"],
): string {
  return new Date(value).toLocaleString(language === "ar" ? "ar-EG" : "en-US");
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
  const { t, language } = useLanguage();
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
  const [reviewForms, setReviewForms] = useState<
    Record<
      number,
      {
        rating: number;
        comment: string;
        loading: boolean;
        error: string | null;
        success: boolean;
      }
    >
  >({});

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
          setSlotError(t("couldNotLoadDoctorSlots"));
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
  }, [doctorId, t]);

  async function handleLookupPatient() {
    const nationalId = patientNationalId.trim();
    if (!nationalId) {
      setPatientLookupError(t("enterPatientNationalIdFirst"));
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
      setPatientLookupError(t("noPatientProfileFound"));
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
              {t("previous")}
            </button>
            <span className="pagination-strip__page">
              {t("page")} {safePage} {t("of")} {pageCount}
            </span>
            <button
              type="button"
              className="button button--ghost button--small"
              disabled={safePage === pageCount}
              onClick={() => setPage(Math.min(pageCount, safePage + 1))}
            >
              {t("next")}
            </button>
          </div>
        </div>
    );
  }

  function getPatientName(appointment: AppointmentResponseDto): string {
    return (
      patients.find((patient) => patient.id === appointment.patient_id)?.full_name ??
      `${t("patientNumber")} #${appointment.patient_id}`
    );
  }

  function getDoctorName(appointment: AppointmentResponseDto): string {
    return (
      doctors.find((doctor) => doctor.id === appointment.doctor_id)?.full_name ??
      `${t("doctorNumber")} #${appointment.doctor_id}`
    );
  }

  function getDoctorSpecialty(appointment: AppointmentResponseDto): string {
    return (
      doctors.find((doctor) => doctor.id === appointment.doctor_id)?.specialty ??
      t("specialtyNotRecorded")
    );
  }

  function getReviewForm(appointmentId: number) {
    return (
      reviewForms[appointmentId] ?? {
        rating: 5,
        comment: "",
        loading: false,
        error: null,
        success: false,
      }
    );
  }

  function updateReviewForm(
    appointmentId: number,
    patch: Partial<ReturnType<typeof getReviewForm>>,
  ) {
    setReviewForms((current) => ({
      ...current,
      [appointmentId]: {
        ...(current[appointmentId] ?? {
          rating: 5,
          comment: "",
          loading: false,
          error: null,
          success: false,
        }),
        ...patch,
      },
    }));
  }

  function canReviewAppointment(appointment: AppointmentResponseDto): boolean {
    if (role !== "patient" || currentPatientId !== appointment.patient_id) {
      return false;
    }
    if (appointment.status === "completed") {
      return true;
    }
    return Boolean(
      appointment.status === "approved" &&
        appointment.scheduled_for &&
        new Date(appointment.scheduled_for) <= new Date(),
    );
  }

  async function handleDoctorReviewSubmit(appointment: AppointmentResponseDto) {
    const form = getReviewForm(appointment.id);
    updateReviewForm(appointment.id, { loading: true, error: null, success: false });
    try {
      await submitDoctorReview({
        doctor_id: appointment.doctor_id,
        appointment_id: appointment.id,
        rating: form.rating,
        comment: form.comment.trim() || null,
      });
      updateReviewForm(appointment.id, { loading: false, success: true });
    } catch (error) {
      updateReviewForm(appointment.id, {
        loading: false,
        error: error instanceof Error ? error.message : "Could not submit review.",
      });
    }
  }

  function openDetails(appointment: AppointmentResponseDto) {
    setSelectedAppointment(appointment);
    setStatusNotes(appointment.notes ?? "");
  }

  function renderAppointmentCard(
    appointment: AppointmentResponseDto,
    options?: { showWorkflowActions?: boolean; showDetailsAction?: boolean },
  ) {
    const reviewForm = getReviewForm(appointment.id);
    const showReviewForm = canReviewAppointment(appointment);

    return (
      <article key={appointment.id} className="entity-card entity-card--appointment">
        <div className="entity-card__header">
          <div>
            <h3>{t("appointmentId")} #{appointment.id}</h3>
            <p dir="auto">{appointment.reason}</p>
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
            <span>{formatDateTime(appointment.scheduled_for, language)}</span>
          </div>
          <div>
            <strong>{t("clinicReview")}</strong>
            <span>{formatClinic(appointment, t)}</span>
          </div>
        </div>

        <p className="muted-copy">
          {t("requestedAt")}: {formatRequestedAt(appointment.requested_at, language)}
        </p>
        {appointment.notes ? (
          <p className="muted-copy" dir="auto">
            {appointment.notes}
          </p>
        ) : null}

        {showReviewForm ? (
          <div className="doctor-review-box">
            <div>
              <p className="micro-label">{t("rateDoctor")}</p>
              <p className="muted-copy">{t("doctorRatingHint")}</p>
            </div>
            <div className="doctor-review-stars" aria-label={t("yourRating")}>
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  type="button"
                  className={`doctor-review-star ${
                    value <= reviewForm.rating ? "is-active" : ""
                  }`}
                  onClick={() => updateReviewForm(appointment.id, { rating: value })}
                  aria-label={`${value}`}
                >
                  ★
                </button>
              ))}
            </div>
            <textarea
              rows={2}
              value={reviewForm.comment}
              onChange={(event) =>
                updateReviewForm(appointment.id, { comment: event.target.value })
              }
              placeholder={t("optionalReviewComment")}
            />
            {reviewForm.error ? (
              <p className="form-error" role="alert">
                {reviewForm.error}
              </p>
            ) : null}
            {reviewForm.success ? (
              <p className="success-copy">{t("reviewSubmitted")}</p>
            ) : null}
            <div className="button-row button-row--align-end">
              <button
                type="button"
                className="button button--primary button--small"
                disabled={reviewForm.loading}
                onClick={() => handleDoctorReviewSubmit(appointment)}
              >
                {reviewForm.loading ? t("saving") : t("submitReview")}
              </button>
            </div>
          </div>
        ) : null}

        {options?.showWorkflowActions || options?.showDetailsAction ? (
          <div className="button-row">
            {options.showDetailsAction ? (
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => openDetails(appointment)}
              >
                {t("viewDetails")}
              </button>
            ) : null}
            {options.showWorkflowActions && appointment.status === "requested" ? (
              <>
                <button
                  type="button"
                  className="button button--primary"
                  onClick={() => onUpdateStatus(appointment.id, { status: "approved" })}
                >
                  {t("approve")}
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => onUpdateStatus(appointment.id, { status: "rejected" })}
                >
                  {t("reject")}
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
            <h4>
              {items.length} {t("trackedBookings")}
            </h4>
          </div>
          {renderPaginationControls(items, page, setPage)}
        </div>

        {items.length === 0 ? (
          <div className="empty-state">{emptyMessage}</div>
        ) : (
          <div className="appointment-table">
            <div className="appointment-table__header">
              <span>{t("appointmentId")}</span>
              <span>{t("patientLabel")}</span>
              <span>{t("doctor")}</span>
              <span>{t("dateLabel")}</span>
              <span>{t("statusLabel")}</span>
              <span>{t("actionLabel")}</span>
            </div>
            {pageItems.map((appointment) => (
              <div key={appointment.id} className="appointment-table__row">
                <strong>#{appointment.id}</strong>
                <span>{getPatientName(appointment)}</span>
                <span>{getDoctorName(appointment)}</span>
                <span>{formatDateTime(appointment.scheduled_for, language)}</span>
                <span className={`badge badge--status-${appointment.status}`}>
                  {renderStatusLabel(appointment.status, t)}
                </span>
                <button
                  type="button"
                  className="button button--ghost button--small"
                  onClick={() => openDetails(appointment)}
                >
                  {t("viewDetails")}
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
              <p className="micro-label">{t("appointmentDetails")}</p>
              <h3>{t("appointmentId")} #{selectedAppointment.id}</h3>
            </div>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => setSelectedAppointment(null)}
            >
              {t("close")}
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
              <span>{patient?.national_id ?? t("notAvailable")}</span>
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
              <span>{formatClinic(selectedAppointment, t)}</span>
            </div>
            <div>
              <strong>{t("scheduled")}</strong>
              <span>{formatDateTime(selectedAppointment.scheduled_for, language)}</span>
            </div>
            <div>
              <strong>{t("scheduled")}</strong>
              <span dir="auto">{describeSlot(selectedAppointment.slot, t, language)}</span>
            </div>
            <div>
              <strong>{t("reason")}</strong>
              <span dir="auto">{selectedAppointment.reason}</span>
            </div>
            <div>
              <strong>{t("notes")}</strong>
              <span dir="auto">{selectedAppointment.notes ?? t("noNotesRecorded")}</span>
            </div>
            <div>
              <strong>{t("createdAt")}</strong>
              <span>{formatDateTime(selectedAppointment.requested_at, language)}</span>
            </div>
            <div>
              <strong>{t("lastUpdated")}</strong>
              <span>{t("notSeparatelyRecorded")}</span>
            </div>
          </div>

          {role === "admin" ? (
            <div className="appointment-admin-actions">
              <label htmlFor="appointment-status-notes">{t("adminStatusNotes")}</label>
              <textarea
                id="appointment-status-notes"
                rows={3}
                value={statusNotes}
                onChange={(event) => setStatusNotes(event.target.value)}
                placeholder={t("optionalReasonForStatusChange")}
              />
              <div className="button-row">
                <button
                  type="button"
                  className="button button--primary"
                  disabled={loading || selectedAppointment.status === "approved"}
                  onClick={() => handleAdminStatusUpdate("approved")}
                >
                  {t("markConfirmed")}
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  disabled={loading || selectedAppointment.status === "rejected"}
                  onClick={() => handleAdminStatusUpdate("rejected")}
                >
                  {t("markRejected")}
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
      description={t("appointmentsPanelDescription")}
    >
      {role !== "doctor" ? (
        <div className="stack-md">
          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("newBooking")}</p>
                <h3>
                  {role === "admin"
                    ? t("createAppointmentRequest")
                    : t("bookAFollowUpAppointment")}
                </h3>
              </div>
            </div>
            <form ref={formRef} className="form-grid" onSubmit={handleCreate}>
              {preFill ? (
                <div className="field field--full">
                  <div className="appointment-prefill">
                  <div>
                      <p className="micro-label">{t("readyFromTriage")}</p>
                      <h3>
                        Dr. {preFill.doctorName} {t("isPreselected")}
                      </h3>
                      <p dir="auto">
                        {language === "ar"
                          ? `${preFill.specialty} من نتيجة الفرز. ${t("reviewDetailsBelow")}`
                          : `The appointment request was prepared from the triage result for ${preFill.specialty}. ${t("reviewDetailsBelow")}`}
                      </p>
                    </div>
                    {onClearPreFill ? (
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        onClick={onClearPreFill}
                      >
                        {t("clearRecommendation")}
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
                      placeholder={t("enterEgyptianNationalId")}
                    />
                    <button
                      type="button"
                      className="button button--ghost button--small"
                      disabled={patientLookupLoading}
                      onClick={handleLookupPatient}
                    >
                      {patientLookupLoading ? t("searching") : t("findPatient")}
                    </button>
                  </div>
                  {resolvedPatient ? (
                    <small className="field__hint">
                      {t("found")} {resolvedPatient.full_name} · #{resolvedPatient.id} ·{" "}
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
                <CustomSelect
                  id="appointment-specialty"
                  value={selectedSpecialty}
                  onChange={(value) => {
                    setSelectedSpecialty(value);
                    setDoctorId("");
                  }}
                  options={[
                    { value: "", label: t("allSpecialties") },
                    ...specialties.map((specialty) => ({
                      value: specialty,
                      label: specialty,
                    })),
                  ]}
                />
              </div>

              <div className="field">
                <label htmlFor="appointment-doctor">{t("doctor")}</label>
                <CustomSelect
                  id="appointment-doctor"
                  value={doctorId}
                  onChange={(value) =>
                    setDoctorId(value ? Number(value) : "")
                  }
                  options={[
                    { value: "", label: t("selectDoctor") },
                    ...filteredDoctors.map((doctor) => ({
                      value: String(doctor.id),
                      label: `${doctor.full_name} · ${doctor.specialty} · ${doctor.area ?? doctor.city ?? doctor.clinic}${preFill?.doctorId === doctor.id ? ` · ${t("recommended")}` : ""}`,
                    })),
                  ]}
                />
                {selectedDoctor ? (
                  <small className="field__hint">
                    {preFill?.doctorId === selectedDoctor.id
                      ? `${t("preselectedFromTriageRecommendation")} `
                      : ""}
                    {selectedDoctor.clinic} · {selectedDoctor.area ?? t("areaNotListed")}
                  </small>
                ) : null}
              </div>

              <div className="field field--full">
                <label htmlFor="appointment-slot">{t("availableSlot")}</label>
                <CustomSelect
                  id="appointment-slot"
                  value={selectedSlotId}
                  onChange={(value) =>
                    setSelectedSlotId(value ? Number(value) : "")
                  }
                  disabled={!doctorId || slotLoading}
                  options={[
                    { value: "", label: slotLoading ? t("loadingSlots") : t("selectAvailableTime") },
                    ...availableSlots.map((slot) => ({
                      value: String(slot.id),
                      label: formatLocalizedSlotLabel(slot, language),
                    })),
                  ]}
                />
                {slotError ? <small className="field__error">{slotError}</small> : null}
                {!slotLoading && doctorId && availableSlots.length === 0 ? (
                  <small className="field__hint">
                    {t("noOpenSlotsAvailable")}
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
                  placeholder={t("followUpConsultMedicationReview")}
                />
              </div>

              <div className="field field--full">
                <label htmlFor="appointment-notes">{t("notes")}</label>
                <input
                  id="appointment-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder={t("optionalExtraContext")}
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
                {loading ? t("saving") : t("requestAppointment")}
              </button>
            </form>
          </section>

          <section className="workspace-card workspace-card--compact">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("appointmentHistory")}</p>
                <h3>{appointments.length} {t("trackedBookings")}</h3>
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
                    {t("sortByDate")}
                  </button>
                  <button
                    type="button"
                    className={sortBy === "id" ? "is-active" : ""}
                    onClick={() => setSortBy("id")}
                  >
                    {t("sortByNumber")}
                  </button>
                </div>
                <button
                  type="button"
                  className="button button--ghost button--small"
                  onClick={() => setSortDirection(sortDirection === "asc" ? "desc" : "asc")}
                >
                  {sortDirection === "asc" ? t("ascending") : t("descending")}
                </button>
              </div>
            ) : null}

            {role === "admin" ? (
              <div className="appointment-page-grid">
                {renderAdminAppointmentTable(
                  t("activeAndUpcoming"),
                  activeAppointments,
                  activePage,
                  setActivePage,
                  t("noCurrentAppointmentRequests"),
                )}
                {renderAdminAppointmentTable(
                  t("previousDecisions"),
                  previousAppointments,
                  previousPage,
                  setPreviousPage,
                  t("noPreviousDecisions"),
                )}
              </div>
            ) : (
              <div className="stack-md">
                <div>
                  <p className="micro-label">{t("upcomingAppointments")}</p>
                  <div className="stack-md">
                    {activeAppointments.length === 0 ? (
                      <div className="empty-state">
                        {t("noCurrentAppointmentRequests")}{" "}
                        {language === "ar" ? "" : t("startWithANewBookingAbove")}
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
                  <p className="micro-label">{t("previousDecisions")}</p>
                  <div className="stack-md">
                    {previousAppointments.length === 0 ? (
                      <div className="empty-state">
                        {t("noPreviousDecisions")}
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
                <h3>
                  {pendingAppointments.length} {t("requestsNeedDecision")}
                </h3>
              </div>
            </div>
            <div className="stack-md">
              {pendingAppointments.length === 0 ? (
                <div className="empty-state">{t("noPendingApprovalsRightNow")}</div>
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
                <h3>
                  {confirmedAppointments.length} {t("upcomingBookings")}
                </h3>
              </div>
            </div>
            <div className="stack-md">
              {confirmedAppointments.length === 0 ? (
                <div className="empty-state">
                  {t("confirmedAppointmentsWillAppear")}
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
                  {t("pastCompletedRejectedAppear")}
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

