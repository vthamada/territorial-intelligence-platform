type StateBlockProps = {
  tone: "loading" | "error" | "empty";
  title: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
};

export function StateBlock({ tone, title, message, requestId, onRetry }: StateBlockProps) {
  return (
    <div className={`state-block state-${tone}`}>
      <h3>{title}</h3>
      <p>{message}</p>
      {requestId ? <code>request_id: {requestId}</code> : null}
      {onRetry ? (
        <button type="button" className="button-secondary" onClick={onRetry}>
          Tentar novamente
        </button>
      ) : null}
    </div>
  );
}
