export const API_V1_PREFIX = "/api/v1";

export const apiPaths = {
  health: `${API_V1_PREFIX}/health`,
  triage: `${API_V1_PREFIX}/triage`,
  clarify: `${API_V1_PREFIX}/clarify`,
  auth: {
    register: `${API_V1_PREFIX}/auth/register`,
    login: `${API_V1_PREFIX}/auth/login`,
    me: `${API_V1_PREFIX}/auth/me`,
  },
  patients: {
    list: `${API_V1_PREFIX}/patients/`,
    create: `${API_V1_PREFIX}/patients/`,
    me: `${API_V1_PREFIX}/patients/me`,
    byNationalId: (nationalId: string) =>
      `${API_V1_PREFIX}/patients/by-national-id/${nationalId}`,
    byId: (patientId: number) => `${API_V1_PREFIX}/patients/${patientId}`,
  },
  doctors: {
    list: `${API_V1_PREFIX}/doctors/`,
    me: `${API_V1_PREFIX}/doctors/me`,
    byId: (doctorId: number) => `${API_V1_PREFIX}/doctors/${doctorId}`,
  },
  appointments: {
    list: `${API_V1_PREFIX}/appointments/`,
    create: `${API_V1_PREFIX}/appointments/`,
    status: (appointmentId: number) =>
      `${API_V1_PREFIX}/appointments/${appointmentId}/status`,
  },
  visits: {
    create: `${API_V1_PREFIX}/visits/`,
    list: `${API_V1_PREFIX}/visits/`,
    byPatient: (patientId: number) => `${API_V1_PREFIX}/visits/patient/${patientId}`,
  },
  records: {
    import: `${API_V1_PREFIX}/records/import`,
  },
} as const;
