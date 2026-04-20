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
        <label htmlFor="triage-query">Describe what you are feeling</label>
        <textarea
          id="triage-query"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Example: I have chest tightness and shortness of breath since this morning, and it gets worse when I walk."
          rows={5}
        />
      </div>

      <div className="field">
        <label htmlFor="triage-patient">Linked patient profile</label>
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
        {loading ? "Reviewing symptoms..." : "Check symptoms"}
      </button>
    </form>
  );
}
