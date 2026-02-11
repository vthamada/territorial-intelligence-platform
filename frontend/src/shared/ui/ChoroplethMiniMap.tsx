type GeoJsonPolygon = {
  type: "Polygon";
  coordinates: number[][][];
};

type GeoJsonMultiPolygon = {
  type: "MultiPolygon";
  coordinates: number[][][][];
};

type ChoroplethGeometry = GeoJsonPolygon | GeoJsonMultiPolygon;

type ChoroplethFeature = {
  territoryId: string;
  territoryName: string;
  value: number | null;
  geometry: Record<string, unknown> | null;
};

type ChoroplethMiniMapProps = {
  items: ChoroplethFeature[];
  selectedTerritoryId?: string;
  onSelect?: (territoryId: string) => void;
};

type Point = { x: number; y: number };
type PreparedFeature = {
  territoryId: string;
  territoryName: string;
  value: number | null;
  paths: string[];
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function parseGeometry(raw: Record<string, unknown> | null): ChoroplethGeometry | null {
  if (!raw || typeof raw.type !== "string" || !("coordinates" in raw)) {
    return null;
  }
  if (raw.type === "Polygon") {
    return raw as unknown as GeoJsonPolygon;
  }
  if (raw.type === "MultiPolygon") {
    return raw as unknown as GeoJsonMultiPolygon;
  }
  return null;
}

function flattenCoordinates(geometry: ChoroplethGeometry): Point[] {
  if (geometry.type === "Polygon") {
    return geometry.coordinates.flatMap((ring) => ring.map(([x, y]) => ({ x, y })));
  }
  return geometry.coordinates.flatMap((polygon) => polygon.flatMap((ring) => ring.map(([x, y]) => ({ x, y }))));
}

function normalizePath(
  ring: number[][],
  bbox: { minX: number; maxX: number; minY: number; maxY: number },
  width: number,
  height: number,
  padding: number
) {
  const contentWidth = width - padding * 2;
  const contentHeight = height - padding * 2;
  const xRange = Math.max(1e-9, bbox.maxX - bbox.minX);
  const yRange = Math.max(1e-9, bbox.maxY - bbox.minY);

  const points = ring.map(([lon, lat]) => {
    const nx = (lon - bbox.minX) / xRange;
    const ny = (bbox.maxY - lat) / yRange;
    return {
      x: padding + nx * contentWidth,
      y: padding + ny * contentHeight
    };
  });

  if (points.length < 3) {
    return "";
  }

  const [first, ...rest] = points;
  return `M ${first.x.toFixed(2)} ${first.y.toFixed(2)} ${rest
    .map((point) => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ")} Z`;
}

function featureColor(value: number | null, minValue: number, maxValue: number) {
  if (value === null) {
    return "#d9d9d9";
  }
  if (minValue === maxValue) {
    return "#0f766e";
  }
  const t = clamp((value - minValue) / (maxValue - minValue), 0, 1);
  const r = Math.round(lerp(217, 15, t));
  const g = Math.round(lerp(237, 118, t));
  const b = Math.round(lerp(232, 110, t));
  return `rgb(${r}, ${g}, ${b})`;
}

export function ChoroplethMiniMap({ items, selectedTerritoryId, onSelect }: ChoroplethMiniMapProps) {
  const width = 820;
  const height = 420;
  const padding = 16;

  const rawFeatures = items
    .map((item) => ({
      territoryId: item.territoryId,
      territoryName: item.territoryName,
      value: item.value,
      geometry: parseGeometry(item.geometry)
    }))
    .filter((item) => item.geometry !== null);

  if (rawFeatures.length === 0) {
    return <p className="map-empty">Sem geometria valida para renderizar mapa.</p>;
  }

  const allPoints = rawFeatures.flatMap((feature) => flattenCoordinates(feature.geometry!));
  const bbox = {
    minX: Math.min(...allPoints.map((point) => point.x)),
    maxX: Math.max(...allPoints.map((point) => point.x)),
    minY: Math.min(...allPoints.map((point) => point.y)),
    maxY: Math.max(...allPoints.map((point) => point.y))
  };

  const preparedFeatures: PreparedFeature[] = rawFeatures.map((feature) => {
    const geometry = feature.geometry!;
    const paths: string[] = [];
    if (geometry.type === "Polygon") {
      const outerRing = geometry.coordinates[0] ?? [];
      const path = normalizePath(outerRing, bbox, width, height, padding);
      if (path) {
        paths.push(path);
      }
    } else {
      for (const polygon of geometry.coordinates) {
        const outerRing = polygon[0] ?? [];
        const path = normalizePath(outerRing, bbox, width, height, padding);
        if (path) {
          paths.push(path);
        }
      }
    }
    return {
      territoryId: feature.territoryId,
      territoryName: feature.territoryName,
      value: feature.value,
      paths
    };
  });

  const values = preparedFeatures.map((feature) => feature.value).filter((value): value is number => value !== null);
  const minValue = values.length > 0 ? Math.min(...values) : 0;
  const maxValue = values.length > 0 ? Math.max(...values) : 0;

  return (
    <div className="choropleth-wrapper">
      <svg className="choropleth-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Mapa coropletico">
        <rect x={0} y={0} width={width} height={height} fill="#f6f4ee" />
        {preparedFeatures.map((feature) =>
          feature.paths.map((path, pathIndex) => {
            const isSelected = feature.territoryId === selectedTerritoryId;
            return (
              <path
                key={`${feature.territoryId}-${pathIndex}`}
                d={path}
                fill={featureColor(feature.value, minValue, maxValue)}
                stroke={isSelected ? "#111827" : "#f8fafc"}
                strokeWidth={isSelected ? 2.2 : 1}
                className="choropleth-path"
                onClick={() => onSelect?.(feature.territoryId)}
              >
                <title>
                  {feature.territoryName} - {feature.value ?? "sem valor"}
                </title>
              </path>
            );
          })
        )}
      </svg>
      <div className="choropleth-legend">
        <span>Menor: {Number.isFinite(minValue) ? minValue.toFixed(2) : "-"}</span>
        <span>Maior: {Number.isFinite(maxValue) ? maxValue.toFixed(2) : "-"}</span>
      </div>
    </div>
  );
}
