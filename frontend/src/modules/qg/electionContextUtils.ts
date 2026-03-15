import { getElectorateElectionContext } from "../../shared/api/qg";
import type { ElectorateElectionContextResponse } from "../../shared/api/types";

export function normalizeExecutiveLevel(value: string | null | undefined) {
  if (value === "district" || value === "census_sector" || value === "electoral_zone" || value === "electoral_section") {
    return value;
  }
  return "municipality";
}

export function formatOfficeLabel(value: string | null) {
  if (!value) {
    return "-";
  }
  return value
    .toLocaleLowerCase("pt-BR")
    .split(" ")
    .map((part) => part.charAt(0).toLocaleUpperCase("pt-BR") + part.slice(1))
    .join(" ");
}

export function formatCandidateLabel(ballotName: string | null, candidateName: string | null) {
  return ballotName || candidateName || "-";
}

export function formatInteger(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${value.toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

export async function getExecutiveElectionContext(level: string) {
  try {
    const payload = await getElectorateElectionContext({ level, limit: 5 });
    if (payload.items.length > 0 || level === "municipality") {
      return payload;
    }
  } catch (error) {
    if (level === "municipality") {
      throw error;
    }
  }
  return getElectorateElectionContext({ level: "municipality", limit: 5 });
}

export function buildElectorateDeepLink(
  context: ElectorateElectionContextResponse | null | undefined,
  candidateId?: string | null,
) {
  const search = new URLSearchParams();
  if (context?.year) {
    search.set("year", String(context.year));
  }
  if (context?.office) {
    search.set("office", context.office);
  }
  if (context?.election_round) {
    search.set("election_round", String(context.election_round));
  }
  if (candidateId) {
    search.set("candidate_id", candidateId);
  }
  const queryString = search.toString();
  return `/eleitorado${queryString ? `?${queryString}` : ""}`;
}

export function buildElectoralMapDeepLink(
  context: ElectorateElectionContextResponse | null | undefined,
  params?: { territoryId?: string | null; electoralMetric?: string | null },
) {
  const search = new URLSearchParams();
  search.set("level", "secao_eleitoral");
  search.set("layer_id", "territory_polling_place");
  search.set("electoral_metric", params?.electoralMetric || "voters");
  if (context?.year) {
    search.set("period", String(context.year));
  }
  if (params?.territoryId) {
    search.set("territory_id", params.territoryId);
  }
  return `/mapa?${search.toString()}`;
}
