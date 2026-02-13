# STRATEGIC_ENGINE_SPEC
Versao: 0.1.0
Data: 2026-02-13
Escopo: motor estrategico para priorizacao, insights, simulacao e explicabilidade no QG.

## 1) Objetivo

Definir o comportamento do motor estrategico para:
1. priorizar territorios e indicadores com score auditavel.
2. gerar insights com justificativa objetiva.
3. simular impacto de variacao e recalcular ranking.
4. manter consistencia entre API, frontend e documentacao.

## 2) Entradas do motor

Tabelas/fonte base:
1. `silver.fact_indicator`
2. `silver.dim_territory`
3. `silver.fact_electorate` (quando aplicavel)
4. `silver.fact_election_result` (quando aplicavel)

Filtros minimos:
1. `period`
2. `level`
3. `domain` (opcional)
4. `territory_id` (quando aplicavel)

## 3) Modelo de score

## 3.1 Normalizacao

1. normalizacao principal: min-max por indicador no recorte.
2. clipping/winsorization para reduzir outliers extremos.
3. score final por indicador em escala 0-100.

## 3.2 Score composto por dominio

1. `domain_score = soma(weight_i * indicator_score_i) / soma(weight_i)`.
2. pesos por indicador definidos em configuracao versionada.
3. indicador sem dado nao entra na soma; cobertura e reportada.

## 3.3 Score global territorial

1. `global_score = soma(domain_weight_j * domain_score_j) / soma(domain_weight_j)`.
2. cobertura minima exigida para score global valido.
3. quando cobertura insuficiente, retornar `status=insufficient_data`.

## 4) Severidade

Classificacao base (v1):
1. `critical` quando score >= 80.
2. `attention` quando score >= 60 e < 80.
3. `stable` quando score < 60.

Regra:
1. thresholds ficam em configuracao versionada e auditavel.
2. frontend nao deve hardcodar threshold.

## 5) Explainability (obrigatorio)

Todo item de prioridade deve retornar:
1. `score`.
2. `severity`.
3. `rationale` (lista curta de motivos).
4. `evidence` com `source`, `dataset`, `reference_period`, `updated_at`.
5. `coverage` (completude do recorte para o score).

## 6) Insights

## 6.1 Regras

1. selecionar top sinais por severidade, tendencia e impacto.
2. evitar duplicacao de insight para mesmo indicador/territorio.
3. limitar quantidade por dominio para diversidade de leitura.

## 6.2 Payload minimo

1. titulo curto.
2. explicacao objetiva.
3. severidade.
4. robustez/qualidade da evidencia.
5. link de navegacao para prioridade/mapa/perfil.

## 7) Cenarios

## 7.1 Simulacao v1

1. entrada: variacao percentual em indicador alvo.
2. recalculo de score/ranking no recorte selecionado.
3. saida: antes/depois + delta de score + delta de ranking + leitura textual.

## 7.2 Limites

1. simulacao e deterministica e nao probabilistica.
2. sem inferencia causal forte no v1.
3. sempre mostrar disclaimer de estimativa simplificada.

## 8) Configuracao versionada

Arquivos previstos (proposta):
1. `configs/strategic_engine/indicator_weights.yml`
2. `configs/strategic_engine/domain_weights.yml`
3. `configs/strategic_engine/severity_thresholds.yml`
4. `configs/strategic_engine/insight_rules.yml`

Cada mudanca deve registrar:
1. versao.
2. data.
3. racional da alteracao.

## 9) Contratos de API impactados

1. `GET /v1/priority/list`
2. `GET /v1/priority/summary`
3. `GET /v1/insights/highlights`
4. `POST /v1/scenarios/simulate`
5. `GET /v1/kpis/overview` (score agregado)

## 10) Observabilidade e auditoria

Registrar por execucao de motor:
1. versao de configuracao usada.
2. filtros de recorte.
3. quantidade de itens avaliados.
4. estatisticas de cobertura.

## 11) Testes e qualidade

1. testes unitarios de normalizacao e score composto.
2. testes de contrato para payload de explainability.
3. testes de regressao para thresholds de severidade.
4. testes de simulacao antes/depois com fixtures controladas.

## 12) Plano de implementacao

## Fase SE-1
1. externalizar thresholds/pesos para configuracao versionada.
2. incluir versao da configuracao no payload de prioridade.

## Fase SE-2
1. padronizar explainability em todos endpoints do motor.
2. consolidar regras de insight e cobertura minima.

## Fase SE-3
1. endurecer simulacao com validacoes e testes de regressao.
2. publicar nota metodologica no `/admin` com versao ativa.

## 13) Criterios de aceite

1. motor retorna score/severidade/rationale/evidence de forma consistente.
2. regras de peso/threshold sao versionadas e auditaveis.
3. simulacao retorna antes/depois e delta de ranking com testes aprovados.
4. divergencias entre frontend e backend sobre thresholds deixam de existir.
