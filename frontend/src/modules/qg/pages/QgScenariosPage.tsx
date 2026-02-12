import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { postScenarioSimulate } from "../../../shared/api/qg";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { Panel } from "../../../shared/ui/Panel";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";

function formatSigned(value: number) {
  if (value > 0) {
    return `+${value.toFixed(2)}`;
  }
  return value.toFixed(2);
}

function impactStatus(impact: string): "critical" | "attention" | "stable" | "info" {
  if (impact === "worsened") {
    return "critical";
  }
  if (impact === "improved") {
    return "stable";
  }
  if (impact === "unchanged") {
    return "attention";
  }
  return "info";
}

export function QgScenariosPage() {
  const [searchParams] = useSearchParams();
  const [territoryId, setTerritoryId] = useState(searchParams.get("territory_id") || "3121605");
  const [period, setPeriod] = useState(searchParams.get("period") || "2025");
  const [level, setLevel] = useState(searchParams.get("level") === "district" ? "district" : "municipality");
  const [domain, setDomain] = useState(normalizeQgDomain(searchParams.get("domain")));
  const [indicatorCode, setIndicatorCode] = useState(searchParams.get("indicator_code") || "");
  const [adjustmentPercent, setAdjustmentPercent] = useState("10");

  const territoriesQuery = useQuery({
    queryKey: ["territories", "scenario-picker"],
    queryFn: () => getTerritories({ level: "municipality", page: 1, page_size: 200 }),
  });

  const territoryOptions = useMemo(() => territoriesQuery.data?.items ?? [], [territoriesQuery.data]);

  useEffect(() => {
    if (!territoryOptions.length) {
      return;
    }
    const territoryExists = territoryOptions.some((item) => item.territory_id === territoryId);
    if (!territoryExists) {
      setTerritoryId(territoryOptions[0].territory_id);
    }
  }, [territoryId, territoryOptions]);

  const simulationMutation = useMutation({
    mutationFn: postScenarioSimulate,
  });

  function submitScenario() {
    const parsedAdjustment = Number(adjustmentPercent);
    if (!Number.isFinite(parsedAdjustment)) {
      return;
    }

    simulationMutation.mutate({
      territory_id: territoryId,
      period: period.trim() || undefined,
      level,
      domain: domain.trim() || undefined,
      indicator_code: indicatorCode.trim() || undefined,
      adjustment_percent: parsedAdjustment,
    });
  }

  function clearForm() {
    setTerritoryId(territoryOptions[0]?.territory_id ?? "3121605");
    setPeriod("2025");
    setLevel("municipality");
    setDomain("");
    setIndicatorCode("");
    setAdjustmentPercent("10");
  }

  if (territoriesQuery.isPending) {
    return <StateBlock tone="loading" title="Carregando cenarios" message="Preparando lista de territorios para simulacao." />;
  }

  if (territoriesQuery.error) {
    const { message, requestId } = formatApiError(territoriesQuery.error);
    return (
      <StateBlock
        tone="error"
        title="Falha ao carregar cenarios"
        message={message}
        requestId={requestId}
        onRetry={() => void territoriesQuery.refetch()}
      />
    );
  }

  const simulation = simulationMutation.data;

  return (
    <div className="page-grid">
      <Panel title="Cenarios estrategicos" subtitle="Simulacao simplificada de impacto no score territorial">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            submitScenario();
          }}
        >
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
            Periodo
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nivel
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">municipality</option>
              <option value="district">district</option>
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
            Codigo do indicador (opcional)
            <input value={indicatorCode} onChange={(event) => setIndicatorCode(event.target.value)} placeholder="DATASUS_APS_COBERTURA" />
          </label>
          <label>
            Ajuste percentual
            <input value={adjustmentPercent} onChange={(event) => setAdjustmentPercent(event.target.value)} placeholder="10" />
          </label>
          <div className="filter-actions">
            <button type="submit" disabled={simulationMutation.isPending}>
              Simular
            </button>
            <button type="button" className="button-secondary" onClick={clearForm}>
              Limpar
            </button>
          </div>
        </form>
      </Panel>

      {simulationMutation.isPending ? (
        <StateBlock tone="loading" title="Executando simulacao" message="Calculando impacto estimado para o recorte informado." />
      ) : null}

      {simulationMutation.error ? (
        <StateBlock
          tone="error"
          title="Falha na simulacao"
          message={formatApiError(simulationMutation.error).message}
          requestId={formatApiError(simulationMutation.error).requestId}
          onRetry={submitScenario}
        />
      ) : null}

      {simulation ? (
        <Panel
          title={`Resultado: ${simulation.territory_name}`}
          subtitle={`${getQgDomainLabel(simulation.domain)} | ${simulation.indicator_code}`}
        >
          <div className="kpi-grid">
            <StrategicIndexCard label="Score base" value={simulation.base_score.toFixed(2)} status="info" />
            <StrategicIndexCard
              label="Score simulado"
              value={simulation.simulated_score.toFixed(2)}
              status={impactStatus(simulation.impact)}
            />
            <StrategicIndexCard
              label="Ranking antes"
              value={`${simulation.base_rank}/${simulation.peer_count}`}
              status="info"
            />
            <StrategicIndexCard
              label="Ranking apos"
              value={`${simulation.simulated_rank}/${simulation.peer_count}`}
              status={impactStatus(simulation.impact)}
            />
            <StrategicIndexCard
              label="Delta de ranking"
              value={formatSigned(simulation.rank_delta)}
              status={impactStatus(simulation.impact)}
              helper="valor positivo indica melhora de posicao"
            />
            <StrategicIndexCard label="Status antes" value={simulation.status_before} status="info" />
            <StrategicIndexCard label="Status apos" value={simulation.status_after} status={impactStatus(simulation.impact)} />
            <StrategicIndexCard
              label="Delta de valor"
              value={formatSigned(simulation.delta_value)}
              status={impactStatus(simulation.impact)}
            />
            <StrategicIndexCard
              label="Impacto"
              value={simulation.impact}
              status={impactStatus(simulation.impact)}
              helper="estimativa simplificada baseada em variacao percentual"
            />
          </div>

          <ul className="trend-list">
            {simulation.explanation.map((entry, index) => (
              <li key={`${simulation.indicator_code}-${index}`}>
                <div>
                  <strong>Leitura {index + 1}</strong>
                  <p>{entry}</p>
                </div>
              </li>
            ))}
          </ul>

          <SourceFreshnessBadge metadata={simulation.metadata} />
        </Panel>
      ) : null}
    </div>
  );
}
