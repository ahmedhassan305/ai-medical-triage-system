import type { AppointmentStatus } from "../../lib/appointmentStatus";
import { getStatusDisplay } from "../../lib/appointmentStatus";

type StatusBadgeProps = {
  status: AppointmentStatus;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  showDescription?: boolean;
  className?: string;
};

/**
 * StatusBadge - Color-coded badge component for appointment status
 *
 * Displays appointment status with semantic colors, icons, and optional descriptions.
 * Uses Tailwind CSS for styling and adapts to different sizes.
 *
 * @example
 * <StatusBadge status={AppointmentStatus.ACTIVE} />
 * <StatusBadge status={AppointmentStatus.PENDING} size="lg" showIcon showDescription />
 */
export function StatusBadge({
  status,
  size = "md",
  showIcon = true,
  showDescription = false,
  className = "",
}: StatusBadgeProps) {
  const displayInfo = getStatusDisplay(status);
  const { label, description, colors, icon } = displayInfo;

  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  };

  const baseClasses =
    "inline-flex items-center gap-1 font-medium rounded-full border transition-colors duration-200";

  return (
    <div
      className={`${baseClasses} ${sizeClasses[size]} ${colors.background} ${colors.text} ${colors.border} ${className}`}
      role="status"
      aria-label={label}
      title={description}
    >
      {showIcon && <span className="flex-shrink-0">{icon}</span>}
      <span className="flex-1">{label}</span>
    </div>
  );
}

type StatusIndicatorProps = {
  status: AppointmentStatus;
  inline?: boolean;
  className?: string;
};

/**
 * StatusIndicator - Minimal status indicator (just icon + text)
 *
 * Lightweight version of StatusBadge for use in tables, lists, and compact layouts.
 *
 * @example
 * <StatusIndicator status={AppointmentStatus.COMPLETED} />
 */
export function StatusIndicator({
  status,
  inline = true,
  className = "",
}: StatusIndicatorProps) {
  const displayInfo = getStatusDisplay(status);
  const { label, colors, icon } = displayInfo;

  const containerClass = inline ? "inline-flex" : "flex";

  return (
    <span
      className={`${containerClass} items-center gap-1 ${colors.text} ${className}`}
      title={displayInfo.description}
    >
      <span>{icon}</span>
      <span className="font-medium">{label}</span>
    </span>
  );
}

type StatusGroupHeaderProps = {
  groupLabel: string;
  count: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  className?: string;
};

/**
 * StatusGroupHeader - Header for grouped appointment sections
 *
 * Used to organize appointments by status group with optional expand/collapse.
 *
 * @example
 * <StatusGroupHeader groupLabel="Upcoming & Active" count={3} />
 */
export function StatusGroupHeader({
  groupLabel,
  count,
  isExpanded = true,
  onToggle,
  className = "",
}: StatusGroupHeaderProps) {
  return (
    <div
      className={`flex items-center gap-3 py-3 px-4 bg-gray-50 border-b border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors ${className}`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && onToggle) {
          onToggle();
        }
      }}
    >
      {onToggle && (
        <span className={`text-gray-600 transform transition-transform ${isExpanded ? "rotate-90" : ""}`}>
          ▶
        </span>
      )}
      <h3 className="text-sm font-semibold text-gray-700 flex-1">{groupLabel}</h3>
      <span className="bg-gray-200 text-gray-700 px-2.5 py-0.5 rounded-full text-xs font-semibold">
        {count}
      </span>
    </div>
  );
}
