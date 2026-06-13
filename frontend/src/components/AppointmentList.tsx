import { useMemo, useState } from "react";

import type {
  AppointmentResponseDto,
  DoctorProfileResponseDto,
  PatientProfileResponseDto,
} from "../api/dto";
import {
  getAppointmentStats,
  groupAppointmentsByStatus,
  normalizeAppointments,
  searchAppointments,
  sortAppointmentsByDate,
  type AppointmentWithStatus,
} from "../lib/appointmentFilters";
import type { AppointmentStatusGroup } from "../lib/appointmentStatus";
import CustomSelect from "./CustomSelect";
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
    expandedGroups: new Set([
      "active_upcoming",
      "pending",
    ] as AppointmentStatusGroup[]),
  });

  const normalizedAppointments = useMemo(
    () => normalizeAppointments(appointments),
    [appointments],
  );

  const doctorMap = useMemo(
    () => Object.fromEntries(doctors.map((doc) => [doc.id, doc])),
    [doctors],
  );

  const patientMap = useMemo(
    () => Object.fromEntries(patients.map((pat) => [pat.id, pat])),
    [patients],
  );

  const filteredAndSearched = useMemo(() => {
    let result = normalizedAppointments;

    if (filter.statusGroup !== "all") {
      const grouped = groupAppointmentsByStatus(result);
      result = grouped[filter.statusGroup];
    }

    if (filter.searchQuery) {
      result = searchAppointments(
        result,
        doctorMap,
        patientMap,
        filter.searchQuery,
      );
    }

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
  }, [
    normalizedAppointments,
    filter,
    doctorMap,
    patientMap,
    currentRole,
    currentUserId,
  ]);

  const groupedAppointments = useMemo(
    () => groupAppointmentsByStatus(filteredAndSearched),
    [filteredAndSearched],
  );

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
    <div className="appointment-list">
      <div className="appointment-list__toolbar">
        <div className="appointment-list__search">
          <input
            type="text"
            placeholder="Search by doctor, specialty, patient, national ID, or reason..."
            value={filter.searchQuery}
            onChange={(e) =>
              setFilter({ ...filter, searchQuery: e.target.value })
            }
          />
        </div>
        <CustomSelect
          className="appointment-list__filter"
          value={filter.statusGroup}
          onChange={(e) =>
            setFilter({
              ...filter,
              statusGroup: e as FilterState["statusGroup"],
            })
          }
          options={[
            { value: "all", label: "All Status" },
            { value: "active_upcoming", label: "Active & Upcoming" },
            { value: "pending", label: "Pending" },
            { value: "completed", label: "Completed" },
            { value: "rejected_cancelled", label: "Rejected/Cancelled" },
          ]}
        />
      </div>

      <div className="appointment-stats">
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

      <div className="appointment-list__groups">
        <AppointmentGroup
          title="Active & Upcoming"
          appointments={groupedAppointments.active_upcoming}
          isExpanded={filter.expandedGroups.has("active_upcoming")}
          onToggle={() => toggleGroup("active_upcoming")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />
        <AppointmentGroup
          title="Pending Approval"
          appointments={groupedAppointments.pending}
          isExpanded={filter.expandedGroups.has("pending")}
          onToggle={() => toggleGroup("pending")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />
        <AppointmentGroup
          title="Completed"
          appointments={groupedAppointments.completed}
          isExpanded={filter.expandedGroups.has("completed")}
          onToggle={() => toggleGroup("completed")}
          doctorMap={doctorMap}
          patientMap={patientMap}
          currentRole={currentRole}
        />
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

      {filteredAndSearched.length === 0 && (
        <div className="appointment-list__empty">
          <p>
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
    <div className="appointment-group">
      <StatusGroupHeader
        groupLabel={title}
        count={appointments.length}
        isExpanded={isExpanded}
        onToggle={onToggle}
      />

      {isExpanded && (
        <div className="appointment-group__rows">
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
    <div className="appointment-row">
      <div className="appointment-row__body">
        <div className="appointment-row__header">
          <div className="appointment-row__identity">
            <p className="appointment-row__name">
              {currentRole === "patient" || !patient
                ? `Dr. ${doctor?.full_name || "Unknown"}`
                : patient.full_name}
            </p>
            <p className="appointment-row__meta">
              {doctor?.specialty && (
                <>
                  {doctor.specialty}
                  {doctor.clinic && ` - ${doctor.clinic}`}
                </>
              )}
            </p>
          </div>
          <StatusBadge status={appointment.normalizedStatus} size="sm" />
        </div>

        <div className="appointment-row__reason">
          <span>Reason:</span> {appointment.reason}
        </div>

        <div className="appointment-row__details">
          {scheduledDate && (
            <span>
              Scheduled: <strong>{scheduledDate}</strong>
            </span>
          )}
          <span>
            Requested: <strong>{requestedDate}</strong>
          </span>
          {appointment.clinic?.name && <span>{appointment.clinic.name}</span>}
        </div>

        {appointment.notes && (
          <div className="appointment-row__notes">
            <span>Notes:</span> {appointment.notes}
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
    <div className={`appointment-stat ${highlight ? "is-highlighted" : ""}`}>
      <p className="appointment-stat__value">{value}</p>
      <p className="appointment-stat__label">{label}</p>
    </div>
  );
}

export default AppointmentList;
