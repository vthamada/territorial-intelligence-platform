import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMapLayersReadiness } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import type { MapLayerReadinessItem } from "../../../shared/api/types";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

type LayerFilters = {
  metric: string;
  period: string;
  scope: "territorial" | "all" | "urban";
};

function makeEmptyFilters(): LayerFilters {
  return {
    metric: "",
    period: "",
    scope: "territorial"
  };
}

function toStatusClass(status: string) {
  if (status === "pass") {
    return "status-pass";
  }
  if (status === "warn") {
    return "status-warn";
  }
  if (status === "fail") {
    return "status-fail";
  }
  return "status-planned";
}

function toOfficialClass(status: string) {
  if (status === "official") {
    return "status-implemented";
  }
  if (status === "hybrid") {
    return "status-partial";
  }
  return "status-planned";
}

function countByStatus(items: MapLayerReadinessItem[]) {
  const counts = {
    pass: 0,
    warn: 0,
    fail: 0,
    pending: 0
  };
  for (const item of items) {
    if (item.readiness_status === "pass") {
      counts.pass += 1;
    } else if (item.readiness_status === "warn") {
      counts.warn += 1;
    } else if (item.readiness_status === "fail") {
      counts.fail += 1;
    } else {
      counts.pending += 1;
    }
  }
  return counts;
}

