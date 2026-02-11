type StrategicCardStatus = "critical" | "attention" | "stable" | "info";
type StrategicCardTrend = "up" | "down" | "flat";

type StrategicIndexCardProps = {
  label: string;
  value: string;
  status?: StrategicCardStatus;
  trend?: StrategicCardTrend;
  helper?: string;
};

function statusText(status: StrategicCardStatus) {
  if (status === "critical") {
    return "critico";
  }
  if (status === "attention") {
    return "atencao";
  }
  if (status === "stable") {
    return "estavel";
  }
  return "informativo";
}

function trendText(trend: StrategicCardTrend) {
  if (trend === "up") {
    return "subindo";
  }
  if (trend === "down") {
    return "caindo";
  }
  return "estavel";
}

export function StrategicIndexCard({ label, value, status = "info", trend, helper }: StrategicIndexCardProps) {
  return (
    <article className={`strategic-index-card strategic-${status}`}>
      <div className="strategic-index-top">
        <span>{label}</span>
        <small>{statusText(status)}</small>
      </div>
      <strong>{value}</strong>
      {trend ? <p className="strategic-index-trend">tendencia: {trendText(trend)}</p> : null}
      {helper ? <p className="strategic-index-helper">{helper}</p> : null}
    </article>
  );
}
