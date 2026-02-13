import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getChoropleth, getMapLayers } from "../../../shared/api/domain";
import { getInsightsHighlights, getKpisOverview, getPriorityList, getPrioritySummary } from "../../../shared/api/qg";
import { getQgDomainLabel, QG_ONDA_BC_SPOTLIGHT } from "../domainCatalog";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { ChoroplethMiniMap } from "../../../shared/ui/ChoroplethMiniMap";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { formatLevelLabel, formatStatusLabel, formatValueWithUnit } from "../../../shared/ui/presentation";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { useFilterStore } from "../../../shared/stores/filterStore";

export function QgOverviewPage() {
  const globalFilters = useFilterStore();
  const [period, setPeriod] = useState(globalFilters.period);
  const [level, setLevel] = useState(globalFilters.level);
  const [appliedPeriod, setAppliedPeriod] = useState(globalFilters.period);
  const [appliedLevel, setAppliedLevel] = useState(globalFilters.level);
  const [detailedLayerId, setDetailedLayerId] = useState("");
  const [appliedDetailedLayerId, setAppliedDetailedLayerId] = useState("");
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string | undefined>(undefined);

  const baseQuery = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel,
    }),
    [appliedLevel, appliedPeriod],
  );

  const kpiQuery = useQuery({
    queryKey: ["qg", "kpis", baseQuery],
    queryFn: () => getKpisOverview({ ...baseQuery, limit: 20 }),
  });
  const summaryQuery = useQuery({
    queryKey: ["qg", "priority-summary", baseQuery],
    queryFn: () => getPrioritySummary({ ...baseQuery, limit: 100 }),
  });
  const prioritiesPreviewQuery = useQuery({
    queryKey: ["qg", "priority-preview", baseQuery],
    queryFn: () => getPriorityList({ ...baseQuery, limit: 5 }),
  });
  const highlightsQuery = useQuery({
    queryKey: ["qg", "insights", baseQuery],
    queryFn: () => getInsightsHighlights({ ...baseQuery, limit: 5 }),
  });
  const choroplethQuery = useQuery({
    queryKey: [
      "qg",
      "map",
      {
        metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
        period: appliedPeriod || "2025",
        level: appliedLevel === "district" ? "distrito" : "municipio",
        page: 1,
        page_size: 500,
      },
    ],
    queryFn: () =>
      getChoropleth({
        metric: "MTE_NOVO_CAGED_SALDO_TOTAL",
        period: appliedPeriod || "2025",
        level: appliedLevel === "district" ? "distrito" : "municipio",
        page: 1,
        page_size: 500,
      }),
  });
  const mapLayersQuery = useQuery({
    queryKey: ["qg", "map", "layers"],
    queryFn: () => getMapLayers(),
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = kpiQuery.isPending || summaryQuery.isPending || prioritiesPreviewQuery.isPending || highlightsQuery.isPending;
  const firstError = kpiQuery.error ?? summaryQuery.error ?? prioritiesPreviewQuery.error ?? highlightsQuery.error;

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setAppliedDetailedLayerId(detailedLayerId);
    globalFilters.setPeriod(period);
    globalFilters.setLevel(level);
  }

  function clearFilters() {
    setPeriod("2025");
    setLevel("municipality");
    setAppliedPeriod("2025");
    setAppliedLevel("municipality");
    setDetailedLayerId("");
    setAppliedDetailedLayerId("");
    globalFilters.applyDefaults();
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando QG estrategico"
        message="Consultando KPIs, prioridades e destaques executivos."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar QG estrategico"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void kpiQuery.refetch();
          void summaryQuery.refetch();
          void prioritiesPreviewQuery.refetch();
          void highlightsQuery.refetch();
        }}
      />
    );
  }

  const kpis = kpiQuery.data!;
  const summary = summaryQuery.data!;
  const prioritiesPreview = prioritiesPreviewQuery.data!;
  const highlights = highlightsQuery.data!;

  const topPriority = prioritiesPreview.items[0];
  const mostCriticalTerritory = topPriority?.territory_id;
  const sectionDetailLayerOptions = (mapLayersQuery.data?.items ?? []).filter(
    (item) => item.territory_level === "electoral_section",
  );
  function appendDetailedLayer(path: string) {
    if (!appliedDetailedLayerId) {
      return path;
    }
    const delimiter = path.includes("?") ? "&" : "?";
    return `${path}${delimiter}layer_id=${encodeURIComponent(appliedDetailedLayerId)}`;
  }
  const mapQuickLink = topPriority
    ? appendDetailedLayer(
        `/mapa?metric=${encodeURIComponent(topPriority.indicator_code)}&period=${encodeURIComponent(
          topPriority.evidence.reference_period,
        )}&territory_id=${encodeURIComponent(topPriority.territory_id)}`,
      )
    : appendDetailedLayer("/mapa");
  const resolvedPeriod = appliedPeriod || kpis.period || "2025";
  const resolvedMapLevel = appliedLevel === "district" ? "distrito" : "municipio";

  const choroplethItems = (choroplethQuery.data?.items ?? []).map((item: Record<string, unknown>) => ({
    territoryId: String(item.territory_id ?? ""),
    territoryName: String(item.territory_name ?? ""),
    value: typeof item.value === "number" ? item.value : null,
    geometry: (item.geometry as Record<string, unknown>) ?? null,
  }));

  return (
    <main className="page-grid">
      <Panel title="Situacao geral" subtitle="Prioridades, filtros e navegação executiva">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nivel territorial
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
              <option value="district">{formatLevelLabel("district")}</option>
              <option value="census_sector">{formatLevelLabel("census_sector")}</option>
              <option value="electoral_zone">{formatLevelLabel("electoral_zone")}</option>
              <option value="electoral_section">{formatLevelLabel("electoral_section")}</option>
            </select>
          </label>
          {sectionDetailLayerOptions.length > 0 ? (
            <label>
              Camada detalhada (Mapa)
              <select value={detailedLayerId} onChange={(event) => setDetailedLayerId(event.target.value)}>
                <option value="">Automatica (recomendada)</option>
                {sectionDetailLayerOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <div className="filter-actions">
            <button type="submit">Aplicar</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        <div className="kpi-grid">
          <StrategicIndexCard label="Criticos" value={String(summary.by_status.critical ?? 0)} status="critical" helper="resposta imediata" />
          <StrategicIndexCard label="Atencao" value={String(summary.by_status.attention ?? 0)} status="attention" helper="risco moderado" />
          <StrategicIndexCard label="Estavel" value={String(summary.by_status.stable ?? 0)} status="stable" helper="sob controle" />
          <StrategicIndexCard label="Dominios" value={String(Object.keys(summary.by_domain).length)} status="info" helper="fontes ativas" />
        </div>

        <nav aria-label="Atalhos de decisao" className="quick-actions" style={{ marginTop: "0.8rem" }}>
          <Link className="quick-action-link" to="/prioridades">Prioridades</Link>
          <Link className="quick-action-link" to={mapQuickLink}>Mapa detalhado</Link>
          {mostCriticalTerritory ? <Link className="quick-action-link" to={`/territorio/${mostCriticalTerritory}`}>Territorio critico</Link> : null}
        </nav>

        <SourceFreshnessBadge metadata={kpis.metadata} />
      </Panel>

      <Panel title="Mapa rapido" subtitle="Visual territorial do recorte aplicado">
        {choroplethItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados no mapa" message="Nao ha geometrias para o recorte atual." />
        ) : (
          <>
            <ChoroplethMiniMap
              items={choroplethItems}
              selectedTerritoryId={selectedTerritoryId}
              onSelect={(id) => setSelectedTerritoryId(id)}
            />
            <div className="map-floating-stats" style={{ position: "static", marginTop: "0.5rem" }}>
              <span className="map-floating-stat"><strong>{summary.by_status.critical ?? 0}</strong> criticos</span>
              <span className="map-floating-stat"><strong>{summary.by_status.attention ?? 0}</strong> atencao</span>
              <span className="map-floating-stat"><strong>{summary.total_items}</strong> monitorados</span>
            </div>
          </>
        )}
      </Panel>

      <CollapsiblePanel title="Top prioridades" defaultOpen={true} badgeCount={prioritiesPreview.items.length}>
        {prioritiesPreview.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada." />
        ) : (
          <div className="priority-card-grid">
            {prioritiesPreview.items.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel title="Destaques" defaultOpen={false} badgeCount={highlights.items.length}>
        {highlights.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem destaques" message="Sem insights para o recorte." />
        ) : (
          <ul className="trend-list" aria-label="Lista de destaques">
            {highlights.items.map((item) => (
              <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                </div>
                <small>severidade: {formatStatusLabel(item.severity)} | robustez: {item.robustness}</small>
              </li>
            ))}
          </ul>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel title="Dominios Onda B/C" subtitle="Atalhos para fontes novas com recorte aplicado" defaultOpen={false} badgeCount={QG_ONDA_BC_SPOTLIGHT.length}>
        <div className="table-wrap">
          <table aria-label="Dominios Onda B/C">
            <thead>
              <tr>
                <th>Dominio</th>
                <th>Fonte</th>
                <th>Itens no recorte</th>
                <th>Metrica de mapa</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {QG_ONDA_BC_SPOTLIGHT.map((item) => {
                const totalInDomain = summary.by_domain[item.domain] ?? 0;
                const prioritiesLink = `/prioridades?domain=${encodeURIComponent(item.domain)}&period=${encodeURIComponent(resolvedPeriod)}&level=${encodeURIComponent(appliedLevel)}`;
                const mapLink = appendDetailedLayer(
                  `/mapa?metric=${encodeURIComponent(item.defaultMetric)}&period=${encodeURIComponent(
                    resolvedPeriod,
                  )}&level=${encodeURIComponent(resolvedMapLevel)}`,
                );
                return (
                  <tr key={item.domain}>
                    <td>{item.label}</td>
                    <td>{item.source}</td>
                    <td>{totalInDomain}</td>
                    <td>{item.defaultMetric}</td>
                    <td>
                      <Link className="inline-link" to={prioritiesLink}>Abrir prioridades</Link>{" "}|{" "}
                      <Link className="inline-link" to={mapLink}>Ver no mapa</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel title="KPIs executivos" subtitle="Indicadores agregados para leitura rapida" defaultOpen={false} badgeCount={kpis.items.length}>
        {kpis.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem KPIs" message="Nenhum KPI encontrado para os filtros aplicados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dominio</th>
                  <th>Fonte</th>
                  <th>Codigo</th>
                  <th>Indicador</th>
                  <th>Valor</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {kpis.items.map((item) => (
                  <tr key={`${item.domain}-${item.indicator_code}`}>
                    <td>{getQgDomainLabel(item.domain)}</td>
                    <td>{item.source ?? "-"}</td>
                    <td>{item.indicator_code}</td>
                    <td>{item.indicator_name}</td>
                    <td>{formatValueWithUnit(item.value, item.unit)}</td>
                    <td>{formatLevelLabel(item.territory_level)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>
    </main>
  );
}

