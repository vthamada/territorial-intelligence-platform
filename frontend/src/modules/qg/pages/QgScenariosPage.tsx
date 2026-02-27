import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getTerritories } from "../../../shared/api/domain";
import { formatApiError } from "../../../shared/api/http";
import { postScenarioSimulate } from "../../../shared/api/qg";
import { getQgDomainLabel, normalizeQgDomain, QG_DOMAIN_OPTIONS } from "../domainCatalog";
import { usePersistedFormState } from "../../../shared/hooks/usePersistedFormState";
import { CollapsiblePanel } from "../../../shared/ui/CollapsiblePanel";
import { Panel } from "../../../shared/ui/Panel";
import { formatDecimal, formatInteger, formatLevelLabel, formatStatusLabel, toNumber } from "../../../shared/ui/presentation";
import { SourceFreshnessBadge } from "../../../shared/ui/SourceFreshnessBadge";
import { StateBlock } from "../../../shared/ui/StateBlock";
import { StrategicIndexCard } from "../../../shared/ui/StrategicIndexCard";

type ScenarioFormSnapshot = {
  territoryId: string;
  period: string;
  level: string;
  domain: string;
  indicatorCode: string;
  adjustmentPercent: string;
};

function normalizeNumber(value: unknown, fallback = 0): number {
  const numeric = toNumber(value);
  return numeric === null ? fallback : numeric;
}

function formatSigned(value: unknown) {
  const parsed = normalizeNumber(value);
  if (parsed === 0) {
    return formatDecimal(0);
  }
  if (parsed > 0) {
    return `+${formatDecimal(parsed)}`;
  }
  return `-${formatDecimal(Math.abs(parsed))}`;
}

