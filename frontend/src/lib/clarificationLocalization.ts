import type { ClarificationQuestionDto } from "../api/dto";
import type { TranslationKey } from "../i18n/languageContext";

const QUESTION_TRANSLATION_KEYS: Array<{
  id?: string;
  includes?: string;
  key: TranslationKey;
}> = [
  { includes: "how long have you had", key: "clarificationQuestionDuration" },
  { includes: "how severe are your symptoms overall", key: "clarificationQuestionSeverity" },
  {
    includes: "do you have any of these additional symptoms",
    key: "clarificationQuestionAdditionalSymptoms",
  },
  { includes: "where exactly is the pain", key: "clarificationPainLocation" },
  { includes: "how severe is the pain", key: "clarificationPainSeverity" },
  {
    includes: "how severe is the breathing difficulty",
    key: "clarificationBreathingSeverity",
  },
];

const OPTION_TRANSLATIONS: Record<string, TranslationKey> = {
  Months: "clarificationMonths",
  "More than 2 weeks": "clarificationMoreThanTwoWeeks",
  "About a week": "clarificationAboutAWeek",
  "A few days": "clarificationAFewDays",
  "Just started today": "clarificationJustStartedToday",
  "Severe - can barely function": "clarificationSevere",
  "Moderate - affecting daily life": "clarificationModerate",
  "Mild - barely noticeable": "clarificationMild",
  "None of these": "clarificationNoneOfThese",
  "Nausea/vomiting": "clarificationNauseaVomiting",
  "Breathing difficulty": "clarificationBreathingDifficulty",
  Pain: "clarificationPain",
  Fever: "clarificationFever",
};

export function translateClarificationQuestion(
  question: ClarificationQuestionDto,
  t: (key: TranslationKey) => string,
): string {
  const lowerQuestion = question.question.toLowerCase();
  const matched = QUESTION_TRANSLATION_KEYS.find(
    (entry) => entry.id === question.id || lowerQuestion.includes(entry.includes ?? ""),
  );
  return matched ? t(matched.key) : question.question;
}

export function translateClarificationOption(
  option: string,
  t: (key: TranslationKey) => string,
): string {
  return OPTION_TRANSLATIONS[option] ? t(OPTION_TRANSLATIONS[option]) : option;
}
