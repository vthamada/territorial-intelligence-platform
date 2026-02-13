import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { getChoropleth, getMapLayers, getMapLayersCoverage, getMapStyleMetadata } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { useAutoLayerSwitch } from "../../../shared/hooks/useAutoLayerSwitch";
import { ChoroplethMiniMap } from "../../../shared/ui/ChoroplethMiniMap";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatLevelLabel, toNumber } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { VectorMap, type VizMode } from "../../../shared/ui/VectorMap";
import { useFilterStore } from "../../../shared/stores/filterStore";

const TILE_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/v1";

const VIZ_MODES: { value: VizMode; label: string }[] = [
  { value: "choropleth", label: "Coropletico" },
  { value: "points", label: "Pontos" },
  { value: "heatmap", label: "Heatmap" },
  { value: "hotspots", label: "Hotspots" },
];

function formatNumber(value: unknown) {
  const numeric = toNumber(value);
  if (numeric === null) {
    return "-";
  }
  return formatDecimal(numeric);
}

function normalizeMapLevel(value: string | null) {
  const normalized = (value ?? "").trim().toLowerCase();
  if (normalized === "municipio" || normalized === "municipality") {
    return "municipio";
  }
  if (normalized === "distrito" || normalized === "district") {
    return "distrito";
  }
  if (normalized === "setor_censitario" || normalized === "census_sector") {
    return "setor_censitario";
  }
  if (normalized === "zona_eleitoral" || normalized === "electoral_zone") {
    return "zona_eleitoral";
  }
  if (normalized === "secao_eleitoral" || normalized === "electoral_section") {
    return "secao_eleitoral";
  }
  return "municipio";
}

function toManifestTerritoryLevel(level: string) {
  if (level === "distrito") {
    return "district";
  }
  if (level === "setor_censitario") {
    return "census_sector";
  }
  if (level === "zona_eleitoral") {
    return "electoral_zone";
  }
  if (level === "secao_eleitoral") {
    return "electoral_section";
  }
  return "municipality";
}

function toFormLevel(level: string) {
  if (level === "district") {
    return "distrito";
  }
  if (level === "census_sector") {
    return "setor_censitario";
  }
  if (level === "electoral_zone") {
    return "zona_eleitoral";
  }
  if (level === "electoral_section") {
    return "secao_eleitoral";
  }
  return "municipio";
}

function supportsChoropleth(level: string) {
  return level === "municipio" || level === "distrito";
}

const MAP_LEVEL_ORDER: string[] = [
  "municipality",
  "district",
  "census_sector",
  "electoral_zone",
  "electoral_section",
];

function sortLayerLevels(a: string, b: string) {
  const aIndex = MAP_LEVEL_ORDER.indexOf(a);
  const bIndex = MAP_LEVEL_ORDER.indexOf(b);
  if (aIndex === -1 && bIndex === -1) {
    return a.localeCompare(b);
  }
  if (aIndex === -1) {
    return 1;
  }
  if (bIndex === -1) {
    return -1;
  }
  return aIndex - bIndex;
}

function formatZoomRange(zoomMin: number, zoomMax: number | null) {
  if (zoomMax === null) {
    return `z>=${zoomMin}`;
  }
  return `z${zoomMin}-${zoomMax}`;
}

function csvEscape(value: string) {
  const escaped = value.split('"').join('""');
  return `"${escaped}"`;
}

function sanitizeFilePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "mapa";
}

