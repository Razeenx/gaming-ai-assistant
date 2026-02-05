interface Props {
  loading: boolean;
  error: string | null;
}

export function StatusBar({ loading, error }: Props) {
  return (
    <footer className="status-bar">
      <div className="status-left">
        <span className={`status-dot ${loading ? "status-dot-busy" : "status-dot-ok"}`} />
        <span>{loading ? "Загрузка данных..." : "Агент активен и следит за играми."}</span>
      </div>
      {error && <div className="status-error">{error}</div>}
    </footer>
  );
}

