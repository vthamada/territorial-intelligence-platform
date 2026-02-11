import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getFrontendEvents } from "../../../shared/api/ops";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const PAGE_SIZE = 20;

type FrontendEventsFilters = {
  category: string;
  severity: string;
  name: string;
  eventFrom: string;
  eventTo: string;
};

function makeEmptyFilters(): FrontendEventsFilters {
  return {
    category: "",
    severity: "",
    name: "",
    eventFrom: "",
    eventTo: ""
  };
}

function severityToChip(severity: string) {
  if (severity === "error") {
    return "fail";
  }
  if (severity === "warn") {
    return "warn";
  }
  return "pass";
}

function renderAttributes(attributes: Record<string, unknown> | null): string {
  if (!attributes || Object.keys(attributes).length === 0) {
    return "-";
  }
  const compact = JSON.stringify(attributes);
  if (compact.length <= 120) {
    return compact;
  }
  return `${compact.slice(0, 117)}...`;
}

export function OpsFrontendEventsPage() {
  const [draftFilters, setDraftFilters] = useState<FrontendEventsFilters>(makeEmptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<FrontendEventsFilters>(makeEmptyFilters);
  const [page, setPage] = useState(1);

  const queryParams = useMemo(
    () => ({
      category: appliedFilters.category || undefined,
      severity: appliedFilters.severity || undefined,
      name: appliedFilters.name || undefined,
      event_from: appliedFilters.eventFrom || undefined,
      event_to: appliedFilters.eventTo || undefined,
      page,
      page_size: PAGE_SIZE
    }),
    [appliedFilters, page]
  );

  const eventsQuery = useQuery({
    queryKey: ["ops", "frontend-events", queryParams],
    queryFn: () => getFrontendEvents(queryParams)
  });

  const totalPages = eventsQuery.data ? Math.max(1, Math.ceil(eventsQuery.data.total / PAGE_SIZE)) : 1;

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
      <Panel title="Eventos frontend" subtitle="Erros, web vitals e telemetria de chamadas API">
        <form
          className="filter-grid"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Categoria
            <select
              value={draftFilters.category}
              onChange={(event) => setDraftFilters((old) => ({ ...old, category: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="api_request">api_request</option>
              <option value="frontend_error">frontend_error</option>
              <option value="web_vital">web_vital</option>
              <option value="performance">performance</option>
              <option value="lifecycle">lifecycle</option>
            </select>
          </label>
          <label>
            Severidade
            <select
              value={draftFilters.severity}
              onChange={(event) => setDraftFilters((old) => ({ ...old, severity: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="error">error</option>
              <option value="warn">warn</option>
              <option value="info">info</option>
            </select>
          </label>
          <label>
            Evento
            <input
              value={draftFilters.name}
              onChange={(event) => setDraftFilters((old) => ({ ...old, name: event.target.value }))}
              placeholder="api_request_failed"
            />
          </label>
          <label>
            Evento em
            <input
              type="datetime-local"
              value={draftFilters.eventFrom}
              onChange={(event) => setDraftFilters((old) => ({ ...old, eventFrom: event.target.value }))}
            />
          </label>
          <label>
            Evento ate
            <input
              type="datetime-local"
              value={draftFilters.eventTo}
              onChange={(event) => setDraftFilters((old) => ({ ...old, eventTo: event.target.value }))}
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        {eventsQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando eventos frontend" message="Consultando /v1/ops/frontend-events." />
        ) : eventsQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(eventsQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar eventos frontend"
                message={message}
                requestId={requestId}
                onRetry={() => void eventsQuery.refetch()}
              />
            );
          })()
        ) : eventsQuery.data && eventsQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem eventos frontend" message="Nenhum evento encontrado para os filtros aplicados." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Evento em</th>
                    <th>Categoria</th>
                    <th>Nome</th>
                    <th>Severidade</th>
                    <th>Atributos</th>
                  </tr>
                </thead>
                <tbody>
                  {eventsQuery.data?.items.map((item) => (
                    <tr key={item.event_id}>
                      <td>{new Date(item.event_timestamp_utc).toLocaleString("pt-BR")}</td>
                      <td>{item.category}</td>
                      <td>{item.name}</td>
                      <td>
                        <span className={`status-chip status-${severityToChip(item.severity)}`}>{item.severity}</span>
                      </td>
                      <td title={JSON.stringify(item.attributes ?? {})}>{renderAttributes(item.attributes)}</td>
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
