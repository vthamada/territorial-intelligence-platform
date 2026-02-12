import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatApiError } from "../../../shared/api/http";
import { getElectorateMap, getElectorateSummary } from "../../../shared/api/qg";
import type { ElectorateMapResponse } from "../../../shared/api/types";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatInteger, formatLevelLabel } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";

type ElectorateMetric = ElectorateMapResponse["metric"];

function formatPercent(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${formatDecimal(value)}%`;
}

function metricLabel(metric: ElectorateMetric) {
  if (metric === "voters") {
    return "Total de eleitores";
  }
  if (metric === "turnout") {
    return "Comparecimento";
  }
  if (metric === "abstention_rate") {
    return "Taxa de abstencao";
  }
  if (metric === "blank_rate") {
    return "Taxa de brancos";
  }
  return "Taxa de nulos";
}

function breakdownGroupLabel(group: "sex" | "age" | "education") {
  if (group === "sex") {
    return "sexo";
  }
  if (group === "age") {
    return "faixa etaria";
  }
  return "escolaridade";
}

export function ElectorateExecutivePage() {
  const [yearInput, setYearInput] = useState("");
  const [metric, setMetric] = useState<ElectorateMetric>("voters");
  const [appliedYear, setAppliedYear] = useState<number | undefined>(undefined);
  const [appliedMetric, setAppliedMetric] = useState<ElectorateMetric>("voters");

  const baseQuery = useMemo(
    () => ({
      level: "municipality",
      year: appliedYear
    }),
    [appliedYear]
  );

  const summaryQuery = useQuery({
    queryKey: ["qg", "electorate-summary", baseQuery],
    queryFn: () => getElectorateSummary(baseQuery)
  });

  const mapQuery = useQuery({
    queryKey: ["qg", "electorate-map", baseQuery, appliedMetric],
    queryFn: () => getElectorateMap({ ...baseQuery, metric: appliedMetric, include_geometry: false, limit: 500 })
  });

  const isLoading = summaryQuery.isPending || mapQuery.isPending;
  const firstError = summaryQuery.error ?? mapQuery.error;

  function applyFilters() {
    const parsedYear = yearInput.trim() ? Number(yearInput) : undefined;
    setAppliedYear(Number.isFinite(parsedYear) ? parsedYear : undefined);
    setAppliedMetric(metric);
  }

  function clearFilters() {
    setYearInput("");
    setMetric("voters");
    setAppliedYear(undefined);
    setAppliedMetric("voters");
  }

  if (isLoading) {
    return (
      <StateBlock tone="loading" title="Carregando eleitorado executivo" message="Consultando resumo e mapa do eleitorado." />
    );
  }

  if (firstError) {
    const { message, requestId } = formatApiError(firstError);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar eleitorado executivo"
        message={message}
        requestId={requestId}
        onRetry={() => {
          void summaryQuery.refetch();
          void mapQuery.refetch();
        }}
      />
    );
  }

  const summary = summaryQuery.data!;
  const map = mapQuery.data!;

  return (
    <div className="page-grid">
      <Panel title="Eleitorado e participacao" subtitle="Leitura institucional para apoio a decisao">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <label>
            Ano
            <input value={yearInput} onChange={(event) => setYearInput(event.target.value)} placeholder="2024" />
          </label>
          <label>
            Metrica do mapa
            <select value={metric} onChange={(event) => setMetric(event.target.value as ElectorateMetric)}>
              <option value="voters">{metricLabel("voters")}</option>
              <option value="turnout">{metricLabel("turnout")}</option>
              <option value="abstention_rate">{metricLabel("abstention_rate")}</option>
              <option value="blank_rate">{metricLabel("blank_rate")}</option>
              <option value="null_rate">{metricLabel("null_rate")}</option>
            </select>
          </label>
          <div className="filter-actions">
            <button type="submit">Aplicar filtros</button>
            <button type="button" className="button-secondary" onClick={clearFilters}>
              Limpar
            </button>
          </div>
        </form>
        <SourceFreshnessBadge metadata={summary.metadata} />
      </Panel>

      <Panel title="Resumo executivo" subtitle="Volume eleitoral e comportamento de participacao">
        <div className="kpi-grid">
          <article>
            <span>Ano</span>
            <strong>{summary.year ?? "-"}</strong>
          </article>
          <article>
            <span>Total eleitores</span>
            <strong>{formatInteger(summary.total_voters)}</strong>
          </article>
          <article>
            <span>Taxa comparecimento</span>
            <strong>{formatPercent(summary.turnout_rate)}</strong>
          </article>
          <article>
            <span>Taxa abstencao</span>
            <strong>{formatPercent(summary.abstention_rate)}</strong>
          </article>
          <article>
            <span>Brancos</span>
            <strong>{formatPercent(summary.blank_rate)}</strong>
          </article>
          <article>
            <span>Nulos</span>
            <strong>{formatPercent(summary.null_rate)}</strong>
          </article>
        </div>
      </Panel>

      <Panel title="Composicao do eleitorado" subtitle="Distribuicao por sexo, faixa etaria e escolaridade">
        {summary.by_sex.length === 0 && summary.by_age.length === 0 && summary.by_education.length === 0 ? (
          <StateBlock tone="empty" title="Sem composicao" message="Nao ha dados de composicao para o recorte atual." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Grupo</th>
                  <th>Categoria</th>
                  <th>Eleitores</th>
                  <th>Participacao</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_sex.map((item) => (
                  <tr key={`sex-${item.label}`}>
                    <td>{breakdownGroupLabel("sex")}</td>
                    <td>{item.label}</td>
                    <td>{formatInteger(item.voters)}</td>
                    <td>{formatPercent(item.share_percent)}</td>
                  </tr>
                ))}
                {summary.by_age.map((item) => (
                  <tr key={`age-${item.label}`}>
                    <td>{breakdownGroupLabel("age")}</td>
                    <td>{item.label}</td>
                    <td>{formatInteger(item.voters)}</td>
                    <td>{formatPercent(item.share_percent)}</td>
                  </tr>
                ))}
                {summary.by_education.map((item) => (
                  <tr key={`education-${item.label}`}>
                    <td>{breakdownGroupLabel("education")}</td>
                    <td>{item.label}</td>
                    <td>{formatInteger(item.voters)}</td>
                    <td>{formatPercent(item.share_percent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Mapa tabular por territorio" subtitle={`${metricLabel(map.metric)} por ${formatLevelLabel(map.level)}`}>
        {map.items.length === 0 ? (
          <StateBlock tone="empty" title="Sem mapa eleitoral" message="Nenhum territorio retornado para a metrica selecionada." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Territorio</th>
                  <th>Nivel</th>
                  <th>Ano</th>
                  <th>Metrica</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                {map.items.map((item) => (
                  <tr key={`${item.territory_id}-${item.metric}`}>
                    <td>{item.territory_name}</td>
                    <td>{formatLevelLabel(item.territory_level)}</td>
                    <td>{item.year ?? "-"}</td>
                    <td>{metricLabel(item.metric)}</td>
                    <td>
                      {item.value === null
                        ? "-"
                        : item.metric === "voters"
                          ? formatInteger(item.value)
                          : formatPercent(item.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
