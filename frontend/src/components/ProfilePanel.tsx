import { useEffect, useMemo, useState } from "react";

import type {
  AppointmentSlotDto,
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  DoctorScheduleCreateDto,
  DoctorScheduleDto,
  DoctorProfileUpsertDto,
  PatientMedicalHistoryEntryResponseDto,
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
  RoleType,
  VisitResponseDto,
} from "../api/dto";
import {
  createDoctorSchedule,
  listDoctorSchedules,
  listDoctorSlots,
  updateDoctorProfile,
  updateDoctorSchedule,
} from "../api/doctors";
import {
  createPatientMedicalHistoryEntry,
  extractPatientMedicalHistoryReport,
  listPatientMedicalHistory,
} from "../api/patients";
import { useLanguage } from "../i18n/useLanguage";
import { parseEgyptianNationalId } from "../lib/egyptianNationalId";
import {
  ALEXANDRIA_AREAS,
  composeResidenceLocation,
  EGYPTIAN_GOVERNORATES,
  splitResidenceLocation,
} from "../lib/egyptianLocations";
import {
  localizeAppointmentStatus,
  localizeSlotStatus,
} from "../lib/localizedDisplay";
import {
  composeDoctorSpecialty,
  MEDICAL_SPECIALTY_GROUPS,
  splitDoctorSpecialty,
} from "../lib/medicalSpecialties";
import type { DashboardTab } from "./DashboardNav";
import SectionPanel from "./SectionPanel";
import CustomSelect from "./CustomSelect";

type ProfilePanelProps = {
  role: RoleType;
  patientProfile: PatientProfileResponseDto | null;
  doctorProfile: DoctorProfileResponseDto | null;
  savingPatient: boolean;
  savingDoctor: boolean;
  patients: PatientProfileResponseDto[];
  doctors: DoctorProfileResponseDto[];
  appointments: AppointmentResponseDto[];
  recentVisits: VisitResponseDto[];
  onNavigate: (tab: DashboardTab) => void;
  onSavePatient: (payload: PatientProfileUpsertDto) => Promise<void>;
  onSaveDoctor: (payload: DoctorProfileUpsertDto) => Promise<void>;
};

type PatientProfileFormState = Omit<PatientProfileUpsertDto, "sex"> & {
  sex: "" | PatientProfileUpsertDto["sex"];
};

type DoctorEditFormState = {
  doctorId: number;
  values: DoctorProfileUpsertDto;
};

type DoctorScheduleWorkspaceState = {
  doctorId: number;
  schedules: DoctorScheduleDto[];
  slots: AppointmentSlotDto[];
  loading: boolean;
};

type PatientHistoryState = {
  patientId: number;
  entries: PatientMedicalHistoryEntryResponseDto[];
};

const EMPTY_PATIENT_FORM: PatientProfileFormState = {
  full_name: "",
  age: 0,
  sex: "",
  national_id: "",
  current_governorate: "",
  smoker: false,
  alcoholic: false,
  chronic_conditions: [],
};

const ADMIN_PROFILE_PAGE_SIZE = 8;
const ADMIN_RELATED_RECORD_LIMIT = 5;
const WEEKDAY_OPTIONS = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
];

const EMPTY_SCHEDULE_FORM: DoctorScheduleCreateDto = {
  doctor_clinic_id: null,
  day_of_week: "sunday",
  start_time: "09:00:00",
  end_time: "17:00:00",
  slot_minutes: 30,
  valid_from: null,
  valid_to: null,
  location_label: "",
  is_active: true,
};

