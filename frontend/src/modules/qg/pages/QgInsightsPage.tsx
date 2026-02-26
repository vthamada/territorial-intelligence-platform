import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { formatApiError } from "../../../shared/api/http";
import { getInsightsHighlights } from "../../../shared/api/qg";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { Panel } from "../../../shared/ui/Panel";
import { formatStatusLabel, humanizeDatasetSource } from "../../../shared/ui/presentation";
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
  const [pageSize, setPageSize] = useState("20");
  const [currentPage, setCurrentPage] = useState(1);

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
  const insights = insightsQuery.data;
  const insightItems = insights?.items ?? [];
  const normalizedPageSize = Math.max(1, Number(pageSize) || 20);
  const totalPages = Math.max(1, Math.ceil(insightItems.length / normalizedPageSize));
  const visibleItems = useMemo(() => {
    const start = (currentPage - 1) * normalizedPageSize;
    return insightItems.slice(start, start + normalizedPageSize);
  }, [currentPage, insightItems, normalizedPageSize]);
  const groupedVisibleItems = useMemo(() => {
    const groups = {
      critical: [] as typeof visibleItems,
      attention: [] as typeof visibleItems,
      info: [] as typeof visibleItems,
    };
    for (const item of visibleItems) {
      groups[item.severity].push(item);
    }
    return groups;
  }, [visibleItems]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [pageSize]);

  function applyFilters() {
    setAppliedPeriod(period);
    setAppliedDomain(domain);
    setAppliedSeverity(severity);
    setCurrentPage(1);
  }

  function clearFilters() {
    setPeriod("");
    setDomain("");
    setSeverity("");
    setAppliedPeriod("");
    setAppliedDomain("");
    setAppliedSeverity("");
    setPageSize("20");
    setCurrentPage(1);
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
  const insightsData = insights!;

  return (
    <main className="page-grid">
      <Panel title="Insights estrategicos" subtitle="Destaques priorizados para leitura executiva">
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
            Severidade
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="">Todas</option>
              <option value="critical">{formatStatusLabel("critical")}</option>
              <option value="attention">{formatStatusLabel("attention")}</option>
              <option value="info">{formatStatusLabel("info")}</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={insightsData.metadata} />
      </Panel>

      <Panel title="Lista de insights" subtitle="Narrativa curta com evidencias por item">
        <div className="panel-actions-row">
          <label>
            Itens por pagina
            <select
              aria-label="Itens por pagina"
              value={pageSize}
              onChange={(event) => setPageSize(event.target.value)}
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </label>
        </div>
        {insightItems.length === 0 ? (
          <StateBlock tone="empty" title="Sem insights" message="Nenhum insight encontrado para os filtros aplicados." />
        ) : (
          <>
            <CollapsiblePanel
              title={`Criticos (${groupedVisibleItems.critical.length})`}
              subtitle="Leituras de resposta imediata"
              defaultOpen={true}
            >
              {groupedVisibleItems.critical.length === 0 ? (
                <StateBlock tone="empty" title="Sem itens criticos" message="Nenhum insight critico na pagina atual." />
              ) : (
                <ul className="trend-list" aria-label="Insights criticos">
                  {groupedVisibleItems.critical.map((item) => (
                    <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                      </div>
                      <small>
                        {getQgDomainLabel(item.domain)} | {formatStatusLabel(item.severity)} |{" "}
                        {humanizeDatasetSource(item.evidence.source, item.evidence.dataset)}
                      </small>
                      <div className="panel-actions-row">
                        <Link className="inline-link" to={`/mapa?territory_id=${encodeURIComponent(item.territory_id)}`}>
                          Ver no mapa
                        </Link>
                        <Link
                          className="inline-link"
                          to={`/briefs?territory_id=${encodeURIComponent(item.territory_id)}&period=${encodeURIComponent(
                            item.evidence.reference_period,
                          )}&domain=${encodeURIComponent(item.domain)}`}
                        >
                          Adicionar ao brief
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CollapsiblePanel>
            <CollapsiblePanel
              title={`Atencao (${groupedVisibleItems.attention.length})`}
              subtitle="Itens para monitoramento proximo"
              defaultOpen={false}
            >
              {groupedVisibleItems.attention.length === 0 ? (
                <StateBlock tone="empty" title="Sem itens em atencao" message="Nenhum insight em atencao na pagina atual." />
              ) : (
                <ul className="trend-list" aria-label="Insights atencao">
                  {groupedVisibleItems.attention.map((item) => (
                    <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                      </div>
                      <small>
                        {getQgDomainLabel(item.domain)} | {formatStatusLabel(item.severity)} |{" "}
                        {humanizeDatasetSource(item.evidence.source, item.evidence.dataset)}
                      </small>
                      <div className="panel-actions-row">
                        <Link className="inline-link" to={`/mapa?territory_id=${encodeURIComponent(item.territory_id)}`}>
                          Ver no mapa
                        </Link>
                        <Link
                          className="inline-link"
                          to={`/briefs?territory_id=${encodeURIComponent(item.territory_id)}&period=${encodeURIComponent(
                            item.evidence.reference_period,
                          )}&domain=${encodeURIComponent(item.domain)}`}
                        >
                          Adicionar ao brief
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CollapsiblePanel>
            <CollapsiblePanel
              title={`Informativos (${groupedVisibleItems.info.length})`}
              subtitle="Itens sem criticidade imediata"
              defaultOpen={false}
            >
              {groupedVisibleItems.info.length === 0 ? (
                <StateBlock tone="empty" title="Sem itens informativos" message="Nenhum insight informativo na pagina atual." />
              ) : (
                <ul className="trend-list" aria-label="Insights informativos">
                  {groupedVisibleItems.info.map((item) => (
                    <li key={`${item.territory_id}-${item.evidence.indicator_code}-${item.severity}`}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.explanation[0] ?? "Sem explicacao."}</p>
                      </div>
                      <small>
                        {getQgDomainLabel(item.domain)} | {formatStatusLabel(item.severity)} |{" "}
                        {humanizeDatasetSource(item.evidence.source, item.evidence.dataset)}
                      </small>
                      <div className="panel-actions-row">
                        <Link className="inline-link" to={`/mapa?territory_id=${encodeURIComponent(item.territory_id)}`}>
                          Ver no mapa
                        </Link>
                        <Link
                          className="inline-link"
                          to={`/briefs?territory_id=${encodeURIComponent(item.territory_id)}&period=${encodeURIComponent(
                            item.evidence.reference_period,
                          )}&domain=${encodeURIComponent(item.domain)}`}
                        >
                          Adicionar ao brief
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CollapsiblePanel>
          </>
        )}
        {insightItems.length > normalizedPageSize ? (
          <div className="pagination-row" aria-label="Paginacao de insights">
            <button
              type="button"
              className="button-secondary"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage <= 1}
            >
              Anterior
            </button>
            <span>
              Pagina {currentPage} de {totalPages}
            </span>
            <button
              type="button"
              className="button-secondary"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={currentPage >= totalPages}
            >
              Proxima
            </button>
          </div>
        ) : null}
      </Panel>
    </main>
  );
}
