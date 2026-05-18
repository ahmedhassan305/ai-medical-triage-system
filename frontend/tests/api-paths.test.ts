import { describe, expect, it } from "vitest";

import { API_V1_PREFIX, apiPaths } from "../src/api/paths";

describe("api paths", () => {
  it("uses versioned triage path", () => {
    expect(apiPaths.triage).toBe("/api/v1/triage");
    expect(apiPaths.triage.startsWith(API_V1_PREFIX)).toBe(true);
  });

  it("exposes crm routes under the versioned prefix", () => {
    expect(apiPaths.auth.login).toBe("/api/v1/auth/login");
    expect(apiPaths.patients.list).toBe("/api/v1/patients/");
    expect(apiPaths.doctors.list).toBe("/api/v1/doctors/");
    expect(apiPaths.doctors.slots(7)).toBe("/api/v1/doctors/7/slots");
    expect(apiPaths.appointments.create).toBe("/api/v1/appointments/");
    expect(apiPaths.visits.list).toBe("/api/v1/visits/");
    expect(apiPaths.records.import).toBe("/api/v1/records/import");
  });
});
