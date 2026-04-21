import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
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
  current_governorate: "Cairo",
  smoker: false,
  alcoholic: false,
  chronic_conditions: ["Asthma"],
  date_of_birth: "2001-01-01",
  inferred_governorate_code: "01",
  inferred_governorate: "Cairo",
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
  source_name: null,
  source_url: null,
  booking_url: null,
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

describe("OverviewPanel", () => {
  it("renders patient-specific overview content", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="patient"
        patientProfile={patientProfile}
        doctorProfile={null}
        appointments={[{ ...baseAppointment, status: "approved" }]}
        patients={[]}
        visits={[visit]}
        doctors={[]}
      />,
    );

    expect(markup).toContain("Your appointments");
    expect(markup).toContain("Recent medical history");
    expect(markup).toContain("Recommended actions");
  });

  it("renders doctor-specific operational overview", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="doctor"
        patientProfile={null}
        doctorProfile={doctorProfile}
        appointments={[baseAppointment, { ...baseAppointment, id: 2, status: "approved" }]}
        patients={[patientProfile]}
        visits={[]}
        doctors={[]}
      />,
    );

    expect(markup).toContain("Upcoming appointments");
    expect(markup).toContain("Appointment requests awaiting review");
    expect(markup).toContain("Operational Doctor");
  });

  it("renders admin-specific operational metrics", () => {
    const markup = renderToStaticMarkup(
      <OverviewPanel
        role="admin"
        patientProfile={null}
        doctorProfile={null}
        appointments={[baseAppointment, { ...baseAppointment, id: 2, status: "approved" }]}
        patients={[patientProfile]}
        visits={[]}
        doctors={[doctorProfile, { ...doctorProfile, id: 21, specialty: "Psychiatry", full_name: "Seeded Psychiatrist" }]}
      />,
    );

    expect(markup).toContain("Operational metrics");
    expect(markup).toContain("Doctor specialties available");
    expect(markup).toContain("Quick actions");
  });
});
