import type { AppointmentSlotDto } from "../api/dto";
import type { TranslationKey } from "../i18n/languageContext";
import type { Language } from "../i18n/translations";

export function getLocaleForLanguage(language: Language): string {
  return language === "ar" ? "ar-EG" : "en-US";
}

export function formatLocalizedDateTime(
  value: string | null | undefined,
  language: Language,
): string {
  if (!value) {
    return language === "ar" ? "غير محدد" : "Not scheduled yet";
  }

  try {
    return new Date(value).toLocaleString(getLocaleForLanguage(language), {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function formatLocalizedSlotLabel(
  slot: AppointmentSlotDto,
  language: Language,
): string {
  const dayPart = new Date(slot.start_at).toLocaleDateString(
    getLocaleForLanguage(language),
    {
      weekday: "short",
      month: "short",
      day: "numeric",
    },
  );
  const timePart = new Date(slot.start_at).toLocaleTimeString(
    getLocaleForLanguage(language),
    {
      hour: "numeric",
      minute: "2-digit",
    },
  );
  return `${dayPart} — ${timePart}`;
}

export function localizeUrgencyLevel(
  level: string,
  t: (key: TranslationKey) => string,
): string {
  switch (level.toLowerCase()) {
    case "low":
      return t("urgencyLow");
    case "medium":
      return t("urgencyMedium");
    case "high":
      return t("urgencyHigh");
    default:
      return level;
  }
}

export function localizeAppointmentStatus(
  status: string,
  t: (key: TranslationKey) => string,
): string {
  switch (status.toLowerCase()) {
    case "requested":
      return t("requested");
    case "approved":
      return t("approved");
    case "rejected":
      return t("rejected");
    case "completed":
      return t("completed");
    case "cancelled":
      return t("cancelled");
    case "booked":
      return t("booked");
    case "available":
    case "open":
      return t("available");
    case "released":
      return t("available");
    case "reserved":
      return t("reserved");
    default:
      return status;
  }
}

export function localizeSlotStatus(
  status: string,
  t: (key: TranslationKey) => string,
): string {
  switch (status.toLowerCase()) {
    case "open":
    case "available":
    case "released":
      return t("available");
    case "requested":
    case "reserved":
      return t("reserved");
    case "booked":
    case "approved":
      return t("booked");
    case "cancelled":
      return t("cancelled");
    default:
      return status;
  }
}
