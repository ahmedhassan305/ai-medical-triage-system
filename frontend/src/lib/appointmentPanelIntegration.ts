/**
 * AppointmentPanel Integration Utilities
 *
 * This module provides utilities for integrating the new appointment status
 * system into the existing AppointmentsPanel component.
 *
 * It maintains backward compatibility while adding new features.
 */

import type { AppointmentResponseDto } from "../api/dto";
import { AppointmentStatus, normalizeBackendStatus } from "./appointmentStatus";

/**
 * Helper to convert AppointmentPanel's status update payload to new format
 *
 * Used when onUpdateStatus is called from AppointmentsPanel
 */
export function convertStatusUpdatePayload(
  backendStatus: "approved" | "rejected",
  notes?: string,
): {
  status: AppointmentStatus;
  notes?: string;
} {
  const normalizedStatus =
    backendStatus === "approved"
      ? AppointmentStatus.ACTIVE
      : AppointmentStatus.REJECTED;

  return {
    status: normalizedStatus,
    notes,
  };
}

/**
 * Check if user can perform certain actions based on appointment status
 */
export function canApproveAppointment(appointment: AppointmentResponseDto): boolean {
  const status = normalizeBackendStatus(appointment.status, appointment.scheduled_for);
  return status === AppointmentStatus.PENDING;
}

export function canRejectAppointment(appointment: AppointmentResponseDto): boolean {
  const status = normalizeBackendStatus(appointment.status, appointment.scheduled_for);
  return status === AppointmentStatus.PENDING;
}

export function canCancelAppointment(appointment: AppointmentResponseDto): boolean {
  const status = normalizeBackendStatus(appointment.status, appointment.scheduled_for);
  return (
    status === AppointmentStatus.ACTIVE ||
    status === AppointmentStatus.UPCOMING
  );
}

export function canRescheduleAppointment(appointment: AppointmentResponseDto): boolean {
  const status = normalizeBackendStatus(appointment.status, appointment.scheduled_for);
  return (
    status === AppointmentStatus.ACTIVE ||
    status === AppointmentStatus.UPCOMING
  );
}

/**
 * Get action label based on appointment status
 */
export function getAppointmentActionLabel(appointment: AppointmentResponseDto): string {
  const status = normalizeBackendStatus(appointment.status, appointment.scheduled_for);

  switch (status) {
    case AppointmentStatus.PENDING:
      return "Review";
    case AppointmentStatus.ACTIVE:
    case AppointmentStatus.UPCOMING:
      return "Manage";
    case AppointmentStatus.COMPLETED:
      return "View Details";
    case AppointmentStatus.REJECTED:
    case AppointmentStatus.CANCELLED:
      return "View";
    default:
      return "Actions";
  }
}
