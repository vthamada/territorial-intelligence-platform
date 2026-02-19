# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-19
Planejamento principal: `PLANO.md`
Contrato tecnico principal: `CONTRATO.md`

## Atualizacao tecnica (2026-02-18) - Robustez de banco

- Hardening de cobertura territorial concluido no backend:
  - `tse_electorate_fetch` agora grava eleitorado municipal e por zona eleitoral (com upsert em `dim_territory` nivel `electoral_zone`).
  - `ibge_geometries_fetch` agora grava `IBGE_GEOMETRY_AREA_KM2` em `silver.fact_indicator` para `municipality`, `district` e `census_sector`.
- Backfill robusto executado com sucesso:
  - comando (historico eleitoral): `scripts/backfill_robust_database.py --tse-years 2024,2022,2020,2018,2016 --indicator-periods 2025`.
  - comando (multianual indicadores): `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --indicator-periods 2025,2024,2023,2022,2021`.
  - relatorio: `data/reports/robustness_backfill_report.json`.
  - cobertura eleitoral consolidada:
    - `fact_electorate`: `5` anos distintos (`2016`-`2024`) e `3562` linhas.
    - `fact_election_result`: `5` anos distintos (`2016`-`2024`), `180` linhas totais e `90` por zona eleitoral.
- Qualidade apos backfill:
  - scorecard atualizado em `data/reports/data_coverage_scorecard.json`: `pass=10`, `warn=1`.
  - `backend_readiness`: `READY`, `hard_failures=0`, `warnings=0`.
  - `indicator_distinct_periods`: `5` (`pass`) e `implemented_runs_success_pct_7d`: `95.36` (`pass`).
  - `implemented_connectors_pct`: `91.67` (`warn`) por entrada de 2 conectores sociais em `partial`.
- Sprint D0 da trilha de robustez maxima concluido:
  - `BD-001`: DoD de robustez maxima oficializado no `docs/CONTRATO.md`.
  - `BD-002`: scorecard SQL versionado em `ops.v_data_coverage_scorecard` + export em `scripts/export_data_coverage_scorecard.py`.
  - `BD-003`: runbook semanal publicado em `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`.
  - baseline semanal gerado em `data/reports/data_coverage_scorecard.json`.
- Sprint D1 concluido:
  - `BD-010`: historico TSE carregado para `2024,2022,2020,2018,2016`.
  - `BD-011`: checks de integridade de `electoral_zone` ativos (`count`, `orphans`, `canonical_key`).
  - `BD-012`: checks de continuidade temporal ativos (`max_year_gap` e `source_periods_*`).
  - aceite D1 atendido:
    - `fact_electorate` com `>=5` anos (`pass`).
    - `fact_election_result` com `>=5` anos (`pass`).
    - cobertura de `electoral_zone` em `pass` sem excecao.
- Sprint D2 iniciado com entrega tecnica base:
  - migration `db/sql/008_social_domain.sql` com:
    - `silver.fact_social_protection`
    - `silver.fact_social_assistance_network`
  - conectores sociais implementados:
    - `cecad_social_protection_fetch`
    - `censo_suas_fetch`
  - helper comum criado em `src/pipelines/common/social_tabular_connector.py`.
  - endpoints sociais publicados:
    - `GET /v1/social/protection`
    - `GET /v1/social/assistance-network`
  - checks sociais adicionados no `quality_suite`.
  - status atual dos conectores sociais em `ops.connector_registry`: `partial` (aguardando fonte governada estavel).
  - paths de fallback manual para ativacao controlada:
    - `data/manual/cecad/`
    - `data/manual/censo_suas/`
- Sprint D2 consolidado com ciclo operacional social:
  - comando executado:
    - `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --include-wave6 --indicator-periods 2014,2015,2016,2017 --output-json data/reports/robustness_backfill_report.json`.
  - resultado:
    - `censo_suas_fetch`: `success` em `2014..2017`.
    - `cecad_social_protection_fetch`: `blocked` em `2014..2017` (esperado sem acesso governado).
  - estado de dados apos ciclo:
    - `silver.fact_social_assistance_network`: `4` linhas (`2014..2017`).
    - `silver.fact_social_protection`: `0` linhas (pendencia externa de acesso CECAD).
  - cobertura e readiness revalidados:
    - `data/reports/data_coverage_scorecard.json`: `pass=10`, `warn=1`.
    - `scripts/backend_readiness.py --output-json`: `READY`, `hard_failures=0`, `warnings=0`.
- Encaminhamento:
  - D2 fechado tecnicamente com ressalva de governanca CECAD.
  - frente ativa passa para D3 (`BD-030`, `BD-031`, `BD-032`) com foco em vias, POIs e geocodificacao local.
- Sprint D3 iniciado com incremento tecnico base (backend):
  - migration `db/sql/009_urban_domain.sql` aplicada com objetos:
    - `map.urban_road_segment`
    - `map.urban_poi`
    - `map.v_urban_data_coverage`
  - novos endpoints urbanos publicados:
    - `GET /v1/map/urban/roads`
    - `GET /v1/map/urban/pois`
    - `GET /v1/map/urban/nearby-pois`
  - validacao tecnica:
    - `scripts/init_db.py`: `Applied 9 SQL scripts`.
    - `pytest (contracts + api_contract)`: `18 passed`.
    - `backend_readiness`: `READY`, `hard_failures=0`, `warnings=0`.
- Sprint D3 avancado para ingestao e geocodificacao local (2026-02-19):
  - conectores urbanos implementados e integrados:
    - `urban_roads_fetch` (`src/pipelines/urban_roads.py`)
    - `urban_pois_fetch` (`src/pipelines/urban_pois.py`)
  - catalogos urbanos adicionados:
    - `configs/urban_roads_catalog.yml`
    - `configs/urban_pois_catalog.yml`
  - orquestracao atualizada:
    - `run_mvp_all` inclui jobs urbanos.
    - novo fluxo `run_mvp_wave_7`.
    - `configs/jobs.yml` e `configs/waves.yml` incluem `MVP-7`.
    - `scripts/backfill_robust_database.py` com flag `--include-wave7`.
  - API urbana ampliada:
    - novo endpoint `GET /v1/map/urban/geocode`.
  - qualidade ampliada:
    - `quality_suite` executa `check_urban_domain`.
    - thresholds urbanos em `configs/quality_thresholds.yml`.
  - scorecard de cobertura ampliado:
    - `urban_road_rows` e `urban_poi_rows` em `ops.v_data_coverage_scorecard`.
  - validacao deste incremento:
    - `pytest` focado em connectors/map/quality/flows/contracts: `40 passed`.
  - benchmark de performance para fechamento de `BD-032` executado:
    - `scripts/benchmark_api.py` com suites `executive`, `urban` e `all`.
    - suite `urban` mede p95 dos endpoints:
      - `/v1/map/urban/roads`
      - `/v1/map/urban/pois`
      - `/v1/map/urban/nearby-pois`
      - `/v1/map/urban/geocode`
    - comando de evidencia:
      - `python scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json`
    - resultado atual:
      - `ALL PASS` com p95 `< 1.0s` para todos os endpoints urbanos.
  - carga urbana real (D3) executada e validada:
    - `urban_roads_fetch(2026)`: `success`, `rows_written=6550`.
    - `urban_pois_fetch(2026)`: `success`, `rows_written=319`.
    - `backend_readiness --output-json`: `READY`, `hard_failures=0`, `warnings=0`.
  - `BD-033` iniciado no frontend para UX de navegacao:
    - `QgMapPage` com seletor de mapa base (`Ruas`, `Claro`, `Sem base`).
    - `VectorMap` com suporte a basemap raster por baixo das camadas MVT.
    - overrides por ambiente em `frontend/.env.example`:
      - `VITE_MAP_BASEMAP_STREETS_URL`
      - `VITE_MAP_BASEMAP_LIGHT_URL`

