export const API_V1_PREFIX = "/api/v1";

export const apiPaths = {
  health: `${API_V1_PREFIX}/health`,
  triage: `${API_V1_PREFIX}/triage`,
  labPdfExtract: `${API_V1_PREFIX}/triage/lab-pdf/extract`,
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
    medicalHistory: (patientId: number) =>
      `${API_V1_PREFIX}/patients/${patientId}/medical-history`,
  },
  doctors: {
    list: `${API_V1_PREFIX}/doctors/`,
    me: `${API_V1_PREFIX}/doctors/me`,
    byId: (doctorId: number) => `${API_V1_PREFIX}/doctors/${doctorId}`,
    reviews: `${API_V1_PREFIX}/doctors/reviews`,
    doctorReviews: (doctorId: number) =>
      `${API_V1_PREFIX}/doctors/${doctorId}/reviews`,
    rating: (doctorId: number) => `${API_V1_PREFIX}/doctors/${doctorId}/rating`,
    slots: (doctorId: number) => `${API_V1_PREFIX}/doctors/${doctorId}/slots`,
    schedules: (doctorId: number) =>
      `${API_V1_PREFIX}/doctors/${doctorId}/schedules`,
    schedule: (doctorId: number, scheduleId: number) =>
      `${API_V1_PREFIX}/doctors/${doctorId}/schedules/${scheduleId}`,
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
