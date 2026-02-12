import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { getTerritoryCompare, getTerritoryPeers, getTerritoryProfile } from "../../../shared/api/qg";
import { getQgDomainLabel } from "../../qg/domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import { StateBlock } from "../../../shared/ui/StateBlock";

const DEFAULT_TERRITORY_ID = "3121605";

function formatValue(value: number, unit: string | null) {
  if (unit) {
    return `${value.toFixed(2)} ${unit}`;
  }
  return value.toFixed(2);
}

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

type TerritoryProfilePageProps = {
  initialTerritoryId?: string;
};

export function TerritoryProfilePage({ initialTerritoryId }: TerritoryProfilePageProps) {
  const fallbackTerritoryId = initialTerritoryId || DEFAULT_TERRITORY_ID;

  const [territoryId, setTerritoryId] = useState(fallbackTerritoryId);
  const [compareWithId, setCompareWithId] = useState("");
  const [period, setPeriod] = useState("");
  const [appliedTerritoryId, setAppliedTerritoryId] = useState(fallbackTerritoryId);
  const [appliedCompareWithId, setAppliedCompareWithId] = useState("");
  const [appliedPeriod, setAppliedPeriod] = useState("");

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

  const profileQuery = useQuery({
    queryKey: ["qg", "territory-profile", appliedTerritoryId, appliedPeriod],
    queryFn: () =>
      getTerritoryProfile(appliedTerritoryId, {
        period: appliedPeriod || undefined,
        limit: 80
      })
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
      })
  });

  const firstError = territoryListQuery.error ?? profileQuery.error ?? compareQuery.error ?? peersQuery.error;
  const isLoading =
    territoryListQuery.isPending ||
    profileQuery.isPending ||
    peersQuery.isPending ||
    (compareQuery.isPending && Boolean(appliedCompareWithId));

  const territoryOptions = useMemo(() => territoryListQuery.data?.items ?? [], [territoryListQuery.data]);

  function applyFilters() {
    setAppliedTerritoryId(territoryId);
    setAppliedCompareWithId(compareWithId);
    setAppliedPeriod(period);
  }

  function clearFilters() {
    setTerritoryId(fallbackTerritoryId);
    setCompareWithId("");
    setPeriod("");
    setAppliedTerritoryId(fallbackTerritoryId);
    setAppliedCompareWithId("");
    setAppliedPeriod("");
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

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar perfil territorial"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void territoryListQuery.refetch();
          void profileQuery.refetch();
          if (appliedCompareWithId) {
            void compareQuery.refetch();
          }
          void peersQuery.refetch();
        }}
      />
    );
  }

  const profile = profileQuery.data!;
  const compare = compareQuery.data;
  const peers = peersQuery.data!;

  function applyPeerComparison(peerId: string) {
    setCompareWithId(peerId);
    setAppliedCompareWithId(peerId);
  }

  return (
    <div className="page-grid">
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
        <div className="quick-actions">
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
        </div>
      </Panel>

      <Panel title="Status geral do territorio" subtitle="Leitura executiva consolidada do recorte atual">
        <div className="kpi-grid">
          <StrategicIndexCard
            label="Score territorial"
            value={profile.overall_score === null ? "-" : profile.overall_score.toFixed(2)}
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

      <Panel title={profile.territory_name} subtitle={`Nivel ${profile.territory_level} - evidencias por dominio`}>
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
      </Panel>

      <Panel title="Pares recomendados" subtitle="Territorios similares para comparacao rapida">
        {peers.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem pares sugeridos" message="Nao ha pares com indicadores compartilhados no recorte." />
        ) : (
          <div className="table-wrap">
            <table>
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
                    <td>{item.territory_level}</td>
                    <td>{item.similarity_score.toFixed(2)}</td>
                    <td>{item.shared_indicators}</td>
                    <td>{item.status}</td>
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
        <SourceFreshnessBadge metadata={peers.metadata} />
      </Panel>

      <Panel title="Dominios e indicadores" subtitle="Visao consolidada do recorte atual">
        {profile.domains.length === 0 ? (
          <StateBlock tone="empty" title="Sem indicadores" message="Nao ha indicadores no recorte selecionado." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dominio</th>
                  <th>Indicador</th>
                  <th>Codigo</th>
                  <th>Periodo</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {profile.domains.flatMap((domain) =>
                  domain.indicators.map((indicator) => (
                    <tr key={`${domain.domain}-${indicator.indicator_code}`}>
                      <td>{getQgDomainLabel(domain.domain)}</td>
                      <td>{indicator.indicator_name}</td>
                      <td>{indicator.indicator_code}</td>
                      <td>{indicator.reference_period}</td>
                      <td>{formatValue(indicator.value, indicator.unit)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {appliedCompareWithId ? (
        <Panel title="Comparacao territorial" subtitle="Deltas entre territorio base e territorio de referencia">
          {!compare || compare.items.length === 0 ? (
            <StateBlock tone="empty" title="Sem comparacao" message="Nao ha indicadores compartilhados para comparacao." />
          ) : (
            <div className="table-wrap">
              <table>
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
                      <td>{formatValue(item.base_value, item.unit)}</td>
                      <td>{formatValue(item.compare_value, item.unit)}</td>
                      <td>{item.delta.toFixed(2)}</td>
                      <td>{item.direction}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      ) : null}
    </div>
  );
}
