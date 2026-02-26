import type { QgMetadata } from "../api/types";
import { humanizeCoverageNote, humanizeSourceName } from "./presentation";

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

function classificationLabel(classification: string | null | undefined): string | null {
  if (!classification) {
    return null;
  }
  if (classification === "oficial") {
    return "Fonte oficial";
  }
  if (classification === "proxy") {
    return "Proxy/estimado";
  }
  return "Fontes mistas";
}

export function SourceFreshnessBadge({ metadata }: SourceFreshnessBadgeProps) {
  const classLabel = classificationLabel(metadata.source_classification);
  return (
    <div className="source-freshness-badge" role="status" aria-label="Metadados de fonte e atualização">
      <span>Fonte: {humanizeSourceName(metadata.source_name)}</span>
      {classLabel ? <span className={`source-classification source-classification-${metadata.source_classification}`}>{classLabel}</span> : null}
      <span>Atualizacao: {formatUpdatedAt(metadata.updated_at)}</span>
      <span>Cobertura: {humanizeCoverageNote(metadata.coverage_note)}</span>
    </div>
  );
}