## Governanca documental consolidada (2026-02-13)

1. `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` passa a ser somente visao estrategica do produto.
2. `docs/PLANO_IMPLEMENTACAO_QG.md` permanece como fonte unica de execucao e prioridade.
3. `HANDOFF.md` permanece como estado operacional corrente + proximos passos imediatos.
4. Specs estrategicas promovidas a v1.0 com fases concluidas marcadas:
   - `MAP_PLATFORM_SPEC.md` (MP-1, MP-2 e MP-3 baseline concluidos)
   - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` (TL-1, TL-2 e TL-3 baseline concluidos)
   - `STRATEGIC_ENGINE_SPEC.md` (SE-1 e SE-2 concluidos)
5. Matriz detalhada de rastreabilidade (item a item da evolucao) publicada em:
   - `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`
6. Classificacao de referencia complementar:
   - `docs/FRONTEND_SPEC.md` = referencia de produto/UX para debate.
   - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` = catalogo/priorizacao de fontes (nao status operacional diario).

## Atualizacao tecnica (2026-02-13)

### Sprint 9 - territorial layers TL-2/TL-3 + base eleitoral (iteracao atual)
- **Camadas territoriais com rastreabilidade operacional**:
  - `GET /v1/map/layers/coverage` e `GET /v1/map/layers/{layer_id}/metadata` publicados.
  - `GET /v1/territory/layers/*` publicado para catalogo, cobertura, metadata e readiness.
  - readiness combina catalogo + cobertura + checks do `quality_suite` para visao tecnica unica.
  - camada `territory_polling_place` adicionada no catalogo MVT como ponto eleitoral derivado.
- **Admin/ops com pagina dedicada para camadas**:
  - nova rota `/ops/layers` com filtros por metrica/periodo e tabela de readiness por camada.
  - `AdminHubPage` atualizado com atalho direto para a pagina de camadas.
  - `QgMapPage` com seletor explicito de camada de secao (incluindo `Locais de votacao`) para controle manual no fluxo executivo.
  - `QgMapPage` passa a respeitar `layer_id` por query string no carregamento inicial.
  - `QgOverviewPage` passa a propagar `layer_id` nos links para `/mapa` (atalho principal e cards Onda B/C), via seletor `Camada detalhada (Mapa)`.
- **Quality suite com checks de camada**:
  - checks de volume e geometria por nivel (`map_layer_rows_*` e `map_layer_geometry_ratio_*`) integrados.
  - thresholds dedicados em `configs/quality_thresholds.yml`.
- **Pipeline TSE resultados evoluido para base eleitoral territorial**:
  - parse de zona/secao eleitoral (quando colunas existirem no arquivo oficial).
  - deteccao de `local_votacao` (quando disponivel) como metadata preparatoria da secao.
  - upsert de `electoral_zone` e `electoral_section` em `silver.dim_territory`.
  - `fact_election_result` agora resolve `territory_id` em ordem secao > zona > municipio.
- **Validacoes da iteracao**:
  - backend: testes de `tse_results`, `mvt_tiles` e `quality_core_checks` passando.
  - frontend: `QgPages.test.tsx` passando apos incluir seletor de camada; build Vite passando.

### Sprint 8 - Vector engine MP-3 + Strategic engine SE-2 (iteracao anterior)
- **MapLibre GL JS + VectorMap** (`VectorMap.tsx`):
  - Componente MVT-first (~280 linhas) com 4 viz modes: coroplético, pontos, heatmap, hotspots.
  - Auto layer switch por zoom, seleção de território, estilo local-first.
  - Integrado no QgMapPage com fallback SVG (ChoroplethMiniMap).
- **Multi-level geometry simplification** (`routes_map.py`):
  - 5 faixas de tolerância por zoom (0.05 → 0.0001).
  - Substituiu fórmula genérica por bandas discretas.
- **MVT cache ETag + latency metrics**:
  - ETag MD5 + If-None-Match 304 + header X-Tile-Ms.
  - Endpoint `GET /v1/map/tiles/metrics` com p50/p95/p99.
- **Strategic engine config SE-2** (`configs/strategic_engine.yml`):
  - Thresholds, severity_weights, limites externalizados em YAML.
  - `score_to_status()` + `status_impact()` config-driven (não mais hardcoded).
  - SQL CASE parametrizado + `config_version` em todas as respostas QgMetadata.
- **Spatial GIST index**: `idx_dim_territory_geometry` adicionado.
- Validações:
  - backend: 246 testes passando (+33 vs Sprint 7).
  - frontend: 59 testes passando em 18 arquivos.
  - build Vite: OK.
  - 26 endpoints totais.

### Sprint 7 - UX evolution + map platform MP-2 (iteracao anterior)
- **Layout B: mapa dominante na Home**:
  - QgOverviewPage reescrito com ChoroplethMiniMap dominante + sidebar overlay com glassmorphism.
  - Barra de estatisticas flutuante (criticos/atencao/monitorados), toggle sidebar.
  - Labels encurtados: Aplicar, Prioridades, Mapa detalhado, Territorio critico.
- **Drawer lateral reutilizavel** (`Drawer.tsx`):
  - Componente slide-in left/right, escape key, backdrop click, aria-modal, foco automatico.
- **Zustand para estado global** (`filterStore.ts`):
  - Store compartilhado: period, level, metric, zoom.
  - Integrado na Home e pronto para uso cross-page.
- **MapDominantLayout** (`MapDominantLayout.tsx`):
  - Layout wrapper: mapa full-viewport + sidebar colapsavel, responsivo.
