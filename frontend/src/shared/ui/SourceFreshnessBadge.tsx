import type { QgMetadata } from "../api/types";

type SourceFreshnessBadgeProps = {
  metadata: QgMetadata;
};

function formatUpdatedAt(updatedAt: string | null) {
  if (!updatedAt) {
    return "sem data";
  }

  const parsed = new Date(updatedAt);
  if (Number.isNaN(parsed.getTime())) {
    return updatedAt;
  }

  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function SourceFreshnessBadge({ metadata }: SourceFreshnessBadgeProps) {
  return (
    <div className="source-freshness-badge" role="status" aria-label="Metadados de fonte e atualizacao">
      <span>Fonte: {metadata.source_name}</span>
      <span>Atualizacao: {formatUpdatedAt(metadata.updated_at)}</span>
      <span>Cobertura: {metadata.coverage_note}</span>
    </div>
  );
}
