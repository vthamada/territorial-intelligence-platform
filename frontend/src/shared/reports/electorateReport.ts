import type {
  ElectorateCandidateTerritoriesResponse,
  ElectorateElectionContextResponse,
  ElectorateHistoryResponse,
  ElectoratePollingPlacesResponse,
  ElectorateSummaryResponse,
} from "../api/types";
import { formatDecimal, formatInteger } from "../ui/presentation";

export type ElectorateReportSection =
  | "summary"
  | "history"
  | "election_context"
  | "candidate_territories"
  | "polling_places"
  | "composition";

export type ElectorateReportFormat = "html" | "pdf";

type BreakdownItem = {
  label: string;
  voters: number;
  share_percent: number;
};

export type BuildElectorateReportInput = {
  generatedAt: Date;
  year: number | null;
  metricLabel: string;
  officeLabel: string;
  electionTypeLabel: string;
  electionRoundLabel: string;
  candidateLabel: string | null;
  sections: ElectorateReportSection[];
  summary: ElectorateSummaryResponse;
  summaryTurnout: number | null;
  summaryTurnoutRate: number | null;
  summaryAbstentionRate: number | null;
  summaryBlankRate: number | null;
  summaryNullRate: number | null;
  history: ElectorateHistoryResponse;
  electionContext: ElectorateElectionContextResponse | null;
  candidateTerritories: ElectorateCandidateTerritoriesResponse | null;
  pollingPlaces: ElectoratePollingPlacesResponse;
  ageBreakdown: BreakdownItem[];
};

function escapeHtml(value: string) {
  return value
    .split("&").join("&amp;")
    .split("<").join("&lt;")
    .split(">").join("&gt;")
    .split('"').join("&quot;")
    .split("'").join("&#39;");
}

export function sanitizeFilePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "relatorio";
}

