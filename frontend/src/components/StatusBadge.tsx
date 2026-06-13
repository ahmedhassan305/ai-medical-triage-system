import type { AppointmentStatus } from "../lib/appointmentStatus";
import { getStatusDisplay } from "../lib/appointmentStatus";

export type StatusBadgeProps = {
  status: AppointmentStatus;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  showDescription?: boolean;
  className?: string;
};

/**
 * Displays appointment status with semantic colors, icons, and optional descriptions.
 */
export function StatusBadge({
  status,
  size = "md",
  showIcon = true,
  showDescription = false,
  className = "",
}: StatusBadgeProps) {
  const displayInfo = getStatusDisplay(status);
  const { label, description, colors } = displayInfo;
  const { icon } = colors;

  return (
    <div
      className={`status-badge status-badge--${status} status-badge--${size} ${className}`}
      role="status"
      aria-label={label}
      title={description}
    >
      {showIcon && <span className="status-badge__icon">{icon}</span>}
      <span className="status-badge__label">{label}</span>
      {showDescription && (
        <span className="status-badge__description">{description}</span>
      )}
    </div>
  );
}

export type StatusIndicatorProps = {
  status: AppointmentStatus;
  inline?: boolean;
  className?: string;
};

/**
 * Lightweight status indicator for compact layouts.
 */
export function StatusIndicator({
  status,
  inline = true,
  className = "",
}: StatusIndicatorProps) {
  const displayInfo = getStatusDisplay(status);
  const { label, colors } = displayInfo;
  const { icon } = colors;

  return (
    <span
      className={`status-indicator ${
        inline ? "status-indicator--inline" : ""
      } status-indicator--${status} ${className}`}
      title={displayInfo.description}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  );
}

export type StatusGroupHeaderProps = {
  groupLabel: string;
  count: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  className?: string;
};

/**
 * Header for grouped appointment sections.
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
      className={`status-group-header ${className}`}
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
        <span
          className={`status-group-header__chevron ${
            isExpanded ? "is-open" : ""
          }`}
        >
          &#9654;
        </span>
      )}
      <h3>{groupLabel}</h3>
      <span className="status-group-header__count">{count}</span>
    </div>
  );
}
