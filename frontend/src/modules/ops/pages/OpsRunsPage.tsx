import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPipelineRuns } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const PAGE_SIZE = 20;

export function OpsRunsPage() {
  const [jobName, setJobName] = useState("");
  const [runStatus, setRunStatus] = useState("");
  const [wave, setWave] = useState("");
  const [startedFrom, setStartedFrom] = useState("");
  const [startedTo, setStartedTo] = useState("");
  const [page, setPage] = useState(1);

  const queryParams = useMemo(
    () => ({
      job_name: jobName || undefined,
      status: runStatus || undefined,
      wave: wave || undefined,
      started_from: startedFrom || undefined,
      started_to: startedTo || undefined,
      page,
      page_size: PAGE_SIZE
    }),
    [jobName, page, runStatus, startedFrom, startedTo, wave]
  );

  const runsQuery = useQuery({
    queryKey: ["ops", "pipeline-runs", queryParams],
    queryFn: () => getPipelineRuns(queryParams)
  });

  const totalPages = runsQuery.data ? Math.max(1, Math.ceil(runsQuery.data.total / PAGE_SIZE)) : 1;

  return (
    <div className="page-grid">
      <Panel title="Execucoes de pipeline" subtitle="Filtros por job, status e janela temporal">
        <form
          className="filter-grid"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            void runsQuery.refetch();
          }}
        >
          <label>
            Job
            <input value={jobName} onChange={(event) => setJobName(event.target.value)} placeholder="labor_mte_fetch" />
          </label>
          <label>
            Status
            <select value={runStatus} onChange={(event) => setRunStatus(event.target.value)}>
              <option value="">Todos</option>
              <option value="success">success</option>
              <option value="blocked">blocked</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label>
            Wave
            <select value={wave} onChange={(event) => setWave(event.target.value)}>
              <option value="">Todas</option>
              <option value="MVP-1">MVP-1</option>
              <option value="MVP-2">MVP-2</option>
              <option value="MVP-3">MVP-3</option>
            </select>
          </label>
          <label>
            Inicio em
            <input type="datetime-local" value={startedFrom} onChange={(event) => setStartedFrom(event.target.value)} />
          </label>
          <label>
            Inicio ate
            <input type="datetime-local" value={startedTo} onChange={(event) => setStartedTo(event.target.value)} />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
          </div>
        </form>

        {runsQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando execucoes" message="Consultando /v1/ops/pipeline-runs." />
        ) : runsQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(runsQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar execucoes"
                message={message}
                requestId={requestId}
                onRetry={() => void runsQuery.refetch()}
              />
            );
          })()
        ) : runsQuery.data && runsQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem execucoes" message="Nenhum registro encontrado para os filtros aplicados." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Inicio</th>
                    <th>Job</th>
                    <th>Status</th>
                    <th>Wave</th>
                    <th>Rows loaded</th>
                    <th>Duracao (s)</th>
                  </tr>
                </thead>
                <tbody>
                  {runsQuery.data?.items.map((item) => (
                    <tr key={item.run_id}>
                      <td>{new Date(item.started_at_utc).toLocaleString("pt-BR")}</td>
                      <td>{item.job_name}</td>
                      <td>
                        <span className={`status-chip status-${item.status}`}>{item.status}</span>
                      </td>
                      <td>{item.wave}</td>
                      <td>{item.rows_loaded}</td>
                      <td>{item.duration_seconds ?? "-"}</td>
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
