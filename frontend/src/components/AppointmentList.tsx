import { useState, useMemo } from "react";
import type { AppointmentResponseDto, DoctorProfileResponseDto, PatientProfileResponseDto } from "../api/dto";
import type { AppointmentStatusGroup } from "../lib/appointmentStatus";
import {
  normalizeAppointments,
  groupAppointmentsByStatus,
  sortAppointmentsByDate,
  searchAppointments,
  getAppointmentStats,
  type AppointmentWithStatus,
} from "../lib/appointmentFilters";
import { StatusBadge, StatusGroupHeader } from "./StatusBadge";

export type AppointmentListProps = {
  appointments: AppointmentResponseDto[];
  doctors: DoctorProfileResponseDto[];
  patients: PatientProfileResponseDto[];
  currentRole?: "patient" | "doctor" | "admin";
  currentUserId?: number;
};

type FilterState = {
  statusGroup: AppointmentStatusGroup | "all";
  searchQuery: string;
  expandedGroups: Set<AppointmentStatusGroup>;
};

/**
 * AppointmentList - Comprehensive appointment display component
 *
 * Features:
 * - Groups appointments by normalized status
 * - Color-coded status badges
 * - Search functionality
 * - Expandable/collapsible groups
 * - Role-aware display (shows relevant appointments based on user role)
 * - Summary statistics
 *
 * @example
 * <AppointmentList
 *   appointments={appointments}
 *   doctors={doctors}
 *   patients={patients}
 *   currentRole="doctor"
 *   currentUserId={42}
 * />
 */
