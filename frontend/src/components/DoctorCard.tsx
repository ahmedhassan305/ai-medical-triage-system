import { useMemo } from "react";

import { useLanguage } from "../i18n/useLanguage";
import { formatLocalizedDateTime } from "../lib/localizedDisplay";
import type { DoctorSuggestionDto } from "../api/dto";

type DoctorCardProps = {
  doctor: DoctorSuggestionDto;
  specialty: string;
  patientLocation?: string | null;
  rank?: number;
  onReserveAppointment?: () => void;
};

type RecommendationReason = {
  text: string;
  icon: string;
  type: "specialty" | "location" | "availability" | "continuity" | "profile" | "booking";
};

function splitBackendReasons(reason?: string | null): string[] {
  return (reason || "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);
}

function classifyBackendReason(
  reason: string,
  doctor: DoctorSuggestionDto,
  language: ReturnType<typeof useLanguage>["language"],
  t: ReturnType<typeof useLanguage>["t"],
): RecommendationReason {
  const normalized = reason.toLowerCase();

  if (normalized.includes("specialty matches")) {
    return {
      text: `${t("specialtyMatch")}: ${doctor.specialty}`,
      icon: "✓",
      type: "specialty",
    };
  }

  if (normalized.includes("location")) {
    const location = reason.replace(/^Location is closer to you:\s*/i, "").trim();
    return {
      text: location ? `${t("nearYourLocation")}: ${location}` : t("nearYourLocation"),
      icon: "📍",
      type: "location",
    };
  }

  if (normalized.includes("appointment") || normalized.includes("availability")) {
    return {
      text: doctor.earliest_available_slot
        ? `${t("availableSlot")}: ${formatLocalizedDateTime(
            doctor.earliest_available_slot,
            language,
          )}`
        : t("availableSoon"),
      icon: "⏰",
      type: "availability",
    };
  }

  if (normalized.includes("seen this doctor")) {
    return {
      text: t("seenDoctorBefore"),
      icon: "↻",
      type: "continuity",
    };
  }

  if (normalized.includes("profile text overlaps")) {
    return {
      text: reason.replace(/^Profile text overlaps with this case:\s*/i, `${t("because")} `),
      icon: "⌁",
      type: "profile",
    };
  }

  if (normalized.includes("booking")) {
    return {
      text: t("bookingLinkAvailable"),
      icon: "↗",
      type: "booking",
    };
  }

  return {
    text: reason,
    icon: "•",
    type: "profile",
  };
}

function getFallbackReasons(
  doctor: DoctorSuggestionDto,
  specialty: string,
  language: ReturnType<typeof useLanguage>["language"],
  t: ReturnType<typeof useLanguage>["t"],
  patientLocation?: string | null,
): RecommendationReason[] {
  const reasons: RecommendationReason[] = [];

  if (doctor.specialty.toLowerCase() === specialty.toLowerCase()) {
    reasons.push({
      text: doctor.specialty_match_reason || t("specialtyMatchesYourCondition"),
      icon: "✓",
      type: "specialty",
    });
  }

  if (patientLocation && [doctor.area, doctor.city].some((part) => part === patientLocation)) {
    reasons.push({
      text: t("nearYourLocation"),
      icon: "📍",
      type: "location",
    });
  } else if (doctor.area || doctor.city) {
    reasons.push({
      text: t("locationInfoAvailable"),
      icon: "📍",
      type: "location",
    });
  }

  if (doctor.earliest_available_slot) {
    reasons.push({
      text: `${t("availableSlot")}: ${formatLocalizedDateTime(
        doctor.earliest_available_slot,
        language,
      )}`,
      icon: "⏰",
      type: "availability",
    });
  }

  return reasons;
}

function getRecommendationReasons(
  doctor: DoctorSuggestionDto,
  specialty: string,
  language: ReturnType<typeof useLanguage>["language"],
  t: ReturnType<typeof useLanguage>["t"],
  patientLocation?: string | null,
): RecommendationReason[] {
  const backendReasons = splitBackendReasons(doctor.recommendation_reason);
  if (backendReasons.length > 0) {
    return backendReasons.map((reason) => classifyBackendReason(reason, doctor, language, t));
  }

  return getFallbackReasons(doctor, specialty, language, t, patientLocation);
}

function RatingStars({ rating }: { rating?: number | null }) {
  if (!rating || rating < 0 || rating > 5) {
    return null;
  }

  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 !== 0;

  return (
    <div className="doctor-card__rating">
      <div className="rating-stars" aria-label={`Rating ${rating.toFixed(1)} out of 5`}>
        {Array.from({ length: 5 }).map((_, index) => (
          <span
            key={index}
            className={`star ${
              index < fullStars
                ? "star--full"
                : index === fullStars && hasHalfStar
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

export default function DoctorCard({
  doctor,
  specialty,
  patientLocation,
  rank,
  onReserveAppointment,
}: DoctorCardProps) {
  const { t, language } = useLanguage();
  const reasons = useMemo(
    () => getRecommendationReasons(doctor, specialty, language, t, patientLocation),
    [doctor, language, patientLocation, specialty, t],
  );
  const locationLabel = [doctor.area, doctor.city].filter(Boolean).join(", ");

  return (
    <article className={`doctor-card ${rank === 1 ? "doctor-card--top-ranked" : ""}`}>
      <div className="doctor-card__header">
        <div className="doctor-card__info">
          <div className="doctor-card__title-row">
            <h3 className="doctor-card__name">{doctor.full_name}</h3>
            {rank ? (
              <span className="doctor-card__rank">
                #{rank} {rank === 1 ? t("recommended") : ""}
              </span>
            ) : null}
          </div>
          <p className="doctor-card__specialty">{doctor.specialty}</p>
          <p className="doctor-card__clinic">{doctor.clinic}</p>
          {locationLabel ? <p className="doctor-card__location">{locationLabel}</p> : null}
        </div>
        <RatingStars rating={doctor.rating} />
      </div>
      {doctor.rating ? (
        <p className="doctor-card__review-count">
          {doctor.review_count
            ? `${doctor.review_count} ${doctor.review_count === 1 ? "review" : "reviews"}`
            : null}
        </p>
      ) : null}

      {reasons.length > 0 ? (
        <div className="doctor-card__why-recommended">
          <p className="micro-label">{t("whyRecommended")}</p>
          <ul className="recommendation-reasons">
            {reasons.slice(0, 5).map((reason, index) => (
              <li key={`${reason.type}-${index}`} className="recommendation-reason">
                <span
                  className={`reason-icon reason-icon--${reason.type}`}
                  aria-hidden="true"
                >
                  {reason.icon}
                </span>
                <span className="reason-text" dir="auto">
                  {reason.text}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="doctor-card__match-strip">
        <span className="doctor-card__match-pill">
          <strong>{t("specialtyMatchesLabel")}</strong> {doctor.specialty}
        </span>
        {doctor.earliest_available_slot ? (
          <span className="doctor-card__match-pill doctor-card__match-pill--available">
            <strong>{t("availableSlot")}</strong>{" "}
            {formatLocalizedDateTime(doctor.earliest_available_slot, language)}
          </span>
        ) : null}
      </div>

      {doctor.source_name ? (
        <div className="doctor-card__source">
          <span className="badge badge--neutral">
            {t("listedOn")} {doctor.source_name}
          </span>
        </div>
      ) : null}

      <div className="doctor-card__actions">
        {(doctor.booking_url || doctor.source_url) && (
          <a
            className="button button--ghost button--small"
            href={doctor.booking_url || doctor.source_url || "#"}
            target="_blank"
            rel="noreferrer"
          >
            {t("viewProfile")}
          </a>
        )}
        {onReserveAppointment ? (
          <button
            type="button"
            className="button button--primary button--small"
            onClick={onReserveAppointment}
          >
            {t("reserveAppointment")}
          </button>
        ) : null}
      </div>
    </article>
  );
}
