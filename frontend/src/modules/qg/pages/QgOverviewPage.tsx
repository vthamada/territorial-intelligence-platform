import { Suspense, lazy, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getChoropleth, getMapLayers, getMapStyleMetadata } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import type { MapLayerItem } from "../../../shared/api/types";
import { getInsightsHighlights, getKpisOverview, getPriorityList, getPrioritySummary } from "../../../shared/api/qg";
import { useFilterStore } from "../../../shared/stores/filterStore";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { ChoroplethMiniMap } from "../../../shared/ui/ChoroplethMiniMap";
import { MapDominantLayout } from "../../../shared/ui/MapDominantLayout";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { formatLevelLabel, formatStatusLabel, formatValueWithUnit } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import type { BasemapMode } from "../../../shared/ui/VectorMap";
import { getQgDomainLabel, QG_ONDA_BC_SPOTLIGHT } from "../domainCatalog";

const TILE_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/v1";
const BASEMAP_STREETS_URL =
  (import.meta.env.VITE_MAP_BASEMAP_STREETS_URL as string | undefined) ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const BASEMAP_LIGHT_URL =
  (import.meta.env.VITE_MAP_BASEMAP_LIGHT_URL as string | undefined) ??
  "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png";

const BASEMAP_MODES: Array<{ value: BasemapMode; label: string }> = [
  { value: "streets", label: "Ruas" },
  { value: "light", label: "Claro" },
  { value: "none", label: "Sem base" },
];

const OVERVIEW_MAP_METRIC = "MTE_NOVO_CAGED_SALDO_TOTAL";

const LazyVectorMap = lazy(async () => {
  const module = await import("../../../shared/ui/VectorMap");
  return { default: module.VectorMap };
});

function resolveChoroplethLevel(level: string) {
  return level === "district" ? "distrito" : "municipio";
}

function recommendedOverviewZoom(level: string) {
  if (level === "district") {
    return 10;
  }
  if (level === "census_sector") {
    return 13;
  }
  if (level === "electoral_zone") {
    return 11;
  }
  if (level === "electoral_section") {
    return 14;
  }
  return 8;
}

function resolveLayerClassification(layer?: Pick<MapLayerItem, "official_status" | "is_official"> | null) {
  if (!layer) {
    return null;
  }
  const normalized = (layer.official_status ?? "").trim().toLowerCase();
  if (normalized === "official" || normalized === "proxy" || normalized === "hybrid") {
    return normalized;
  }
  return layer.is_official ? "official" : "proxy";
}

function formatLayerClassificationLabel(layer?: Pick<MapLayerItem, "official_status" | "is_official"> | null) {
  const classification = resolveLayerClassification(layer);
  if (classification === "official") {
    return "oficial";
  }
  if (classification === "proxy") {
    return "proxy";
  }
  if (classification === "hybrid") {
    return "hibrida";
  }
  return "n/d";
}

function buildLayerClassificationHint(layer?: MapLayerItem | null) {
  const classification = resolveLayerClassification(layer);
  if (classification === "proxy") {
    return (
      layer?.proxy_method ??
      layer?.notes ??
      "Camada proxy derivada de agregacao espacial; validar limites antes de decisoes criticas."
    );
  }
  if (classification === "hybrid") {
    return layer?.notes ?? "Camada hibrida com composicao de fontes oficiais e auxiliares.";
  }
  if (classification === "official") {
    return layer?.notes ?? "Camada oficial baseada em recorte territorial institucional.";
  }
  return layer?.notes ?? "Camada sem metadata adicional.";
}

function formatVectorMapError(rawMessage: string) {
  const token = rawMessage.trim();
  if (!token) {
    return "Falha temporaria no modo vetorial. Use o fallback SVG se o problema persistir.";
  }
  const normalized = token.toLowerCase();
  if (normalized.includes("service unavailable") || normalized.includes("503")) {
    return "Camada vetorial temporariamente indisponivel (503). Tente novamente em instantes.";
  }
  return `Falha temporaria no modo vetorial: ${token}`;
}

