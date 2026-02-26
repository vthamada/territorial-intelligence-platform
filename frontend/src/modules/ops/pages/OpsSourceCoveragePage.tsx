import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getOpsSourceCoverage } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

type CoverageFilters = {
  source: string;
  wave: string;
  referencePeriod: string;
  startedFrom: string;
  startedTo: string;
  includeInternal: boolean;
};

function makeEmptyFilters(): CoverageFilters {
  return {
    source: "",
    wave: "",
    referencePeriod: "",
    startedFrom: "",
    startedTo: "",
    includeInternal: false
  };
}

function toCoverageClass(status: string) {
  if (status === "ready") {
    return "status-success";
  }
  if (status === "blocked") {
    return "status-blocked";
  }
  if (status === "failed") {
    return "status-failed";
  }
  if (status === "idle") {
    return "status-planned";
  }
  return "status-partial";
}

export function OpsSourceCoveragePage() {
  const [draftFilters, setDraftFilters] = useState<CoverageFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<CoverageFilters>(makeEmptyFilters);

  const queryParams = useMemo(
    () => ({
      source: appliedFilters.source || undefined,
      wave: appliedFilters.wave || undefined,
      reference_period: appliedFilters.referencePeriod || undefined,
      started_from: appliedFilters.startedFrom || undefined,
      started_to: appliedFilters.startedTo || undefined,
      include_internal: appliedFilters.includeInternal
    }),
    [appliedFilters]
  );

  const coverageQuery = useQuery({
    queryKey: ["ops", "source-coverage", queryParams],
    queryFn: () => getOpsSourceCoverage(queryParams)
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
      <Panel title="Cobertura por fonte" subtitle="Evidencia se cada fonte implementada realmente possui dados">
        <form
          className="filter-grid"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Fonte
            <input
              value={draftFilters.source}
              onChange={(event) => setDraftFilters((old) => ({ ...old, source: event.target.value }))}
              placeholder="MTE"
            />
          </label>
          <label>
            Wave
            <select
              value={draftFilters.wave}
              onChange={(event) => setDraftFilters((old) => ({ ...old, wave: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="MVP-1">MVP-1</option>
              <option value="MVP-2">MVP-2</option>
              <option value="MVP-3">MVP-3</option>
              <option value="MVP-4">MVP-4</option>
              <option value="MVP-5">MVP-5</option>
            </select>
          </label>
          <label>
            Período
            <input
              value={draftFilters.referencePeriod}
              onChange={(event) => setDraftFilters((old) => ({ ...old, referencePeriod: event.target.value }))}
              placeholder="2025"
            />
          </label>
          <label>
            Runs de
            <input
              type="datetime-local"
              value={draftFilters.startedFrom}
              onChange={(event) => setDraftFilters((old) => ({ ...old, startedFrom: event.target.value }))}
            />
          </label>
          <label>
            Runs ate
            <input
              type="datetime-local"
              value={draftFilters.startedTo}
              onChange={(event) => setDraftFilters((old) => ({ ...old, startedTo: event.target.value }))}
            />
          </label>
          <label>
            <span>Incluir INTERNAL</span>
            <input
              type="checkbox"
              checked={draftFilters.includeInternal}
              onChange={(event) => setDraftFilters((old) => ({ ...old, includeInternal: event.target.checked }))}
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        {coverageQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando cobertura" message="Consultando /v1/ops/source-coverage." />
        ) : coverageQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(coverageQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar cobertura por fonte"
                message={message}
                requestId={requestId}
                onRetry={() => void coverageQuery.refetch()}
              />
            );
          })()
        ) : coverageQuery.data && coverageQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados de cobertura" message="Nenhuma fonte encontrada para os filtros aplicados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fonte</th>
                  <th>Wave</th>
                  <th>Conectores</th>
                  <th>Runs</th>
                  <th>Sucesso</th>
                  <th>Bloqueado</th>
                  <th>Falha</th>
                  <th>Rows loaded</th>
                  <th>Fact rows</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {coverageQuery.data?.items.map((item) => (
                  <tr key={`${item.wave}:${item.source}`}>
                    <td>{item.source}</td>
                    <td>{item.wave}</td>
                    <td>{item.implemented_connectors}</td>
                    <td>{item.runs_total}</td>
                    <td>{item.runs_success}</td>
                    <td>{item.runs_blocked}</td>
                    <td>{item.runs_failed}</td>
                    <td>{item.rows_loaded_total}</td>
                    <td>{item.fact_indicator_rows}</td>
                    <td>
                      <span className={`status-chip ${toCoverageClass(item.coverage_status)}`}>{item.coverage_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
