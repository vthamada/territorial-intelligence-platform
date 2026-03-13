import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getElectorateElectionContext, getPriorityList } from "../../../shared/api/qg";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { formatLevelLabel } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";

type PrioritySort = "criticality_desc" | "criticality_asc" | "territory_asc" | "trend_desc";

function trendWeight(trend: string) {
  const normalized = trend.toLowerCase();
  if (normalized === "worsening" || normalized === "up") {
    return 3;
  }
  if (normalized === "stable" || normalized === "flat") {
    return 2;
  }
  if (normalized === "improving" || normalized === "down") {
    return 1;
  }
  return 0;
}

function csvEscape(value: string) {
  const escaped = value.split('"').join('""');
  return `"${escaped}"`;
}

function normalizeLevel(value: string | null) {
  if (value === "district" || value === "census_sector" || value === "electoral_zone" || value === "electoral_section") {
    return value;
  }
  return "municipality";
}

function normalizeSort(value: string | null): PrioritySort {
  if (value === "criticality_desc" || value === "criticality_asc" || value === "territory_asc" || value === "trend_desc") {
    return value;
  }
  return "criticality_desc";
}

function formatOfficeLabel(value: string | null) {
  if (!value) {
    return "-";
  }
  return value
    .toLocaleLowerCase("pt-BR")
    .split(" ")
    .map((part) => part.charAt(0).toLocaleUpperCase("pt-BR") + part.slice(1))
    .join(" ");
}

function formatCandidateLabel(ballotName: string | null, candidateName: string | null) {
  return ballotName || candidateName || "-";
}

