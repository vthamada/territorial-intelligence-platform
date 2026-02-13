# Matriz de Rastreabilidade - Plano de Evolucao QG

Data de referencia: 2026-02-13
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
| P01 | Frontend orientado a decisao | PARCIAL | `frontend/src/modules/qg/pages/QgOverviewPage.tsx`, `QgPrioritiesPage.tsx`, `QgInsightsPage.tsx` | Refinar UX para reduzir densidade e aumentar leitura instantanea |
| P02 | Mapa como elemento principal da experiencia | PARCIAL | `frontend/src/modules/qg/pages/QgMapPage.tsx` | Home ainda nao esta no layout B com mapa dominante |
| P03 | Separacao executivo x tecnico (`/admin`) | OK | `frontend/src/modules/admin/pages/AdminHubPage.tsx`, rotas QG e ops segregadas | Consolidar indicadores de readiness tambem no `/admin` |
| P04 | Dados eleitorais apenas agregados | OK | `src/app/api/routes_qg.py` (`/electorate/summary`, `/electorate/map`) | Documentar regra de supressao/limiar por granularidade fina |
| P05 | Transparencia "oficial vs proxy" | PARCIAL | mencoes em docs e badges de fonte (`SourceFreshnessBadge`) | Implementar badge explicito oficial/proxy por camada |
| P06 | Local-first reproduzivel | PARCIAL | `scripts/dev_up.ps1`, `scripts/dev_down.ps1` | Empacotamento launcher final e modo demo seedado |
| P07 | Nomes tecnicos em ingles e UI em portugues | OK | SQL/API em ingles; rotulos UI em portugues nas paginas QG | Revisao final de consistencia de termos |

## 2) Entregaveis documentais do plano

| ID | Documento esperado | Status | Evidencia atual | Falta implementar |
|---|---|---|---|---|
| D01 | `CONTRATO.md` como base tecnica | OK | `CONTRATO.md` | Revisoes pontuais de SLO/criterios com readiness novo |
| D02 | Plano executavel consolidado | OK | `docs/PLANO_IMPLEMENTACAO_QG.md` | Manter atualizacao por ciclo |
| D03 | Estado operacional corrente | OK | `HANDOFF.md` | Atualizacao continua |
| D04 | `FRONTEND_SPEC_QG_ESTRATEGICO_v2.0.0.md` | PENDENTE | existe `docs/FRONTEND_SPEC.md` | Decidir: criar arquivo v2.0.0 ou manter `FRONTEND_SPEC.md` como substituto oficial |
| D05 | `MAP_PLATFORM_SPEC.md` | OK | `MAP_PLATFORM_SPEC.md` (v0.1.0) | Refinar para v1.0 com contratos finais e metas validadas em homologacao |
| D06 | `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` | OK | `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` (v0.1.0) | Refinar para v1.0 com catalogo final de camadas e regras de supressao |
| D07 | `STRATEGIC_ENGINE_SPEC.md` | OK | `STRATEGIC_ENGINE_SPEC.md` (v0.1.0) | Refinar para v1.0 com pesos/thresholds versionados em config real |

## 3) Macro-arquitetura alvo

| ID | Item do plano | Status | Evidencia atual | Falta implementar |
|---|---|---|---|---|
| A01 | Bronze/Silver/Gold/Ops ativos | OK | `db/sql/002_silver_schema.sql`, `src/pipelines/*`, `src/app/api/routes_ops.py` | Ajustes incrementais por dominio |
| A02 | Postgres + PostGIS | OK | checks de readiness em `src/app/ops_readiness.py` | N/A |
| A03 | Indices geoespaciais dedicados | PARCIAL | indices gerais em `db/sql/003_indexes.sql`, `db/sql/004_qg_ops_indexes.sql` | Adicionar indices espaciais (GIST) e tuning geospatial |
| A04 | Materialized views para mapa/ranking | PENDENTE | sem `MATERIALIZED VIEW` em `db/sql` | Implementar MVs e refresh strategy |
| A05 | Geometrias simplificadas por zoom | PENDENTE | sem pipeline de simplificacao por zoom | Criar artefatos simplificados por nivel |
| A06 | API orientada a UI | OK | `src/app/api/routes_qg.py`, `src/app/api/routes_geo.py`, `src/app/api/routes_ops.py` | Evolucoes de contrato conforme E2E |
| A07 | Cache HTTP (ETag/Last-Modified) | PENDENTE | sem evidencia de headers de cache em rotas | Implementar cache headers nos endpoints criticos |
| A08 | React Query | OK | queries em paginas QG/ops (`useQuery`) | N/A |
| A09 | Zustand | PENDENTE | sem uso de `zustand` no frontend | Decidir se sera adotado ou remover da meta |
| A10 | Layout B (mapa dominante + painel lateral) | PENDENTE | Home atual existe, mas sem mapa dominante | Implementar layout B na Home executiva |
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
| O5-01 | Plataforma de vector tiles (MVT) | PENDENTE | sem endpoint de tiles vetoriais | Implementar arquitetura de tiles |
| O5-02 | Troca automatica de camadas por zoom | PENDENTE | mapa atual nao possui motor multi-zoom de layers | Implementar regras por zoom |
| O5-03 | Modos: choropleth/heatmap/pontos/hotspots | PARCIAL | choropleth existente | Implementar heatmap/hotspots/pontos com toggle |
| O5-04 | Split view comparativo | PENDENTE | sem recurso no mapa atual | Implementar visao comparativa |
| O5-05 | Time slider | PENDENTE | sem slider temporal no mapa | Implementar controle temporal |
| O5-06 | Home B com mapa 60-70% | PENDENTE | Home atual nao e mapa-dominante | Redesenhar Home executiva |

