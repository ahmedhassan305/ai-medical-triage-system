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
  const { t } = useLanguage();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
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
      };
      const response = await api.post(apiPaths.clarify, payload);
      if (response.data.triage_result) {
        onComplete(response.data.triage_result);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="clarification-panel result-card">
      <div>
        <p className="micro-label">{t("clarificationTitle")}</p>
        <h3>{t("clarificationTitle")}</h3>
        <p className="muted-copy">{t("clarificationHint")}</p>
      </div>

      <div className="clarification-list">
        {questions.map((question) => (
          <div key={question.id} className="clarification-question">
            <p>
              <strong dir="auto">
                {translateClarificationQuestion(question, t)}
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
                    {translateClarificationOption(option, t)}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="text"
                placeholder={t("typeYourAnswer")}
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
        {loading ? t("clarificationAnalyzing") : t("clarificationGetMyAssessment")}
      </button>
    </section>
  );
}
