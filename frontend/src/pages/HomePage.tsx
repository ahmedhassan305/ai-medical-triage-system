import axios from "axios";
import { startTransition, useCallback, useEffect, useState } from "react";

import {
  createAppointment,
  listAppointments,
  updateAppointmentStatus,
} from "../api/appointments";
import { fetchCurrentUser, loginUser, registerUser } from "../api/auth";
import {
  fetchMyDoctorProfile,
  listDoctors,
  upsertMyDoctorProfile,
} from "../api/doctors";
import { getErrorMessage } from "../api/errors";
import {
  createManagedPatientProfile,
  fetchMyPatientProfile,
  findPatientByNationalId,
  listPatients,
  upsertMyPatientProfile,
} from "../api/patients";
import { importRecords } from "../api/records";
import { extractLabPdf, triage, type TriageResponse } from "../api/triage";
import { createVisit, listPatientVisits, listWorkspaceVisits } from "../api/visits";
import type {
  AppointmentResponseDto,
  DoctorSuggestionDto,
  DoctorProfileResponseDto,
  LabValueDto,
  ManagedPatientProfileCreateDto,
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
  RegisterRequestDto,
  RoleType,
  TokenResponseDto,
  UserResponseDto,
  VisitResponseDto,
} from "../api/dto";
import AppointmentsPanel from "../components/AppointmentsPanel";
import AuthPanel from "../components/AuthPanel";
import DashboardNav, { type DashboardTab } from "../components/DashboardNav";
import OverviewPanel from "../components/OverviewPanel";
import ProfilePanel from "../components/ProfilePanel";
import RecordsImportPanel from "../components/RecordsImportPanel";
import TriagePanel from "../components/TriagePanel";
import VisitsPanel from "../components/VisitsPanel";
import {
  buildAppointmentPrefill,
  type AppointmentPrefill,
} from "../lib/appointmentPrefill";
import { clearSession, readSession, writeSession } from "../lib/session";

function isStatus(error: unknown, statusCode: number): boolean {
  return axios.isAxiosError(error) && error.response?.status === statusCode;
}

