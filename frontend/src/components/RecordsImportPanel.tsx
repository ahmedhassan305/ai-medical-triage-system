import { useState } from "react";

import type { PatientProfileResponseDto } from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";
import SectionPanel from "./SectionPanel";
import CustomSelect from "./CustomSelect";

type RecordsImportPanelProps = {
  patients: PatientProfileResponseDto[];
  selectedPatientId: number | null;
  loading: boolean;
  error: string | null;
  successMessage: string | null;
  onSelectPatient: (patientId: number | null) => void;
  onImport: (patientId: number, file: File) => Promise<void>;
};

export default function RecordsImportPanel({
  patients,
  selectedPatientId,
  loading,
  error,
  successMessage,
  onSelectPatient,
  onImport,
}: RecordsImportPanelProps) {
  const { t } = useLanguage();
  const [patientSearch, setPatientSearch] = useState("");
  const [file, setFile] = useState<File | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPatientId || !file) {
      return;
    }

    await onImport(selectedPatientId, file);
    setFile(null);
  }

  const filteredPatients = patients.filter((patient) => {
    const search = patientSearch.trim();
    if (!search) {
      return true;
    }
    const nationalId = patient.national_id?.toLowerCase() ?? "";
    return nationalId.includes(search.toLowerCase()) ||
      patient.full_name.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <SectionPanel
      eyebrow="Bulk records"
      title="Import structured records"
      description="Upload JSON or CSV records to create visits for an existing patient."
    >
      <div className="workspace-card workspace-card--compact">
        <div className="workspace-card__header">
          <div>
            <p className="micro-label">{t("recordsTitle")}</p>
            <h3>{t("importRecords")}</h3>
          </div>
        </div>
        <div className="detail-list">
          <div>
            <strong>{t("recordsTitle")}</strong>
            <span>JSON or CSV</span>
          </div>
          <div>
            <strong>{t("topNextStep")}</strong>
            <span>Backfilling historical visits for an existing patient</span>
          </div>
          <div>
            <strong>{t("notes")}</strong>
            <span>Pick the patient first, then upload one clean file.</span>
          </div>
        </div>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="records-patient-search">{t("patientNationalId")}</label>
          <input
            id="records-patient-search"
            type="text"
            value={patientSearch}
            onChange={(event) => setPatientSearch(event.target.value)}
            placeholder="Enter patient national ID"
          />
        </div>
        <div className="field">
          <label htmlFor="records-patient">{t("patient")}</label>
          <CustomSelect
            id="records-patient"
            value={selectedPatientId ? String(selectedPatientId) : ""}
            onChange={(value) => {
              onSelectPatient(value ? Number(value) : null);
            }}
            options={[
              { value: "", label: t("selectPatient") },
              ...filteredPatients.map((patient) => ({
                value: String(patient.id),
                label: patient.national_id ? `${patient.national_id} — ${patient.full_name}` : `#${patient.id} — ${patient.full_name}`,
              })),
            ]}
          />
        </div>

        <div className="field">
          <label htmlFor="records-file">{t("recordsTitle")}</label>
          <input
            id="records-file"
            type="file"
            accept=".json,.csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>

        <button
          type="submit"
          className="button button--primary"
          disabled={loading || !selectedPatientId || !file}
        >
          {loading ? "Importing..." : "Import records"}
        </button>
      </form>

      {error ? <div className="notice notice--error">{error}</div> : null}
      {successMessage ? <div className="notice notice--success">{successMessage}</div> : null}

      {!error && !successMessage ? (
        <div className="empty-prompt empty-prompt--compact">
          <h4>{t("importRecordsCopy")}</h4>
          <p>
            After upload, the workspace will show whether the file succeeded or needs
            correction.
          </p>
        </div>
      ) : null}
    </SectionPanel>
  );
}
