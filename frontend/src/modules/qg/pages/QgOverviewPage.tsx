import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getInsightsHighlights, getKpisOverview, getPriorityList, getPrioritySummary } from "../../../shared/api/qg";
import { QG_ONDA_BC_SPOTLIGHT } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { PriorityItemCard } from "../../../shared/ui/PriorityItemCard";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";
import { StateBlock } from "../../../shared/ui/StateBlock";

function formatValue(value: number, unit: string | null) {
  if (unit) {
    return `${value.toFixed(2)} ${unit}`;
  }
  return value.toFixed(2);
}

export function QgOverviewPage() {
  const [period, setPeriod] = useState("");
  const [level, setLevel] = useState("municipality");
  const [appliedPeriod, setAppliedPeriod] = useState("");
  const [appliedLevel, setAppliedLevel] = useState("municipality");

  const baseQuery = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      level: appliedLevel
    }),
    [appliedLevel, appliedPeriod]
  );

  const kpiQuery = useQuery({
    queryKey: ["qg", "kpis", baseQuery],
    queryFn: () => getKpisOverview({ ...baseQuery, limit: 20 })
  });
  const summaryQuery = useQuery({
    queryKey: ["qg", "priority-summary", baseQuery],
    queryFn: () => getPrioritySummary({ ...baseQuery, limit: 100 })
  });
  const prioritiesPreviewQuery = useQuery({
    queryKey: ["qg", "priority-preview", baseQuery],
    queryFn: () => getPriorityList({ ...baseQuery, limit: 5 })
  });
  const highlightsQuery = useQuery({
    queryKey: ["qg", "insights", baseQuery],
    queryFn: () => getInsightsHighlights({ ...baseQuery, limit: 5 })
  });

  const isLoading =
    kpiQuery.isPending || summaryQuery.isPending || prioritiesPreviewQuery.isPending || highlightsQuery.isPending;
  const firstError = kpiQuery.error ?? summaryQuery.error ?? prioritiesPreviewQuery.error ?? highlightsQuery.error;

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedLevel(level);
  }

  function clearFilters() {
    setPeriod("");
    setLevel("municipality");
    setAppliedPeriod("");
    setAppliedLevel("municipality");
  }

  if (isLoading) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando QG estrategico"
        message="Consultando KPIs, prioridades e destaques executivos."
      />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar QG estrategico"
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
  const prioritiesPreview = prioritiesPreviewQuery.data!;
  const highlights = highlightsQuery.data!;
  const topPriority = prioritiesPreview.items[0];
  const mostCriticalTerritory = topPriority?.territory_id;
  const mapQuickLink = topPriority
    ? `/mapa?metric=${encodeURIComponent(topPriority.indicator_code)}&period=${encodeURIComponent(
        topPriority.evidence.reference_period
      )}&territory_id=${encodeURIComponent(topPriority.territory_id)}`
    : "/mapa";
  const resolvedPeriod = appliedPeriod || kpis.period || "2025";
  const resolvedMapLevel = appliedLevel === "district" ? "distrito" : "municipio";

  return (
    <div className="page-grid">
      <Panel title="QG estrategico" subtitle="Diagnostico rapido e prioridades para decisao">
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
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={kpis.metadata} />
      </Panel>

      <Panel title="Situacao geral" subtitle="Resumo de criticidade e cobertura do recorte atual">
        <div className="kpi-grid">
          <StrategicIndexCard
            label="Total priorizado"
            value={String(summary.total_items)}
            status="info"
            helper="total de itens monitorados no recorte"
          />
          <StrategicIndexCard
            label="Criticos"
            value={String(summary.by_status.critical ?? 0)}
            status="critical"
            helper="prioridades de resposta imediata"
          />
          <StrategicIndexCard
            label="Atencao"
            value={String(summary.by_status.attention ?? 0)}
            status="attention"
            helper="itens de risco moderado"
          />
          <StrategicIndexCard
            label="Estavel"
            value={String(summary.by_status.stable ?? 0)}
            status="stable"
            helper="itens sob controle no periodo"
          />
          <StrategicIndexCard
            label="Dominios ativos"
            value={String(Object.keys(summary.by_domain).length)}
            status="info"
            helper="fontes com dados no periodo atual"
          />
        </div>
      </Panel>

      <Panel title="Acoes rapidas" subtitle="Atalhos para o fluxo de decisao executiva">
        <div className="quick-actions">
          <Link className="quick-action-link" to="/prioridades">
            Abrir prioridades
          </Link>
          <Link className="quick-action-link" to={mapQuickLink}>
            Ver no mapa
          </Link>
          {mostCriticalTerritory ? (
            <Link className="quick-action-link" to={`/territorio/${mostCriticalTerritory}`}>
              Abrir territorio critico
            </Link>
          ) : null}
        </div>
      </Panel>

      <Panel title="Dominios Onda B/C" subtitle="Atalhos para fontes novas com recorte aplicado">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Dominio</th>
                <th>Fonte</th>
                <th>Itens no recorte</th>
                <th>Metrica de mapa</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {QG_ONDA_BC_SPOTLIGHT.map((item) => {
                const totalInDomain = summary.by_domain[item.domain] ?? 0;
                const prioritiesLink = `/prioridades?domain=${encodeURIComponent(item.domain)}&period=${encodeURIComponent(
                  resolvedPeriod
                )}&level=${encodeURIComponent(appliedLevel)}`;
                const mapLink = `/mapa?metric=${encodeURIComponent(item.defaultMetric)}&period=${encodeURIComponent(
                  resolvedPeriod
                )}&level=${encodeURIComponent(resolvedMapLevel)}`;

                return (
                  <tr key={item.domain}>
                    <td>{item.label}</td>
                    <td>{item.source}</td>
                    <td>{totalInDomain}</td>
                    <td>{item.defaultMetric}</td>
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
      </Panel>

      <Panel title="Top prioridades" subtitle="Previa dos itens mais criticos do recorte atual">
        {prioritiesPreview.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem prioridades" message="Nenhuma prioridade encontrada para os filtros aplicados." />
        ) : (
          <div className="priority-card-grid">
            {prioritiesPreview.items.map((item) => (
              <PriorityItemCard key={`${item.territory_id}-${item.indicator_code}`} item={item} />
            ))}
          </div>
        )}
        <SourceFreshnessBadge metadata={prioritiesPreview.metadata} />
      </Panel>

      <Panel title="KPIs executivos" subtitle="Indicadores agregados para leitura rapida">
        {kpis.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem KPIs" message="Nenhum KPI encontrado para os filtros aplicados." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dominio</th>
                  <th>Fonte</th>
                  <th>Codigo</th>
                  <th>Indicador</th>
                  <th>Valor</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {kpis.items.map((item) => (
                  <tr key={`${item.domain}-${item.indicator_code}`}>
                    <td>{item.domain}</td>
                    <td>{item.source ?? "-"}</td>
                    <td>{item.indicator_code}</td>
                    <td>{item.indicator_name}</td>
                    <td>{formatValue(item.value, item.unit)}</td>
                    <td>{item.territory_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Destaques" subtitle="Principais insights para acao imediata">
        {highlights.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem destaques" message="Nao ha insights para o recorte atual." />
        ) : (
          <ul className="trend-list">
            {highlights.items.map((item) => (
              <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                </div>
                <small>
                  severidade: {item.severity} | robustez: {item.robustness}
                </small>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
