import type { DoctorSuggestionDto } from "../api/dto";

export type AppointmentPrefill = {
  doctorId: number;
  doctorName: string;
  specialty: string;
  reason: string;
  notes: string;
};

export function buildAppointmentPrefill(
  doctor: Pick<DoctorSuggestionDto, "id" | "full_name" | "specialty">,
  triageQuery: string,
  recommendedSpecialty?: string | null,
): AppointmentPrefill {
  const specialty =
    recommendedSpecialty?.trim() || doctor.specialty.trim() || "General Practice";
  const normalizedQuery = triageQuery.trim().replace(/\s+/g, " ");
  const reason = normalizedQuery
    ? `Triage follow-up for ${specialty}: ${normalizedQuery}`
    : `Triage follow-up consultation for ${specialty}`;

  return {
    doctorId: doctor.id,
    doctorName: doctor.full_name,
    specialty,
    reason,
    notes: `Booked after AI triage recommendation. Specialty focus: ${specialty}.`,
  };
}