function formatSignedInteger(value: unknown) {
  const rounded = Math.trunc(normalizeNumber(value));
  if (rounded === 0) {
    return "0";
  }
  if (rounded > 0) {
    return `+${formatInteger(rounded)}`;
  }
  return `-${formatInteger(Math.abs(rounded))}`;
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
  const normalizedInitialLevel = searchParams.get("level") === "municipality" ? "municipality" : "";

  const [formValues, setFormField] = usePersistedFormState(
    "scenarios",
    {
      territoryId: "3121605",
      period: "2025",
      level: "municipality",
      domain: "",
      indicatorCode: "",
      adjustmentPercent: "10",
    },
    {
      territoryId: searchParams.get("territory_id") || "",
      period: searchParams.get("period") || "",
      level: normalizedInitialLevel,
      domain: searchParams.get("domain") || "",
      indicatorCode: searchParams.get("indicator_code") || "",
    }
  );

  const territoryId = formValues.territoryId;
  const period = formValues.period;
  const level = "municipality";
  const domain = normalizeQgDomain(formValues.domain);
  const indicatorCode = formValues.indicatorCode;
  const adjustmentPercent = formValues.adjustmentPercent;

  const setTerritoryId = (v: string) => setFormField("territoryId", v);
  const setPeriod = (v: string) => setFormField("period", v);
  const setLevel = (v: string) => setFormField("level", v);
  const setDomain = (v: string) => setFormField("domain", v);
  const setIndicatorCode = (v: string) => setFormField("indicatorCode", v);
  const setAdjustmentPercent = (v: string) => setFormField("adjustmentPercent", v);

  const [lastSubmittedSnapshot, setLastSubmittedSnapshot] = useState<ScenarioFormSnapshot | null>(null);
  const [lastSubmittedIndicatorCode, setLastSubmittedIndicatorCode] = useState<string>("");

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

  useEffect(() => {
    if (formValues.level !== "municipality") {
      setLevel("municipality");
    }
  }, [formValues.level, setLevel]);

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
    setLastSubmittedSnapshot({
      territoryId,
      period: period.trim(),
      level,
      domain: domain.trim(),
      indicatorCode: indicatorCode.trim(),
      adjustmentPercent: adjustmentPercent.trim(),
    });
    setLastSubmittedIndicatorCode(indicatorCode.trim());
  }

  function clearForm() {
    setTerritoryId(territoryOptions[0]?.territory_id ?? "3121605");
    setPeriod("2025");
    setLevel("municipality");
    setDomain("");
    setIndicatorCode("");
    setAdjustmentPercent("10");
    setLastSubmittedSnapshot(null);
    setLastSubmittedIndicatorCode("");
    simulationMutation.reset();
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
  const hasFormChangesAfterSimulation =
    Boolean(simulation && lastSubmittedSnapshot) &&
    (lastSubmittedSnapshot?.territoryId !== territoryId ||
      lastSubmittedSnapshot?.period !== period.trim() ||
      lastSubmittedSnapshot?.level !== level ||
      lastSubmittedSnapshot?.domain !== domain.trim() ||
      lastSubmittedSnapshot?.indicatorCode !== indicatorCode.trim() ||
      lastSubmittedSnapshot?.adjustmentPercent !== adjustmentPercent.trim());

  return (
    <main className="page-grid">
      <Panel title="Cenarios estrategicos" subtitle="Simulacao simplificada de impacto no score territorial">
        <form
          className="filter-grid compact"
          onSubmit={(event) => {
            event.preventDefault();
            submitScenario();
          }}
        >
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
            Período
            <input value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="2025" />
          </label>
          <label>
            Nível
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="municipality">{formatLevelLabel("municipality")}</option>
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
            Indicador (opcional)
            <input value={indicatorCode} onChange={(event) => setIndicatorCode(event.target.value)} placeholder="Ex: DATASUS_APS_COBERTURA" />
          </label>
          <label>
            Percentual de ajuste
            <input
              type="number"
              step="0.01"
              value={adjustmentPercent}
              onChange={(event) => setAdjustmentPercent(event.target.value)}
              placeholder="10"
            />
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
          subtitle={`${getQgDomainLabel(simulation.domain)} | ${simulation.indicator_name}`}
        >
          {hasFormChangesAfterSimulation ? (
            <StateBlock
              tone="empty"
              title="Filtros alterados apos a simulacao"
              message="Os resultados abaixo refletem o último envio. Clique em Simular para atualizar com os filtros atuais."
            />
          ) : null}

          {lastSubmittedIndicatorCode && lastSubmittedIndicatorCode !== simulation.indicator_code ? (
            <StateBlock
              tone="empty"
              title="Indicador ajustado automaticamente"
              message={`O indicador informado nao foi encontrado no recorte. Resultado calculado com ${simulation.indicator_code}.`}
            />
          ) : null}

          <div className="kpi-grid">
            <StrategicIndexCard
              label="Score antes/depois"
              value={`${formatDecimal(normalizeNumber(simulation.base_score))} -> ${formatDecimal(normalizeNumber(simulation.simulated_score))}`}
              status={impactStatus(simulation.impact)}
            />
            <StrategicIndexCard
              label="Status antes/depois"
              value={`${formatStatusLabel(simulation.status_before)} -> ${formatStatusLabel(simulation.status_after)}`}
              status={impactStatus(simulation.impact)}
            />
            <StrategicIndexCard
              label="Variacao ranking"
              value={formatSignedInteger(simulation.rank_delta)}
              status={impactStatus(simulation.impact)}
              helper={`posicao ${simulation.base_rank}/${simulation.peer_count} -> ${simulation.simulated_rank}/${simulation.peer_count}`}
            />
            <StrategicIndexCard
              label="Impacto resumido"
              value={formatStatusLabel(simulation.impact)}
              status={impactStatus(simulation.impact)}
              helper={`delta de valor ${formatSigned(simulation.delta_value)}`}
            />
          </div>

          <CollapsiblePanel
            title="Analises detalhadas"
            subtitle="Leituras tecnicas de apoio ao resultado"
            defaultOpen={false}
            badgeCount={simulation.explanation.length}
          >
            <ul className="trend-list" aria-label="Detalhes do cenario simulado">
              {simulation.explanation.map((entry, index) => (
                <li key={`${simulation.indicator_code}-${index}`}>
                  <div>
                    <strong>Leitura {index + 1}</strong>
                    <p>{entry}</p>
                  </div>
                </li>
              ))}
            </ul>
          </CollapsiblePanel>

          <SourceFreshnessBadge metadata={simulation.metadata} />
        </Panel>
      ) : null}
    </main>
  );
}
