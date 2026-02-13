import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getPriorityList } from "../../../shared/api/qg";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { formatLevelLabel } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

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

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedLevel(level);
    setAppliedDomain(domain);
    setAppliedOnlyCritical(onlyCritical);
    setAppliedSortBy(sortBy);
    setAppliedLimit(limit);
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
  const activeFilterSummary = useMemo(() => {
    const tokens: string[] = [];
    if (appliedPeriod) tokens.push(`Periodo ${appliedPeriod}`);
    if (appliedDomain) tokens.push(`Dominio ${getQgDomainLabel(appliedDomain)}`);
    if (appliedOnlyCritical) tokens.push("Somente criticos");
    if (appliedLevel) tokens.push(`Nivel ${formatLevelLabel(appliedLevel)}`);
    return tokens;
  }, [appliedDomain, appliedLevel, appliedOnlyCritical, appliedPeriod]);

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
      <Panel title="Prioridades estrategicas" subtitle="Ranking territorial por criticidade e evidencia">
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
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
              <option value="district">{formatLevelLabel("district")}</option>
              <option value="census_sector">{formatLevelLabel("census_sector")}</option>
              <option value="electoral_zone">{formatLevelLabel("electoral_zone")}</option>
              <option value="electoral_section">{formatLevelLabel("electoral_section")}</option>
            </select>
          </label>
          <label>
            Dominio
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
            Somente criticos
            <select value={String(onlyCritical)} onChange={(event) => setOnlyCritical(event.target.value === "true")}>
              <option value="false">Nao</option>
              <option value="true">Sim</option>
            </select>
          </label>
          <label>
            Ordenar por
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as PrioritySort)}>
              <option value="criticality_desc">criticidade (maior score)</option>
              <option value="criticality_asc">criticidade (menor score)</option>
              <option value="trend_desc">tendencia (pior primeiro)</option>
              <option value="territory_asc">territorio (A-Z)</option>
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
      </Panel>

      <Panel title="Lista priorizada" subtitle="Itens com justificativa e evidencia para decisao">
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportCsv} disabled={sortedItems.length === 0}>
            Exportar CSV
          </button>
        </div>
        <p className="priority-summary">
          Mostrando {sortedItems.length} de {priorities!.items.length} prioridade(s).
          {activeFilterSummary.length > 0 ? ` Filtros ativos: ${activeFilterSummary.join(" | ")}.` : ""}
        </p>
        {sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada para os filtros aplicados." />
        ) : (
          <div className="priority-card-grid" role="list" aria-label="Lista de prioridades">
            {sortedItems.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
      </Panel>
    </main>
  );
}
