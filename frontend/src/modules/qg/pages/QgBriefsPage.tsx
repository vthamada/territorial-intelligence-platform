import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { postBriefGenerate } from "../../../shared/api/qg";
import type { BriefGenerateResponse } from "../../../shared/api/types";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { formatLevelLabel, formatStatusLabel, formatValueWithUnit } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

function normalizeLevel(value: string | null) {
  if (value === "district") {
    return "district";
  }
  return "municipality";
}

function escapeHtml(value: string) {
  return value
    .split("&").join("&amp;")
    .split("<").join("&lt;")
    .split(">").join("&gt;")
    .split('"').join("&quot;")
    .split("'").join("&#39;");
}

function sanitizeFilePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "brief";
}

function buildBriefHtml(brief: BriefGenerateResponse) {
  const summaryItems = brief.summary_lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  const actionItems = brief.recommended_actions.map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  const evidenceRows = brief.evidences
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.territory_name)}</td>
          <td>${escapeHtml(getQgDomainLabel(item.domain))}</td>
          <td>${escapeHtml(item.indicator_name)}</td>
          <td>${escapeHtml(formatValueWithUnit(item.value, item.unit))}</td>
          <td>${escapeHtml(formatValueWithUnit(item.score, null))}</td>
          <td>${escapeHtml(formatStatusLabel(item.status))}</td>
          <td>${escapeHtml(`${item.source} / ${item.dataset}`)}</td>
          <td>${escapeHtml(item.reference_period)}</td>
        </tr>
      `
    )
    .join("");

  return `<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(brief.title)}</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }
      h1, h2, h3 { margin: 0 0 10px; }
      h2 { margin-top: 18px; }
      p { margin: 6px 0; }
      ul { margin: 6px 0 0 18px; }
      li { margin: 4px 0; }
      .meta { color: #4b5563; font-size: 13px; margin-bottom: 16px; }
      table { width: 100%; border-collapse: collapse; margin-top: 8px; }
      th, td { border: 1px solid #d1d5db; padding: 6px 8px; font-size: 13px; text-align: left; }
      th { background: #f3f4f6; text-transform: uppercase; font-size: 12px; letter-spacing: 0.03em; }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(brief.title)}</h1>
    <p class="meta">Brief ID: ${escapeHtml(brief.brief_id)} | Gerado em: ${escapeHtml(brief.generated_at)}</p>
    <p class="meta">Periodo: ${escapeHtml(brief.period ?? "-")} | Nivel: ${escapeHtml(formatLevelLabel(brief.level))} | Dominio: ${escapeHtml(getQgDomainLabel(brief.domain))}</p>

    <h2>Resumo executivo</h2>
    <ul>${summaryItems}</ul>

    <h2>Acoes recomendadas</h2>
    <ul>${actionItems}</ul>

    <h2>Evidencias</h2>
    <table>
      <thead>
        <tr>
          <th>Territorio</th>
          <th>Dominio</th>
          <th>Indicador</th>
          <th>Valor</th>
          <th>Score</th>
          <th>Status</th>
          <th>Fonte</th>
          <th>Periodo</th>
        </tr>
      </thead>
      <tbody>${evidenceRows}</tbody>
    </table>
  </body>
</html>`;
}

export function QgBriefsPage() {
  const [searchParams] = useSearchParams();
  const [period, setPeriod] = useState(searchParams.get("period") || "2025");
  const [level, setLevel] = useState(normalizeLevel(searchParams.get("level")));
  const [territoryId, setTerritoryId] = useState(searchParams.get("territory_id") || "");
  const [domain, setDomain] = useState(normalizeQgDomain(searchParams.get("domain")));
  const [limit, setLimit] = useState(searchParams.get("limit") || "20");
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
      setExportError("Nao foi possivel abrir janela de impressao. Verifique bloqueio de pop-up.");
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
        message="Preparando selecao de territorios para gerar o brief executivo."
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
    <div className="page-grid">
      <Panel title="Briefs executivos" subtitle="Geracao de resumo acionavel com evidencias priorizadas">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            submitBrief();
          }}
        >
          <label>
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nivel
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
              <option value="district">{formatLevelLabel("district")}</option>
            </select>
          </label>
          <label>
            Territorio
            <select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}>
              {territoryOptions.map((territory) => (
                <option key={territory.territory_id} value={territory.territory_id}>
                  {territory.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Dominio (opcional)
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
        <Panel title={brief.title} subtitle={`Brief ID: ${brief.brief_id}`}>
          <div className="panel-actions-row">
            <button type="button" className="button-secondary" onClick={exportBriefHtml}>
              Exportar HTML
            </button>
            <button type="button" className="button-secondary" onClick={printBrief}>
              Imprimir / PDF
            </button>
          </div>
          {exportError ? <p className="brief-export-error">{exportError}</p> : null}

          <h3>Resumo executivo</h3>
          <ul className="trend-list">
            {brief.summary_lines.map((line, index) => (
              <li key={`summary-${index}`}>
                <div>
                  <strong>Linha {index + 1}</strong>
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
              <table>
                <thead>
                  <tr>
                    <th>Territorio</th>
                    <th>Dominio</th>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Fonte</th>
                    <th>Periodo</th>
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
                        {item.source} / {item.dataset}
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
    </div>
  );
}
