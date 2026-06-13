import { useContext } from "react";

import { LanguageContext } from "./languageContext";
import { translations } from "./translations";

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      language: "en" as const,
      setLanguage: () => undefined,
      t: (key: keyof typeof translations.en) => translations.en[key],
    };
  }
  return context;
}
