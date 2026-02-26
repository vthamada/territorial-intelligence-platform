import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getOpsReadiness } from "../../../shared/api/ops";
import { getMapLayers, getMapLayersCoverage } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";
import type {
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
    icon: "🩺"
  },
  {
    to: "/ops/runs",
    label: "Execuções",
    description: "Histórico de runs de pipeline com filtros e paginação.",
    icon: "▶️"
  },
  {
    to: "/ops/checks",
    label: "Checks",
    description: "Resultados dos checks de qualidade e operação.",
    icon: "✅"
  },
  {
    to: "/ops/connectors",
    label: "Conectores",
    description: "Registry de conectores e status por onda.",
    icon: "🔌"
  },
  {
    to: "/ops/frontend-events",
    label: "Eventos Frontend",
    description: "Telemetria de erros, web vitals e chamadas API do cliente.",
    icon: "📡"
  },
  {
    to: "/ops/source-coverage",
    label: "Cobertura por Fonte",
    description: "Mostra se as fontes implementadas estao com dados carregados no Silver.",
    icon: "📊"
  },
  {
    to: "/ops/layers",
    label: "Rastreabilidade de Camadas",
    description: "Catalogo territorial, cobertura de geometria e checks de qualidade por camada.",
    icon: "🗺️"
  },
  {
    to: "/territory/indicators",
    label: "Territórios e Indicadores",
    description: "Consulta técnica para depuracao de dados territoriais.",
    icon: "📍"
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
    return <p className="panel-subtitle">Carregando cobertura de camadas...</p>;
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
            <th>Observacao</th>
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
          Use esta area para operação de dados, validação de execuções e troubleshooting técnico.
        </p>
      </Panel>

      <Panel title="Readiness operacional" subtitle="Estado consolidado do backend e pipelines">
        <ReadinessBanner />
      </Panel>

      <Panel title="Cobertura das camadas de mapa" subtitle="Base territorial para o stack de mapas">
        <LayerCoverageBanner />
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
