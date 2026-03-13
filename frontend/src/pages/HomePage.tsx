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
  fetchMyPatientProfile,
  listPatients,
  upsertMyPatientProfile,
} from "../api/patients";
import { importRecords } from "../api/records";
import { triage, type TriageResponse } from "../api/triage";
import { createVisit, listPatientVisits } from "../api/visits";
import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
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

  useEffect(() => {
    if (!user) {
      return;
    }

    if (user.role === "patient" && selectedTab === "records") {
      setSelectedTab("overview");
    }
  }, [selectedTab, user]);

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
    setSelectedPatientId(null);
    setTriageResult(null);
    setTriageQuery("");
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
        ] = await Promise.all([
          patientProfileRequest,
          doctorProfileRequest,
          listDoctors().catch(() => []),
          currentUser.role === "patient"
            ? Promise.resolve([])
            : listPatients().catch(() => []),
          listAppointments().catch(() => []),
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

  async function refreshVisits(patientId: number | null) {
    setSelectedPatientId(patientId);
    if (!patientId) {
      setVisits([]);
      return;
    }

    setVisitsLoading(true);
    setVisitsError(null);
    try {
      const response = await listPatientVisits(patientId);
      setVisits(response);
    } catch (error) {
      setVisitsError(getErrorMessage(error, "Failed to load visits."));
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
    sex: string;
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
      const result = await triage(triageQuery.trim(), selectedPatientId ?? undefined);
      setTriageResult(result);
    } catch (error) {
      setTriageError(getErrorMessage(error, "Failed to run triage."));
    } finally {
      setTriageLoading(false);
    }
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

  const triagePatients =
    currentUser.role === "patient"
      ? patientProfile
        ? [patientProfile]
        : []
      : patients;

  const currentPatientId =
    currentUser.role === "patient" ? patientProfile?.id ?? null : selectedPatientId;

  function renderPanel() {
    switch (selectedTab) {
      case "overview":
        return (
          <OverviewPanel
            role={currentUser.role}
            key={`overview-${currentUser.role}`}
            patientProfile={patientProfile}
            doctorProfile={doctorProfile}
            doctorsCount={doctors.length}
            patientsCount={patients.length}
            appointmentsCount={appointments.length}
            visitsCount={visits.length}
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
            onSavePatient={handleSavePatientProfile}
            onSaveDoctor={handleSaveDoctorProfile}
          />
        );
      case "triage":
        return (
          <TriagePanel
            key={`triage-${currentPatientId ?? "none"}`}
            loading={triageLoading}
            error={triageError}
            result={triageResult}
            patientOptions={triagePatients}
            patientId={currentPatientId}
            lockPatientSelection={
              currentUser.role === "patient" && Boolean(patientProfile)
            }
            query={triageQuery}
            onQueryChange={setTriageQuery}
            onPatientChange={refreshVisits}
            onSubmit={handleRunTriage}
          />
        );
      case "appointments":
        return (
          <AppointmentsPanel
            key={`appointments-${currentPatientId ?? "none"}`}
            role={currentUser.role}
            doctors={doctors}
            patients={patients}
            currentPatientId={currentPatientId}
            appointments={appointments}
            loading={appointmentsLoading}
            error={appointmentsError}
            onCreate={handleCreateAppointment}
            onUpdateStatus={handleUpdateAppointmentStatus}
          />
        );
      case "visits":
        return (
          <VisitsPanel
            key={`visits-${currentPatientId ?? "none"}`}
            role={currentUser.role}
            patientOptions={triagePatients}
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
              <p className="dashboard-main__eyebrow">Live backend workspace</p>
              <h2>{selectedTab.toUpperCase()}</h2>
              <p className="dashboard-main__copy">
                Frontend actions are wired to FastAPI endpoints with JWT auth.
              </p>
            </div>

            <div className="status-bubble">
              <span>API</span>
              <strong>connected</strong>
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
