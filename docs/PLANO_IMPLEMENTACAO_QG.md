# Plano Integrado de Implementacao (Backend + Frontend QG)

Data de referencia: 2026-02-13  
Status: execucao ativa (fase de hardening + go-live controlado)  
Escopo: plano executavel para consolidar QG estrategico em producao com dados reais.

## 1) Objetivo

Entregar e estabilizar o QG estrategico municipal de Diamantina/MG, com:

1. Home executiva para leitura rapida.
2. Priorizacao territorial explicavel.
3. Mapa analitico com recorte por indicador/periodo.
4. Territorio 360 com comparacao orientada.
5. Camada institucional de eleitorado.
6. Fluxo tecnico isolado em `/admin`.
7. Extensoes operacionais de decisao (`/cenarios` e `/briefs`).

## 2) Premissas e decisoes vigentes

1. Fonte de verdade tecnica: `CONTRATO.md`.
2. `docs/FRONTEND_SPEC.md` permanece como referencia complementar de produto/UX, sem substituir contrato tecnico ou este plano executavel.
3. Camada tecnica segue separada da UX executiva (sem foco em auth nesta fase).
4. Entrega segue vertical (API + pipeline + UI + teste), por bloco de valor.
5. Modelo principal de integracao de dados continua em `silver.fact_indicator`, com rastreabilidade de `source`, `dataset`, `reference_period` e metadados.
6. `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` e o documento de visao estrategica (north star), sem competir com este plano executavel.
7. `PLANO_FONTES_DADOS_DIAMANTINA.md` e documento de catalogo/priorizacao de fontes; validacao de estado atual fica em `HANDOFF.md` e `ops/readiness`.

## 2.1 Consolidacao documental (feito em 2026-02-13)

1. Visao estrategica consolidada em `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`.
2. Execucao e priorizacao consolidada neste arquivo.
3. Estado operacional e validacoes correntes consolidadas em `HANDOFF.md`.
4. Rastreabilidade item a item do plano de evolucao consolidada em
   `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`.
5. Specs-base da visao estrategica consolidadas (v1.0):
   - `MAP_PLATFORM_SPEC.md`
   - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
   - `STRATEGIC_ENGINE_SPEC.md`
6. Proximo passo documental: manter sincronia continua das specs com cada entrega vertical (codigo + teste + operacao).

## 2.2 Status por onda (fonte unica)

1. Onda 0: concluida.
2. Onda 1: concluida.
3. Onda 2: concluida.
4. Onda 3: concluida.
5. Onda 4: concluida.
6. Onda 5: em andamento avancado (MP-1, MP-2 e MP-3 entregues; pendente consolidacao UX final e recursos pos-v1).
7. Onda 6: em andamento (UX imersiva com mapa dominante + ajuste de usabilidade em telas executivas).
8. Onda 7: concluida v1 (cenarios/briefs), com refinamentos pendentes.
9. Onda 8: em andamento (E2E fluxo critico concluido, cache HTTP ativo, MVs e GIST criados, benchmark p95 criado, edge-cases 44 testes, acessibilidade concluida).

## 3) Estado consolidado atual

## 3.1 Backend/API

1. Contratos QG implementados e ativos:
   - `GET /v1/kpis/overview`
   - `GET /v1/priority/list`
   - `GET /v1/priority/summary`
   - `GET /v1/insights/highlights`
   - `GET /v1/geo/choropleth`
   - `GET /v1/territory/{id}/profile`
   - `GET /v1/territory/{id}/compare`
   - `GET /v1/territory/{id}/peers`
   - `GET /v1/electorate/summary`
   - `GET /v1/electorate/map`
   - `POST /v1/scenarios/simulate`
   - `POST /v1/briefs`
2. Camada ops/observabilidade ativa:
   - `GET /v1/ops/*`
   - `POST /v1/ops/frontend-events`
   - `GET /v1/ops/frontend-events`
   - `GET /v1/ops/source-coverage`
3. Readiness local atual: `READY` com `hard_failures=0` e `warnings=1` (SLO-1 historico na janela de 7 dias).

## 3.2 Frontend

1. Rotas executivas ativas:
   - `/`
   - `/prioridades`
   - `/mapa`
   - `/territorio/:territoryId`
   - `/insights`
   - `/eleitorado`
   - `/cenarios`
   - `/briefs`
   - `/admin`
2. Recursos ja entregues:
   - deep-link por query string (mapa/prioridades/insights/briefs/cenarios).
   - exportacoes no mapa (CSV/SVG/PNG).
   - exportacao de brief (HTML + print para PDF).
   - metadados de fonte/frescor/cobertura nas telas executivas.
   - padronizacao de dominios e rotulos amigaveis (QG e Territorio 360).
3. Testes e build do frontend estaveis no ciclo atual.

