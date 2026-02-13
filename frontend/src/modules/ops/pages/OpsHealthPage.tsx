import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getConnectorRegistry, getOpsReadiness, getOpsSla, getOpsSourceCoverage, getOpsSummary, getOpsTimeseries, getPipelineChecks } from "../../../shared/api/ops";
import { formatApiError, requestJson } from "../../../shared/api/http";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";
import type { OpsReadinessResponse, ConnectorRegistryItem, OpsSourceCoverageResponse, PipelineCheck } from "../../../shared/api/types";

type HealthResponse = {
  status: string;
  db: string | boolean;
};

const HISTORICAL_WINDOW_DAYS = 7;
const CURRENT_HEALTH_WINDOW_DAYS = 1;

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function isoDaysAgo(days: number): string {
  const now = new Date();
  now.setUTCDate(now.getUTCDate() - days);
  return now.toISOString();
}

export function OpsHealthPage() {
  const historicalStartedFrom = useMemo(() => isoDaysAgo(HISTORICAL_WINDOW_DAYS), []);

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => requestJson<HealthResponse>("/health")
  });
  const summaryQuery = useQuery({
    queryKey: ["ops", "summary"],
    queryFn: () => getOpsSummary()
  });
  const slaQuery = useQuery({
    queryKey: ["ops", "sla", "historical", historicalStartedFrom],
    queryFn: () =>
      getOpsSla({
        min_total_runs: 1,
        started_from: historicalStartedFrom
      })
  });
  const readinessQuery = useQuery({
    queryKey: ["ops", "readiness", HISTORICAL_WINDOW_DAYS, CURRENT_HEALTH_WINDOW_DAYS],
    queryFn: () =>
      getOpsReadiness({
        window_days: HISTORICAL_WINDOW_DAYS,
        health_window_days: CURRENT_HEALTH_WINDOW_DAYS,
        slo1_target_pct: 95
      })
  });
  const timeseriesQuery = useQuery({
    queryKey: ["ops", "timeseries"],
    queryFn: () => getOpsTimeseries({ entity: "runs", granularity: "day" })
  });
  const checksQuery = useQuery({
    queryKey: ["ops", "checks", "latest"],
    queryFn: () => getPipelineChecks({ limit: 50 })
  });
  const connectorsQuery = useQuery({
    queryKey: ["ops", "connectors"],
    queryFn: () => getConnectorRegistry()
  });
  const coverageQuery = useQuery({
    queryKey: ["ops", "source-coverage"],
    queryFn: () => getOpsSourceCoverage()
  });

  const isLoading =
    healthQuery.isPending ||
    summaryQuery.isPending ||
    slaQuery.isPending ||
    readinessQuery.isPending ||
    timeseriesQuery.isPending ||
    checksQuery.isPending ||
    connectorsQuery.isPending ||
    coverageQuery.isPending;
  const firstError =
    healthQuery.error ??
    summaryQuery.error ??
    slaQuery.error ??
    readinessQuery.error ??
    timeseriesQuery.error ??
    checksQuery.error ??
    connectorsQuery.error ??
    coverageQuery.error;

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
          void readinessQuery.refetch();
          void timeseriesQuery.refetch();
          void checksQuery.refetch();
          void connectorsQuery.refetch();
          void coverageQuery.refetch();
        }}
      />
    );
  }

  const health = healthQuery.data as HealthResponse;
  const summary = summaryQuery.data!;
  const sla = slaQuery.data!;
  const readiness = readinessQuery.data as OpsReadinessResponse;
  const timeseries = timeseriesQuery.data!;
  const checks = checksQuery.data!;
  const connectors = connectorsQuery.data!;
  const coverage = coverageQuery.data!;
  const historicalRate = readiness.slo1.total_runs > 0 ? readiness.slo1.successful_runs / readiness.slo1.total_runs : null;
  const currentHealthRate =
    readiness.slo1_current.total_runs > 0
      ? readiness.slo1_current.successful_runs / readiness.slo1_current.total_runs
      : null;
  const historicalBelowTargetJobs = readiness.slo1.below_target_jobs.length;
  const currentHealthBelowTargetJobs = readiness.slo1_current.below_target_jobs.length;

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

      <Panel title="Monitor SLO-1" subtitle="Comparativo entre historico recente (7 dias) e saude corrente (1 dia)">
        <div className="kpi-grid">
          <article>
            <span>SLO-1 (7d)</span>
            <strong>{historicalRate === null ? "-" : formatPercent(historicalRate)}</strong>
          </article>
          <article>
            <span>Jobs abaixo da meta (7d)</span>
            <strong>{historicalBelowTargetJobs}</strong>
          </article>
          <article>
            <span>SLO-1 (1d)</span>
            <strong>{currentHealthRate === null ? "-" : formatPercent(currentHealthRate)}</strong>
          </article>
          <article>
            <span>Jobs abaixo da meta (1d)</span>
            <strong>{currentHealthBelowTargetJobs}</strong>
          </article>
          <article>
            <span>Status readiness</span>
            <strong>{readiness.status}</strong>
          </article>
        </div>
        {readiness.hard_failures.length > 0 ? (
          <p className="map-export-error">Hard failures: {readiness.hard_failures.join(" | ")}</p>
        ) : null}
        {readiness.warnings.length > 0 ? <p className="panel-subtitle">Warnings: {readiness.warnings.join(" | ")}</p> : null}
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

      <CollapsiblePanel title="Quality checks" subtitle="Resultados dos ultimos checks de qualidade" defaultOpen={false} badgeCount={checks?.items?.length ?? 0}>
        {!checks?.items?.length ? (
          <StateBlock tone="empty" title="Sem checks" message="Nenhum check de qualidade encontrado." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Check</th>
                  <th>Status</th>
                  <th>Detalhes</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                {checks.items.map((item, idx) => (
                  <tr key={`${item.check_name}-${idx}`}>
                    <td>{item.check_name}</td>
                    <td>{item.status}</td>
                    <td style={{ maxWidth: "20rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.details}</td>
                    <td>{item.created_at_utc ? new Date(item.created_at_utc).toLocaleString("pt-BR") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel title="Cobertura de fontes" subtitle="Linhas ingeridas por fonte de dados" defaultOpen={false} badgeCount={coverage?.items?.length ?? 0}>
        {!coverage?.items?.length ? (
          <StateBlock tone="empty" title="Sem cobertura" message="Nenhuma fonte com dados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fonte</th>
                  <th>Total linhas</th>
                  <th>Ultima atualizacao</th>
                </tr>
              </thead>
              <tbody>
                {coverage.items.map((item) => (
                  <tr key={item.source}>
                    <td>{item.source}</td>
                    <td>{item.rows_loaded_total.toLocaleString("pt-BR")}</td>
                    <td>{item.latest_run_started_at_utc ? new Date(item.latest_run_started_at_utc).toLocaleString("pt-BR") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel title="Registro de conectores" subtitle="Status de todos os conectores configurados" defaultOpen={false} badgeCount={connectors?.items?.length ?? 0}>
        {!connectors?.items?.length ? (
          <StateBlock tone="empty" title="Sem conectores" message="Nenhum conector registrado." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Conector</th>
                  <th>Wave</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {connectors.items.map((item) => (
                  <tr key={item.connector_name}>
                    <td>{item.connector_name}</td>
                    <td>{item.wave}</td>
                    <td>{item.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>
    </div>
  );
}

