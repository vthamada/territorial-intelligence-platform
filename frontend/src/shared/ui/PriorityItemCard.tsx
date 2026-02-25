import { Link } from "react-router-dom";
import type { PriorityItem } from "../api/types";
import { getQgDomainLabel } from "../../modules/qg/domainCatalog";
import { formatLevelLabel, formatStatusLabel, formatTrendLabel, formatValueWithUnit, humanizeDatasetSource } from "./presentation";

type PriorityItemCardProps = {
  item: PriorityItem;
};

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
          <small className="priority-item-meta">
            Nivel {formatLevelLabel(item.territory_level)} | Periodo {item.evidence.reference_period}
          </small>
        </div>
        <span className={statusClass(item.status)}>{formatStatusLabel(item.status)}</span>
      </header>

      <div className="priority-item-kpis">
        <div>
          <span>Valor</span>
          <strong>{formatValueWithUnit(item.value, item.unit)}</strong>
        </div>
        <div>
          <span>Score</span>
          <strong>{formatValueWithUnit(item.score, null)}</strong>
        </div>
        <div>
          <span>Tendencia</span>
          <strong>{formatTrendLabel(item.trend)}</strong>
        </div>
      </div>

      <ul className="priority-item-rationale">
        {(item.rationale.length > 0 ? item.rationale : ["Sem racional disponivel."]).slice(0, 3).map((entry, index) => (
          <li key={`${item.indicator_code}-${index}`}>{entry}</li>
        ))}
      </ul>

      <p className="priority-item-evidence">
        Evidencia: {humanizeDatasetSource(item.evidence.source, item.evidence.dataset)}
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
