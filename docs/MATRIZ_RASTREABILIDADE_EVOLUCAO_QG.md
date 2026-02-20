# Matriz de Rastreabilidade - Plano de Evolucao QG

Data de referencia: 2026-02-20
Fonte analisada: `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` (versao 1.1.0)

## Regra de leitura

- Objetivo: evidenciar, item a item, o que ja esta implementado e o que ainda falta.
- Excecao acordada: **nao exigir** reorganizacao para `apps/frontend` e `apps/api`.
- Legenda de status:
  - `OK`: implementado e evidenciado.
  - `PARCIAL`: implementado em parte, com lacunas relevantes.
  - `PENDENTE`: ainda nao implementado.
  - `NAO EVIDENCIADO`: sem evidencia suficiente no codigo/documentacao atual.

## 1) Principios nao negociaveis

| ID | Item do plano | Status | Evidencia atual | Falta implementar |
|---|---|---|---|---|
| P01 | Frontend orientado a decisao | PARCIAL | `frontend/src/modules/qg/pages/QgOverviewPage.tsx`, `QgPrioritiesPage.tsx`, `QgInsightsPage.tsx`; `CollapsiblePanel` com progressive disclosure | Layout B com mapa dominante na Home |
| P02 | Mapa como elemento principal da experiencia | PARCIAL | `frontend/src/modules/qg/pages/QgMapPage.tsx` | Home ainda nao esta no layout B com mapa dominante |
| P03 | Separacao executivo x tecnico (`/admin`) | OK | `AdminHubPage.tsx` com `ReadinessBanner` consumindo `GET /v1/ops/readiness`, rotas QG e ops segregadas | N/A |
| P04 | Dados eleitorais apenas agregados | OK | `src/app/api/routes_qg.py` (`/electorate/summary`, `/electorate/map`) | Documentar regra de supressao/limiar por granularidade fina |
| P05 | Transparencia "oficial vs proxy" | OK | `source_classification` no `QgMetadata` (backend + frontend), `_classify_source()` em routes_qg.py, badge em `SourceFreshnessBadge` com label contextual | - |
| P06 | Local-first reproduzivel | PARCIAL | `scripts/dev_up.ps1`, `scripts/dev_down.ps1` | Empacotamento launcher final e modo demo seedado |
| P07 | Nomes tecnicos em ingles e UI em portugues | OK | SQL/API em ingles; rotulos UI em portugues nas paginas QG | Revisao final de consistencia de termos |

## 2) Entregaveis documentais do plano

| ID | Documento esperado | Status | Evidencia atual | Falta implementar |
|---|---|---|---|---|
| D01 | `CONTRATO.md` como base tecnica | OK | `CONTRATO.md` v1.0 congelado (2026-02-13): endpoints executivos, SLOs validados, criterios de go-live com ferramentas, frontend executivo completo | N/A |
| D02 | Plano executavel consolidado | OK | `docs/PLANO_IMPLEMENTACAO_QG.md` | Manter atualizacao por ciclo |
| D03 | Estado operacional corrente | OK | `HANDOFF.md` | Atualizacao continua |
| D04 | `docs/FRONTEND_SPEC.md` (referencia complementar) | OK | `docs/FRONTEND_SPEC.md` mantido como referencia oficial complementar de UX/produto | Revisar incrementalmente conforme evolucao de UX |
| D05 | `MAP_PLATFORM_SPEC.md` | OK | `MAP_PLATFORM_SPEC.md` atualizado para v1.0.0 com MP-2/MP-3 entregues e backlog pos-v2 | Manter atualizacao incremental de backlog |
| D06 | `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` | OK | `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` v1.0.0 com TL-2 concluido e TL-3 baseline entregue | Evoluir camada `local_votacao` |
| D07 | `STRATEGIC_ENGINE_SPEC.md` | OK | `STRATEGIC_ENGINE_SPEC.md` v1.0.0 | Revisoes futuras de pesos/thresholds por dominio |

## 3) Macro-arquitetura alvo

