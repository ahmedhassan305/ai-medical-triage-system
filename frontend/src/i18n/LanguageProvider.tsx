import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { LanguageContext, type LanguageContextValue } from "./languageContext";
import { translations, type Language } from "./translations";

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const stored =
      typeof localStorage === "undefined"
        ? null
        : localStorage.getItem("aimts-language");
    return stored === "ar" ? "ar" : "en";
  });

  useEffect(() => {
    localStorage.setItem("aimts-language", language);
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage: setLanguageState,
      t: (key) => translations[language][key] ?? translations.en[key],
    }),
    [language],
  );

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}
