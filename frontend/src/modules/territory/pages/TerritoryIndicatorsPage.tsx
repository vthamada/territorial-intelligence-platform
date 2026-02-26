import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getIndicators, getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import type { TerritoryItem } from "../../../shared/api/types";
import { Panel } from "../../../shared/ui/Panel";
import { StateBlock } from "../../../shared/ui/StateBlock";

const TERRITORY_PAGE_SIZE = 20;
const INDICATOR_PAGE_SIZE = 20;

type IndicatorFilters = {
  territoryId: string;
  period: string;
  indicatorCode: string;
  source: string;
  dataset: string;
};

function makeEmptyIndicatorFilters(): IndicatorFilters {
  return {
    territoryId: "",
    period: "",
    indicatorCode: "",
    source: "",
    dataset: ""
  };
}

export function TerritoryIndicatorsPage() {
  const [territoryDraftLevel, setTerritoryDraftLevel] = useState("municipality");
  const [territoryAppliedLevel, setTerritoryAppliedLevel] = useState("municipality");
  const [territoryPage, setTerritoryPage] = useState(1);

  const [indicatorDraftFilters, setIndicatorDraftFilters] = useState<IndicatorFilters>(makeEmptyIndicatorFilters);
  const [indicatorAppliedFilters, setIndicatorAppliedFilters] = useState<IndicatorFilters>(makeEmptyIndicatorFilters);
  const [indicatorPage, setIndicatorPage] = useState(1);

  const territoryParams = useMemo(
    () => ({
      level: territoryAppliedLevel,
      page: territoryPage,
      page_size: TERRITORY_PAGE_SIZE
    }),
    [territoryAppliedLevel, territoryPage]
  );

  const territoryQuery = useQuery({
    queryKey: ["territories", territoryParams],
    queryFn: () => getTerritories(territoryParams)
  });

  const indicatorParams = useMemo(
    () => ({
      territory_id: indicatorAppliedFilters.territoryId || undefined,
      period: indicatorAppliedFilters.period || undefined,
      indicator_code: indicatorAppliedFilters.indicatorCode || undefined,
      source: indicatorAppliedFilters.source || undefined,
      dataset: indicatorAppliedFilters.dataset || undefined,
      page: indicatorPage,
      page_size: INDICATOR_PAGE_SIZE
    }),
    [indicatorAppliedFilters, indicatorPage]
  );

  const indicatorsQuery = useQuery({
    queryKey: ["indicators", indicatorParams],
    queryFn: () => getIndicators(indicatorParams)
  });

  const territoryTotalPages = territoryQuery.data ? Math.max(1, Math.ceil(territoryQuery.data.total / TERRITORY_PAGE_SIZE)) : 1;
  const indicatorTotalPages = indicatorsQuery.data ? Math.max(1, Math.ceil(indicatorsQuery.data.total / INDICATOR_PAGE_SIZE)) : 1;

  const selectedTerritoryName =
    territoryQuery.data?.items.find((item) => item.territory_id === indicatorDraftFilters.territoryId)?.name ??
    indicatorDraftFilters.territoryId;

  function applyTerritoryFilters() {
    setTerritoryPage(1);
    setTerritoryAppliedLevel(territoryDraftLevel);
  }

  function clearTerritoryFilters() {
    setTerritoryPage(1);
    setTerritoryDraftLevel("municipality");
    setTerritoryAppliedLevel("municipality");
  }

  function selectTerritory(territory: TerritoryItem) {
    setIndicatorDraftFilters((old) => ({ ...old, territoryId: territory.territory_id }));
  }

  function applyIndicatorFilters() {
    setIndicatorPage(1);
    setIndicatorAppliedFilters(indicatorDraftFilters);
  }

  function clearIndicatorFilters() {
    const cleared = makeEmptyIndicatorFilters();
    setIndicatorPage(1);
    setIndicatorDraftFilters(cleared);
    setIndicatorAppliedFilters(cleared);
  }

  return (
    <div className="page-grid">
      <Panel title="Territórios" subtitle="Consulta por nivel territorial com seleção para filtrar indicadores">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyTerritoryFilters();
          }}
        >
          <label>
            Nível
            <select value={territoryDraftLevel} onChange={(event) => setTerritoryDraftLevel(event.target.value)}>
              <option value="municipality">municipality</option>
              <option value="district">district</option>
              <option value="census_sector">census_sector</option>
              <option value="electoral_zone">electoral_zone</option>
              <option value="electoral_section">electoral_section</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearTerritoryFilters}>
              Limpar
            </button>
          </div>
        </form>

        {territoryQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando territorios" message="Consultando /v1/territories." />
        ) : territoryQuery.error ? (
          (() => {
            const { message, requestId } = formatApiError(territoryQuery.error);
            return (
              <StateBlock
                tone="error"
                title="Falha ao carregar territorios"
                message={message}
                requestId={requestId}
                onRetry={() => void territoryQuery.refetch()}
              />
            );
          })()
        ) : territoryQuery.data && territoryQuery.data.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem territorios" message="Nenhum territorio retornado para o nivel selecionado." />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Nível</th>
                    <th>UF</th>
                    <th>IBGE municipio</th>
                    <th>Acao</th>
                  </tr>
                </thead>
                <tbody>
                  {territoryQuery.data?.items.map((territory) => {
                    const isSelected = territory.territory_id === indicatorDraftFilters.territoryId;
                    return (
                      <tr key={territory.territory_id} className={isSelected ? "territory-selected-row" : undefined}>
                        <td>{territory.name}</td>
                        <td>{territory.level}</td>
                        <td>{territory.uf ?? "-"}</td>
                        <td>{territory.municipality_ibge_code ?? "-"}</td>
                        <td>
                          <button type="button" className="button-secondary" onClick={() => selectTerritory(territory)}>
                            Selecionar
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="pagination-row">
              <button
                type="button"
                className="button-secondary"
                disabled={territoryPage <= 1}
                onClick={() => setTerritoryPage((old) => old - 1)}
              >
                Anterior
              </button>
              <span>
                Pagina {territoryPage} de {territoryTotalPages}
              </span>
              <button
                type="button"
                className="button-secondary"
                disabled={territoryPage >= territoryTotalPages}
                onClick={() => setTerritoryPage((old) => old + 1)}
              >
                Proxima
              </button>
            </div>
          </>
        )}
      </Panel>

      <Panel title="Indicadores" subtitle="Filtros por periodo, codigo, fonte e dataset">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyIndicatorFilters();
          }}
        >
          <label>
            Território selecionado
            <input
              value={selectedTerritoryName || ""}
              readOnly
              placeholder="Selecione na tabela de territorios"
              aria-label="Território selecionado"
            />
          </label>
          <label>
            Período
            <input
              value={indicatorDraftFilters.period}
              onChange={(event) => setIndicatorDraftFilters((old) => ({ ...old, period: event.target.value }))}
              placeholder="2025"
            />
          </label>
          <label>
            Codigo indicador
            <input
              value={indicatorDraftFilters.indicatorCode}
              onChange={(event) => setIndicatorDraftFilters((old) => ({ ...old, indicatorCode: event.target.value }))}
              placeholder="MTE_NOVO_CAGED_SALDO_TOTAL"
            />
          </label>
          <label>
            Fonte
            <input
              value={indicatorDraftFilters.source}
              onChange={(event) => setIndicatorDraftFilters((old) => ({ ...old, source: event.target.value }))}
              placeholder="MTE"
            />
          </label>
          <label>
            Dataset
            <input
              value={indicatorDraftFilters.dataset}
              onChange={(event) => setIndicatorDraftFilters((old) => ({ ...old, dataset: event.target.value }))}
              placeholder="mte_novo_caged"
            />
          </label>
          <div className="filter-actions">
            <button type="submit">Filtrar</button>
            <button type="button" className="button-secondary" onClick={clearIndicatorFilters}>
              Limpar
            </button>
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
                    <th>Período</th>
                    <th>Codigo</th>
                    <th>Nome</th>
                    <th>Fonte</th>
                    <th>Dataset</th>
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
                      <td>{indicator.dataset}</td>
                      <td>{indicator.value ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination-row">
              <button type="button" className="button-secondary" disabled={indicatorPage <= 1} onClick={() => setIndicatorPage((old) => old - 1)}>
                Anterior
              </button>
              <span>
                Pagina {indicatorPage} de {indicatorTotalPages}
              </span>
              <button
                type="button"
                className="button-secondary"
                disabled={indicatorPage >= indicatorTotalPages}
                onClick={() => setIndicatorPage((old) => old + 1)}
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
