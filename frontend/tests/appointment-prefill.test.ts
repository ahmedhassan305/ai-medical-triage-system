import { describe, expect, it } from "vitest";

import { buildAppointmentPrefill } from "../src/lib/appointmentPrefill";

describe("buildAppointmentPrefill", () => {
  it("creates a ready-to-book handoff payload from a recommended doctor", () => {
    const prefill = buildAppointmentPrefill(
      {
        id: 12,
        full_name: "Dr. Mariam Adel",
        specialty: "Neurology",
      },
      "I hit my head and now have a severe headache with nausea",
      "Neurology",
    );

    expect(prefill.doctorId).toBe(12);
    expect(prefill.doctorName).toBe("Dr. Mariam Adel");
    expect(prefill.specialty).toBe("Neurology");
    expect(prefill.reason).toContain("Triage follow-up for Neurology");
    expect(prefill.reason).toContain("severe headache");
    expect(prefill.notes).toContain("Specialty focus: Neurology");
  });

  it("falls back to the doctor specialty when the triage specialty is missing", () => {
    const prefill = buildAppointmentPrefill(
      {
        id: 7,
        full_name: "Dr. Ahmed Samir",
        specialty: "Pulmonology",
      },
      "Shortness of breath and wheezing",
    );

    expect(prefill.specialty).toBe("Pulmonology");
    expect(prefill.reason).toContain("Pulmonology");
  });
});
