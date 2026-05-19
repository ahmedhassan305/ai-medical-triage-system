import { useMemo, useState } from "react";

import type {
  DoctorSuggestionDto,
  LabValueDto,
  ManagedPatientProfileCreateDto,
  PatientProfileResponseDto,
  RoleType,
  TriageResponseDto,
  VisitResponseDto,
} from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";
import { parseEgyptianNationalId } from "../lib/egyptianNationalId";
import { localizeUrgencyLevel } from "../lib/localizedDisplay";
import ClarificationPanel from "./ClarificationPanel";
import DoctorCard from "./DoctorCard";
import SectionPanel from "./SectionPanel";
import TriageForm from "./TriageForm";

type TriagePanelProps = {
  role: RoleType;
  loading: boolean;
  error: string | null;
  result: TriageResponseDto | null;
  patientProfile: PatientProfileResponseDto | null;
  linkedPatient: PatientProfileResponseDto | null;
  linkedPatientLatestVisit: VisitResponseDto | null;
  patientLookupNationalId: string;
  patientLookupLoading: boolean;
  patientLookupError: string | null;
  patientCreateLoading: boolean;
  patientCreateError: string | null;
  query: string;
  labValues?: LabValueDto[];
  labLoading?: boolean;
  labError?: string | null;
  onQueryChange: (value: string) => void;
  onLabFileChange?: (file: File | null) => void;
  onLookupNationalIdChange: (value: string) => void;
  onLookupPatient: (nationalId: string) => Promise<void>;
  onClearLinkedPatient: () => void;
  onCreatePatientProfile: (
    payload: ManagedPatientProfileCreateDto,
  ) => Promise<void>;
  onSubmit: () => void;
  onClarificationComplete: (result: TriageResponseDto) => void;
  onReserveAppointment?: (
    doctor: DoctorSuggestionDto,
    specialty: string,
    reason: string,
  ) => void;
};

type ManagedPatientFormState = {
  full_name: string;
  sex: "" | "Male" | "Female";
  national_id: string;
  current_governorate: string;
  smoker: boolean;
  alcoholic: boolean;
  chronic_conditions: string;
};

const EMPTY_PATIENT_FORM: ManagedPatientFormState = {
  full_name: "",
  sex: "",
  national_id: "",
  current_governorate: "",
  smoker: false,
  alcoholic: false,
  chronic_conditions: "",
};

function summarize(text?: string | null, fallback = "No summary available."): string {
  if (!text) {
    return fallback;
  }
  const normalized = text.trim();
  if (normalized.length <= 160) {
    return normalized;
  }
  return `${normalized.slice(0, 157).trimEnd()}...`;
}

function getLikelihoodLabel(
  value: TriageResponseDto["suspected_conditions"][number]["likelihood"],
  t: ReturnType<typeof useLanguage>["t"],
): string {
  switch (value) {
    case "more_likely":
    case "more likely":
      return t("moreLikely");
    case "possible":
      return t("possible");
    case "less_likely":
    case "less likely":
      return t("lessLikely");
    default:
      return value;
  }
}

function formatDateTime(dateValue?: string | null): string {
  if (!dateValue) {
    return "Not recorded";
  }
  try {
    return new Date(dateValue).toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateValue;
  }
}