function triggerDownload(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function QgMapPage() {
  const [searchParams] = useSearchParams();
  const globalFilters = useFilterStore();
  const initialMetric = searchParams.get("metric") || "MTE_NOVO_CAGED_SALDO_TOTAL";
  const initialPeriod = searchParams.get("period") || "2025";
  const initialLevel = normalizeMapLevel(searchParams.get("level"));
  const initialTerritoryId = searchParams.get("territory_id") || undefined;
  const initialLayerId = searchParams.get("layer_id") || null;

  const [metric, setMetric] = useState(initialMetric);
  const [period, setPeriod] = useState(initialPeriod);
  const [level, setLevel] = useState<string>(initialLevel);
  const [appliedMetric, setAppliedMetric] = useState(initialMetric);
  const [appliedPeriod, setAppliedPeriod] = useState(initialPeriod);
  const [appliedLevel, setAppliedLevel] = useState<string>(initialLevel);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string | undefined>(initialTerritoryId);
  const [exportError, setExportError] = useState<string | null>(null);
  const [vectorMapError, setVectorMapError] = useState<string | null>(null);
  const [currentZoom, setCurrentZoom] = useState(globalFilters.zoom);
  const [vizMode, setVizMode] = useState<VizMode>("choropleth");
  const [useVectorMap, setUseVectorMap] = useState(true);
  const [selectedFeature, setSelectedFeature] = useState<{ tid: string; tname: string; val?: number } | null>(null);
  const [selectedVectorLayerId, setSelectedVectorLayerId] = useState<string | null>(initialLayerId);
  const previousAppliedLevelRef = useRef(appliedLevel);

  const isChoroplethLevel = supportsChoropleth(appliedLevel);

  const choroplethParams = useMemo(
    () => ({
      metric: appliedMetric,
      period: appliedPeriod,
      level: appliedLevel,
      page: 1,
      page_size: 1000,
    }),
    [appliedLevel, appliedMetric, appliedPeriod],
  );

  const choroplethQuery = useQuery({
    queryKey: ["qg", "map", choroplethParams],
    queryFn: () => getChoropleth(choroplethParams),
    enabled: isChoroplethLevel,
  });

  const mapLayersQuery = useQuery({
    queryKey: ["qg", "map", "layers"],
    queryFn: () => getMapLayers(),
    staleTime: 5 * 60 * 1000,
  });

  const mapStyleQuery = useQuery({
    queryKey: ["qg", "map", "style-metadata"],
    queryFn: () => getMapStyleMetadata(),
    staleTime: 5 * 60 * 1000,
  });

  const layersCoverageQuery = useQuery({
    queryKey: ["qg", "map", "layers", "coverage", appliedMetric, appliedPeriod],
    queryFn: () => getMapLayersCoverage({ metric: appliedMetric, period: appliedPeriod }),
    staleTime: 60 * 1000,
  });

  const availableFormLevels = useMemo<string[]>(() => {
    const levels = Array.from(new Set((mapLayersQuery.data?.items ?? []).map((item) => item.territory_level)));
    return levels.sort(sortLayerLevels).map((item) => toFormLevel(item));
  }, [mapLayersQuery.data?.items]);

  useEffect(() => {
    if (availableFormLevels.length === 0) {
      return;
    }
    if (!availableFormLevels.includes(level)) {
      setLevel(availableFormLevels[0]);
    }
    if (!availableFormLevels.includes(appliedLevel)) {
      setAppliedLevel(availableFormLevels[0]);
    }
  }, [appliedLevel, availableFormLevels, level]);

  const activeTerritoryLevel = toManifestTerritoryLevel(appliedLevel);
  const levelScopedLayers = useMemo(
    () => (mapLayersQuery.data?.items ?? []).filter((layerItem) => layerItem.territory_level === activeTerritoryLevel),
    [activeTerritoryLevel, mapLayersQuery.data?.items],
  );
  const resolvedDefaultLayerId =
    levelScopedLayers.find((layerItem) => layerItem.default_visibility)?.id ??
    levelScopedLayers[0]?.id ??
    mapLayersQuery.data?.default_layer_id;

  const autoLayer = useAutoLayerSwitch(
    levelScopedLayers.length > 0 ? levelScopedLayers : mapLayersQuery.data?.items,
    currentZoom,
    resolvedDefaultLayerId,
  );

  const normalizedItems = useMemo(
    () =>
      (isChoroplethLevel ? choroplethQuery.data?.items ?? [] : []).map((item) => ({
        ...item,
        value: toNumber(item.value),
      })),
    [choroplethQuery.data?.items, isChoroplethLevel],
  );

  const sortedItems = useMemo(
    () =>
      [...normalizedItems].sort(
        (a, b) => (b.value ?? Number.NEGATIVE_INFINITY) - (a.value ?? Number.NEGATIVE_INFINITY),
      ),
    [normalizedItems],
  );

  const canUseVectorMap = Boolean(resolvedDefaultLayerId);
  const availableLevelLayerIds = useMemo(() => new Set(levelScopedLayers.map((item) => item.id)), [levelScopedLayers]);
  const selectedLayerCoverage = layersCoverageQuery.data?.items.find(
    (item) => item.territory_level === activeTerritoryLevel,
  );

  useEffect(() => {
    setVectorMapError(null);
    if (!canUseVectorMap) {
      setUseVectorMap(false);
    }
  }, [appliedLevel, appliedMetric, appliedPeriod, canUseVectorMap]);

  useEffect(() => {
    if (!selectedVectorLayerId) {
      return;
    }
    if (levelScopedLayers.length === 0) {
      return;
    }
    if (!availableLevelLayerIds.has(selectedVectorLayerId)) {
      setSelectedVectorLayerId(null);
    }
  }, [availableLevelLayerIds, levelScopedLayers.length, selectedVectorLayerId]);

  useEffect(() => {
    if (previousAppliedLevelRef.current !== appliedLevel) {
      setSelectedVectorLayerId(null);
    }
    previousAppliedLevelRef.current = appliedLevel;
  }, [appliedLevel]);

  function handleZoomChange(newZoom: number) {
    setCurrentZoom(newZoom);
    globalFilters.setZoom(newZoom);
  }

  function applyFilters() {
    setAppliedMetric(metric);
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setSelectedTerritoryId(undefined);
    setSelectedFeature(null);
    setExportError(null);
    setVectorMapError(null);
  }

  function clearFilters() {
    setMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setPeriod("2025");
    setLevel("municipio");
    setAppliedMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setAppliedPeriod("2025");
    setAppliedLevel("municipio");
    setSelectedTerritoryId(undefined);
    setSelectedFeature(null);
    setExportError(null);
    setVectorMapError(null);
  }

  function exportCsv() {
    if (!sortedItems.length) {
      return;
    }
    const rows = [
      ["territory_id", "territory_name", "level", "metric", "reference_period", "value"],
      ...sortedItems.map((item) => [
        item.territory_id,
        item.territory_name,
        item.level,
        item.metric,
        item.reference_period,
        item.value === null ? "" : String(item.value),
      ]),
    ];
    const csv = rows.map((row) => row.map(csvEscape).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    triggerDownload(blob, "qg_mapa_ranking.csv");
  }

  function resolveMapSvgElement() {
    const node = document.querySelector(".choropleth-svg");
    if (node instanceof SVGSVGElement) {
      return node;
    }
    return null;
  }

  function serializeMapSvg() {
    const svg = resolveMapSvgElement();
    if (!svg) {
      return null;
    }
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svg);
    if (!source.includes("xmlns=")) {
      source = source.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    if (!source.includes("xmlns:xlink=")) {
      source = source.replace("<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
    }
    return { svg, source };
  }

  function exportMapSvg() {
    setExportError(null);
    const serialized = serializeMapSvg();
    if (!serialized) {
      setExportError("Nao foi possivel localizar o mapa para exportacao. Use o modo SVG fallback.");
      return;
    }
    const metricPart = sanitizeFilePart(appliedMetric);
    const periodPart = sanitizeFilePart(appliedPeriod);
    const fileName = `qg_mapa_${metricPart}_${periodPart}.svg`;
    const blob = new Blob([serialized.source], { type: "image/svg+xml;charset=utf-8" });
    triggerDownload(blob, fileName);
  }

  function exportMapPng() {
    setExportError(null);
    const serialized = serializeMapSvg();
    if (!serialized) {
      setExportError("Nao foi possivel localizar o mapa para exportacao. Use o modo SVG fallback.");
      return;
    }

    const { svg, source } = serialized;
    const viewBox = svg.viewBox?.baseVal;
    const width = Math.max(1, Math.round(viewBox?.width || 820));
    const height = Math.max(1, Math.round(viewBox?.height || 420));

    const svgBlob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
    const svgUrl = URL.createObjectURL(svgBlob);
    const image = new Image();

    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        if (!context) {
          setExportError("Nao foi possivel preparar o canvas para exportacao.");
          URL.revokeObjectURL(svgUrl);
          return;
        }
        context.fillStyle = "#f6f4ee";
        context.fillRect(0, 0, width, height);
        context.drawImage(image, 0, 0, width, height);
        canvas.toBlob((blob) => {
          URL.revokeObjectURL(svgUrl);
          if (!blob) {
            setExportError("Falha ao converter o mapa para PNG.");
            return;
          }
          const metricPart = sanitizeFilePart(appliedMetric);
          const periodPart = sanitizeFilePart(appliedPeriod);
          const fileName = `qg_mapa_${metricPart}_${periodPart}.png`;
          triggerDownload(blob, fileName);
        }, "image/png");
      } catch (_error) {
        URL.revokeObjectURL(svgUrl);
        setExportError("Falha ao exportar PNG no navegador atual.");
      }
    };

    image.onerror = () => {
      URL.revokeObjectURL(svgUrl);
      setExportError("Falha ao carregar imagem temporaria para exportacao.");
    };

    image.src = svgUrl;
  }

  if (isChoroplethLevel && choroplethQuery.isPending) {
    return <StateBlock tone="loading" title="Carregando mapa" message="Consultando distribuicao territorial do indicador." />;
  }

  if (isChoroplethLevel && choroplethQuery.error) {
    const { message, requestId } = formatApiError(choroplethQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar mapa"
        message={message}
        requestId={requestId}
        onRetry={() => void choroplethQuery.refetch()}
      />
    );
  }

  const selectedItem = sortedItems.find((item) => item.territory_id === selectedTerritoryId) ?? sortedItems[0];
  const recommendedLayer =
    levelScopedLayers.find((layerItem) => layerItem.default_visibility) ?? levelScopedLayers[0];
  const hasMultipleLevelLayers = levelScopedLayers.length > 1;
  const explicitLayer = selectedVectorLayerId
    ? levelScopedLayers.find((layerItem) => layerItem.id === selectedVectorLayerId) ?? null
    : null;
  const effectiveLayer = explicitLayer ?? autoLayer ?? recommendedLayer;
  const vectorLayers = effectiveLayer ? [effectiveLayer] : levelScopedLayers;
  const effectiveVizMode: VizMode =
    effectiveLayer?.layer_kind === "point" && vizMode === "choropleth" ? "points" : vizMode;

  const selectedTerritoryName = selectedItem?.territory_name ?? selectedFeature?.tname;
  const selectedTerritoryValue = selectedItem?.value ?? selectedFeature?.val;
  const selectedTerritoryIdSafe = selectedItem?.territory_id ?? selectedFeature?.tid;

  return (
    <main className="page-grid">
      <Panel title="Mapa estrategico" subtitle="Distribuicao territorial por indicador e periodo">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Codigo do indicador
            <input value={metric} onChange={(event) => setMetric(event.target.value)} />
          </label>
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} />
          </label>
          <label>
            Nivel territorial
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              {availableFormLevels.length === 0 ? (
                <option value="municipio">Municipio</option>
              ) : (
                availableFormLevels.map((levelOption) => (
                  <option key={levelOption} value={levelOption}>
                    {formatLevelLabel(levelOption)}
                  </option>
                ))
              )}
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <p className="map-selected-note">
          {recommendedLayer
            ? `Camada recomendada: ${recommendedLayer.label} (${formatZoomRange(
                recommendedLayer.zoom_min,
                recommendedLayer.zoom_max,
              )})`
            : "Camada recomendada: manifesto de camadas em carregamento."}
          {autoLayer && autoLayer.id !== recommendedLayer?.id ? ` | Auto-zoom: ${autoLayer.label} (z=${currentZoom})` : null}
        </p>
        {hasMultipleLevelLayers ? (
          <div className="map-layer-toggle">
            <label>
              Camada de secao
              <select
                value={selectedVectorLayerId ?? ""}
                onChange={(event) => setSelectedVectorLayerId(event.target.value || null)}
                aria-label="Camada de secao"
              >
                <option value="">Automatica (recomendada)</option>
                {levelScopedLayers.map((layerItem) => (
                  <option key={layerItem.id} value={layerItem.id}>
                    {layerItem.label}
                  </option>
                ))}
              </select>
            </label>
            <p
              className="map-selected-note"
              title={effectiveLayer?.proxy_method ?? effectiveLayer?.notes ?? "Camada sem metadata adicional."}
            >
              Camada ativa: <strong>{effectiveLayer?.label ?? "n/d"}</strong>
              {effectiveLayer?.proxy_method ? ` | metodo: ${effectiveLayer.proxy_method}` : ""}
            </p>
          </div>
        ) : null}
        <div className="zoom-control compact" aria-label="Controle de zoom">
          <label>
            Zoom
            <input
              type="range"
              min={0}
              max={18}
              step={1}
              value={currentZoom}
              onChange={(e) => handleZoomChange(Number(e.target.value))}
              aria-label="Nivel de zoom do mapa"
            />
            <span className="zoom-value">{currentZoom}</span>
          </label>
        </div>
        {mapLayersQuery.error ? (
          <p className="map-export-error">
            Manifesto de camadas indisponivel; mantendo fallback em {choroplethParams.level}.
          </p>
        ) : null}
        {selectedLayerCoverage ? (
          <p className="map-selected-note">
            Cobertura da camada: {selectedLayerCoverage.territories_with_geometry}/{selectedLayerCoverage.territories_total} com
            geometria
            {isChoroplethLevel
              ? ` | ${selectedLayerCoverage.territories_with_indicator} com indicador no recorte`
              : ""}
            {selectedLayerCoverage.notes ? ` | ${selectedLayerCoverage.notes}` : ""}
          </p>
        ) : null}
      </Panel>

      <Panel title="Mapa visual" subtitle="Visualizacao vetorial MVT com fallback SVG">
        <div className="panel-actions-row">
          <div className="viz-mode-selector" role="radiogroup" aria-label="Modo de visualizacao">
            {VIZ_MODES.map((mode) => (
              <button
                key={mode.value}
                type="button"
                className={`viz-mode-btn${vizMode === mode.value ? " viz-mode-active" : ""}`}
                onClick={() => setVizMode(mode.value)}
                role="radio"
                aria-checked={vizMode === mode.value}
              >
                {mode.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="button-secondary"
            onClick={() => setUseVectorMap((prev) => !prev)}
            disabled={!canUseVectorMap}
            aria-label={useVectorMap ? "Alternar para SVG fallback" : "Alternar para mapa vetorial"}
          >
            {useVectorMap ? "SVG fallback" : canUseVectorMap ? "Mapa vetorial" : "Somente SVG"}
          </button>
        </div>
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportMapSvg} aria-label="Exportar mapa como SVG">
            Exportar SVG
          </button>
          <button type="button" className="button-secondary" onClick={exportMapPng} aria-label="Exportar mapa como PNG">
            Exportar PNG
          </button>
        </div>
        {mapStyleQuery.data ? (
          <div className="map-style-meta">
            <p>
              Modo: <strong>{VIZ_MODES.find((mode) => mode.value === effectiveVizMode)?.label ?? effectiveVizMode}</strong> | versao: {mapStyleQuery.data.version}
            </p>
            <div className="map-style-chip-row">
              {mapStyleQuery.data.severity_palette.map((item) => (
                <span key={item.severity} className="map-style-chip" style={{ borderColor: item.color, color: item.color }}>
                  {item.label}
                </span>
              ))}
            </div>
            {effectiveLayer?.layer_kind === "point" ? (
              <p>Camada atual e pontual; coropletico muda automaticamente para pontos.</p>
            ) : null}
          </div>
        ) : null}
        {mapStyleQuery.error ? (
          <p className="map-export-error">Metadados de estilo indisponiveis; legenda padrao mantida.</p>
        ) : null}
        {useVectorMap && canUseVectorMap ? (
          <div style={{ height: 500, borderRadius: "0.5rem", overflow: "hidden", border: "1px solid var(--line)" }}>
            <VectorMap
              tileBaseUrl={TILE_BASE_URL}
              metric={appliedMetric}
              period={appliedPeriod}
              layers={vectorLayers.length > 0 ? vectorLayers : levelScopedLayers}
              defaultLayerId={effectiveLayer?.id ?? resolvedDefaultLayerId}
              vizMode={effectiveVizMode}
              zoom={currentZoom}
              onZoomChange={(z) => handleZoomChange(z)}
              onFeatureClick={(feature) => {
                setSelectedTerritoryId(feature.tid);
                setSelectedFeature(feature);
              }}
              onError={() => {
                setVectorMapError("Falha no modo vetorial, fallback SVG aplicado.");
                setUseVectorMap(false);
              }}
              selectedTerritoryId={selectedTerritoryId}
              colorStops={mapStyleQuery.data?.legend_ranges?.map((range) => ({ value: range.min_value, color: range.color }))}
            />
          </div>
        ) : (
          <ChoroplethMiniMap
            items={sortedItems.map((item) => ({
              territoryId: item.territory_id,
              territoryName: item.territory_name,
              value: item.value,
              geometry: item.geometry,
            }))}
            selectedTerritoryId={selectedTerritoryId}
            onSelect={setSelectedTerritoryId}
          />
        )}
        {selectedTerritoryName ? (
          <p className="map-selected-note">
            Selecionado: <strong>{selectedTerritoryName}</strong> | valor: {formatNumber(selectedTerritoryValue)}
            {selectedTerritoryIdSafe ? (
              <>
                {" "}
                |{" "}
                <Link className="inline-link" to={`/territorio/${selectedTerritoryIdSafe}`}>
                  abrir perfil
                </Link>
              </>
            ) : null}
          </p>
        ) : null}
        {vectorMapError ? <p className="map-export-error">{vectorMapError}</p> : null}
        {exportError ? <p className="map-export-error">{exportError}</p> : null}
      </Panel>

      <Panel title="Ranking territorial" subtitle="Leitura tabular do choropleth para apoio a priorizacao">
        <div className="panel-actions-row">
          <button
            type="button"
            className="button-secondary"
            onClick={exportCsv}
            disabled={sortedItems.length === 0}
            aria-label="Exportar ranking como CSV"
          >
            Exportar CSV
          </button>
        </div>
        {!isChoroplethLevel ? (
          <StateBlock
            tone="empty"
            title="Ranking indisponivel neste nivel"
            message="O ranking tabular ainda usa o endpoint de choropleth (municipio/distrito). O mapa vetorial continua ativo para exploracao."
          />
        ) : sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados para mapa" message="Nenhum territorio encontrado para o recorte informado." />
        ) : (
          <div className="table-wrap">
            <table aria-label="Ranking territorial">
              <thead>
                <tr>
                  <th>Territorio</th>
                  <th>Nivel</th>
                  <th>Metrica</th>
                  <th>Periodo</th>
                  <th>Valor</th>
                  <th>Acao</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((item) => (
                  <tr
                    key={item.territory_id}
                    className={item.territory_id === selectedTerritoryId ? "territory-selected-row" : undefined}
                    onClick={() => setSelectedTerritoryId(item.territory_id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedTerritoryId(item.territory_id);
                      }
                    }}
                    tabIndex={0}
                    role="button"
                    aria-pressed={item.territory_id === selectedTerritoryId}
                  >
                    <td>{item.territory_name}</td>
                    <td>{formatLevelLabel(item.level)}</td>
                    <td>{item.metric}</td>
                    <td>{item.reference_period}</td>
                    <td>{formatNumber(item.value)}</td>
                    <td>
                      <Link className="inline-link" to={`/territorio/${item.territory_id}`}>
                        Abrir perfil
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </main>
  );
}
