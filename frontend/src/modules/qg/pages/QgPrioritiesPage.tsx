import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatApiError } from "../../../shared/api/http";
import { getPriorityList } from "../../../shared/api/qg";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
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

export function QgPrioritiesPage() {
  const [period, setPeriod] = useState("");
  const [level, setLevel] = useState("municipality");
  const [domain, setDomain] = useState("");
  const [onlyCritical, setOnlyCritical] = useState(false);
  const [sortBy, setSortBy] = useState<PrioritySort>("criticality_desc");
  const [appliedPeriod, setAppliedPeriod] = useState("");
  const [appliedLevel, setAppliedLevel] = useState("municipality");
  const [appliedDomain, setAppliedDomain] = useState("");
  const [appliedOnlyCritical, setAppliedOnlyCritical] = useState(false);
  const [appliedSortBy, setAppliedSortBy] = useState<PrioritySort>("criticality_desc");

  const query = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel,
      domain: appliedDomain || undefined,
      limit: 100
    }),
    [appliedDomain, appliedLevel, appliedPeriod]
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
  }

  function clearFilters() {
    setPeriod("");
    setLevel("municipality");
    setDomain("");
    setOnlyCritical(false);
    setSortBy("criticality_desc");
    setAppliedPeriod("");
    setAppliedLevel("municipality");
    setAppliedDomain("");
    setAppliedOnlyCritical(false);
    setAppliedSortBy("criticality_desc");
  }

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

  const priorities = prioritiesQuery.data!;
  const filteredItems = appliedOnlyCritical ? priorities.items.filter((item) => item.status === "critical") : priorities.items;
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
    <div className="page-grid">
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
              <option value="municipality">municipality</option>
              <option value="district">district</option>
              <option value="census_sector">census_sector</option>
              <option value="electoral_zone">electoral_zone</option>
              <option value="electoral_section">electoral_section</option>
            </select>
          </label>
          <label>
            Dominio
            <input value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="saude" />
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
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={priorities.metadata} />
      </Panel>

      <Panel title="Lista priorizada" subtitle="Itens com justificativa e evidencia para decisao">
        <div className="panel-actions-row">
          <button type="button" className="button-secondary" onClick={exportCsv} disabled={sortedItems.length === 0}>
            Exportar CSV
          </button>
        </div>
        {sortedItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada para os filtros aplicados." />
        ) : (
          <div className="priority-card-grid">
            {sortedItems.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
