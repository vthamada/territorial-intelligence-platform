import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getInsightsHighlights } from "../../../shared/api/qg";
import { normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

function normalizeSeverity(value: string | null) {
  if (value === "critical" || value === "attention" || value === "info") {
    return value;
  }
  return "";
}

export function QgInsightsPage() {
  const [searchParams] = useSearchParams();
  const initialPeriod = searchParams.get("period") || "";
  const initialDomain = normalizeQgDomain(searchParams.get("domain"));
  const initialSeverity = normalizeSeverity(searchParams.get("severity"));

  const [period, setPeriod] = useState(initialPeriod);
  const [domain, setDomain] = useState(initialDomain);
  const [severity, setSeverity] = useState(initialSeverity);
  const [appliedPeriod, setAppliedPeriod] = useState(initialPeriod);
  const [appliedDomain, setAppliedDomain] = useState(initialDomain);
  const [appliedSeverity, setAppliedSeverity] = useState(initialSeverity);

  const query = useMemo(
    () => ({
      period: appliedPeriod || undefined,
      domain: appliedDomain || undefined,
      severity: appliedSeverity || undefined,
      limit: 50
    }),
    [appliedDomain, appliedPeriod, appliedSeverity]
  );

  const insightsQuery = useQuery({
    queryKey: ["qg", "insights-page", query],
    queryFn: () => getInsightsHighlights(query)
  });

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedDomain(domain);
    setAppliedSeverity(severity);
  }

  function clearFilters() {
    setPeriod("");
    setDomain("");
    setSeverity("");
    setAppliedPeriod("");
    setAppliedDomain("");
    setAppliedSeverity("");
  }

  if (insightsQuery.isPending) {
    return <StateBlock tone="loading" title="Carregando insights" message="Consultando destaques por severidade e dominio." />;
  }

  if (insightsQuery.error) {
    const { message, requestId } = formatApiError(insightsQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar insights"
        message={message}
        requestId={requestId}
        onRetry={() => void insightsQuery.refetch()}
      />
    );
  }

  const insights = insightsQuery.data!;

  return (
    <div className="page-grid">
      <Panel title="Insights estrategicos" subtitle="Destaques priorizados para leitura executiva">
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
            Dominio
            <select value={domain} onChange={(event) => setDomain(event.target.value)}>
              <option value="">Todos</option>
              {QG_DOMAIN_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Severidade
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="">Todas</option>
              <option value="critical">critical</option>
              <option value="attention">attention</option>
              <option value="info">info</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={insights.metadata} />
      </Panel>

      <Panel title="Lista de insights" subtitle="Narrativa curta com evidencias por item">
        {insights.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem insights" message="Nenhum insight encontrado para os filtros aplicados." />
        ) : (
          <ul className="trend-list">
            {insights.items.map((item) => (
              <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                </div>
                <small>
                  {item.domain} | {item.severity} | evidencia: {item.evidence.source}/{item.evidence.dataset}
                </small>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