function formatPercent(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${formatDecimal(value)}%`;
}

function formatMetricValue(metric: ElectoratePollingPlacesResponse["metric"], value: number | null) {
  if (value === null) {
    return "-";
  }
  if (metric === "voters" || metric === "turnout") {
    return formatInteger(value);
  }
  return formatPercent(value);
}

function renderTable(headers: string[], rows: string[][], emptyLabel: string) {
  const body =
    rows.length > 0
      ? rows
          .map(
            (row) => `
          <tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>
        `,
          )
          .join("")
      : `<tr><td colspan="${headers.length}">${escapeHtml(emptyLabel)}</td></tr>`;

  return `
    <table>
      <thead>
        <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  `;
}

function renderSection(title: string, subtitle: string, content: string) {
  return `
    <section class="report-section">
      <div class="report-section-header">
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(subtitle)}</p>
      </div>
      ${content}
    </section>
  `;
}

function renderSummarySection(input: BuildElectorateReportInput) {
  const cards = [
    ["Ano", input.summary.year === null ? "-" : String(input.summary.year)],
    ["Total de eleitores", formatInteger(input.summary.total_voters)],
    ["Comparecimento", input.summaryTurnout === null ? "-" : formatInteger(input.summaryTurnout)],
    ["Taxa de comparecimento", formatPercent(input.summaryTurnoutRate)],
    ["Taxa de abstenção", formatPercent(input.summaryAbstentionRate)],
    ["Brancos", formatPercent(input.summaryBlankRate)],
    ["Nulos", formatPercent(input.summaryNullRate)],
  ];

  return renderSection(
    "Resumo executivo",
    "Volume eleitoral e comportamento de participação",
    `
      <div class="metric-grid">
        ${cards
          .map(
            ([label, value]) => `
          <article>
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </article>
        `,
          )
          .join("")}
      </div>
    `,
  );
}

function renderHistorySection(history: ElectorateHistoryResponse) {
  const rows = history.items.map((item) => [
    escapeHtml(String(item.year)),
    escapeHtml(formatInteger(item.total_voters)),
    escapeHtml(item.turnout === null ? "-" : formatInteger(item.turnout)),
    escapeHtml(formatPercent(item.turnout_rate)),
    escapeHtml(formatPercent(item.abstention_rate)),
    escapeHtml(formatPercent(item.blank_rate)),
    escapeHtml(formatPercent(item.null_rate)),
  ]);

  return renderSection(
    "Histórico eleitoral",
    "Evolução anual do eleitorado e das métricas de participação",
    renderTable(
      ["Ano", "Eleitores", "Comparecimento", "Taxa comparecimento", "Taxa abstenção", "Brancos", "Nulos"],
      rows,
      "Sem série histórica para o recorte.",
    ),
  );
}

function renderElectionContextSection(context: ElectorateElectionContextResponse | null) {
  if (!context || context.items.length === 0) {
    return renderSection(
      "Contexto da eleição",
      "Cargo principal e candidatos mais votados no recorte",
      `<p class="empty-note">Sem contexto nominal disponível para o recorte atual.</p>`,
    );
  }

  const summaryCards = [
    ["Ano eleitoral", context.year === null ? "-" : String(context.year)],
    ["Tipo da eleição", context.election_type ?? "-"],
    ["Cargo em exibição", context.office ?? "-"],
    ["Turno", context.election_round ? `${context.election_round}º turno` : "-"],
    ["Votos válidos no recorte", formatInteger(context.total_votes)],
  ];
  const rows = context.items.map((item) => [
    escapeHtml(item.ballot_name || item.candidate_name),
    escapeHtml(item.candidate_number),
    escapeHtml(item.party_abbr || item.party_name || "-"),
    escapeHtml(formatInteger(item.votes)),
    escapeHtml(formatPercent(item.share_percent)),
  ]);

  return renderSection(
    "Contexto da eleição",
    "Cargo principal, turno e candidatos mais votados",
    `
      <div class="metric-grid">
        ${summaryCards
          .map(
            ([label, value]) => `
          <article>
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </article>
        `,
          )
          .join("")}
      </div>
      ${renderTable(["Candidato", "Número", "Partido", "Votos", "% do recorte"], rows, "Sem candidatos para o recorte.")}
    `,
  );
}

function renderCandidateTerritoriesSection(
  candidateLabel: string | null,
  territories: ElectorateCandidateTerritoriesResponse | null,
) {
  if (!territories || territories.items.length === 0) {
    return renderSection(
      "Distribuição territorial do candidato",
      candidateLabel ? `${candidateLabel} por local de votação` : "Distribuição nominal do candidato selecionado",
      `<p class="empty-note">Sem distribuição territorial disponível para o candidato selecionado.</p>`,
    );
  }

  const rows = territories.items.map((item) => [
    escapeHtml(item.polling_place_name || item.territory_name),
    escapeHtml(item.district_name || "-"),
    escapeHtml(item.zone_codes.join(", ") || "-"),
    escapeHtml(`${formatInteger(item.section_count)} seções`),
    escapeHtml(item.sections.join(", ") || "-"),
    escapeHtml(formatInteger(item.votes)),
    escapeHtml(formatPercent(item.share_percent)),
  ]);

  return renderSection(
    "Distribuição territorial do candidato",
    candidateLabel ? `${candidateLabel} por local de votação` : "Distribuição nominal do candidato selecionado",
    renderTable(
      ["Local", "Distrito", "Zonas", "Seções com votos", "Lista de seções", "Votos", "% do candidato"],
      rows,
      "Sem distribuição territorial para o candidato selecionado.",
    ),
  );
}

function renderPollingPlacesSection(pollingPlaces: ElectoratePollingPlacesResponse, metricLabel: string) {
  const rows = pollingPlaces.items.map((item) => [
    escapeHtml(item.polling_place_name || item.territory_name),
    escapeHtml(item.district_name || "-"),
    escapeHtml(item.zone_codes.join(", ") || "-"),
    escapeHtml(`${formatInteger(item.section_count)} seções`),
    escapeHtml(item.sections.join(", ") || "-"),
    escapeHtml(formatInteger(item.voters_total)),
    escapeHtml(formatPercent(item.share_percent)),
    escapeHtml(formatMetricValue(pollingPlaces.metric, item.value)),
  ]);

  return renderSection(
    "Ranking de locais de votação",
    `${metricLabel} por local de votação`,
    renderTable(
      ["Local", "Distrito", "Zonas", "Seções", "Lista de seções", "Eleitores", "% do município", "Indicador"],
      rows,
      "Sem ranking de locais de votação para o recorte.",
    ),
  );
}

function renderCompositionSection(summary: ElectorateSummaryResponse, ageBreakdown: BreakdownItem[]) {
  const sexRows = summary.by_sex.map((item) => [
    escapeHtml("Sexo"),
    escapeHtml(item.label),
    escapeHtml(formatInteger(item.voters)),
    escapeHtml(formatPercent(item.share_percent)),
  ]);
  const ageRows = ageBreakdown.map((item) => [
    escapeHtml("Faixa etária"),
    escapeHtml(item.label),
    escapeHtml(formatInteger(item.voters)),
    escapeHtml(formatPercent(item.share_percent)),
  ]);
  const educationRows = summary.by_education.map((item) => [
    escapeHtml("Escolaridade"),
    escapeHtml(item.label),
    escapeHtml(formatInteger(item.voters)),
    escapeHtml(formatPercent(item.share_percent)),
  ]);

  return renderSection(
    "Composição do eleitorado",
    "Distribuição por sexo, faixa etária e escolaridade",
    renderTable(
      ["Grupo", "Categoria", "Eleitores", "Participação"],
      [...sexRows, ...ageRows, ...educationRows],
      "Sem composição do eleitorado para o recorte.",
    ),
  );
}

export function buildElectorateReportHtml(input: BuildElectorateReportInput) {
  const sections = input.sections
    .map((section) => {
      if (section === "summary") {
        return renderSummarySection(input);
      }
      if (section === "history") {
        return renderHistorySection(input.history);
      }
      if (section === "election_context") {
        return renderElectionContextSection(input.electionContext);
      }
      if (section === "candidate_territories") {
        return renderCandidateTerritoriesSection(input.candidateLabel, input.candidateTerritories);
      }
      if (section === "polling_places") {
        return renderPollingPlacesSection(input.pollingPlaces, input.metricLabel);
      }
      return renderCompositionSection(input.summary, input.ageBreakdown);
    })
    .join("");

  return `<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <title>Relatório Eleitoral - ${escapeHtml(String(input.year ?? "-"))}</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }
      h1, h2, h3 { margin: 0; }
      p { margin: 0; }
      table { width: 100%; border-collapse: collapse; margin-top: 12px; }
      th, td { border: 1px solid #d1d5db; padding: 8px; font-size: 12px; text-align: left; vertical-align: top; }
      th { background: #f3f4f6; text-transform: uppercase; font-size: 11px; letter-spacing: 0.03em; }
      .report-header { display: grid; gap: 8px; margin-bottom: 18px; }
      .report-header p { color: #4b5563; font-size: 13px; }
      .report-section { display: grid; gap: 12px; margin-top: 22px; }
      .report-section-header { display: grid; gap: 4px; }
      .report-section-header p { color: #4b5563; font-size: 13px; }
      .metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
      .metric-grid article { border: 1px solid #d1d5db; border-radius: 8px; padding: 10px; display: grid; gap: 4px; }
      .metric-grid span { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
      .metric-grid strong { font-size: 18px; }
      .empty-note { color: #6b7280; font-size: 13px; }
      @media print {
        body { margin: 16px; }
        .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
    </style>
  </head>
  <body>
    <header class="report-header">
      <h1>Relatório eleitoral</h1>
      <p>Ano: ${escapeHtml(String(input.year ?? "-"))} | Cargo: ${escapeHtml(input.officeLabel)} | Tipo da eleição: ${escapeHtml(input.electionTypeLabel)} | Turno: ${escapeHtml(input.electionRoundLabel)}</p>
      <p>Gerado em ${escapeHtml(input.generatedAt.toLocaleString("pt-BR"))}</p>
    </header>
    ${sections}
  </body>
</html>`;
}
