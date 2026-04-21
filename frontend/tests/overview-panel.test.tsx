import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  TriageResponseDto,
  VisitResponseDto,
} from "../src/api/dto";
import OverviewPanel from "../src/components/OverviewPanel";

const baseAppointment: AppointmentResponseDto = {
  id: 1,
  patient_id: 10,
  doctor_id: 20,
  status: "requested",
  reason: "Neurology review",
  notes: "Needs follow-up",
  requested_at: "2026-04-21T10:00:00Z",
  scheduled_for: null,
};

const patientProfile: PatientProfileResponseDto = {
  id: 10,
  user_id: 100,
  full_name: "Live Patient",
  age: 25,
  sex: "Female",
  national_id: "30101010112345",
  current_governorate: "Alexandria",
  smoker: false,
  alcoholic: false,
  chronic_conditions: ["Asthma"],
  date_of_birth: "2001-01-01",
  inferred_governorate_code: "03",
  inferred_governorate: "Alexandria",
  created_at: "2026-04-21T10:00:00Z",
  updated_at: "2026-04-21T10:00:00Z",
};

const doctorProfile: DoctorProfileResponseDto = {
  id: 20,
  user_id: 200,
  full_name: "Operational Doctor",
  specialty: "Neurology",
  clinic: "Operational Neurology Clinic",
  area: "Smouha",
  city: "Alexandria",
  source_name: "Vezeeta public directory",
  source_url: "https://www.vezeeta.com/example-doctor",
  booking_url: "https://www.vezeeta.com/example-doctor",
  created_at: "2026-04-21T10:00:00Z",
  updated_at: "2026-04-21T10:00:00Z",
};

const visit: VisitResponseDto = {
  id: 30,
  patient_id: 10,
  doctor_id: 20,
  symptoms: "Head injury with nausea",
  diagnosis: "Urgent neurological assessment recommended",
  notes: "Needs imaging.",
  prescriptions: null,
  vitals: null,
  attachments: null,
  created_at: "2026-04-21T10:30:00Z",
};

const triageResult: TriageResponseDto = {
  triage_level: "high",
  urgency_level: "high",
  urgency_label: "Emergency assessment needed now",
  urgency_reason:
    "Recent head trauma followed by severe headache and nausea or vomiting raises concern for concussion or intracranial bleeding.",
  summary: "This could be a serious head injury rather than a stomach problem.",
  clinical_summary:
    "Recent head trauma followed by severe headache and nausea or vomiting raises concern for concussion or intracranial bleeding.",
  patient_friendly_explanation:
    "Because you recently injured your head and now have severe headache with nausea or vomiting, this could be a serious head injury rather than a stomach problem.",
  actions: ["Go to the emergency department now for urgent brain injury assessment."],
  recommended_actions: [
    "Go to the emergency department now for urgent brain injury assessment.",
  ],
  red_flags: ["Recent head injury with severe headache, vomiting, or drowsiness"],
  disclaimer:
    "This is not a diagnosis. Because your symptoms may be urgent, seek emergency care now or contact local emergency services.",
  history_used: true,
  simple_reasoning: "Head injury red flags need urgent assessment.",
  plain_language_explanation:
    "This could be a serious head injury rather than a stomach problem.",
  recommended_specialty: "Neurology",
  specialty_reason:
    "The symptom combination contains warning signs that are safest under neurology review.",
  suspected_condition: "Intracranial hematoma",
  suspected_conditions: [
    {
      name: "Intracranial hematoma",
      likelihood: "more_likely",
      explanation:
        "Red-flag symptom combination makes this condition important to exclude.",
    },
  ],
  suggested_doctors: [
    {
      id: 20,
      full_name: "Operational Doctor",
      specialty: "Neurology",
      clinic: "Operational Neurology Clinic",
      area: "Smouha",
      city: "Alexandria",
      source_name: "Vezeeta public directory",
      source_url: "https://www.vezeeta.com/example-doctor",
      booking_url: "https://www.vezeeta.com/example-doctor",
    },
  ],
  supporting_references: [
    {
      title: "Intracranial hematoma",
      source: "Mayo Clinic",
      url: "https://example.com/reference",
      snippet:
        "Head injury followed by vomiting and severe headache needs urgent assessment.",
    },
  ],
};

describe("OverviewPanel", () => {
  it("renders a patient care workspace with next-step guidance", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="patient"
        patientProfile={patientProfile}
        doctorProfile={null}
        appointments={[{ ...baseAppointment, status: "approved" }]}
        patients={[]}
        visits={[visit]}
        recentVisits={[]}
        doctors={[doctorProfile]}
        triageResult={triageResult}
        onNavigate={vi.fn()}
      />,
    );

    expect(markup).toContain("My care space");
    expect(markup).toContain("Next appointment");
    expect(markup).toContain("Latest triage");
    expect(markup).toContain("What do you want to do next?");
    expect(markup).toContain("Continue to booking");
  });

  it("renders patient empty states when no care activity exists yet", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="patient"
        patientProfile={patientProfile}
        doctorProfile={null}
        appointments={[]}
        patients={[]}
        visits={[]}
        recentVisits={[]}
        doctors={[]}
        triageResult={null}
        onNavigate={vi.fn()}
      />,
    );

    expect(markup).toContain("No appointment booked yet");
    expect(markup).toContain("No triage result yet.");
    expect(markup).toContain("No visit records are linked to your profile yet.");
  });

  it("renders doctor setup-required state when profile is missing", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="doctor"
        patientProfile={null}
        doctorProfile={null}
        appointments={[]}
        patients={[patientProfile]}
        visits={[]}
        recentVisits={[]}
        doctors={[]}
        triageResult={null}
        onNavigate={vi.fn()}
      />,
    );

    expect(markup).toContain("Complete your doctor profile");
    expect(markup).toContain("Doctor setup actions");
    expect(markup).toContain("Scheduling activates after profile setup");
  });

  it("renders admin control-center sections and coverage analysis", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="admin"
        patientProfile={null}
        doctorProfile={null}
        appointments={[
          baseAppointment,
          { ...baseAppointment, id: 2, status: "approved", doctor_id: 21 },
        ]}
        patients={[patientProfile]}
        visits={[]}
        recentVisits={[visit]}
        doctors={[
          doctorProfile,
          {
            ...doctorProfile,
            id: 21,
            specialty: "Psychiatry",
            full_name: "Seeded Psychiatrist",
          },
        ]}
        triageResult={null}
        onNavigate={vi.fn()}
      />,
    );

    expect(markup).toContain("Admin control center");
    expect(markup).toContain("Top operational metrics");
    expect(markup).toContain("Specialty coverage");
    expect(markup).toContain("Most requested specialties");
    expect(markup).toContain("Doctor import workflow");
  });
});
