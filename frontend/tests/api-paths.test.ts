import { describe, expect, it } from "vitest";

import { API_V1_PREFIX, apiPaths } from "../src/api/paths";

describe("api paths", () => {
  it("uses versioned triage path", () => {
    expect(apiPaths.triage).toBe("/api/v1/triage");
    expect(apiPaths.triageHistory).toBe("/api/v1/triage/history");
    expect(apiPaths.triageDetail(42)).toBe("/api/v1/triage/42");
    expect(apiPaths.triage.startsWith(API_V1_PREFIX)).toBe(true);
  });

  it("exposes crm routes under the versioned prefix", () => {
    expect(apiPaths.auth.login).toBe("/api/v1/auth/login");
    expect(apiPaths.patients.list).toBe("/api/v1/patients/");
    expect(apiPaths.doctors.list).toBe("/api/v1/doctors/");
    expect(apiPaths.appointments.create).toBe("/api/v1/appointments/");
    expect(apiPaths.records.import).toBe("/api/v1/records/import");
  });
});