export function AppointmentList({
  appointments,
  doctors,
  patients,
  currentRole,
  currentUserId,
}: AppointmentListProps) {
  const [filter, setFilter] = useState<FilterState>({
    statusGroup: "all",
    searchQuery: "",
    expandedGroups: new Set(["active_upcoming", "pending"] as AppointmentStatusGroup[]),
  });

  // Normalize appointments
  const normalizedAppointments = useMemo(
    () => normalizeAppointments(appointments),
    [appointments],
  );

  // Create lookup maps for fast access
  const doctorMap = useMemo(
    () =>
      Object.fromEntries(doctors.map((doc) => [doc.id, doc])),
    [doctors],
  );

  const patientMap = useMemo(
    () =>
      Object.fromEntries(patients.map((pat) => [pat.id, pat])),
    [patients],
  );

  // Apply filters
  const filteredAndSearched = useMemo(() => {
    let result = normalizedAppointments;

    // Filter by status group
    if (filter.statusGroup !== "all") {
      const grouped = groupAppointmentsByStatus(result);
      result = grouped[filter.statusGroup];
    }

    // Apply search
    if (filter.searchQuery) {
      result = searchAppointments(
        result,
        doctorMap,
        patientMap,
        filter.searchQuery,
      );
    }

    // Apply role-based filtering
    if (currentRole === "patient" && currentUserId) {
      result = result.filter((apt) => {
        const patient = patientMap[apt.patient_id];
        return patient?.user_id === currentUserId;
      });
    } else if (currentRole === "doctor" && currentUserId) {
      result = result.filter((apt) => {
        const doctor = doctorMap[apt.doctor_id];
        return doctor?.user_id === currentUserId;
      });
    }

    return sortAppointmentsByDate(result);
  }, [normalizedAppointments, filter, doctorMap, patientMap, currentRole, currentUserId]);

  // Group filtered results by status
  const groupedAppointments = useMemo(
    () => groupAppointmentsByStatus(filteredAndSearched),
    [filteredAndSearched],
  );

  // Calculate stats
  const stats = useMemo(
    () => getAppointmentStats(normalizedAppointments),
    [normalizedAppointments],
  );

  const toggleGroup = (group: AppointmentStatusGroup) => {
    const newGroups = new Set(filter.expandedGroups);
    if (newGroups.has(group)) {
      newGroups.delete(group);
    } else {
      newGroups.add(group);
    }
    setFilter({ ...filter, expandedGroups: newGroups });
  };

  return (
    <div className="space-y-4">
      {/* Header with search and filter */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by doctor, specialty, patient, or reason..."
            value={filter.searchQuery}
            onChange={(e) =>
              setFilter({ ...filter, searchQuery: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={filter.statusGroup}
          onChange={(e) =>
            setFilter({
              ...filter,
              statusGroup: e.target.value as FilterState["statusGroup"],
            })
          }
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Status</option>
          <option value="active_upcoming">Active & Upcoming</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="rejected_cancelled">Rejected/Cancelled</option>
        </select>
      </div>

      {/* Statistics bar */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <StatCard
          label="Total"
          value={stats.total}
          highlight={filter.statusGroup === "all"}
        />
        <StatCard
          label="Upcoming"
          value={stats.activeUpcoming}
          highlight={filter.statusGroup === "active_upcoming"}
        />
        <StatCard
          label="Pending"
          value={stats.pending}
          highlight={filter.statusGroup === "pending"}
        />
        <StatCard
          label="Completed"
          value={stats.completed}
          highlight={filter.statusGroup === "completed"}
        />
        <StatCard
          label="Rejected"
          value={stats.rejectedCancelled}
          highlight={filter.statusGroup === "rejected_cancelled"}
        />
      </div>

      {/* Appointments list */}
      <div className="space-y-2 rounded-lg border border-gray-200 overflow-hidden bg-white shadow-sm">
        {/* Active/Upcoming */}
        <AppointmentGroup
          title="Active & Upcoming"
          appointments={groupedAppointments.active_upcoming}
          isExpanded={filter.expandedGroups.has("active_upcoming")}
          onToggle={() => toggleGroup("active_upcoming")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />

        {/* Pending */}
        <AppointmentGroup
          title="Pending Approval"
          appointments={groupedAppointments.pending}
          isExpanded={filter.expandedGroups.has("pending")}
          onToggle={() => toggleGroup("pending")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />

        {/* Completed */}
        <AppointmentGroup
          title="Completed"
          appointments={groupedAppointments.completed}
          isExpanded={filter.expandedGroups.has("completed")}
          onToggle={() => toggleGroup("completed")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />

        {/* Rejected/Cancelled */}
        <AppointmentGroup
          title="Rejected & Cancelled"
          appointments={groupedAppointments.rejected_cancelled}
          isExpanded={filter.expandedGroups.has("rejected_cancelled")}
          onToggle={() => toggleGroup("rejected_cancelled")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />
      </div>

      {/* Empty state */}
      {filteredAndSearched.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          <p className="text-sm">
            {appointments.length === 0
              ? "No appointments yet"
              : "No appointments match your filters"}
          </p>
        </div>
      )}
    </div>
  );
}

type AppointmentGroupProps = {
  title: string;
  appointments: AppointmentWithStatus[];
  isExpanded: boolean;
  onToggle: () => void;
  doctorMap: Record<number, DoctorProfileResponseDto>;
  patientMap: Record<number, PatientProfileResponseDto>;
  currentRole?: "patient" | "doctor" | "admin";
};

function AppointmentGroup({
  title,
  appointments,
  isExpanded,
  onToggle,
  doctorMap,
  patientMap,
  currentRole,
}: AppointmentGroupProps) {
  return (
    <div className="border-b last:border-b-0 border-gray-200">
      <StatusGroupHeader
        groupLabel={title}
        count={appointments.length}
        isExpanded={isExpanded}
        onToggle={onToggle}
      />

      {isExpanded && (
        <div className="divide-y divide-gray-100">
          {appointments.map((apt) => (
            <AppointmentRow
              key={apt.id}
              appointment={apt}
              doctor={doctorMap[apt.doctor_id]}
              patient={patientMap[apt.patient_id]}
              currentRole={currentRole}
            />
          ))}
        </div>
      )}
    </div>
  );
}

type AppointmentRowProps = {
  appointment: AppointmentWithStatus;
  doctor?: DoctorProfileResponseDto;
  patient?: PatientProfileResponseDto;
  currentRole?: "patient" | "doctor" | "admin";
};

function AppointmentRow({
  appointment,
  doctor,
  patient,
  currentRole,
}: AppointmentRowProps) {
  const scheduledDate = appointment.scheduled_for
    ? new Date(appointment.scheduled_for).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  const requestedDate = new Date(appointment.requested_at).toLocaleDateString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    },
  );

  return (
    <div className="px-4 py-3 hover:bg-gray-50 transition-colors">
      <div className="flex flex-col gap-2">
        {/* Header: Status badge, Doctor, Patient */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-900">
              {currentRole === "patient" || !patient
                ? `Dr. ${doctor?.full_name || "Unknown"}`
                : patient.full_name}
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              {doctor?.specialty && (
                <>
                  {doctor.specialty}
                  {doctor.clinic && ` • ${doctor.clinic}`}
                </>
              )}
            </p>
          </div>
          <StatusBadge status={appointment.normalizedStatus} size="sm" />
        </div>

        {/* Reason */}
        <div className="text-sm text-gray-700">
          <span className="text-gray-600">Reason:</span> {appointment.reason}
        </div>

        {/* Dates and details */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
          {scheduledDate && (
            <span>📅 Scheduled: <span className="font-medium">{scheduledDate}</span></span>
          )}
          <span>Requested: <span className="font-medium">{requestedDate}</span></span>
          {appointment.clinic?.name && (
            <span>📍 {appointment.clinic.name}</span>
          )}
        </div>

        {/* Notes */}
        {appointment.notes && (
          <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded border border-gray-200">
            <span className="font-medium">Notes:</span> {appointment.notes}
          </div>
        )}
      </div>
    </div>
  );
}

type StatCardProps = {
  label: string;
  value: number;
  highlight?: boolean;
};

function StatCard({ label, value, highlight = false }: StatCardProps) {
  return (
    <div
      className={`p-2 rounded-lg text-center text-xs border transition-colors ${
        highlight
          ? "bg-blue-50 border-blue-300"
          : "bg-gray-50 border-gray-200"
      }`}
    >
      <p className="text-lg font-bold text-gray-900">{value}</p>
      <p className="text-gray-600 text-xs">{label}</p>
    </div>
  );
}

export default AppointmentList;
