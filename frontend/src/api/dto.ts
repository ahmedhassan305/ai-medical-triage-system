export type RoleType = "patient" | "doctor" | "admin";
export type TriageLevel = "low" | "medium" | "high";

export type RegisterRequestDto = {
  email: string;
  password: string;
  role: RoleType;
  full_name?: string;
  national_id?: string;
  sex?: "Male" | "Female";
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
  sex: "Male" | "Female";
  national_id?: string | null;
  current_governorate?: string | null;
  smoker: boolean;
  alcoholic: boolean;
  chronic_conditions: string[];
};

export type PatientProfileResponseDto = PatientProfileUpsertDto & {
  id: number;
  user_id: number | null;
  date_of_birth?: string | null;
  inferred_governorate_code?: string | null;
  inferred_governorate?: string | null;
  created_at: string;
  updated_at: string;
};

export type ManagedPatientProfileCreateDto = {
  full_name: string;
  sex: "Male" | "Female";
  national_id: string;
  current_governorate?: string | null;
  smoker: boolean;
  alcoholic: boolean;
  chronic_conditions: string[];
};

export type DoctorProfileUpsertDto = {
  full_name: string;
  specialty: string;
  clinic: string;
  area?: string | null;
  city?: string | null;
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

export type DoctorSuggestionDto = {
  id: number;
  full_name: string;
  specialty: string;
  clinic: string;
  area?: string | null;
  city?: string | null;
  booking_url?: string | null;
  source_url?: string | null;
  source_name?: string | null;
};

export type ClarificationQuestionDto = {
  id: string;
  question: string;
  options: string[] | null;
};

export type ClarificationAnswerDto = {
  question_id: string;
  answer: string;
};

export type SupportingReferenceDto = {
  title: string;
  source: string;
  url?: string | null;
  snippet: string;
};

export type SuspectedConditionDto = {
  name: string;
  likelihood: "more likely" | "more_likely" | "possible" | "less likely" | "less_likely";
  explanation: string;
};

export type TriageResponseDto = {
  triage_level: TriageLevel;
  urgency_level: TriageLevel;
  confidence_score: number;
  needs_clarification: boolean;
  questions: ClarificationQuestionDto[];
  urgency_label: string;
  urgency_reason: string;
  summary: string;
  clinical_summary: string;
  actions: string[];
  recommended_actions: string[];
  red_flags: string[];
  disclaimer: string;
  history_used: boolean;
  simple_reasoning?: string;
  plain_language_explanation?: string;
  patient_friendly_explanation: string;
  recommended_specialty?: string;
  specialty_reason: string;
  suspected_condition?: string;
  suspected_conditions: SuspectedConditionDto[];
  supporting_references: SupportingReferenceDto[];
  suggested_doctors: DoctorSuggestionDto[];
};
