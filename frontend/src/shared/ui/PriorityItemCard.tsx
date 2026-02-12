import { Link } from "react-router-dom";
import type { PriorityItem } from "../api/types";
import { getQgDomainLabel } from "../../modules/qg/domainCatalog";

type PriorityItemCardProps = {
  item: PriorityItem;
};

function formatValue(value: number, unit: string | null) {
  if (unit) {
    return `${value.toFixed(2)} ${unit}`;
  }
  return value.toFixed(2);
}

function statusClass(status: string) {
  if (status === "critical") {
    return "status-chip status-failed";
  }
  if (status === "attention") {
    return "status-chip status-warn";
  }
  return "status-chip status-success";
}

export function PriorityItemCard({ item }: PriorityItemCardProps) {
  const mapQuery = new URLSearchParams({
    metric: item.indicator_code,
    period: item.evidence.reference_period,
    territory_id: item.territory_id,
  });

  return (
    <article className="priority-item-card">
      <header className="priority-item-header">
        <div>
          <h3>{item.territory_name}</h3>
          <p>
            {getQgDomainLabel(item.domain)} | {item.indicator_name}
          </p>
        </div>
        <span className={statusClass(item.status)}>{item.status}</span>
      </header>

      <div className="priority-item-kpis">
        <div>
          <span>valor</span>
          <strong>{formatValue(item.value, item.unit)}</strong>
        </div>
        <div>
          <span>score</span>
          <strong>{item.score.toFixed(2)}</strong>
        </div>
        <div>
          <span>tendencia</span>
          <strong>{item.trend}</strong>
        </div>
      </div>

      <ul className="priority-item-rationale">
        {(item.rationale.length > 0 ? item.rationale : ["Sem racional disponivel."]).slice(0, 3).map((entry, index) => (
          <li key={`${item.indicator_code}-${index}`}>{entry}</li>
        ))}
      </ul>

      <p className="priority-item-evidence">
        evidencia: {item.evidence.source} / {item.evidence.dataset} / {item.evidence.reference_period}
      </p>

      <div className="priority-item-actions">
        <Link className="inline-link" to={`/territorio/${item.territory_id}`}>
          Abrir perfil
        </Link>
        <Link className="inline-link" to={`/mapa?${mapQuery.toString()}`}>
          Ver no mapa
        </Link>
      </div>
    </article>
  );
}