## 3.3 Pipelines e fontes

1. Ondas Onda A e Onda B/C implementadas e integradas no orquestrador (`run_mvp_wave_4`, `run_mvp_wave_5`, `run_mvp_all`).
2. Estado de conectores sincronizado em `ops.connector_registry` com 22 conectores `implemented`.
3. Fluxos reais recentes executados com sucesso para ondas 4 e 5.

## 4) Status por sprint

1. Sprint 0 (contratos e base): concluida.
2. Sprint 1 (Home + Prioridades): concluida.
3. Sprint 2 (Mapa + Territorio 360): concluida.
4. Sprint 3 (Onda A parte 1 + Insights): concluida.
5. Sprint 4 (Onda A parte 2 + Eleitorado): concluida.
6. Sprint 5 (hardening QG v1): em andamento.
7. Sprint 6 (extensoes v1.1: cenarios/briefs): concluida.

## 5) Escopo de proxima execucao (Sprint 9)

## 5.1 Prioridade alta

1. Fechar homologacao ponta a ponta com dados reais (API + frontend).
2. Cobrir fluxo critico com E2E:
   - Home -> Prioridades -> Mapa -> Territorio -> Eleitorado -> Cenarios/Briefs.
   - **status 2026-02-13: CONCLUIDO** — `e2e-flow.test.tsx` com 5 testes cobrindo fluxo completo + deep-links + admin.
3. Consolidar SLO-1 operacional sem ruido historico:
   - ajustar janela/estrategia de leitura para separar historico legado de estado corrente.
   - status 2026-02-12: parcial entregue no `scripts/backend_readiness.py` com
     `--health-window-days` e bloco `slo1_current`; pendente refletir o mesmo
     padrao nas visoes de frontend operacional.
   - status 2026-02-12 (iteracao atual): monitor comparativo de janela (`7d` vs `1d`)
     entregue na `OpsHealthPage` e endpoint dedicado `GET /v1/ops/readiness`
     implementado para consumo direto por dashboards externos.
   - **status 2026-02-13: CONCLUIDO** — `ReadinessBanner` no `/admin` consome `GET /v1/ops/readiness`
     com exibicao de conectores, SLO-1 (7d/1d), falhas e avisos.
4. Revisar performance das queries executivas mais usadas (`overview`, `priority`, `mapa`, `territory profile`).
   - **status 2026-02-13: PARCIAL** — materialized views criadas (`db/sql/006_materialized_views.sql`),
     indices GIST criados (`db/sql/007_spatial_indexes.sql`),
     cache HTTP ativo via `CacheHeaderMiddleware`.
   - **status 2026-02-13 (Sprint 5.2): OK** — script de benchmark criado (`scripts/benchmark_api.py`)
     com medicao de p50/p95/p99 em 12 endpoints criticos, alvo p95<=800ms.
5. Evoluir as specs estrategicas de `v0.1` para `v1.0` e iniciar execucao tecnica orientada por elas:
   - `MAP_PLATFORM_SPEC.md`
   - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
   - `STRATEGIC_ENGINE_SPEC.md`
   - status 2026-02-13: MP-1 do mapa concluido (`/v1/map/layers` + integracao no `QgMapPage`).

## 5.2 Prioridade media

1. Completar hardening de acessibilidade nas telas executivas (teclado, foco e contraste em todos os estados).
   - **status 2026-02-13 (Sprint 5.2): CONCLUIDO** — `Panel` com `aria-labelledby` via `useId`, `StateBlock` com `role=alert/status`,
     `StrategicIndexCard` com `aria-label`, paginas executivas com `<main>`, 7 tabelas com `aria-label`,
     botoes de exportacao com `aria-label` contextual, ranking com keyboard support, quick-actions em `<nav>`.
2. Revisar cobertura de testes de contrato backend para casos limite dos endpoints QG.
   - **status 2026-02-13 (Sprint 5.2): CONCLUIDO** — `tests/unit/test_qg_edge_cases.py` com 44 testes
     (nivel invalido, limites, dados vazios, request_id, content-type, electorate year/metric).
3. Revisar thresholds de qualidade por dominio/fonte com base no comportamento real das ondas 4 e 5.
   - **status 2026-02-13 (Sprint 5.3): CONCLUIDO** — 15 fontes com `min_rows` explicito em `quality_thresholds.yml`;
     `quality.py` ampliado para 15 fontes em `source_rows` e 14 jobs em `ops_pipeline_runs`;
     MVP-5 sources elevados de 0→1.

## 5.3 Prioridade baixa

1. Refinar UX de observabilidade no `/admin` para acelerar diagnostico operacional.
   - **status 2026-02-13 (Sprint 5.3): CONCLUIDO** — 3 paineis colapsaveis adicionados em `OpsHealthPage`:
     Quality checks, Cobertura de fontes, Registro de conectores.
     `CollapsiblePanel` component criado com chevron, badge count, `aria-expanded`.
     Progressive disclosure aplicado em `QgOverviewPage` (Dominios Onda B/C colapsado).
