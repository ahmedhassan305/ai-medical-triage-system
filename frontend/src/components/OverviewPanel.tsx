import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  RoleType,
  VisitResponseDto,
} from "../api/dto";
import SectionPanel from "./SectionPanel";

type OverviewPanelProps = {
  role: RoleType;
  patientProfile: PatientProfileResponseDto | null;
  doctorProfile: DoctorProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
  visits: VisitResponseDto[];
  doctors: DoctorProfileResponseDto[];
};

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

function PatientOverview({
  patientProfile,
  appointments,
  visits,
}: {
  patientProfile: PatientProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  visits: VisitResponseDto[];
}) {
  const upcomingAppointments = appointments
    .filter((apt) => apt.status === "approved")
    .sort(
      (a, b) =>
        new Date(b.requested_at).getTime() -
        new Date(a.requested_at).getTime()
    )
    .slice(0, 2);

  const pendingRequests = appointments
    .filter((apt) => apt.status === "requested")
    .length;

  const lastVisit = visits.length > 0 ? visits[0] : null;

  return (
    <div className="stack-lg">
      {patientProfile ? (
        <>
          <SectionPanel
            eyebrow="Your appointments"
            title="Upcoming and pending"
            description="View your scheduled appointments and booking requests."
          >
            <div className="metric-grid">
              <article className="metric-card">
                <span>Confirmed appointments</span>
                <strong>{upcomingAppointments.length}</strong>
              </article>
              <article className="metric-card">
                <span>Pending requests</span>
                <strong>{pendingRequests}</strong>
              </article>
              <article className="metric-card">
                <span>Total appointments</span>
                <strong>{appointments.length}</strong>
              </article>
            </div>

            {upcomingAppointments.length > 0 ? (
              <div className="stack-md">
                <p className="micro-label">Confirmed appointments</p>
                {upcomingAppointments.map((apt) => (
                  <article key={apt.id} className="entity-card">
                    <div className="entity-card__header">
                      <div>
                        <h4>Appointment #{apt.id}</h4>
                        <p>{apt.reason}</p>
                      </div>
                      <span className={`badge badge--status-${apt.status}`}>
                        {apt.status}
                      </span>
                    </div>
                    <p className="muted-copy">
                      Requested: {formatDate(apt.requested_at)}
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="callout">
                <p>
                  No confirmed appointments yet. Use triage to get doctor
                  recommendations, then book an appointment.
                </p>
              </div>
            )}
          </SectionPanel>

          {lastVisit ? (
            <SectionPanel
              eyebrow="Latest visit"
              title="Recent medical history"
              description="Your most recent consultation."
            >
              <div className="entity-card">
                <p className="micro-label">Symptoms reported</p>
                <p>{lastVisit.symptoms}</p>
                {lastVisit.diagnosis && (
                  <>
                    <p className="micro-label">Diagnosis</p>
                    <p>{lastVisit.diagnosis}</p>
                  </>
                )}
                {lastVisit.notes && (
                  <>
                    <p className="micro-label">Notes</p>
                    <p>{lastVisit.notes}</p>
                  </>
                )}
                <p className="muted-copy">
                  {formatDate(lastVisit.created_at)}
                </p>
              </div>
            </SectionPanel>
          ) : null}

          <SectionPanel
            eyebrow="Next steps"
            title="Recommended actions"
            description="Your triage insights and booking options."
          >
            <ul className="list">
              {appointments.length === 0 && (
                <li>
                  Run a triage assessment to get personalized doctor
                  recommendations
                </li>
              )}
              {pendingRequests > 0 && (
                <li>
                  You have {pendingRequests} pending appointment request
                  {pendingRequests !== 1 ? "s" : ""}
                </li>
              )}
              {visits.length === 0 && (
                <li>
                  Complete your profile with chronic conditions to enable
                  history-aware triage
                </li>
              )}
              {patientProfile.chronic_conditions.length === 0 && (
                <li>
                  Update your profile with chronic conditions for better
                  triage accuracy
                </li>
              )}
            </ul>
          </SectionPanel>
        </>
      ) : (
        <SectionPanel
          eyebrow="Patient profile"
          title="Setup required"
          description="You need to create your profile first."
        >
          <div className="callout">
            <p>
              Complete your patient profile to unlock triage, appointments, and
              visit history features.
            </p>
          </div>
        </SectionPanel>
      )}
    </div>
  );
}

function DoctorOverview({
  doctorProfile,
  appointments,
  patients,
}: {
  doctorProfile: DoctorProfileResponseDto | null;
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
}) {
  const todayAppointments = appointments
    .filter((apt) => apt.status === "approved")
    .slice(0, 3);

  const pendingRequests = appointments.filter(
    (apt) => apt.status === "requested"
  );

  const patientsCount = patients.length;

  return (
    <div className="stack-lg">
      {doctorProfile ? (
        <>
          <SectionPanel
            eyebrow="Your schedule"
            title="Upcoming appointments"
            description={`${doctorProfile.full_name} · ${doctorProfile.specialty} · ${doctorProfile.clinic}`}
          >
            <div className="metric-grid">
              <article className="metric-card">
                <span>Confirmed appointments</span>
                <strong>{todayAppointments.length}</strong>
              </article>
              <article className="metric-card">
                <span>Pending requests</span>
                <strong>{pendingRequests.length}</strong>
              </article>
              <article className="metric-card">
                <span>Total patients</span>
                <strong>{patientsCount}</strong>
              </article>
            </div>

            {todayAppointments.length > 0 ? (
              <div className="stack-md">
                <p className="micro-label">Next appointments</p>
                {todayAppointments.map((apt) => (
                  <article key={apt.id} className="entity-card">
                    <div className="entity-card__header">
                      <div>
                        <h4>Appointment #{apt.id}</h4>
                        <p className="muted-copy">
                          {patients.find((p) => p.id === apt.patient_id)
                            ?.full_name || "Patient " + apt.patient_id}
                        </p>
                      </div>
                      <span className={`badge badge--status-${apt.status}`}>
                        {apt.status}
                      </span>
                    </div>
                    <p>{apt.reason}</p>
                    <p className="muted-copy">
                      Requested: {formatDate(apt.requested_at)}
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="callout">
                <p>No confirmed appointments scheduled.</p>
              </div>
            )}
          </SectionPanel>

          {pendingRequests.length > 0 ? (
            <SectionPanel
              eyebrow="Pending"
              title="Appointment requests awaiting review"
              description="Review and approve or reject incoming appointment requests."
            >
              <div className="stack-md">
                {pendingRequests.map((apt) => (
                  <article key={apt.id} className="entity-card">
                    <div className="entity-card__header">
                      <div>
                        <h4>Request #{apt.id}</h4>
                        <p className="muted-copy">
                          {patients.find((p) => p.id === apt.patient_id)
                            ?.full_name || "Patient " + apt.patient_id}
                        </p>
                      </div>
                    </div>
                    <p>{apt.reason}</p>
                    <p className="muted-copy">
                      Requested: {formatDate(apt.requested_at)}
                    </p>
                  </article>
                ))}
              </div>
            </SectionPanel>
          ) : null}
        </>
      ) : (
        <SectionPanel
          eyebrow="Doctor profile"
          title="Setup required"
          description="You need to create your doctor profile first."
        >
          <div className="callout">
            <p>
              Complete your doctor profile to enable appointment scheduling and
              patient management.
            </p>
          </div>
        </SectionPanel>
      )}
    </div>
  );
}

function AdminOverview({
  appointments,
  patients,
  doctors,
}: {
  appointments: AppointmentResponseDto[];
  patients: PatientProfileResponseDto[];
  doctors: DoctorProfileResponseDto[];
}) {
  const appointmentsByStatus = {
    requested: appointments.filter((a) => a.status === "requested").length,
    approved: appointments.filter((a) => a.status === "approved").length,
    rejected: appointments.filter((a) => a.status === "rejected").length,
  };

  const specialtyCount: Record<string, number> = {};
  doctors.forEach((doctor) => {
    specialtyCount[doctor.specialty] =
      (specialtyCount[doctor.specialty] || 0) + 1;
  });

  const topSpecialties = Object.entries(specialtyCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="stack-lg">
      <SectionPanel
        eyebrow="System overview"
        title="Operational metrics"
        description="Key system metrics and resource allocation."
      >
        <div className="metric-grid">
          <article className="metric-card">
            <span>Total patients</span>
            <strong>{patients.length}</strong>
          </article>
          <article className="metric-card">
            <span>Total doctors</span>
            <strong>{doctors.length}</strong>
          </article>
          <article className="metric-card">
            <span>Total appointments</span>
            <strong>{appointments.length}</strong>
          </article>
          <article className="metric-card">
            <span>Pending requests</span>
            <strong>{appointmentsByStatus.requested}</strong>
          </article>
          <article className="metric-card">
            <span>Confirmed bookings</span>
            <strong>{appointmentsByStatus.approved}</strong>
          </article>
          <article className="metric-card">
            <span>Rejected</span>
            <strong>{appointmentsByStatus.rejected}</strong>
          </article>
        </div>
      </SectionPanel>

      {topSpecialties.length > 0 ? (
        <SectionPanel
          eyebrow="Coverage"
          title="Doctor specialties available"
          description="Distribution of doctor coverage by specialty."
        >
          <div className="stack-md">
            {topSpecialties.map(([specialty, count]) => (
              <article key={specialty} className="entity-card">
                <div className="entity-card__header">
                  <h4>{specialty}</h4>
                  <strong>{count} doctor{count !== 1 ? "s" : ""}</strong>
                </div>
              </article>
            ))}
          </div>
        </SectionPanel>
      ) : (
        <SectionPanel
          eyebrow="Coverage"
          title="Doctor specialties"
          description="No doctors registered yet."
        >
          <div className="callout">
            <p>
              Seed the doctor database with real medical professionals to
              enable appointment recommendations.
            </p>
          </div>
        </SectionPanel>
      )}

      <SectionPanel
        eyebrow="Management"
        title="Quick actions"
        description="Common administrative tasks."
      >
        <ul className="list">
          {appointmentsByStatus.requested > 0 && (
            <li>
              {appointmentsByStatus.requested} appointment request
              {appointmentsByStatus.requested !== 1 ? "s" : ""} pending
              approval
            </li>
          )}
          {patients.length === 0 && (
            <li>Invite patients to register and use the system</li>
          )}
          {doctors.length === 0 && (
            <li>Seed the doctor database with real medical professionals</li>
          )}
          {doctors.length > 0 &&
            topSpecialties.length > 0 &&
            topSpecialties[0][1] === 1 && <li>Consider adding more doctors for better coverage</li>}
        </ul>
      </SectionPanel>
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
  doctors,
}: OverviewPanelProps) {
  return (
    <>
      {role === "patient" && (
        <PatientOverview
          patientProfile={patientProfile}
          appointments={appointments}
          visits={visits}
        />
      )}

      {role === "doctor" && (
        <DoctorOverview
          doctorProfile={doctorProfile}
          appointments={appointments}
          patients={patients}
        />
      )}

      {role === "admin" && (
        <AdminOverview
          appointments={appointments}
          patients={patients}
          doctors={doctors}
        />
      )}
    </>
  );
}
