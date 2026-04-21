import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
  TriageResponseDto,
  VisitResponseDto,
} from "../api/dto";
import type { DashboardTab } from "./DashboardNav";

type OverviewPanelProps = {
  role: RoleType;
  patientProfile: PatientProfileResponseDto | null;
  doctorProfile: DoctorProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
  visits: VisitResponseDto[];
  recentVisits: VisitResponseDto[];
  doctors: DoctorProfileResponseDto[];
  triageResult: TriageResponseDto | null;
  onNavigate: (tab: DashboardTab) => void;
};

type QuickAction = {
  label: string;
  description: string;
  tab: DashboardTab;
  tone?: "primary" | "ghost";
};

const APPOINTMENT_STATUS_LABELS: Record<string, string> = {
  requested: "Requested",
  approved: "Confirmed",
  rejected: "Rejected",
  completed: "Completed",
};

const REQUIRED_SPECIALTIES = [
  "Cardiology",
  "Neurology",
  "Neurosurgery",
  "Internal Medicine",
  "Gastroenterology",
  "Dermatology",
  "Psychiatry",
  "Ophthalmology",
  "Orthopedics",
  "ENT",
  "Pediatrics",
  "Family Medicine",
];

function formatDateTime(dateString?: string | null): string {
  if (!dateString) {
    return "Not scheduled yet";
  }

  try {
    return new Date(dateString).toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

function summarize(text?: string | null, fallback = "No summary available."): string {
  if (!text) {
    return fallback;
  }
  const normalized = text.trim();
  if (normalized.length <= 140) {
    return normalized;
  }
  return `${normalized.slice(0, 137).trimEnd()}...`;
}

function getAppointmentDisplayDate(appointment: AppointmentResponseDto): string {
  return appointment.scheduled_for || appointment.requested_at;
}

function sortAppointments(appointments: AppointmentResponseDto[]): AppointmentResponseDto[] {
  return [...appointments].sort(
    (left, right) =>
      new Date(getAppointmentDisplayDate(left)).getTime() -
      new Date(getAppointmentDisplayDate(right)).getTime(),
  );
}

function classForStatus(status: string): string {
  switch (status) {
    case "approved":
      return "is-complete";
    case "rejected":
      return "is-blocked";
    default:
      return "is-current";
  }
}

function appointmentStatusLabel(status: string): string {
  return APPOINTMENT_STATUS_LABELS[status] || status;
}

function topDoctorForAppointment(
  appointment: AppointmentResponseDto | null,
  doctors: DoctorProfileResponseDto[],
): DoctorProfileResponseDto | null {
  if (!appointment) {
    return null;
  }
  return doctors.find((doctor) => doctor.id === appointment.doctor_id) || null;
}

function latestVisitForPatient(
  visits: VisitResponseDto[],
  patientId: number | null,
): VisitResponseDto | null {
  if (!patientId) {
    return null;
  }
  return visits.find((visit) => visit.patient_id === patientId) || null;
}

function countBySpecialty(doctors: DoctorProfileResponseDto[]): Array<[string, number]> {
  const counts = new Map<string, number>();
  doctors.forEach((doctor) => {
    counts.set(doctor.specialty, (counts.get(doctor.specialty) || 0) + 1);
  });
  return Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
}

function countAppointmentDemand(
  appointments: AppointmentResponseDto[],
  doctors: DoctorProfileResponseDto[],
): Array<[string, number]> {
  const doctorSpecialty = new Map(doctors.map((doctor) => [doctor.id, doctor.specialty]));
  const counts = new Map<string, number>();
  appointments.forEach((appointment) => {
    const specialty = doctorSpecialty.get(appointment.doctor_id);
    if (!specialty) {
      return;
    }
    counts.set(specialty, (counts.get(specialty) || 0) + 1);
  });
  return Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
}

function normalizeStatus(status: string): "good" | "pending" | "problem" | "info" {
  if (status === "approved" || status === "completed") {
    return "good";
  }
  if (status === "requested") {
    return "pending";
  }
  if (status === "rejected") {
    return "problem";
  }
  return "info";
}

function primaryPatientAction(
  triageResult: TriageResponseDto | null,
  nextAppointment: AppointmentResponseDto | null,
): QuickAction {
  if (!triageResult) {
    return {
      label: "Run triage",
      description: "Start with symptom review to get urgency and specialty guidance.",
      tab: "triage",
      tone: "primary",
    };
  }
  if (!nextAppointment) {
    return {
      label: "Book appointment",
      description: "Convert the latest triage result into a confirmed doctor follow-up.",
      tab: "appointments",
      tone: "primary",
    };
  }
  return {
    label: "Prepare for appointment",
    description: "Review the booking status and latest notes before the visit.",
    tab: "appointments",
    tone: "primary",
  };
}

function QuickActions({
  title,
  actions,
  onNavigate,
}: {
  title: string;
  actions: QuickAction[];
  onNavigate: (tab: DashboardTab) => void;
}) {
  return (
    <section className="workspace-card workspace-card--actions">
      <div className="workspace-card__header">
        <div>
          <p className="micro-label">Quick actions</p>
          <h3>{title}</h3>
        </div>
      </div>
      <div className="action-grid">
        {actions.map((action) => (
          <button
            key={`${action.tab}-${action.label}`}
            type="button"
            className={`action-shortcut ${action.tone === "ghost" ? "action-shortcut--ghost" : ""}`}
            onClick={() => onNavigate(action.tab)}
          >
            <strong>{action.label}</strong>
            <span>{action.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function EmptyPrompt({
  eyebrow,
  title,
  body,
  actionLabel,
  actionTab,
  onNavigate,
}: {
  eyebrow: string;
  title: string;
  body: string;
  actionLabel: string;
  actionTab: DashboardTab;
  onNavigate: (tab: DashboardTab) => void;
}) {
  return (
    <div className="empty-prompt">
      <p className="micro-label">{eyebrow}</p>
      <h4>{title}</h4>
      <p>{body}</p>
      <button
        type="button"
        className="button button--primary button--small"
        onClick={() => onNavigate(actionTab)}
      >
        {actionLabel}
      </button>
    </div>
  );
}

function PatientOverview({
  patientProfile,
  appointments,
  visits,
  doctors,
  triageResult,
  onNavigate,
}: {
  patientProfile: PatientProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  visits: VisitResponseDto[];
  doctors: DoctorProfileResponseDto[];
  triageResult: TriageResponseDto | null;
  onNavigate: (tab: DashboardTab) => void;
}) {
  if (!patientProfile) {
    return (
      <div className="workspace-dashboard workspace-dashboard--patient">
        <section className="dashboard-hero dashboard-hero--patient">
          <div>
            <p className="dashboard-hero__eyebrow">My care space</p>
            <h3>Complete your patient profile to unlock triage and booking.</h3>
            <p>
              Your profile links national ID details, visit history, and future doctor
              recommendations.
            </p>
          </div>
          <button
            type="button"
            className="button button--primary"
            onClick={() => onNavigate("profile")}
          >
            Complete profile
          </button>
        </section>
      </div>
    );
  }

  const activeAppointments = sortAppointments(
    appointments.filter((appointment) => appointment.status !== "rejected"),
  );
  const nextAppointment = activeAppointments[0] || null;
  const nextDoctor = topDoctorForAppointment(nextAppointment, doctors);
  const latestVisit = latestVisitForPatient(visits, patientProfile.id);
  const nextAction =
    triageResult?.recommended_actions[0] ||
    "Run triage if symptoms change or you need a new recommendation.";
  const latestSuggestedDoctor = triageResult?.suggested_doctors[0] || null;
  const primaryAction = primaryPatientAction(triageResult, nextAppointment);

  return (
    <div className="workspace-dashboard workspace-dashboard--patient">
      <section className="dashboard-hero dashboard-hero--patient">
        <div>
          <p className="dashboard-hero__eyebrow">My care space</p>
          <h3>{patientProfile.full_name}, here is your next care step.</h3>
          <p>
            Keep appointments, triage guidance, and recent visit notes in one calm
            workspace.
          </p>
        </div>
        <div className="hero-pill-group">
          <span className="hero-pill">{appointments.length} appointments tracked</span>
          <span className="hero-pill">{visits.length} visit records</span>
          <span className="hero-pill">
            {patientProfile.current_governorate ||
              patientProfile.inferred_governorate ||
              "Governorate pending"}
          </span>
        </div>
      </section>

      <div className="workspace-grid workspace-grid--patient">
        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Care status</p>
              <h3>Your current care summary</h3>
            </div>
            <span className={`badge badge--${triageResult?.urgency_level || "neutral"}`}>
              {triageResult ? triageResult.urgency_level.toUpperCase() : "NO TRIAGE"}
            </span>
          </div>
          <div className="care-status-grid">
            <article className={`status-card status-card--${nextAppointment ? normalizeStatus(nextAppointment.status) : "info"}`}>
              <span>Appointment</span>
              <strong>
                {nextAppointment
                  ? appointmentStatusLabel(nextAppointment.status)
                  : "No appointment booked"}
              </strong>
              <p>
                {nextAppointment
                  ? formatDateTime(nextAppointment.scheduled_for)
                  : "Book once you are ready to follow up."}
              </p>
            </article>
            <article className={`status-card status-card--${triageResult ? normalizeStatus(triageResult.urgency_level === "high" ? "rejected" : triageResult.urgency_level === "medium" ? "requested" : "approved") : "info"}`}>
              <span>Latest triage</span>
              <strong>{triageResult ? triageResult.urgency_label : "Not started"}</strong>
              <p>{triageResult ? nextAction : "Run triage to get urgency guidance."}</p>
            </article>
            <article className={`status-card status-card--${latestVisit ? "good" : "info"}`}>
              <span>Visit history</span>
              <strong>{latestVisit ? "History available" : "No visits yet"}</strong>
              <p>
                {latestVisit
                  ? latestVisit.diagnosis || "Recent visit recorded."
                  : "Doctor visit notes will appear here after your first consultation."}
              </p>
            </article>
          </div>
          <div className="workspace-primary-action">
            <button
              type="button"
              className="button button--primary"
              onClick={() => onNavigate(primaryAction.tab)}
            >
              {primaryAction.label}
            </button>
            <p>{primaryAction.description}</p>
          </div>
        </section>

        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Next appointment</p>
              <h3>
                {nextAppointment
                  ? appointmentStatusLabel(nextAppointment.status)
                  : "No appointment booked yet"}
              </h3>
            </div>
            {nextAppointment ? (
              <span className={`badge badge--status-${nextAppointment.status}`}>
                {appointmentStatusLabel(nextAppointment.status)}
              </span>
            ) : null}
          </div>

          {nextAppointment ? (
            <>
              <div className="status-track">
                <div className={`status-track__step ${classForStatus("requested")}`}>
                  <strong>Request submitted</strong>
                  <span>{formatDateTime(nextAppointment.requested_at)}</span>
                </div>
                <div
                  className={`status-track__step ${
                    nextAppointment.status === "approved"
                      ? "is-complete"
                      : nextAppointment.status === "rejected"
                        ? "is-blocked"
                        : "is-pending"
                  }`}
                >
                  <strong>Clinic review</strong>
                  <span>
                    {nextAppointment.status === "approved"
                      ? "Confirmed"
                      : nextAppointment.status === "rejected"
                        ? "Rejected"
                        : "Awaiting review"}
                  </span>
                </div>
                <div className="status-track__step is-pending">
                  <strong>Visit day</strong>
                  <span>{formatDateTime(nextAppointment.scheduled_for)}</span>
                </div>
              </div>
              <div className="detail-list">
                <div>
                  <span>Doctor</span>
                  <strong>
                    {nextDoctor?.full_name || `Doctor #${nextAppointment.doctor_id}`}
                  </strong>
                </div>
                <div>
                  <span>Specialty</span>
                  <strong>{nextDoctor?.specialty || "Specialty pending"}</strong>
                </div>
                <div>
                  <span>Reason</span>
                  <strong>{summarize(nextAppointment.reason)}</strong>
                </div>
              </div>
            </>
          ) : (
            <EmptyPrompt
              eyebrow="Booking"
              title="You do not have an active appointment yet."
              body="Run triage to get a specialty recommendation, then reserve an appointment directly from the result."
              actionLabel="Book appointment"
              actionTab="appointments"
              onNavigate={onNavigate}
            />
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Latest triage</p>
              <h3>
                {triageResult
                  ? triageResult.urgency_label
                  : "No triage completed in this session"}
              </h3>
            </div>
            {triageResult ? (
              <span className={`badge badge--${triageResult.urgency_level}`}>
                {triageResult.urgency_level.toUpperCase()}
              </span>
            ) : null}
          </div>

          {triageResult ? (
            <div className="stack-md">
              <p>{summarize(triageResult.patient_friendly_explanation, "")}</p>
              <div className="detail-list">
                <div>
                  <span>Recommended specialty</span>
                  <strong>
                    {triageResult.recommended_specialty || "General Practice"}
                  </strong>
                </div>
                <div>
                  <span>Top next step</span>
                  <strong>{nextAction}</strong>
                </div>
              </div>
              {latestSuggestedDoctor ? (
                <div className="spotlight-inline">
                  <div>
                    <span>Latest doctor recommendation</span>
                    <strong>{latestSuggestedDoctor.full_name}</strong>
                    <p>
                      {latestSuggestedDoctor.specialty}
                      {latestSuggestedDoctor.area
                        ? ` · ${latestSuggestedDoctor.area}`
                        : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="button button--ghost button--small"
                    onClick={() => onNavigate("appointments")}
                  >
                    Continue to booking
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyPrompt
              eyebrow="Triage"
              title="No triage result yet."
              body="Describe current symptoms to get urgency guidance, possible conditions, and doctor suggestions."
              actionLabel="Run triage"
              actionTab="triage"
              onNavigate={onNavigate}
            />
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Latest visit</p>
              <h3>{latestVisit ? "Recent clinical summary" : "No visit history yet"}</h3>
            </div>
          </div>

          {latestVisit ? (
            <div className="stack-md">
              <div className="detail-list">
                <div>
                  <span>Recorded</span>
                  <strong>{formatDateTime(latestVisit.created_at)}</strong>
                </div>
                <div>
                  <span>Diagnosis</span>
                  <strong>{latestVisit.diagnosis || "Not recorded"}</strong>
                </div>
              </div>
              <p>{summarize(latestVisit.notes || latestVisit.symptoms)}</p>
            </div>
          ) : (
            <EmptyPrompt
              eyebrow="History"
              title="No visit records are linked to your profile yet."
              body="Once a doctor creates a visit, the summary will appear here and improve future triage context."
              actionLabel="View visits"
              actionTab="visits"
              onNavigate={onNavigate}
            />
          )}
        </section>

        <QuickActions
          title="Secondary actions"
          onNavigate={onNavigate}
          actions={[
            {
              label: "Book appointment",
              description:
                "Choose a doctor or continue from a triage recommendation.",
              tab: "appointments",
            },
            {
              label: "Run triage",
              description: "Check urgency and get a specialty recommendation.",
              tab: "triage",
            },
            {
              label: "Update profile",
              description:
                "Review national ID details, governorate, and chronic conditions.",
              tab: "profile",
            },
            {
              label: "View visits",
              description:
                "Read your latest diagnoses, notes, and prescriptions.",
              tab: "visits",
            },
          ]}
        />
      </div>
    </div>
  );
}

function DoctorOverview({
  doctorProfile,
  appointments,
  patients,
  recentVisits,
  onNavigate,
}: {
  doctorProfile: DoctorProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
  recentVisits: VisitResponseDto[];
  onNavigate: (tab: DashboardTab) => void;
}) {
  if (!doctorProfile) {
    return (
      <div className="workspace-dashboard workspace-dashboard--doctor">
        <section className="dashboard-hero dashboard-hero--doctor dashboard-hero--warning">
          <div>
            <p className="dashboard-hero__eyebrow">Clinician workspace</p>
            <h3>Complete your doctor profile to activate scheduling and patient workflows.</h3>
            <p>
              Your clinic and specialty details are required before appointment
              approvals, visit creation, and record imports can run safely.
            </p>
          </div>
          <button
            type="button"
            className="button button--primary"
            onClick={() => onNavigate("profile")}
          >
            Complete doctor profile
          </button>
        </section>

        <div className="workspace-grid workspace-grid--doctor">
          <section className="workspace-card workspace-card--skeleton">
            <p className="micro-label">Appointments</p>
            <h3>Scheduling activates after profile setup</h3>
            <p>
              Once your profile is complete, new appointment requests and approved
              bookings will appear here automatically.
            </p>
          </section>
          <QuickActions
            title="Doctor setup actions"
            onNavigate={onNavigate}
            actions={[
              {
                label: "Complete profile",
                description:
                  "Set your specialty and clinic so patients can find you.",
                tab: "profile",
                tone: "primary",
              },
              {
                label: "Review appointments",
                description: "Open the scheduling workspace after setup.",
                tab: "appointments",
              },
              {
                label: "Import records",
                description:
                  "Record imports become useful once patient work starts.",
                tab: "records",
              },
            ]}
          />
        </div>
      </div>
    );
  }

  const orderedAppointments = sortAppointments(appointments);
  const pendingApprovals = orderedAppointments.filter(
    (appointment) => appointment.status === "requested",
  );
  const upcomingAppointments = orderedAppointments.filter(
    (appointment) => appointment.status === "approved",
  );
  const completedAppointments = orderedAppointments.filter(
    (appointment) =>
      appointment.status === "completed" ||
      (appointment.status === "approved" &&
        appointment.scheduled_for &&
        new Date(appointment.scheduled_for) < new Date()),
  );
  const uniquePatientLoad = new Set([
    ...appointments.map((appointment) => appointment.patient_id),
    ...recentVisits.map((visit) => visit.patient_id),
  ]).size;

  return (
    <div className="workspace-dashboard workspace-dashboard--doctor">
      <section className="dashboard-hero dashboard-hero--doctor">
        <div>
          <p className="dashboard-hero__eyebrow">Clinician workspace</p>
          <h3>{doctorProfile.full_name}</h3>
          <p>
            {doctorProfile.specialty} · {doctorProfile.clinic}
            {doctorProfile.area ? ` · ${doctorProfile.area}` : ""}
          </p>
        </div>
        <div className="hero-pill-group">
          <span className="hero-pill">{pendingApprovals.length} pending approvals</span>
          <span className="hero-pill">{uniquePatientLoad} active patients</span>
          <span className="hero-pill">{recentVisits.length} visits on record</span>
        </div>
      </section>

      <div className="workspace-grid workspace-grid--doctor">
        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Today's focus</p>
              <h3>What needs your attention</h3>
            </div>
          </div>
          <div className="care-status-grid">
            <article
              className={`status-card status-card--${
                pendingApprovals.length > 0 ? "pending" : "good"
              }`}
            >
              <span>Pending approvals</span>
              <strong>{pendingApprovals.length}</strong>
              <p>
                {pendingApprovals.length > 0
                  ? "Start with the waiting appointment approvals."
                  : "No approvals are waiting right now."}
              </p>
            </article>
            <article
              className={`status-card status-card--${
                upcomingAppointments.length > 0 ? "info" : "good"
              }`}
            >
              <span>Confirmed appointments</span>
              <strong>{upcomingAppointments.length}</strong>
              <p>
                {upcomingAppointments.length > 0
                  ? "Review confirmed visits and prepare the clinic flow."
                  : "No confirmed bookings are scheduled yet."}
              </p>
            </article>
            <article className="status-card status-card--good">
              <span>Active patient load</span>
              <strong>{uniquePatientLoad}</strong>
              <p>Distinct patients currently flowing through your workspace.</p>
            </article>
          </div>
        </section>

        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Today and next</p>
              <h3>Confirmed appointments</h3>
            </div>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => onNavigate("appointments")}
            >
              Open schedule
            </button>
          </div>

          {upcomingAppointments.length > 0 ? (
            <div className="activity-list">
              {upcomingAppointments.slice(0, 4).map((appointment) => {
                const patient = patients.find((item) => item.id === appointment.patient_id);
                return (
                  <article key={appointment.id} className="activity-item">
                    <div>
                      <strong>
                        {patient?.full_name || `Patient #${appointment.patient_id}`}
                      </strong>
                      <p>{summarize(appointment.reason)}</p>
                    </div>
                    <div className="activity-meta">
                      <span className={`badge badge--status-${appointment.status}`}>
                        {appointmentStatusLabel(appointment.status)}
                      </span>
                      <small>{formatDateTime(getAppointmentDisplayDate(appointment))}</small>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <EmptyPrompt
              eyebrow="Schedule"
              title="No upcoming appointments yet."
              body="As soon as patients book you or triage handoffs convert into requests, the schedule will appear here."
              actionLabel="Review appointments"
              actionTab="appointments"
              onNavigate={onNavigate}
            />
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Pending approvals</p>
              <h3>{pendingApprovals.length} requests awaiting your decision</h3>
            </div>
          </div>
          {pendingApprovals.length > 0 ? (
            <div className="task-list">
              {pendingApprovals.slice(0, 4).map((appointment) => {
                const patient = patients.find((item) => item.id === appointment.patient_id);
                return (
                  <article key={appointment.id} className="activity-item">
                    <div>
                      <strong>
                        {patient?.full_name || `Patient #${appointment.patient_id}`}
                      </strong>
                      <p>{summarize(appointment.reason)}</p>
                    </div>
                    <div className="activity-meta">
                      <span className="badge badge--status-requested">
                        requested
                      </span>
                      <small>{formatDateTime(appointment.requested_at)}</small>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-prompt empty-prompt--compact">
              <h4>No approvals are waiting right now.</h4>
              <p>
                You can focus on visit documentation and record imports until new
                requests arrive.
              </p>
            </div>
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Recent visits created</p>
              <h3>Latest clinical notes</h3>
            </div>
          </div>
          {recentVisits.length > 0 ? (
            <div className="activity-list">
              {recentVisits.slice(0, 4).map((visit) => {
                const patient = patients.find((item) => item.id === visit.patient_id);
                return (
                  <article key={visit.id} className="activity-item">
                    <div>
                      <strong>
                        {patient?.full_name || `Patient #${visit.patient_id}`}
                      </strong>
                      <p>{summarize(visit.diagnosis || visit.symptoms)}</p>
                    </div>
                    <div className="activity-meta">
                      <span className="badge badge--neutral">Visit #{visit.id}</span>
                      <small>{formatDateTime(visit.created_at)}</small>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <EmptyPrompt
              eyebrow="Visits"
              title="No visits have been documented yet."
              body="Create a visit after a consultation so symptoms, diagnosis, and prescriptions are stored in patient history."
              actionLabel="Create visit"
              actionTab="visits"
              onNavigate={onNavigate}
            />
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Completed work</p>
              <h3>Recently finished appointments</h3>
            </div>
          </div>
          {completedAppointments.length > 0 ? (
            <div className="activity-list">
              {completedAppointments.slice(0, 4).map((appointment) => {
                const patient = patients.find((item) => item.id === appointment.patient_id);
                return (
                  <article key={appointment.id} className="activity-item">
                    <div>
                      <strong>
                        {patient?.full_name || `Patient #${appointment.patient_id}`}
                      </strong>
                      <p>{summarize(appointment.reason)}</p>
                    </div>
                    <div className="activity-meta">
                      <span className="badge badge--status-completed">
                        completed
                      </span>
                      <small>{formatDateTime(appointment.scheduled_for)}</small>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-prompt empty-prompt--compact">
              <h4>No completed appointments yet.</h4>
              <p>Finished bookings will appear here once clinic work closes them.</p>
            </div>
          )}
        </section>

        <QuickActions
          title="Workflow shortcuts"
          onNavigate={onNavigate}
          actions={[
            {
              label: "Review appointments",
              description: "Approve or reject incoming requests quickly.",
              tab: "appointments",
              tone: "primary",
            },
            {
              label: "Create visit",
              description: "Capture symptoms, diagnosis, and prescriptions.",
              tab: "visits",
            },
            {
              label: "Import records",
              description: "Bring external visit records into patient history.",
              tab: "records",
            },
            {
              label: "Update profile",
              description:
                "Keep specialty and clinic details accurate for patient discovery.",
              tab: "profile",
            },
          ]}
        />
      </div>
    </div>
  );
}

function AdminOverview({
  appointments,
  patients,
  doctors,
  recentVisits,
  onNavigate,
}: {
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
  doctors: DoctorProfileResponseDto[];
  recentVisits: VisitResponseDto[];
  onNavigate: (tab: DashboardTab) => void;
}) {
  const coverage = countBySpecialty(doctors);
  const coverageMap = new Map(coverage);
  const demand = countAppointmentDemand(appointments, doctors);
  const weakCoverage = REQUIRED_SPECIALTIES.filter(
    (specialty) => (coverageMap.get(specialty) || 0) < 2,
  );
  const appointmentsByStatus = {
    requested: appointments.filter((appointment) => appointment.status === "requested")
      .length,
    approved: appointments.filter((appointment) => appointment.status === "approved")
      .length,
    rejected: appointments.filter((appointment) => appointment.status === "rejected")
      .length,
    completed: appointments.filter((appointment) => appointment.status === "completed")
      .length,
  };
  const recentPatients = [...patients]
    .sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
    )
    .slice(0, 4);
  const recentDoctors = [...doctors]
    .sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
    )
    .slice(0, 4);
  const recentAppointments = [...appointments]
    .sort(
      (left, right) =>
        new Date(right.requested_at).getTime() -
        new Date(left.requested_at).getTime(),
    )
    .slice(0, 4);
  const specialtyDemandMap = new Map(demand);
  const specialtyRows = REQUIRED_SPECIALTIES.map((specialty) => {
    const doctorCount = coverageMap.get(specialty) || 0;
    const appointmentDemand = specialtyDemandMap.get(specialty) || 0;
    const status =
      doctorCount === 0
        ? "needs attention"
        : appointmentDemand > doctorCount * 3
          ? "overloaded"
          : doctorCount < 2
            ? "needs attention"
            : "balanced";
    return { specialty, doctorCount, appointmentDemand, status };
  });
  const actionAlerts = [
    appointmentsByStatus.requested > 0
      ? `${appointmentsByStatus.requested} pending appointments need review`
      : null,
    weakCoverage.length > 0
      ? `${weakCoverage.length} specialties need stronger coverage`
      : null,
    recentVisits.length === 0 ? "No recent visits recorded in the workspace" : null,
  ].filter(Boolean) as string[];

  return (
    <div className="workspace-dashboard workspace-dashboard--admin">
      <section className="dashboard-hero dashboard-hero--admin">
        <div>
          <p className="dashboard-hero__eyebrow">Admin control center</p>
          <h3>Operational command view for the care platform.</h3>
          <p>
            Watch appointment flow, doctor coverage, and recent workspace activity
            from one place.
          </p>
        </div>
        <div className="hero-pill-group">
          <span className="hero-pill">{doctors.length} doctors loaded</span>
          <span className="hero-pill">{patients.length} patients registered</span>
          <span className="hero-pill">
            {weakCoverage.length === 0
              ? "Coverage balanced"
              : `${weakCoverage.length} specialties need attention`}
          </span>
        </div>
      </section>

      <div className="workspace-grid workspace-grid--admin">
        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Action required</p>
              <h3>Immediate operational priorities</h3>
            </div>
          </div>
          {actionAlerts.length > 0 ? (
            <div className="task-list">
              {actionAlerts.map((alert) => (
                <article key={alert} className="activity-item">
                  <div>
                    <strong>{alert}</strong>
                    <p>Use the admin actions below to resolve this quickly.</p>
                  </div>
                  <div className="activity-meta">
                    <span className="badge badge--status-rejected">attention</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-prompt empty-prompt--compact">
              <h4>No urgent admin actions right now.</h4>
              <p>The control center is stable across appointments, coverage, and records.</p>
            </div>
          )}
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Admin actions</p>
              <h3>Act on the workspace</h3>
            </div>
          </div>
          <div className="action-grid">
            <button
              type="button"
              className="action-shortcut"
              onClick={() => onNavigate("appointments")}
            >
              <strong>Manage appointments</strong>
              <span>Review pending bookings, confirmations, and past activity.</span>
            </button>
            <button
              type="button"
              className="action-shortcut action-shortcut--ghost"
              onClick={() => onNavigate("profile")}
            >
              <strong>Review profiles</strong>
              <span>Inspect patient and doctor records from the admin profile workspace.</span>
            </button>
            <button
              type="button"
              className="action-shortcut action-shortcut--ghost"
              onClick={() => onNavigate("records")}
            >
              <strong>Import records</strong>
              <span>Bring in external medical history when staff need it.</span>
            </button>
            <button
              type="button"
              className="action-shortcut action-shortcut--ghost"
              onClick={() => onNavigate("triage")}
            >
              <strong>Update doctor directory</strong>
              <span>Open staff-assisted triage and review the doctor handoff experience.</span>
            </button>
          </div>
        </section>

        <section className="workspace-card workspace-card--feature">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Top operational metrics</p>
              <h3>Live system posture</h3>
            </div>
          </div>
          <div className="admin-metric-grid">
            <article className="metric-card">
              <span>Total patients</span>
              <strong>{patients.length}</strong>
            </article>
            <article className="metric-card">
              <span>Total doctors</span>
              <strong>{doctors.length}</strong>
            </article>
            <article className="metric-card">
              <span>Pending appointments</span>
              <strong>{appointmentsByStatus.requested}</strong>
            </article>
            <article className="metric-card">
              <span>Confirmed appointments</span>
              <strong>{appointmentsByStatus.approved}</strong>
            </article>
            <article className="metric-card">
              <span>Rejected appointments</span>
              <strong>{appointmentsByStatus.rejected}</strong>
            </article>
            <article className="metric-card">
              <span>Recent visits</span>
              <strong>{recentVisits.length}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Appointment funnel</p>
              <h3>Status breakdown</h3>
            </div>
          </div>
          <div className="funnel-list">
            {[
              ["Requested", appointmentsByStatus.requested],
              ["Confirmed", appointmentsByStatus.approved],
              ["Completed", appointmentsByStatus.completed],
              ["Rejected", appointmentsByStatus.rejected],
            ].map(([label, count]) => (
              <div key={label} className="funnel-row">
                <span>{label}</span>
                <div className="funnel-row__bar">
                  <div
                    style={{
                      width: `${
                        appointments.length
                          ? Math.max((Number(count) / appointments.length) * 100, 8)
                          : 0
                      }%`,
                    }}
                  />
                </div>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Coverage and demand</p>
              <h3>Specialty balancing table</h3>
            </div>
          </div>
          {specialtyRows.length > 0 ? (
            <div className="ops-table">
              <div className="ops-table__header">
                <span>Specialty</span>
                <span>Doctors</span>
                <span>Demand</span>
                <span>Status</span>
              </div>
              {specialtyRows.map((row) => (
                <div key={row.specialty} className="ops-table__row">
                  <strong>{row.specialty}</strong>
                  <span>{row.doctorCount}</span>
                  <span>{row.appointmentDemand}</span>
                  <span className={`badge ${
                    row.status === "balanced"
                      ? "badge--status-approved"
                      : row.status === "overloaded"
                        ? "badge--status-rejected"
                        : "badge--status-requested"
                  }`}>
                    {row.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-prompt empty-prompt--compact">
              <h4>No specialty balancing data yet.</h4>
              <p>
                Coverage and demand will appear once appointments and doctor records are available.
              </p>
            </div>
          )}
        </section>

        <section className="workspace-card workspace-card--activity-span">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Recent activity</p>
              <h3>Registrations, additions, and care events</h3>
            </div>
          </div>
          <div className="activity-columns">
            <div>
              <h4>Recent patients</h4>
              <div className="activity-list compact">
                {recentPatients.slice(0, 3).map((patient) => (
                  <article key={patient.id} className="activity-item">
                    <div>
                      <strong>{patient.full_name}</strong>
                      <p>
                        {patient.current_governorate ||
                          patient.inferred_governorate ||
                          "Governorate pending"}
                      </p>
                    </div>
                    <div className="activity-meta">
                      <small>{formatDateTime(patient.created_at)}</small>
                    </div>
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h4>Recent doctors</h4>
              <div className="activity-list compact">
                {recentDoctors.slice(0, 3).map((doctor) => (
                  <article key={doctor.id} className="activity-item">
                    <div>
                      <strong>{doctor.full_name}</strong>
                      <p>{doctor.specialty}</p>
                    </div>
                    <div className="activity-meta">
                      <small>{formatDateTime(doctor.created_at)}</small>
                    </div>
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h4>Recent appointments</h4>
              <div className="activity-list compact">
                {recentAppointments.slice(0, 3).map((appointment) => (
                  <article key={appointment.id} className="activity-item">
                    <div>
                      <strong>{appointment.reason}</strong>
                      <p>{appointmentStatusLabel(appointment.status)}</p>
                    </div>
                    <div className="activity-meta">
                      <small>{formatDateTime(appointment.requested_at)}</small>
                    </div>
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h4>Recent visits</h4>
              <div className="activity-list compact">
                {recentVisits.slice(0, 3).map((visit) => (
                  <article key={visit.id} className="activity-item">
                    <div>
                      <strong>{visit.diagnosis || "Visit note"}</strong>
                      <p>{summarize(visit.symptoms)}</p>
                    </div>
                    <div className="activity-meta">
                      <small>{formatDateTime(visit.created_at)}</small>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => onNavigate("appointments")}
            >
              View all appointments
            </button>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => onNavigate("profile")}
            >
              View all profiles
            </button>
          </div>
        </section>

        <section className="workspace-card">
          <div className="workspace-card__header">
            <div>
              <p className="micro-label">Workspace status</p>
              <h3>System readiness</h3>
            </div>
          </div>
          <div className="status-grid">
            <article className="status-card">
              <span>Backend connection</span>
              <strong>Connected</strong>
              <p>The frontend is currently operating against the live API workspace.</p>
            </article>
            <article className="status-card">
              <span>Doctor dataset</span>
              <strong>{doctors.length >= 80 ? "Seed target reached" : "Seed target pending"}</strong>
              <p>
                {doctors.length} doctors currently available for matching and booking
                handoff.
              </p>
            </article>
            <article className="status-card">
              <span>Coverage review</span>
              <strong>{weakCoverage.length === 0 ? "Balanced" : "Needs follow-up"}</strong>
              <p>
                {weakCoverage.length === 0
                  ? "No required specialty is currently uncovered."
                  : `Review these specialties next: ${weakCoverage.slice(0, 4).join(", ")}.`}
              </p>
            </article>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function OverviewPanel({
  role,
  patientProfile,
  doctorProfile,
  appointments,
  patients,
  visits,
  recentVisits,
  doctors,
  triageResult,
  onNavigate,
}: OverviewPanelProps) {
  if (role === "patient") {
    return (
      <PatientOverview
        patientProfile={patientProfile}
        appointments={appointments}
        visits={visits}
        doctors={doctors}
        triageResult={triageResult}
        onNavigate={onNavigate}
      />
    );
  }

  if (role === "doctor") {
    return (
      <DoctorOverview
        doctorProfile={doctorProfile}
        appointments={appointments}
        patients={patients}
        recentVisits={recentVisits}
        onNavigate={onNavigate}
      />
    );
  }

  return (
    <AdminOverview
      appointments={appointments}
      patients={patients}
      doctors={doctors}
      recentVisits={recentVisits}
      onNavigate={onNavigate}
    />
  );
}