function formatInteger(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${value.toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

async function getExecutiveElectionContext(level: string) {
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

export function QgPrioritiesPage() {
  const [searchParams] = useSearchParams();
  const initialPeriod = searchParams.get("period") || "";
  const initialLevel = normalizeLevel(searchParams.get("level"));
  const initialDomain = normalizeQgDomain(searchParams.get("domain"));
  const initialOnlyCritical = searchParams.get("only_critical") === "true";
  const initialSortBy = normalizeSort(searchParams.get("sort"));

  const [period, setPeriod] = useState(initialPeriod);
  const [level, setLevel] = useState(initialLevel);
  const [domain, setDomain] = useState(initialDomain);
  const [onlyCritical, setOnlyCritical] = useState(initialOnlyCritical);
  const [sortBy, setSortBy] = useState<PrioritySort>(initialSortBy);
  const [limit, setLimit] = useState("24");
  const [appliedPeriod, setAppliedPeriod] = useState(initialPeriod);
  const [appliedLevel, setAppliedLevel] = useState(initialLevel);
  const [appliedDomain, setAppliedDomain] = useState(initialDomain);
  const [appliedOnlyCritical, setAppliedOnlyCritical] = useState(initialOnlyCritical);
  const [appliedSortBy, setAppliedSortBy] = useState<PrioritySort>(initialSortBy);
  const [appliedLimit, setAppliedLimit] = useState("24");
  const [pageSize, setPageSize] = useState("24");
  const [currentPage, setCurrentPage] = useState(1);

  const query = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel,
      domain: appliedDomain || undefined,
      limit: Number(appliedLimit) || 24
    }),
    [appliedDomain, appliedLevel, appliedLimit, appliedPeriod]
  );

  const prioritiesQuery = useQuery({
    queryKey: ["qg", "priority-list", query],
    queryFn: () => getPriorityList(query)
  });
  const electionContextQuery = useQuery({
    queryKey: ["qg", "priority-list", "election-context", appliedLevel],
    queryFn: () => getExecutiveElectionContext(appliedLevel),
  });

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setAppliedDomain(domain);
    setAppliedOnlyCritical(onlyCritical);
    setAppliedSortBy(sortBy);
    setAppliedLimit(limit);
    setCurrentPage(1);
  }

  function clearFilters() {
    setPeriod("");
    setLevel("municipality");
    setDomain("");
    setOnlyCritical(false);
    setSortBy("criticality_desc");
    setLimit("24");
    setAppliedPeriod("");
    setAppliedLevel("municipality");
    setAppliedDomain("");
    setAppliedOnlyCritical(false);
    setAppliedSortBy("criticality_desc");
    setAppliedLimit("24");
    setPageSize("24");
    setCurrentPage(1);
  }

  const priorities = prioritiesQuery.data;
  const filteredItems = useMemo(() => {
    if (!priorities) return [];
    return appliedOnlyCritical ? priorities.items.filter((item) => item.status === "critical") : priorities.items;
  }, [priorities, appliedOnlyCritical]);
  const sortedItems = useMemo(() => {
    const items = [...filteredItems];
    if (appliedSortBy === "criticality_asc") {
      items.sort((a, b) => a.score - b.score);
      return items;
    }
    if (appliedSortBy === "territory_asc") {
      items.sort((a, b) => a.territory_name.localeCompare(b.territory_name, "pt-BR"));
      return items;
    }
    if (appliedSortBy === "trend_desc") {
      items.sort((a, b) => trendWeight(b.trend) - trendWeight(a.trend) || b.score - a.score);
      return items;
    }
    items.sort((a, b) => b.score - a.score);
    return items;
  }, [appliedSortBy, filteredItems]);
  const summaryByStatus = useMemo(() => {
    const statusCounts = { critical: 0, attention: 0, stable: 0 };
    for (const item of sortedItems) {
      if (item.status === "critical") {
        statusCounts.critical += 1;
      } else if (item.status === "attention") {
        statusCounts.attention += 1;
      } else {
        statusCounts.stable += 1;
      }
    }
    return statusCounts;
  }, [sortedItems]);
  const activeFilterSummary = useMemo(() => {
    const tokens: string[] = [];
    if (appliedPeriod) tokens.push(`Período ${appliedPeriod}`);
    if (appliedDomain) tokens.push(`Domínio ${getQgDomainLabel(appliedDomain)}`);
    if (appliedOnlyCritical) tokens.push("Somente críticos");
    if (appliedLevel) tokens.push(`Nível ${formatLevelLabel(appliedLevel)}`);
    return tokens;
  }, [appliedDomain, appliedLevel, appliedOnlyCritical, appliedPeriod]);
  const normalizedPageSize = Math.max(1, Number(pageSize) || 24);
  const totalPages = Math.max(1, Math.ceil(sortedItems.length / normalizedPageSize));
  const visibleItems = useMemo(() => {
    const start = (currentPage - 1) * normalizedPageSize;
    return sortedItems.slice(start, start + normalizedPageSize);
  }, [currentPage, normalizedPageSize, sortedItems]);
  const electionContext = electionContextQuery.data ?? null;
  const electionContextError = electionContextQuery.error ? formatApiError(electionContextQuery.error) : null;
  const leadingCandidate = electionContext?.items[0] ?? null;

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [pageSize]);

  if (prioritiesQuery.isPending) {
    return (
      <StateBlock tone="loading" title="Carregando prioridades" message="Consultando ranking de criticidade territorial." />
    );
  }

  if (prioritiesQuery.error) {
    const { message, requestId } = formatApiError(prioritiesQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar prioridades"
        message={message}
        requestId={requestId}
        onRetry={() => void prioritiesQuery.refetch()}
      />
    );
  }

  function exportCsv() {
    if (sortedItems.length === 0) {
      return;
    }
    const rows = [
      [
        "territory_id",
        "territory_name",
        "territory_level",
        "domain",
        "indicator_code",
        "indicator_name",
        "value",
        "unit",
        "score",
        "trend",
        "status",
        "reference_period",
        "source",
        "dataset",
      ],
      ...sortedItems.map((item) => [
        item.territory_id,
        item.territory_name,
        item.territory_level,
        item.domain,
        item.indicator_code,
        item.indicator_name,
        String(item.value),
        item.unit ?? "",
        String(item.score),
        item.trend,
        item.status,
        item.evidence.reference_period,
        item.evidence.source,
        item.evidence.dataset,
      ]),
    ];
    const csv = rows.map((row) => row.map(csvEscape).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "qg_prioridades.csv";
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }

  return (
    <main className="page-grid">
      <Panel title="Prioridades estratégicas" subtitle="Ranking territorial por criticidade e evidência">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Período
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nível territorial
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
              <option value="district">{formatLevelLabel("district")}</option>
              <option value="census_sector">{formatLevelLabel("census_sector")}</option>
              <option value="electoral_zone">{formatLevelLabel("electoral_zone")}</option>
              <option value="electoral_section">{formatLevelLabel("electoral_section")}</option>
            </select>
          </label>
          <label>
            Domínio
            <select value={domain} onChange={(event) => setDomain(event.target.value)}>
              <option value="">Todos</option>
              {QG_DOMAIN_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {getQgDomainLabel(option)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Somente críticos
            <select value={String(onlyCritical)} onChange={(event) => setOnlyCritical(event.target.value === "true")}>
              <option value="false">Não</option>
              <option value="true">Sim</option>
            </select>
          </label>
          <label>
            Ordenar por
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as PrioritySort)}>
              <option value="criticality_desc">criticidade (maior score)</option>
              <option value="criticality_asc">criticidade (menor score)</option>
              <option value="trend_desc">tendência (pior primeiro)</option>
              <option value="territory_asc">território (A-Z)</option>
            </select>
          </label>
          <label>
            Itens
            <select value={limit} onChange={(event) => setLimit(event.target.value)}>
              <option value="24">24</option>
              <option value="48">48</option>
              <option value="100">100</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={priorities!.metadata} />
        {electionContextQuery.isPending && !electionContext ? (
          <StateBlock
            tone="loading"
            title="Carregando contexto eleitoral"
            message="Buscando o cargo principal e a liderança nominal do nível filtrado."
          />
        ) : electionContextError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar contexto eleitoral"
            message={electionContextError.message}
            requestId={electionContextError.requestId}
            onRetry={() => void electionContextQuery.refetch()}
          />
        ) : electionContext && electionContext.items.length > 0 ? (
          <div className="kpi-grid" style={{ marginTop: "0.85rem" }}>
            <StrategicIndexCard
              label="Ano eleitoral"
              value={electionContext.year ? String(electionContext.year) : "-"}
              status="info"
              helper="referência nominal"
            />
            <StrategicIndexCard
              label="Cargo principal"
              value={formatOfficeLabel(electionContext.office)}
              status="info"
              helper={electionContext.election_round ? `${electionContext.election_round}o turno` : "turno único"}
            />
            <StrategicIndexCard
              label="Líder do recorte"
              value={formatCandidateLabel(leadingCandidate?.ballot_name ?? null, leadingCandidate?.candidate_name ?? null)}
              status="info"
              helper={formatPercent(leadingCandidate?.share_percent)}
            />
            <StrategicIndexCard
              label="Votos válidos"
              value={formatInteger(electionContext.total_votes)}
              status="info"
              helper={formatLevelLabel(electionContext.level)}
            />
          </div>
        ) : null}
        <div className="kpi-grid" style={{ marginTop: "0.85rem" }}>
          <StrategicIndexCard
            label="Itens"
            value={String(sortedItems.length)}
            status="info"
            helper="prioridades no recorte aplicado"
          />
          <StrategicIndexCard
            label="Críticos"
            value={String(summaryByStatus.critical)}
            status="critical"
            helper="ação imediata"
          />
          <StrategicIndexCard
            label="Atenção"
            value={String(summaryByStatus.attention)}
            status="attention"
            helper="monitoramento"
          />
          <StrategicIndexCard
            label="Estáveis"
            value={String(summaryByStatus.stable)}
            status="stable"
            helper="sob controle"
          />
        </div>
      </Panel>

      <Panel title="Lista priorizada" subtitle="Itens com justificativa e evidência para decisão">
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportCsv} disabled={sortedItems.length === 0}>
            Exportar CSV
          </button>
          <label>
            Itens por p?gina
            <select
              aria-label="Itens por página"
              value={pageSize}
              onChange={(event) => setPageSize(event.target.value)}
            >
              <option value="12">12</option>
              <option value="24">24</option>
              <option value="48">48</option>
            </select>
          </label>
        </div>
        <p className="priority-summary">
          Mostrando {visibleItems.length} de {sortedItems.length} prioridade(s) filtradas ({priorities!.items.length} no retorno bruto).
          {activeFilterSummary.length > 0 ? ` Filtros ativos: ${activeFilterSummary.join(" | ")}.` : ""}
        </p>
        {sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada para os filtros aplicados." />
        ) : (
          <div className="priority-card-grid" role="list" aria-label="Lista de prioridades">
            {visibleItems.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
        {sortedItems.length > normalizedPageSize ? (
          <div className="pagination-row" aria-label="Paginação de prioridades">
            <button
              type="button"
              className="button-secondary"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage <= 1}
            >
              Anterior
            </button>
            <span>
              Página {currentPage} de {totalPages}
            </span>
            <button
              type="button"
              className="button-secondary"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={currentPage >= totalPages}
            >
              Próxima
            </button>
          </div>
        ) : null}
      </Panel>
    </main>
  );
}
