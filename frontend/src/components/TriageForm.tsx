type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export default function TriageForm({
  query,
  onQueryChange,
  onSubmit,
  loading,
}: Props) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="card"
    >
      <label className="label" htmlFor="query">
        Medical Query
      </label>
      <input
        id="query"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="Describe symptoms or ask a medical question..."
        className="input"
      />
      <button type="submit" disabled={loading || query.trim().length === 0}>
        {loading ? "Submitting..." : "Submit"}
      </button>
    </form>
  );
}