export function OpsLayersPage() {
  const [draftFilters, setDraftFilters] = useState<LayerFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<LayerFilters>(makeEmptyFilters);

  const queryParams = useMemo(
    () => ({
      metric: appliedFilters.metric || undefined,
      period: appliedFilters.period || undefined,
      include_urban: appliedFilters.scope === "all" || appliedFilters.scope === "urban"
    }),
    [appliedFilters]
  );

  const readinessQuery = useQuery({
    queryKey: ["map", "layers", "readiness", queryParams],
    queryFn: () => getMapLayersReadiness(queryParams)
  });

  const displayedItems = useMemo(() => {
    const items = readinessQuery.data?.items ?? [];
    if (appliedFilters.scope === "urban") {
      return items.filter((item) => item.layer.territory_level === "urban");
    }
    return items;
  }, [appliedFilters.scope, readinessQuery.data?.items]);

  const hasResults = displayedItems.length > 0;
  const statusCounts = useMemo(() => countByStatus(displayedItems), [displayedItems]);
  const degradedItems = useMemo(
    () => displayedItems.filter((item) => item.readiness_status === "fail" || item.readiness_status === "warn" || item.readiness_status === "pending"),
    [displayedItems],
  );
  const hasHardDegradation = degradedItems.some((item) => item.readiness_status === "fail");

  function applyFilters() {
    setAppliedFilters(draftFilters);
  }

  function clearFilters() {
    const cleared = makeEmptyFilters();
    setDraftFilters(cleared);
    setAppliedFilters(cleared);
  }

  return (
    <div className="page-grid">
      <Panel title="Rastreabilidade de camadas" subtitle="Catalogo, cobertura e checks de qualidade por camada">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Codigo do indicador
            <input
              value={draftFilters.metric}
              onChange={(event) => setDraftFilters((old) => ({ ...old, metric: event.target.value }))}
              placeholder="DATASUS_APS_COBERTURA"
            />
          </label>
          <label>
            Período
            <input
              value={draftFilters.period}
              onChange={(event) => setDraftFilters((old) => ({ ...old, period: event.target.value }))}
              placeholder="2025"
            />
          </label>
          <label>
            Escopo
            <select
              value={draftFilters.scope}
              onChange={(event) =>
                setDraftFilters((old) => ({ ...old, scope: event.target.value as LayerFilters["scope"] }))
              }
            >
              <option value="territorial">Territorial</option>
              <option value="all">Territorial + Urbano</option>
              <option value="urban">Somente urbano</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        {readinessQuery.isPending ? (
          <StateBlock
            tone="loading"
            title="Carregando rastreabilidade de camadas"
            message="Consultando /v1/map/layers/readiness."
          />
        ) : readinessQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(readinessQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar rastreabilidade de camadas"
                message={message}
                requestId={requestId}
                onRetry={() => void readinessQuery.refetch()}
              />
            );
          })()
        ) : !hasResults ? (
          <StateBlock tone="empty" title="Sem camadas" message="Nenhuma camada retornada pelo endpoint de readiness." />
        ) : (
          <>
            {degradedItems.length > 0 ? (
              <section
                className={`ops-degradation-alert ${hasHardDegradation ? "ops-degradation-critical" : "ops-degradation-warning"}`}
                role={hasHardDegradation ? "alert" : "status"}
                aria-live="polite"
              >
                <h3>Degradacao de camadas detectada</h3>
                <p>
                  {statusCounts.fail} fail | {statusCounts.warn} warn | {statusCounts.pending} pending
                </p>
                <ul className="ops-degradation-list">
                  {degradedItems.slice(0, 6).map((item) => (
                    <li key={`degradation-${item.layer.id}`}>
                      <strong>{item.layer.label}</strong>: {item.readiness_reason ?? item.coverage.notes ?? "Sem detalhe"}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            <p className="panel-subtitle">
              Run de qualidade: {readinessQuery.data?.quality_run_id ?? "-"} | iniciado em{" "}
              {readinessQuery.data?.quality_run_started_at_utc
                ? new Date(readinessQuery.data.quality_run_started_at_utc).toLocaleString("pt-BR")
                : "-"}
            </p>
            <div className="kpi-grid">
              <article>
                <span>Camadas no recorte</span>
                <strong>{displayedItems.length}</strong>
              </article>
              <article>
                <span>Readiness pass</span>
                <strong>{statusCounts.pass}</strong>
              </article>
              <article>
                <span>Readiness warn</span>
                <strong>{statusCounts.warn}</strong>
              </article>
              <article>
                <span>Readiness fail</span>
                <strong>{statusCounts.fail}</strong>
              </article>
              <article>
                <span>Readiness pending</span>
                <strong>{statusCounts.pending}</strong>
              </article>
            </div>
            <h3>Resumo rapido das camadas</h3>
            <div className="ops-layer-check-grid" aria-label="Resumo rapido das camadas">
              {displayedItems.map((item) => (
                <article key={`summary-${item.layer.id}`} className="ops-layer-check-card">
                  <header>
                    <strong>{item.layer.label}</strong>
                    <small>{item.layer.territory_level}</small>
                  </header>
                  <p className="ops-layer-check-meta">
                    cobertura: {item.coverage.territories_with_geometry}/{item.coverage.territories_total} geom |{" "}
                    {item.coverage.territories_with_indicator} indicador
                  </p>
                  <div className="ops-layer-check-chips">
                    <span className={`status-chip ${toStatusClass(item.row_check?.status ?? "pending")}`}>
                      rows: {item.row_check?.status ?? "pending"}
                    </span>
                    <span className={`status-chip ${toStatusClass(item.geometry_check?.status ?? "pending")}`}>
                      geom: {item.geometry_check?.status ?? "pending"}
                    </span>
                    <span className={`status-chip ${toStatusClass(item.readiness_status)}`}>
                      readiness: {item.readiness_status}
                    </span>
                  </div>
                  <p className="ops-layer-check-reason">{item.readiness_reason ?? item.coverage.notes ?? "-"}</p>
                </article>
              ))}
            </div>
            <div className="table-wrap">
              <table aria-label="Rastreabilidade de camadas">
                <thead>
                  <tr>
                    <th>Camada</th>
                    <th>Nível</th>
                    <th>Classificacao</th>
                    <th>Cobertura</th>
                    <th>Rows check</th>
                    <th>Geometry check</th>
                    <th>Readiness</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedItems.map((item: MapLayerReadinessItem) => (
                    <tr key={item.layer.id}>
                      <td>{item.layer.label}</td>
                      <td>{item.layer.territory_level}</td>
                      <td>
                        <span className={`status-chip ${toOfficialClass(item.layer.official_status ?? "proxy")}`}>
                          {item.layer.official_status ?? "proxy"}
                        </span>
                      </td>
                      <td>
                        {item.coverage.territories_with_geometry}/{item.coverage.territories_total} geom |{" "}
                        {item.coverage.territories_with_indicator} indicador
                      </td>
                      <td>
                        <span className={`status-chip ${toStatusClass(item.row_check?.status ?? "pending")}`}>
                          {item.row_check?.status ?? "pending"}
                        </span>
                      </td>
                      <td>
                        <span className={`status-chip ${toStatusClass(item.geometry_check?.status ?? "pending")}`}>
                          {item.geometry_check?.status ?? "pending"}
                        </span>
                      </td>
                      <td>
                        <span className={`status-chip ${toStatusClass(item.readiness_status)}`}>
                          {item.readiness_status}
                        </span>
                      </td>
                      <td>{item.readiness_reason ?? item.coverage.notes ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Panel>
    </div>
  );
}
