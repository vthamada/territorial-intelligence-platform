import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import {
  getElectorateCandidateTerritories,
  getElectorateElectionContext,
  getElectorateHistory,
  getElectoratePollingPlaces,
  getElectorateSummary,
} from "../../../shared/api/qg";
import type {
  ElectorateCandidateTerritoriesResponse,
  ElectorateHistoryResponse,
  ElectoratePollingPlacesResponse,
} from "../../../shared/api/types";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatInteger } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

type ElectorateMetric = ElectoratePollingPlacesResponse["metric"];

function formatPercent(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${formatDecimal(value)}%`;
}

function formatMetricValue(metric: ElectorateMetric, value: number | null) {
  if (value === null) {
    return "-";
  }
  if (metric === "voters" || metric === "turnout") {
    return formatInteger(value);
  }
  return formatPercent(value);
}

function formatSectionCountLabel(sectionCount: number) {
  if (sectionCount <= 0) {
    return "-";
  }
  if (sectionCount === 1) {
    return "1 seção";
  }
  return `${formatInteger(sectionCount)} seções`;
}

function metricLabel(metric: ElectorateMetric) {
  if (metric === "voters") {
    return "Total de eleitores";
  }
  if (metric === "turnout") {
    return "Comparecimento";
  }
  if (metric === "abstention_rate") {
    return "Taxa de abstenção";
  }
  if (metric === "blank_rate") {
    return "Taxa de brancos";
  }
  return "Taxa de nulos";
}

function breakdownGroupLabel(group: "sex" | "age" | "education") {
  if (group === "sex") {
    return "sexo";
  }
  if (group === "age") {
    return "faixa etária";
  }
  return "escolaridade";
}

type BreakdownItem = {
  label: string;
  voters: number;
  share_percent: number;
};

function aggregateAgeBreakdown(items: BreakdownItem[]) {
  if (items.length === 0) {
    return items;
  }

  const totalVoters = items.reduce((acc, item) => acc + item.voters, 0);
  let mergedYoungVoters = 0;
  const preservedItems: BreakdownItem[] = [];

  for (const item of items) {
    const ageMatch = item.label.match(/^(\d{2}) anos?$/i);
    const ageValue = ageMatch ? Number(ageMatch[1]) : null;
    if (ageValue !== null && ageValue >= 16 && ageValue <= 20) {
      mergedYoungVoters += item.voters;
      continue;
    }
    preservedItems.push(item);
  }

  const aggregatedItems = [...preservedItems];
  if (mergedYoungVoters > 0) {
    aggregatedItems.push({
      label: "16 a 20 anos",
      voters: mergedYoungVoters,
      share_percent: totalVoters > 0 ? (mergedYoungVoters / totalVoters) * 100 : 0,
    });
  }

  return aggregatedItems.sort((left, right) => right.voters - left.voters || left.label.localeCompare(right.label));
}

function formatSections(sectionCount: number, sections: string[]) {
  if (sectionCount <= 0) {
    return "-";
  }
  if (sections.length === 0) {
    return `${formatInteger(sectionCount)} seções`;
  }
  const preview = sections.slice(0, 6).join(", " );
  const suffix = sections.length > 6 ? " ..." : "";
  return `${formatInteger(sectionCount)} (${preview}${suffix})`;
}

function formatSectionsPreview(sections: string[]) {
  if (sections.length === 0) {
    return "Seções não detalhadas";
  }
  const preview = sections.slice(0, 6).join(", " );
  const suffix = sections.length > 6 ? " ..." : "";
  return `Seções: ${preview}${suffix}`;
}

function formatZones(zoneCodes: string[]) {
  if (zoneCodes.length === 0) {
    return "-";
  }
  return zoneCodes.join(", ");
}

function formatElectionType(value: string | null) {
  if (!value) {
    return "-";
  }
  return value
    .toLowerCase()
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function formatOfficeLabel(value: string | null) {
  if (!value) {
    return "-";
  }
  return value
    .toLowerCase()
    .split(" ")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function buildOfficeSelectionKey(office: string | null | undefined, electionRound: number | null | undefined) {
  if (!office) {
    return null;
  }
  return `${office}::${electionRound ?? ""}`;
}

function parseOfficeSelectionKey(value: string | null) {
  if (!value) {
    return { office: undefined, electionRound: undefined };
  }
  const [office, round] = value.split("::");
  return {
    office: office || undefined,
    electionRound: round ? Number(round) : undefined,
  };
}

function formatCandidateLabel(ballotName: string | null, candidateName: string) {
  return ballotName && ballotName.trim().length > 0 ? ballotName : candidateName;
}

function normalizeDistrictName(value: string | null | undefined) {
  if (!value || value.trim().length === 0) {
    return "Sem distrito identificado";
  }
  return value;
}

function extractMetadataFlag(notes: string | null | undefined, prefix: string) {
  if (!notes) {
    return null;
  }
  const chunk = notes.split("|").find((item) => item.startsWith(`${prefix}=`));
  return chunk ? chunk.slice(prefix.length + 1) : null;
}

function sourceLevelLabel(level: string | null | undefined) {
  if (level === "electoral_zone") {
    return "zona eleitoral";
  }
  if (level === "electoral_section") {
    return "seção eleitoral";
  }
  if (level === "polling_place") {
    return "local de votação";
  }
  if (level === "municipality") {
    return "município";
  }
  return level ?? null;
}

export function ElectorateExecutivePage() {
  const [yearInput, setYearInput] = useState("");
  const [metric, setMetric] = useState<ElectorateMetric>("voters");
  const [appliedYear, setAppliedYear] = useState<number | undefined>(undefined);
  const [appliedMetric, setAppliedMetric] = useState<ElectorateMetric>("voters");
  const [compositionTab, setCompositionTab] = useState<"sex" | "age" | "education">("sex");
  const [selectedOfficeKey, setSelectedOfficeKey] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const requestedOfficeSelection = useMemo(() => parseOfficeSelectionKey(selectedOfficeKey), [selectedOfficeKey]);

  const baseQuery = useMemo(
    () => ({
      level: "municipality",
      year: appliedYear,
    }),
    [appliedYear],
  );

  const summaryQuery = useQuery({
    queryKey: ["qg", "electorate-summary", baseQuery],
    queryFn: () => getElectorateSummary(baseQuery),
  });

  const historyQuery = useQuery({
    queryKey: ["qg", "electorate-history", baseQuery],
    queryFn: () => getElectorateHistory({ ...baseQuery, limit: 10 }),
  });

  const pollingPlacesQuery = useQuery({
    queryKey: ["qg", "electorate-polling-places", appliedYear, appliedMetric],
    queryFn: () => getElectoratePollingPlaces({ year: appliedYear, metric: appliedMetric, limit: 200 }),
  });

  const fallbackSummaryQuery = useQuery({
    queryKey: ["qg", "electorate-summary-fallback", { level: "municipality" }],
    queryFn: () => getElectorateSummary({ level: "municipality" }),
    enabled: appliedYear !== undefined,
  });

  const fallbackHistoryQuery = useQuery({
    queryKey: ["qg", "electorate-history-fallback", { level: "municipality" }],
    queryFn: () => getElectorateHistory({ level: "municipality", limit: 10 }),
    enabled: appliedYear !== undefined,
  });

  const fallbackPollingPlacesQuery = useQuery({
    queryKey: ["qg", "electorate-polling-places-fallback", { metric: appliedMetric }],
    queryFn: () => getElectoratePollingPlaces({ metric: appliedMetric, limit: 200 }),
    enabled: appliedYear !== undefined,
  });

  const summaryYear = summaryQuery.data?.year ?? null;
  const historyCount = historyQuery.data?.items.length ?? 0;
  const pollingPlacesCount = pollingPlacesQuery.data?.items.length ?? 0;
  const summaryTotalVoters = summaryQuery.data?.total_voters ?? 0;
  const hasNoData = summaryYear === null || (summaryTotalVoters === 0 && historyCount === 0 && pollingPlacesCount === 0);

  const fallbackYear =
    fallbackSummaryQuery.data?.year ??
    fallbackPollingPlacesQuery.data?.year ??
    fallbackHistoryQuery.data?.items[0]?.year ??
    null;
  const hasFallbackData =
    Boolean(fallbackYear) &&
    ((fallbackSummaryQuery.data?.total_voters ?? 0) > 0 ||
      (fallbackHistoryQuery.data?.items.length ?? 0) > 0 ||
      (fallbackPollingPlacesQuery.data?.items.length ?? 0) > 0);
  const showingFallbackData = hasNoData && appliedYear !== undefined && hasFallbackData;
  const effectiveDisplayYear = showingFallbackData ? fallbackYear : summaryYear;
  const displayAgeItems =
    (showingFallbackData ? fallbackSummaryQuery.data?.by_age : summaryQuery.data?.by_age) ?? [];
  const ageBreakdown = useMemo(() => aggregateAgeBreakdown(displayAgeItems), [displayAgeItems]);

  const isLoading =
    summaryQuery.isPending ||
    historyQuery.isPending ||
    pollingPlacesQuery.isPending ||
    (appliedYear !== undefined &&
      (fallbackSummaryQuery.isPending || fallbackHistoryQuery.isPending || fallbackPollingPlacesQuery.isPending));
  const firstError = summaryQuery.error ?? historyQuery.error ?? pollingPlacesQuery.error;

  const electionContextQuery = useQuery({
    queryKey: [
      "qg",
      "electorate-election-context",
      effectiveDisplayYear,
      requestedOfficeSelection.office ?? null,
      requestedOfficeSelection.electionRound ?? null,
    ],
    queryFn: () =>
      getElectorateElectionContext({
        level: "municipality",
        year: effectiveDisplayYear ?? undefined,
        office: requestedOfficeSelection.office,
        election_round: requestedOfficeSelection.electionRound,
        limit: 8,
      }),
    enabled: !isLoading && !firstError && effectiveDisplayYear !== null,
  });
  const currentOfficeKey = buildOfficeSelectionKey(
    electionContextQuery.data?.office,
    electionContextQuery.data?.election_round,
  );

  const effectiveCandidateId = useMemo(() => {
    const items = electionContextQuery.data?.items ?? [];
    if (items.length === 0) {
      return null;
    }
    if (selectedCandidateId && items.some((item) => item.candidate_id === selectedCandidateId)) {
      return selectedCandidateId;
    }
    return items[0].candidate_id;
  }, [electionContextQuery.data?.items, selectedCandidateId]);

  const candidateTerritoriesQuery = useQuery({
    queryKey: [
      "qg",
      "electorate-candidate-territories",
      effectiveDisplayYear,
      electionContextQuery.data?.office,
      electionContextQuery.data?.election_round,
      effectiveCandidateId,
    ],
    queryFn: () =>
      getElectorateCandidateTerritories({
        candidate_id: effectiveCandidateId ?? "",
        aggregate_by: "polling_place",
        year: effectiveDisplayYear ?? undefined,
        office: electionContextQuery.data?.office ?? undefined,
        election_round: electionContextQuery.data?.election_round ?? undefined,
        limit: 15,
      }),
    enabled:
      !isLoading &&
      !firstError &&
      effectiveDisplayYear !== null &&
      Boolean(effectiveCandidateId) &&
      electionContextQuery.isSuccess,
  });

  const effectivePollingPlacesData = showingFallbackData ? fallbackPollingPlacesQuery.data : pollingPlacesQuery.data;
  const pollingPlaceGroups = useMemo(() => {
    const items = effectivePollingPlacesData?.items ?? [];
    const groups = new Map<
      string,
      {
        districtName: string;
        totalVoters: number;
        items: ElectoratePollingPlacesResponse["items"];
      }
    >();
    for (const item of items) {
      const districtName = normalizeDistrictName(item.district_name);
      const existing = groups.get(districtName);
      if (existing) {
        existing.totalVoters += item.voters_total;
        existing.items.push(item);
        continue;
      }
      groups.set(districtName, {
        districtName,
        totalVoters: item.voters_total,
        items: [item],
      });
    }
    return Array.from(groups.values()).sort(
      (left, right) => right.totalVoters - left.totalVoters || left.districtName.localeCompare(right.districtName),
    );
  }, [effectivePollingPlacesData?.items]);
  const showMetricColumn = (effectivePollingPlacesData?.metric ?? appliedMetric) !== "voters";

  function applyFilters() {
    const parsedYear = yearInput.trim() ? Number(yearInput) : undefined;
    setAppliedYear(Number.isFinite(parsedYear) ? parsedYear : undefined);
    setAppliedMetric(metric);
    setSelectedOfficeKey(null);
    setSelectedCandidateId(null);
  }

  function clearFilters() {
    setYearInput("");
    setMetric("voters");
    setAppliedYear(undefined);
    setAppliedMetric("voters");
    setSelectedOfficeKey(null);
    setSelectedCandidateId(null);
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando eleitorado executivo"
        message="Consultando resumo, série histórica e ranking dos locais de votação."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar eleitorado executivo"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void summaryQuery.refetch();
          void historyQuery.refetch();
          void pollingPlacesQuery.refetch();
        }}
      />
    );
  }

  const summary = summaryQuery.data!;
  const history = historyQuery.data!;
  const pollingPlaces = pollingPlacesQuery.data!;
  const fallbackError =
    hasNoData && appliedYear !== undefined
      ? fallbackSummaryQuery.error ?? fallbackHistoryQuery.error ?? fallbackPollingPlacesQuery.error
      : null;

  if (fallbackError) {
    const { message, requestId } = formatApiError(fallbackError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar fallback do eleitorado"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void summaryQuery.refetch();
          void historyQuery.refetch();
          void pollingPlacesQuery.refetch();
          void fallbackSummaryQuery.refetch();
          void fallbackHistoryQuery.refetch();
          void fallbackPollingPlacesQuery.refetch();
        }}
      />
    );
  }

  const effectiveSummary = showingFallbackData ? fallbackSummaryQuery.data! : summary;
  const effectiveHistory: ElectorateHistoryResponse = showingFallbackData ? fallbackHistoryQuery.data! : history;
  const effectivePollingPlaces: ElectoratePollingPlacesResponse = showingFallbackData
    ? fallbackPollingPlacesQuery.data!
    : pollingPlaces;
  const selectedCandidate = electionContextQuery.data?.items.find((item) => item.candidate_id === effectiveCandidateId) ?? null;
  const candidateTerritories: ElectorateCandidateTerritoriesResponse | null = candidateTerritoriesQuery.data ?? null;
  const electionContextSourceLevel = extractMetadataFlag(electionContextQuery.data?.metadata.notes, "source_level");
  const candidateTerritoriesSourceLevel = extractMetadataFlag(candidateTerritories?.metadata.notes, "source_level");
  const candidateTerritoriesRequestedAggregate = extractMetadataFlag(candidateTerritories?.metadata.notes, "requested_aggregate");
  const candidateTerritoriesUnavailable = candidateTerritories?.metadata.notes?.startsWith("candidate_territories_unavailable") ?? false;

  return (
    <div className="page-grid">
      <Panel title="Eleitorado e participação" subtitle="Leitura institucional para apoio à decisão">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Ano
            <input value={yearInput} onChange={(event) => setYearInput(event.target.value)} placeholder="2024" />
          </label>
          <label>
            Métrica do ranking
            <select value={metric} onChange={(event) => setMetric(event.target.value as ElectorateMetric)}>
              <option value="voters">{metricLabel("voters")}</option>
              <option value="turnout">{metricLabel("turnout")}</option>
              <option value="abstention_rate">{metricLabel("abstention_rate")}</option>
              <option value="blank_rate">{metricLabel("blank_rate")}</option>
              <option value="null_rate">{metricLabel("null_rate")}</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        <SourceFreshnessBadge metadata={effectiveSummary.metadata} />

        {showingFallbackData ? (
          <StateBlock
            tone="empty"
            title={`Ano ${appliedYear} sem dados consolidados`}
            message={
              fallbackYear
                ? `Mostrando automaticamente o último recorte com dados (${fallbackYear}) para manter a leitura executiva.`
                : "Mostrando automaticamente o último recorte com dados disponível."
            }
          />
        ) : null}
        {hasNoData && appliedYear !== undefined && !showingFallbackData ? (
          <StateBlock
            tone="empty"
            title="Sem dados para o ano informado"
            message={
              fallbackYear
                ? `Não há dados consolidados para ${appliedYear}. Use ${fallbackYear} para visualizar o recorte mais recente.`
                : `Não há dados consolidados para ${appliedYear}. Limpe o filtro de ano para tentar o último recorte disponível.`
            }
          />
        ) : null}
        {hasNoData && appliedYear === undefined && !showingFallbackData ? (
          <StateBlock
            tone="empty"
            title="Sem dados de eleitorado no recorte atual"
            message={
              fallbackYear
                ? `Não há dados consolidados no recorte padrão. Use ${fallbackYear} para visualizar o último ano com dados.`
                : "Não há dados consolidados no recorte padrão. Informe um ano e aplique filtros para consultar disponibilidade."
            }
          />
        ) : null}
        {hasNoData && appliedYear !== undefined && !showingFallbackData ? (
          <div className="filter-actions" style={{ marginTop: "0.55rem" }}>
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setYearInput("");
                setAppliedYear(undefined);
                setSelectedCandidateId(null);
              }}
            >
              Usar último ano disponível
            </button>
          </div>
        ) : null}

        <div className="panel-actions-row">
          <Link className="inline-link" to="/mapa?level=secao_eleitoral&layer_id=territory_polling_place">
            Abrir mapa eleitoral (locais de votação)
          </Link>
        </div>
      </Panel>

      <Panel title="Resumo executivo" subtitle="Volume eleitoral e comportamento de participação">
        <div className="kpi-grid">
          <article>
            <span>Ano</span>
            <strong>{effectiveSummary.year ?? "-"}</strong>
          </article>
          <article>
            <span>Total eleitores</span>
            <strong>{effectiveSummary.total_voters ? formatInteger(effectiveSummary.total_voters) : "-"}</strong>
          </article>
          <article>
            <span>Taxa comparecimento</span>
            <strong>{formatPercent(effectiveSummary.turnout_rate)}</strong>
          </article>
          <article>
            <span>Taxa abstenção</span>
            <strong>{formatPercent(effectiveSummary.abstention_rate)}</strong>
          </article>
          <article>
            <span>Brancos</span>
            <strong>{formatPercent(effectiveSummary.blank_rate)}</strong>
          </article>
          <article>
            <span>Nulos</span>
            <strong>{formatPercent(effectiveSummary.null_rate)}</strong>
          </article>
        </div>
      </Panel>

      <Panel title="Histórico eleitoral" subtitle="Evolução recente do eleitorado e participação">
        {effectiveHistory.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem histórico eleitoral" message="Nenhuma série anual disponível para o recorte atual." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ano</th>
                  <th>Eleitores</th>
                  <th>Comparecimento</th>
                  <th>Taxa comparecimento</th>
                  <th>Taxa abstenção</th>
                  <th>Brancos</th>
                  <th>Nulos</th>
                </tr>
              </thead>
              <tbody>
                {effectiveHistory.items.map((item) => (
                  <tr key={item.year}>
                    <td>{item.year}</td>
                    <td>{formatInteger(item.total_voters)}</td>
                    <td>{item.turnout === null ? "-" : formatInteger(item.turnout)}</td>
                    <td>{formatPercent(item.turnout_rate)}</td>
                    <td>{formatPercent(item.abstention_rate)}</td>
                    <td>{formatPercent(item.blank_rate)}</td>
                    <td>{formatPercent(item.null_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Contexto da eleição" subtitle="Cargo principal e candidatos mais votados no recorte exibido">
        {electionContextQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando contexto da eleição" message="Consultando candidatos e escopo da eleição para o ano exibido." />
        ) : electionContextQuery.error ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar contexto da eleição"
            message={formatApiError(electionContextQuery.error).message}
            requestId={formatApiError(electionContextQuery.error).requestId}
            onRetry={() => void electionContextQuery.refetch()}
          />
        ) : !electionContextQuery.data || electionContextQuery.data.items.length === 0 ? (
          <StateBlock
            tone="empty"
            title="Sem contexto nominal"
            message="Ainda não há dados nominais de candidatos para o recorte exibido."
          />
        ) : (
          <div>
            <div className="kpi-grid">
              <article>
                <span>Ano eleitoral</span>
                <strong>{electionContextQuery.data.year ?? "-"}</strong>
              </article>
              <article>
                <span>Tipo da eleição</span>
                <strong>{formatElectionType(electionContextQuery.data.election_type)}</strong>
              </article>
              <article>
                <span>Cargo em exibição</span>
                <strong>{formatOfficeLabel(electionContextQuery.data.office)}</strong>
              </article>
              <article>
                <span>Turno</span>
                <strong>
                  {electionContextQuery.data.election_round ? `${electionContextQuery.data.election_round}º turno` : "-"}
                </strong>
              </article>
              <article>
                <span>Total de votos válidos do recorte</span>
                <strong>{formatInteger(electionContextQuery.data.total_votes)}</strong>
              </article>
            </div>
            {electionContextQuery.data.available_offices.length > 1 ? (
              <div
                style={{
                  display: "grid",
                  gap: "0.35rem",
                  marginTop: "1rem",
                  marginBottom: "1rem",
                  maxWidth: "22rem",
                }}
              >
                <label htmlFor="electorate-office-select">Cargo da eleição</label>
                <select
                  id="electorate-office-select"
                  value={selectedOfficeKey ?? currentOfficeKey ?? ""}
                  onChange={(event) => {
                    setSelectedOfficeKey(event.target.value || null);
                    setSelectedCandidateId(null);
                  }}
                >
                  {electionContextQuery.data.available_offices.map((item) => {
                    const value = buildOfficeSelectionKey(item.office, item.election_round) ?? "";
                    const label = `${formatOfficeLabel(item.office)}${
                      item.election_round ? ` · ${item.election_round}º turno` : ""
                    }`;
                    return (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>
            ) : null}
            {electionContextSourceLevel ? (
              <StateBlock
                tone="empty"
                title={`Contexto nominal agregado a partir de ${sourceLevelLabel(electionContextSourceLevel)}`}
                message="Nesta rodada, o contexto municipal de candidatos foi consolidado a partir da melhor granularidade nominal oficial disponível."
              />
            ) : null}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Candidato</th>
                    <th>Número</th>
                    <th>Partido</th>
                    <th>Votos</th>
                    <th>% do recorte</th>
                    <th>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {electionContextQuery.data.items.map((item) => (
                    <tr key={item.candidate_id}>
                      <td>{formatCandidateLabel(item.ballot_name, item.candidate_name)}</td>
                      <td>{item.candidate_number}</td>
                      <td>{item.party_abbr ?? item.party_name ?? "-"}</td>
                      <td>{formatInteger(item.votes)}</td>
                      <td>{formatPercent(item.share_percent)}</td>
                      <td>
                        <button
                          type="button"
                          className={effectiveCandidateId === item.candidate_id ? "button-secondary" : undefined}
                          onClick={() => setSelectedCandidateId(item.candidate_id)}
                        >
                          {effectiveCandidateId === item.candidate_id ? "Selecionado" : "Ver distribuição"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>

      <Panel
        title="Distribuição territorial do candidato"
        subtitle={
          selectedCandidate
            ? candidateTerritoriesUnavailable && candidateTerritoriesSourceLevel
              ? `${formatCandidateLabel(selectedCandidate.ballot_name, selectedCandidate.candidate_name)} com distribuição nominal disponível em ${sourceLevelLabel(candidateTerritoriesSourceLevel)}`
              : `${formatCandidateLabel(selectedCandidate.ballot_name, selectedCandidate.candidate_name)} por local de votação`
            : "Selecione um candidato para ver a distribuição territorial"
        }
      >
        {candidateTerritoriesQuery.isPending ? (
          <StateBlock tone="loading" title="Carregando distribuição territorial" message="Consultando os locais com maior votação do candidato selecionado." />
        ) : candidateTerritoriesQuery.error ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar distribuição territorial"
            message={formatApiError(candidateTerritoriesQuery.error).message}
            requestId={formatApiError(candidateTerritoriesQuery.error).requestId}
            onRetry={() => void candidateTerritoriesQuery.refetch()}
          />
        ) : candidateTerritoriesUnavailable && candidateTerritoriesSourceLevel ? (
          <StateBlock
            tone="empty"
            title={`Distribuição nominal disponível apenas em ${sourceLevelLabel(candidateTerritoriesSourceLevel)}`}
            message={
              candidateTerritoriesRequestedAggregate
                ? `A fonte nominal carregada nesta rodada não desce até ${sourceLevelLabel(candidateTerritoriesRequestedAggregate)}. O contexto de candidatos segue válido no agregado municipal.`
                : "A fonte nominal carregada nesta rodada não possui granularidade territorial suficiente para o recorte solicitado."
            }
          />
        ) : !candidateTerritories || candidateTerritories.items.length === 0 ? (
          <StateBlock
            tone="empty"
            title="Sem distribuição territorial"
            message="Nenhum local de votação retornado para o candidato selecionado."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Local</th>
                  <th>Distrito</th>
                  <th>Zonas</th>
                        <th>Seções</th>
                  <th>Votos</th>
                  <th>% do candidato</th>
                </tr>
              </thead>
              <tbody>
                {candidateTerritories.items.map((item) => (
                  <tr key={`${item.territory_id}-${item.candidate_id}`}>
                    <td>{item.polling_place_name ?? item.territory_name}</td>
                    <td>{item.district_name ?? "-"}</td>
                    <td>{formatZones(item.zone_codes)}</td>
                    <td>{formatSections(item.section_count, item.sections)}</td>
                    <td>{formatInteger(item.votes)}</td>
                    <td>{formatPercent(item.share_percent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel
        title="Ranking de locais de votação"
        subtitle={`${metricLabel(effectivePollingPlaces.metric)} por local de votação, agrupado por distrito`}
      >
        {effectivePollingPlaces.items.length === 0 ? (
          <StateBlock
            tone="empty"
            title="Sem ranking eleitoral"
            message="Nenhum local de votação retornado para a métrica selecionada."
          />
        ) : (
          <div style={{ display: "grid", gap: "1rem" }}>
            {pollingPlaceGroups.map((group) => (
              <section
                key={group.districtName}
                style={{
                  display: "grid",
                  gap: "0.6rem",
                  border: "1px solid var(--line)",
                  borderRadius: "0.9rem",
                  padding: "0.85rem",
                  background: "rgba(255, 253, 248, 0.65)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", alignItems: "baseline", flexWrap: "wrap" }}>
                  <div>
                    <h3 style={{ fontSize: "1rem" }}>{group.districtName}</h3>
                    <p className="panel-subtitle">
                      {group.items.length} locais · {formatInteger(group.totalVoters)} eleitores no distrito
                    </p>
                  </div>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Local</th>
                        <th>Zonas</th>
                        <th>Seções</th>
                        <th>Eleitores</th>
                        <th>% do município</th>
                        {showMetricColumn ? <th>Indicador selecionado</th> : null}
                      </tr>
                    </thead>
                    <tbody>
                      {group.items.map((item) => (
                        <tr key={`${group.districtName}-${item.territory_id}-${item.metric}`}>
                          <td>{item.polling_place_name ?? item.territory_name}</td>
                          <td>{formatZones(item.zone_codes)}</td>
                          <td>
                            <div style={{ display: "grid", gap: "0.18rem" }}>
                              <strong>{formatSectionCountLabel(item.section_count)}</strong>
                              <span style={{ color: "var(--ink-soft)", fontSize: "0.82rem" }}>
                                {formatSectionsPreview(item.sections)}
                              </span>
                            </div>
                          </td>
                          <td>{formatInteger(item.voters_total)}</td>
                          <td>{formatPercent(item.share_percent)}</td>
                          {showMetricColumn ? <td>{formatMetricValue(item.metric, item.value)}</td> : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Composição do eleitorado" subtitle="Distribuição por sexo, faixa etária e escolaridade">
        {effectiveSummary.by_sex.length === 0 && effectiveSummary.by_age.length === 0 && effectiveSummary.by_education.length === 0 ? (
          <StateBlock tone="empty" title="Sem composição" message="Não há dados de composição para o recorte atual." />
        ) : (
          <div>
            <div className="viz-mode-selector" role="tablist" aria-label="Composição do eleitorado">
              <button
                type="button"
                className={`viz-mode-btn${compositionTab === "sex" ? " viz-mode-active" : ""}`}
                onClick={() => setCompositionTab("sex")}
              >
                Sexo
              </button>
              <button
                type="button"
                className={`viz-mode-btn${compositionTab === "age" ? " viz-mode-active" : ""}`}
                onClick={() => setCompositionTab("age")}
              >
                Idade
              </button>
              <button
                type="button"
                className={`viz-mode-btn${compositionTab === "education" ? " viz-mode-active" : ""}`}
                onClick={() => setCompositionTab("education")}
              >
                Escolaridade
              </button>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Grupo</th>
                    <th>Categoria</th>
                    <th>Eleitores</th>
                    <th>Participação</th>
                  </tr>
                </thead>
                <tbody>
                  {compositionTab === "sex"
                    ? effectiveSummary.by_sex.map((item) => (
                        <tr key={`sex-${item.label}`}>
                          <td>{breakdownGroupLabel("sex")}</td>
                          <td>{item.label}</td>
                          <td>{formatInteger(item.voters)}</td>
                          <td>{formatPercent(item.share_percent)}</td>
                        </tr>
                      ))
                    : null}
                  {compositionTab === "age"
                    ? ageBreakdown.map((item) => (
                        <tr key={`age-${item.label}`}>
                          <td>{breakdownGroupLabel("age")}</td>
                          <td>{item.label}</td>
                          <td>{formatInteger(item.voters)}</td>
                          <td>{formatPercent(item.share_percent)}</td>
                        </tr>
                      ))
                    : null}
                  {compositionTab === "education"
                    ? effectiveSummary.by_education.map((item) => (
                        <tr key={`education-${item.label}`}>
                          <td>{breakdownGroupLabel("education")}</td>
                          <td>{item.label}</td>
                          <td>{formatInteger(item.voters)}</td>
                          <td>{formatPercent(item.share_percent)}</td>
                        </tr>
                      ))
                    : null}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
