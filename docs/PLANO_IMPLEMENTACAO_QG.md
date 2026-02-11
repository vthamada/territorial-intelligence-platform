# Plano Integrado de Implementacao (Backend + Frontend QG)

Data de referencia: 2026-02-11  
Status: ativo  
Escopo: plano executavel para fechar o QG estrategico com entregas verticalizadas.

## 1) Objetivo

Entregar um QG estrategico municipal para Diamantina/MG, com:

1. Diagnostico rapido da cidade (Home executiva).
2. Priorizacao territorial e por dominio (lista explicavel).
3. Analise espacial por mapa (coropletico com drill-down quando existir).
4. Perfil 360 por territorio (historico + comparacao + evidencias).
5. Camada institucional de eleitorado/participacao.
6. Camada tecnica separada para operacao de dados (`/admin`).

## 2) Decisoes fechadas para execucao

1. Fonte de verdade tecnica permanece em `CONTRATO.md`.
2. `docs/FRONTEND_SPEC.md` e documento de produto/implementacao frontend, nao substitui contrato tecnico.
3. Camada tecnica fica separada da experiencia principal (sem foco em auth nesta fase).
4. QG v1 usara as fontes novas da Onda A:
   - SIDRA
   - SENATRAN
   - SEJUSP-MG
   - SIOPS
   - SNIS/SINISA
5. Implementacao sera vertical (API + dados + UI por bloco de valor), nao por camada isolada.

## 3) Estado atual (baseline)

1. Backend pronto e estavel para evolucao (ops, quality, dbt, conectores MVP implementados).
2. Frontend com base operacional pronta (F1/F2/F3/F4) e integrado com API.
3. MTE ja promovido para `implemented`.
4. Contratos executivos QG ja implementados na API (Home/Prioridades/Mapa/Perfil/Insights/Eleitorado + extensoes).
5. Lacuna principal atual: fechar hardening QG v1 no frontend (E2E/homologacao/acessibilidade final), com qualidade/performance backend da Onda A ja calibradas por checks e indices.

## 4) Escopo alvo do QG v1

## 4.1 Rotas frontend alvo

1. `/` (Home executiva).
2. `/prioridades`.
3. `/mapa`.
4. `/territorio/:territory_id`.
5. `/insights`.
6. `/eleitorado`.
7. `/admin` (tecnico, separado).

Nota: `/cenarios` e `briefs` ficam como extensao v1.1 (apos QG v1 em producao).

## 4.2 Endpoints backend alvo

## Reuso imediato (ja existem)

1. `GET /v1/territories`
2. `GET /v1/territories/{id}`
3. `GET /v1/indicators`
4. `GET /v1/electorate`
5. `GET /v1/elections/results`
6. `GET /v1/geo/choropleth`
7. `GET /v1/ops/*`

## Novos endpoints obrigatorios (QG v1)

1. `GET /v1/kpis/overview`
2. `GET /v1/priority/list`
3. `GET /v1/priority/summary`
4. `GET /v1/territory/{id}/profile`
5. `GET /v1/territory/{id}/compare`
6. `GET /v1/insights/highlights`
7. `GET /v1/electorate/summary`
8. `GET /v1/electorate/map`

## Extensao v1.1

1. `POST /v1/scenarios/simulate`
2. `POST /v1/briefs` (opcional)

## 5) Modelo de dados para acelerar entrega

Abordagem pragmatica para reduzir tempo de implementacao:

1. Indicadores agregados das novas fontes entram primeiro em `silver.fact_indicator`.
2. Campos obrigatorios por linha:
   - `territory_id`
   - `reference_period`
   - `source`
   - `dataset`
   - `indicator_code`
   - `indicator_name`
   - `value`
   - `metadata_json` (fonte, cobertura, notas, unidade)
3. Tabelas dedicadas so entram quando agregacao em `fact_indicator` nao suportar necessidade analitica.

## 6) Roadmap executavel (6 sprints)

Duracao sugerida: 1 semana por sprint, com demo no final de cada sprint.

## Sprint 0 - Preparacao e contratos (1 semana)

Backend:
1. Definir schemas de resposta para endpoints novos em `src/app/schemas`.
2. Definir contrato de score/criticidade/status (formula e thresholds).
3. Definir padrao de metadados obrigatorios (`source_name`, `updated_at`, `coverage_note`, `unit`, `notes`).

Frontend:
1. Definir IA final de navegacao do QG (menu principal + admin separado).
2. Definir componentes base: `StrategicIndexCard`, `PriorityItem`, `SourceFreshnessBadge`.

Dados:
1. Definir mapeamento de indicadores para Onda A.
2. Definir chaves canonicamente estaveis para `indicator_code`.

Aceite:
1. Contratos de endpoint versionados e testados.
2. Sem decisoes pendentes para Sprint 1.

## Sprint 1 - Home QG + Prioridades basicas (1 semana)

Backend:
1. Implementar `GET /v1/kpis/overview`.
2. Implementar `GET /v1/priority/list` e `GET /v1/priority/summary` (com dados atuais disponiveis).

