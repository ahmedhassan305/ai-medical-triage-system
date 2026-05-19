import { describe, expect, it } from "vitest";

import type { AppointmentSlotDto } from "../src/api/dto";
import { translations } from "../src/i18n/translations";
import {
  formatLocalizedSlotLabel,
  localizeAppointmentStatus,
  localizeUrgencyLevel,
} from "../src/lib/localizedDisplay";
import {
  translateClarificationOption,
  translateClarificationQuestion,
} from "../src/lib/clarificationLocalization";

const tEn = (key: keyof typeof translations.en) => translations.en[key];
const tAr = (key: keyof typeof translations.en) => translations.ar[key];

describe("localized display helpers", () => {
  it("localizes urgency and appointment statuses", () => {
    expect(localizeUrgencyLevel("low", tAr)).toBe("منخفضة");
    expect(localizeUrgencyLevel("medium", tAr)).toBe("متوسطة");
    expect(localizeUrgencyLevel("high", tAr)).toBe("عالية");
    expect(localizeAppointmentStatus("available", tAr)).toBe("متاح");
    expect(localizeAppointmentStatus("reserved", tAr)).toBe("محجوز مسبقاً");
    expect(localizeAppointmentStatus("booked", tAr)).toBe("محجوز");
  });

  it("localizes clarification prompts and options", () => {
    expect(
      translateClarificationQuestion(
        { id: "duration", question: "How long have you had these symptoms?", options: [] },
        tAr,
      ),
    ).toBe("منذ متى لديك هذه الأعراض؟");
    expect(translateClarificationOption("More than 2 weeks", tAr)).toBe("أكثر من أسبوعين");
    expect(translateClarificationOption("Nausea/vomiting", tAr)).toBe("غثيان/قيء");
  });

  it("formats compact localized slot labels", () => {
    const slot: AppointmentSlotDto = {
      id: 1,
      doctor_clinic_id: 2,
      schedule_id: 3,
      start_at: "2026-05-19T16:00:00Z",
      end_at: "2026-05-19T16:30:00Z",
      status: "open",
    };

    const englishLabel = formatLocalizedSlotLabel(slot, "en");
    const arabicLabel = formatLocalizedSlotLabel(slot, "ar");

    expect(englishLabel).toContain("—");
    expect(arabicLabel).toContain("—");
    expect(englishLabel).not.toEqual(arabicLabel);
    expect(arabicLabel).not.toContain("Consultant");
  });

  it("keeps key Arabic labels available", () => {
    expect(translations.ar.clarificationTitle).toContain("الأسئلة");
    expect(translations.ar.reserveAppointment).toBe("حجز موعد");
    expect(translations.ar.selectAvailableTime).toBe("اختر وقتاً متاحاً");
    expect(tEn("available")).toBe("Available");
  });
});
