import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPipelineChecks } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const PAGE_SIZE = 20;

type ChecksFilters = {
  runId: string;
  jobName: string;
  status: string;
  checkName: string;
  createdFrom: string;
  createdTo: string;
};

function makeEmptyFilters(): ChecksFilters {
  return {
    runId: "",
    jobName: "",
    status: "",
    checkName: "",
    createdFrom: "",
    createdTo: ""
  };
}

export function OpsChecksPage() {
  const [draftFilters, setDraftFilters] = useState<ChecksFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<ChecksFilters>(makeEmptyFilters);
  const [page, setPage] = useState(1);

  const queryParams = useMemo(
    () => ({
      run_id: appliedFilters.runId || undefined,
      job_name: appliedFilters.jobName || undefined,
      status: appliedFilters.status || undefined,
      check_name: appliedFilters.checkName || undefined,
      created_from: appliedFilters.createdFrom || undefined,
      created_to: appliedFilters.createdTo || undefined,
      page,
      page_size: PAGE_SIZE
    }),
    [appliedFilters, page]
  );

  const checksQuery = useQuery({
    queryKey: ["ops", "pipeline-checks", queryParams],
    queryFn: () => getPipelineChecks(queryParams)
  });

  const totalPages = checksQuery.data ? Math.max(1, Math.ceil(checksQuery.data.total / PAGE_SIZE)) : 1;

  function applyFilters() {
    setPage(1);
    setAppliedFilters(draftFilters);
  }

  function clearFilters() {
    const cleared = makeEmptyFilters();
    setPage(1);
    setDraftFilters(cleared);
    setAppliedFilters(cleared);
  }

  return (
    <div className="page-grid">
      <Panel title="Checks de pipeline" subtitle="Filtros por run, job, check e janela temporal">
        <form
          className="filter-grid"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Run ID
            <input
              value={draftFilters.runId}
              onChange={(event) => setDraftFilters((old) => ({ ...old, runId: event.target.value }))}
              placeholder="UUID da execucao"
            />
          </label>
          <label>
            Job
            <input
              value={draftFilters.jobName}
              onChange={(event) => setDraftFilters((old) => ({ ...old, jobName: event.target.value }))}
              placeholder="labor_mte_fetch"
            />
          </label>
          <label>
            Status
            <select value={draftFilters.status} onChange={(event) => setDraftFilters((old) => ({ ...old, status: event.target.value }))}>
              <option value="">Todos</option>
              <option value="pass">pass</option>
              <option value="warn">warn</option>
              <option value="fail">fail</option>
            </select>
          </label>
          <label>
            Check
            <input
              value={draftFilters.checkName}
              onChange={(event) => setDraftFilters((old) => ({ ...old, checkName: event.target.value }))}
              placeholder="mte_data_source_resolved"
            />
          </label>
          <label>
            Criado em
            <input
              type="datetime-local"
              value={draftFilters.createdFrom}
              onChange={(event) => setDraftFilters((old) => ({ ...old, createdFrom: event.target.value }))}
            />
          </label>
          <label>
            Criado ate
            <input
              type="datetime-local"
              value={draftFilters.createdTo}
              onChange={(event) => setDraftFilters((old) => ({ ...old, createdTo: event.target.value }))}
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        {checksQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando checks" message="Consultando /v1/ops/pipeline-checks." />
        ) : checksQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(checksQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar checks"
                message={message}
                requestId={requestId}
                onRetry={() => void checksQuery.refetch()}
              />
            );
          })()
        ) : checksQuery.data && checksQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem checks" message="Nenhum check encontrado para os filtros aplicados." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Criado</th>
                    <th>Job</th>
                    <th>Check</th>
                    <th>Status</th>
                    <th>Valor</th>
                    <th>Threshold</th>
                  </tr>
                </thead>
                <tbody>
                  {checksQuery.data?.items.map((item) => (
                    <tr key={item.check_id}>
                      <td>{new Date(item.created_at_utc).toLocaleString("pt-BR")}</td>
                      <td>{item.job_name}</td>
                      <td>{item.check_name}</td>
                      <td>
                        <span className={`status-chip status-${item.status}`}>{item.status}</span>
                      </td>
                      <td>{item.observed_value ?? "-"}</td>
                      <td>{item.threshold_value ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination-row">
              <button type="button" className="button-secondary" disabled={page <= 1} onClick={() => setPage((old) => old - 1)}>
                Anterior
              </button>
              <span>
                Pagina {page} de {totalPages}
              </span>
              <button
                type="button"
                className="button-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((old) => old + 1)}
              >
                Proxima
              </button>
            </div>
          </>
        )}
      </Panel>
    </div>
  );
}