export function QgOverviewPage() {
  const globalFilters = useFilterStore();
  const [period, setPeriod] = useState(globalFilters.period);
  const [level, setLevel] = useState(globalFilters.level);
  const [appliedPeriod, setAppliedPeriod] = useState(globalFilters.period);
  const [appliedLevel, setAppliedLevel] = useState(globalFilters.level);
  const [detailedLayerId, setDetailedLayerId] = useState("");
  const [appliedDetailedLayerId, setAppliedDetailedLayerId] = useState("");
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string | undefined>(undefined);
  const [selectedFeatureName, setSelectedFeatureName] = useState<string | null>(null);
  const [mapSidebarOpen, setMapSidebarOpen] = useState(true);
  const [basemapMode, setBasemapMode] = useState<BasemapMode>("streets");
  const [useVectorMap, setUseVectorMap] = useState(true);
  const [vectorMapError, setVectorMapError] = useState<string | null>(null);
  const [mapZoom, setMapZoom] = useState(Math.max(globalFilters.zoom, recommendedOverviewZoom(globalFilters.level)));
  const [focusSignal, setFocusSignal] = useState(0);
  const [resetViewSignal, setResetViewSignal] = useState(0);

  const baseQuery = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel,
    }),
    [appliedLevel, appliedPeriod],
  );

  const choroplethLevel = resolveChoroplethLevel(appliedLevel);

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
        metric: OVERVIEW_MAP_METRIC,
        period: appliedPeriod || "2025",
        level: choroplethLevel,
        page: 1,
        page_size: 500,
      },
    ],
    queryFn: () =>
      getChoropleth({
        metric: OVERVIEW_MAP_METRIC,
        period: appliedPeriod || "2025",
        level: choroplethLevel,
        page: 1,
        page_size: 500,
      }),
  });
  const mapLayersQuery = useQuery({
    queryKey: ["qg", "map", "layers"],
    queryFn: () => getMapLayers(),
    staleTime: 5 * 60 * 1000,
  });
  const mapStyleQuery = useQuery({
    queryKey: ["qg", "map", "style-metadata", "overview"],
    queryFn: () => getMapStyleMetadata(),
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = kpiQuery.isPending || summaryQuery.isPending;
  const firstError = kpiQuery.error ?? summaryQuery.error;

  function applyFilters() {
    const nextZoom = Math.max(mapZoom, recommendedOverviewZoom(level));
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setAppliedDetailedLayerId(level === "electoral_section" ? detailedLayerId : "");
    setSelectedTerritoryId(undefined);
    setSelectedFeatureName(null);
    setVectorMapError(null);
    setMapZoom(nextZoom);
    globalFilters.setPeriod(period);
    globalFilters.setLevel(level);
    globalFilters.setZoom(nextZoom);
  }

  function clearFilters() {
    setPeriod("2025");
    setLevel("municipality");
    setAppliedPeriod("2025");
    setAppliedLevel("municipality");
    setDetailedLayerId("");
    setAppliedDetailedLayerId("");
    setSelectedTerritoryId(undefined);
    setSelectedFeatureName(null);
    setVectorMapError(null);
    setBasemapMode("streets");
    setUseVectorMap(true);
    setMapZoom(8);
    globalFilters.applyDefaults();
    globalFilters.setZoom(8);
    setResetViewSignal((value) => value + 1);
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando painel"
        message="Consultando KPIs, prioridades e destaques executivos."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar painel"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void kpiQuery.refetch();
          void summaryQuery.refetch();
        }}
      />
    );
  }

  const kpis = kpiQuery.data!;
  const summary = summaryQuery.data!;
  const prioritiesPreview = prioritiesPreviewQuery.data;
  const highlights = highlightsQuery.data;
  const prioritiesPreviewItems = prioritiesPreview?.items ?? [];
  const highlightsItems = highlights?.items ?? [];
  const prioritiesPreviewError = prioritiesPreviewQuery.error ? formatApiError(prioritiesPreviewQuery.error) : null;
  const highlightsError = highlightsQuery.error ? formatApiError(highlightsQuery.error) : null;

  const topPriority = prioritiesPreviewItems[0];
  const mostCriticalTerritory = topPriority?.territory_id;
  const sectionDetailLayerOptions = (mapLayersQuery.data?.items ?? []).filter(
    (item) => item.territory_level === "electoral_section",
  );
  const canSelectDetailedLayer = level === "electoral_section" && sectionDetailLayerOptions.length > 0;
  const shouldAppendDetailedLayer =
    appliedLevel === "electoral_section" &&
    sectionDetailLayerOptions.some((item) => item.id === appliedDetailedLayerId);

  function appendDetailedLayer(path: string) {
    if (!shouldAppendDetailedLayer) {
      return path;
    }
    const [basePath, rawQuery = ""] = path.split("?");
    const params = new URLSearchParams(rawQuery);
    params.set("layer_id", appliedDetailedLayerId);
    params.set("level", "secao_eleitoral");
    return `${basePath}?${params.toString()}`;
  }
  const mapQuickLink = topPriority
    ? appendDetailedLayer(
        `/mapa?territory_id=${encodeURIComponent(topPriority.territory_id)}`,
      )
    : appendDetailedLayer("/mapa");
  const resolvedPeriod = appliedPeriod || kpis.period || "2025";
  const resolvedMapLevel = resolveChoroplethLevel(appliedLevel);

  const choroplethItems = (choroplethQuery.data?.items ?? []).map((item: Record<string, unknown>) => ({
    territoryId: String(item.territory_id ?? ""),
    territoryName: String(item.territory_name ?? ""),
    value: typeof item.value === "number" ? item.value : null,
    geometry: (item.geometry as Record<string, unknown>) ?? null,
  }));
  const selectedTerritory =
    choroplethItems.find((item) => item.territoryId === selectedTerritoryId) ?? choroplethItems[0];
  const selectedTerritoryLabel = selectedTerritory?.territoryName ?? selectedFeatureName;
  const mapError = choroplethQuery.error ? formatApiError(choroplethQuery.error) : null;
  const levelScopedLayers = (mapLayersQuery.data?.items ?? []).filter((item) => item.territory_level === appliedLevel);
  const baseDefaultLayerId =
    levelScopedLayers.find((item) => item.default_visibility)?.id ??
    levelScopedLayers[0]?.id ??
    mapLayersQuery.data?.default_layer_id;
  const appliedDetailedLayer = levelScopedLayers.find((item) => item.id === appliedDetailedLayerId) ?? null;
  const appliedDetailedLayerClassification = formatLayerClassificationLabel(appliedDetailedLayer);
  const effectiveDefaultLayerId = appliedDetailedLayer?.id ?? baseDefaultLayerId;
  const canUseVectorMap = Boolean(effectiveDefaultLayerId);
  const isPollingPlaceDetailedLayer = appliedDetailedLayer?.id === "territory_polling_place";
  const mapColorStops = mapStyleQuery.data?.legend_ranges?.map((range) => ({
    value: range.min_value,
    color: range.color,
  }));

  return (
    <main className="page-grid">
      <section className="panel">
        <header className="panel-header">
          <div>
            <h2>Mapa situacional</h2>
            <p className="panel-subtitle">Camada territorial dominante com painel executivo colapsavel</p>
          </div>
        </header>
        <button
          type="button"
          className="map-sidebar-toggle"
          aria-expanded={mapSidebarOpen}
          aria-controls="overview-map-sidebar"
          onClick={() => setMapSidebarOpen((value) => !value)}
        >
          {mapSidebarOpen ? "Ocultar filtros" : "Mostrar filtros"}
        </button>
        <MapDominantLayout
          sidebarOpen={mapSidebarOpen}
          map={
            <>
              {choroplethQuery.isPending ? (
                <StateBlock
                  tone="loading"
                  title="Carregando mapa rapido"
                  message="Consultando distribuicao territorial do recorte aplicado."
                />
              ) : mapError ? (
                <StateBlock
                  tone="error"
                  title="Falha ao carregar mapa rapido"
                  message={mapError.message}
                  requestId={mapError.requestId}
                  onRetry={() => void choroplethQuery.refetch()}
                />
              ) : choroplethItems.length === 0 ? (
                <StateBlock tone="empty" title="Sem dados no mapa" message="Nao ha geometrias para o recorte atual." />
              ) : (
                <>
                  {useVectorMap && canUseVectorMap ? (
                    <div className="map-canvas-shell map-overview-canvas">
                      <Suspense
                        fallback={
                          <StateBlock
                            tone="loading"
                            title="Carregando mapa vetorial"
                            message="Preparando camadas vetoriais da Home executiva."
                          />
                        }
                      >
                        <LazyVectorMap
                          tileBaseUrl={TILE_BASE_URL}
                          layers={levelScopedLayers}
                          defaultLayerId={effectiveDefaultLayerId}
                          zoom={mapZoom}
                          onZoomChange={(zoomValue) => {
                            setMapZoom(zoomValue);
                            globalFilters.setZoom(zoomValue);
                          }}
                          selectedTerritoryId={selectedTerritoryId}
                          focusTerritorySignal={focusSignal}
                          resetViewSignal={resetViewSignal}
                          onFeatureClick={(feature) => {
                            setSelectedTerritoryId(feature.tid || undefined);
                            setSelectedFeatureName(feature.tname || feature.label || null);
                          }}
                          onError={(message) => {
                            const nextError = formatVectorMapError(message);
                            setVectorMapError((current) => (current === nextError ? current : nextError));
                          }}
                          colorStops={mapColorStops}
                          basemapMode={basemapMode}
                          basemapTileUrls={{
                            streets: BASEMAP_STREETS_URL,
                            light: BASEMAP_LIGHT_URL,
                          }}
                        />
                      </Suspense>
                    </div>
                  ) : (
                    <ChoroplethMiniMap
                      items={choroplethItems}
                      selectedTerritoryId={selectedTerritoryId}
                      onSelect={(id) => {
                        setSelectedTerritoryId(id);
                        const selected = choroplethItems.find((item) => item.territoryId === id);
                        setSelectedFeatureName(selected?.territoryName ?? null);
                      }}
                    />
                  )}
                  <div className="map-floating-stats">
                    <span className="map-floating-stat">
                      <strong>{summary.by_status.critical ?? 0}</strong> criticos
                    </span>
                    <span className="map-floating-stat">
                      <strong>{summary.by_status.attention ?? 0}</strong> atencao
                    </span>
                    <span className="map-floating-stat">
                      <strong>{summary.total_items}</strong> monitorados
                    </span>
                  </div>
                  {vectorMapError ? <p className="map-export-error">{vectorMapError}</p> : null}
                </>
              )}
            </>
          }
          sidebar={
            <aside id="overview-map-sidebar" className="map-sidebar-content" aria-label="Painel executivo do mapa">
              <section className="map-sidebar-section">
                <h3>Filtros</h3>
                <p className="panel-subtitle">Periodo e nivel</p>
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
                    <select
                      value={level}
                      onChange={(event) => {
                        const nextLevel = event.target.value;
                        setLevel(nextLevel);
                        if (nextLevel !== "electoral_section") {
                          setDetailedLayerId("");
                        }
                      }}
                    >
                      <option value="municipality">{formatLevelLabel("municipality")}</option>
                      <option value="district">{formatLevelLabel("district")}</option>
                      <option value="census_sector">{formatLevelLabel("census_sector")}</option>
                      <option value="electoral_zone">{formatLevelLabel("electoral_zone")}</option>
                      <option value="electoral_section">{formatLevelLabel("electoral_section")}</option>
                    </select>
                  </label>
                  {canSelectDetailedLayer ? (
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
                <SourceFreshnessBadge metadata={kpis.metadata} />
                {appliedDetailedLayer ? (
                  <p className="map-layer-guidance" title={buildLayerClassificationHint(appliedDetailedLayer)}>
                    Camada detalhada ativa: <strong>{appliedDetailedLayer.label}</strong>.
                    {" "}Classificacao: <strong>{appliedDetailedLayerClassification}</strong>.
                    {isPollingPlaceDetailedLayer
                      ? " O mapa esta priorizando local_votacao detectado por secao eleitoral."
                      : ""}
                  </p>
                ) : null}
              </section>

              <section className="map-sidebar-section">
                <h3>Navegacao do mapa</h3>
                <div className="zoom-control compact" aria-label="Controle de zoom">
                  <label>
                    Zoom
                    <input
                      type="range"
                      min={recommendedOverviewZoom(appliedLevel)}
                      max={18}
                      step={1}
                      value={mapZoom}
                      onChange={(event) => {
                        const nextZoom = Number(event.target.value);
                        setMapZoom(nextZoom);
                        globalFilters.setZoom(nextZoom);
                      }}
                      aria-label="Nivel de zoom do mapa rapido"
                    />
                    <span className="zoom-value">{mapZoom}</span>
                  </label>
                </div>
                <div className="viz-mode-selector" role="radiogroup" aria-label="Mapa base">
                  {BASEMAP_MODES.map((mode) => (
                    <button
                      key={mode.value}
                      type="button"
                      className={`viz-mode-btn${basemapMode === mode.value ? " viz-mode-active" : ""}`}
                      onClick={() => setBasemapMode(mode.value)}
                      role="radio"
                      aria-checked={basemapMode === mode.value}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
                <div className="map-territory-search-row">
                  <button
                    type="button"
                    className="button-secondary"
                    disabled={!selectedTerritoryId}
                    onClick={() => setFocusSignal((value) => value + 1)}
                  >
                    Focar selecionado
                  </button>
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => setResetViewSignal((value) => value + 1)}
                  >
                    Recentrar mapa
                  </button>
                </div>
                <button
                  type="button"
                  className="button-secondary"
                  disabled={!canUseVectorMap}
                  onClick={() => setUseVectorMap((value) => !value)}
                >
                  {useVectorMap ? "Modo simplificado" : canUseVectorMap ? "Modo avancado" : "Somente simplificado"}
                </button>
              </section>

              <section className="map-sidebar-section">
                <h3>Situacao geral</h3>
                <div className="kpi-grid">
                  <StrategicIndexCard
                    label="Criticos"
                    value={String(summary.by_status.critical ?? 0)}
                    status="critical"
                    helper="resposta imediata"
                  />
                  <StrategicIndexCard
                    label="Atencao"
                    value={String(summary.by_status.attention ?? 0)}
                    status="attention"
                    helper="risco moderado"
                  />
                  <StrategicIndexCard
                    label="Estavel"
                    value={String(summary.by_status.stable ?? 0)}
                    status="stable"
                    helper="sob controle"
                  />
                  <StrategicIndexCard
                    label="Dominios"
                    value={String(Object.keys(summary.by_domain).length)}
                    status="info"
                    helper="fontes ativas"
                  />
                </div>
              </section>

              <section className="map-sidebar-section">
                <h3>Acoes rapidas</h3>
                <nav aria-label="Atalhos de decisao" className="quick-actions">
                  <Link className="quick-action-link" to="/prioridades">
                    Prioridades
                  </Link>
                  <Link className="quick-action-link" to={mapQuickLink}>
                    Mapa detalhado
                  </Link>
                  {mostCriticalTerritory ? (
                    <Link className="quick-action-link" to={`/territorio/${mostCriticalTerritory}`}>
                      Territorio critico
                    </Link>
                  ) : null}
                </nav>
                {selectedTerritory ? (
                  <p className="map-selected-note">
                    Selecionado: <strong>Territorio: {selectedTerritoryLabel ?? "n/d"}</strong>
                    {" | "}
                    valor: {formatValueWithUnit(selectedTerritory.value, null)}
                  </p>
                ) : null}
              </section>
            </aside>
          }
        />
      </section>

      <CollapsiblePanel title="Top prioridades" defaultOpen={true} badgeCount={prioritiesPreviewItems.length}>
        {prioritiesPreviewQuery.isPending && !prioritiesPreview ? (
          <StateBlock
            tone="loading"
            title="Carregando top prioridades"
            message="Buscando recorte executivo de prioridades para a Home."
          />
        ) : prioritiesPreviewError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar top prioridades"
            message={prioritiesPreviewError.message}
            requestId={prioritiesPreviewError.requestId}
            onRetry={() => void prioritiesPreviewQuery.refetch()}
          />
        ) : prioritiesPreviewItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada." />
        ) : (
          <div className="priority-card-grid">
            {prioritiesPreviewItems.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel title="Destaques" defaultOpen={false} badgeCount={highlightsItems.length}>
        {highlightsQuery.isPending && !highlights ? (
          <StateBlock
            tone="loading"
            title="Carregando destaques"
            message="Consultando insights executivos para o recorte aplicado."
          />
        ) : highlightsError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar destaques"
            message={highlightsError.message}
            requestId={highlightsError.requestId}
            onRetry={() => void highlightsQuery.refetch()}
          />
        ) : highlightsItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem destaques" message="Sem insights para o recorte." />
        ) : (
          <ul className="trend-list" aria-label="Lista de destaques">
            {highlightsItems.map((item) => (
              <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                </div>
                <small>
                  severidade: {formatStatusLabel(item.severity)} | robustez: {item.robustness}
                </small>
              </li>
            ))}
          </ul>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel
        title="Dominios Onda B/C"
        subtitle="Atalhos para fontes novas com recorte aplicado"
        defaultOpen={false}
        badgeCount={QG_ONDA_BC_SPOTLIGHT.length}
      >
        <div className="table-wrap">
          <table aria-label="Dominios Onda B/C">
            <thead>
              <tr>
                <th>Dominio</th>
                <th>Fonte</th>
                <th>Itens no recorte</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {QG_ONDA_BC_SPOTLIGHT.map((item) => {
                const totalInDomain = summary.by_domain[item.domain] ?? 0;
                const prioritiesLink = `/prioridades?domain=${encodeURIComponent(item.domain)}&period=${encodeURIComponent(
                  resolvedPeriod,
                )}&level=${encodeURIComponent(appliedLevel)}`;
                const mapLink = appendDetailedLayer(
                  `/mapa?level=${encodeURIComponent(resolvedMapLevel)}`,
                );
                return (
                  <tr key={item.domain}>
                    <td>{item.label}</td>
                    <td>{item.source}</td>
                    <td>{totalInDomain}</td>
                    <td>
                      <Link className="inline-link" to={prioritiesLink}>
                        Abrir prioridades
                      </Link>{" "}
                      |{" "}
                      <Link className="inline-link" to={mapLink}>
                        Ver no mapa
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel
        title="KPIs executivos"
        subtitle="Indicadores agregados para leitura rapida"
        defaultOpen={false}
        badgeCount={kpis.items.length}
      >
        {kpis.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem KPIs" message="Nenhum KPI encontrado para os filtros aplicados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dominio</th>
                  <th>Indicador</th>
                  <th>Valor</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {kpis.items.map((item) => (
                  <tr key={`${item.domain}-${item.indicator_code}`}>
                    <td>{getQgDomainLabel(item.domain)}</td>
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
