import { useMemo, useState } from "react";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
  RoleType,
  VisitResponseDto,
} from "../api/dto";
import { createPatientMedicalHistoryEntry } from "../api/patients";
import { parseEgyptianNationalId } from "../lib/egyptianNationalId";
import {
  composeDoctorSpecialty,
  MEDICAL_SPECIALTY_GROUPS,
  splitDoctorSpecialty,
} from "../lib/medicalSpecialties";
import type { DashboardTab } from "./DashboardNav";
import SectionPanel from "./SectionPanel";

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

  const patientAppointments = selectedPatient
    ? appointments.filter((a) => a.patient_id === selectedPatient.id)
    : [];
  const patientVisits = selectedPatient
    ? recentVisits.filter((v) => v.patient_id === selectedPatient.id)
    : [];
  const doctorAppointments = selectedDoctor
    ? appointments.filter((a) => a.doctor_id === selectedDoctor.id)
    : [];

  return (
    <div className="stack-lg">
      <SectionPanel
        eyebrow="Admin records"
        title="Operational records center"
        description="Review all patient profiles, doctor profiles, appointments, and recent medical history without patient-facing demographic forms."
      >
        <div className="admin-metric-grid">
          <article className="metric-card">
            <span>Patients on record</span>
            <strong>{patients.length}</strong>
          </article>
          <article className="metric-card">
            <span>Doctors on record</span>
            <strong>{doctors.length}</strong>
          </article>
          <article className="metric-card">
            <span>Future appointments</span>
            <strong>{futureAppointments.length}</strong>
          </article>
          <article className="metric-card">
            <span>Completed appointments</span>
            <strong>{completedAppointments.length}</strong>
          </article>
          <article className="metric-card">
            <span>Recent visits</span>
            <strong>{recentVisits.length}</strong>
          </article>
          <article className="metric-card">
            <span>Pending approvals</span>
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
            <strong>Review appointments</strong>
            <span>Open future and previous bookings in one scheduling workspace.</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("visits")}
          >
            <strong>Open medical history</strong>
            <span>Inspect recent visits and add clinician records when needed.</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("profile")}
          >
            <strong>Review profiles</strong>
            <span>Filter patient and doctor records from one compact admin view.</span>
          </button>
          <button
            type="button"
            className="action-shortcut action-shortcut--ghost"
            onClick={() => onNavigate("records")}
          >
            <strong>Manage record imports</strong>
            <span>Import structured medical records into the visit history.</span>
          </button>
        </div>
      </SectionPanel>

      <SectionPanel
        eyebrow="Management"
        title="Profiles and records"
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
              <label htmlFor="patient-search">Search by national ID</label>
              <input
                id="patient-search"
                value={patientSearch}
                onChange={(event) => setPatientSearch(event.target.value)}
                placeholder="Enter patient national ID"
              />
            </div>

            {selectedPatient ? (
              <section className="workspace-card workspace-card--compact">
                <div className="workspace-card__header">
                  <div>
                    <p className="micro-label">Patient details</p>
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
                    <strong>Full name</strong>
                    <span>{selectedPatient.full_name}</span>
                  </div>
                  <div>
                    <strong>Age</strong>
                    <span>{selectedPatient.age}</span>
                  </div>
                  <div>
                    <strong>Sex</strong>
                    <span>{selectedPatient.sex}</span>
                  </div>
                  <div>
                    <strong>National ID</strong>
                    <span>{selectedPatient.national_id || "Not recorded"}</span>
                  </div>
                  <div>
                    <strong>Governorate</strong>
                    <span>
                      {selectedPatient.current_governorate ||
                        selectedPatient.inferred_governorate ||
                        "Pending"}
                    </span>
                  </div>
                  <div>
                    <strong>Chronic conditions</strong>
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
                        patientAppointments.map((appointment) => (
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
                                {appointment.status}
                              </span>
                              <small>{formatDateTime(appointment.scheduled_for || appointment.requested_at)}</small>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                  </div>

                  <div>
                    <p className="micro-label">Visits ({patientVisits.length})</p>
                    <div className="activity-list">
                      {patientVisits.length === 0 ? (
                        <div className="empty-state">No visits recorded.</div>
                      ) : (
                        patientVisits.map((visit) => (
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
                  <div className="activity-list">
                    {filteredPatients.map((patient) => (
                      <button
                        key={patient.id}
                        type="button"
                        className="activity-item"
                        onClick={() => setSelectedPatientId(patient.id)}
                      >
                        <div>
                          <strong>{patient.full_name}</strong>
                          <p>
                            {patient.national_id
                              ? `National ID: ${patient.national_id}`
                              : "No national ID"}
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
                      </button>
                    ))}
                  </div>
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
                onChange={(event) => setDoctorSearch(event.target.value)}
                placeholder="Enter doctor name or specialty"
              />
            </div>

            {selectedDoctor ? (
              <section className="workspace-card workspace-card--compact">
                <div className="workspace-card__header">
                  <div>
                    <p className="micro-label">Doctor details</p>
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
                    <strong>Full name</strong>
                    <span>{selectedDoctor.full_name}</span>
                  </div>
                  <div>
                    <strong>Specialty</strong>
                    <span>{selectedDoctor.specialty}</span>
                  </div>
                  <div>
                    <strong>Clinic</strong>
                    <span>{selectedDoctor.clinic || "Not specified"}</span>
                  </div>
                  <div>
                    <strong>Area</strong>
                    <span>{selectedDoctor.area || "Not specified"}</span>
                  </div>
                  <div>
                    <strong>City</strong>
                    <span>{selectedDoctor.city || "Not specified"}</span>
                  </div>
                </div>

                <div className="stack-md">
                  <div>
                    <p className="micro-label">Appointments ({doctorAppointments.length})</p>
                    <div className="activity-list">
                      {doctorAppointments.length === 0 ? (
                        <div className="empty-state">No appointments recorded.</div>
                      ) : (
                        doctorAppointments.map((appointment) => (
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
                                {appointment.status}
                              </span>
                              <small>{formatDateTime(appointment.scheduled_for || appointment.requested_at)}</small>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
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
                  <div className="activity-list">
                    {filteredDoctors.map((doctor) => (
                      <button
                        key={doctor.id}
                        type="button"
                        className="activity-item"
                        onClick={() => setSelectedDoctorId(doctor.id)}
                      >
                        <div>
                          <strong>{doctor.full_name}</strong>
                          <p>{doctor.specialty}</p>
                          <p>
                            {[doctor.area, doctor.city].filter(Boolean).join(", ") ||
                              doctor.clinic}
                          </p>
                        </div>
                        <div className="activity-meta">
                          <small>{formatDateTime(doctor.updated_at)}</small>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </SectionPanel>

      {/* Keep a short operational summary below the management grid. */}
      <div className="activity-columns">
        <SectionPanel
          eyebrow="Patients"
          title="Profile updates"
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
          eyebrow="Doctors"
          title="Doctor updates"
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
        }
      : {
          full_name: "",
          specialty: "",
          clinic: "",
          area: "",
          city: "",
        },
  );
  const [chronicConditionsInput, setChronicConditionsInput] = useState(
    patientProfile?.chronic_conditions.join(", ") ?? "",
  );
  const [historyCategory, setHistoryCategory] = useState("diagnosed_condition");
  const [historyTitle, setHistoryTitle] = useState("");
  const [historyNotes, setHistoryNotes] = useState("");
  const [historySaving, setHistorySaving] = useState(false);
  const [historyMessage, setHistoryMessage] = useState<string | null>(null);

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
    });
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
      await createPatientMedicalHistoryEntry(patientProfile.id, {
        category: historyCategory,
        title: historyTitle.trim(),
        notes: historyNotes.trim() || null,
        status: "active",
      });
      setHistoryTitle("");
      setHistoryNotes("");
      setHistoryMessage("Medical history entry saved.");
    } catch {
      setHistoryMessage("Could not save medical history entry.");
    } finally {
      setHistorySaving(false);
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
  const nationalIdHasValue = Boolean(patientForm.national_id?.trim());
  const nationalIdInvalid = nationalIdHasValue && !parsedNationalId;

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
          eyebrow="Patient profile"
          title="Demographics and identity"
          description="This profile powers patient-aware triage, appointments, and visit history. The national ID can derive date of birth and the governorate encoded inside the ID, while current residence stays editable."
        >
          <form className="form-grid" onSubmit={submitPatientProfile}>
            <div className="field">
              <label htmlFor="patient-full-name">Full name</label>
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
              <select
                id="patient-sex"
                value={patientForm.sex}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    sex: event.target.value as PatientProfileFormState["sex"],
                  }))
                }
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="patient-national-id">Egyptian national ID</label>
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
              <input
                id="patient-current-governorate"
                value={patientForm.current_governorate ?? ""}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    current_governorate: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field field--full">
              <label htmlFor="patient-conditions">Chronic conditions</label>
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
          eyebrow="Medical history"
          title="Important history entries"
          description="Add structured details that should inform future triage, such as diagnosed conditions, injuries, surgeries, allergies, medications, hospitalizations, and family history."
        >
          <form className="form-grid" onSubmit={submitMedicalHistoryEntry}>
            <div className="field">
              <label htmlFor="history-category">Category</label>
              <select
                id="history-category"
                value={historyCategory}
                onChange={(event) => setHistoryCategory(event.target.value)}
              >
                <option value="diagnosed_condition">Diagnosed condition</option>
                <option value="injury">Injury</option>
                <option value="surgery">Surgery</option>
                <option value="allergy">Allergy</option>
                <option value="medication">Current medication</option>
                <option value="hospitalization">Past hospitalization</option>
                <option value="family_history">Family history</option>
                <option value="note">Important note</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="history-title">Title</label>
              <input
                id="history-title"
                value={historyTitle}
                onChange={(event) => setHistoryTitle(event.target.value)}
                placeholder="Asthma, knee injury, penicillin allergy..."
              />
            </div>

            <div className="field field--full">
              <label htmlFor="history-notes">Notes</label>
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
              disabled={historySaving || !historyTitle.trim()}
            >
              {historySaving ? "Saving..." : "Add history entry"}
            </button>
          </form>
        </SectionPanel>
      ) : null}

      {role === "doctor" ? (
        <SectionPanel
          eyebrow="Doctor profile"
          title="Clinical identity"
          description="Choose a primary field from the controlled medical specialty list, then optionally add a more specific scope."
        >
          <form className="form-grid" onSubmit={submitDoctorProfile}>
            <div className="field">
              <label htmlFor="doctor-full-name">Full name</label>
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
              <label htmlFor="doctor-primary-specialty">Primary specialty</label>
              <select
                id="doctor-primary-specialty"
                value={doctorPrimarySpecialty}
                onChange={(event) => {
                  const nextPrimary = event.target.value;
                  setDoctorPrimarySpecialty(nextPrimary);
                  setDoctorSpecialtyScope("");
                  setDoctorForm((current) => ({
                    ...current,
                    specialty: nextPrimary,
                  }));
                }}
              >
                <option value="">Select specialty</option>
                {MEDICAL_SPECIALTY_GROUPS.map((option) => (
                  <option key={option.label} value={option.label}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="doctor-specialty-scope">
                Specific scope (optional)
              </label>
              <input
                id="doctor-specialty-scope"
                list="doctor-specialty-scope-options"
                value={doctorSpecialtyScope}
                onChange={(event) => setDoctorSpecialtyScope(event.target.value)}
                placeholder="Optional narrower scope"
                disabled={!doctorPrimarySpecialty}
              />
              <datalist id="doctor-specialty-scope-options">
                {specialtyOptions.map((scope) => (
                  <option key={scope} value={scope} />
                ))}
              </datalist>
            </div>

            <div className="field">
              <label htmlFor="doctor-city">City</label>
              <input
                id="doctor-city"
                value={doctorForm.city ?? ""}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    city: event.target.value,
                  }))
                }
                placeholder="Alexandria"
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-area">Area</label>
              <input
                id="doctor-area"
                value={doctorForm.area ?? ""}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    area: event.target.value,
                  }))
                }
                placeholder="Smouha"
              />
            </div>

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

            <div className="callout field--full">
              <p className="micro-label">Saved display</p>
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
    </div>
  );
}