function StaffPatientLookup({
  linkedPatient,
  latestVisit,
  lookupNationalId,
  lookupLoading,
  lookupError,
  createLoading,
  createError,
  onLookupNationalIdChange,
  onLookupPatient,
  onClearLinkedPatient,
  onCreatePatientProfile,
}: {
  linkedPatient: PatientProfileResponseDto | null;
  latestVisit: VisitResponseDto | null;
  lookupNationalId: string;
  lookupLoading: boolean;
  lookupError: string | null;
  createLoading: boolean;
  createError: string | null;
  onLookupNationalIdChange: (value: string) => void;
  onLookupPatient: (nationalId: string) => Promise<void>;
  onClearLinkedPatient: () => void;
  onCreatePatientProfile: (
    payload: ManagedPatientProfileCreateDto,
  ) => Promise<void>;
}) {
  const { t, language } = useLanguage();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] =
    useState<ManagedPatientFormState>(EMPTY_PATIENT_FORM);

  const parsedNationalId = useMemo(
    () =>
      createForm.national_id
        ? parseEgyptianNationalId(createForm.national_id)
        : null,
    [createForm.national_id],
  );
  const nationalIdInvalid =
    createForm.national_id.trim().length > 0 && parsedNationalId === null;

  function handleToggleCreateForm() {
    setShowCreateForm((current) => {
      const nextValue = !current;
      if (nextValue) {
        setCreateForm((form) => ({
          ...form,
          national_id: lookupNationalId || form.national_id,
        }));
      }
      return nextValue;
    });
  }

  async function submitCreateForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (createForm.sex !== "Male" && createForm.sex !== "Female") {
      return;
    }
    await onCreatePatientProfile({
      full_name: createForm.full_name.trim(),
      sex: createForm.sex,
      national_id: createForm.national_id,
      current_governorate:
        createForm.current_governorate.trim() ||
        parsedNationalId?.governorate ||
        null,
      smoker: createForm.smoker,
      alcoholic: createForm.alcoholic,
      chronic_conditions: createForm.chronic_conditions
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
    setShowCreateForm(false);
    setCreateForm(EMPTY_PATIENT_FORM);
  }

  return (
    <div className="stack-lg">
      <section className="result-card">
        <div className="result-card__meta">
          <span className="badge badge--neutral">{t("patientNationalId")}</span>
          <span className="muted-copy">{t("enterPatientHistoryCopy")}</span>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="triage-patient-national-id">{t("patientNationalId")}</label>
            <input
              id="triage-patient-national-id"
              inputMode="numeric"
              maxLength={14}
              value={lookupNationalId}
              onChange={(event) =>
                onLookupNationalIdChange(
                  event.target.value.replace(/\D/g, "").slice(0, 14),
                )
              }
              placeholder={
                language === "ar"
                  ? "الرقم القومي المكون من 14 رقمًا"
                  : "14-digit national ID"
              }
            />
          </div>

          <div className="button-row button-row--align-end">
            <button
              type="button"
              className="button button--primary"
              disabled={lookupLoading || lookupNationalId.trim().length !== 14}
              onClick={() => onLookupPatient(lookupNationalId)}
            >
              {lookupLoading ? t("lookingUp") : t("findPatientShort")}
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={handleToggleCreateForm}
            >
              {showCreateForm ? t("closeNewPatientForm") : t("createNewPatientProfile")}
            </button>
            {linkedPatient ? (
              <button
                type="button"
                className="button button--ghost"
                onClick={onClearLinkedPatient}
              >
                {t("clearLinkedPatient")}
              </button>
            ) : null}
          </div>
        </div>

        {lookupError ? <div className="notice notice--error">{lookupError}</div> : null}

        {linkedPatient ? (
          <div className="patient-lookup-card">
            <div className="patient-lookup-card__header">
              <div>
                <p className="micro-label">{t("matchedPatient")}</p>
                <h3>{linkedPatient.full_name}</h3>
                <p className="muted-copy">
                  {linkedPatient.sex} · {linkedPatient.age} {t("years")} ·{" "}
                  {linkedPatient.current_governorate ||
                    linkedPatient.inferred_governorate ||
                    t("governoratePendingShort")}
                </p>
              </div>
              <span className="badge badge--neutral">
                {t("nationalIdLinked")}
              </span>
            </div>

            <div className="detail-list">
              <div>
                <span>{t("medicalHistory")}</span>
                <strong>
                  {linkedPatient.chronic_conditions.length > 0
                    ? linkedPatient.chronic_conditions.join(", ")
                    : t("noneRecorded")}
                </strong>
              </div>
              <div>
                <span>{t("latestVisitSummary")}</span>
                <strong>
                  {latestVisit
                    ? formatDateTime(latestVisit.created_at)
                    : t("visitHistoryNotAvailableYet")}
                </strong>
              </div>
            </div>

            {latestVisit ? (
              <div className="callout">
                <p className="micro-label">{t("latestVisit")}</p>
                <p>
                  <strong>{latestVisit.diagnosis || t("visitNoteRecorded")}</strong>
                </p>
                <p>{summarize(latestVisit.notes || latestVisit.symptoms)}</p>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="empty-state">{t("noPatientLinked")}</div>
        )}
      </section>

      {showCreateForm ? (
        <section className="result-card">
          <div className="result-card__meta">
            <span className="badge badge--neutral">{t("createAccount")}</span>
            <span className="muted-copy">
              {language === "ar"
                ? "يمكن للطبيب أو المسؤول تسجيل ملف مريض جديد مباشرة من الفرز عند وصول حالة جديدة."
                : "Doctors and admins can register an unlinked patient profile directly from triage when a new case arrives."}
            </span>
          </div>

          <form className="form-grid" onSubmit={submitCreateForm}>
            <div className="field">
              <label htmlFor="triage-create-full-name">{t("fullName")}</label>
              <input
                id="triage-create-full-name"
                value={createForm.full_name}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="triage-create-sex">{t("gender")}</label>
              <select
                id="triage-create-sex"
                value={createForm.sex}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    sex: event.target.value as ManagedPatientFormState["sex"],
                  }))
                }
              >
                <option value="">{t("selectGender")}</option>
                <option value="Male">{t("male")}</option>
                <option value="Female">{t("female")}</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="triage-create-national-id">{t("egyptianNationalId")}</label>
              <input
                id="triage-create-national-id"
                inputMode="numeric"
                maxLength={14}
                value={createForm.national_id}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    national_id: event.target.value.replace(/\D/g, "").slice(0, 14),
                  }))
                }
              />
              <small className="field__hint">
                The system derives date of birth and inferred governorate from this
                ID.
              </small>
            </div>

            <div className="field">
              <label htmlFor="triage-create-governorate">
                {t("currentGovernorateResidence")}
              </label>
              <input
                id="triage-create-governorate"
                value={createForm.current_governorate}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    current_governorate: event.target.value,
                  }))
                }
                placeholder={parsedNationalId?.governorate || t("optionalOverride")}
              />
            </div>

            <div className="field field--full">
              <label htmlFor="triage-create-conditions">{t("medicalHistory")}</label>
              <input
                id="triage-create-conditions"
                value={createForm.chronic_conditions}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    chronic_conditions: event.target.value,
                  }))
                }
                placeholder={t("chronicConditionsExample")}
              />
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={createForm.smoker}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    smoker: event.target.checked,
                  }))
                }
              />
              {t("smoker")}
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={createForm.alcoholic}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    alcoholic: event.target.checked,
                  }))
                }
              />
              {t("alcoholUse")}
            </label>

            {nationalIdInvalid ? (
              <div className="notice notice--error">
                {t("enterValidNationalId")}
              </div>
            ) : null}

            {createError ? (
              <div className="notice notice--error">{createError}</div>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={
                createLoading ||
                !createForm.full_name.trim() ||
                !createForm.national_id ||
                !createForm.sex ||
                nationalIdInvalid
              }
            >
              {createLoading ? t("creating") : t("createPatientProfile")}
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}

export default function TriagePanel({
  role,
  loading,
  error,
  result,
  patientProfile,
  linkedPatient,
  linkedPatientLatestVisit,
  patientLookupNationalId,
  patientLookupLoading,
  patientLookupError,
  patientCreateLoading,
  patientCreateError,
  query,
  labValues = [],
  labLoading = false,
  labError = null,
  onQueryChange,
  onLabFileChange = () => undefined,
  onLookupNationalIdChange,
  onLookupPatient,
  onClearLinkedPatient,
  onCreatePatientProfile,
  onSubmit,
  onClarificationComplete,
  onReserveAppointment,
}: TriagePanelProps) {
  const { t } = useLanguage();
  const urgencyLabel =
    ["low", "medium", "high"].includes(
      result?.urgency_label.trim().toLowerCase() ?? "",
    )
      ? localizeUrgencyLevel(result?.urgency_label ?? "", t)
      : result?.urgency_label ?? "";

  return (
    <SectionPanel
      eyebrow={t("triageTitle")}
      title={t("triageDescription")}
      description={t("describeSymptomsEmpty")}
    >
      {role === "patient" ? (
        <div className="result-card">
          <div className="result-card__meta">
            <span className="badge badge--neutral">{t("patientProfiles")}</span>
            <span className="muted-copy">
              {patientProfile
                ? t("patientProfileWillBeUsedAutomatically")
                : t("completeProfileToUseHistory")}
            </span>
          </div>
          {patientProfile ? (
            <div className="detail-list">
              <div>
                <span>{t("matchedPatient")}</span>
                <strong>{patientProfile.full_name}</strong>
              </div>
              <div>
                <span>{t("governoratePending")}</span>
                <strong>
                  {patientProfile.current_governorate ||
                    patientProfile.inferred_governorate ||
                    t("governoratePendingShort")}
                </strong>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              {t("noPatientProfileLinkedYet")}
            </div>
          )}
        </div>
      ) : (
        <StaffPatientLookup
          linkedPatient={linkedPatient}
          latestVisit={linkedPatientLatestVisit}
          lookupNationalId={patientLookupNationalId}
          lookupLoading={patientLookupLoading}
          lookupError={patientLookupError}
          createLoading={patientCreateLoading}
          createError={patientCreateError}
          onLookupNationalIdChange={onLookupNationalIdChange}
          onLookupPatient={onLookupPatient}
          onClearLinkedPatient={onClearLinkedPatient}
          onCreatePatientProfile={onCreatePatientProfile}
        />
      )}

      <TriageForm
        query={query}
        loading={loading}
        labValues={labValues}
        labLoading={labLoading}
        labError={labError}
        onQueryChange={onQueryChange}
        onLabFileChange={onLabFileChange}
        onSubmit={onSubmit}
      />

      {error ? <div className="notice notice--error">{error}</div> : null}

      {result && result.needs_clarification ? (
        <ClarificationPanel
          originalQuery={query}
          questions={result.questions}
          patientId={patientProfile?.id ?? linkedPatient?.id ?? null}
          onComplete={onClarificationComplete}
        />
      ) : result ? (
        <div className="result-layout">
          <section className="result-card result-card--hero">
            <div className="result-card__meta">
              <span className={`badge badge--${result.triage_level}`}>
                {localizeUrgencyLevel(result.triage_level, t)}
              </span>
              <span className="muted-copy">
                {result.history_used ? t("historyUsed") : t("historyNotUsed")}
              </span>
            </div>

            <div className="stack-md">
              <div>
                <p className="micro-label">{t("status")}</p>
                <h3 className="result-title" dir="auto">
                  {urgencyLabel}
                </h3>
                <p dir="auto">{result.patient_friendly_explanation}</p>
              </div>

              {result.urgency_reason ? (
                <div className="callout callout--next-step">
                  <p className="micro-label">{t("attention")}</p>
                  <p dir="auto">{result.urgency_reason}</p>
                </div>
              ) : null}

              {result.recommended_actions[0] ? (
                <div className="callout">
                  <p className="micro-label">{t("topNextStep")}</p>
                  <p dir="auto">{result.recommended_actions[0]}</p>
                </div>
              ) : null}

              {result.red_flags.length > 0 ? (
                <div className="callout callout--warning">
                  <p className="micro-label">{t("attention")}</p>
                  <ul className="list">
                    {result.red_flags.map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </section>

          <div className="result-grid">
            <section className="result-card">
              <p className="micro-label">{t("recentClinicalSummary")}</p>
              <p>{result.clinical_summary}</p>
            </section>

            <section className="result-card">
              <p className="micro-label">{t("recommendedSpecialty")}</p>
              <p>{result.recommended_specialty ?? t("generalPractice")}</p>
              {result.specialty_reason ? (
                <p className="muted-copy" dir="auto">
                  {result.specialty_reason}
                </p>
              ) : (
                <p className="muted-copy">{t("supportingReferencesFitSpecialty")}</p>
              )}
            </section>
          </div>

            <section className="result-card">
              <p className="micro-label">{t("possibleConditions")}</p>
              {result.suspected_conditions.length === 0 ? (
                <p className="muted-copy">{t("couldNotRankConditions")}</p>
              ) : (
                <div className="condition-list">
                  {result.suspected_conditions.map((condition) => (
                    <article key={condition.name} className="condition-card">
                      <div className="condition-card__header">
                        <strong>{condition.name}</strong>
                        <span className="badge badge--neutral">
                          {getLikelihoodLabel(condition.likelihood, t)}
                        </span>
                      </div>
                      <p>{condition.explanation}</p>
                    </article>
                  ))}
                </div>
            )}
          </section>

          <div className="result-grid">
            <section className="result-card">
              <p className="micro-label">{t("latestDoctorRecommendation")}</p>
              {result.suggested_doctors.length === 0 ? (
                <p className="muted-copy">{t("noDoctorsMatchedYet")}</p>
              ) : (
                <div className="stack-md">
                  {result.suggested_doctors.map((doctor) => {
                    const patientLoc =
                      role === "patient"
                        ? patientProfile?.current_governorate ||
                          patientProfile?.inferred_governorate
                        : linkedPatient?.current_governorate ||
                          linkedPatient?.inferred_governorate;

                    return (
                      <DoctorCard
                        key={doctor.id}
                        doctor={doctor}
                        specialty={result.recommended_specialty || t("generalPractice")}
                        patientLocation={patientLoc || null}
                        onReserveAppointment={
                          onReserveAppointment
                            ? () =>
                                onReserveAppointment(
                                  doctor,
                                  result.recommended_specialty || t("generalPractice"),
                                  query,
                                )
                            : undefined
                        }
                      />
                    );
                  })}
                </div>
              )}
            </section>

            <section className="result-card">
              <p className="micro-label">{t("topNextStep")}</p>
              <ul className="list">
                {result.recommended_actions.map((action) => (
                  <li key={action} dir="auto">
                    {action}
                  </li>
                ))}
              </ul>
            </section>
          </div>

          {result.supporting_references.length > 0 ? (
            <section className="result-card">
              <p className="micro-label">{t("supportingMedicalReferences")}</p>
              <div className="reference-list">
                {result.supporting_references.map((reference) => (
                  <article
                    key={`${reference.source}-${reference.title}`}
                    className="reference-card"
                  >
                    <p>
                      <strong dir="auto">{reference.title}</strong>
                    </p>
                    <p className="muted-copy" dir="auto">
                      {reference.source}
                    </p>
                    <p dir="auto">{reference.snippet}</p>
                    {reference.url ? (
                      <a
                        className="reference-link"
                        href={reference.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t("openSource")}
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          <section className="result-card">
            <p className="micro-label">{t("attention")}</p>
            <p className="muted-copy" dir="auto">
              {result.disclaimer}
            </p>
          </section>
        </div>
      ) : null}
    </SectionPanel>
  );
}