- **MVT tiles endpoint (MP-2)**:
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt` via PostGIS ST_AsMVT.
  - Dois caminhos SQL: com join de indicador ou geometria pura.
  - Filtro por domain, tolerancia adaptativa por zoom, Cache-Control 1h.
  - 25 endpoints totais (11 QG + 10 ops + 1 geo + 2 map + 1 MVT).
- **Auto layer switch por zoom** (`useAutoLayerSwitch.ts`):
  - Hook que seleciona camada pelo zoom_min/zoom_max do manifesto /v1/map/layers.
  - Controle de zoom (range slider) integrado no QgMapPage.
- Validacoes:
  - backend: 213 testes passando (+6 MVT).
  - frontend: 59 testes passando, 18 arquivos (+16 testes vs Sprint 6).
  - build Vite: OK (1.51s).

### Sprint 6 - go-live v1.0 closure (iteracao anterior)
- Contrato v1.0 congelado (`CONTRATO.md`):
  - 24 endpoints formalizados (11 QG + 10 ops + 1 geo + 2 map).
  - SLO-2 bifurcado: operacional (p95 <= 1.5s) e executivo (p95 <= 800ms).
  - Secao 12.1 com tabela de ferramentas (homologation_check, benchmark_api, backend_readiness, quality_suite).
- Runbook de operacoes (`OPERATIONS_RUNBOOK.md`):
  - 12 secoes cobrindo todo ciclo de vida: ambiente, pipelines, qualidade, views, API, frontend, go-live, testes, troubleshooting, conectores especiais, deploy (11 passos + rollback).
- Specs v0.1 → v1.0:
  - `MAP_PLATFORM_SPEC.md`: MP-1 CONCLUIDO (manifesto, style-metadata, cache, fallback).
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`: TL-1 CONCLUIDO (is_official, badge, coverage_note).
  - `STRATEGIC_ENGINE_SPEC.md`: SE-1 CONCLUIDO (score/severity/rationale/evidence, simulacao, briefs).
- Matriz de rastreabilidade atualizada:
  - O6-03 → OK (progressive disclosure), O8-02 → OK (admin diagnostics 7 paineis), D01 → OK (contrato v1.0).
- Validacoes:
  - backend: 207 testes passando.
  - frontend: 43 testes passando, 15 arquivos.
  - build Vite: OK.

### Sprint 5.3 - go-live readiness (iteracao anterior)
- Thresholds de qualidade por dominio/fonte:
  - 15 fontes com `min_rows` explicito em `quality_thresholds.yml` (incluindo DATASUS, INEP, SICONFI, MTE, TSE).
  - MVP-5 sources elevados de 0→1.
  - `quality.py`: 15 fontes checadas em `source_rows`, 14 jobs em `ops_pipeline_runs`.
- Script de homologacao consolidado (`scripts/homologation_check.py`):
  - 5 dimensoes: backend readiness, quality suite, frontend build, test suites, API smoke.
  - Verdict unico READY/NOT READY com suporte `--json` e `--strict`.
- Progressive disclosure na Home (QgOverviewPage):
  - `CollapsiblePanel` component com chevron, badge count, `aria-expanded`.
  - "Dominios Onda B/C" colapsado por padrao; "KPIs executivos" expandido.
- Admin diagnostics refinement (OpsHealthPage):
  - 3 paineis colapsaveis adicionados: Quality checks, Cobertura de fontes, Registro de conectores.
- Validacoes:
  - backend: 207 testes passando.
  - frontend: 43 testes passando, 15 arquivos.
  - build Vite: OK.

### Sprint 5.2 - acessibilidade e hardening (iteracao anterior)
- Benchmark de performance da API criado:
  - `scripts/benchmark_api.py`: p50/p95/p99 em 12 endpoints, alvo p95<=800ms.
- Edge-case contract tests adicionados:
  - `tests/unit/test_qg_edge_cases.py`: 44 testes (validacao de nivel, limites, dados vazios, request_id, content-type).
- Badge de classificacao de fonte (P05):
  - `source_classification` no backend (oficial/proxy/misto) + badge no frontend.
- Persistencia de sessao (O7-05):
  - `usePersistedFormState` hook com prioridade queryString > localStorage > defaults.
  - integrado em Cenarios (6 campos) e Briefs (5 campos).
- Accessibility hardening (Sprint 5.2 item 1):
  - `Panel`: `aria-labelledby` vinculado ao titulo via `useId`.
  - `StateBlock`: `role=alert/status` + `aria-live`.
  - `StrategicIndexCard`: `aria-label` no article e status.
  - Paginas executivas: `<main>` no lugar de `<div>`, tabelas com `aria-label`, botoes com `aria-label` contextual.
  - Ranking territorial: linhas com keyboard support (tabIndex, onKeyDown, role=button).
  - Quick-actions: `<nav aria-label>`.
- Validacoes desta iteracao:
  - backend: 207 testes passando (pytest).
  - frontend: 43 testes passando (vitest), 15 arquivos.
  - build Vite: OK.

### Sprint 5 - hardening (iteracao anterior)
- E2E do fluxo critico de decisao implementado:
  - `frontend/src/app/e2e-flow.test.tsx` com 5 testes: fluxo principal completo + 3 deep-links + admin→executivo.
  - cobertura: Home → Prioridades → Mapa → Territorio 360 → Eleitorado → Cenarios → Briefs.
- Cache HTTP ativo nos endpoints criticos:
  - `CacheHeaderMiddleware` com Cache-Control, weak ETag e 304 condicional.
  - endpoints cobertos: map/layers, map/style-metadata, kpis, priority, insights, choropleth, electorate, territory.
- Materialized views criadas para ranking e mapa:
  - `db/sql/006_materialized_views.sql`: 3 MVs com refresh concorrente.
  - geometria simplificada via `ST_SimplifyPreserveTopology` na MV de mapa.
- Indices espaciais GIST adicionados:
  - `db/sql/007_spatial_indexes.sql`: GIST, GIN trigram, covering index.
- Admin readiness integrado:
  - `AdminHubPage.tsx` exibe ReadinessBanner com status consolidado de `GET /v1/ops/readiness`.
- Validacoes desta iteracao:
  - backend: 163 testes passando (pytest).
  - frontend: 43 testes passando (vitest), 15 arquivos.
  - build Vite: OK.

### MP-1 (entregue anteriormente nesta data)
- MP-1 do mapa executado no backend/frontend:
  - `QgMapPage` integrado ao manifesto para exibir recomendacao de camada por nivel (`municipio`/`distrito`).
  - fallback preservado para `GET /v1/geo/choropleth`, sem interrupcao da pagina quando o manifesto falhar.
