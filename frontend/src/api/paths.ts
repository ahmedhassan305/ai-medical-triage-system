export const API_V1_PREFIX = "/api/v1";

export const apiPaths = {
  health: `${API_V1_PREFIX}/health`,
  triage: `${API_V1_PREFIX}/triage`,
} as const;