Frontend:
1. Entregar Home (`/`) com:
   - faixa de situacao geral
   - KPIs executivos
   - preview de prioridades
2. Entregar tela `/prioridades` com filtros e ordenacao.

Aceite:
1. Home responde pergunta "como esta a cidade e o que piorou".
2. Prioridades exibem justificativa curta por item.

## Sprint 2 - Mapa QG + Perfil 360 (1 semana)

Backend:
1. Endurecer `GET /v1/geo/choropleth` para metadados e consistencia por nivel.
2. Implementar `GET /v1/territory/{id}/profile`.
3. Implementar `GET /v1/territory/{id}/compare`.

Frontend:
1. Entregar `/mapa` com legenda, tooltip rico e drawer.
2. Entregar `/territorio/:territory_id` com secoes por dominio e comparacao.

Aceite:
1. Navegacao Home -> Mapa -> Perfil sem friccao.
2. Todas as telas mostram metadados de fonte/frescor.

## Sprint 3 - Onda A dados (parte 1) + Insights basicos (1 semana)

Backend (pipelines):
1. Implementar conectores:
   - `sidra_indicators_fetch`
   - `senatran_fleet_fetch`
   - `sejusp_public_safety_fetch`
2. Upsert em `silver.fact_indicator` + checks de qualidade + ops logs.
3. Implementar `GET /v1/insights/highlights` (versao inicial baseada em regras).

Frontend:
1. Entregar `/insights` com filtros (dominio, severidade, periodo).

Aceite:
1. 3 novas fontes em execucao idempotente.
2. Insights com evidencias navegaveis.

## Sprint 4 - Onda A dados (parte 2) + Eleitorado executivo (1 semana)

Backend (pipelines):
1. Implementar conectores:
   - `siops_health_finance_fetch`
   - `snis_sanitation_fetch`
2. Implementar:
   - `GET /v1/electorate/summary`
   - `GET /v1/electorate/map`

Frontend:
1. Entregar `/eleitorado` com visao institucional e mapas tematicos.
2. Integrar novas fontes nos blocos de Home, Prioridades e Perfil.

Aceite:
1. Onda A completa com checks e historico minimo.
2. Camada eleitorado integrada ao fluxo executivo.

## Sprint 5 - Hardening QG v1 (1 semana)

Backend:
1. Revisar performance das queries executivas.
2. Revisar cobertura de testes de contrato para endpoints novos.
3. Ajustar thresholds finais de qualidade por fonte/dominio.

Frontend:
1. E2E dos fluxos criticos:
   - Home -> Prioridades -> Mapa -> Perfil -> Eleitorado
2. Acessibilidade minima (teclado/foco/contraste).
3. Observabilidade basica de frontend (erros e web vitals).

Aceite:
1. Build e testes estaveis em homologacao.
2. QG v1 pronto para uso decisorio.

## Sprint 6 - Extensao v1.1 (opcional recomendado)

1. `POST /v1/scenarios/simulate`.
2. `/cenarios` no frontend.
3. `POST /v1/briefs` + export simples.

## 7) Matriz de implementacao por fonte (QG v1)

1. SIDRA:
   - pipeline: `sidra_indicators_fetch`
   - consumo: Home, Prioridades, Perfil
2. SENATRAN:
   - pipeline: `senatran_fleet_fetch`
   - consumo: Home, Perfil, Insights
3. SEJUSP-MG:
   - pipeline: `sejusp_public_safety_fetch`
   - consumo: Home, Mapa, Prioridades
4. SIOPS:
   - pipeline: `siops_health_finance_fetch`
   - consumo: Home, Perfil, Insights
5. SNIS/SINISA:
   - pipeline: `snis_sanitation_fetch`
   - consumo: Home, Mapa, Perfil

## 8) Criterios de aceite globais (go-live QG v1)

1. Novos endpoints executivos implementados e cobertos por testes.
2. Onda A de fontes em producao local com:
   - Bronze + manifesto/checksum
   - Silver com `territory_id`
   - quality checks ativos
   - logs em `ops.pipeline_runs` e `ops.pipeline_checks`
3. Frontend executa fluxos principais sem SQL manual.
4. Metadados de fonte/frescor/cobertura visiveis nas telas executivas.
5. `/admin` separado do fluxo principal.
6. Build + testes backend/frontend estaveis em homologacao.

## 9) Riscos de execucao e mitigacao

1. Quebra de layout de fonte externa:
   - mitigacao: parser resiliente + testes de contrato de conector.
2. Latencia em endpoints executivos:
   - mitigacao: agregacoes pre-computadas e cache por chave de filtro.
3. Divergencia entre narrativa e dado:
   - mitigacao: regras de prioridade/insight versionadas no backend.
4. Escopo inflado:
   - mitigacao: manter cenarios/briefs em v1.1.

## 10) Ordem de inicio recomendada (acao imediata)

1. Sprint 0: contratos de endpoint + regras de score/criticidade.
2. Sprint 1: Home + Prioridades com APIs novas.
3. Sprint 2: Mapa + Perfil 360.
4. Sprint 3/4: Onda A completa.
5. Sprint 5: hardening e go-live QG v1.