2. Consolidar runbooks de operacao para ambiente de homologacao/producao.

## 5.4 Atualizacao de foco (2026-02-13)

1. Camadas territoriais:
   - API tecnica de camadas publicada em `/v1/territory/layers/*` (catalogo, coverage, metadata e readiness).
   - pagina tecnica `/ops/layers` ativa para rastreio operacional por camada.
2. Qualidade de camadas:
   - checks `map_layer_rows_*` e `map_layer_geometry_ratio_*` integrados ao `quality_suite`.
3. Base eleitoral territorial:
   - `tse_results_fetch` evoluido para carregar zona e secao eleitoral em `silver.dim_territory`.
   - `tse_results_fetch` agora detecta `local_votacao` quando presente e preserva o dado em metadata da secao.
   - gravacao de resultados eleitorais com resolucao de territorio por secao > zona > municipio.
   - camada backend `territory_polling_place` publicada no manifesto de mapa para pontos eleitorais derivados.
4. Proximos incrementos imediatos:
   - consolidar o consumo explicito da camada `local_votacao` no frontend (toggle/legenda/tooltip) em todas as telas com mapa;
   - fechamento de UX em `Territorio 360` e `Eleitorado` para eliminar estados vazios sem contexto;
   - regressao completa de backend/frontend apos cada entrega vertical.

## 6) Matriz de fontes e consumo no QG

## Onda A

1. SIDRA (`sidra_indicators_fetch`): Home, Prioridades, Perfil.
2. SENATRAN (`senatran_fleet_fetch`): Home, Perfil, Insights.
3. SEJUSP-MG (`sejusp_public_safety_fetch`): Home, Mapa, Prioridades.
4. SIOPS (`siops_health_finance_fetch`): Home, Perfil, Insights.
5. SNIS (`snis_sanitation_fetch`): Home, Mapa, Perfil.

## Onda B/C

1. INMET (`inmet_climate_fetch`): Home, Insights, Perfil.
2. INPE Queimadas (`inpe_queimadas_fetch`): Home, Mapa, Insights.
3. ANA (`ana_hydrology_fetch`): Home, Mapa, Perfil.
4. ANATEL (`anatel_connectivity_fetch`): Home, Perfil, Prioridades.
5. ANEEL (`aneel_energy_fetch`): Home, Perfil, Insights.

## 7) Criterios de aceite para go-live controlado

1. Endpoints executivos e extensoes (`cenarios`/`briefs`) estaveis com testes de contrato.
2. Ondas A e B/C operando com:
   - Bronze + manifesto/checksum
   - Silver com `territory_id`
   - checks de qualidade ativos
   - rastreio em `ops.pipeline_runs` e `ops.pipeline_checks`
3. Frontend com testes e build estaveis no ciclo de entrega.
4. Fluxo executivo separado da camada tecnica (`/admin`).
5. Homologacao executada com dados reais e sem bloqueador critico aberto.
6. Metas operacionais objetivas registradas e validadas:
   - API executiva p95 <= 800ms em homologacao para endpoints criticos.
   - render inicial da Home executiva <= 3s em ambiente de referencia.
   - E2E do fluxo principal com taxa de sucesso >= 95% no ciclo de release.

## 8) Riscos atuais e mitigacoes

1. Instabilidade eventual de fonte externa:
   - mitigacao: fallback por catalogo/manual + bronze cache + testes de conector.
2. SLO operacional distorcido por historico antigo:
   - mitigacao: separar leitura de saude corrente e historica nos relatorios.
3. Divergencia entre narrativa e dado:
   - mitigacao: manter regras de prioridade/insight versionadas e auditaveis no backend.
4. Regressao de UX em evolucoes rapidas:
   - mitigacao: ampliar E2E dos caminhos de decisao e manter smoke de roteamento.

## 9) Ordem recomendada para os proximos passos

1. Fechar E2E dos fluxos executivos e registrar baseline de homologacao.
2. Rodar bateria completa em ambiente limpo e publicar relatorio unico de readiness.
   - **status 2026-02-13: CONCLUIDO** — `scripts/homologation_check.py` criado com 5 dimensoes
     (backend readiness, quality suite, frontend build, test suites, API smoke).
3. Ajustar pendencias de performance/thresholds detectadas na homologacao.
   - **status 2026-02-13: CONCLUIDO** — thresholds revisados por fonte; MVP-5 corrigido de 0→1.
4. Congelar contrato v1.0 do QG para operacao assistida.
5. Planejar proximo ciclo incremental (novas fontes e refinamentos analiticos).
