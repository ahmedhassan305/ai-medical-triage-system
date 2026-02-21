import { describe, expect, it } from "vitest";

import { API_V1_PREFIX, apiPaths } from "../src/api/paths";

describe("api paths", () => {
  it("uses versioned triage path", () => {
    expect(apiPaths.triage).toBe("/api/v1/triage");
    expect(apiPaths.triage.startsWith(API_V1_PREFIX)).toBe(true);
  });
});
