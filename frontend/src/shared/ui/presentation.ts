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
  if (normalizedUnit === "count" || normalizedUnit === "pessoas" || normalizedUnit === "habitantes") {
    const rounded = Math.round(numeric);
    return `${formatInteger(rounded)} ${unit}`;
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
