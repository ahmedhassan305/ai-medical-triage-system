import type {
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
} from "../api/dto";
import SectionPanel from "./SectionPanel";

type OverviewPanelProps = {
  role: RoleType;
  patientProfile: PatientProfileResponseDto | null;
  doctorProfile: DoctorProfileResponseDto | null;
  doctorsCount: number;
  patientsCount: number;
  appointmentsCount: number;
  visitsCount: number;
};

export default function OverviewPanel({
  role,
  patientProfile,
  doctorProfile,
  doctorsCount,
  patientsCount,
  appointmentsCount,
  visitsCount,
}: OverviewPanelProps) {
  const profileReady =
    role === "patient"
      ? Boolean(patientProfile)
      : role === "doctor"
        ? Boolean(doctorProfile)
        : Boolean(patientProfile || doctorProfile);

  return (
    <SectionPanel
      eyebrow="System status"
      title="Operational snapshot"
      description="A live summary of profile readiness and the CRM objects currently available in the backend."
    >
      <div className="metric-grid">
        <article className="metric-card">
          <span>Role</span>
          <strong>{role.toUpperCase()}</strong>
        </article>
        <article className="metric-card">
          <span>Profile status</span>
          <strong>{profileReady ? "Ready" : "Needs setup"}</strong>
        </article>
        <article className="metric-card">
          <span>Appointments</span>
          <strong>{appointmentsCount}</strong>
        </article>
        <article className="metric-card">
          <span>Visits loaded</span>
          <strong>{visitsCount}</strong>
        </article>
        <article className="metric-card">
          <span>Doctors indexed</span>
          <strong>{doctorsCount}</strong>
        </article>
        <article className="metric-card">
          <span>Patients indexed</span>
          <strong>{patientsCount}</strong>
        </article>
      </div>

      <div className="callout">
        <p>
          {profileReady
            ? "Profile data is available, so triage can attach patient context and CRM operations can use live IDs."
            : "Create the relevant profile first. Triage still works, but patient-history features and appointment flows stay limited."}
        </p>
      </div>
    </SectionPanel>
  );
}
