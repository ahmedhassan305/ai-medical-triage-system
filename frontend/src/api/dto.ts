export type RoleType = "patient" | "doctor" | "admin";
export type TriageLevel = "low" | "medium" | "high";

export type RegisterRequestDto = {
  email: string;
  password: string;
  role: RoleType;
};

export type LoginRequestDto = {
  email: string;
  password: string;
};

export type UserResponseDto = {
  id: number;
  email: string;
  role: RoleType;
  created_at: string;
};

export type TokenResponseDto = {
  access_token: string;
  token_type: string;
  user_id: number;
  role: RoleType;
};

export type PatientProfileUpsertDto = {
  full_name: string;
  age: number;
  sex: string;
  smoker: boolean;
  alcoholic: boolean;
  chronic_conditions: string[];
};

export type PatientProfileResponseDto = PatientProfileUpsertDto & {
  id: number;
  user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type DoctorProfileUpsertDto = {
  full_name: string;
  specialty: string;
  clinic: string;
};

export type DoctorProfileResponseDto = DoctorProfileUpsertDto & {
  id: number;
  user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type AppointmentCreateDto = {
  patient_id: number;
  doctor_id: number;
  reason: string;
  notes?: string | null;
  scheduled_for?: string | null;
};

export type AppointmentStatusUpdateDto = {
  status: "approved" | "rejected";
  notes?: string | null;
};

export type AppointmentResponseDto = AppointmentCreateDto & {
  id: number;
  status: string;
  requested_at: string;
};

export type VisitCreateDto = {
  patient_id: number;
  doctor_id?: number | null;
  symptoms: string;
  vitals?: Record<string, string> | null;
  diagnosis?: string | null;
  notes?: string | null;
  prescriptions?: string | null;
  attachments?: string[] | null;
};

export type VisitResponseDto = VisitCreateDto & {
  id: number;
  created_at: string;
};

export type RecordsImportResultDto = {
  imported: number;
  patient_id: number;
};

export type TriageRequestDto = {
  query: string;
  patient_id?: number;
};

export type TriageResponseDto = {
  triage_level: TriageLevel;
  summary: string;
  actions: string[];
  disclaimer: string;
  history_used: boolean;
};
