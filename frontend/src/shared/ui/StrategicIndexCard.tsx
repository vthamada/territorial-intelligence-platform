import { formatStatusLabel, formatTrendLabel } from "./presentation";

type StrategicCardStatus = "critical" | "attention" | "stable" | "info";
type StrategicCardTrend = "up" | "down" | "flat";

type StrategicIndexCardProps = {
  label: string;
  value: string;
  status?: StrategicCardStatus;
  trend?: StrategicCardTrend;
  helper?: string;
};

export function StrategicIndexCard({ label, value, status = "info", trend, helper }: StrategicIndexCardProps) {
  return (
    <article className={`strategic-index-card strategic-${status}`} aria-label={label}>
      <div className="strategic-index-top">
        <span>{label}</span>
        <small aria-label={`status: ${formatStatusLabel(status)}`}>{formatStatusLabel(status)}</small>
      </div>
      <strong>{value}</strong>
      {trend ? <p className="strategic-index-trend">tendencia: {formatTrendLabel(trend)}</p> : null}
      {helper ? <p className="strategic-index-helper">{helper}</p> : null}
    </article>
  );
}
