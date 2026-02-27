import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getInsightsHighlights, getKpisOverview, getPriorityList, getPrioritySummary } from "../../../shared/api/qg";
import { useFilterStore } from "../../../shared/stores/filterStore";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { formatLevelLabel, formatStatusLabel, formatValueWithUnit, humanizeDatasetSource } from "../../../shared/ui/presentation";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import { getQgDomainLabel, QG_ONDA_BC_SPOTLIGHT } from "../domainCatalog";

type StrategicStatus = "critical" | "attention" | "stable" | "info";

function resolveStrategicScore(byStatus: Record<string, number>, totalItems: number) {
  if (totalItems <= 0) {
    return 0;
  }
  const critical = byStatus.critical ?? 0;
  const attention = byStatus.attention ?? 0;
  const stable = byStatus.stable ?? 0;
  const weighted = critical * 100 + attention * 60 + stable * 35;
  return Math.round((weighted / totalItems) * 10) / 10;
}

function resolveStrategicStatus(score: number): StrategicStatus {
  if (score >= 80) {
    return "critical";
  }
  if (score >= 50) {
    return "attention";
  }
  if (score > 0) {
    return "stable";
  }
  return "info";
}

function resolveStrategicTrend(byStatus: Record<string, number>): string {
  const critical = byStatus.critical ?? 0;
  const attention = byStatus.attention ?? 0;
  if (critical > 0) {
    return "Atencao persistente";
  }
  if (attention > 0) {
    return "Monitoramento ativo";
  }
  return "Cenario estavel";
}

function normalizeLevel(value: string) {
  if (value === "district" || value === "census_sector" || value === "electoral_zone" || value === "electoral_section") {
    return value;
  }
  return "municipality";
}