| ID | Item do plano | Status | Evidencia atual | Falta implementar |
|---|---|---|---|---|
| A01 | Bronze/Silver/Gold/Ops ativos | OK | `db/sql/002_silver_schema.sql`, `src/pipelines/*`, `src/app/api/routes_ops.py` | Ajustes incrementais por dominio |
| A02 | Postgres + PostGIS | OK | checks de readiness em `src/app/ops_readiness.py` | N/A |
| A03 | Indices geoespaciais dedicados | OK | `db/sql/007_spatial_indexes.sql` com GIST em `dim_territory.geometry`, GIN trigram em `name`, covering index para joins de mapa | N/A |
| A04 | Materialized views para mapa/ranking | OK | `db/sql/006_materialized_views.sql` com `mv_territory_ranking`, `mv_map_choropleth`, `mv_territory_map_summary` + funcao `gold.refresh_materialized_views()` | Executar `REFRESH` inicial em producao |
| A05 | Geometrias simplificadas por zoom | PARCIAL | `mv_territory_map_summary` usa `ST_SimplifyPreserveTopology(geometry, 0.001)` para geometria simplificada | Implementar multiplos niveis de simplificacao por faixa de zoom |
| A06 | API orientada a UI | OK | `src/app/api/routes_qg.py`, `src/app/api/routes_geo.py`, `src/app/api/routes_ops.py` | Evolucoes de contrato conforme E2E |
| A07 | Cache HTTP (ETag/Last-Modified) | OK | `src/app/api/cache_middleware.py` com `CacheHeaderMiddleware` (Cache-Control + weak ETag + 304 condicional) aplicado em endpoints criticos (mapa/kpis/territory/choropleth/electorate) | N/A |
| A08 | React Query | OK | queries em paginas QG/ops (`useQuery`) | N/A |
| A09 | Zustand | OK | store global de filtros ativo em `frontend/src/shared/stores/filterStore.ts` | Revisar acoplamento entre paginas |
| A10 | Layout B (mapa dominante + painel lateral) | PARCIAL | layout dominante implementado, mas com ajustes de UX e overflow ainda em curso | Ajustar usabilidade final e responsividade |
| A11 | Empacotamento local tipo launcher final | PARCIAL | scripts PowerShell de subida/queda | Empacotar distribuicao sem terminal (ex.: PyInstaller) |

## 4) Ondas de evolucao (item por item)

### Onda 0 - Fundamentos

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O0-01 | Projeto roda local com stack base | PARCIAL | `scripts/dev_up.ps1`, `docker-compose.yml` | Fluxo "um clique" completo e robusto para usuario nao tecnico |
| O0-02 | PostGIS + migrations + base ops | OK | `db/sql/*.sql`, `scripts/init_db.py` | N/A |
| O0-03 | Observabilidade minima (health/logs) | OK | `/v1/health`, `routes_ops.py`, telemetria frontend | Expandir alertas operacionais |

### Onda 1 - Territorio oficial + geoespacial

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O1-01 | Ingestao IBGE admin/geometrias/indicadores | OK | conectores IBGE em `src/pipelines` e registry em `configs/connectors.yml` | N/A |
| O1-02 | Camada territorial Gold para joins | OK | `silver.dim_territory`, `silver.fact_indicator` | N/A |
| O1-03 | Microterritorio setorial pronto para uso executado | PARCIAL | niveis contemplados em schema e filtros | Consolidar cobertura operacional por setor censitario |
| O1-04 | Mapa choropleth minimo por municipio/distrito | OK | `/v1/geo/choropleth`, `QgMapPage.tsx` | Evoluir para plataforma vetorial |

### Onda 2 - Eleitorado e participacao

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O2-01 | Eleitorado agregado por zona/secao | OK | `fact_electorate`, `routes_qg.py` (`/electorate/summary`) | N/A |
| O2-02 | Participacao (comparecimento/abstencao/brancos/nulos) | PARCIAL | endpoint e tela executiva eleitorado | Completar cobertura de indicadores em todos os recortes pretendidos |
| O2-03 | Locais de votacao geocodificados | NAO EVIDENCIADO | nao ha evidencia explicita no frontend/API atual | Implementar camada de pontos de locais |
| O2-04 | Proxies eleitorais espaciais (ex.: Voronoi) | PENDENTE | sem implementacao detectada | Definir metodologia e implementar |

### Onda 3 - Servicos publicos e infraestrutura

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O3-01 | Fontes de servicos integradas (INEP, DATASUS etc.) | OK | conectores MVP-3 e ondas 4/5 em `src/pipelines` | N/A |
| O3-02 | Camada de pontos de servicos no mapa | PARCIAL | dados existem em pipeline; UI principal ainda centrada em choropleth | Implementar camadas de pontos/toggles de servico |
| O3-03 | Proxies de cobertura (buffers/isochrones) | PENDENTE | sem evidencia no codigo atual | Definir spec + executar |

### Onda 4 - Motor estrategico v1

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O4-01 | Prioridades (`/priority/list`, `/priority/summary`) | OK | `src/app/api/routes_qg.py` | N/A |
| O4-02 | Insights (`/insights/highlights`) | OK | `src/app/api/routes_qg.py` | N/A |
| O4-03 | Regras de severidade e justificativas | OK | resposta QG e cards no frontend (`PriorityItemCard`) | Formalizar spec do motor |
| O4-04 | Indices compostos formalmente especificados | PARCIAL | score/ranking em APIs e UI | Consolidar metodologia em `STRATEGIC_ENGINE_SPEC.md` |
| O4-05 | Supressao/limiar minimo por granularidade | PARCIAL | checks de qualidade existentes | Formalizar regra de supressao no spec do motor |

