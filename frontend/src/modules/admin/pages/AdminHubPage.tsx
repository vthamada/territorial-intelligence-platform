import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAdminSyncHistory,
  getAdminSyncStatus,
  getOpsReadiness,
  startAdminSync
} from "../../../shared/api/ops";
import { getMapLayers, getMapLayersCoverage } from "../../../shared/api/domain";
import { ApiClientError, formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";
import type {
  AdminSyncHistoryItem,
  AdminSyncJobStatus,
  MapLayersCoverageResponse,
  MapLayersResponse,
  OpsReadinessResponse
} from "../../../shared/api/types";

type AdminRouteLink = {
  to: string;
  label: string;
  description: string;
  icon: string;
};

const adminLinks: AdminRouteLink[] = [
  {
    to: "/ops/health",
    label: "Saúde Ops",
    description: "Saúde da API, banco e volume operacional.",
    icon: "[+]"
  },
  {
    to: "/ops/runs",
    label: "Execuções",
    description: "Histórico de runs de pipeline com filtros e paginação.",
    icon: ">>"
  },
  {
    to: "/ops/checks",
    label: "Checks",
    description: "Resultados dos checks de qualidade e operação.",
    icon: "[ok]"
  },
  {
    to: "/ops/connectors",
    label: "Conectores",
    description: "Registry de conectores e status por onda.",
    icon: "[=]"
  },
  {
    to: "/ops/frontend-events",
    label: "Eventos Frontend",
    description: "Telemetria de erros, web vitals e chamadas API do cliente.",
    icon: "[~]"
  },
  {
    to: "/ops/source-coverage",
    label: "Cobertura por Fonte",
    description: "Mostra se as fontes implementadas estão com dados carregados no Silver.",
    icon: "[#]"
  },
  {
    to: "/ops/layers",
    label: "Rastreabilidade de Camadas",
    description: "Catálogo territorial, cobertura de geometria e checks de qualidade por camada.",
    icon: "[map]"
  },
  {
    to: "/territory/indicators",
    label: "Territórios e Indicadores",
    description: "Consulta técnica para depuração de dados territoriais.",
    icon: "[pin]"
  }
];

type QueryErrorStateProps = {
  title: string;
  error: unknown;
  onRetry: () => void;
};

function QueryErrorState({ title, error, onRetry }: QueryErrorStateProps) {
  const { message, requestId } = formatApiError(error);
  return <StateBlock tone="error" title={title} message={message} requestId={requestId} onRetry={onRetry} />;
}

function formatAdminSyncError(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.status === 404) {
      return {
        message: "Backend sem suporte à operação assistida. Atualize e reinicie a API.",
        requestId: error.requestId
      };
    }
    if (error.status === 403) {
      return {
        message: "Acesso administrativo negado. Verifique o token configurado para o Admin.",
        requestId: error.requestId
      };
    }
  }
  return formatApiError(error);
}

function AdminSyncErrorState({ title, error, onRetry }: QueryErrorStateProps) {
  const { message, requestId } = formatAdminSyncError(error);
  return <StateBlock tone="error" title={title} message={message} requestId={requestId} onRetry={onRetry} />;
}

