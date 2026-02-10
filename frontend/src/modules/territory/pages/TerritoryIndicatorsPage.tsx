import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getIndicators, getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const PAGE_SIZE = 20;

export function TerritoryIndicatorsPage() {
  const [level, setLevel] = useState("municipality");
  const [period, setPeriod] = useState("");
  const [indicatorCode, setIndicatorCode] = useState("");
  const [page, setPage] = useState(1);

  const territoryQuery = useQuery({
    queryKey: ["territories", level],
    queryFn: () => getTerritories({ level, page: 1, page_size: 50 })
  });

  const indicatorParams = useMemo(
    () => ({
      period: period || undefined,
      indicator_code: indicatorCode || undefined,
      page,
      page_size: PAGE_SIZE
    }),
    [indicatorCode, page, period]
  );

  const indicatorsQuery = useQuery({
    queryKey: ["indicators", indicatorParams],
    queryFn: () => getIndicators(indicatorParams)
  });

  const totalPages = indicatorsQuery.data ? Math.max(1, Math.ceil(indicatorsQuery.data.total / PAGE_SIZE)) : 1;

  return (
    <div className="page-grid">
      <Panel title="Territorios" subtitle="Consulta por nivel territorial">
        <div className="filter-grid compact">
          <label>
            Nivel
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">municipality</option>
              <option value="district">district</option>
              <option value="census_sector">census_sector</option>
              <option value="electoral_zone">electoral_zone</option>
              <option value="electoral_section">electoral_section</option>
            </select>
          </label>
        </div>

        {territoryQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando territorios" message="Consultando /v1/territories." />
        ) : territoryQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(territoryQuery.error);
            return <StateBlock tone="error" title="Falha ao carregar territorios" message={message} requestId={requestId} />;
          })()
        ) : territoryQuery.data && territoryQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem territorios" message="Nenhum territorio retornado para o nivel selecionado." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Nivel</th>
                  <th>UF</th>
                  <th>IBGE municipio</th>
                </tr>
              </thead>
              <tbody>
                {territoryQuery.data?.items.map((territory) => (
                  <tr key={territory.territory_id}>
                    <td>{territory.name}</td>
                    <td>{territory.level}</td>
                    <td>{territory.uf ?? "-"}</td>
                    <td>{territory.municipality_ibge_code ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Indicadores" subtitle="Filtros por periodo e codigo de indicador">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            void indicatorsQuery.refetch();
          }}
        >
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Codigo indicador
            <input value={indicatorCode} onChange={(event) => setIndicatorCode(event.target.value)} placeholder="MTE_NOVO_CAGED_SALDO_TOTAL" />
          </label>
          <div className="filter-actions">
            <button type="submit">Filtrar</button>
          </div>
        </form>

        {indicatorsQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando indicadores" message="Consultando /v1/indicators." />
        ) : indicatorsQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(indicatorsQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar indicadores"
                message={message}
                requestId={requestId}
                onRetry={() => void indicatorsQuery.refetch()}
              />
            );
          })()
        ) : indicatorsQuery.data && indicatorsQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem indicadores" message="Nenhum indicador encontrado para os filtros aplicados." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Periodo</th>
                    <th>Codigo</th>
                    <th>Nome</th>
                    <th>Fonte</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {indicatorsQuery.data?.items.map((indicator) => (
                    <tr key={indicator.fact_id}>
                      <td>{indicator.reference_period}</td>
                      <td>{indicator.indicator_code}</td>
                      <td>{indicator.indicator_name}</td>
                      <td>{indicator.source}</td>
                      <td>{indicator.value ?? "-"}</td>
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