### Onda 6 - UX imersiva orientada por decisao

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O6-01 | Home com painel lateral + top prioridades + hotspots | PARCIAL | painel de prioridades e acoes rapidas em `QgOverviewPage.tsx` | Tornar mapa o elemento dominante com painel lateral persistente |
| O6-02 | Drawer de mini perfil 360 com acoes | PENDENTE | sem drawer estrategico dedicado | Implementar drawer e fluxo de clique no mapa |
| O6-03 | Remover tabelas longas da Home | PARCIAL | parte da Home ainda usa tabelas/cartoes em bloco | Migrar para abas/detalhes progressivos |
| O6-04 | Meta de compreensao <10s validada | PENDENTE | sem metrica UX formal | Definir e medir KPI de compreensao |

### Onda 7 - Cenarios + Briefs

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O7-01 | Simulacao (`POST /scenarios/simulate`) | OK | `routes_qg.py`, `QgScenariosPage.tsx` | N/A |
| O7-02 | Antes/depois de score e ranking | OK | `QgScenariosPage.tsx` (cards de resultado) | Refinar UX de leitura executiva |
| O7-03 | Brief executivo (`POST /briefs`) | OK | `routes_qg.py`, `QgBriefsPage.tsx` | N/A |
| O7-04 | Export HTML/PDF | OK | botoes exportar/imprimir em `QgBriefsPage.tsx` | N/A |
| O7-05 | Salvar selecoes persistentes para reuniao | PARCIAL | prefill por query string | Persistencia de sessao/colecoes de brief |

### Onda 8 - Hardening, QA e defensabilidade

| ID | Item | Status | Evidencia | Falta |
|---|---|---|---|---|
| O8-01 | Testes E2E de fluxos criticos | PARCIAL | smoke test em `frontend/src/app/router.smoke.test.tsx` | Cobertura E2E completa dos fluxos de decisao |
| O8-02 | Monitoramento frontend + API | PARCIAL | telemetria frontend + endpoints ops | Painel consolidado e alertas operacionais |
| O8-03 | Performance profiling (mapa/consultas) | PENDENTE | metas registradas no plano, sem rotina de profiling evidenciada | Implementar benchmark p95 e rotina de afericao |
| O8-04 | Seguranca minima com admin separado | PARCIAL | separacao `/admin` existente | Definir/implementar auth local se exigido |
| O8-05 | Defensabilidade metodologica completa | PARCIAL | fontes e metadados exibidos em UI | Documento formal de metodologia/limites/proxies |

## 5) Consolidado de pendencias de implementacao

### Criticas (prioridade imediata)

1. Executar a Onda 5 real (MVT, multi-zoom, camadas dinamicas, mapa dominante na Home).
2. Fechar hardening Onda 8 com E2E de fluxo principal e baseline de performance.
3. Evoluir as 3 specs v0.1 para v1.0 com contratos finais e criterios de aceite medidos.

### Importantes

1. Formalizar regra "oficial vs proxy" na UI e em metadados de resposta.
2. Evoluir camada eleitoral espacial (locais/proxies) com transparencia metodologica.
3. Completar persistencia de selecoes para fluxo de reuniao (brief/cenario).

## 6) Observacao sobre estrutura de repositorio

Conforme decisao do time, a exigencia de estrutura exata `apps/frontend` e `apps/api`
nao e obrigatoria neste ciclo e nao bloqueia aceite.
