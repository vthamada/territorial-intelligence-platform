import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getConnectorRegistry } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const PAGE_SIZE = 20;

type ConnectorsFilters = {
  connectorName: string;
  source: string;
  wave: string;
  status: string;
  updatedFrom: string;
  updatedTo: string;
};

function makeEmptyFilters(): ConnectorsFilters {
  return {
    connectorName: "",
    source: "",
    wave: "",
    status: "",
    updatedFrom: "",
    updatedTo: ""
  };
}

export function OpsConnectorsPage() {
  const [draftFilters, setDraftFilters] = useState<ConnectorsFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<ConnectorsFilters>(makeEmptyFilters);
  const [page, setPage] = useState(1);

  const queryParams = useMemo(
    () => ({
      connector_name: appliedFilters.connectorName || undefined,
      source: appliedFilters.source || undefined,
      wave: appliedFilters.wave || undefined,
      status: appliedFilters.status || undefined,
      updated_from: appliedFilters.updatedFrom || undefined,
      updated_to: appliedFilters.updatedTo || undefined,
      page,
      page_size: PAGE_SIZE
    }),
    [appliedFilters, page]
  );

  const connectorsQuery = useQuery({
    queryKey: ["ops", "connector-registry", queryParams],
    queryFn: () => getConnectorRegistry(queryParams)
  });

  const totalPages = connectorsQuery.data ? Math.max(1, Math.ceil(connectorsQuery.data.total / PAGE_SIZE)) : 1;

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
      <Panel title="Registry de conectores" subtitle="Filtros por conector, fonte, wave, status e atualizacao">
        <form
          className="filter-grid"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Conector
            <input
              value={draftFilters.connectorName}
              onChange={(event) => setDraftFilters((old) => ({ ...old, connectorName: event.target.value }))}
              placeholder="labor_mte_fetch"
            />
          </label>
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
            <select value={draftFilters.wave} onChange={(event) => setDraftFilters((old) => ({ ...old, wave: event.target.value }))}>
              <option value="">Todas</option>
              <option value="MVP-1">MVP-1</option>
              <option value="MVP-2">MVP-2</option>
              <option value="MVP-3">MVP-3</option>
              <option value="MVP-4">MVP-4</option>
              <option value="MVP-5">MVP-5</option>
            </select>
          </label>
          <label>
            Status
            <select value={draftFilters.status} onChange={(event) => setDraftFilters((old) => ({ ...old, status: event.target.value }))}>
              <option value="">Todos</option>
              <option value="implemented">implemented</option>
              <option value="partial">partial</option>
              <option value="blocked">blocked</option>
              <option value="planned">planned</option>
            </select>
          </label>
          <label>
            Atualizado em
            <input
              type="datetime-local"
              value={draftFilters.updatedFrom}
              onChange={(event) => setDraftFilters((old) => ({ ...old, updatedFrom: event.target.value }))}
            />
          </label>
          <label>
            Atualizado ate
            <input
              type="datetime-local"
              value={draftFilters.updatedTo}
              onChange={(event) => setDraftFilters((old) => ({ ...old, updatedTo: event.target.value }))}
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        {connectorsQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando conectores" message="Consultando /v1/ops/connector-registry." />
        ) : connectorsQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(connectorsQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar conectores"
                message={message}
                requestId={requestId}
                onRetry={() => void connectorsQuery.refetch()}
              />
            );
          })()
        ) : connectorsQuery.data && connectorsQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem conectores" message="Nenhum conector encontrado para os filtros aplicados." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Conector</th>
                    <th>Fonte</th>
                    <th>Wave</th>
                    <th>Status</th>
                    <th>Atualizado</th>
                    <th>Notas</th>
                  </tr>
                </thead>
                <tbody>
                  {connectorsQuery.data?.items.map((item) => (
                    <tr key={`${item.wave}:${item.connector_name}`}>
                      <td>{item.connector_name}</td>
                      <td>{item.source}</td>
                      <td>{item.wave}</td>
                      <td>
                        <span className={`status-chip status-${item.status}`}>{item.status}</span>
                      </td>
                      <td>{new Date(item.updated_at_utc).toLocaleString("pt-BR")}</td>
                      <td>{item.notes ?? "-"}</td>
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
