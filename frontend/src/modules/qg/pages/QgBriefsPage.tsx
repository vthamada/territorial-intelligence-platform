import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { postBriefGenerate } from "../../../shared/api/qg";
import { buildBriefHtml, sanitizeFilePart } from "../../../shared/reports/briefHtml";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { usePersistedFormState } from "../../../shared/hooks/usePersistedFormState";
import { Panel } from "../../../shared/ui/Panel";
import { formatLevelLabel, formatStatusLabel, formatValueWithUnit, humanizeDatasetSource } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

function normalizeLevel(value: string | null) {
  if (value === "district") {
    return "district";
  }
  return "municipality";
}

export function QgBriefsPage() {
  const [searchParams] = useSearchParams();

  const [formValues, setFormField] = usePersistedFormState(
    "briefs",
    {
      period: "2025",
      level: "municipality",
      territoryId: "",
      domain: "",
      limit: "20",
    },
    {
      period: searchParams.get("period") || "",
      level: searchParams.get("level") || "",
      territoryId: searchParams.get("territory_id") || "",
      domain: searchParams.get("domain") || "",
      limit: searchParams.get("limit") || "",
    }
  );

  const period = formValues.period;
  const level = normalizeLevel(formValues.level);
  const territoryId = formValues.territoryId;
  const domain = normalizeQgDomain(formValues.domain);
  const limit = formValues.limit;

  const setPeriod = (v: string) => setFormField("period", v);
  const setLevel = (v: string) => setFormField("level", v);
  const setTerritoryId = (v: string) => setFormField("territoryId", v);
  const setDomain = (v: string) => setFormField("domain", v);
  const setLimit = (v: string) => setFormField("limit", v);

  const [exportError, setExportError] = useState<string | null>(null);

  const territoriesQuery = useQuery({
    queryKey: ["territories", "brief-picker"],
    queryFn: () => getTerritories({ level: "municipality", page: 1, page_size: 200 }),
  });

  const territoryOptions = useMemo(() => territoriesQuery.data?.items ?? [], [territoriesQuery.data]);

  useEffect(() => {
    if (!territoryOptions.length) {
      return;
    }
    if (!territoryId) {
      setTerritoryId(territoryOptions[0].territory_id);
    }
  }, [territoryId, territoryOptions]);

  const briefMutation = useMutation({
    mutationFn: postBriefGenerate,
  });

  function submitBrief() {
    const parsedLimit = Number(limit);
    if (!Number.isFinite(parsedLimit)) {
      return;
    }

    briefMutation.mutate({
      period: period.trim() || undefined,
      level,
      territory_id: territoryId || undefined,
      domain: domain.trim() || undefined,
      limit: parsedLimit,
    });
  }

  function clearFilters() {
    setPeriod("2025");
    setLevel("municipality");
    setTerritoryId(territoryOptions[0]?.territory_id ?? "");
    setDomain("");
    setLimit("20");
  }

  function exportBriefHtml() {
    if (!brief) {
      return;
    }
    setExportError(null);
    const html = buildBriefHtml(brief);
    const fileName = `brief_${sanitizeFilePart(brief.title)}_${sanitizeFilePart(brief.period ?? "sem_periodo")}.html`;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }

  function printBrief() {
    if (!brief) {
      return;
    }
    setExportError(null);
    const popup = window.open("", "_blank", "noopener,noreferrer,width=980,height=820");
    if (!popup) {
      setExportError("Não foi possível abrir janela de impressao. Verifique bloqueio de pop-up.");
      return;
    }
    const html = buildBriefHtml(brief);
    popup.document.open();
    popup.document.write(html);
    popup.document.close();
    setTimeout(() => {
      popup.focus();
      popup.print();
    }, 200);
  }

  if (territoriesQuery.isPending) {
    return (
      <StateBlock
        tone="loading"
        title="Carregando briefs"
        message="Preparando seleção de territorios para gerar o brief executivo."
      />
    );
  }

  if (territoriesQuery.error) {
    const { message, requestId } = formatApiError(territoriesQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar briefs"
        message={message}
        requestId={requestId}
        onRetry={() => void territoriesQuery.refetch()}
      />
    );
  }

  const brief = briefMutation.data;

  return (
    <main className="page-grid">
      <Panel title="Briefs executivos" subtitle="Geracao de resumo acionavel com evidencias priorizadas">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            submitBrief();
          }}
        >
          <label>
            Período
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nível
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
              <option value="district">{formatLevelLabel("district")}</option>
            </select>
          </label>
          <label>
            Território
            <select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}>
              {territoryOptions.map((territory) => (
                <option key={territory.territory_id} value={territory.territory_id}>
                  {territory.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Domínio (opcional)
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
            Limite de evidencias
            <input value={limit} onChange={(event) => setLimit(event.target.value)} placeholder="20" />
          </label>
          <div className="filter-actions">
            <button type="submit" disabled={briefMutation.isPending}>
              Gerar brief
            </button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
      </Panel>

      {briefMutation.isPending ? (
        <StateBlock tone="loading" title="Gerando brief" message="Consolidando resumo e evidencias para decisao." />
      ) : null}

      {briefMutation.error ? (
        <StateBlock
          tone="error"
          title="Falha ao gerar brief"
          message={formatApiError(briefMutation.error).message}
          requestId={formatApiError(briefMutation.error).requestId}
          onRetry={submitBrief}
        />
      ) : null}

      {brief ? (
        <Panel title={brief.title} subtitle={`Gerado em ${brief.generated_at}`}>
          <div className="panel-actions-row">
            <button type="button" className="button-secondary" onClick={exportBriefHtml} aria-label="Exportar brief como HTML">
              Exportar HTML
            </button>
            <button type="button" className="button-secondary" onClick={printBrief} aria-label="Imprimir ou salvar como PDF">
              Imprimir / PDF
            </button>
          </div>
          {exportError ? <p className="brief-export-error">{exportError}</p> : null}

          <h3>Resumo executivo</h3>
          <ul className="trend-list" aria-label="Resumo executivo do brief">
            {brief.summary_lines.map((line, index) => (
              <li key={`summary-${index}`}>
                <div>
                  <strong>Ponto {index + 1}</strong>
                  <p>{line}</p>
                </div>
              </li>
            ))}
          </ul>

          <h3>Acoes recomendadas</h3>
          <ul className="priority-item-rationale">
            {brief.recommended_actions.map((line, index) => (
              <li key={`action-${index}`}>{line}</li>
            ))}
          </ul>

          <h3>Evidencias</h3>
          {brief.evidences.length === 0 ? (
            <StateBlock tone="empty" title="Sem evidencias" message="Nenhuma evidencia retornada para os filtros aplicados." />
          ) : (
            <div className="table-wrap">
              <table aria-label="Evidencias do brief">
                <thead>
                  <tr>
                    <th>Território</th>
                    <th>Domínio</th>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Fonte</th>
                    <th>Período</th>
                  </tr>
                </thead>
                <tbody>
                  {brief.evidences.map((item) => (
                    <tr key={`${item.territory_id}-${item.indicator_code}`}>
                      <td>{item.territory_name}</td>
                      <td>{getQgDomainLabel(item.domain)}</td>
                      <td>{item.indicator_name}</td>
                      <td>{formatValueWithUnit(item.value, item.unit)}</td>
                      <td>{formatValueWithUnit(item.score, null)}</td>
                      <td>{formatStatusLabel(item.status)}</td>
                      <td>
                        {humanizeDatasetSource(item.source, item.dataset)}
                      </td>
                      <td>{item.reference_period}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <SourceFreshnessBadge metadata={brief.metadata} />
        </Panel>
      ) : null}
    </main>
  );
}
