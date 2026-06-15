import { useState } from "react";

import { api } from "../api/client";
import type {
  ClarificationAnswerDto,
  ClarificationQuestionDto,
  TriageResponseDto,
} from "../api/dto";
import { apiPaths } from "../api/paths";
import { useLanguage } from "../i18n/useLanguage";
import {
  translateClarificationOption,
  translateClarificationQuestion,
} from "../lib/clarificationLocalization";

const ARABIC_RE = /[\u0600-\u06ff]/;

const ARABIC_CLARIFICATION_TEXT = {
  clarificationTitle: "أسئلة سريعة",
  clarificationHint: "تساعدنا إجاباتك على إعطائك إرشاداً أدق.",
  clarificationQuestionDuration: "منذ متى لديك هذه الأعراض؟",
  clarificationQuestionSeverity: "ما مدى شدة الأعراض بشكل عام؟",
  clarificationQuestionAdditionalSymptoms: "هل لديك أي من الأعراض الإضافية التالية؟",
  clarificationPainLocation: "أين يوجد الألم بالضبط؟",
  clarificationMonths: "أشهر",
  clarificationMoreThanTwoWeeks: "أكثر من أسبوعين",
  clarificationAboutAWeek: "حوالي أسبوع",
  clarificationAFewDays: "عدة أيام",
  clarificationJustStartedToday: "بدأت اليوم",
  clarificationSevere: "شديدة",
  clarificationModerate: "متوسطة",
  clarificationMild: "خفيفة",
  clarificationNoneOfThese: "لا شيء مما سبق",
  clarificationNauseaVomiting: "غثيان أو قيء",
  clarificationBreathingDifficulty: "صعوبة في التنفس",
  clarificationPain: "ألم",
  clarificationFever: "حمى",
  clarificationHowLong: "منذ متى لديك هذا العرض؟",
  clarificationPainSeverity: "ما مدى شدة الألم؟",
  clarificationBreathingSeverity: "ما مدى شدة صعوبة التنفس؟",
  clarificationInjuryTrigger:
    "هل بدأ الألم بعد إصابة أو سقوط أو حمل شيء ثقيل أو تمرين؟",
  clarificationClearInjury: "نعم، إصابة واضحة",
  clarificationAfterExerciseStrain: "بعد تمرين أو إجهاد",
  clarificationNoInjury: "لا توجد إصابة",
  clarificationNotSure: "لست متأكداً",
  clarificationGetMyAssessment: "احصل على التقييم",
  clarificationAnalyzing: "جارٍ التحليل...",
  typeYourAnswer: "اكتب إجابتك...",
};

type Props = {
  originalQuery: string;
  questions: ClarificationQuestionDto[];
  patientId: number | null;
  onComplete: (result: TriageResponseDto) => void;
};

export default function ClarificationPanel({
  originalQuery,
  questions,
  patientId,
  onComplete,
}: Props) {
  const { t, language } = useLanguage();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isArabicFlow =
    language === "ar" ||
    ARABIC_RE.test(originalQuery) ||
    questions.some(
      (question) =>
        ARABIC_RE.test(question.question) ||
        question.options?.some((option) => ARABIC_RE.test(option)),
    );
  const flowLanguage = isArabicFlow ? "ar" : language;
  const flowT: typeof t = (key) =>
    isArabicFlow && key in ARABIC_CLARIFICATION_TEXT
      ? ARABIC_CLARIFICATION_TEXT[
          key as keyof typeof ARABIC_CLARIFICATION_TEXT
        ]
      : t(key);

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = {
        original_query: originalQuery,
        answers: Object.entries(answers).map(
          ([question_id, answer]): ClarificationAnswerDto => ({
            question_id,
            answer,
          }),
        ),
        patient_id: patientId,
        language: flowLanguage,
      };
      const response = await api.post(apiPaths.clarify, payload);
      if (response.data.triage_result) {
        onComplete(response.data.triage_result);
        return;
      }
      setError("The assessment could not be completed. Please try again.");
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "The assessment could not be completed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="clarification-panel result-card" dir={isArabicFlow ? "rtl" : undefined}>
      <div>
        <h3>{flowT("clarificationTitle")}</h3>
        <p className="muted-copy">{flowT("clarificationHint")}</p>
      </div>

      <div className="clarification-list">
        {questions.map((question) => (
          <div key={question.id} className="clarification-question">
            <p>
              <strong dir="auto">
                {translateClarificationQuestion(question, flowT)}
              </strong>
            </p>
            {question.options ? (
              <div className="clarification-options">
                {question.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`button button--ghost button--small ${
                      answers[question.id] === option ? "button--active" : ""
                    }`}
                    onClick={() =>
                      setAnswers((current) => ({
                        ...current,
                        [question.id]: option,
                      }))
                    }
                  >
                    {translateClarificationOption(option, flowT)}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="text"
                placeholder={flowT("typeYourAnswer")}
                onChange={(event) =>
                  setAnswers((current) => ({
                    ...current,
                    [question.id]: event.target.value,
                  }))
                }
              />
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        className="button button--primary"
        onClick={handleSubmit}
        disabled={loading || Object.keys(answers).length < questions.length}
      >
        {loading
          ? flowT("clarificationAnalyzing")
          : flowT("clarificationGetMyAssessment")}
      </button>
      {error ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
