import { createContext } from "react";

import type { translations, Language } from "./translations";

export type TranslationKey = keyof typeof translations.en;

export type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey) => string;
};

export const LanguageContext = createContext<LanguageContextValue | null>(null);
