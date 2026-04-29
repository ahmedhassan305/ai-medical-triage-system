import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  PatientProfileResponseDto,
  TriageResponseDto,
  VisitResponseDto,
} from "../src/api/dto";
import AppointmentsPanel from "../src/components/AppointmentsPanel";
import TriagePanel from "../src/components/TriagePanel";

const triageResult: TriageResponseDto = {
  triage_level: "high",
  urgency_level: "high",
  urgency_label: "Emergency assessment needed now",
  urgency_reason: "Recent head trauma followed by severe headache and nausea or vomiting raises concern for concussion or intracranial bleeding.",
  summary: "This could be a serious head injury rather than a stomach problem.",
  clinical_summary: "Recent head trauma followed by severe headache and nausea or vomiting raises concern for concussion or intracranial bleeding.",
  patient_friendly_explanation: "Because you recently injured your head and now have severe headache with nausea or vomiting, this could be a serious head injury rather than a stomach problem. You should get urgent medical assessment now.",
  actions: ["Go to the emergency department now for urgent brain injury assessment."],
  recommended_actions: ["Go to the emergency department now for urgent brain injury assessment."],
  red_flags: ["Recent head injury with severe headache, vomiting, or drowsiness"],
  disclaimer: "This is not a diagnosis. Because your symptoms may be urgent, seek emergency care now or contact local emergency services.",
  history_used: true,
  simple_reasoning: "Head injury red flags need urgent assessment.",
  plain_language_explanation: "This could be a serious head injury rather than a stomach problem.",
  recommended_specialty: "Neurology",
  specialty_reason: "The symptom combination contains warning signs that are safest under neurology review.",
  suspected_condition: "Intracranial hematoma",
  suspected_conditions: [
    {
      name: "Intracranial hematoma",
      likelihood: "more_likely",
      explanation: "Red-flag symptom combination makes this condition important to exclude.",
    },
  ],
  suggested_doctors: [
    {
      id: 5,
      full_name: "hesham elhenawy",
      specialty: "Neurology",
      clinic: "Senior Consultant in Neurological Diseases",
      area: "Sidy Bishr",
      city: "Alexandria",
      source_name: "Vezeeta public directory",
      source_url: "https://example.com/neurology",
      booking_url: "https://example.com/neurology",
    },
  ],
  supporting_references: [
    {
      title: "Intracranial hematoma",
      source: "Mayo Clinic",
      url: "https://example.com/reference",
      snippet: "Head injury followed by vomiting and severe headache needs urgent assessment.",
    },
  ],
};

describe("triage handoff rendering", () => {
  it("renders reserve appointment action for suggested doctors", () => {
    const linkedPatient: PatientProfileResponseDto = {
      id: 10,
      user_id: null,
      full_name: "Mariam Hassan",
      age: 24,
      sex: "Female",
      national_id: "30101010212345",
      current_governorate: "Alexandria",
      smoker: false,
      alcoholic: false,
      chronic_conditions: ["Asthma"],
      date_of_birth: "2001-01-01",
      inferred_governorate_code: "02",
      inferred_governorate: "Alexandria",
      created_at: "2026-04-21T10:00:00Z",
      updated_at: "2026-04-21T10:00:00Z",
    };
    const latestVisit: VisitResponseDto = {
      id: 99,
      patient_id: 10,
      doctor_id: 5,
      symptoms: "Severe headache after head injury",
      diagnosis: "Observation for concussion",
      notes: "Recent head trauma requires follow-up.",
      prescriptions: null,
      vitals: null,
      attachments: null,
      created_at: "2026-04-20T15:00:00Z",
    };

    const markup = renderToStaticMarkup(
      <TriagePanel
        role="doctor"
        loading={false}
        error={null}
        result={triageResult}
        patientProfile={null}
        linkedPatient={linkedPatient}
        linkedPatientLatestVisit={latestVisit}
        patientLookupNationalId="30101010212345"
        patientLookupLoading={false}
        patientLookupError={null}
        patientCreateLoading={false}
        patientCreateError={null}
        query="head injury"
        onQueryChange={vi.fn()}
        onLookupNationalIdChange={vi.fn()}
        onLookupPatient={vi.fn(async () => {})}
        onClearLinkedPatient={vi.fn()}
        onCreatePatientProfile={vi.fn(() => Promise.resolve())}
        onSubmit={vi.fn()}
        onReserveAppointment={vi.fn()}
      />,
    );

    expect(markup).toContain("Reserve Appointment");
    expect(markup).toContain("Supporting medical references");
    expect(markup).toContain("Possible conditions");
    expect(markup).toContain("Matched patient");
    expect(markup).toContain("Latest visit summary");
  });

  it("renders prefilled appointment banner", () => {
    const markup = renderToStaticMarkup(
      <AppointmentsPanel
        role="patient"
        doctors={[
          {
            id: 5,
            user_id: null,
            full_name: "hesham elhenawy",
            specialty: "Neurology",
            clinic: "Senior Consultant in Neurological Diseases",
            area: "Sidy Bishr",
            city: "Alexandria",
            source_name: "Vezeeta public directory",
            source_url: "https://example.com/neurology",
            booking_url: "https://example.com/neurology",
            created_at: "2026-04-21T10:00:00Z",
            updated_at: "2026-04-21T10:00:00Z",
          },
        ]}
        patients={[]}
        currentPatientId={10}
        appointments={[]}
        loading={false}
        error={null}
        onCreate={vi.fn(async () => {})}
        onUpdateStatus={vi.fn(async () => {})}
        preFill={{
          doctorId: 5,
          doctorName: "hesham elhenawy",
          specialty: "Neurology",
          reason: "head injury",
          notes: "Triage suggested Neurology. Because you recently injured your head...",
        }}
        onClearPreFill={vi.fn()}
      />,
    );

    expect(markup).toContain("Ready from triage");
    expect(markup).toContain("hesham elhenawy");
    expect(markup).toContain("Preselected from the triage recommendation");
  });
});
