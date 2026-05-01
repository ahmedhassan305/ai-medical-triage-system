/**
 * Appointment Status Management
 *
 * This module provides type-safe appointment status handling with color-coding,
 * grouping, and filtering capabilities. The status states are designed to cover
 * the complete lifecycle of an appointment.
 *
 * NOTE: Backend API may return status as `requested`, `approved`, `completed`, or `rejected`.
 * This module provides normalized, user-friendly status names and grouping logic.
 */

/**
 * Normalized appointment status types
 * These represent the complete lifecycle of an appointment
 */
export enum AppointmentStatus {
  // Upcoming/Active States
  PENDING = "pending", // Requested, awaiting doctor approval
  ACTIVE = "active", // Approved and scheduled for future date
  UPCOMING = "upcoming", // Scheduled appointment coming soon (alias for active)

  // Completed States
  COMPLETED = "completed", // Visited/consulted

  // Rejected/Cancelled States
  REJECTED = "rejected", // Doctor rejected the request
  CANCELLED = "cancelled", // User/admin cancelled the appointment
}

/**
 * Status group types for filtering and organization
 */
export type AppointmentStatusGroup =
  | "active_upcoming"
  | "pending"
  | "completed"
  | "rejected_cancelled";

/**
 * Color scheme for status badges
 * Uses accessible, semantic colors
 */
export type StatusColorScheme = {
  background: string; // Tailwind bg class
  text: string; // Tailwind text color class
  border: string; // Tailwind border color class
  icon: string; // Icon type or character
};

/**
 * Display information for a status
 */
export type StatusDisplayInfo = {
  label: string;
  description: string;
  colors: StatusColorScheme;
  group: AppointmentStatusGroup;
};

/**
 * Map of status to display information
 */
export const STATUS_DISPLAY_MAP: Record<
  AppointmentStatus,
  StatusDisplayInfo
> = {
  [AppointmentStatus.PENDING]: {
    label: "Pending",
    description: "Awaiting doctor approval",
    colors: {
      background: "bg-blue-100",
      text: "text-blue-900",
      border: "border-blue-300",
      icon: "⏳",
    },
    group: "pending",
  },
  [AppointmentStatus.ACTIVE]: {
    label: "Active",
    description: "Confirmed and upcoming",
    colors: {
      background: "bg-green-100",
      text: "text-green-900",
      border: "border-green-300",
      icon: "✓",
    },
    group: "active_upcoming",
  },
  [AppointmentStatus.UPCOMING]: {
    label: "Upcoming",
    description: "Scheduled appointment coming soon",
    colors: {
      background: "bg-green-100",
      text: "text-green-900",
      border: "border-green-300",
      icon: "📅",
    },
    group: "active_upcoming",
  },
  [AppointmentStatus.COMPLETED]: {
    label: "Completed",
    description: "Appointment finished",
    colors: {
      background: "bg-gray-100",
      text: "text-gray-700",
      border: "border-gray-300",
      icon: "✔️",
    },
    group: "completed",
  },
  [AppointmentStatus.REJECTED]: {
    label: "Rejected",
    description: "Doctor rejected the request",
    colors: {
      background: "bg-red-100",
      text: "text-red-900",
      border: "border-red-300",
      icon: "✗",
    },
    group: "rejected_cancelled",
  },
  [AppointmentStatus.CANCELLED]: {
    label: "Cancelled",
    description: "Appointment cancelled",
    colors: {
      background: "bg-orange-100",
      text: "text-orange-900",
      border: "border-orange-300",
      icon: "⊘",
    },
    group: "rejected_cancelled",
  },
};

/**
 * Normalize backend status strings to our appointment status enum
 *
 * @param backendStatus - Status string from backend API
 * @param scheduledFor - Optional scheduled date to determine if it's upcoming
 * @returns Normalized AppointmentStatus
 */
export function normalizeBackendStatus(
  backendStatus: string | undefined,
  scheduledFor?: string | null,
): AppointmentStatus {
  if (!backendStatus) {
    return AppointmentStatus.PENDING;
  }

  const lower = backendStatus.toLowerCase().trim();

  switch (lower) {
    case "requested":
      return AppointmentStatus.PENDING;
    case "approved":
      // Check if it's in the past (completed) or future (active/upcoming)
      if (scheduledFor) {
        const scheduled = new Date(scheduledFor);
        return scheduled < new Date()
          ? AppointmentStatus.COMPLETED
          : AppointmentStatus.ACTIVE;
      }
      return AppointmentStatus.ACTIVE;
    case "completed":
      return AppointmentStatus.COMPLETED;
    case "rejected":
      return AppointmentStatus.REJECTED;
    case "cancelled":
      return AppointmentStatus.CANCELLED;
    default:
      return AppointmentStatus.PENDING;
  }
}

/**
 * Get display information for a normalized status
 */
export function getStatusDisplay(
  status: AppointmentStatus,
): StatusDisplayInfo {
  return STATUS_DISPLAY_MAP[status];
}

/**
 * Check if a status represents an active/upcoming appointment
 */
export function isActiveOrUpcoming(status: AppointmentStatus): boolean {
  return status === AppointmentStatus.ACTIVE || status === AppointmentStatus.UPCOMING;
}

/**
 * Check if a status represents a completed appointment
 */
export function isCompleted(status: AppointmentStatus): boolean {
  return status === AppointmentStatus.COMPLETED;
}

/**
 * Check if a status represents a rejected/cancelled appointment
 */
export function isRejectedOrCancelled(status: AppointmentStatus): boolean {
  return (
    status === AppointmentStatus.REJECTED || status === AppointmentStatus.CANCELLED
  );
}

/**
 * Check if a status is pending approval
 */
export function isPending(status: AppointmentStatus): boolean {
  return status === AppointmentStatus.PENDING;
}
