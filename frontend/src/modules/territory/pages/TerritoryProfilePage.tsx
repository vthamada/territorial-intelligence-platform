import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { ApiClientError, formatApiError } from "../../../shared/api/http";
import { getTerritoryCompare, getTerritoryPeers, getTerritoryProfile } from "../../../shared/api/qg";
import { getQgDomainLabel } from "../../qg/domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatLevelLabel, formatStatusLabel, formatValueWithUnit, toNumber } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import { StateBlock } from "../../../shared/ui/StateBlock";

function toStrategicStatus(status: string): "critical" | "attention" | "stable" | "info" {
  if (status === "critical") {
    return "critical";
  }
  if (status === "attention") {
    return "attention";
  }
  if (status === "stable") {
    return "stable";
  }
  return "info";
}

function toStrategicTrend(trend: string): "up" | "down" | "flat" {
  if (trend === "up" || trend === "down" || trend === "flat") {
    return trend;
  }
  return "flat";
}

function formatUnknownDecimal(value: unknown, fractionDigits = 2): string {
  const numeric = toNumber(value);
  return numeric === null ? "-" : formatDecimal(numeric, fractionDigits);
}

type TerritoryProfilePageProps = {
  initialTerritoryId?: string;
};

export function TerritoryProfilePage({ initialTerritoryId }: TerritoryProfilePageProps) {
  const [territoryId, setTerritoryId] = useState(initialTerritoryId ?? "");
  const [compareWithId, setCompareWithId] = useState("");
  const [period, setPeriod] = useState("");
  const [appliedTerritoryId, setAppliedTerritoryId] = useState(initialTerritoryId ?? "");
  const [appliedCompareWithId, setAppliedCompareWithId] = useState("");
  const [appliedPeriod, setAppliedPeriod] = useState("");
  const [indicatorsPageSize, setIndicatorsPageSize] = useState("20");
  const [indicatorsPage, setIndicatorsPage] = useState(1);

  useEffect(() => {
    if (!initialTerritoryId) {
      return;
    }
    setTerritoryId(initialTerritoryId);
    setAppliedTerritoryId(initialTerritoryId);
    setCompareWithId("");
    setAppliedCompareWithId("");
  }, [initialTerritoryId]);

  const territoryListQuery = useQuery({
    queryKey: ["territories", "profile-picker"],
    queryFn: () => getTerritories({ level: "municipality", page: 1, page_size: 200 })
  });

  const territoryOptions = useMemo(() => territoryListQuery.data?.items ?? [], [territoryListQuery.data]);
  const defaultTerritoryId = territoryOptions[0]?.territory_id ?? "";

  useEffect(() => {
    if (initialTerritoryId || territoryOptions.length === 0) {
      return;
    }
    setTerritoryId((current) => current || defaultTerritoryId);
    setAppliedTerritoryId((current) => current || defaultTerritoryId);
  }, [defaultTerritoryId, initialTerritoryId, territoryOptions.length]);

  useEffect(() => {
    if (territoryOptions.length === 0) {
      return;
    }
    const availableIds = new Set(territoryOptions.map((item) => item.territory_id));
    if (!territoryId || !availableIds.has(territoryId)) {
      setTerritoryId(defaultTerritoryId);
    }
    if (!appliedTerritoryId || !availableIds.has(appliedTerritoryId)) {
      setAppliedTerritoryId(defaultTerritoryId);
      setCompareWithId("");
      setAppliedCompareWithId("");
    }
  }, [appliedTerritoryId, defaultTerritoryId, territoryId, territoryOptions]);

  const profileQuery = useQuery({
    queryKey: ["qg", "territory-profile", appliedTerritoryId, appliedPeriod],
    queryFn: () =>
      getTerritoryProfile(appliedTerritoryId, {
        period: appliedPeriod || undefined,
        limit: 80
      }),
    enabled: Boolean(appliedTerritoryId),
  });

  const compareQuery = useQuery({
    queryKey: ["qg", "territory-compare", appliedTerritoryId, appliedCompareWithId, appliedPeriod],
    queryFn: () =>
      getTerritoryCompare(appliedTerritoryId, {
        with_id: appliedCompareWithId,
        period: appliedPeriod || undefined,
        limit: 80
      }),
    enabled: Boolean(appliedCompareWithId)
  });
  const peersQuery = useQuery({
    queryKey: ["qg", "territory-peers", appliedTerritoryId, appliedPeriod],
    queryFn: () =>
      getTerritoryPeers(appliedTerritoryId, {
        period: appliedPeriod || undefined,
        limit: 5
      }),
    enabled: Boolean(appliedTerritoryId),
  });
  const profileData = profileQuery.data;
  const flattenedIndicators = useMemo(
    () =>
      (profileData?.domains ?? []).flatMap((domain) =>
        domain.indicators.map((indicator) => ({
          domain: domain.domain,
          indicator,
        })),
      ),
    [profileData?.domains],
  );
  const normalizedIndicatorsPageSize = Math.max(1, Number(indicatorsPageSize) || 20);
  const indicatorsTotalPages = Math.max(1, Math.ceil(flattenedIndicators.length / normalizedIndicatorsPageSize));
  const visibleIndicators = useMemo(() => {
    const start = (indicatorsPage - 1) * normalizedIndicatorsPageSize;
    return flattenedIndicators.slice(start, start + normalizedIndicatorsPageSize);
  }, [flattenedIndicators, indicatorsPage, normalizedIndicatorsPageSize]);

  useEffect(() => {
    if (indicatorsPage > indicatorsTotalPages) {
      setIndicatorsPage(indicatorsTotalPages);
    }
  }, [indicatorsPage, indicatorsTotalPages]);

  useEffect(() => {
    setIndicatorsPage(1);
  }, [indicatorsPageSize]);

  const territoryPickerError = appliedTerritoryId ? null : territoryListQuery.error;
  const firstError = profileQuery.error ?? territoryPickerError;
  const isLoading = (appliedTerritoryId ? false : territoryListQuery.isPending) || (Boolean(appliedTerritoryId) && profileQuery.isPending);
  const hasSelectedTerritory = territoryOptions.some((item) => item.territory_id === appliedTerritoryId);
  const shouldRenderNoDataState =
    firstError instanceof ApiClientError &&
    firstError.status === 404 &&
    Boolean(appliedTerritoryId) &&
    hasSelectedTerritory;

  function applyFilters() {
    if (!territoryId) {
      return;
    }
    setAppliedTerritoryId(territoryId);
    setAppliedCompareWithId(compareWithId);
    setAppliedPeriod(period);
    setIndicatorsPage(1);
  }

  function clearFilters() {
    setTerritoryId(defaultTerritoryId);
    setCompareWithId("");
    setPeriod("");
    setAppliedTerritoryId(defaultTerritoryId);
    setAppliedCompareWithId("");
    setAppliedPeriod("");
    setIndicatorsPageSize("20");
    setIndicatorsPage(1);
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando perfil territorial"
        message="Consultando perfil 360 e comparacao territorial."
      />
    );
  }

  if (shouldRenderNoDataState) {
    return (
      <main className="page-grid">
        <Panel title="Perfil 360 do territorio" subtitle="Diagnostico por dominio e comparacao orientada">
          <form
            className="filter-grid compact"
            onSubmit={(event) => {
              event.preventDefault();
              applyFilters();
            }}
          >
            <label>
              Territorio base
              <select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}>
                {territoryOptions.map((territory) => (
                  <option key={territory.territory_id} value={territory.territory_id}>
                    {territory.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Comparar com
              <select value={compareWithId} onChange={(event) => setCompareWithId(event.target.value)}>
                <option value="">Sem comparacao</option>
                {territoryOptions
                  .filter((territory) => territory.territory_id !== territoryId)
                  .map((territory) => (
                    <option key={territory.territory_id} value={territory.territory_id}>
                      {territory.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Periodo
              <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
            </label>
            <div className="filter-actions">
              <button type="submit">Aplicar filtros</button>
              <button type="button" className="button-secondary" onClick={clearFilters}>
                Limpar
              </button>
            </div>
          </form>
          <StateBlock
            tone="empty"
            title="Sem dados para o territorio selecionado"
            message="Nao ha indicadores disponiveis para esse recorte. Selecione outro territorio ou periodo."
          />
        </Panel>
      </main>
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar perfil territorial"
        message={message}
        requestId={requestId}
        onRetry={() => {
          if (!appliedTerritoryId) {
            void territoryListQuery.refetch();
          }
          if (appliedTerritoryId) {
            void profileQuery.refetch();
          }
          if (appliedCompareWithId) {
            void compareQuery.refetch();
          }
          if (appliedTerritoryId) {
            void peersQuery.refetch();
          }
        }}
      />
    );
  }

  if (!appliedTerritoryId && !territoryListQuery.isPending && territoryOptions.length === 0) {
    return (
      <main className="page-grid">
        <Panel title="Perfil 360 do territorio" subtitle="Diagnostico por dominio e comparacao orientada">
          <StateBlock
            tone="empty"
            title="Sem territorios disponiveis"
            message="Nao ha territorios cadastrados para montar o perfil 360."
          />
        </Panel>
      </main>
    );
  }

  if (!appliedTerritoryId || !profileQuery.data) {
    return (
      <StateBlock
        tone="loading"
        title="Preparando perfil territorial"
        message="Selecionando territorio base para carregar o perfil 360."
      />
    );
  }

  const profile = profileData!;
  const compare = compareQuery.data;
  const peers = peersQuery.data;
  const overallScore = toNumber(profile.overall_score);

  function applyPeerComparison(peerId: string) {
    setCompareWithId(peerId);
    setAppliedCompareWithId(peerId);
  }

  return (
    <main className="page-grid">
      <Panel title="Perfil 360 do territorio" subtitle="Diagnostico por dominio e comparacao orientada">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Territorio base
            <select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}>
              {territoryOptions.map((territory) => (
                <option key={territory.territory_id} value={territory.territory_id}>
                  {territory.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Comparar com
            <select value={compareWithId} onChange={(event) => setCompareWithId(event.target.value)}>
              <option value="">Sem comparacao</option>
              {territoryOptions
                .filter((territory) => territory.territory_id !== territoryId)
                .map((territory) => (
                  <option key={territory.territory_id} value={territory.territory_id}>
                    {territory.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={profile.metadata} />
        <nav aria-label="Atalhos do territorio" className="quick-actions">
          <Link
            className="quick-action-link"
            to={`/briefs?territory_id=${encodeURIComponent(appliedTerritoryId)}&period=${encodeURIComponent(
              appliedPeriod || profile.period || ""
            )}`}
          >
            Gerar brief deste territorio
          </Link>
          <Link
            className="quick-action-link"
            to={`/cenarios?territory_id=${encodeURIComponent(appliedTerritoryId)}&period=${encodeURIComponent(
              appliedPeriod || profile.period || ""
            )}`}
          >
            Simular cenarios
          </Link>
        </nav>
      </Panel>

      <Panel title="Status geral do territorio" subtitle="Leitura executiva consolidada do recorte atual">
        <div className="kpi-grid">
          <StrategicIndexCard
            label="Score territorial"
            value={overallScore === null ? "-" : formatDecimal(overallScore)}
            status={toStrategicStatus(profile.overall_status)}
            trend={toStrategicTrend(profile.overall_trend)}
            helper="score agregado dos dominios com dados disponiveis"
          />
          <StrategicIndexCard
            label="Dominios monitorados"
            value={String(profile.domains.length)}
            status="info"
            helper="dominios com indicadores no recorte atual"
          />
          <StrategicIndexCard
            label="Indicadores totais"
            value={String(profile.domains.reduce((acc, domain) => acc + domain.indicators_count, 0))}
            status="info"
            helper="volume de evidencias consideradas no perfil"
          />
        </div>
      </Panel>

      <Panel title={profile.territory_name} subtitle={`Nivel ${formatLevelLabel(profile.territory_level)} - evidencias por dominio`}>
        {profile.highlights.length === 0 ? (
          <StateBlock
            tone="empty"
            title="Sem destaques no recorte"
            message="Nao ha destaques narrativos para o territorio e periodo selecionados."
          />
        ) : (
          <ul className="trend-list">
            {profile.highlights.map((item) => (
              <li key={item}>
                <div>
                  <strong>Destaque</strong>
                  <p>{item}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Pares recomendados" subtitle="Territorios similares para comparacao rapida">
        {peersQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando pares" message="Calculando territorios similares para comparacao." />
        ) : peersQuery.error ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar pares recomendados"
            message={formatApiError(peersQuery.error).message}
            requestId={formatApiError(peersQuery.error).requestId}
            onRetry={() => void peersQuery.refetch()}
          />
        ) : !peers || peers.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem pares sugeridos" message="Nao ha pares com indicadores compartilhados no recorte." />
        ) : (
          <div className="table-wrap">
            <table aria-label="Pares recomendados">
              <thead>
                <tr>
                  <th>Territorio</th>
                  <th>Nivel</th>
                  <th>Similaridade</th>
                  <th>Indicadores em comum</th>
                  <th>Status</th>
                  <th>Acao</th>
                </tr>
              </thead>
              <tbody>
                {peers.items.map((item) => (
                  <tr key={item.territory_id}>
                    <td>{item.territory_name}</td>
                    <td>{formatLevelLabel(item.territory_level)}</td>
                    <td>{formatUnknownDecimal(item.similarity_score)}</td>
                    <td>{item.shared_indicators}</td>
                    <td>{formatStatusLabel(item.status)}</td>
                    <td>
                      <button type="button" className="button-secondary" onClick={() => applyPeerComparison(item.territory_id)}>
                        Comparar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {peers ? <SourceFreshnessBadge metadata={peers.metadata} /> : null}
      </Panel>

      <Panel title="Dominios e indicadores" subtitle="Visao consolidada do recorte atual">
        {profile.domains.length === 0 ? (
          <StateBlock tone="empty" title="Sem indicadores" message="Nao ha indicadores no recorte selecionado." />
        ) : (
          <>
            <div className="panel-actions-row">
              <label>
                Itens por pagina
                <select
                  aria-label="Itens por pagina"
                  value={indicatorsPageSize}
                  onChange={(event) => setIndicatorsPageSize(event.target.value)}
                >
                  <option value="10">10</option>
                  <option value="20">20</option>
                  <option value="40">40</option>
                  <option value="80">80</option>
                </select>
              </label>
            </div>
            <div className="table-wrap">
              <table aria-label="Dominios e indicadores">
                <thead>
                  <tr>
                    <th>Dominio</th>
                    <th>Indicador</th>
                    <th>Periodo</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleIndicators.map(({ domain, indicator }) => (
                    <tr key={`${domain}-${indicator.indicator_code}`}>
                      <td>{getQgDomainLabel(domain)}</td>
                      <td>{indicator.indicator_name}</td>
                      <td>{indicator.reference_period}</td>
                      <td>{formatValueWithUnit(indicator.value, indicator.unit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {flattenedIndicators.length > normalizedIndicatorsPageSize ? (
              <div className="pagination-row" aria-label="Paginacao de indicadores">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setIndicatorsPage((page) => Math.max(1, page - 1))}
                  disabled={indicatorsPage <= 1}
                >
                  Anterior
                </button>
                <span>
                  Pagina {indicatorsPage} de {indicatorsTotalPages}
                </span>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setIndicatorsPage((page) => Math.min(indicatorsTotalPages, page + 1))}
                  disabled={indicatorsPage >= indicatorsTotalPages}
                >
                  Proxima
                </button>
              </div>
            ) : null}
          </>
        )}
      </Panel>

      {appliedCompareWithId ? (
        <Panel title="Comparacao territorial" subtitle="Deltas entre territorio base e territorio de referencia">
          {compareQuery.isPending ? (
            <StateBlock tone="loading" title="Carregando comparacao" message="Buscando indicadores compartilhados." />
          ) : compareQuery.error ? (
            <StateBlock
              tone="error"
              title="Falha ao carregar comparacao"
              message={formatApiError(compareQuery.error).message}
              requestId={formatApiError(compareQuery.error).requestId}
              onRetry={() => void compareQuery.refetch()}
            />
          ) : !compare || compare.items.length === 0 ? (
            <StateBlock tone="empty" title="Sem comparacao" message="Nao ha indicadores compartilhados para comparacao." />
          ) : (
            <div className="table-wrap">
              <table aria-label="Comparacao territorial">
                <thead>
                  <tr>
                    <th>Dominio</th>
                    <th>Indicador</th>
                    <th>Base</th>
                    <th>Comparado</th>
                    <th>Delta</th>
                    <th>Direcao</th>
                  </tr>
                </thead>
                <tbody>
                {compare.items.map((item) => (
                  <tr key={`${item.indicator_code}-${item.direction}`}>
                    <td>{getQgDomainLabel(item.domain)}</td>
                    <td>{item.indicator_name}</td>
                    <td>{formatValueWithUnit(item.base_value, item.unit)}</td>
                    <td>{formatValueWithUnit(item.compare_value, item.unit)}</td>
                    <td>{formatUnknownDecimal(item.delta)}</td>
                    <td>{formatStatusLabel(item.direction)}</td>
                  </tr>
                ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      ) : null}
    </main>
  );
}
