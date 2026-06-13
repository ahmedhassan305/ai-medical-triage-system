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

export type ManagedPatientProfileCreateDto = {
  full_name: string;
  sex: "Male" | "Female";
  national_id: string;
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
  department_id?: number | null;
  rating?: number | null;
  review_count?: number;
  source_name?: string | null;
  source_url?: string | null;
  booking_url?: string | null;
  created_at: string;
  updated_at: string;
};

export type ClinicDto = {
  id: number;
  name: string;
  area?: string | null;
  city?: string | null;
  address?: string | null;
  is_active?: boolean;
};

export type AppointmentSlotDto = {
  id: number;
  doctor_clinic_id: number;
  schedule_id?: number | null;
  start_at: string;
  end_at: string;
  status: string;
  clinic?: ClinicDto | null;
};

export type AppointmentCreateDto = {
  patient_id: number;
  doctor_id?: number | null;
  reason: string;
  notes?: string | null;
  scheduled_for?: string | null;
  clinic_id?: number | null;
  slot_id?: number | null;
};

export type AppointmentStatusUpdateDto = {
  status: "approved" | "rejected";
  notes?: string | null;
};

export type AppointmentResponseDto = AppointmentCreateDto & {
  id: number;
  doctor_id: number;
  clinic_id?: number | null;
  status: string;
  requested_at: string;
  slot?: AppointmentSlotDto | null;
  clinic?: ClinicDto | null;
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
  lab_values?: LabValueDto[];
  language?: "en" | "ar";
};

export type DoctorScheduleDto = {
  id: number;
  doctor_id: number;
  doctor_clinic_id?: number | null;
  day_of_week: string;
  start_time: string;
  end_time: string;
  slot_minutes: number;
  valid_from?: string | null;
  valid_to?: string | null;
  location_label?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type DoctorScheduleCreateDto = Omit<
  DoctorScheduleDto,
  "id" | "doctor_id" | "created_at" | "updated_at"
>;

export type PatientMedicalHistoryEntryCreateDto = {
  category: string;
  title: string;
  occurred_on?: string | null;
  status?: string | null;
  notes?: string | null;
};

export type PatientMedicalHistoryEntryResponseDto =
  PatientMedicalHistoryEntryCreateDto & {
    id: number;
    patient_id: number;
    created_at: string;
    updated_at: string;
  };

export type LabValueDto = {
  lab_name: string;
  value: string;
  unit?: string | null;
  reference_range?: string | null;
};

export type LabPdfExtractionResponseDto = {
  filename: string;
  values: LabValueDto[];
  warning: string;
};

export type DoctorSuggestionDto = {
  id: number;
  full_name: string;
  specialty: string;
  clinic: string;
  clinic_id?: number | null;
  area?: string | null;
  city?: string | null;
  earliest_available_slot?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  booking_url?: string | null;
  rating?: number | null;
  review_count?: number;
  recommendation_reason?: string | null;
  distance_km?: number | null;
  specialty_match_reason?: string | null;
};

export type DoctorReviewCreateDto = {
  doctor_id: number;
  rating: number;
  comment?: string | null;
  appointment_id?: number | null;
  visit_id?: number | null;
};

export type DoctorReviewResponseDto = DoctorReviewCreateDto & {
  id: number;
  patient_id: number;
  appointment_id?: number | null;
  visit_id?: number | null;
  created_at: string;
  updated_at: string;
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
  likelihood:
    | "more_likely"
    | "more likely"
    | "possible"
    | "less_likely"
    | "less likely";
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
  simple_reasoning?: string;
  plain_language_explanation?: string;
  patient_friendly_explanation: string;
  actions: string[];
  recommended_actions: string[];
  red_flags: string[];
  recommended_specialty?: string | null;
  specialty_reason: string;
  suspected_condition?: string | null;
  suspected_conditions: SuspectedConditionDto[];
  supporting_references: SupportingReferenceDto[];
  suggested_doctors: DoctorSuggestionDto[];
  disclaimer: string;
  history_used: boolean;
};
