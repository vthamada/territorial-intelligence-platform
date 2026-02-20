export function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const normalized = value.trim().replace(",", ".");
    if (!normalized) {
      return null;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function formatDecimal(value: number, fractionDigits = 2): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatInteger(value: number): string {
  return value.toLocaleString("pt-BR", {
    maximumFractionDigits: 0,
  });
}

function formatCurrencyBRL(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function normalizeUnit(unit: string | null): string {
  return (unit ?? "").trim().toLowerCase();
}

export function formatValueWithUnit(value: unknown, unit: string | null, fractionDigits = 2): string {
  const numeric = toNumber(value);
  if (numeric === null) {
    return "-";
  }

  const normalizedUnit = normalizeUnit(unit);
  if (normalizedUnit === "brl" || normalizedUnit === "r$") {
    return formatCurrencyBRL(numeric);
  }
  if (normalizedUnit === "%") {
    return `${formatDecimal(numeric, fractionDigits)} %`;
  }
  if (normalizedUnit === "count") {
    return formatInteger(Math.round(numeric));
  }
  if (normalizedUnit === "pessoas" || normalizedUnit === "habitantes") {
    return `${formatInteger(Math.round(numeric))} ${unit}`;
  }
  if (normalizedUnit === "percent") {
    return `${formatDecimal(numeric, fractionDigits)}%`;
  }
  if (normalizedUnit === "ratio") {
    return formatDecimal(numeric, fractionDigits);
  }

  const UNIT_DISPLAY: Record<string, string> = {
    c: "°C",
    mm: "mm",
    "m3/s": "m³/s",
    m3s: "m³/s",
    km: "km",
    ha: "ha",
    kwh: "kWh",
  };
  const displayUnit = UNIT_DISPLAY[normalizedUnit];
  if (displayUnit) {
    return `${formatDecimal(numeric, fractionDigits)} ${displayUnit}`;
  }

  const formatted = formatDecimal(numeric, fractionDigits);
  return unit ? `${formatted} ${unit}` : formatted;
}

const LEVEL_LABELS: Record<string, string> = {
  municipality: "Municipio",
  municipio: "Municipio",
  district: "Distrito",
  distrito: "Distrito",
  census_sector: "Setor censitario",
  setor_censitario: "Setor censitario",
  electoral_zone: "Zona eleitoral",
  zona_eleitoral: "Zona eleitoral",
  electoral_section: "Secao eleitoral",
  secao_eleitoral: "Secao eleitoral",
};

export function formatLevelLabel(level: string | null | undefined): string {
  if (!level) {
    return "-";
  }
  return LEVEL_LABELS[level] ?? level;
}

const STATUS_LABELS: Record<string, string> = {
  critical: "critico",
  attention: "atencao",
  stable: "estavel",
  info: "informativo",
  improved: "melhorou",
  worsened: "piorou",
  unchanged: "inalterado",
  success: "sucesso",
  fail: "falha",
  failed: "falha",
  warn: "alerta",
  blocked: "bloqueado",
};

export function formatStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "-";
  }
  return STATUS_LABELS[status] ?? status;
}

const TREND_LABELS: Record<string, string> = {
  up: "subindo",
  down: "caindo",
  flat: "estavel",
  stable: "estavel",
  improving: "melhorando",
  worsening: "piorando",
};

export function formatTrendLabel(trend: string | null | undefined): string {
  if (!trend) {
    return "-";
  }
  return TREND_LABELS[trend] ?? trend;
}

const SOURCE_NAME_LABELS: Record<string, string> = {
  "silver.fact_indicator": "Indicadores consolidados",
  "silver.fact_electorate": "Eleitorado consolidado",
  fact_indicator: "Indicadores consolidados",
  fact_electorate: "Eleitorado consolidado",
};

const COVERAGE_NOTE_LABELS: Record<string, string> = {
  territorial_aggregated: "Agregado territorial",
  regional_aggregated: "Agregado regional",
  municipal: "Municipal",
  district: "Distrital",
};

export function humanizeSourceName(raw: string | null | undefined): string {
  if (!raw) {
    return "-";
  }
  return SOURCE_NAME_LABELS[raw] ?? raw;
}

export function humanizeCoverageNote(raw: string | null | undefined): string {
  if (!raw) {
    return "-";
  }
  return COVERAGE_NOTE_LABELS[raw] ?? raw;
}

const DATASET_SOURCE_LABELS: Record<string, string> = {
  SICONFI: "SICONFI",
  SIOPS: "SIOPS",
  DATASUS: "DATASUS",
  INEP: "INEP",
  IBGE: "IBGE",
  MTE: "MTE",
  ANEEL: "ANEEL",
  ANA: "ANA",
  ANATEL: "ANATEL",
  INMET: "INMET",
  INPE: "INPE/Queimadas",
  INPE_QUEIMADAS: "INPE/Queimadas",
  TSE: "TSE",
};

const DATASET_NAME_LABELS: Record<string, string> = {
  siconfi_dca_finance: "Financas municipais (DCA)",
  siops_health_finance_municipal: "Financas de saude (SIOPS)",
  datasus_aps_municipal: "Atencao primaria (APS)",
  inep_education_municipal: "Educacao municipal",
  ibge_social_indicators: "Indicadores sociais",
  ibge_population: "Populacao estimada",
  mte_caged_municipal: "Emprego formal (CAGED)",
  aneel_energy_municipal: "Energia eletrica",
  ana_water_resources: "Recursos hidricos",
  anatel_broadband: "Banda larga",
  inmet_climate: "Dados climaticos",
  inpe_fires: "Focos de queimadas",
  tse_electorate: "Eleitorado",
};

export function humanizeDatasetSource(source: string | null | undefined, dataset: string | null | undefined): string {
  if (!source && !dataset) {
    return "-";
  }
  const humanSource = (source && DATASET_SOURCE_LABELS[source]) || source || "";
  const humanDataset = (dataset && DATASET_NAME_LABELS[dataset]) || null;
  if (humanDataset) {
    return `${humanSource} — ${humanDataset}`;
  }
  return humanSource || "-";
}