### Onda 5 - Plataforma de mapa "Google Maps-like"

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O5-01 | Plataforma de vector tiles (MVT) | OK | endpoint MVT ativo em `routes_map.py`, com testes de contrato | N/A |
| O5-02 | Troca automatica de camadas por zoom | OK | `useAutoLayerSwitch` + regras por manifesto de camadas | N/A |
| O5-03 | Modos: choropleth/heatmap/pontos/hotspots | OK | modos vetoriais implementados no `QgMapPage` com fallback SVG | N/A |
| O5-04 | Split view comparativo | PENDENTE | sem recurso no mapa atual | Implementar visao comparativa |
| O5-05 | Time slider | PENDENTE | sem slider temporal no mapa | Implementar controle temporal |
| O5-06 | Home B com mapa 60-70% | PARCIAL | Home com mapa dominante entregue, pendente acabamento de UX e leitura em telas menores | Ajustes finais de layout e navegacao |

### Onda 6 - UX imersiva orientada por decisao

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O6-01 | Home com painel lateral + top prioridades + hotspots | PARCIAL | painel de prioridades e acoes rapidas em `QgOverviewPage.tsx` | Tornar mapa o elemento dominante com painel lateral persistente |
| O6-02 | Drawer de mini perfil 360 com acoes | PENDENTE | sem drawer estrategico dedicado | Implementar drawer e fluxo de clique no mapa |
| O6-03 | Remover tabelas longas da Home | OK | `CollapsiblePanel` criado; "Dominios Onda B/C" colapsado por padrao, "KPIs executivos" expandido com badge de contagem | - |
| O6-04 | Meta de compreensao <10s validada | PENDENTE | sem metrica UX formal | Definir e medir KPI de compreensao |

### Onda 7 - Cenarios + Briefs

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O7-01 | Simulacao (`POST /scenarios/simulate`) | OK | `routes_qg.py`, `QgScenariosPage.tsx` | N/A |
| O7-02 | Antes/depois de score e ranking | OK | `QgScenariosPage.tsx` (cards de resultado) | Refinar UX de leitura executiva |
| O7-03 | Brief executivo (`POST /briefs`) | OK | `routes_qg.py`, `QgBriefsPage.tsx` | N/A |
| O7-04 | Export HTML/PDF | OK | botoes exportar/imprimir em `QgBriefsPage.tsx` | N/A |
| O7-05 | Salvar selecoes persistentes para reuniao | OK | `usePersistedFormState` hook (queryString > localStorage > defaults) integrado em QgScenariosPage (6 campos) e QgBriefsPage (5 campos) | - |

### Onda 8 - Hardening, QA e defensabilidade

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O8-01 | Testes E2E de fluxos criticos | OK | `frontend/src/app/e2e-flow.test.tsx` com 5 testes cobrindo Home→Prioridades→Mapa→Territorio→Eleitorado→Cenarios→Briefs + deep-links + admin→executivo; smoke test mantido em `router.smoke.test.tsx` | Expandir cobertura para fluxos secundarios |
| O8-02 | Monitoramento frontend + API | OK | telemetria frontend (events ingest + query), OpsHealthPage com 7 paineis (status geral, SLO-1, SLA por job, tendencia, quality checks, cobertura de fontes, conectores), `scripts/homologation_check.py` com 5 dimensoes | Alertas automaticos opcionais |
| O8-03 | Performance profiling (mapa/consultas) | OK | `scripts/benchmark_api.py` com p50/p95/p99 em 12 endpoints, alvo p95<=800ms, CLI com --rounds/--json | Executar benchmark em ambiente de homologacao |
| O8-04 | Seguranca minima com admin separado | PARCIAL | separacao `/admin` existente | Definir/implementar auth local se exigido |
| O8-05 | Defensabilidade metodologica completa | PARCIAL | fontes e metadados exibidos em UI | Documento formal de metodologia/limites/proxies |

## 5) Consolidado de pendencias de implementacao

### Criticas (prioridade imediata)

1. Evoluir camada eleitoral espacial para `local_votacao` (ponto) com transparencia metodologica.
2. Corrigir inconsistencias de UX/layout em telas executivas (mapa, territorio 360, eleitorado).
3. Fechar hardening Onda 8 com benchmark recorrente em homologacao e alertas operacionais.
4. Consolidar runbook de operacoes para homologacao/producao com procedimento de degradacao de camadas.

### Importantes

1. Expandir governanca de qualidade de camadas eleitorais (threshold por nivel e alerta).
2. Evoluir backlog pos-v2 do mapa (split view, time slider, comparacao temporal).

## 6) Observacao sobre estrutura de repositorio

Conforme decisao do time, a exigencia de estrutura exata `apps/frontend` e `apps/api`
nao e obrigatoria neste ciclo e nao bloqueia aceite.
