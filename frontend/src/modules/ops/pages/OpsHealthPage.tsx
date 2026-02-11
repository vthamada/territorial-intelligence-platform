import { useQuery } from "@tanstack/react-query";
import { getOpsSla, getOpsSummary, getOpsTimeseries } from "../../../shared/api/ops";
import { formatApiError, requestJson } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

type HealthResponse = {
  status: string;
  db: string | boolean;
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function OpsHealthPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => requestJson<HealthResponse>("/health")
  });
  const summaryQuery = useQuery({
    queryKey: ["ops", "summary"],
    queryFn: () => getOpsSummary()
  });
  const slaQuery = useQuery({
    queryKey: ["ops", "sla"],
    queryFn: () => getOpsSla({ wave: "MVP-3", min_total_runs: 1 })
  });
  const timeseriesQuery = useQuery({
    queryKey: ["ops", "timeseries"],
    queryFn: () => getOpsTimeseries({ entity: "runs", granularity: "day" })
  });

  const isLoading = healthQuery.isPending || summaryQuery.isPending || slaQuery.isPending || timeseriesQuery.isPending;
  const firstError = healthQuery.error ?? summaryQuery.error ?? slaQuery.error ?? timeseriesQuery.error;

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando saude operacional"
        message="Consultando health, summary, SLA e serie temporal."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar painel"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void healthQuery.refetch();
          void summaryQuery.refetch();
          void slaQuery.refetch();
          void timeseriesQuery.refetch();
        }}
      />
    );
  }

  const health = healthQuery.data as HealthResponse;
  const summary = summaryQuery.data!;
  const sla = slaQuery.data!;
  const timeseries = timeseriesQuery.data!;

  return (
    <div className="page-grid">
      <Panel title="Status geral" subtitle="Saude da API e volume operacional">
        <div className="kpi-grid">
          <article>
            <span>API</span>
            <strong>{health.status.toUpperCase()}</strong>
          </article>
          <article>
            <span>Banco</span>
            <strong>{String(health.db).toUpperCase()}</strong>
          </article>
          <article>
            <span>Runs</span>
            <strong>{summary.runs.total}</strong>
          </article>
          <article>
            <span>Checks</span>
            <strong>{summary.checks.total}</strong>
          </article>
          <article>
            <span>Conectores</span>
            <strong>{summary.connectors.total}</strong>
          </article>
        </div>
      </Panel>

      <Panel title="SLA por job" subtitle="Taxa de sucesso e duracao media">
        {sla.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados de SLA" message="Nenhum job encontrado para os filtros atuais." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Wave</th>
                  <th>Total</th>
                  <th>Sucesso</th>
                  <th>P95 (s)</th>
                </tr>
              </thead>
              <tbody>
                {sla.items.map((item) => (
                  <tr key={item.job_name}>
                    <td>{item.job_name}</td>
                    <td>{item.wave}</td>
                    <td>{item.total_runs}</td>
                    <td>{formatPercent(item.success_rate)}</td>
                    <td>{item.p95_duration_seconds ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Tendencia de runs" subtitle="Buckets diarios agregados por status">
        {timeseries.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados de serie temporal" message="Execute pipelines para alimentar os buckets." />
        ) : (
          <ul className="trend-list">
            {timeseries.items.map((bucket) => (
              <li key={bucket.bucket_start_utc}>
                <div>
                  <strong>{new Date(bucket.bucket_start_utc).toLocaleString("pt-BR")}</strong>
                  <p>Total: {bucket.total}</p>
                </div>
                <small>{Object.entries(bucket.by_status).map(([status, value]) => `${status}: ${value}`).join(" | ")}</small>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

