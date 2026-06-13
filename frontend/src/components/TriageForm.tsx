import type { LabValueDto } from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";

type TriageFormProps = {
  query: string;
  loading: boolean;
  labValues: LabValueDto[];
  labLoading: boolean;
  labError: string | null;
  onQueryChange: (value: string) => void;
  onLabFileChange: (file: File | null) => void;
  onSubmit: () => void;
};

export default function TriageForm({
  query,
  loading,
  labValues,
  labLoading,
  labError,
  onQueryChange,
  onLabFileChange,
  onSubmit,
}: TriageFormProps) {
  const { t } = useLanguage();
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="field field--full">
        <label htmlFor="triage-query">{t("symptomLabel")}</label>
        <textarea
          id="triage-query"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t("symptomPlaceholder")}
          rows={5}
        />
      </div>

      <div className="field field--full">
        <label htmlFor="triage-lab-pdf">{t("labUpload")}</label>
        <input
          id="triage-lab-pdf"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => onLabFileChange(event.target.files?.[0] ?? null)}
        />
        <small className="field__hint">{t("labWarning")}</small>
        {labLoading ? <small className="field__hint">{t("extractLabs")}...</small> : null}
        {labError ? <small className="field__error">{labError}</small> : null}
        {labValues.length > 0 ? (
          <div className="lab-value-list">
            <p className="micro-label">{t("detectedLabs")}</p>
            {labValues.map((value) => (
              <span key={`${value.lab_name}-${value.value}`} className="lab-value-pill">
                {value.lab_name}: {value.value} {value.unit ?? ""}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <button
        type="submit"
        className="button button--primary"
        disabled={loading || query.trim().length === 0}
      >
        {loading ? t("reviewingSymptoms") : t("checkSymptoms")}
      </button>
    </form>
  );
}