export default function HomePage() {
  const [session, setSession] = useState<TokenResponseDto | null>(() => readSession());
  const [user, setUser] = useState<UserResponseDto | null>(null);
  const [patientProfile, setPatientProfile] =
    useState<PatientProfileResponseDto | null>(null);
  const [doctorProfile, setDoctorProfile] =
    useState<DoctorProfileResponseDto | null>(null);
  const [patients, setPatients] = useState<PatientProfileResponseDto[]>([]);
  const [doctors, setDoctors] = useState<DoctorProfileResponseDto[]>([]);
  const [appointments, setAppointments] = useState<AppointmentResponseDto[]>([]);
  const [visits, setVisits] = useState<VisitResponseDto[]>([]);
  const [workspaceVisits, setWorkspaceVisits] = useState<VisitResponseDto[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);
  const [selectedTab, setSelectedTab] = useState<DashboardTab>("overview");

  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [patientSaving, setPatientSaving] = useState(false);
  const [doctorSaving, setDoctorSaving] = useState(false);
  const [appointmentsLoading, setAppointmentsLoading] = useState(false);
  const [visitsLoading, setVisitsLoading] = useState(false);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [triageLoading, setTriageLoading] = useState(false);

  const [pageError, setPageError] = useState<string | null>(null);
  const [triageError, setTriageError] = useState<string | null>(null);
  const [appointmentsError, setAppointmentsError] = useState<string | null>(null);
  const [visitsError, setVisitsError] = useState<string | null>(null);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [recordsSuccess, setRecordsSuccess] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const [triageQuery, setTriageQuery] = useState("");
  const [triageResult, setTriageResult] = useState<TriageResponse | null>(null);
  const [triageLabValues, setTriageLabValues] = useState<LabValueDto[]>([]);
  const [triageLabLoading, setTriageLabLoading] = useState(false);
  const [triageLabError, setTriageLabError] = useState<string | null>(null);
  const [appointmentPrefill, setAppointmentPrefill] =
    useState<AppointmentPrefill | null>(null);
  const [triagePatientNationalId, setTriagePatientNationalId] = useState("");
  const [triageLinkedPatient, setTriageLinkedPatient] =
    useState<PatientProfileResponseDto | null>(null);
  const [triageLinkedPatientLatestVisit, setTriageLinkedPatientLatestVisit] =
    useState<VisitResponseDto | null>(null);
  const [triagePatientLookupLoading, setTriagePatientLookupLoading] =
    useState(false);
  const [triagePatientLookupError, setTriagePatientLookupError] =
    useState<string | null>(null);
  const [triagePatientCreateLoading, setTriagePatientCreateLoading] =
    useState(false);
  const [triagePatientCreateError, setTriagePatientCreateError] =
    useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      return;
    }

    if (user.role === "patient" && selectedTab === "records") {
      setSelectedTab("overview");
    }
  }, [selectedTab, user]);

  useEffect(() => {
    if (!user || user.role === "patient") {
      return;
    }
    if (!selectedPatientId) {
      setTriageLinkedPatient(null);
      setTriageLinkedPatientLatestVisit(null);
      return;
    }
    const matchedPatient =
      patients.find((patient) => patient.id === selectedPatientId) ?? null;
    setTriageLinkedPatient(matchedPatient);
  }, [patients, selectedPatientId, user]);

  function resetWorkspace() {
    clearSession();
    setSession(null);
    setUser(null);
    setPatientProfile(null);
    setDoctorProfile(null);
    setPatients([]);
    setDoctors([]);
    setAppointments([]);
    setVisits([]);
    setWorkspaceVisits([]);
    setSelectedPatientId(null);
    setTriageResult(null);
    setTriageQuery("");
    setAppointmentPrefill(null);
    setTriagePatientNationalId("");
    setTriageLinkedPatient(null);
    setTriageLinkedPatientLatestVisit(null);
    setTriagePatientLookupError(null);
    setTriagePatientCreateError(null);
    setPageError(null);
    setRecordsSuccess(null);
  }

  const refreshWorkspace = useCallback(
    async (
      activeSession: TokenResponseDto,
      currentSelection: number | null,
      forcedPatientId?: number | null,
    ): Promise<boolean> => {
      try {
        const currentUser = await fetchCurrentUser();
        const patientProfileRequest =
          currentUser.role === "patient" || currentUser.role === "admin"
            ? fetchMyPatientProfile().catch((error) =>
                isStatus(error, 404) ? null : Promise.reject(error),
              )
            : Promise.resolve(null);
        const doctorProfileRequest =
          currentUser.role === "doctor" || currentUser.role === "admin"
            ? fetchMyDoctorProfile().catch((error) =>
                isStatus(error, 404) ? null : Promise.reject(error),
              )
            : Promise.resolve(null);
        const [
          nextPatientProfile,
          nextDoctorProfile,
          nextDoctors,
          nextPatients,
          nextAppointments,
          nextWorkspaceVisits,
        ] = await Promise.all([
          patientProfileRequest,
          doctorProfileRequest,
          listDoctors().catch(() => []),
          currentUser.role === "patient"
            ? Promise.resolve([])
            : listPatients().catch(() => []),
          listAppointments().catch(() => []),
          currentUser.role === "doctor" || currentUser.role === "admin"
            ? listWorkspaceVisits().catch(() => [])
            : Promise.resolve([]),
        ]);

        let nextSelectedPatientId = forcedPatientId ?? currentSelection;
        if (currentUser.role === "patient") {
          nextSelectedPatientId = nextPatientProfile?.id ?? null;
        } else if (
          nextSelectedPatientId === null ||
          !nextPatients.some((patient) => patient.id === nextSelectedPatientId)
        ) {
          nextSelectedPatientId = nextPatients[0]?.id ?? null;
        }

        let nextVisits: VisitResponseDto[] = [];
        if (nextSelectedPatientId) {
          nextVisits = await listPatientVisits(nextSelectedPatientId).catch(() => []);
        }

        setUser(currentUser);
        setPatientProfile(nextPatientProfile);
        setDoctorProfile(nextDoctorProfile);
        setDoctors(nextDoctors);
        setPatients(nextPatients);
        setAppointments(nextAppointments);
        setWorkspaceVisits(nextWorkspaceVisits);
        setSelectedPatientId(nextSelectedPatientId);
        setVisits(nextVisits);
        setPageError(null);

        if (
          activeSession.user_id !== currentUser.id ||
          activeSession.role !== currentUser.role
        ) {
          const syncedSession = {
            ...activeSession,
            user_id: currentUser.id,
            role: currentUser.role,
          };
          writeSession(syncedSession);
          setSession(syncedSession);
        }

        return true;
      } catch (error) {
        if (isStatus(error, 401)) {
          setAuthError("Your session expired. Please sign in again.");
          return false;
        }

        setPageError(
          getErrorMessage(error, "Failed to load the workspace from the backend."),
        );
        return true;
      }
    },
    [],
  );

  useEffect(() => {
    if (!session) {
      return;
    }

    const activeSession = session;
    let cancelled = false;

    async function hydrate() {
      setDashboardLoading(true);
      const ok = await refreshWorkspace(activeSession, null);
      if (!cancelled) {
        setDashboardLoading(false);
        if (!ok) {
          resetWorkspace();
        }
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, [refreshWorkspace, session]);

  async function refreshVisits(patientId: number | null): Promise<VisitResponseDto[]> {
    setSelectedPatientId(patientId);
    if (!patientId) {
      setVisits([]);
      setTriageLinkedPatientLatestVisit(null);
      return [];
    }

    setVisitsLoading(true);
    setVisitsError(null);
    try {
      const response = await listPatientVisits(patientId);
      setVisits(response);
      setTriageLinkedPatientLatestVisit(response[0] ?? null);
      return response;
    } catch (error) {
      setVisitsError(getErrorMessage(error, "Failed to load visits."));
      setTriageLinkedPatientLatestVisit(null);
      return [];
    } finally {
      setVisitsLoading(false);
    }
  }

  async function handleLogin(payload: { email: string; password: string }) {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const nextSession = await loginUser(payload);
      writeSession(nextSession);
      setSession(nextSession);
    } catch (error) {
      setAuthError(getErrorMessage(error, "Login failed."));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(payload: {
    email: string;
    password: string;
    role: RoleType;
    full_name?: string;
    national_id?: string;
    sex?: RegisterRequestDto["sex"];
  }) {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await registerUser(payload);
      const nextSession = await loginUser({
        email: payload.email,
        password: payload.password,
      });
      writeSession(nextSession);
      setSession(nextSession);
    } catch (error) {
      setAuthError(getErrorMessage(error, "Registration failed."));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSavePatientProfile(payload: {
    full_name: string;
    age: number;
    sex: PatientProfileUpsertDto["sex"];
    national_id?: string | null;
    current_governorate?: string | null;
    smoker: boolean;
    alcoholic: boolean;
    chronic_conditions: string[];
  }) {
    if (!session) {
      return;
    }

    setPatientSaving(true);
    setPageError(null);
    try {
      const profile = await upsertMyPatientProfile(payload);
      await refreshWorkspace(session, selectedPatientId, profile.id);
    } catch (error) {
      setPageError(getErrorMessage(error, "Failed to save patient profile."));
    } finally {
      setPatientSaving(false);
    }
  }

  async function handleSaveDoctorProfile(payload: {
    full_name: string;
    specialty: string;
    clinic: string;
    area?: string | null;
    city?: string | null;
  }) {
    if (!session) {
      return;
    }

    setDoctorSaving(true);
    setPageError(null);
    try {
      await upsertMyDoctorProfile(payload);
      await refreshWorkspace(session, selectedPatientId);
    } catch (error) {
      setPageError(getErrorMessage(error, "Failed to save doctor profile."));
    } finally {
      setDoctorSaving(false);
    }
  }

  async function handleRunTriage() {
    setTriageLoading(true);
    setTriageError(null);
    setTriageResult(null);
    try {
      const result = await triage(
        triageQuery.trim(),
        selectedPatientId ?? undefined,
        triageLabValues,
      );
      setTriageResult(result);
    } catch (error) {
      setTriageError(getErrorMessage(error, "Failed to run triage."));
    } finally {
      setTriageLoading(false);
    }
  }

  async function handleLabFileChange(file: File | null) {
    setTriageLabError(null);
    setTriageLabValues([]);
    if (!file) {
      return;
    }
    setTriageLabLoading(true);
    try {
      const extracted = await extractLabPdf(file, selectedPatientId ?? undefined);
      setTriageLabValues(extracted.values);
    } catch (error) {
      setTriageLabError(getErrorMessage(error, "Failed to extract lab PDF."));
    } finally {
      setTriageLabLoading(false);
    }
  }

  function handleReserveAppointment(
    doctor: DoctorSuggestionDto,
    specialty: string,
    reason: string,
  ) {
    setAppointmentPrefill(buildAppointmentPrefill(doctor, reason, specialty));
    setSelectedTab("appointments");
  }

  async function handleLookupPatientByNationalId(nationalId: string) {
    const normalizedNationalId = nationalId.replace(/\D/g, "").slice(0, 14);
    setTriagePatientNationalId(normalizedNationalId);
    if (!normalizedNationalId) {
      setTriagePatientLookupError(null);
      setTriageLinkedPatient(null);
      await refreshVisits(null);
      return;
    }

    setTriagePatientLookupLoading(true);
    setTriagePatientLookupError(null);
    try {
      const patient = await findPatientByNationalId(normalizedNationalId);
      setTriageLinkedPatient(patient);
      await refreshVisits(patient.id);
    } catch (error) {
      setTriageLinkedPatient(null);
      await refreshVisits(null);
      setTriagePatientLookupError(
        getErrorMessage(error, "Failed to find patient by national ID."),
      );
    } finally {
      setTriagePatientLookupLoading(false);
    }
  }

  async function handleCreateManagedPatientProfile(
    payload: ManagedPatientProfileCreateDto,
  ) {
    if (!session) {
      return;
    }

    setTriagePatientCreateLoading(true);
    setTriagePatientCreateError(null);
    try {
      const profile = await createManagedPatientProfile(payload);
      await refreshWorkspace(session, profile.id, profile.id);
      setTriagePatientNationalId(profile.national_id ?? payload.national_id);
      setTriageLinkedPatient(profile);
      await refreshVisits(profile.id);
    } catch (error) {
      setTriagePatientCreateError(
        getErrorMessage(error, "Failed to create patient profile."),
      );
    } finally {
      setTriagePatientCreateLoading(false);
    }
  }

  function handleClearLinkedTriagePatient() {
    setTriagePatientLookupError(null);
    setTriagePatientNationalId("");
    setTriageLinkedPatient(null);
    void refreshVisits(null);
  }

  async function handleCreateAppointment(payload: {
    patient_id: number;
    doctor_id: number;
    reason: string;
    notes?: string;
    scheduled_for?: string | null;
  }) {
    setAppointmentsLoading(true);
    setAppointmentsError(null);
    try {
      await createAppointment(payload);
      const data = await listAppointments();
      setAppointments(data);
    } catch (error) {
      setAppointmentsError(getErrorMessage(error, "Failed to create appointment."));
    } finally {
      setAppointmentsLoading(false);
    }
  }

  async function handleUpdateAppointmentStatus(
    appointmentId: number,
    payload: { status: "approved" | "rejected"; notes?: string },
  ) {
    setAppointmentsLoading(true);
    setAppointmentsError(null);
    try {
      await updateAppointmentStatus(appointmentId, payload);
      const data = await listAppointments();
      setAppointments(data);
    } catch (error) {
      setAppointmentsError(
        getErrorMessage(error, "Failed to update appointment status."),
      );
    } finally {
      setAppointmentsLoading(false);
    }
  }

  async function handleCreateVisit(payload: {
    patient_id: number;
    doctor_id?: number | null;
    symptoms: string;
    diagnosis?: string;
    notes?: string;
    prescriptions?: string;
  }) {
    setVisitsLoading(true);
    setVisitsError(null);
    try {
      await createVisit(payload);
      const data = await listPatientVisits(payload.patient_id);
      setVisits(data);
      setSelectedPatientId(payload.patient_id);
      if (user?.role === "doctor" || user?.role === "admin") {
        const recentVisits = await listWorkspaceVisits().catch(() => workspaceVisits);
        setWorkspaceVisits(recentVisits);
      }
    } catch (error) {
      setVisitsError(getErrorMessage(error, "Failed to create visit."));
    } finally {
      setVisitsLoading(false);
    }
  }

  async function handleImportRecords(patientId: number, file: File) {
    setRecordsLoading(true);
    setRecordsError(null);
    setRecordsSuccess(null);
    try {
      const result = await importRecords(patientId, file);
      setRecordsSuccess(
        `Imported ${result.imported} record(s) for patient #${result.patient_id}.`,
      );
      await refreshVisits(patientId);
    } catch (error) {
      setRecordsError(getErrorMessage(error, "Failed to import records."));
    } finally {
      setRecordsLoading(false);
    }
  }

  function handleLogout() {
    resetWorkspace();
  }

  function handleSelectTab(tab: DashboardTab) {
    startTransition(() => setSelectedTab(tab));
  }

  if (!session || !user) {
    return (
      <div className="page-shell">
        <AuthPanel
          loading={authLoading || dashboardLoading}
          error={authError}
          onLogin={handleLogin}
          onRegister={handleRegister}
        />
      </div>
    );
  }

  const currentUser: UserResponseDto = user;

  const currentPatientId =
    currentUser.role === "patient" ? patientProfile?.id ?? null : selectedPatientId;

  const tabMeta: Record<
    DashboardTab,
    { title: string; description: string }
  > = {
    overview: {
      title: "Workspace overview",
      description:
        currentUser.role === "admin"
          ? "Operational visibility across appointments, specialty coverage, and activity."
          : currentUser.role === "doctor"
            ? "A live clinician workspace for schedule review, visits, and patient workload."
            : "A personal care workspace for your next appointment, triage guidance, and visit history.",
    },
    profile: {
      title: "Profile",
      description:
        currentUser.role === "admin"
          ? "Review patients, doctors, appointments, and recent medical history from one operations workspace."
          : "Keep role details accurate so triage, scheduling, and history stay aligned.",
    },
    triage: {
      title: "Triage",
      description: "Describe symptoms to get urgency guidance, likely conditions, and doctor suggestions.",
    },
    appointments: {
      title: "Appointments",
      description: "Coordinate requests, approvals, and confirmed visits without leaving the workspace.",
    },
    visits: {
      title: "Visits",
      description: "Review clinical notes or create new visit records from the care workflow.",
    },
    records: {
      title: "Records",
      description: "Import external records into the structured visit history.",
    },
  };

  function renderPanel() {
    switch (selectedTab) {
      case "overview":
        return (
          <OverviewPanel
            role={currentUser.role}
            key={`overview-${currentUser.role}`}
            patientProfile={patientProfile}
            doctorProfile={doctorProfile}
            appointments={appointments}
            patients={patients}
            visits={visits}
            recentVisits={workspaceVisits}
            doctors={doctors}
            triageResult={triageResult}
            onNavigate={handleSelectTab}
          />
        );
      case "profile":
        return (
          <ProfilePanel
            role={currentUser.role}
            key={`profile-${patientProfile?.updated_at ?? "np"}-${doctorProfile?.updated_at ?? "nd"}`}
            patientProfile={patientProfile}
            doctorProfile={doctorProfile}
            savingPatient={patientSaving}
            savingDoctor={doctorSaving}
            patients={patients}
            doctors={doctors}
            appointments={appointments}
            recentVisits={workspaceVisits}
            onNavigate={handleSelectTab}
            onSavePatient={handleSavePatientProfile}
            onSaveDoctor={handleSaveDoctorProfile}
          />
        );
      case "triage":
        return (
          <TriagePanel
            key={`triage-${currentPatientId ?? "none"}`}
            role={currentUser.role}
            loading={triageLoading}
            error={triageError}
            result={triageResult}
            patientProfile={patientProfile}
            linkedPatient={currentUser.role === "patient" ? patientProfile : triageLinkedPatient}
            linkedPatientLatestVisit={triageLinkedPatientLatestVisit}
            patientLookupNationalId={triagePatientNationalId}
            patientLookupLoading={triagePatientLookupLoading}
            patientLookupError={triagePatientLookupError}
            patientCreateLoading={triagePatientCreateLoading}
            patientCreateError={triagePatientCreateError}
            query={triageQuery}
            labValues={triageLabValues}
            labLoading={triageLabLoading}
            labError={triageLabError}
            onQueryChange={setTriageQuery}
            onLabFileChange={handleLabFileChange}
            onLookupNationalIdChange={setTriagePatientNationalId}
            onLookupPatient={handleLookupPatientByNationalId}
            onClearLinkedPatient={handleClearLinkedTriagePatient}
            onCreatePatientProfile={handleCreateManagedPatientProfile}
            onSubmit={handleRunTriage}
            onClarificationComplete={setTriageResult}
            onReserveAppointment={
              currentUser.role === "doctor" ? undefined : handleReserveAppointment
            }
          />
        );
      case "appointments":
        return (
          <AppointmentsPanel
            key={`appointments-${currentPatientId ?? "none"}-${appointmentPrefill?.doctorId ?? "none"}`}
            role={currentUser.role}
            doctors={doctors}
            patients={patients}
            currentPatientId={currentPatientId}
            appointments={appointments}
            loading={appointmentsLoading}
            error={appointmentsError}
            onCreate={handleCreateAppointment}
            onUpdateStatus={handleUpdateAppointmentStatus}
            preFill={appointmentPrefill}
            onClearPreFill={() => setAppointmentPrefill(null)}
          />
        );
      case "visits":
        return (
          <VisitsPanel
            key={`visits-${currentPatientId ?? "none"}`}
            role={currentUser.role}
            patientOptions={
              currentUser.role === "patient"
                ? patientProfile
                  ? [patientProfile]
                  : []
                : patients
            }
            selectedPatientId={currentPatientId}
            currentDoctorId={doctorProfile?.id ?? null}
            visits={visits}
            loading={visitsLoading}
            error={visitsError}
            onSelectPatient={refreshVisits}
            onCreateVisit={handleCreateVisit}
          />
        );
      case "records":
        return (
          <RecordsImportPanel
            key={`records-${selectedPatientId ?? "none"}`}
            patients={patients}
            selectedPatientId={selectedPatientId}
            loading={recordsLoading}
            error={recordsError}
            successMessage={recordsSuccess}
            onSelectPatient={refreshVisits}
            onImport={handleImportRecords}
          />
        );
      default:
        return null;
    }
  }

  return (
    <div className="page-shell">
      <div className="dashboard-shell">
        <DashboardNav
          user={currentUser}
          selectedTab={selectedTab}
          onSelectTab={handleSelectTab}
          onLogout={handleLogout}
        />

        <main className="dashboard-main">
          <header className="dashboard-main__header">
            <div>
              <p className="dashboard-main__eyebrow">Live care workspace</p>
              <h2>{tabMeta[selectedTab].title}</h2>
              <p className="dashboard-main__copy">
                {tabMeta[selectedTab].description}
              </p>
            </div>

            <div className="status-bubble">
              <span>{currentUser.role.toUpperCase()}</span>
              <strong>API connected</strong>
            </div>
          </header>

          {pageError ? <div className="notice notice--error">{pageError}</div> : null}

          {dashboardLoading ? (
            <div className="loading-card">Loading workspace...</div>
          ) : (
            renderPanel()
          )}
        </main>
      </div>
    </div>
  );
}
