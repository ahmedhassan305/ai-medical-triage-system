/**
 * Appointment Status System - Type Exports Index
 *
 * Central export file for all types and interfaces.
 * Import from here for convenience:
 *
 * import type { AppointmentStatus, StatusDisplayInfo } from '../lib/types';
 */

// ============================================================================
// Status Types
// ============================================================================

export type { StatusColorScheme, StatusDisplayInfo } from '../lib/appointmentStatus';
export { AppointmentStatus } from '../lib/appointmentStatus';

// ============================================================================
// Status Group Types
// ============================================================================

export type { AppointmentStatusGroup } from '../lib/appointmentStatus';

// ============================================================================
// Appointment Types
// ============================================================================

export type {
  AppointmentWithStatus,
  AppointmentStats,
} from '../lib/appointmentFilters';

// ============================================================================
// Component Props Types
// ============================================================================

export type { StatusBadgeProps, StatusIndicatorProps, StatusGroupHeaderProps } from '../components/StatusBadge';

export type {
  AppointmentListProps,
} from '../components/AppointmentList';

// ============================================================================
// Re-export Common Functions
// ============================================================================

export {
  // Status display
  normalizeBackendStatus,
  getStatusDisplay,
  // Status checks
  isActiveOrUpcoming,
  isCompleted,
  isRejectedOrCancelled,
  isPending,
} from '../lib/appointmentStatus';

export {
  // Normalization
  normalizeAppointment,
  normalizeAppointments,
  // Grouping
  groupAppointmentsByStatus,
  // Filtering
  filterAppointmentsByStatusGroup,
  filterAppointmentsByStatus,
  // Sorting
  sortAppointmentsByDate,
  sortAppointmentsByStatusGroup,
  // Search
  searchAppointments,
  // Statistics
  getAppointmentStats,
} from '../lib/appointmentFilters';

export {
  // Status checks for actions
  canApproveAppointment,
  canRejectAppointment,
  canCancelAppointment,
  canRescheduleAppointment,
  getAppointmentActionLabel,
} from '../lib/appointmentPanelIntegration';
