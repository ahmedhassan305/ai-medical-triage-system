import { describe, expect, it } from "vitest";

import { translations } from "../src/i18n/translations";

describe("bilingual labels", () => {
  it("contains Arabic labels for core navigation and triage actions", () => {
    expect(translations.ar.navTriage).toBe("الفرز الطبي");
    expect(translations.ar.checkSymptoms).toBe("فحص الأعراض");
    expect(translations.ar.navAppointments).toBe("المواعيد");
  });
});
