export type QgDomainSpotlight = {
  domain: string;
  label: string;
  source: string;
  defaultMetric: string;
};

export const QG_ONDA_BC_SPOTLIGHT: QgDomainSpotlight[] = [
  {
    domain: "clima",
    label: "Clima",
    source: "INMET",
    defaultMetric: "INMET_TEMPERATURA_MEDIA_C",
  },
  {
    domain: "meio_ambiente",
    label: "Meio ambiente",
    source: "INPE_QUEIMADAS",
    defaultMetric: "INPE_FOCOS_QUEIMADAS_TOTAL",
  },
  {
    domain: "recursos_hidricos",
    label: "Recursos hidricos",
    source: "ANA",
    defaultMetric: "ANA_VAZAO_MEDIA_M3S",
  },
  {
    domain: "conectividade",
    label: "Conectividade",
    source: "ANATEL",
    defaultMetric: "ANATEL_DENSIDADE_BANDA_LARGA_FIXA_100HAB",
  },
  {
    domain: "energia",
    label: "Energia",
    source: "ANEEL",
    defaultMetric: "ANEEL_UNIDADES_CONSUMIDORAS_TOTAL",
  },
];

export const QG_DOMAIN_OPTIONS = [
  "saude",
  "educacao",
  "trabalho",
  "financas",
  "eleitorado",
  "socioeconomico",
  "mobilidade",
  "seguranca",
  "saneamento",
  "clima",
  "meio_ambiente",
  "recursos_hidricos",
  "conectividade",
  "energia",
];

const QG_DOMAIN_LABELS: Record<string, string> = {
  saude: "Saúde",
  educacao: "Educacao",
  trabalho: "Trabalho",
  financas: "Financas",
  eleitorado: "Eleitorado",
  socioeconomico: "Socioeconomico",
  mobilidade: "Mobilidade",
  seguranca: "Seguranca",
  saneamento: "Saneamento",
  clima: "Clima",
  meio_ambiente: "Meio ambiente",
  recursos_hidricos: "Recursos hidricos",
  conectividade: "Conectividade",
  energia: "Energia",
};

export function normalizeQgDomain(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return QG_DOMAIN_OPTIONS.includes(value) ? value : "";
}

export function getQgDomainLabel(domain: string | null | undefined) {
  if (!domain) {
    return "-";
  }
  return QG_DOMAIN_LABELS[domain] ?? domain;
}
