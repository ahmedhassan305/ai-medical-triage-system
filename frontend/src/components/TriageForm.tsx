type PatientOption = {
  id: number;
  label: string;
};

type TriageFormProps = {
  query: string;
  patientId: number | null;
  patientOptions: PatientOption[];
  lockPatientSelection: boolean;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onPatientChange: (value: number | null) => void;
  onSubmit: () => void;
};

export default function TriageForm({
  query,
  patientId,
  patientOptions,
  lockPatientSelection,
  loading,
  onQueryChange,
  onPatientChange,
  onSubmit,
}: TriageFormProps) {
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="field field--full">
        <label htmlFor="triage-query">Medical query</label>
        <textarea
          id="triage-query"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Describe symptoms, onset, severity, and any concerns..."
          rows={5}
        />
      </div>

      <div className="field">
        <label htmlFor="triage-patient">Patient context</label>
        <select
          id="triage-patient"
          value={patientId ?? ""}
          onChange={(event) =>
            onPatientChange(
              event.target.value ? Number(event.target.value) : null,
            )
          }
          disabled={lockPatientSelection || patientOptions.length === 0}
        >
          <option value="">No linked patient</option>
          {patientOptions.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        className="button button--primary"
        disabled={loading || query.trim().length === 0}
      >
        {loading ? "Running triage..." : "Run triage"}
      </button>
    </form>
  );
}