function formatAdminStepLabel(stepName: string) {
  return stepName
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function getSyncModeLabel(mode: AdminSyncJobStatus["mode"] | AdminSyncHistoryItem["mode"]) {
  return mode === "sync" ? "Sincronização" : "Validação";
}

function getStepStatusTone(status: string) {
  if (status === "success") {
    return "status-success";
  }
  if (status === "failed") {
    return "status-warn";
  }
  return "";
}

function AdminSyncHistoryTable() {
  const historyQuery = useQuery({
    queryKey: ["ops", "admin-sync", "history"],
    queryFn: () => getAdminSyncHistory({ page: 1, page_size: 10 }),
    staleTime: 10_000,
    refetchOnWindowFocus: false,
  });

  if (historyQuery.isPending) {
    return <p className="panel-subtitle">Carregando histórico de execuções...</p>;
  }

  if (historyQuery.error) {
    return (
      <AdminSyncErrorState
        title="Falha ao carregar histórico da operação assistida"
        error={historyQuery.error}
        onRetry={() => void historyQuery.refetch()}
      />
    );
  }

  if ((historyQuery.data?.items.length ?? 0) === 0) {
    return (
      <StateBlock
        tone="empty"
        title="Sem histórico persistido"
        message="As próximas execuções administrativas ficarão registradas em ops.admin_sync_jobs."
      />
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Modo</th>
            <th>Status</th>
            <th>Etapa atual</th>
            <th>Início</th>
            <th>Fim</th>
          </tr>
        </thead>
        <tbody>
          {historyQuery.data?.items.map((item) => (
            <tr key={item.job_id}>
              <td>{item.job_id}</td>
              <td>{getSyncModeLabel(item.mode)}</td>
              <td>
                <span className={`status-chip ${getStepStatusTone(item.status)}`}>{item.status}</span>
              </td>
              <td>{item.current_step ? formatAdminStepLabel(item.current_step) : "-"}</td>
              <td>{item.started_at_utc}</td>
              <td>{item.finished_at_utc ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdminSyncPanel() {
  const queryClient = useQueryClient();
  const syncStatusQuery = useQuery({
    queryKey: ["ops", "admin-sync", "status"],
    queryFn: () => getAdminSyncStatus(),
    staleTime: 5_000,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => (query.state.data?.job?.is_active ? 3_000 : false),
  });

  const syncMutation = useMutation({
    mutationFn: startAdminSync,
    onSuccess: (job) => {
      queryClient.setQueryData(["ops", "admin-sync", "status"], { job });
      void queryClient.invalidateQueries({ queryKey: ["ops", "admin-sync"] });
    },
  });

  const currentJob = syncStatusQuery.data?.job ?? null;
  const hasActiveJob = currentJob?.is_active ?? false;
  const isSubmitting = syncMutation.isPending;

  const handleStart = async (mode: "validate" | "sync") => {
    if (mode === "sync") {
      const confirmed = window.confirm(
        "A sincronização vai executar a rotina oficial de equalização do ambiente. Deseja continuar?",
      );
      if (!confirmed) {
        return;
      }
    }
    await syncMutation.mutateAsync({
      mode,
      include_wave7: true,
      allow_backfill_blocked: true,
    });
  };

  if (syncStatusQuery.isPending) {
    return <p className="panel-subtitle">Verificando operação assistida...</p>;
  }

  if (syncStatusQuery.error) {
    return (
      <AdminSyncErrorState
        title="Falha ao carregar status da operação assistida"
        error={syncStatusQuery.error}
        onRetry={() => void syncStatusQuery.refetch()}
      />
    );
  }

  return (
    <div data-testid="admin-sync-panel">
      <div className="filter-actions">
        <button
          type="button"
          onClick={() => void handleStart("validate")}
          disabled={hasActiveJob || isSubmitting}
        >
          Validar ambiente
        </button>
        <button
          type="button"
          className="button-secondary"
          onClick={() => void handleStart("sync")}
          disabled={hasActiveJob || isSubmitting}
        >
          Sincronizar ambiente
        </button>
      </div>
      {syncMutation.error ? (
        <AdminSyncErrorState
          title="Falha ao iniciar operação assistida"
          error={syncMutation.error}
          onRetry={() => syncMutation.reset()}
        />
      ) : null}
      {currentJob ? (
        <>
          <div className="kpi-grid">
            <article>
              <span>Modo</span>
              <strong>{getSyncModeLabel(currentJob.mode)}</strong>
            </article>
            <article>
              <span>Status</span>
              <strong>{currentJob.status}</strong>
            </article>
            <article>
              <span>Etapa atual</span>
              <strong>{currentJob.current_step ? formatAdminStepLabel(currentJob.current_step) : "-"}</strong>
            </article>
            <article>
              <span>Início</span>
              <strong>{currentJob.started_at_utc}</strong>
            </article>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Etapa</th>
                  <th>Status</th>
                  <th>Exit code</th>
                  <th>Resumo</th>
                </tr>
              </thead>
              <tbody>
                {currentJob.steps.map((step) => (
                  <tr key={step.name}>
                    <td>{formatAdminStepLabel(step.name)}</td>
                    <td>
                      <span className={`status-chip ${getStepStatusTone(step.status)}`}>{step.status}</span>
                    </td>
                    <td>{step.exit_code ?? "-"}</td>
                    <td>{step.summary ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <p className="panel-subtitle">Última mensagem: {currentJob.last_message ?? "-"}</p>
            <pre
              style={{
                maxHeight: "14rem",
                overflow: "auto",
                margin: 0,
                padding: "0.85rem 1rem",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-md)",
                background: "var(--bg-subtle)",
                fontSize: "0.78rem",
                whiteSpace: "pre-wrap",
              }}
            >
              {currentJob.recent_logs.length > 0 ? currentJob.recent_logs.join("\n") : "Sem logs recentes."}
            </pre>
          </div>
          <div>
            <h3 style={{ marginBottom: "0.5rem" }}>Histórico recente</h3>
            <AdminSyncHistoryTable />
          </div>
        </>
      ) : (
        <>
          <StateBlock
            tone="empty"
            title="Nenhuma execução administrativa registrada"
            message="Use Validar ambiente para rodar checks sem escrita ou Sincronizar ambiente para disparar a rotina oficial de equalização."
          />
          <div>
            <h3 style={{ marginBottom: "0.5rem" }}>Histórico recente</h3>
            <AdminSyncHistoryTable />
          </div>
        </>
      )}
    </div>
  );
}

function ReadinessBanner() {
  const readinessQuery = useQuery({
    queryKey: ["ops", "readiness", "admin-hub"],
    queryFn: () =>
      getOpsReadiness({
        window_days: 7,
        health_window_days: 1,
        slo1_target_pct: 95
      }),
    staleTime: 60_000,
    refetchOnWindowFocus: false
  });

  if (readinessQuery.isPending) {
    return <p className="panel-subtitle">Verificando readiness...</p>;
  }

  if (readinessQuery.error) {
    return (
      <QueryErrorState
        title="Falha ao carregar readiness"
        error={readinessQuery.error}
        onRetry={() => void readinessQuery.refetch()}
      />
    );
  }

  const data = readinessQuery.data as OpsReadinessResponse;
  const isReady = data.status === "READY";
  const slo1HistRate = data.slo1.total_runs > 0
    ? `${((data.slo1.successful_runs / data.slo1.total_runs) * 100).toFixed(1)}%`
    : "-";
  const slo1CurrRate = data.slo1_current.total_runs > 0
    ? `${((data.slo1_current.successful_runs / data.slo1_current.total_runs) * 100).toFixed(1)}%`
    : "-";

  return (
    <div data-testid="readiness-banner">
      <div className="kpi-grid">
        <article>
          <span>Readiness</span>
          <strong className={isReady ? "" : "map-export-error"}>{data.status}</strong>
        </article>
        <article>
          <span>Conectores</span>
          <strong>{data.connector_registry.total}</strong>
        </article>
        <article>
          <span>SLO-1 (7d)</span>
          <strong>{slo1HistRate}</strong>
        </article>
        <article>
          <span>SLO-1 (1d)</span>
          <strong>{slo1CurrRate}</strong>
        </article>
        <article>
          <span>Hard failures</span>
          <strong>{data.hard_failures.length}</strong>
        </article>
        <article>
          <span>Warnings</span>
          <strong>{data.warnings.length}</strong>
        </article>
      </div>
      {data.hard_failures.length > 0 ? (
        <p className="map-export-error">Hard failures: {data.hard_failures.join(" | ")}</p>
      ) : null}
      {data.warnings.length > 0 ? (
        <p className="panel-subtitle">Warnings: {data.warnings.join(" | ")}</p>
      ) : null}
    </div>
  );
}

function LayerCoverageBanner() {
  const mapLayersQuery = useQuery({
    queryKey: ["map", "layers", "catalog", "admin-hub"],
    queryFn: () => getMapLayers(),
    staleTime: 60_000,
    refetchOnWindowFocus: false
  });

  const coverageQuery = useQuery({
    queryKey: ["map", "layers", "coverage", "admin-hub"],
    queryFn: () => getMapLayersCoverage(),
    staleTime: 60_000,
    refetchOnWindowFocus: false
  });

  if (mapLayersQuery.isPending || coverageQuery.isPending) {
    return <p className="panel-subtitle">Carregando cobertura das camadas...</p>;
  }

  if (mapLayersQuery.error || coverageQuery.error) {
    return (
      <QueryErrorState
        title="Falha ao carregar cobertura das camadas"
        error={mapLayersQuery.error ?? coverageQuery.error}
        onRetry={() => {
          void mapLayersQuery.refetch();
          void coverageQuery.refetch();
        }}
      />
    );
  }

  const catalog = mapLayersQuery.data as MapLayersResponse;
  const coverage = coverageQuery.data as MapLayersCoverageResponse;

  const layerLabelById = new Map(catalog.items.map((item) => [item.id, item.label]));
  const orderedItems = [...coverage.items].sort((a, b) => {
    const indexA = catalog.items.findIndex((item) => item.id === a.layer_id);
    const indexB = catalog.items.findIndex((item) => item.id === b.layer_id);
    return indexA - indexB;
  });

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Camada</th>
            <th>Nível</th>
            <th>Total</th>
            <th>Com geometria</th>
            <th>Com indicador</th>
            <th>Status</th>
            <th>Observação</th>
          </tr>
        </thead>
        <tbody>
          {orderedItems.map((item) => (
            <tr key={item.layer_id}>
              <td>{layerLabelById.get(item.layer_id) ?? item.layer_id}</td>
              <td>{item.territory_level}</td>
              <td>{item.territories_total}</td>
              <td>{item.territories_with_geometry}</td>
              <td>{item.territories_with_indicator}</td>
              <td>
                <span className={`status-chip ${item.is_ready ? "status-success" : "status-warn"}`}>
                  {item.is_ready ? "ready" : "pending"}
                </span>
              </td>
              <td>{item.notes ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdminHubPage() {
  return (
    <div className="page-grid">
      <Panel title="Admin técnico" subtitle="Camada operacional separada do fluxo executivo do QG">
        <p className="panel-subtitle">
          Use esta área para operação de dados, validação de execuções e troubleshooting técnico.
        </p>
      </Panel>

      <Panel title="Readiness operacional" subtitle="Estado consolidado do backend e pipelines">
        <ReadinessBanner />
      </Panel>

      <Panel title="Cobertura das camadas de mapa" subtitle="Base territorial para o stack de mapas">
        <LayerCoverageBanner />
      </Panel>

      <Panel title="Operação assistida do ambiente" subtitle="Validação e sincronização governadas a partir do Admin">
        <AdminSyncPanel />
      </Panel>

      <Panel title="Ferramentas operacionais" subtitle="Atalhos para monitoramento e suporte técnico">
        <div className="admin-link-grid">
          {adminLinks.map((item) => (
            <article key={item.to} className="admin-link-card">
              <div className="admin-card-header">
                <span className="admin-card-icon" aria-hidden="true">{item.icon}</span>
                <h3>{item.label}</h3>
              </div>
              <p>{item.description}</p>
              <Link className="inline-link" to={item.to}>
                Abrir {item.label}
              </Link>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
