# STRATEGIC_ENGINE_SPEC
Versão: 1.0.0
Data: 2026-02-13
Escopo: motor estratégico para priorização, insights, simulação e explicabilidade no QG.

## 1) Objetivo

Definir o comportamento do motor estratégico para:
1. priorizar territórios e indicadores com score auditavel.
2. gerar insights com justificativa objetiva.
3. simular impacto de variação e recalcular ranking.
4. manter consistencia entre API, frontend e documentacao.

## 2) Entradas do motor

Tabelas/fonte base:
1. `silver.fact_indicator`
2. `silver.dim_territory`
3. `silver.fact_electorate` (quando aplicavel)
4. `silver.fact_election_result` (quando aplicavel)

Filtros mínimos:
1. `period`
2. `level`
3. `domain` (opcional)
4. `territory_id` (quando aplicavel)

## 3) Modelo de score

## 3.1 Normalizacao

1. normalizacao principal: min-max por indicador no recorte.
2. clipping/winsorization para reduzir outliers extremos.
3. score final por indicador em escala 0-100.

## 3.2 Score composto por domínio

1. `domain_score = soma(weight_i * indicator_score_i) / soma(weight_i)`.
2. pesos por indicador definidos em configuração versionada.
3. indicador sem dado não entra na soma; cobertura e reportada.

## 3.3 Score global territorial

1. `global_score = soma(domain_weight_j * domain_score_j) / soma(domain_weight_j)`.
2. cobertura minima exigida para score global valido.
3. quando cobertura insuficiente, retornar `status=insufficient_data`.

## 4) Severidade

Classificação base (v1):
1. `critical` quando score >= 80.
2. `attention` quando score >= 60 e < 80.
3. `stable` quando score < 60.

Regra:
1. thresholds ficam em configuração versionada e auditavel.
2. frontend não deve hardcodar threshold.

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
2. evitar duplicacao de insight para mesmo indicador/território.
3. limitar quantidade por domínio para diversidade de leitura.

## 6.2 Payload mínimo

1. titulo curto.
2. explicacao objetiva.
3. severidade.
4. robustez/qualidade da evidencia.
5. link de navegacao para prioridade/mapa/perfil.

## 7) Cenarios

## 7.1 Simulação v1

1. entrada: variação percentual em indicador alvo.
2. recalculo de score/ranking no recorte selecionado.
3. saida: antes/depois + delta de score + delta de ranking + leitura textual.

## 7.2 Limites

1. simulação e deterministica e não probabilistica.
2. sem inferencia causal forte no v1.
3. sempre mostrar disclaimer de estimativa simplificada.

## 8) Configuração versionada

Arquivos previstos (proposta):
1. `configs/strategic_engine/indicator_weights.yml`
2. `configs/strategic_engine/domain_weights.yml`
3. `configs/strategic_engine/severity_thresholds.yml`
4. `configs/strategic_engine/insight_rules.yml`

Cada mudanca deve registrar:
1. versão.
2. data.
3. racional da alteracao.

## 9) Contratos de API impactados

1. `GET /v1/priority/list`
2. `GET /v1/priority/summary`
3. `GET /v1/insights/highlights`
4. `POST /v1/scenarios/simulate`
5. `GET /v1/kpis/overview` (score agregado)

## 10) Observabilidade e auditoria

Registrar por execução de motor:
1. versão de configuração usada.
2. filtros de recorte.
3. quantidade de itens avaliados.
4. estatisticas de cobertura.

## 11) Testes e qualidade

1. testes unitarios de normalizacao e score composto.
2. testes de contrato para payload de explainability.
3. testes de regressão para thresholds de severidade.
4. testes de simulação antes/depois com fixtures controladas.

## 12) Plano de implementação

## Fase SE-1 (CONCLUIDO)
1. ✅ Score min-max por indicador implementado em SQL (routes_qg.py CTEs `scored`).
2. ✅ Thresholds de severidade: `critical >= 80`, `attention >= 50`, `stable < 50`.
3. ✅ Funções auxiliares `_score_to_status()` e `_score_from_rank()` auditaveis.
4. ✅ `rationale` retornado em `/v1/priority/list` com justificativa textual.
5. ✅ `evidence` com source, dataset, reference_period, updated_at em payloads de prioridade.
6. ✅ `coverage_note` presente em todos os endpoints territoriais.
7. ✅ Simulação basica em `/v1/scenarios/simulate` com antes/depois/delta.
8. ✅ Briefs com evidencias estruturadas (`BriefEvidenceItem`).

## Fase SE-2
1. externalizar thresholds/pesos para `configs/strategic_engine/*.yml`.
2. incluir versão da configuração no payload de prioridade.
3. padronizar explainability em todos endpoints do motor.

## Fase SE-3
1. endurecer simulação com validações e testes de regressão.
2. publicar nota metodologica no `/admin` com versão ativa.

## 13) Critérios de aceite

### v1.0 (SE-1) — ATENDIDOS
1. ✅ Motor retorna score/severidade/rationale/evidence para `/v1/priority/list`.
2. ✅ Thresholds de score auditaveis em funções Python dedicadas.
3. ✅ Simulação retorna antes/depois e delta via `/v1/scenarios/simulate`.
4. ✅ Briefs com evidencias estruturadas.
5. ✅ Coverage note presente em payloads territoriais.
6. ✅ Testes de contrato cobrindo payloads de prioridade, insights e cenarios.

### v2.0 (SE-2/SE-3) — PENDENTES
1. Regras de peso/threshold externalizadas em YAML versionado.
2. Versão da configuração incluida no payload de resposta.
3. Testes de regressão para simulação com fixtures controladas.
4. Nota metodologica publicada no `/admin`.