- MP-1 estendido com metadados de estilo:
  - endpoint `GET /v1/map/style-metadata` ativo com modo padrao, paleta de severidade e ranges de legenda.
  - `QgMapPage` integrado para exibir contexto visual de estilo sem acoplar a renderizacao ao backend.
- Validacoes desta iteracao:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `6 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `38 passed`.
  - `npm --prefix frontend run build`: `OK`.

## Atualizacao rapida (2026-02-12)

- Backend funcionalmente pronto para avancar no frontend (API + pipelines + checks + scripts operacionais).
- Sprint 0 do QG iniciado no backend com contratos de API para Home/Prioridades/Insights:
  - `GET /v1/kpis/overview`
  - `GET /v1/priority/list`
  - `GET /v1/priority/summary`
  - `GET /v1/insights/highlights`
- Sprint 2 do QG avancou no backend com contratos de API para Perfil/Comparacao e Eleitorado executivo:
  - `GET /v1/territory/{id}/profile`
  - `GET /v1/territory/{id}/compare`
  - `GET /v1/electorate/summary`
  - `GET /v1/electorate/map`
- Extensao v1.1 iniciada no backend:
  - `POST /v1/scenarios/simulate` (simulacao simplificada por variacao percentual).
  - simulacao evoluida para calcular ranking antes/depois por indicador e delta de posicao.
  - `POST /v1/briefs` para geracao de brief executivo com resumo e evidencias.
- Sprint 3/4 (Onda A) iniciado no backend:
  - `sidra_indicators_fetch` evoluido para ingestao real via SIDRA API (`implemented`).
  - `senatran_fleet_fetch` evoluido para ingestao real tabular (`implemented`).
  - `sejusp_public_safety_fetch` evoluido para ingestao real tabular (`implemented`).
  - `siops_health_finance_fetch` evoluido para ingestao real tabular (`implemented`).
  - `snis_sanitation_fetch` evoluido para ingestao real tabular (`implemented`).
  - Onda A de conectores concluida no backend em modo implementado.
  - todos integrados no orquestrador em `run_mvp_wave_4` e `run_mvp_all`.
- Sprint 6 tecnico (Onda B/C) iniciado no backend:
  - novos conectores integrados:
    - `inmet_climate_fetch`
    - `inpe_queimadas_fetch`
    - `ana_hydrology_fetch`
    - `anatel_connectivity_fetch`
    - `aneel_energy_fetch`
  - todos integrados no orquestrador em `run_mvp_wave_5` e `run_mvp_all`.
  - padrao de execucao igual aos conectores Onda A:
    - remote catalog quando disponivel
    - fallback manual por diretorio dedicado em `data/manual/*`
    - Bronze + checks + `ops.pipeline_runs/pipeline_checks` + upsert em `silver.fact_indicator`.
  - `scripts/bootstrap_manual_sources.py` ampliado para Onda B/C:
    - novas opcoes de bootstrap: `INMET`, `INPE_QUEIMADAS`, `ANA`, `ANATEL`, `ANEEL`.
    - parser tabular generico por catalogo com tentativa de filtro municipal automatico.
    - parser CSV/TXT endurecido com selecao automatica do melhor delimitador.
    - selecao de entrada ZIP por nome do municipio quando disponivel.
    - deteccao do cabecalho INMET (`Data;Hora UTC;...`) para leitura correta da serie horaria.
    - fallback de recorte municipal por nome de arquivo quando o payload nao traz colunas de municipio.
    - quando nao for possivel consolidar recorte municipal de forma confiavel, retorna `manual_required`
      no relatorio, mantendo rastreabilidade dos links/arquivos tentados.
  - validacao local do bootstrap Onda B/C executada sem erro de processo:
    - `INMET`/`INPE_QUEIMADAS`: consolidacao municipal automatica validada com status `ok`
      e geracao de arquivos em `data/manual/inmet` e `data/manual/inpe_queimadas`.
    - `ANATEL`/`ANEEL`: consolidacao municipal automatica validada com status `ok`
      e geracao de arquivos em `data/manual/anatel` e `data/manual/aneel`.
    - `ANA`: consolidacao municipal automatica validada com status `ok`
      e geracao de arquivo em `data/manual/ana`.
  - catalogos remotos oficiais configurados:
    - `ANATEL`: `meu_municipio.zip` (acessos/densidade por municipio).
    - `ANEEL`: `indger-dados-comerciais.csv` (dados comerciais por municipio).
    - `ANA`: download oficial via ArcGIS Hub (`api/download/v1/items/.../csv?layers=18`)
      com fallback para endpoints ArcGIS (`www.snirh.gov.br` e `portal1.snirh.gov.br`).
  - `ANEEL` foi ajustado para `prefer_manual_first` no conector, reduzindo custo de execucao
    local quando o CSV municipal consolidado ja existe em `data/manual/aneel`.
  - estado de rede atual para `ANA` no ambiente local:
    - hosts SNIRH seguem instaveis (`ConnectTimeout`) em algumas tentativas;
    - coleta automatica segue funcional via URL ArcGIS Hub e fallback manual permanece disponivel.
  - validacao de fluxo `run_mvp_wave_5` (referencia 2025, `dry_run=False`):
    - `success`: `inmet_climate_fetch`, `inpe_queimadas_fetch`, `anatel_connectivity_fetch`, `aneel_energy_fetch`.
    - `blocked`: `ana_hydrology_fetch` (timeout remoto + sem arquivo em `data/manual/ana`).
  - mapeamento de dominio QG atualizado para as novas fontes
    (`clima`, `meio_ambiente`, `recursos_hidricos`, `conectividade`, `energia`).
- Frontend integrado ao novo contrato QG:
  - rota inicial (`/`) com `QgOverviewPage` consumindo `kpis/overview`, `priority/summary` e `insights/highlights`.
  - rota `prioridades` com `QgPrioritiesPage` consumindo `priority/list`.
  - rota `mapa` com `QgMapPage` consumindo `geo/choropleth`.
  - `mapa` agora possui visualizacao geografica simplificada (SVG) com escala de valor e selecao de territorio.
  - rota `insights` com `QgInsightsPage` consumindo `insights/highlights`.
  - rota `cenarios` com `QgScenariosPage` consumindo `POST /v1/scenarios/simulate`.
  - tela de cenarios passou a exibir score e ranking antes/depois com impacto estimado.
  - rota `briefs` com `QgBriefsPage` consumindo `POST /v1/briefs`.
  - Home QG passou a exibir `Top prioridades` (previsualizacao) e `Acoes rapidas` para fluxo de decisao.
  - acao `Ver no mapa` da Home passou a abrir diretamente o recorte da prioridade mais critica.
  - `Territorio 360` passou a oferecer atalhos para `briefs` e `cenarios` com territorio/periodo pre-preenchidos.
  - `QgBriefsPage` e `QgScenariosPage` passaram a aceitar query string para prefill de filtros.
  - `QgPrioritiesPage` passou a oferecer ordenacao local e exportacao CSV da lista priorizada.
  - `PriorityItemCard` ganhou deep-link `Ver no mapa` para recorte de indicador/periodo/territorio.
  - `QgMapPage` passou a aceitar query string para prefill de filtros e selecao territorial inicial.
  - `QgMapPage` ganhou exportacao CSV do ranking territorial.
  - `QgMapPage` ganhou exportacao visual do mapa em `SVG` e `PNG`.
  - endpoint `GET /v1/territory/{id}/profile` evoluiu com score/status/tendencia agregados do territorio:
    - `overall_score`
    - `overall_status`
    - `overall_trend`
  - `TerritoryProfilePage` passou a exibir card executivo de status geral com score consolidado e tendencia.
  - endpoint `GET /v1/territory/{id}/peers` adicionado para sugerir comparacoes por similaridade de indicadores.
  - `TerritoryProfilePage` passou a exibir painel de pares recomendados com acao direta `Comparar`.
  - `QgBriefsPage` passou a suportar exportacao do brief em `HTML` e impressao para `PDF` pelo navegador.
  - rota `territorio/perfil` (alias legado: `territory/profile`) com `TerritoryProfilePage` (profile + compare).
  - rota dinamica `territorio/:territoryId` (alias legado: `territory/:territoryId`) com `TerritoryProfileRoutePage`.
  - rota `eleitorado` (alias legado: `electorate/executive`) com `ElectorateExecutivePage` (summary + map).
  - links de contexto (`Abrir perfil`) adicionados em `Mapa` e `Prioridades` para navegação direta ao perfil territorial.
  - rota `admin` adicionada como hub tecnico, separando links operacionais (`ops/*`) do menu principal executivo.
  - metadados de fonte/atualizacao/cobertura expostos nas telas executivas com `SourceFreshnessBadge`.
  - Home QG evoluida para usar `StrategicIndexCard` na secao de situacao geral.
  - lista de prioridades evoluida para `PriorityItemCard` (cards com score, racional, evidencia e acao).
  - cliente dedicado em `frontend/src/shared/api/qg.ts` e tipagens QG em `frontend/src/shared/api/types.ts`.
  - cobertura de teste de pagina adicionada para fluxo QG em:
    - `frontend/src/modules/qg/pages/QgPages.test.tsx`
    - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
    - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - wrappers de teste com `MemoryRouter` adicionados nas paginas com navegacao interna.
  - testes QG ampliados para validar prefill por query string no mapa e deep-links de prioridade.
- Hardening frontend (Sprint 5) iniciado:
  - acessibilidade minima no shell: `skip link` para conteudo principal e foco visivel padronizado.
  - foco programatico no conteudo principal (`main`) em trocas de rota.
  - observabilidade basica frontend:
    - captura de `window.error` e `unhandledrejection`.
    - captura de metricas de performance/web-vitals (paint, LCP, CLS e navigation timing).
    - evento de navegacao por troca de rota (`route_change`).
  - endpoint de telemetria configuravel por `VITE_FRONTEND_OBSERVABILITY_URL`.
  - endpoint tecnico para cobertura de dados por fonte:
    - `GET /v1/ops/source-coverage` (runs por fonte + `rows_loaded` + `fact_indicator_rows` + `coverage_status`).
  - cliente HTTP passou a emitir telemetria de chamadas API:
    - `api_request_success`
    - `api_request_retry`
    - `api_request_failed`
    com `method`, `path`, `status`, `request_id`, `duration_ms` e tentativas.
- Validacao frontend:
  - `npm --prefix frontend run typecheck`: `OK`.
  - `npm --prefix frontend run typecheck` (apos telemetria de API no cliente HTTP): `OK`.
  - `npm --prefix frontend run typecheck` (apos hardening de a11y/observabilidade): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao SVG/PNG): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao de briefs HTML/PDF): `OK`.
  - `npm --prefix frontend run test`: `14 passed` / `33 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido).
  - `RouterProvider` e testes com `MemoryRouter` atualizados com `future flags` do React Router v7.
- Validacao backend do contrato QG:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `15 passed`.
- Router QG integrado ao app em `src/app/api/main.py`.
- Schemas dedicados do QG adicionados em `src/app/schemas/qg.py`.
- Testes unitarios de contrato do QG adicionados em `tests/unit/test_qg_routes.py` e validados.
  - estado atual local: `14 passed` (incluindo cenarios e briefs).
- Testes de orquestracao e conectores Onda A adicionados/atualizados:
  - `tests/unit/test_prefect_wave3_flow.py`
  - `tests/unit/test_onda_a_connectors.py`
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - validacao local: `35 passed` em `test_onda_a_connectors + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_qg_routes`.
  - validacao local consolidada: `62 passed` em
    `test_qg_routes + test_onda_a_connectors + test_quality_core_checks + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_ops_routes`.
- Hardening aplicado no backend:
  - alias `run_status` em `/v1/ops/pipeline-runs` (compatibilidade com `status`).
  - check `source_probe_rows` no `quality_suite` com threshold versionado.
  - checks de cobertura por fonte Onda A no `quality_suite` (SIDRA, SENATRAN, SEJUSP_MG, SIOPS e SNIS)
    por `reference_period`.
  - thresholds da `fact_indicator` calibrados com minimo de linhas por fonte Onda A.
  - novos indices SQL incrementais para consultas QG/OPS em `db/sql/004_qg_ops_indexes.sql`.
  - telemetria frontend persistida no backend:
    - `POST /v1/ops/frontend-events` (ingestao)
    - `GET /v1/ops/frontend-events` (consulta paginada)
    - tabela `ops.frontend_events` em `db/sql/005_frontend_observability.sql`.
  - scripts de operacao: readiness, backfill de checks e cleanup de legados.
  - `dbt_build` persiste check de falha em `ops.pipeline_checks` quando run falha.
  - logging robusto para execucao local em Windows (sem quebra por encoding).
- Estado operacional atual do backend:
  - `scripts/backend_readiness.py --output-json` retorna `READY` com `hard_failures=0` e `warnings=1`.
  - `SLO-3` atendido na janela operacional de 7 dias no ambiente local.
  - `SLO-1` segue em warning historico (`72.31% < 95%`) por runs antigos.
- Pesquisa de fontes futuras concluida e consolidada em:
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - priorizacao por ondas, complexidade e impacto para o municipio de Diamantina.
- Frontend F2 (operacao) evoluido:
  - filtros de `runs`, `checks` e `connectors` com aplicacao explicita via botao.
  - botao `Limpar` nos formularios de filtros.
  - contrato de filtro de runs alinhado para `run_status`.
  - nova tela tecnica `/ops/frontend-events` com filtros/paginacao para telemetria do frontend.
  - nova tela tecnica `/ops/source-coverage` para auditar disponibilidade real de dados por fonte.
  - `OpsHealthPage` passou a exibir monitor comparativo de SLO-1:
    - taxa agregada e jobs abaixo da meta em janela historica (7d).
    - taxa agregada e jobs abaixo da meta em janela corrente (1d).
  - `OpsHealthPage` passou a consumir `GET /v1/ops/readiness` para status consolidado
    (`READY|NOT_READY`), `hard_failures` e `warnings`, reduzindo divergencia entre
    script de readiness e leitura de saude no frontend.
  - filtros de wave em `ops` atualizados para incluir `MVP-5`.
  - testes de paginas ops adicionados em `frontend/src/modules/ops/pages/OpsPages.test.tsx`.
- Endpoint tecnico de readiness operacional adicionado:
  - `GET /v1/ops/readiness`
  - parametros: `window_days`, `health_window_days`, `slo1_target_pct`,
    `include_blocked_as_success`, `strict`.
  - nucleo compartilhado de calculo em `src/app/ops_readiness.py`,
    reutilizado tambem por `scripts/backend_readiness.py`.
- Frontend F3 (territorio e indicadores) evoluido:
  - filtros territoriais com paginacao e aplicacao explicita.
  - selecao de territorio para compor filtro de indicadores.
  - filtros de indicadores ampliados (periodo, codigo, fonte, dataset, territorio).
  - melhorias de responsividade de tabelas.
  - testes adicionados em `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`.
- Frontend F4 (hardening) evoluido:
  - lazy-loading nas rotas principais (`ops` e `territory`) com fallback de carregamento.
  - smoke test de navegacao ponta a ponta no frontend:
    `frontend/src/app/router.smoke.test.tsx`.
  - build com chunks por pagina confirmado em `dist/assets/*Page-*.js`.
- Bloqueador de fechamento total da Fase 2:
  - sem bloqueador tecnico pendente de backend no estado atual.
  - observacao operacional: validacoes de `dbt` no Windows podem exigir terminal elevado por politica local
    de permissao (WinError 5).
  - observacao operacional adicional: no ambiente atual, `vitest` e `vite build` executaram sem falhas.

## Atualizacao operacional (2026-02-12)

- Filtros de dominio no fluxo QG padronizados no frontend:
  - `Prioridades`, `Insights`, `Briefs` e `Cenarios` agora usam `select` com catalogo unico.
  - normalizacao de dominio por query string (`normalizeQgDomain`) aplicada para evitar estados invalidos.
  - `Prioridades` e `Insights` agora carregam filtros iniciais a partir de query string (deep-links funcionais).
  - arquivo de referencia compartilhada: `frontend/src/modules/qg/domainCatalog.ts`.
- Refinamento de experiencia no QG:
  - dominios agora sao exibidos com rotulos amigaveis para leitura executiva (`getQgDomainLabel`).
  - codigos de dominio permanecem inalterados no contrato tecnico (query string/API), preservando compatibilidade.
- `Territorio 360` alinhado ao padrao de UX do QG para dominio:
  - `TerritoryProfilePage` agora exibe rotulos amigaveis de dominio tambem nas tabelas de indicadores e comparacao.
- Home executiva do QG atualizada para refletir Onda B/C no frontend:
  - novo painel `Dominios Onda B/C` na `QgOverviewPage` com atalhos de navegacao para `Prioridades` e `Mapa` por dominio.
  - catalogo de dominios/fonte/metrica padrao centralizado em `frontend/src/modules/qg/domainCatalog.ts`.
- Contrato de `GET /v1/kpis/overview` evoluido com rastreabilidade de origem:
  - `KpiOverviewItem` agora inclui `source` e `dataset` (backend + frontend).
  - tabela `KPIs executivos` na Home passou a exibir coluna `Fonte`.
- Testes de regressao frontend reestabilizados apos a evolucao da Home:
  - `QgPages.test.tsx` e `router.smoke.test.tsx` atualizados para novo shape e novos links.
  - comportamento de filtros da Home mantido com aplicacao explicita via submit.
- Validacao executada em 2026-02-12 (ciclo atual):
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `38 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (inclui padronizacao de filtros de dominio e deep-links de `Prioridades`/`Insights`).
  - `npm --prefix frontend run build`: `OK` (Vite build concluido com filtros padronizados + prefill por query string).
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos rotulos amigaveis de dominio no QG).
  - `npm --prefix frontend run build`: `OK` (revalidado apos refinamento de UX de dominio).
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos padronizacao de rotulos no `TerritoryProfilePage`).
  - `npm --prefix frontend run build`: `OK` (revalidado apos ajuste no `TerritoryProfilePage`).
- Saneamento operacional executado:
  - `scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply` executado com sucesso.
  - 6 runs sem check foram corrigidos; `SLO-3` voltou a conformidade (`runs_missing_checks=0`).
- Registry de conectores sincronizado:
  - `scripts/sync_connector_registry.py` executado com sucesso.
  - `ops.connector_registry` atualizado para `22` conectores `implemented` (incluindo `MVP-5`).
- Ondas executadas com sucesso em modo real:
  - `run_mvp_wave_4(reference_period='2025', dry_run=False)`: todos os jobs `success`.
  - `run_mvp_wave_5(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- Execucoes direcionadas adicionais:
  - `tse_electorate_fetch`: `success`.
  - `labor_mte_fetch`: `success` (via `bronze_cache`).
  - `ana_hydrology_fetch`: `success` (via ArcGIS Hub CSV).
  - `quality_suite(reference_period='2025')`: `success` (0 fails; 1 warn).
- Readiness atual:
  - `scripts/backend_readiness.py --output-json` => `READY`.
  - `hard_failures=0`.
  - `warnings=1` por `SLO-1` historico na janela de 7 dias (`72.31% < 95%`).
  - script de readiness evoluido para separar leitura historica e saude corrente:
    - novo parametro `--health-window-days` (default `1`).
    - novo bloco `slo1_current` no JSON para diagnostico de estado operacional atual.
    - warning de SLO-1 agora traz contexto combinado (`last 7d` vs janela corrente).
  - observacao: este warning e herdado de runs antigos `blocked/failed`; o estado corrente de execucao das ondas 4 e 5 esta estavel.
- Validacao final executada em 2026-02-12:
  - `pytest -q -p no:cacheprovider`: `152 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `33 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido).
  - warnings de `future flags` do React Router removidos da suite de testes.

## Proximos passos imediatos (apos iteracao readiness API)

1. Expor `GET /v1/ops/readiness` tambem no painel tecnico `/admin` como card de status unico
   para triagem rapida de ambiente.
2. Adicionar teste E2E curto cobrindo o fluxo `OpsHealthPage` com transicao
   `READY -> NOT_READY` por mocks de readiness.
3. Consolidar janela operacional padrao do time (historico x corrente) em `CONTRATO.md`
   para evitar divergencia de leitura entre scripts, API e frontend.
4. Avancar no fechamento de UX/QG (error boundaries por rota + mensagens de estado)
   antes do go-live controlado.

## Proximos passos imediatos (trilha de robustez maxima de dados)

Backlog oficial:
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`

Sprint atual recomendado:
1. Executar Sprint D3 com foco em `BD-030`, `BD-031` e `BD-032`.
2. Publicar schema/indices espaciais para vias e logradouros, com consulta por `bbox`.
3. Publicar camada de POIs essenciais e endpoint de busca espacial por raio/bbox.
4. Manter D2 com ressalva operacional aberta:
   - `cecad_social_protection_fetch` depende de liberacao de acesso governado no CECAD.
5. Para abertura/atualizacao rapida no GitHub:
   - revisar `docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md`;
   - opcionalmente executar
     `powershell -ExecutionPolicy Bypass -File scripts/create_github_issues_backlog_dados.ps1 -Repo vthamada/territorial-intelligence-platform -Apply`.

## 1) O que foi implementado ate agora

### Arquitetura e operacao
- Estrutura por ondas (MVP-1, MVP-2, MVP-3) mantida.
- Bronze/Silver/Gold operacionais com manifestos em `data/manifests/...`.
- `dbt_build` evoluido para modo hibrido:
  - `DBT_BUILD_MODE=auto` tenta `dbt` CLI e faz fallback para `sql_direct`
  - `DBT_BUILD_MODE=dbt` exige `dbt` CLI
  - `DBT_BUILD_MODE=sql_direct` preserva o modo legado
- Persistencia operacional consolidada em:
  - `ops.pipeline_runs`
  - `ops.pipeline_checks`

### API
- Contrato de erro endurecido em `src/app/api/error_handlers.py`:
  - payload padrao `validation_error|http_error|internal_error`
  - cabecalho `x-request-id` garantido em respostas de erro (incluindo 500)
- Novos testes de contrato em `tests/unit/test_api_contract.py`.
- Endpoints de observabilidade operacional adicionados:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary` (agregado por status/wave para runs/checks/connectors)
  - `GET /v1/ops/timeseries` (serie temporal por `runs|checks` em granularidade `day|hour`)
  - `GET /v1/ops/sla` (taxa de sucesso e metricas de duracao por job/wave)
  - filtros + paginacao sobre metadados de `ops.pipeline_runs` e `ops.pipeline_checks`
  - filtros temporais:
    - `pipeline-runs`: `started_from` e `started_to`
    - `pipeline-checks`: `created_from` e `created_to`
    - `connector-registry`: `updated_from` e `updated_to`

### Conectores IBGE e TSE
- Mantidos como implementados e estaveis:
  - IBGE: `ibge_admin_fetch`, `ibge_geometries_fetch`, `ibge_indicators_fetch`
  - TSE: `tse_catalog_discovery`, `tse_electorate_fetch`, `tse_results_fetch`

### MVP-3 (ingestao real)
- `education_inep_fetch`:
  - parse real de ZIP da sinopse INEP
  - localizacao da linha municipal e carga de indicador em `silver.fact_indicator`
- `health_datasus_fetch`:
  - extracao real da API CNES DATASUS com filtro municipal
  - carga de indicadores em `silver.fact_indicator`
- `finance_siconfi_fetch`:
  - extracao real DCA via API SICONFI com fallback de ano
  - carga de indicadores em `silver.fact_indicator`
- `labor_mte_fetch`:
  - conector em modo `implemented`
  - tentativa automatica via FTP `ftp://ftp.mtps.gov.br/pdet/microdados/`
  - fallback automatico via cache Bronze para o mesmo `reference_period`
  - fallback manual por `data/manual/mte` (CSV/TXT/ZIP) apenas em contingencia
  - suporte a derivacao de admissoes/desligamentos/saldo a partir de `saldomovimentacao`
  - configuracao via `.env` para host/porta/raizes/profundidade/limite de varredura FTP
  - persistencia de artefato tabular bruto em Bronze para reuso automatico em execucoes futuras

### Registro de conectores
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` marcado como `implemented`
  - nota operacional com tentativa FTP + cache Bronze + fallback manual de contingencia quando fonte indisponivel
- runbook operacional adicionado em `docs/MTE_RUNBOOK.md`

### Testes e ambiente
- `requirements.txt` adicionado para instalacao no ambiente local.
- Novos testes unitarios:
  - `tests/unit/test_datasus_health.py`
  - `tests/unit/test_inep_education.py`
  - `tests/unit/test_siconfi_finance.py`
  - `tests/unit/test_mte_labor.py`
  - `tests/unit/test_api_contract.py`
  - `tests/unit/test_ops_routes.py`
  - `tests/unit/test_quality_core_checks.py`
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - `tests/unit/test_prefect_wave3_flow.py`
- Testes do `dbt_build` ampliados para validar modo de execucao (`auto|dbt|sql_direct`) em `tests/unit/test_dbt_build.py`.
- Cobertura de orquestracao expandida em `tests/unit/test_prefect_wave3_flow.py` para `run_mvp_wave_3` e `run_mvp_all`.
- Suite validada: `78 passed`.
- Suite unit completa atualizada: `91 passed`.
- Suite unit completa atualizada apos endpoints QG adicionais: `96 passed`.
- Suite de `ops` com summary/timeseries/sla validada: `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider` (`16 passed`).
- Suite de fluxos + ops validada: `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`.
- Suite de `ops` com timeseries validada no mesmo arquivo `tests/unit/test_ops_routes.py`.
- Suite de `ops` com SLA validada no mesmo arquivo `tests/unit/test_ops_routes.py`.
- Suite de `dbt + ops + quality` validada: `pytest -q tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider` (`26 passed`).
- Frontend F1 implementado em `frontend/` com:
  - shell da app (`React Router`)
  - cliente HTTP tipado + `TanStack Query`
  - paginas iniciais de operacao e territorio
  - testes de UI e cliente API (`vitest`)
- Validacoes recentes:
  - `python -m pip check`: sem conflitos
  - `pytest -q -p no:cacheprovider`: `82 passed`
  - `npm run test` (frontend): `7 passed` (validado no terminal do usuario)
  - `npm run build` (frontend): build concluido (validado no terminal do usuario)

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcional.
- Escopo territorial padrao confirmado para Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`) em `settings` e `.env.example`.
- Conectores MVP-1 e MVP-2: `implemented`.
- Conectores MVP-3:
  - INEP, DATASUS, SICONFI: `implemented` com ingestao real.
  - MTE: `implemented`; operacao automatica via FTP com fallback por cache Bronze e fallback manual de contingencia.
- `pip check`: sem dependencias quebradas.
- Frontend:
  - F1 concluido no repositorio (`frontend/`)
  - stack oficial ativa: `React + Vite + TypeScript + React Router + TanStack Query`
  - base de integracao com backend pronta (`/v1/ops/*`, `/v1/territories`, `/v1/indicators`)
  - proximas entregas: F2 (telas operacionais completas), F3 (territorio/indicadores), F4 (hardening)

## 3) Arquivos-chave alterados neste ciclo

- `src/app/api/error_handlers.py`
- `src/pipelines/datasus_health.py`
- `src/pipelines/inep_education.py`
- `src/pipelines/siconfi_finance.py`
- `src/pipelines/mte_labor.py`
- `src/pipelines/sidra_indicators.py`
- `src/pipelines/senatran_fleet.py`
- `src/pipelines/sejusp_public_safety.py`
- `src/pipelines/siops_health_finance.py`
- `src/pipelines/snis_sanitation.py`
- `src/app/api/routes_ops.py`
- `src/app/api/routes_qg.py`
- `src/app/api/main.py`
- `src/pipelines/common/quality.py`
- `src/pipelines/dbt_build.py`
- `src/pipelines/quality_suite.py`
- `src/app/settings.py`
- `.env.example`
- `configs/connectors.yml`
- `configs/sidra_indicators_catalog.yml`
- `configs/senatran_fleet_catalog.yml`
- `configs/sejusp_public_safety_catalog.yml`
- `configs/siops_health_finance_catalog.yml`
- `configs/snis_sanitation_catalog.yml`
- `configs/quality_thresholds.yml`
- `requirements.txt`
- `tests/unit/test_api_contract.py`
- `tests/unit/test_dbt_build.py`
- `tests/unit/test_datasus_health.py`
- `tests/unit/test_inep_education.py`
- `tests/unit/test_siconfi_finance.py`
- `tests/unit/test_mte_labor.py`
- `tests/unit/test_ops_routes.py`
- `tests/unit/test_qg_routes.py`
- `tests/unit/test_quality_ops_pipeline_runs.py`
- `tests/unit/test_prefect_wave3_flow.py`
- `tests/unit/test_onda_a_connectors.py`
- `docs/MTE_RUNBOOK.md`
- `README.md`
- `src/app/schemas/qg.py`
- `frontend/src/shared/api/qg.ts`
- `frontend/src/shared/api/types.ts`
- `frontend/src/modules/admin/pages/AdminHubPage.tsx`
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`
- `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`
- `frontend/src/modules/qg/pages/QgMapPage.tsx`
- `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
- `frontend/src/modules/qg/pages/QgScenariosPage.tsx`
- `frontend/src/modules/qg/pages/QgBriefsPage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfileRoutePage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
- `frontend/src/modules/qg/pages/QgPages.test.tsx`
- `frontend/src/shared/ui/ChoroplethMiniMap.tsx`
- `frontend/src/shared/ui/ChoroplethMiniMap.test.tsx`
- `frontend/src/shared/ui/SourceFreshnessBadge.tsx`
- `frontend/src/shared/ui/SourceFreshnessBadge.test.tsx`
- `frontend/src/shared/ui/StrategicIndexCard.tsx`
- `frontend/src/shared/ui/StrategicIndexCard.test.tsx`
- `frontend/src/shared/ui/PriorityItemCard.tsx`
- `frontend/src/shared/ui/PriorityItemCard.test.tsx`
- `frontend/src/shared/observability/telemetry.ts`
- `frontend/src/shared/observability/bootstrap.ts`
- `frontend/src/shared/observability/telemetry.test.ts`
- `frontend/src/shared/api/http.ts`
- `frontend/src/shared/api/http.test.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/App.test.tsx`
- `frontend/src/app/router.smoke.test.tsx`
- `frontend/src/main.tsx`
- `frontend/.env.example`

## 4) Como operar agora (resumo)

### 4.1 Setup
1. Criar/ativar `.venv`.
2. Instalar dependencias:
   - `pip install -r requirements.txt`
3. Garantir `.env` configurado e banco inicializado:
   - `python scripts/init_db.py`

### 4.2 Validacao rapida
1. `python -m pip check`
2. `pytest -q -p no:cacheprovider`

### 4.3 MTE (fluxo atual)
0. Garantir contexto municipal em `silver.dim_territory` (se ambiente estiver limpo):
   - `python -c "from pipelines.ibge_admin import run; print(run(reference_period='2025', dry_run=False))"`
1. O conector tenta baixar automaticamente via FTP do MTE.
2. Se nao encontrar arquivo via FTP, tenta automaticamente o ultimo artefato tabular valido no Bronze para o mesmo periodo.
3. Se FTP e cache Bronze falharem, usar arquivo manual de Novo CAGED (CSV/TXT/ZIP) em `data/manual/mte`.
4. Executar `labor_mte_fetch`:
   - `dry_run=True` para validar
   - `dry_run=False` para gravar Silver/Bronze/ops
5. Validar criterio P0 (3 execucoes reais consecutivas):
   - `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`
6. Resultado mais recente no ambiente local (2026-02-10): `3/3 success` via `bronze_cache`, sem arquivo manual presente durante a validacao.

## 5) Proximos passos recomendados

### Prioridade alta
1. Rodar suite completa em ambiente limpo e consolidar baseline de regressao.
2. Publicar frontend em homologacao integrado a API real.
3. Planejar kickoff da Onda A de novas fontes apos estabilizacao do frontend.

### Prioridade media
1. Consolidar execucao `dbt` CLI em ambiente alvo (profiles, target e permissao de runtime).
2. Entregar telas frontend de saude operacional e pipelines com dados reais.
3. Expandir checks de qualidade por dominio com thresholds por dataset.
4. Entregar tela frontend de territorios/indicadores com filtros por periodo e nivel.

### Prioridade baixa
1. Hardening de observabilidade (SLA por job e alertas).
2. Revisao de politicas de retencao Bronze por ambiente.

## 6) Comandos uteis

- Testes:
  - `pytest -q -p no:cacheprovider`
- Fluxo completo em dry-run:
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2024', dry_run=True))"`
- Sincronizar registry:
  - `python scripts/sync_connector_registry.py`
- Rodar qualidade:
  - `python -c "from pipelines.quality_suite import run; print(run(reference_period='2024', dry_run=False))"`
- Subir API + frontend no Windows sem `make`:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_up.ps1`
- Encerrar API + frontend iniciados pelo launcher:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_down.ps1`
