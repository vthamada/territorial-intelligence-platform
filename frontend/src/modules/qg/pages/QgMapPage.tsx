import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useSearchParams } from "react-router-dom";
import { getChoropleth, getMapLayers } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { ChoroplethMiniMap } from "../../../shared/ui/ChoroplethMiniMap";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatLevelLabel, toNumber } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";

function formatNumber(value: unknown) {
  const numeric = toNumber(value);
  if (numeric === null) {
    return "-";
  }
  return formatDecimal(numeric);
}

function normalizeMapLevel(value: string | null) {
  if (value === "distrito" || value === "district") {
    return "distrito";
  }
  return "municipio";
}

function toManifestTerritoryLevel(level: string) {
  return level === "distrito" ? "district" : "municipality";
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
  const initialMetric = searchParams.get("metric") || "MTE_NOVO_CAGED_SALDO_TOTAL";
  const initialPeriod = searchParams.get("period") || "2025";
  const initialLevel = normalizeMapLevel(searchParams.get("level"));
  const initialTerritoryId = searchParams.get("territory_id") || undefined;
  const [metric, setMetric] = useState(initialMetric);
  const [period, setPeriod] = useState(initialPeriod);
  const [level, setLevel] = useState(initialLevel);
  const [appliedMetric, setAppliedMetric] = useState(initialMetric);
  const [appliedPeriod, setAppliedPeriod] = useState(initialPeriod);
  const [appliedLevel, setAppliedLevel] = useState(initialLevel);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string | undefined>(initialTerritoryId);
  const [exportError, setExportError] = useState<string | null>(null);

  const choroplethParams = useMemo(
    () => ({
      metric: appliedMetric,
      period: appliedPeriod,
      level: appliedLevel,
      page: 1,
      page_size: 1000
    }),
    [appliedLevel, appliedMetric, appliedPeriod]
  );

  const choroplethQuery = useQuery({
    queryKey: ["qg", "map", choroplethParams],
    queryFn: () => getChoropleth(choroplethParams)
  });

  const mapLayersQuery = useQuery({
    queryKey: ["qg", "map", "layers"],
    queryFn: () => getMapLayers(),
    staleTime: 5 * 60 * 1000
  });

  function applyFilters() {
    setAppliedMetric(metric);
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setSelectedTerritoryId(undefined);
  }

  function clearFilters() {
    setMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setPeriod("2025");
    setLevel("municipio");
    setAppliedMetric("MTE_NOVO_CAGED_SALDO_TOTAL");
    setAppliedPeriod("2025");
    setAppliedLevel("municipio");
    setSelectedTerritoryId(undefined);
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
      setExportError("Nao foi possivel localizar o mapa para exportacao.");
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
      setExportError("Nao foi possivel localizar o mapa para exportacao.");
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

  if (choroplethQuery.isPending) {
    return <StateBlock tone="loading" title="Carregando mapa" message="Consultando distribuicao territorial do indicador." />;
  }

  if (choroplethQuery.error) {
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

  const choropleth = choroplethQuery.data!;
  const normalizedItems = choropleth.items.map((item) => ({
    ...item,
    value: toNumber(item.value),
  }));
  const sortedItems = [...normalizedItems].sort(
    (a, b) => (b.value ?? Number.NEGATIVE_INFINITY) - (a.value ?? Number.NEGATIVE_INFINITY)
  );
  const selectedItem =
    sortedItems.find((item) => item.territory_id === selectedTerritoryId) ??
    sortedItems[0];
  const activeTerritoryLevel = toManifestTerritoryLevel(appliedLevel);
  const recommendedLayer =
    mapLayersQuery.data?.items.find(
      (layer) => layer.territory_level === activeTerritoryLevel && layer.default_visibility
    ) ?? mapLayersQuery.data?.items.find((layer) => layer.territory_level === activeTerritoryLevel);

  return (
    <div className="page-grid">
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
              <option value="municipio">Municipio</option>
              <option value="distrito">Distrito</option>
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
                recommendedLayer.zoom_max
              )})`
            : "Camada recomendada: manifesto de camadas em carregamento."}
        </p>
        {mapLayersQuery.error ? (
          <p className="map-export-error">
            Manifesto de camadas indisponivel; mantendo fallback em {choroplethParams.level}.
          </p>
        ) : null}
      </Panel>

      <Panel title="Mapa visual" subtitle="Visualizacao geografica simplificada com escala de valor">
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportMapSvg}>
            Exportar SVG
          </button>
          <button type="button" className="button-secondary" onClick={exportMapPng}>
            Exportar PNG
          </button>
        </div>
        <ChoroplethMiniMap
          items={sortedItems.map((item) => ({
            territoryId: item.territory_id,
            territoryName: item.territory_name,
            value: item.value,
            geometry: item.geometry
          }))}
          selectedTerritoryId={selectedTerritoryId}
          onSelect={setSelectedTerritoryId}
        />
        {selectedItem ? (
          <p className="map-selected-note">
            Selecionado: <strong>{selectedItem.territory_name}</strong> | valor: {formatNumber(selectedItem.value)} |{" "}
            <Link className="inline-link" to={`/territorio/${selectedItem.territory_id}`}>
              abrir perfil
            </Link>
          </p>
        ) : null}
        {exportError ? <p className="map-export-error">{exportError}</p> : null}
      </Panel>

      <Panel title="Ranking territorial" subtitle="Leitura tabular do choropleth para apoio a priorizacao">
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportCsv} disabled={sortedItems.length === 0}>
            Exportar CSV
          </button>
        </div>
        {sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem dados para mapa" message="Nenhum territorio encontrado para o recorte informado." />
        ) : (
          <div className="table-wrap">
            <table>
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
    </div>
  );
}