function todayDateInputValue(): string {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function toDoctorEditForm(doctor: DoctorProfileResponseDto): DoctorProfileUpsertDto {
  return {
    full_name: doctor.full_name,
    specialty: doctor.specialty,
    clinic: doctor.clinic,
    area: doctor.area ?? "",
    city: doctor.city ?? "",
    consultation_fee: doctor.consultation_fee ?? null,
    insurance_providers: doctor.insurance_providers ?? [],
    payment_methods: doctor.payment_methods ?? [],
    offers_telemedicine: doctor.offers_telemedicine ?? false,
  };
}

function splitCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDateTime(dateValue?: string | null): string {
  if (!dateValue) {
    return "Not scheduled";
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

function weekdayFromDateInput(dateValue: string): string {
  const [year, month, day] = dateValue.split("-").map(Number);
  if (!year || !month || !day) {
    return "sunday";
  }
  return WEEKDAY_OPTIONS[new Date(year, month - 1, day).getDay()] ?? "sunday";
}

function describeScheduleRule(schedule: DoctorScheduleDto): string {
  const timeRange = `${schedule.start_time.slice(0, 5)}-${schedule.end_time.slice(0, 5)}`;
  if (
    schedule.valid_from &&
    schedule.valid_to &&
    schedule.valid_from === schedule.valid_to
  ) {
    return `${schedule.valid_from} · ${timeRange}`;
  }
  return `${schedule.day_of_week} · ${timeRange}`;
}

function summarize(text?: string | null, fallback = "No summary available."): string {
  if (!text) {
    return fallback;
  }
  const normalized = text.trim();
  if (normalized.length <= 120) {
    return normalized;
  }
  return `${normalized.slice(0, 117).trimEnd()}...`;
}

function AdminOperationsPanel({
  patients,
  doctors,
  appointments,
  recentVisits,
  onNavigate,
}: {
  patients: PatientProfileResponseDto[];
  doctors: DoctorProfileResponseDto[];
  appointments: AppointmentResponseDto[];
  recentVisits: VisitResponseDto[];
  onNavigate: (tab: DashboardTab) => void;
}) {
  const [activeTab, setActiveTab] = useState<"patients" | "doctors">("patients");
  const [patientSearch, setPatientSearch] = useState("");
  const [doctorSearch, setDoctorSearch] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | null>(null);
  const [patientPage, setPatientPage] = useState(1);
  const [doctorPage, setDoctorPage] = useState(1);
  const [doctorEditForm, setDoctorEditForm] =
    useState<DoctorEditFormState | null>(null);
  const [doctorScheduleWorkspace, setDoctorScheduleWorkspace] =
    useState<DoctorScheduleWorkspaceState | null>(null);
  const [scheduleForm, setScheduleForm] =
    useState<DoctorScheduleCreateDto>(EMPTY_SCHEDULE_FORM);
  const [doctorManagementMessage, setDoctorManagementMessage] = useState<
    string | null
  >(null);

  const completedAppointments = appointments.filter(
    (appointment) =>
      appointment.status === "approved" &&
      appointment.scheduled_for &&
      new Date(appointment.scheduled_for) < new Date(),
  );
  const futureAppointments = appointments.filter(
    (appointment) =>
      appointment.status !== "rejected" &&
      (!appointment.scheduled_for ||
        new Date(appointment.scheduled_for) >= new Date()),
  );

  // Patient filtering
  const normalizedPatientSearch = patientSearch.trim().toLowerCase();
  const filteredPatients = patients.filter((patient) =>
    patient.national_id?.toLowerCase().includes(normalizedPatientSearch),
  );

  // Doctor filtering
  const normalizedDoctorSearch = doctorSearch.trim().toLowerCase();
  const filteredDoctors = doctors.filter((doctor) =>
    [doctor.full_name, doctor.specialty]
      .filter(Boolean)
      .some((value) => value!.toLowerCase().includes(normalizedDoctorSearch)),
  );

  // Selected entities with their related data
  const selectedPatient = selectedPatientId
    ? patients.find((p) => p.id === selectedPatientId)
    : null;
  const selectedDoctor = selectedDoctorId
    ? doctors.find((d) => d.id === selectedDoctorId)
    : null;
  const { t } = useLanguage();

  const patientAppointments = selectedPatient
    ? appointments.filter((a) => a.patient_id === selectedPatient.id)
    : [];
  const patientVisits = selectedPatient
    ? recentVisits.filter((v) => v.patient_id === selectedPatient.id)
    : [];
  const doctorAppointments = selectedDoctor
    ? appointments.filter((a) => a.doctor_id === selectedDoctor.id)
    : [];
  const selectedDoctorEditForm =
    selectedDoctor && doctorEditForm?.doctorId === selectedDoctor.id
      ? doctorEditForm.values
      : selectedDoctor
        ? toDoctorEditForm(selectedDoctor)
        : null;
  const doctorSchedules =
    selectedDoctor && doctorScheduleWorkspace?.doctorId === selectedDoctor.id
      ? doctorScheduleWorkspace.schedules
      : [];
  const doctorSlots =
    selectedDoctor && doctorScheduleWorkspace?.doctorId === selectedDoctor.id
      ? doctorScheduleWorkspace.slots
      : [];
  const doctorManagementLoading = selectedDoctor
    ? !doctorScheduleWorkspace ||
      doctorScheduleWorkspace.doctorId !== selectedDoctor.id ||
      doctorScheduleWorkspace.loading
    : false;

  useEffect(() => {
    if (!selectedDoctor) {
      return;
    }

    Promise.all([
      listDoctorSchedules(selectedDoctor.id),
      listDoctorSlots(selectedDoctor.id),
    ])
      .then(([schedules, slots]) => {
        setDoctorScheduleWorkspace({
          doctorId: selectedDoctor.id,
          schedules,
          slots,
          loading: false,
        });
      })
      .catch(() => {
        setDoctorScheduleWorkspace({
          doctorId: selectedDoctor.id,
          schedules: [],
          slots: [],
          loading: false,
        });
        setDoctorManagementMessage("Could not load schedules or slots.");
      });
  }, [selectedDoctor]);

  async function refreshDoctorScheduleWorkspace(doctorId: number) {
    const [schedules, slots] = await Promise.all([
      listDoctorSchedules(doctorId),
      listDoctorSlots(doctorId),
    ]);
    setDoctorScheduleWorkspace({
      doctorId,
      schedules,
      slots,
      loading: false,
    });
  }

  async function submitDoctorAdminUpdate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDoctor || !selectedDoctorEditForm) {
      return;
    }
    setDoctorScheduleWorkspace((current) => ({
      doctorId: selectedDoctor.id,
      schedules:
        current?.doctorId === selectedDoctor.id ? current.schedules : doctorSchedules,
      slots: current?.doctorId === selectedDoctor.id ? current.slots : doctorSlots,
      loading: true,
    }));
    setDoctorManagementMessage(null);
    try {
      await updateDoctorProfile(selectedDoctor.id, {
        ...selectedDoctorEditForm,
        area: selectedDoctorEditForm.area?.trim() || null,
        city: selectedDoctorEditForm.city?.trim() || null,
      });
      setDoctorManagementMessage("Doctor details saved.");
    } catch {
      setDoctorManagementMessage("Could not save doctor details.");
    } finally {
      setDoctorScheduleWorkspace((current) =>
        current?.doctorId === selectedDoctor.id
          ? { ...current, loading: false }
          : current,
      );
    }
  }

  async function submitDoctorSchedule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDoctor) {
      return;
    }
    setDoctorScheduleWorkspace((current) => ({
      doctorId: selectedDoctor.id,
      schedules:
        current?.doctorId === selectedDoctor.id ? current.schedules : doctorSchedules,
      slots: current?.doctorId === selectedDoctor.id ? current.slots : doctorSlots,
      loading: true,
    }));
    setDoctorManagementMessage(null);
    try {
      await createDoctorSchedule(selectedDoctor.id, {
        ...scheduleForm,
        location_label: scheduleForm.location_label || selectedDoctor.clinic,
      });
      await refreshDoctorScheduleWorkspace(selectedDoctor.id);
      setScheduleForm({
        ...EMPTY_SCHEDULE_FORM,
        location_label: selectedDoctor.clinic,
      });
      setDoctorManagementMessage("Schedule rule added and slots refreshed.");
    } catch {
      setDoctorManagementMessage("Could not add schedule rule.");
    } finally {
      setDoctorScheduleWorkspace((current) =>
        current?.doctorId === selectedDoctor.id
          ? { ...current, loading: false }
          : current,
      );
    }
  }

  async function toggleSchedule(schedule: DoctorScheduleDto, isActive: boolean) {
    if (!selectedDoctor) {
      return;
    }
    setDoctorScheduleWorkspace((current) => ({
      doctorId: selectedDoctor.id,
      schedules:
        current?.doctorId === selectedDoctor.id ? current.schedules : doctorSchedules,
      slots: current?.doctorId === selectedDoctor.id ? current.slots : doctorSlots,
      loading: true,
    }));
    setDoctorManagementMessage(null);
    try {
      await updateDoctorSchedule(selectedDoctor.id, schedule.id, {
        doctor_clinic_id: schedule.doctor_clinic_id ?? null,
        day_of_week: schedule.day_of_week,
        start_time: schedule.start_time,
        end_time: schedule.end_time,
        slot_minutes: schedule.slot_minutes,
        valid_from: schedule.valid_from ?? null,
        valid_to: schedule.valid_to ?? null,
        location_label: schedule.location_label ?? selectedDoctor.clinic,
        is_active: isActive,
      });
      await refreshDoctorScheduleWorkspace(selectedDoctor.id);
      setDoctorManagementMessage(
        isActive ? "Schedule activated." : "Schedule deactivated.",
      );
    } catch {
      setDoctorManagementMessage("Could not update schedule status.");
    } finally {
      setDoctorScheduleWorkspace((current) =>
        current?.doctorId === selectedDoctor.id
          ? { ...current, loading: false }
          : current,
      );
    }
  }

  function paginate<T>(items: T[], page: number): T[] {
    const start = (page - 1) * ADMIN_PROFILE_PAGE_SIZE;
    return items.slice(start, start + ADMIN_PROFILE_PAGE_SIZE);
  }

  function renderPagination(
    items: unknown[],
    page: number,
    setPage: (page: number) => void,
  ) {
    if (items.length <= ADMIN_PROFILE_PAGE_SIZE) {
      return null;
    }
    const pageCount = Math.ceil(items.length / ADMIN_PROFILE_PAGE_SIZE);
    const safePage = Math.min(page, pageCount);
    const startItem = (safePage - 1) * ADMIN_PROFILE_PAGE_SIZE + 1;
    const endItem = Math.min(safePage * ADMIN_PROFILE_PAGE_SIZE, items.length);

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

  return (
    <div className="stack-lg">
      <SectionPanel
        eyebrow={t("recordsTitle")}
        title={t("adminRecordsCenter")}
        description="Review all patient profiles, doctor profiles, appointments, and recent medical history without patient-facing demographic forms."
      >
        <div className="admin-metric-grid">
          <article className="metric-card">
            <span>{t("patientProfiles")}</span>
            <strong>{patients.length}</strong>
          </article>
          <article className="metric-card">
            <span>{t("doctorProfiles")}</span>
            <strong>{doctors.length}</strong>
          </article>
          <article className="metric-card">
            <span>{t("upcomingAppointments")}</span>
            <strong>{futureAppointments.length}</strong>
          </article>
          <article className="metric-card">
            <span>{t("completed")}</span>
            <strong>{completedAppointments.length}</strong>
          </article>
          <article className="metric-card">
            <span>{t("recentVisits")}</span>
            <strong>{recentVisits.length}</strong>
          </article>
          <article className="metric-card">
            <span>{t("pendingApprovals")}</span>
            <strong>
              {
                appointments.filter((appointment) => appointment.status === "requested")
                  .length
              }
            </strong>
          </article>
        </div>

        <div className="action-grid">
          <button
            type="button"
            className="action-shortcut"
            onClick={() => onNavigate("appointments")}
          >
            <strong>{t("reviewAppointments")}</strong>
            <span>{t("appointmentsDescription")}</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("visits")}
          >
            <strong>{t("medicalHistory")}</strong>
            <span>Inspect recent visits and add clinician records when needed.</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("profile")}
          >
            <strong>{t("reviewProfiles")}</strong>
            <span>Filter patient and doctor records from one compact admin view.</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("records")}
          >
            <strong>{t("importRecords")}</strong>
            <span>Import structured medical records into the visit history.</span>
          </button>
        </div>
      </SectionPanel>

      <SectionPanel
        eyebrow={t("adminActions")}
        title={t("reviewProfiles")}
        description="Search and view detailed patient and doctor profiles with their appointments and medical history."
      >
        <div className="segmented-control">
          <button
            type="button"
            className={activeTab === "patients" ? "is-active" : ""}
            onClick={() => {
              setActiveTab("patients");
              setSelectedPatientId(null);
            }}
          >
            Patient Profiles
          </button>
          <button
            type="button"
            className={activeTab === "doctors" ? "is-active" : ""}
            onClick={() => {
              setActiveTab("doctors");
              setSelectedDoctorId(null);
            }}
          >
            Doctor Profiles
          </button>
        </div>

        {activeTab === "patients" ? (
          <div className="stack-md">
            <div className="field">
              <label htmlFor="patient-search">{t("patientNationalId")}</label>
              <input
                id="patient-search"
                value={patientSearch}
                onChange={(event) => {
                  setPatientSearch(event.target.value);
                  setPatientPage(1);
                }}
                placeholder="Enter patient national ID"
              />
            </div>

            {selectedPatient ? (
              <section className="workspace-card workspace-card--compact">
                <div className="workspace-card__header">
                  <div>
                    <p className="micro-label">{t("patientProfiles")}</p>
                    <h3>{selectedPatient.full_name}</h3>
                  </div>
                  <button
                    type="button"
                    className="button button--ghost button--small"
                    onClick={() => setSelectedPatientId(null)}
                  >
                    Close
                  </button>
                </div>

                <div className="detail-list">
                  <div>
                    <strong>{t("fullName")}</strong>
                    <span>{selectedPatient.full_name}</span>
                  </div>
                  <div>
                    <strong>Age</strong>
                    <span>{selectedPatient.age}</span>
                  </div>
                  <div>
                    <strong>{t("gender")}</strong>
                    <span>{selectedPatient.sex}</span>
                  </div>
                  <div>
                    <strong>{t("egyptianNationalId")}</strong>
                    <span>{selectedPatient.national_id || "Not recorded"}</span>
                  </div>
                  <div>
                    <strong>{t("governoratePending")}</strong>
                    <span>
                      {selectedPatient.current_governorate ||
                        selectedPatient.inferred_governorate ||
                        "Pending"}
                    </span>
                  </div>
                  <div>
                    <strong>{t("medicalHistory")}</strong>
                    <span>
                      {selectedPatient.chronic_conditions.length > 0
                        ? selectedPatient.chronic_conditions.join(", ")
                        : "None recorded"}
                    </span>
                  </div>
                  <div>
                    <strong>Smoker</strong>
                    <span>{selectedPatient.smoker ? "Yes" : "No"}</span>
                  </div>
                  <div>
                    <strong>Alcoholic</strong>
                    <span>{selectedPatient.alcoholic ? "Yes" : "No"}</span>
                  </div>
                </div>

                <div className="stack-md">
                  <div>
                    <p className="micro-label">Appointments ({patientAppointments.length})</p>
                    <div className="activity-list">
                      {patientAppointments.length === 0 ? (
                        <div className="empty-state">No appointments recorded.</div>
                      ) : (
                        patientAppointments
                          .slice(0, ADMIN_RELATED_RECORD_LIMIT)
                          .map((appointment) => (
                          <article key={appointment.id} className="activity-item">
                            <div>
                              <strong>Appointment #{appointment.id}</strong>
                              <p>{appointment.reason}</p>
                              <p>
                                Doctor #
                                {
                                  doctors.find((d) => d.id === appointment.doctor_id)
                                    ?.full_name
                                }
                              </p>
                            </div>
                            <div className="activity-meta">
                              <span className={`badge badge--status-${appointment.status}`}>
                                {localizeAppointmentStatus(appointment.status, t)}
                              </span>
                              <small>{formatDateTime(appointment.scheduled_for || appointment.requested_at)}</small>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                    {patientAppointments.length > ADMIN_RELATED_RECORD_LIMIT ? (
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        onClick={() => onNavigate("appointments")}
                      >
                        View all {patientAppointments.length} appointments
                      </button>
                    ) : null}
                  </div>

                  <div>
                    <p className="micro-label">Visits ({patientVisits.length})</p>
                    <div className="activity-list">
                      {patientVisits.length === 0 ? (
                        <div className="empty-state">No visits recorded.</div>
                      ) : (
                        patientVisits.slice(0, ADMIN_RELATED_RECORD_LIMIT).map((visit) => (
                          <article key={visit.id} className="activity-item">
                            <div>
                              <strong>{visit.diagnosis || "Visit record"}</strong>
                              <p>{summarize(visit.symptoms)}</p>
                              <p>{summarize(visit.notes, "No notes")}</p>
                            </div>
                            <div className="activity-meta">
                              <small>{formatDateTime(visit.created_at)}</small>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                    {patientVisits.length > ADMIN_RELATED_RECORD_LIMIT ? (
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        onClick={() => onNavigate("visits")}
                      >
                        View all {patientVisits.length} visits
                      </button>
                    ) : null}
                  </div>
                </div>
              </section>
            ) : (
              <div className="stack-md">
                {filteredPatients.length === 0 ? (
                  <div className="empty-state">
                    {patientSearch
                      ? "No patients match your search. Try a different national ID."
                      : "Enter a national ID to search for patients."}
                  </div>
                ) : (
                  <>
                    <div className="profile-record-table">
                      <div className="profile-record-table__header">
                        <span>Patient</span>
                        <span>National ID</span>
                        <span>Governorate</span>
                        <span>Updated</span>
                        <span>Action</span>
                      </div>
                      {paginate(filteredPatients, patientPage).map((patient) => (
                        <button
                          key={patient.id}
                          type="button"
                          className="profile-record-table__row"
                          onClick={() => setSelectedPatientId(patient.id)}
                        >
                          <strong>{patient.full_name}</strong>
                          <span>{patient.national_id || "Not recorded"}</span>
                          <span>
                            {patient.current_governorate ||
                              patient.inferred_governorate ||
                              "Pending"}
                          </span>
                          <span>{formatDateTime(patient.updated_at)}</span>
                          <span className="button button--ghost button--small">
                            View
                          </span>
                        </button>
                      ))}
                    </div>
                    {renderPagination(filteredPatients, patientPage, setPatientPage)}
                  </>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="stack-md">
            <div className="field">
              <label htmlFor="doctor-search">Search by name or specialty</label>
              <input
                id="doctor-search"
                value={doctorSearch}
                onChange={(event) => {
                  setDoctorSearch(event.target.value);
                  setDoctorPage(1);
                }}
                placeholder="Enter doctor name or specialty"
              />
            </div>

            {selectedDoctor ? (
              <section className="workspace-card workspace-card--compact">
                <div className="workspace-card__header">
                  <div>
                    <p className="micro-label">{t("doctorProfiles")}</p>
                    <h3>{selectedDoctor.full_name}</h3>
                  </div>
                  <button
                    type="button"
                    className="button button--ghost button--small"
                    onClick={() => setSelectedDoctorId(null)}
                  >
                    Close
                  </button>
                </div>

                <div className="detail-list">
                  <div>
                    <strong>{t("fullName")}</strong>
                    <span>{selectedDoctor.full_name}</span>
                  </div>
                  <div>
                    <strong>{t("specialty")}</strong>
                    <span>{selectedDoctor.specialty}</span>
                  </div>
                  <div>
                    <strong>{t("clinicReview")}</strong>
                    <span>{selectedDoctor.clinic || "Not specified"}</span>
                  </div>
                  <div>
                    <strong>Area</strong>
                    <span>{selectedDoctor.area || "Not specified"}</span>
                  </div>
                  <div>
                    <strong>{t("governoratePending")}</strong>
                    <span>{selectedDoctor.city || "Not specified"}</span>
                  </div>
                  <div>
                    <strong>Consultation fee</strong>
                    <span>
                      {selectedDoctor.consultation_fee != null
                        ? `${selectedDoctor.consultation_fee} EGP`
                        : "Not specified"}
                    </span>
                  </div>
                  <div>
                    <strong>Video visits</strong>
                    <span>
                      {selectedDoctor.offers_telemedicine ? "Available" : "Clinic only"}
                    </span>
                  </div>
                </div>

                {selectedDoctorEditForm ? (
                  <form
                    className="form-grid admin-management-panel"
                    onSubmit={submitDoctorAdminUpdate}
                  >
                    <div className="field">
                      <label htmlFor="admin-doctor-name">{t("fullName")}</label>
                      <input
                        id="admin-doctor-name"
                        value={selectedDoctorEditForm.full_name}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              full_name: event.target.value,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="admin-doctor-specialty">
                        {t("specialty")}
                      </label>
                      <input
                        id="admin-doctor-specialty"
                        value={selectedDoctorEditForm.specialty}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              specialty: event.target.value,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="admin-doctor-clinic">
                        {t("clinicReview")}
                      </label>
                      <input
                        id="admin-doctor-clinic"
                        value={selectedDoctorEditForm.clinic}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              clinic: event.target.value,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="admin-doctor-city">{t("city")}</label>
                      <CustomSelect
                        id="admin-doctor-city"
                        value={selectedDoctorEditForm.city ?? ""}
                        onChange={(value) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              city: value,
                              area:
                                value === "Alexandria"
                                  ? selectedDoctorEditForm.area
                                  : "",
                            },
                          })
                        }
                        options={[
                          { value: "", label: "Select governorate" },
                          ...EGYPTIAN_GOVERNORATES.map((governorate) => ({
                            value: governorate,
                            label: governorate,
                          })),
                        ]}
                      />
                    </div>
                    {selectedDoctorEditForm.city === "Alexandria" ? (
                      <div className="field">
                        <label htmlFor="admin-doctor-area">{t("area")}</label>
                        <CustomSelect
                          id="admin-doctor-area"
                          value={selectedDoctorEditForm.area ?? ""}
                          onChange={(value) =>
                            setDoctorEditForm({
                              doctorId: selectedDoctor.id,
                              values: {
                                ...selectedDoctorEditForm,
                                area: value,
                              },
                            })
                          }
                          options={[
                            { value: "", label: "Select area" },
                            ...ALEXANDRIA_AREAS.map((area) => ({
                              value: area,
                              label: area,
                            })),
                          ]}
                        />
                      </div>
                    ) : null}
                    <div className="field">
                      <label htmlFor="admin-doctor-fee">Consultation fee</label>
                      <input
                        id="admin-doctor-fee"
                        type="number"
                        min="0"
                        value={selectedDoctorEditForm.consultation_fee ?? ""}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              consultation_fee: event.target.value
                                ? Number(event.target.value)
                                : null,
                            },
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="admin-doctor-insurance">
                        Accepted insurance
                      </label>
                      <input
                        id="admin-doctor-insurance"
                        value={selectedDoctorEditForm.insurance_providers.join(", ")}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              insurance_providers: splitCommaList(
                                event.target.value,
                              ),
                            },
                          })
                        }
                        placeholder="Bupa, Allianz,..."
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="admin-doctor-payments">Payment methods</label>
                      <input
                        id="admin-doctor-payments"
                        value={selectedDoctorEditForm.payment_methods.join(", ")}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              payment_methods: splitCommaList(event.target.value),
                            },
                          })
                        }
                        placeholder="Cash, Card, Insurance"
                      />
                    </div>
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={selectedDoctorEditForm.offers_telemedicine}
                        onChange={(event) =>
                          setDoctorEditForm({
                            doctorId: selectedDoctor.id,
                            values: {
                              ...selectedDoctorEditForm,
                              offers_telemedicine: event.target.checked,
                            },
                          })
                        }
                      />
                      <span>Offers video consultations</span>
                    </label>
                    <button
                      type="submit"
                      className="button button--primary"
                      disabled={doctorManagementLoading}
                    >
                      {doctorManagementLoading
                        ? t("working")
                        : t("saveDoctorDetails")}
                    </button>
                  </form>
                ) : null}

                <div className="schedule-management-panel">
                  <div className="workspace-card__header">
                    <div>
                      <p className="micro-label">{t("doctorSchedules")}</p>
                      <h3>{t("scheduleManagement")}</h3>
                    </div>
                    <span className="badge">
                      {doctorSlots.length} {t("availableSlots")}
                    </span>
                  </div>

                  {doctorManagementMessage ? (
                    <div className="notice">{doctorManagementMessage}</div>
                  ) : null}

                  <form className="form-grid" onSubmit={submitDoctorSchedule}>
                    <div className="field">
                      <label htmlFor="schedule-specific-date">
                        {t("specificDate")}
                      </label>
                      <input
                        id="schedule-specific-date"
                        type="date"
                        min={todayDateInputValue()}
                        value={
                          scheduleForm.valid_from === scheduleForm.valid_to
                            ? (scheduleForm.valid_from ?? "")
                            : ""
                        }
                        onChange={(event) => {
                          const value = event.target.value;
                          setScheduleForm((current) => ({
                            ...current,
                            day_of_week: value
                              ? weekdayFromDateInput(value)
                              : current.day_of_week,
                            valid_from: value || null,
                            valid_to: value || null,
                          }));
                        }}
                      />
                      <small className="field__hint">
                        {t("specificDateHint")}
                      </small>
                    </div>
                    <div className="field">
                      <label htmlFor="schedule-day">{t("dayOfWeek")}</label>
                      <CustomSelect
                        id="schedule-day"
                        value={scheduleForm.day_of_week}
                        onChange={(value) =>
                          setScheduleForm((current) => ({
                            ...current,
                            day_of_week: value,
                          }))
                        }
                        disabled={Boolean(scheduleForm.valid_from)}
                        options={[
                          ...WEEKDAY_OPTIONS.map((day) => ({
                            value: day,
                            label: day,
                          })),
                        ]}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="schedule-start">{t("startTime")}</label>
                      <input
                        id="schedule-start"
                        type="time"
                        value={scheduleForm.start_time.slice(0, 5)}
                        onChange={(event) =>
                          setScheduleForm((current) => ({
                            ...current,
                            start_time: `${event.target.value}:00`,
                          }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="schedule-end">{t("endTime")}</label>
                      <input
                        id="schedule-end"
                        type="time"
                        value={scheduleForm.end_time.slice(0, 5)}
                        onChange={(event) =>
                          setScheduleForm((current) => ({
                            ...current,
                            end_time: `${event.target.value}:00`,
                          }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="schedule-minutes">
                        {t("slotMinutes")}
                      </label>
                      <input
                        id="schedule-minutes"
                        type="number"
                        min={5}
                        max={240}
                        value={scheduleForm.slot_minutes}
                        onChange={(event) =>
                          setScheduleForm((current) => ({
                            ...current,
                            slot_minutes: Number(event.target.value),
                          }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="schedule-location">
                        {t("clinicReview")}
                      </label>
                      <input
                        id="schedule-location"
                        value={scheduleForm.location_label ?? ""}
                        onChange={(event) =>
                          setScheduleForm((current) => ({
                            ...current,
                            location_label: event.target.value,
                          }))
                        }
                      />
                    </div>
                    <button
                      type="submit"
                      className="button button--primary"
                      disabled={doctorManagementLoading}
                    >
                      {doctorManagementLoading ? t("working") : t("addSchedule")}
                    </button>
                  </form>

                  <div className="activity-list compact">
                    {doctorSchedules.length === 0 ? (
                      <div className="empty-state">{t("noSchedulesRecorded")}</div>
                    ) : (
                      doctorSchedules.map((schedule) => (
                        <article key={schedule.id} className="activity-item">
                          <div>
                            <strong>
                              {schedule.day_of_week} · {schedule.start_time.slice(0, 5)}
                              -{schedule.end_time.slice(0, 5)}
                            </strong>
                            <p title={describeScheduleRule(schedule)}>
                              {schedule.slot_minutes} {t("minutes")} ·{" "}
                              {schedule.location_label ||
                                selectedDoctor?.clinic ||
                                "Clinic"}
                            </p>
                          </div>
                          <div className="activity-meta">
                            <span
                              className={`badge ${
                                schedule.is_active
                                  ? "badge--status-approved"
                                  : "badge--status-rejected"
                              }`}
                            >
                              {schedule.is_active ? t("active") : t("inactive")}
                            </span>
                            <button
                              type="button"
                              className="button button--ghost button--small"
                              disabled={doctorManagementLoading}
                              onClick={() =>
                                toggleSchedule(schedule, !schedule.is_active)
                              }
                            >
                              {schedule.is_active
                                ? t("deactivate")
                                : t("activate")}
                            </button>
                          </div>
                        </article>
                      ))
                    )}
                  </div>

                  <div className="activity-list compact">
                    <p className="micro-label">{t("availableSlots")}</p>
                    {doctorSlots.length === 0 ? (
                      <div className="empty-state">{t("noSlotsAvailable")}</div>
                    ) : (
                      doctorSlots.slice(0, 8).map((slot) => (
                        <article key={slot.id} className="activity-item">
                          <div>
                            <strong>{formatDateTime(slot.start_at)}</strong>
                            <p>
                              {slot.clinic?.name ||
                                selectedDoctor?.clinic ||
                                "Clinic"}{" "}
                              · {slot.clinic?.area || selectedDoctor?.area}
                            </p>
                          </div>
                          <div className="activity-meta">
                            <span className="badge">{localizeSlotStatus(slot.status, t)}</span>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </div>

                <div className="stack-md">
                  <div>
                    <p className="micro-label">Appointments ({doctorAppointments.length})</p>
                    <div className="activity-list">
                      {doctorAppointments.length === 0 ? (
                        <div className="empty-state">No appointments recorded.</div>
                      ) : (
                        doctorAppointments
                          .slice(0, ADMIN_RELATED_RECORD_LIMIT)
                          .map((appointment) => (
                          <article key={appointment.id} className="activity-item">
                            <div>
                              <strong>Appointment #{appointment.id}</strong>
                              <p>{appointment.reason}</p>
                              <p>
                                Patient #
                                {
                                  patients.find((p) => p.id === appointment.patient_id)
                                    ?.full_name
                                }
                              </p>
                            </div>
                            <div className="activity-meta">
                              <span className={`badge badge--status-${appointment.status}`}>
                                {localizeAppointmentStatus(appointment.status, t)}
                              </span>
                              <small>{formatDateTime(appointment.scheduled_for || appointment.requested_at)}</small>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                    {doctorAppointments.length > ADMIN_RELATED_RECORD_LIMIT ? (
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        onClick={() => onNavigate("appointments")}
                      >
                        View all {doctorAppointments.length} appointments
                      </button>
                    ) : null}
                  </div>
                </div>
              </section>
            ) : (
              <div className="stack-md">
                {filteredDoctors.length === 0 ? (
                  <div className="empty-state">
                    {doctorSearch
                      ? "No doctors match your search. Try a different name or specialty."
                      : "Enter a name or specialty to search for doctors."}
                  </div>
                ) : (
                  <>
                    <div className="profile-record-table profile-record-table--doctors">
                      <div className="profile-record-table__header">
                        <span>Doctor</span>
                        <span>Specialty</span>
                        <span>Location</span>
                        <span>Updated</span>
                        <span>Action</span>
                      </div>
                      {paginate(filteredDoctors, doctorPage).map((doctor) => (
                        <button
                          key={doctor.id}
                          type="button"
                          className="profile-record-table__row"
                          onClick={() => setSelectedDoctorId(doctor.id)}
                        >
                          <strong>{doctor.full_name}</strong>
                          <span>{doctor.specialty}</span>
                          <span>
                            {[doctor.area, doctor.city].filter(Boolean).join(", ") ||
                              doctor.clinic}
                          </span>
                          <span>{formatDateTime(doctor.updated_at)}</span>
                          <span className="button button--ghost button--small">
                            View
                          </span>
                        </button>
                      ))}
                    </div>
                    {renderPagination(filteredDoctors, doctorPage, setDoctorPage)}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </SectionPanel>

      {/* Keep a short operational summary below the management grid. */}
      <div className="activity-columns">
        <SectionPanel
          eyebrow={t("patientProfiles")}
          title={t("updateProfile")}
          description="A short operational snapshot of the latest profile changes."
        >
          <div className="activity-list compact">
            {patients.slice(0, 4).map((patient) => (
              <article key={patient.id} className="activity-item">
                <div>
                  <strong>{patient.full_name}</strong>
                  <p>
                    {patient.national_id
                      ? `National ID: ${patient.national_id}`
                      : "National ID not recorded"}
                  </p>
                  <p>
                    {patient.current_governorate ||
                      patient.inferred_governorate ||
                      "Governorate pending"}
                  </p>
                </div>
                <div className="activity-meta">
                  <small>{formatDateTime(patient.updated_at)}</small>
                </div>
              </article>
            ))}
          </div>
        </SectionPanel>

        <SectionPanel
          eyebrow={t("doctorProfiles")}
          title={t("updateDoctorDirectory")}
          description="Recently updated clinicians and public directory entries."
        >
          <div className="activity-list compact">
            {doctors.slice(0, 4).map((doctor) => (
              <article key={doctor.id} className="activity-item">
                <div>
                  <strong>{doctor.full_name}</strong>
                  <p>{doctor.specialty}</p>
                  <p>
                    {doctor.area || doctor.city
                      ? [doctor.area, doctor.city].filter(Boolean).join(", ")
                      : doctor.clinic}
                  </p>
                </div>
                <div className="activity-meta">
                  <small>{formatDateTime(doctor.updated_at)}</small>
                </div>
              </article>
            ))}
          </div>
        </SectionPanel>
      </div>
    </div>
  );
}

export default function ProfilePanel({
  role,
  patientProfile,
  doctorProfile,
  savingPatient,
  savingDoctor,
  patients,
  doctors,
  appointments,
  recentVisits,
  onNavigate,
  onSavePatient,
  onSaveDoctor,
}: ProfilePanelProps) {
  const { t } = useLanguage();
  const [patientForm, setPatientForm] = useState<PatientProfileFormState>(
    patientProfile
      ? {
          full_name: patientProfile.full_name,
          age: patientProfile.age,
          sex: patientProfile.sex,
          national_id: patientProfile.national_id ?? "",
          current_governorate: patientProfile.current_governorate ?? "",
          smoker: patientProfile.smoker,
          alcoholic: patientProfile.alcoholic,
          chronic_conditions: patientProfile.chronic_conditions,
        }
      : EMPTY_PATIENT_FORM,
  );
  const doctorSpecialtyParts = useMemo(
    () => splitDoctorSpecialty(doctorProfile?.specialty ?? ""),
    [doctorProfile?.specialty],
  );
  const [doctorPrimarySpecialty, setDoctorPrimarySpecialty] = useState(
    doctorSpecialtyParts.primarySpecialty,
  );
  const [doctorSpecialtyScope, setDoctorSpecialtyScope] = useState(
    doctorSpecialtyParts.specialtyScope,
  );
  const [doctorForm, setDoctorForm] = useState<DoctorProfileUpsertDto>(
    doctorProfile
      ? {
          full_name: doctorProfile.full_name,
          specialty: doctorProfile.specialty,
          clinic: doctorProfile.clinic,
          area: doctorProfile.area ?? "",
          city: doctorProfile.city ?? "",
          consultation_fee: doctorProfile.consultation_fee ?? null,
          insurance_providers: doctorProfile.insurance_providers ?? [],
          payment_methods: doctorProfile.payment_methods ?? [],
          offers_telemedicine: doctorProfile.offers_telemedicine ?? false,
        }
      : {
          full_name: "",
          specialty: "",
          clinic: "",
          area: "",
          city: "",
          consultation_fee: null,
          insurance_providers: [],
          payment_methods: [],
          offers_telemedicine: false,
        },
  );
  const [ownScheduleWorkspace, setOwnScheduleWorkspace] =
    useState<DoctorScheduleWorkspaceState | null>(null);
  const [ownScheduleForm, setOwnScheduleForm] =
    useState<DoctorScheduleCreateDto>({
      ...EMPTY_SCHEDULE_FORM,
      location_label: doctorProfile?.clinic ?? "",
    });
  const [ownScheduleMessage, setOwnScheduleMessage] = useState<string | null>(
    null,
  );
  const [chronicConditionsInput, setChronicConditionsInput] = useState(
    patientProfile?.chronic_conditions.join(", ") ?? "",
  );
  const [historyCategory, setHistoryCategory] = useState("diagnosed_condition");
  const [historyTitle, setHistoryTitle] = useState("");
  const [historyNotes, setHistoryNotes] = useState("");
  const [historySaving, setHistorySaving] = useState(false);
  const [historyReportLoading, setHistoryReportLoading] = useState(false);
  const [historyMessage, setHistoryMessage] = useState<string | null>(null);
  const [patientHistory, setPatientHistory] =
    useState<PatientHistoryState | null>(null);
  const historyEntries =
    role === "patient" &&
    patientProfile &&
    patientHistory?.patientId === patientProfile.id
      ? patientHistory.entries
      : [];

  useEffect(() => {
    if (role !== "patient" || !patientProfile) {
      return;
    }

    let cancelled = false;
    listPatientMedicalHistory(patientProfile.id)
      .then((entries) => {
        if (!cancelled) {
          setPatientHistory({ patientId: patientProfile.id, entries });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPatientHistory({ patientId: patientProfile.id, entries: [] });
          setHistoryMessage("Could not load saved medical history entries.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [patientProfile, role]);

  useEffect(() => {
    if (role !== "doctor" || !doctorProfile) {
      Promise.resolve().then(() => setOwnScheduleWorkspace(null));
      return;
    }

    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) {
        return;
      }
      setOwnScheduleWorkspace({
        doctorId: doctorProfile.id,
        schedules: [],
        slots: [],
        loading: true,
      });
      setOwnScheduleForm((current) => ({
        ...current,
        location_label: current.location_label || doctorProfile.clinic,
      }));
    });

    Promise.all([
      listDoctorSchedules(doctorProfile.id),
      listDoctorSlots(doctorProfile.id),
    ])
      .then(([schedules, slots]) => {
        if (!cancelled) {
          setOwnScheduleWorkspace({
            doctorId: doctorProfile.id,
            schedules,
            slots,
            loading: false,
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOwnScheduleWorkspace({
            doctorId: doctorProfile.id,
            schedules: [],
            slots: [],
            loading: false,
          });
          setOwnScheduleMessage("Could not load your schedule.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [doctorProfile, role]);

  const parsedNationalId = useMemo(
    () =>
      patientForm.national_id
        ? parseEgyptianNationalId(patientForm.national_id)
        : null,
    [patientForm.national_id],
  );

  const specialtyOptions = useMemo(
    () =>
      MEDICAL_SPECIALTY_GROUPS.find(
        (option) => option.label === doctorPrimarySpecialty,
      )?.scopes ?? [],
    [doctorPrimarySpecialty],
  );

  async function submitPatientProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (patientForm.sex !== "Male" && patientForm.sex !== "Female") {
      return;
    }
    await onSavePatient({
      ...patientForm,
      sex: patientForm.sex,
      chronic_conditions: chronicConditionsInput
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
  }

  async function submitDoctorProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const specialty = composeDoctorSpecialty(
      doctorPrimarySpecialty,
      doctorSpecialtyScope,
    );
    await onSaveDoctor({
      ...doctorForm,
      specialty,
      area: doctorForm.area?.trim() || null,
      city: doctorForm.city?.trim() || null,
      consultation_fee:
        doctorForm.consultation_fee === null ||
        doctorForm.consultation_fee === undefined
          ? null
          : Number(doctorForm.consultation_fee),
      insurance_providers: doctorForm.insurance_providers,
      payment_methods: doctorForm.payment_methods,
      offers_telemedicine: doctorForm.offers_telemedicine,
    });
  }

  async function refreshOwnScheduleWorkspace(doctorId: number) {
    const [schedules, slots] = await Promise.all([
      listDoctorSchedules(doctorId),
      listDoctorSlots(doctorId),
    ]);
    setOwnScheduleWorkspace({
      doctorId,
      schedules,
      slots,
      loading: false,
    });
  }

  async function submitOwnDoctorSchedule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!doctorProfile) {
      return;
    }
    setOwnScheduleWorkspace((current) => ({
      doctorId: doctorProfile.id,
      schedules:
        current?.doctorId === doctorProfile.id ? current.schedules : [],
      slots: current?.doctorId === doctorProfile.id ? current.slots : [],
      loading: true,
    }));
    setOwnScheduleMessage(null);
    try {
      await createDoctorSchedule(doctorProfile.id, {
        ...ownScheduleForm,
        location_label: ownScheduleForm.location_label || doctorProfile.clinic,
      });
      await refreshOwnScheduleWorkspace(doctorProfile.id);
      setOwnScheduleForm({
        ...EMPTY_SCHEDULE_FORM,
        location_label: doctorProfile.clinic,
      });
      setOwnScheduleMessage("Availability added and appointment slots refreshed.");
    } catch {
      setOwnScheduleMessage("Could not add availability.");
    } finally {
      setOwnScheduleWorkspace((current) =>
        current?.doctorId === doctorProfile.id
          ? { ...current, loading: false }
          : current,
      );
    }
  }

  async function toggleOwnSchedule(
    schedule: DoctorScheduleDto,
    isActive: boolean,
  ) {
    if (!doctorProfile) {
      return;
    }
    setOwnScheduleWorkspace((current) => ({
      doctorId: doctorProfile.id,
      schedules:
        current?.doctorId === doctorProfile.id ? current.schedules : [],
      slots: current?.doctorId === doctorProfile.id ? current.slots : [],
      loading: true,
    }));
    setOwnScheduleMessage(null);
    try {
      await updateDoctorSchedule(doctorProfile.id, schedule.id, {
        doctor_clinic_id: schedule.doctor_clinic_id ?? null,
        day_of_week: schedule.day_of_week,
        start_time: schedule.start_time,
        end_time: schedule.end_time,
        slot_minutes: schedule.slot_minutes,
        valid_from: schedule.valid_from ?? null,
        valid_to: schedule.valid_to ?? null,
        location_label: schedule.location_label ?? doctorProfile.clinic,
        is_active: isActive,
      });
      await refreshOwnScheduleWorkspace(doctorProfile.id);
      setOwnScheduleMessage(
        isActive ? "Availability activated." : "Availability deactivated.",
      );
    } catch {
      setOwnScheduleMessage("Could not update availability.");
    } finally {
      setOwnScheduleWorkspace((current) =>
        current?.doctorId === doctorProfile.id
          ? { ...current, loading: false }
          : current,
      );
    }
  }

  async function submitMedicalHistoryEntry(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    if (!patientProfile || !historyTitle.trim()) {
      return;
    }
    setHistorySaving(true);
    setHistoryMessage(null);
    try {
      const created = await createPatientMedicalHistoryEntry(patientProfile.id, {
        category: historyCategory,
        title: historyTitle.trim(),
        notes: historyNotes.trim() || null,
        status: "active",
      });
      setPatientHistory((current) => ({
        patientId: patientProfile.id,
        entries:
          current?.patientId === patientProfile.id
            ? [created, ...current.entries]
            : [created],
      }));
      setHistoryTitle("");
      setHistoryNotes("");
      setHistoryMessage("Medical history entry saved.");
    } catch {
      setHistoryMessage("Could not save medical history entry.");
    } finally {
      setHistorySaving(false);
    }
  }

  async function handleMedicalHistoryReportUpload(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !patientProfile) {
      return;
    }

    setHistoryReportLoading(true);
    setHistoryMessage(null);
    try {
      const extracted = await extractPatientMedicalHistoryReport(
        patientProfile.id,
        file,
      );
      setHistoryCategory(extracted.category);
      setHistoryTitle(extracted.title);
      setHistoryNotes(extracted.notes);
      setHistoryMessage(
        extracted.warning ||
          "Report read successfully. Review the fields before saving.",
      );
    } catch {
      setHistoryMessage(
        "Could not read this report. Try a text PDF, or enter the details manually.",
      );
    } finally {
      setHistoryReportLoading(false);
    }
  }

  const dateOfBirth =
    parsedNationalId?.dateOfBirth ??
    patientProfile?.date_of_birth ??
    "Derived after validation";
  const inferredGovernorate =
    parsedNationalId?.governorate ??
    patientProfile?.inferred_governorate ??
    "Will be inferred from the national ID";
  const patientResidence = splitResidenceLocation(
    patientForm.current_governorate,
  );
  const nationalIdHasValue = Boolean(patientForm.national_id?.trim());
  const nationalIdInvalid = nationalIdHasValue && !parsedNationalId;
  const ownDoctorSchedules =
    doctorProfile && ownScheduleWorkspace?.doctorId === doctorProfile.id
      ? ownScheduleWorkspace.schedules
      : [];
  const ownDoctorSlots =
    doctorProfile && ownScheduleWorkspace?.doctorId === doctorProfile.id
      ? ownScheduleWorkspace.slots
      : [];
  const ownScheduleLoading = Boolean(
    doctorProfile &&
      (!ownScheduleWorkspace ||
        ownScheduleWorkspace.doctorId !== doctorProfile.id ||
        ownScheduleWorkspace.loading),
  );

  if (role === "admin") {
    return (
      <AdminOperationsPanel
        patients={patients}
        doctors={doctors}
        appointments={appointments}
        recentVisits={recentVisits}
        onNavigate={onNavigate}
      />
    );
  }

  return (
    <div className="stack-lg">
      {role === "patient" ? (
        <SectionPanel
          eyebrow={t("patientProfiles")}
          title={t("profileTitle")}
          description="This profile powers patient-aware triage, appointments, and visit history. The national ID can derive date of birth and the governorate encoded inside the ID, while current residence stays editable."
        >
          <form className="form-grid" onSubmit={submitPatientProfile}>
            <div className="field">
              <label htmlFor="patient-full-name">{t("fullName")}</label>
              <input
                id="patient-full-name"
                value={patientForm.full_name}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="patient-sex">Gender</label>
              <CustomSelect
                id="patient-sex"
                value={patientForm.sex}
                onChange={(value) =>
                  setPatientForm((current) => ({
                    ...current,
                    sex: value as PatientProfileFormState["sex"],
                  }))
                }
                options={[
                  { value: "", label: t("selectGender") },
                  { value: "Male", label: t("male") },
                  { value: "Female", label: t("female") },
                ]}
              />
            </div>

            <div className="field">
              <label htmlFor="patient-national-id">{t("egyptianNationalId")}</label>
              <input
                id="patient-national-id"
                inputMode="numeric"
                maxLength={14}
                value={patientForm.national_id ?? ""}
                onChange={(event) => {
                  const nextValue = event.target.value.replace(/\D/g, "").slice(0, 14);
                  const parsed = parseEgyptianNationalId(nextValue);
                  setPatientForm((current) => ({
                    ...current,
                    ...(() => {
                      const previousParsed = current.national_id
                        ? parseEgyptianNationalId(current.national_id)
                        : null;
                      const shouldPrefillGovernorate =
                        !current.current_governorate ||
                        current.current_governorate === previousParsed?.governorate;
                      return {
                        current_governorate:
                          parsed && shouldPrefillGovernorate
                            ? parsed.governorate
                            : current.current_governorate,
                      };
                    })(),
                    national_id: nextValue,
                    age: parsed?.age ?? current.age,
                  }));
                }}
                placeholder="14-digit الرقم القومي"
              />
            </div>

            <div className="field">
              <label htmlFor="patient-age">Age</label>
              <input
                id="patient-age"
                type="number"
                min={0}
                max={130}
                value={patientForm.age}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    age: Number(event.target.value),
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="patient-dob">Date of birth from national ID</label>
              <input id="patient-dob" value={dateOfBirth} readOnly />
            </div>

            <div className="field">
              <label htmlFor="patient-inferred-governorate">
                Governorate from national ID
              </label>
              <input
                id="patient-inferred-governorate"
                value={inferredGovernorate}
                readOnly
              />
            </div>

            <div className="field">
              <label htmlFor="patient-current-governorate">
                Current governorate / residence
              </label>
              <CustomSelect
                id="patient-current-governorate"
                value={patientResidence.governorate}
                onChange={(value) =>
                  setPatientForm((current) => ({
                    ...current,
                    current_governorate: composeResidenceLocation(value, ""),
                  }))
                }
                options={[
                  { value: "", label: "Select governorate" },
                  ...EGYPTIAN_GOVERNORATES.map((governorate) => ({
                    value: governorate,
                    label: governorate,
                  })),
                ]}
              />
            </div>

            {patientResidence.governorate === "Alexandria" ? (
              <div className="field">
                <label htmlFor="patient-current-area">Area</label>
                <CustomSelect
                  id="patient-current-area"
                  value={patientResidence.area}
                  onChange={(value) =>
                    setPatientForm((current) => ({
                      ...current,
                      current_governorate: composeResidenceLocation(
                        "Alexandria",
                        value,
                      ),
                    }))
                  }
                  options={[
                    { value: "", label: "Select area" },
                    ...ALEXANDRIA_AREAS.map((area) => ({
                      value: area,
                      label: area,
                    })),
                  ]}
                />
              </div>
            ) : null}

            <div className="field field--full">
              <label htmlFor="patient-conditions">{t("medicalHistory")}</label>
              <input
                id="patient-conditions"
                value={chronicConditionsInput}
                onChange={(event) => setChronicConditionsInput(event.target.value)}
                placeholder="hypertension, asthma, diabetes"
              />
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={patientForm.smoker}
                onChange={(event) =>
                  setPatientForm((current) => ({
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
                checked={patientForm.alcoholic}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    alcoholic: event.target.checked,
                  }))
                }
              />
              Alcohol use
            </label>

            {nationalIdInvalid ? (
              <div className="notice notice--error field--full">
                Enter a valid 14-digit Egyptian national ID to derive date of birth and
                governorate.
              </div>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={
                savingPatient ||
                nationalIdInvalid ||
                !patientForm.full_name.trim() ||
                !patientForm.sex.trim()
              }
            >
              {savingPatient ? "Saving..." : "Save patient profile"}
            </button>
          </form>
        </SectionPanel>
      ) : null}

      {role === "patient" && patientProfile ? (
        <SectionPanel
          eyebrow={t("medicalHistory")}
          title={t("medicalHistory")}
          description="Add structured details that should inform future triage, such as diagnosed conditions, injuries, surgeries, allergies, medications, hospitalizations, and family history."
        >
          <form className="form-grid" onSubmit={submitMedicalHistoryEntry}>
            <div className="field field--full">
              <label htmlFor="history-report-upload">
                Doctor report photo or PDF
              </label>
              <input
                id="history-report-upload"
                type="file"
                accept="application/pdf,image/png,image/jpeg,image/webp,.pdf,.png,.jpg,.jpeg,.webp"
                onChange={handleMedicalHistoryReportUpload}
                disabled={historyReportLoading}
              />
              <small className="field__hint">
                {historyReportLoading
                  ? "Reading report..."
                  : "Upload a text PDF, or an image if OCR is available, to draft the fields below."}
              </small>
            </div>

            <div className="field">
              <label htmlFor="history-category">{t("status")}</label>
              <CustomSelect
                id="history-category"
                value={historyCategory}
                onChange={(value) => setHistoryCategory(value)}
                options={[
                  { value: "diagnosed_condition", label: "Diagnosed condition" },
                  { value: "injury", label: "Injury" },
                  { value: "surgery", label: "Surgery" },
                  { value: "allergy", label: "Allergy" },
                  { value: "medication", label: "Current medication" },
                  { value: "hospitalization", label: "Past hospitalization" },
                  { value: "family_history", label: "Family history" },
                  { value: "note", label: "Important note" },
                ]}
              />
            </div>

            <div className="field">
              <label htmlFor="history-title">{t("profileTitle")}</label>
              <input
                id="history-title"
                value={historyTitle}
                onChange={(event) => setHistoryTitle(event.target.value)}
                placeholder="Asthma, knee injury, penicillin allergy..."
              />
            </div>

            <div className="field field--full">
              <label htmlFor="history-notes">{t("notes")}</label>
              <textarea
                id="history-notes"
                rows={3}
                value={historyNotes}
                onChange={(event) => setHistoryNotes(event.target.value)}
                placeholder="Add timing, severity, treatment, or relevant context."
              />
            </div>

            {historyMessage ? (
              <div className="notice field--full">{historyMessage}</div>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={
                historySaving || historyReportLoading || !historyTitle.trim()
              }
            >
              {historySaving ? "Saving..." : "Add history entry"}
            </button>
          </form>

          <div className="activity-list compact medical-history-list">
            {historyEntries.length === 0 ? (
              <div className="empty-state">
                No structured history entries yet. Add surgeries, allergies,
                medications, injuries, or important notes so future triage has better
                context.
              </div>
            ) : (
              historyEntries.map((entry) => (
                <article key={entry.id} className="activity-item">
                  <div>
                    <strong>{entry.title}</strong>
                    <p>
                      {entry.category.replace(/_/g, " ")} ·{" "}
                      {entry.status || "status not recorded"}
                    </p>
                    <p>{entry.notes || "No notes recorded"}</p>
                  </div>
                  <div className="activity-meta">
                    <small>{formatDateTime(entry.created_at)}</small>
                  </div>
                </article>
              ))
            )}
          </div>
        </SectionPanel>
      ) : null}

      {role === "doctor" ? (
        <SectionPanel
          eyebrow={t("doctorProfiles")}
          title={t("profileTitle")}
          description="Choose a primary field from the controlled medical specialty list, then optionally add a more specific scope."
        >
          <form className="form-grid" onSubmit={submitDoctorProfile}>
            <div className="field">
              <label htmlFor="doctor-full-name">{t("fullName")}</label>
              <input
                id="doctor-full-name"
                value={doctorForm.full_name}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-primary-specialty">{t("primarySpecialty")}</label>
              <CustomSelect
                id="doctor-primary-specialty"
                value={doctorPrimarySpecialty}
                onChange={(value) => {
                  setDoctorPrimarySpecialty(value);
                  setDoctorSpecialtyScope("");
                  setDoctorForm((current) => ({
                    ...current,
                    specialty: value,
                  }));
                }}
                options={[
                  { value: "", label: t("selectSpecialty") },
                  ...MEDICAL_SPECIALTY_GROUPS.map((option) => ({
                    value: option.label,
                    label: option.label,
                  })),
                ]}
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-specialty-scope">
                Specific scope (optional)
              </label>
              <CustomSelect
                id="doctor-specialty-scope"
                value={doctorSpecialtyScope}
                onChange={(value) => {
                  setDoctorSpecialtyScope(value);
                  setDoctorForm((current) => ({
                    ...current,
                    specialty: composeDoctorSpecialty(
                      doctorPrimarySpecialty,
                      value,
                    ),
                  }));
                }}
                options={[
                  { value: "", label: "No specific scope" },
                  ...specialtyOptions.map((scope) => ({
                    value: scope,
                    label: scope,
                  })),
                ]}
                placeholder="Optional narrower scope"
                disabled={!doctorPrimarySpecialty}
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-city">{t("governoratePending")}</label>
              <CustomSelect
                id="doctor-city"
                value={doctorForm.city ?? ""}
                onChange={(value) =>
                  setDoctorForm((current) => ({
                    ...current,
                    city: value,
                    area: value === "Alexandria" ? current.area : "",
                  }))
                }
                options={[
                  { value: "", label: "Select governorate" },
                  ...EGYPTIAN_GOVERNORATES.map((governorate) => ({
                    value: governorate,
                    label: governorate,
                  })),
                ]}
              />
            </div>

            {doctorForm.city === "Alexandria" ? (
              <div className="field">
                <label htmlFor="doctor-area">Area</label>
                <CustomSelect
                  id="doctor-area"
                  value={doctorForm.area ?? ""}
                  onChange={(value) =>
                    setDoctorForm((current) => ({
                      ...current,
                      area: value,
                    }))
                  }
                  options={[
                    { value: "", label: "Select area" },
                    ...ALEXANDRIA_AREAS.map((area) => ({
                      value: area,
                      label: area,
                    })),
                  ]}
                />
              </div>
            ) : null}

            <div className="field field--full">
              <label htmlFor="doctor-clinic">Clinic / hospital</label>
              <input
                id="doctor-clinic"
                value={doctorForm.clinic}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    clinic: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-consultation-fee">Consultation fee</label>
              <input
                id="doctor-consultation-fee"
                type="number"
                min="0"
                value={doctorForm.consultation_fee ?? ""}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    consultation_fee: event.target.value
                      ? Number(event.target.value)
                      : null,
                  }))
                }
                placeholder="EGP"
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-payment-methods">Payment methods</label>
              <input
                id="doctor-payment-methods"
                value={doctorForm.payment_methods.join(", ")}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    payment_methods: splitCommaList(event.target.value),
                  }))
                }
                placeholder="Cash, Card, Insurance"
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-insurance">Accepted insurance</label>
              <input
                id="doctor-insurance"
                value={doctorForm.insurance_providers.join(", ")}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    insurance_providers: splitCommaList(event.target.value),
                  }))
                }
                placeholder="Bupa, Allianz,..."
              />
            </div>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={doctorForm.offers_telemedicine}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    offers_telemedicine: event.target.checked,
                  }))
                }
              />
              <span>Offer video consultations</span>
            </label>

            <div className="callout field--full">
              <p className="micro-label">{t("connected")}</p>
              <p>
                {composeDoctorSpecialty(doctorPrimarySpecialty, doctorSpecialtyScope) ||
                  "Select a primary specialty first"}
              </p>
            </div>

            <button
              type="submit"
              className="button button--primary"
              disabled={
                savingDoctor ||
                !doctorForm.full_name.trim() ||
                !doctorPrimarySpecialty.trim() ||
                !doctorForm.clinic.trim()
              }
            >
              {savingDoctor ? "Saving..." : "Save doctor profile"}
            </button>
          </form>
        </SectionPanel>
      ) : null}

      {role === "doctor" && doctorProfile ? (
        <SectionPanel
          eyebrow={t("doctorSchedules")}
          title={t("scheduleManagement")}
          description="Add your clinic availability so patients can book real confirmed appointment slots."
        >
          <div className="schedule-management-panel">
            <div className="workspace-card__header">
              <div>
                <p className="micro-label">{t("availableSlots")}</p>
                <h3>{doctorProfile.clinic}</h3>
              </div>
              <span className="badge">
                {ownDoctorSlots.length} {t("availableSlots")}
              </span>
            </div>

            {ownScheduleMessage ? (
              <div className="notice">{ownScheduleMessage}</div>
            ) : null}

            <form className="form-grid" onSubmit={submitOwnDoctorSchedule}>
              <div className="field">
                <label htmlFor="own-schedule-specific-date">
                  {t("specificDate")}
                </label>
                <input
                  id="own-schedule-specific-date"
                  type="date"
                  min={todayDateInputValue()}
                  value={
                    ownScheduleForm.valid_from === ownScheduleForm.valid_to
                      ? (ownScheduleForm.valid_from ?? "")
                      : ""
                  }
                  onChange={(event) => {
                    const value = event.target.value;
                    setOwnScheduleForm((current) => ({
                      ...current,
                      day_of_week: value
                        ? weekdayFromDateInput(value)
                        : current.day_of_week,
                      valid_from: value || null,
                      valid_to: value || null,
                    }));
                  }}
                />
                <small className="field__hint">{t("specificDateHint")}</small>
              </div>
              <div className="field">
                <label htmlFor="own-schedule-day">{t("dayOfWeek")}</label>
                <CustomSelect
                  id="own-schedule-day"
                  value={ownScheduleForm.day_of_week}
                  onChange={(value) =>
                    setOwnScheduleForm((current) => ({
                      ...current,
                      day_of_week: value,
                    }))
                  }
                  disabled={Boolean(ownScheduleForm.valid_from)}
                  options={WEEKDAY_OPTIONS.map((day) => ({
                    value: day,
                    label: day,
                  }))}
                />
              </div>

              <div className="field">
                <label htmlFor="own-schedule-start">{t("startTime")}</label>
                <input
                  id="own-schedule-start"
                  type="time"
                  value={ownScheduleForm.start_time.slice(0, 5)}
                  onChange={(event) =>
                    setOwnScheduleForm((current) => ({
                      ...current,
                      start_time: `${event.target.value}:00`,
                    }))
                  }
                />
              </div>

              <div className="field">
                <label htmlFor="own-schedule-end">{t("endTime")}</label>
                <input
                  id="own-schedule-end"
                  type="time"
                  value={ownScheduleForm.end_time.slice(0, 5)}
                  onChange={(event) =>
                    setOwnScheduleForm((current) => ({
                      ...current,
                      end_time: `${event.target.value}:00`,
                    }))
                  }
                />
              </div>

              <div className="field">
                <label htmlFor="own-schedule-minutes">{t("slotMinutes")}</label>
                <input
                  id="own-schedule-minutes"
                  type="number"
                  min={5}
                  max={240}
                  value={ownScheduleForm.slot_minutes}
                  onChange={(event) =>
                    setOwnScheduleForm((current) => ({
                      ...current,
                      slot_minutes: Number(event.target.value),
                    }))
                  }
                />
              </div>

              <div className="field">
                <label htmlFor="own-schedule-location">{t("clinicReview")}</label>
                <input
                  id="own-schedule-location"
                  value={ownScheduleForm.location_label ?? ""}
                  onChange={(event) =>
                    setOwnScheduleForm((current) => ({
                      ...current,
                      location_label: event.target.value,
                    }))
                  }
                />
              </div>

              <button
                type="submit"
                className="button button--primary"
                disabled={ownScheduleLoading}
              >
                {ownScheduleLoading ? t("working") : t("addSchedule")}
              </button>
            </form>

            <div className="activity-list compact">
              {ownDoctorSchedules.length === 0 ? (
                <div className="empty-state">{t("noSchedulesRecorded")}</div>
              ) : (
                ownDoctorSchedules.map((schedule) => (
                  <article key={schedule.id} className="activity-item">
                    <div>
                      <strong>
                        {schedule.day_of_week} ·{" "}
                        {schedule.start_time.slice(0, 5)}-
                        {schedule.end_time.slice(0, 5)}
                      </strong>
                      <p title={describeScheduleRule(schedule)}>
                        {schedule.slot_minutes} {t("minutes")} ·{" "}
                        {schedule.location_label || doctorProfile.clinic}
                      </p>
                    </div>
                    <div className="activity-meta">
                      <span
                        className={`badge ${
                          schedule.is_active
                            ? "badge--status-approved"
                            : "badge--status-rejected"
                        }`}
                      >
                        {schedule.is_active ? t("active") : t("inactive")}
                      </span>
                      <button
                        type="button"
                        className="button button--ghost button--small"
                        disabled={ownScheduleLoading}
                        onClick={() =>
                          toggleOwnSchedule(schedule, !schedule.is_active)
                        }
                      >
                        {schedule.is_active ? t("deactivate") : t("activate")}
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>

            <div className="activity-list compact">
              <p className="micro-label">{t("availableSlots")}</p>
              {ownDoctorSlots.length === 0 ? (
                <div className="empty-state">{t("noSlotsAvailable")}</div>
              ) : (
                ownDoctorSlots.slice(0, 8).map((slot) => (
                  <article key={slot.id} className="activity-item">
                    <div>
                      <strong>{formatDateTime(slot.start_at)}</strong>
                      <p>
                        {slot.clinic?.name || doctorProfile.clinic} ·{" "}
                        {slot.clinic?.area || doctorProfile.area}
                      </p>
                    </div>
                    <div className="activity-meta">
                      <span className="badge">
                        {localizeSlotStatus(slot.status, t)}
                      </span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </SectionPanel>
      ) : null}
    </div>
  );
}

