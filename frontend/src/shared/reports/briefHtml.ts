import type { BriefGenerateResponse } from "../api/types";
import {
  formatLevelLabel,
  formatStatusLabel,
  formatValueWithUnit,
  humanizeDatasetSource,
} from "../ui/presentation";
import { getQgDomainLabel } from "../../modules/qg/domainCatalog";

function escapeHtml(value: string) {
  return value
    .split("&").join("&amp;")
    .split("<").join("&lt;")
    .split(">").join("&gt;")
    .split('"').join("&quot;")
    .split("'").join("&#39;");
}

export function sanitizeFilePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "brief";
}

function getElectorateDomainLabel(domain: string) {
  if (domain === "eleitorado_contexto") {
    return "Contexto eleitoral";
  }
  if (domain === "local_votacao") {
    return "Local de votação";
  }
  if (domain === "voto_nominal_local") {
    return "Voto nominal";
  }
  return domain;
}

export function buildBriefHtml(brief: BriefGenerateResponse) {
  const summaryItems = brief.summary_lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  const actionItems = brief.recommended_actions.map((line) => `<li>${escapeHtml(line)}</li>`).join("");

  const headers =
    brief.report_type === "electorate"
      ? ["Território", "Categoria", "Item", "Valor", "Participação", "Fonte", "Referência"]
      : ["Território", "Domínio", "Indicador", "Valor", "Score", "Status", "Fonte", "Período"];

  const evidenceRows = brief.evidences
    .map((item) => {
      if (brief.report_type === "electorate") {
        return `
          <tr>
            <td>${escapeHtml(item.territory_name)}</td>
            <td>${escapeHtml(getElectorateDomainLabel(item.domain))}</td>
            <td>${escapeHtml(item.indicator_name)}</td>
            <td>${escapeHtml(formatValueWithUnit(item.value, item.unit))}</td>
            <td>${escapeHtml(formatValueWithUnit(item.score, "%"))}</td>
            <td>${escapeHtml(humanizeDatasetSource(item.source, item.dataset))}</td>
            <td>${escapeHtml(item.reference_period)}</td>
          </tr>
        `;
      }
      return `
        <tr>
          <td>${escapeHtml(item.territory_name)}</td>
          <td>${escapeHtml(getQgDomainLabel(item.domain))}</td>
          <td>${escapeHtml(item.indicator_name)}</td>
          <td>${escapeHtml(formatValueWithUnit(item.value, item.unit))}</td>
          <td>${escapeHtml(formatValueWithUnit(item.score, null))}</td>
          <td>${escapeHtml(formatStatusLabel(item.status))}</td>
          <td>${escapeHtml(humanizeDatasetSource(item.source, item.dataset))}</td>
          <td>${escapeHtml(item.reference_period)}</td>
        </tr>
      `;
    })
    .join("");

  const evidenceColumnCount = headers.length;

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
      th, td { border: 1px solid #d1d5db; padding: 6px 8px; font-size: 13px; text-align: left; vertical-align: top; }
      th { background: #f3f4f6; text-transform: uppercase; font-size: 12px; letter-spacing: 0.03em; }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(brief.title)}</h1>
    <p class="meta">Gerado em: ${escapeHtml(brief.generated_at)}</p>
    <p class="meta">Período: ${escapeHtml(brief.period ?? "-")} | Nível: ${escapeHtml(formatLevelLabel(brief.level))} | Domínio: ${escapeHtml(brief.report_type === "electorate" ? "Eleitorado" : getQgDomainLabel(brief.domain))}</p>

    <h2>Resumo executivo</h2>
    <ul>${summaryItems}</ul>

    <h2>Ações recomendadas</h2>
    <ul>${actionItems}</ul>

    <h2>Evidências</h2>
    <table>
      <thead>
        <tr>${headers.map((label) => `<th>${escapeHtml(label)}</th>`).join("")}</tr>
      </thead>
      <tbody>${evidenceRows || `<tr><td colspan="${evidenceColumnCount}">Sem evidências para os filtros aplicados.</td></tr>`}</tbody>
    </table>
  </body>
</html>`;
}
