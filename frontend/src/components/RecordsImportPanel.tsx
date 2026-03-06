import { useState } from "react";

import type { PatientProfileResponseDto } from "../api/dto";
import SectionPanel from "./SectionPanel";

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
  const [file, setFile] = useState<File | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPatientId || !file) {
      return;
    }

    await onImport(selectedPatientId, file);
    setFile(null);
  }

  return (
    <SectionPanel
      eyebrow="Bulk records"
      title="Import structured records"
      description="Upload JSON or CSV records to create visits for an existing patient."
    >
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="records-patient">Patient</label>
          <select
            id="records-patient"
            value={selectedPatientId ?? ""}
            onChange={(event) =>
              onSelectPatient(
                event.target.value ? Number(event.target.value) : null,
              )
            }
          >
            <option value="">Select patient</option>
            {patients.map((patient) => (
              <option key={patient.id} value={patient.id}>
                {patient.full_name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="records-file">File</label>
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
    </SectionPanel>
  );
}
