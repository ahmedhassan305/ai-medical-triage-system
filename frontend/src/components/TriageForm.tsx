type TriageFormProps = {
  query: string;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
};

export default function TriageForm({
  query,
  loading,
  onQueryChange,
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
