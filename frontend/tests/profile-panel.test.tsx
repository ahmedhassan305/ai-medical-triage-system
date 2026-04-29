import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
  VisitResponseDto,
} from "../src/api/dto";
import ProfilePanel from "../src/components/ProfilePanel";

const patient: PatientProfileResponseDto = {
  id: 1,
  user_id: 10,
  full_name: "Mariam Hassan",
  age: 26,
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

const doctor: DoctorProfileResponseDto = {
  id: 2,
  user_id: 20,
  full_name: "Dr. Mona Adel",
  specialty: "Cardiology · Heart failure and preventive cardiology",
  clinic: "Alexandria Heart Center",
  area: "Smouha",
  city: "Alexandria",
  source_name: "Vezeeta public directory",
  source_url: "https://example.com/doctor",
  booking_url: "https://example.com/doctor",
  created_at: "2026-04-21T10:00:00Z",
  updated_at: "2026-04-21T10:00:00Z",
};

const appointment: AppointmentResponseDto = {
  id: 1,
  patient_id: 1,
  doctor_id: 2,
  status: "approved",
  reason: "Follow-up review",
  notes: null,
  requested_at: "2026-04-21T10:00:00Z",
  scheduled_for: "2026-04-22T10:00:00Z",
};

const visit: VisitResponseDto = {
  id: 9,
  patient_id: 1,
  doctor_id: 2,
  symptoms: "Chest pain",
  diagnosis: "Stable angina follow-up",
  notes: "Continue the current plan and review in clinic.",
  prescriptions: "Continue aspirin and beta blocker.",
  vitals: null,
  attachments: null,
  created_at: "2026-04-20T10:00:00Z",
};

describe("ProfilePanel", () => {
  it("renders admin operations instead of patient demographics form", () => {
    const markup = renderToStaticMarkup(
      <ProfilePanel
        role="admin"
        patientProfile={null}
        doctorProfile={null}
        savingPatient={false}
        savingDoctor={false}
        patients={[patient]}
        doctors={[doctor]}
        appointments={[appointment]}
        recentVisits={[visit]}
        onNavigate={vi.fn()}
        onSavePatient={vi.fn(async () => {})}
        onSaveDoctor={vi.fn(async () => {})}
      />,
    );

    expect(markup).toContain("Operational records center");
    expect(markup).toContain("Review appointments");
    expect(markup).not.toContain("Egyptian national ID");
  });

  it("renders structured doctor specialty selection", () => {
    const markup = renderToStaticMarkup(
      <ProfilePanel
        role="doctor"
        patientProfile={null}
        doctorProfile={doctor}
        savingPatient={false}
        savingDoctor={false}
        patients={[patient]}
        doctors={[doctor]}
        appointments={[appointment]}
        recentVisits={[visit]}
        onNavigate={vi.fn()}
        onSavePatient={vi.fn(async () => {})}
        onSaveDoctor={vi.fn(async () => {})}
      />,
    );

    expect(markup).toContain("Doctor profile");
    expect(markup).toContain("Primary specialty");
    expect(markup).toContain("Specific scope (optional)");
  });
});
