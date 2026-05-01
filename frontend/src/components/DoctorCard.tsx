import type { DoctorSuggestionDto } from "../api/dto";

type DoctorCardProps = {
  doctor: DoctorSuggestionDto;
  specialty: string;
  patientLocation: string | null;
  onReserveAppointment?: () => void;
};

function formatSlot(slot?: string | null): string {
  if (!slot) {
    return "Availability not listed";
  }

  const date = new Date(slot);
  if (Number.isNaN(date.getTime())) {
    return slot;
  }

  return date.toLocaleString("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDistance(distanceKm?: number | null): string {
  if (typeof distanceKm !== "number") {
    return "Not calculated";
  }

  return `${distanceKm.toFixed(distanceKm < 10 ? 1 : 0)} km away`;
}

export default function DoctorCard({
  doctor,
  specialty,
  patientLocation,
  onReserveAppointment,
}: DoctorCardProps) {
  const location = [doctor.area, doctor.city].filter(Boolean).join(", ");
  const recommendation =
    doctor.recommendation_reason || doctor.specialty_match_reason;

  return (
    <article className="doctor-suggestion-card">
      <div className="doctor-suggestion-card__header">
        <div>
          <p className="micro-label">{doctor.specialty || specialty}</p>
          <h3>{doctor.full_name}</h3>
          <p className="muted-copy">
            {doctor.clinic}
            {location ? ` · ${location}` : ""}
          </p>
        </div>
        {typeof doctor.rating === "number" ? (
          <span className="badge badge--neutral">
            {doctor.rating.toFixed(1)} rating
          </span>
        ) : null}
      </div>

      <div className="detail-list">
        <div>
          <span>Earliest slot</span>
          <strong>{formatSlot(doctor.earliest_available_slot)}</strong>
        </div>
        <div>
          <span>{patientLocation ? `From ${patientLocation}` : "Distance"}</span>
          <strong>{formatDistance(doctor.distance_km)}</strong>
        </div>
      </div>

      {recommendation ? <p className="muted-copy">{recommendation}</p> : null}

      <div className="doctor-suggestion-card__actions">
        <div>
          {doctor.source_name ? (
            <p className="muted-copy">Source: {doctor.source_name}</p>
          ) : null}
          {doctor.source_url ? (
            <a href={doctor.source_url} target="_blank" rel="noreferrer">
              View profile
            </a>
          ) : null}
        </div>

        {onReserveAppointment ? (
          <button
            type="button"
            className="button button--primary"
            onClick={onReserveAppointment}
          >
            Reserve appointment
          </button>
        ) : doctor.booking_url ? (
          <a
            className="button button--primary"
            href={doctor.booking_url}
            target="_blank"
            rel="noreferrer"
          >
            Open booking
          </a>
        ) : null}
      </div>
    </article>
  );
}
