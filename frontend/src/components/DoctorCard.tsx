import type { DoctorSuggestionDto } from "../api/dto";

type DoctorCardProps = {
  doctor: DoctorSuggestionDto;
  specialty: string;
  patientLocation?: string | null;
  onReserveAppointment?: () => void;
};

type RecommendationReason = {
  text: string;
  icon: string;
  type: "specialty" | "location" | "availability";
};

/**
 * Generates structured recommendation reasons based on doctor and patient data.
 * Returns concise, user-friendly reasons why this doctor was recommended.
 */
function getRecommendationReasons(
  doctor: DoctorSuggestionDto,
  specialty: string,
  patientLocation?: string | null,
): RecommendationReason[] {
  const reasons: RecommendationReason[] = [];

  // Specialty match
  if (doctor.specialty.toLowerCase() === specialty.toLowerCase()) {
    reasons.push({
      text: "Specialty matches your condition",
      icon: "✓",
      type: "specialty",
    });
  } else if (
    doctor.specialty.toLowerCase().includes(specialty.toLowerCase()) ||
    specialty.toLowerCase().includes(doctor.specialty.toLowerCase())
  ) {
    reasons.push({
      text: `Specializes in ${doctor.specialty}`,
      icon: "✓",
      type: "specialty",
    });
  }

  // Location proximity
  if (patientLocation) {
    if (doctor.area?.toLowerCase() === patientLocation.toLowerCase() ||
        doctor.city?.toLowerCase() === patientLocation.toLowerCase()) {
      reasons.push({
        text: "Near your location",
        icon: "📍",
        type: "location",
      });
    } else if (doctor.distance_km !== null && doctor.distance_km !== undefined) {
      if (doctor.distance_km <= 5) {
        reasons.push({
          text: "Very close to you",
          icon: "📍",
          type: "location",
        });
      } else if (doctor.distance_km <= 15) {
        reasons.push({
          text: `${doctor.distance_km.toFixed(1)} km away`,
          icon: "📍",
          type: "location",
        });
      }
    }
  } else if (
    doctor.area ||
    (doctor.distance_km !== null && doctor.distance_km !== undefined)
  ) {
    // If no patient location context, still show location is available
    reasons.push({
      text: "Location info available",
      icon: "📍",
      type: "location",
    });
  }

  // Earliest availability
  if (doctor.earliest_available_slot) {
    const slotDate = new Date(doctor.earliest_available_slot);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (slotDate.toDateString() === today.toDateString()) {
      reasons.push({
        text: "Available today",
        icon: "⏰",
        type: "availability",
      });
    } else if (slotDate.toDateString() === tomorrow.toDateString()) {
      reasons.push({
        text: "Available tomorrow",
        icon: "⏰",
        type: "availability",
      });
    } else {
      reasons.push({
        text: `Available soon`,
        icon: "⏰",
        type: "availability",
      });
    }
  }

  return reasons;
}

function RatingStars({
  rating,
  className,
}: {
  rating?: number | null;
  className?: string;
}) {
  if (!rating || rating < 0 || rating > 5) {
    return null;
  }

  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 !== 0;

  return (
    <div className={`doctor-card__rating ${className || ""}`}>
      <div className="rating-stars">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className={`star ${
              i < fullStars
                ? "star--full"
                : i === fullStars && hasHalfStar
                  ? "star--half"
                  : "star--empty"
            }`}
            aria-hidden="true"
          >
            ★
          </span>
        ))}
      </div>
      <span className="rating-value">{rating.toFixed(1)}</span>
    </div>
  );
}

function formatEarliestSlot(dateValue?: string | null): string | null {
  if (!dateValue) {
    return null;
  }
  try {
    const date = new Date(dateValue);
    return date.toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateValue;
  }
}

export default function DoctorCard({
  doctor,
  specialty,
  patientLocation,
  onReserveAppointment,
}: DoctorCardProps) {
  const reasons = getRecommendationReasons(doctor, specialty, patientLocation);
  return (
    <article className="doctor-card">
      {/* Header with doctor name and rating */}
      <div className="doctor-card__header">
        <div className="doctor-card__info">
          <h3 className="doctor-card__name">{doctor.full_name}</h3>
          <p className="doctor-card__specialty">{doctor.specialty}</p>
          <p className="doctor-card__clinic">{doctor.clinic}</p>
          {doctor.area && (
            <p className="doctor-card__location">
              {doctor.area}
              {doctor.city && `, ${doctor.city}`}
            </p>
          )}
        </div>
        <RatingStars rating={doctor.rating} />
      </div>

      {/* Why recommended section */}
      {reasons.length > 0 && (
        <div className="doctor-card__why-recommended">
          <p className="micro-label">Why recommended</p>
          <ul className="recommendation-reasons">
            {reasons.map((reason, idx) => (
              <li key={idx} className="recommendation-reason">
                <span className="reason-icon" aria-hidden="true">
                  {reason.icon}
                </span>
                <span className="reason-text">{reason.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation logic section */}
      <div className="doctor-card__recommendation-logic">
        <p className="micro-label">Match details</p>
        <div className="recommendation-items">
          {/* Specialty match */}
          <div className="recommendation-item">
            <span className="recommendation-item__label">Specialty:</span>
            <span className="recommendation-item__value">
              {specialty} match
              {doctor.specialty_match_reason && (
                <span className="recommendation-item__hint">
                  {" — "}
                  {doctor.specialty_match_reason}
                </span>
              )}
            </span>
          </div>

          {/* Location proximity */}
          {(doctor.distance_km !== null && doctor.distance_km !== undefined) ||
          doctor.area ? (
            <div className="recommendation-item">
              <span className="recommendation-item__label">Location:</span>
              <span className="recommendation-item__value">
                {doctor.distance_km !== null && doctor.distance_km !== undefined ? (
                  <>
                    {doctor.distance_km.toFixed(1)} km away
                    {patientLocation && (
                      <span className="recommendation-item__hint">
                        {" — from "}
                        {patientLocation}
                      </span>
                    )}
                  </>
                ) : doctor.area ? (
                  <>
                    {doctor.area}
                    {doctor.city && `, ${doctor.city}`}
                  </>
                ) : (
                  "Location available"
                )}
              </span>
            </div>
          ) : null}

          {/* Earliest availability */}
          {doctor.earliest_available_slot ? (
            <div className="recommendation-item">
              <span className="recommendation-item__label">Available:</span>
              <span className="recommendation-item__value recommendation-item__availability">
                {formatEarliestSlot(doctor.earliest_available_slot)}
              </span>
            </div>
          ) : null}
        </div>
      </div>

      {/* Source information */}
      {doctor.source_name && (
        <div className="doctor-card__source">
          <span className="badge badge--neutral">
            Listed on {doctor.source_name}
          </span>
        </div>
      )}

      {/* Actions */}
      <div className="doctor-card__actions">
        {(doctor.booking_url || doctor.source_url) && (
          <a
            className="button button--ghost button--small"
            href={doctor.booking_url || doctor.source_url || "#"}
            target="_blank"
            rel="noreferrer"
          >
            View profile
          </a>
        )}
        {onReserveAppointment && (
          <button
            type="button"
            className="button button--primary button--small"
            onClick={onReserveAppointment}
          >
            Reserve Appointment
          </button>
        )}
      </div>
    </article>
  );
}