export function QgOverviewPage() {
  const globalFilters = useFilterStore();
  const [period, setPeriod] = useState(globalFilters.period || "2025");
  const [level, setLevel] = useState(normalizeLevel(globalFilters.level || "municipality"));
  const [appliedPeriod, setAppliedPeriod] = useState(globalFilters.period || "2025");
  const [appliedLevel, setAppliedLevel] = useState(normalizeLevel(globalFilters.level || "municipality"));

  const baseQuery = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel,
    }),
    [appliedLevel, appliedPeriod],
  );

  const kpiQuery = useQuery({
    queryKey: ["qg", "overview", "kpis", baseQuery],
    queryFn: () => getKpisOverview({ ...baseQuery, limit: 20 }),
  });
  const summaryQuery = useQuery({
    queryKey: ["qg", "overview", "priority-summary", baseQuery],
    queryFn: () => getPrioritySummary({ ...baseQuery, limit: 200 }),
  });
  const prioritiesPreviewQuery = useQuery({
    queryKey: ["qg", "overview", "priority-list", baseQuery],
    queryFn: () => getPriorityList({ ...baseQuery, limit: 5 }),
  });
  const highlightsQuery = useQuery({
    queryKey: ["qg", "overview", "insights", baseQuery],
    queryFn: () => getInsightsHighlights({ ...baseQuery, limit: 5 }),
  });

  const isLoading = kpiQuery.isPending || summaryQuery.isPending;
  const firstError = kpiQuery.error ?? summaryQuery.error;

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedLevel(level);
    globalFilters.setPeriod(period);
    globalFilters.setLevel(level);
  }

  function clearFilters() {
    setPeriod("2025");
    setLevel("municipality");
    setAppliedPeriod("2025");
    setAppliedLevel("municipality");
    globalFilters.applyDefaults();
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando painel"
        message="Consultando resumo executivo, prioridades e destaques."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar Home executiva"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void kpiQuery.refetch();
          void summaryQuery.refetch();
          void prioritiesPreviewQuery.refetch();
          void highlightsQuery.refetch();
        }}
      />
    );
  }

  const kpis = kpiQuery.data!;
  const summary = summaryQuery.data!;
  const prioritiesPreviewItems = prioritiesPreviewQuery.data?.items ?? [];
  const highlightsItems = highlightsQuery.data?.items ?? [];

  const prioritiesPreviewError = prioritiesPreviewQuery.error ? formatApiError(prioritiesPreviewQuery.error) : null;
  const highlightsError = highlightsQuery.error ? formatApiError(highlightsQuery.error) : null;

  const strategicScore = resolveStrategicScore(summary.by_status, summary.total_items);
  const strategicStatus = resolveStrategicStatus(strategicScore);
  const strategicTrend = resolveStrategicTrend(summary.by_status);

  return (
    <main className="page-grid">
      <Panel title="Painel de inteligencia territorial" subtitle="Leitura executiva pronta para decisao">
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
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>

        <div className="kpi-grid" style={{ marginTop: "0.85rem" }}>
          <StrategicIndexCard
            label="Score geral"
            value={strategicScore > 0 ? formatValueWithUnit(strategicScore, null) : "-"}
            status={strategicStatus}
            helper={strategicTrend}
          />
          <StrategicIndexCard
            label="Criticos"
            value={String(summary.by_status.critical ?? 0)}
            status="critical"
            helper="resposta imediata"
          />
          <StrategicIndexCard
            label="Atencao"
            value={String(summary.by_status.attention ?? 0)}
            status="attention"
            helper="monitoramento ativo"
          />
          <StrategicIndexCard
            label="Estaveis"
            value={String(summary.by_status.stable ?? 0)}
            status="stable"
            helper="sob controle"
          />
        </div>

        <div className="panel-actions-row">
          <Link className="inline-link" to="/mapa">
            Abrir mapa
          </Link>
          <Link className="inline-link" to="/prioridades">
            Ver prioridades
          </Link>
          <Link className="inline-link" to="/insights">
            Ver insights
          </Link>
        </div>

        <SourceFreshnessBadge metadata={summary.metadata} />
      </Panel>

      <Panel title="Top prioridades" subtitle="Itens com justificativa e acao imediata">
        {prioritiesPreviewQuery.isPending && !prioritiesPreviewQuery.data ? (
          <StateBlock tone="loading" title="Carregando top prioridades" message="Buscando os principais itens do recorte." />
        ) : prioritiesPreviewError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar top prioridades"
            message={prioritiesPreviewError.message}
            requestId={prioritiesPreviewError.requestId}
            onRetry={() => void prioritiesPreviewQuery.refetch()}
          />
        ) : prioritiesPreviewItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade para o recorte aplicado." />
        ) : (
          <div className="priority-card-grid">
            {prioritiesPreviewItems.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Destaques" subtitle="Narrativa curta orientada a decisao">
        {highlightsQuery.isPending && !highlightsQuery.data ? (
          <StateBlock tone="loading" title="Carregando destaques" message="Consolidando os principais insights do recorte." />
        ) : highlightsError ? (
          <StateBlock
            tone="error"
            title="Falha ao carregar destaques"
            message={highlightsError.message}
            requestId={highlightsError.requestId}
            onRetry={() => void highlightsQuery.refetch()}
          />
        ) : highlightsItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem destaques" message="Nenhum destaque encontrado para o recorte atual." />
        ) : (
          <>
            <ul className="trend-list" aria-label="Lista de destaques">
              {highlightsItems.map((item) => (
                <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                  </div>
                  <small>
                    {getQgDomainLabel(item.domain)} | {formatStatusLabel(item.severity)} |{" "}
                    {humanizeDatasetSource(item.evidence.source, item.evidence.dataset)}
                  </small>
                </li>
              ))}
            </ul>
            <div className="panel-actions-row">
              <Link className="inline-link" to="/insights">
                Ver mais insights
              </Link>
            </div>
          </>
        )}
      </Panel>

      <CollapsiblePanel
        title="KPIs executivos"
        subtitle="Indicadores agregados para consulta rapida"
        defaultOpen={false}
        badgeCount={kpis.items.length}
      >
        {kpis.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem KPIs" message="Nenhum KPI encontrado para os filtros aplicados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dominio</th>
                  <th>Indicador</th>
                  <th>Valor</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {kpis.items.map((item) => (
                  <tr key={`${item.domain}-${item.indicator_code}`}>
                    <td>{getQgDomainLabel(item.domain)}</td>
                    <td>{item.indicator_name}</td>
                    <td>{formatValueWithUnit(item.value, item.unit)}</td>
                    <td>{formatLevelLabel(item.territory_level)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>

      <CollapsiblePanel
        title="Dominios Onda B/C"
        subtitle="Atalhos para exploracao no mapa e prioridades"
        defaultOpen={false}
        badgeCount={QG_ONDA_BC_SPOTLIGHT.length}
      >
        <div className="table-wrap">
          <table aria-label="Dominios Onda B/C">
            <thead>
              <tr>
                <th>Dominio</th>
                <th>Fonte</th>
                <th>Itens no recorte</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {QG_ONDA_BC_SPOTLIGHT.map((item) => {
                const totalInDomain = summary.by_domain[item.domain] ?? 0;
                const prioritiesLink = `/prioridades?domain=${encodeURIComponent(item.domain)}&period=${encodeURIComponent(
                  appliedPeriod,
                )}&level=${encodeURIComponent(appliedLevel)}`;
                const mapLink = `/mapa?level=${encodeURIComponent(appliedLevel)}`;
                return (
                  <tr key={item.domain}>
                    <td>{item.label}</td>
                    <td>{item.source}</td>
                    <td>{totalInDomain}</td>
                    <td>
                      <Link className="inline-link" to={prioritiesLink}>
                        Abrir prioridades
                      </Link>{" "}
                      |{" "}
                      <Link className="inline-link" to={mapLink}>
                        Ver no mapa
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>
    </main>
  );
}
