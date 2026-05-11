import type { AppointmentResponseDto } from "../api/dto";
import type { AppointmentStatus, AppointmentStatusGroup } from "./appointmentStatus";
import {
  normalizeBackendStatus,
  isActiveOrUpcoming,
  isCompleted,
  isRejectedOrCancelled,
  isPending,
} from "./appointmentStatus";

/**
 * Extended appointment with normalized status
 */
export type AppointmentWithStatus = AppointmentResponseDto & {
  normalizedStatus: AppointmentStatus;
};

/**
 * Convert a backend appointment response to include normalized status
 */
export function normalizeAppointment(
  appointment: AppointmentResponseDto,
): AppointmentWithStatus {
  return {
    ...appointment,
    normalizedStatus: normalizeBackendStatus(
      appointment.status,
      appointment.scheduled_for,
    ),
  };
}

/**
 * Normalize a list of appointments
 */
export function normalizeAppointments(
  appointments: AppointmentResponseDto[],
): AppointmentWithStatus[] {
  return appointments.map(normalizeAppointment);
}

/**
 * Group appointments by normalized status
 *
 * @example
 * const grouped = groupAppointmentsByStatus(appointments);
 * // {
 * //   active_upcoming: [...],
 * //   pending: [...],
 * //   completed: [...],
 * //   rejected_cancelled: [...]
 * // }
 */
export function groupAppointmentsByStatus(
  appointments: AppointmentWithStatus[],
): Record<AppointmentStatusGroup, AppointmentWithStatus[]> {
  return {
    active_upcoming: appointments.filter((apt) =>
      isActiveOrUpcoming(apt.normalizedStatus),
    ),
    pending: appointments.filter((apt) => isPending(apt.normalizedStatus)),
    completed: appointments.filter((apt) =>
      isCompleted(apt.normalizedStatus),
    ),
    rejected_cancelled: appointments.filter((apt) =>
      isRejectedOrCancelled(apt.normalizedStatus),
    ),
  };
}

/**
 * Filter appointments by status group
 */
export function filterAppointmentsByStatusGroup(
  appointments: AppointmentWithStatus[],
  group: AppointmentStatusGroup,
): AppointmentWithStatus[] {
  switch (group) {
    case "active_upcoming":
      return appointments.filter((apt) =>
        isActiveOrUpcoming(apt.normalizedStatus),
      );
    case "pending":
      return appointments.filter((apt) => isPending(apt.normalizedStatus));
    case "completed":
      return appointments.filter((apt) => isCompleted(apt.normalizedStatus));
    case "rejected_cancelled":
      return appointments.filter((apt) =>
        isRejectedOrCancelled(apt.normalizedStatus),
      );
    default:
      return appointments;
  }
}

/**
 * Filter appointments by specific status
 */
export function filterAppointmentsByStatus(
  appointments: AppointmentWithStatus[],
  status: AppointmentStatus,
): AppointmentWithStatus[] {
  return appointments.filter((apt) => apt.normalizedStatus === status);
}

/**
 * Sort appointments by date (most recent first, then by requested date)
 */
export function sortAppointmentsByDate(
  appointments: AppointmentWithStatus[],
  order: "asc" | "desc" = "desc",
): AppointmentWithStatus[] {
  return [...appointments].sort((a, b) => {
    const dateA = new Date(
      a.scheduled_for || a.requested_at,
    ).getTime();
    const dateB = new Date(
      b.scheduled_for || b.requested_at,
    ).getTime();

    return order === "desc" ? dateB - dateA : dateA - dateB;
  });
}

/**
 * Sort appointments by status group order
 * Order: active_upcoming → pending → completed → rejected_cancelled
 */
export function sortAppointmentsByStatusGroup(
  appointments: AppointmentWithStatus[],
): AppointmentWithStatus[] {
  const groupOrder: Record<AppointmentStatusGroup, number> = {
    active_upcoming: 0,
    pending: 1,
    completed: 2,
    rejected_cancelled: 3,
  };

  const statusToGroup = (status: AppointmentStatus): AppointmentStatusGroup => {
    if (isActiveOrUpcoming(status)) return "active_upcoming";
    if (isPending(status)) return "pending";
    if (isCompleted(status)) return "completed";
    return "rejected_cancelled";
  };

  return [...appointments].sort((a, b) => {
    const groupA = statusToGroup(a.normalizedStatus);
    const groupB = statusToGroup(b.normalizedStatus);
    return groupOrder[groupA] - groupOrder[groupB];
  });
}

/**
 * Search appointments by doctor or patient name, or reason
 */
export function searchAppointments(
  appointments: AppointmentWithStatus[],
  doctors: Record<number, { full_name: string; specialty: string }>,
  patients: Record<number, { full_name: string; national_id?: string | null }>,
  query: string,
): AppointmentWithStatus[] {
  const lowerQuery = query.toLowerCase().trim();

  if (!lowerQuery) {
    return appointments;
  }

  return appointments.filter((apt) => {
    const doctor = doctors[apt.doctor_id];
    const patient = patients[apt.patient_id];

    const doctorName = doctor?.full_name.toLowerCase() || "";
    const specialty = doctor?.specialty.toLowerCase() || "";
    const patientName = patient?.full_name.toLowerCase() || "";
    const patientNationalId = patient?.national_id?.toLowerCase() || "";
    const reason = apt.reason.toLowerCase() || "";

    return (
      doctorName.includes(lowerQuery) ||
      specialty.includes(lowerQuery) ||
      patientName.includes(lowerQuery) ||
      patientNationalId.includes(lowerQuery) ||
      reason.includes(lowerQuery)
    );
  });
}

/**
 * Get summary statistics for appointments
 */
export type AppointmentStats = {
  total: number;
  activeUpcoming: number;
  pending: number;
  completed: number;
  rejectedCancelled: number;
};

export function getAppointmentStats(
  appointments: AppointmentWithStatus[],
): AppointmentStats {
  return {
    total: appointments.length,
    activeUpcoming: appointments.filter((apt) =>
      isActiveOrUpcoming(apt.normalizedStatus),
    ).length,
    pending: appointments.filter((apt) => isPending(apt.normalizedStatus))
      .length,
    completed: appointments.filter((apt) =>
      isCompleted(apt.normalizedStatus),
    ).length,
    rejectedCancelled: appointments.filter((apt) =>
      isRejectedOrCancelled(apt.normalizedStatus),
    ).length,
  };
}
