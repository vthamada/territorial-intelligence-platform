import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTerritoryLayersReadiness } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

type LayerFilters = {
  metric: string;
  period: string;
};

function makeEmptyFilters(): LayerFilters {
  return {
    metric: "",
    period: ""
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

export function OpsLayersPage() {
  const [draftFilters, setDraftFilters] = useState<LayerFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<LayerFilters>(makeEmptyFilters);

  const queryParams = useMemo(
    () => ({
      metric: appliedFilters.metric || undefined,
      period: appliedFilters.period || undefined
    }),
    [appliedFilters]
  );

  const readinessQuery = useQuery({
    queryKey: ["territory", "layers", "readiness", queryParams],
    queryFn: () => getTerritoryLayersReadiness(queryParams)
  });

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
            Periodo
            <input
              value={draftFilters.period}
              onChange={(event) => setDraftFilters((old) => ({ ...old, period: event.target.value }))}
              placeholder="2025"
            />
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
            message="Consultando /v1/territory/layers/readiness."
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
        ) : readinessQuery.data && readinessQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem camadas" message="Nenhuma camada retornada pelo endpoint de readiness." />
        ) : (
          <>
            <p className="panel-subtitle">
              Run de qualidade: {readinessQuery.data?.quality_run_id ?? "-"} | iniciado em{" "}
              {readinessQuery.data?.quality_run_started_at_utc
                ? new Date(readinessQuery.data.quality_run_started_at_utc).toLocaleString("pt-BR")
                : "-"}
            </p>
            <div className="table-wrap">
              <table aria-label="Rastreabilidade de camadas territoriais">
                <thead>
                  <tr>
                    <th>Camada</th>
                    <th>Nivel</th>
                    <th>Classificacao</th>
                    <th>Cobertura</th>
                    <th>Rows check</th>
                    <th>Geometry check</th>
                    <th>Readiness</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {readinessQuery.data?.items.map((item) => (
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
