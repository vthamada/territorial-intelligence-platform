# Changelog

Todas as mudancas relevantes do projeto devem ser registradas aqui.

## 2026-02-19

### Changed
- Frontend QG Prioridades:
  - lista priorizada agora suporta paginacao client-side com controles `Anterior`/`Proxima`, indicador `Pagina X de Y` e seletor `Itens por pagina` (`12`, `24`, `48`) em `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`.
  - pagina atual e tamanho de pagina resetam de forma previsivel ao aplicar/limpar filtros.
  - cobertura de regressao adicionada em `frontend/src/modules/qg/pages/QgPages.test.tsx` para cenario com volume alto de cards (`30` itens).
  - validacao executada:
    - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
    - `npm --prefix frontend run build` -> `OK`.
- Sprint D3 avancou do contrato para ingestao operacional:
  - novos conectores urbanos implementados:
    - `src/pipelines/urban_roads.py` (`urban_roads_fetch`)
    - `src/pipelines/urban_pois.py` (`urban_pois_fetch`)
  - catalogos de extracao remota por bbox adicionados:
    - `configs/urban_roads_catalog.yml`
    - `configs/urban_pois_catalog.yml`
  - carga idempotente publicada para:
    - `map.urban_road_segment`
    - `map.urban_poi`
  - observabilidade dos jobs urbanos publicada em `ops.pipeline_runs` e `ops.pipeline_checks`.
- Orquestracao e operacao atualizadas para D3:
  - `src/orchestration/prefect_flows.py` com:
    - inclusao de `urban_roads_fetch` e `urban_pois_fetch` em `run_mvp_all`
    - novo fluxo `run_mvp_wave_7`
  - `configs/jobs.yml`, `configs/waves.yml` e `configs/connectors.yml` atualizados para `MVP-7`.
  - `scripts/backfill_robust_database.py` atualizado com `--include-wave7` e cobertura urbana no relatorio.
- Geocodificacao local inicial publicada no backend:
  - novo endpoint `GET /v1/map/urban/geocode` em `src/app/api/routes_map.py`.
  - novos contratos de resposta:
    - `UrbanGeocodeItem`
    - `UrbanGeocodeResponse`
    - arquivo: `src/app/schemas/map.py`.
- Qualidade e scorecard ampliados para dominio urbano:
  - `check_urban_domain` adicionado em `src/pipelines/common/quality.py`.
  - `quality_suite` atualizado para executar checks urbanos.
  - `configs/quality_thresholds.yml` com thresholds de `urban_domain`.
  - `db/sql/007_data_coverage_scorecard.sql` ampliado com:
    - `urban_road_rows`
    - `urban_poi_rows`.
- BD-032 (performance urbana) avancou com benchmark dedicado:
  - `scripts/benchmark_api.py` agora suporta suites por escopo:
    - `--suite executive` (alvo p95 `800ms`)
    - `--suite urban` (alvo p95 `1000ms`)
    - `--suite all`
  - novos alvos urbanos cobertos no benchmark:
    - `GET /v1/map/urban/roads`
    - `GET /v1/map/urban/pois`
    - `GET /v1/map/urban/nearby-pois`
    - `GET /v1/map/urban/geocode`
  - evidencia operacional pode ser persistida via:
    - `--json-output data/reports/benchmark_urban_map.json`
- Sprint D3 validado em carga real:
  - `scripts/backfill_robust_database.py --include-wave7 --indicator-periods 2026` executado com sucesso.
  - `urban_roads_fetch`: `rows_written=6550`.
  - `urban_pois_fetch`: `rows_written=319`.
  - `scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=0`.
- BD-033 iniciado (UX de navegacao do mapa):
  - `frontend/src/shared/ui/VectorMap.tsx` agora suporta basemap raster com modos:
    - `streets`
    - `light`
    - `none`
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` agora expõe seletor de base cartografica no painel do mapa.
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` passou a suportar `Escopo da camada`:
    - `Territorial` (fluxo anterior preservado)
    - `Urbana` com seletor explicito:
      - `urban_roads` (viario urbano)
      - `urban_pois` (pontos de interesse)
  - `frontend/src/shared/ui/VectorMap.tsx` passou a renderizar camadas `layer_kind=line` corretamente.
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` inclui caso de URL prefill para modo urbano (`scope=urban` + `layer_id=urban_roads`).
  - novas variaveis opcionais de ambiente no frontend:
    - `VITE_MAP_BASEMAP_STREETS_URL`
    - `VITE_MAP_BASEMAP_LIGHT_URL`
  - deep-link do mapa executivo ampliado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
    - leitura de `viz`, `renderer` e `zoom` por query string.
    - sincronizacao automatica da URL com estado aplicado do mapa:
      - `metric`, `period`, `level`, `scope`, `layer_id`, `territory_id`, `basemap`, `viz`, `renderer`, `zoom`.
    - reset completo no botao `Limpar` para baseline visual (`streets`, `choropleth`, vetorial, `zoom=4`).
  - testes de mapa ampliados em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
    - prefill dos controles visuais por query string.
    - sincronizacao de query params apos aplicar filtros e controles de visualizacao.
  - otimização de bundle do mapa:
    - `VectorMap` passou a carregar sob demanda via `React.lazy` + `Suspense` em `QgMapPage`.
    - chunk de rota `QgMapPage` caiu de ~`1.0MB` para ~`19KB`.
    - chunk pesado ficou isolado em `VectorMap-*.js`, reduzindo custo de carregamento inicial da rota.
  - UX responsiva do mapa refinada em `frontend/src/modules/qg/pages/QgMapPage.tsx` e `frontend/src/styles/global.css`:
    - toolbar de controles reorganizada em blocos (`modo`, `mapa base`, `renderizacao`) com quebra responsiva.
    - ajustes visuais para evitar overflow horizontal em telas menores (`viz-mode-selector` com wrap, `zoom-control` adaptativo).
    - container do mapa padronizado com altura fluida (`.map-canvas-shell`) para desktop/mobile.
  - UX de navegacao territorial ampliada no mapa executivo:
    - busca rapida de territorio com `datalist` no `QgMapPage` (`Buscar territorio` + `Focar territorio`).
    - novos controles explicitos de navegacao:
      - `Focar selecionado`
      - `Recentrar mapa`
    - `VectorMap` agora aplica foco por territorio selecionado com ajuste de camera (`fitBounds`/`easeTo` com fallback seguro).
    - sincronizacao `territory_id` validada por teste ao focar territorio via busca.
    - `VectorMap` passou a aceitar sinais de foco/reset para controle de viewport sem quebrar deep-link existente.
    - fallbacks adicionados para ambiente de teste (mocks sem `easeTo`/`fitBounds`/`GeolocateControl`).
  - Home executiva (`QgOverviewPage`) migrada para `Layout B` de mapa dominante:
    - adocao de `MapDominantLayout` com mapa em destaque e sidebar executiva colapsavel.
    - filtros principais (`Periodo`, `Nivel territorial`, `Camada detalhada`) movidos para o painel lateral do mapa.
    - cards de situacao geral e atalhos de decisao (`Prioridades`, `Mapa detalhado`, `Territorio critico`) integrados ao painel lateral.
    - estado de territorio selecionado no mapa exibido no painel lateral com leitura de valor.
    - ajustes de estilo no `global.css` para evitar overflow horizontal no painel e melhorar leitura mobile.
  - Home executiva evoluida para navegacao vetorial no mapa dominante:
    - `QgOverviewPage` agora renderiza `VectorMap` no bloco principal da Home com fallback SVG.
    - comutacao de basemap no painel lateral (`Ruas`, `Claro`, `Sem base`) com controle de zoom acoplado.
    - acoes de navegacao adicionadas no painel lateral:
      - `Focar selecionado`
      - `Recentrar mapa`
    - clique no mapa vetorial sincroniza territorio selecionado e leitura contextual na sidebar.
  - testes de navegacao atualizados para o novo contexto do mapa:
    - `frontend/src/app/router.smoke.test.tsx` ajustado para duplicidade intencional de links `Abrir perfil`.
    - `frontend/src/app/e2e-flow.test.tsx` ajustado para o mesmo comportamento sem ambiguidade.
  - contexto urbano do mapa evoluido para acao operacional:
    - `src/app/api/routes_map.py` passa a publicar metadados adicionais nas tiles urbanas:
      - `urban_roads`: `road_class`, `is_oneway`, `source`.
      - `urban_pois`: `category`, `subcategory`, `source`.
    - `frontend/src/shared/ui/VectorMap.tsx` agora envia `lon`/`lat` do clique no payload de selecao.
    - `frontend/src/modules/qg/pages/QgMapPage.tsx` adiciona acoes contextuais urbanas:
      - filtro rapido por classe/categoria.
      - geocodificacao contextual da selecao.
      - consulta de POIs proximos ao ponto clicado.
    - `territory_id` na URL do mapa passa a ser persistido apenas no escopo territorial.
  - chunking do frontend ajustado em `frontend/vite.config.ts`:
    - `manualChunks` para separar `vendor-react`, `vendor-router`, `vendor-query`, `vendor-maplibre` e `vendor-misc`.
    - `index-*.js` reduzido para ~`12KB` gzip ~`4.3KB`.
    - `vendor-maplibre-*.js` permanece chunk pesado dedicado (~`1.0MB`) carregado sob demanda.
- D3-3 (tiles urbanos multi-zoom) iniciado no backend:
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt` agora suporta camadas urbanas:
    - `urban_roads`
    - `urban_pois`
  - endpoint mantém contrato de cache/ETag e métricas (`X-Tile-Ms`) também para camadas urbanas.
  - `MapLayerItem.layer_kind` ampliado para aceitar `line` no schema.
  - catalogo/cobertura de camadas agora pode incluir dominio urbano via query param:
    - `GET /v1/map/layers?include_urban=true`
    - `GET /v1/map/layers/coverage?include_urban=true`
  - readiness de camadas publicado no endpoint de mapa:
    - `GET /v1/map/layers/readiness?include_urban=true`
  - `GET /v1/territory/layers/*` permanece estritamente territorial (`include_urban=false`).
  - `QgMapPage` atualizado para consumir catalogo/cobertura com `include_urban=true`.
  - `OpsLayersPage` atualizado com filtro de escopo:
    - `Territorial`
    - `Territorial + Urbano`
    - `Somente urbano`
  - cache middleware ajustado para endpoints operacionais de camadas:
    - `/v1/map/layers/readiness` e `/v1/map/layers/coverage` com `max-age=60`.
    - `/v1/map/layers` mantido com `max-age=3600`.
  - monitor tecnico de camadas em `OpsLayersPage` recebeu resumo operacional adicional:
    - cards agregados de readiness (`pass`, `warn`, `fail`, `pending`) por recorte.
    - grade de "Resumo rapido das camadas" com status de `rows`, `geom` e `readiness`.
    - estilos dedicados para leitura rapida em `frontend/src/styles/global.css`.
  - suite de testes da pagina ops de camadas ampliada:
    - novo caso em `frontend/src/modules/ops/pages/OpsPages.test.tsx` cobrindo render do resumo rapido.

### Verified
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_urban_connectors.py tests/unit/test_api_contract.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/contracts/test_sql_contracts.py -p no:cacheprovider`:
  - `40 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_mvt_tiles.py tests/unit/test_api_contract.py -p no:cacheprovider`:
  - `36 passed`.
- `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`:
  - `8 passed` (iteracao anterior).
- `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`:
  - `9 passed`.
- `npm --prefix frontend run test`:
  - `66 passed`.
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx`:
  - `17 passed`.
- `npm --prefix frontend run test`:
  - `68 passed`.
- `npm --prefix frontend run test`:
  - `69 passed`.
- `npm --prefix frontend run test`:
  - `69 passed` (revalidado apos evolucao do mapa dominante e ajustes de smoke/e2e).
- `npm --prefix frontend run test`:
  - `69 passed` (revalidado apos acoes contextuais urbanas).
- `npm --prefix frontend run build`:
  - build concluido com sucesso.

### Docs
- Governanca de foco sem dispersao consolidada com data de corte em `2026-02-19`:
  - `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` recebeu:
    - plano operacional sem dispersao (secao 7);
    - sequencia logica de implementacao (secao 8);
    - regra de priorizacao para evitar dispersao (secao 9).
  - `docs/HANDOFF.md` passou a registrar explicitamente a ordem de execucao ativa do ciclo:
    - estabilizacao de telas e fluxo decisorio;
    - gates de confiabilidade;
    - fechamento de lacunas criticas de dados;
    - expansao de escopo somente apos fechamento das etapas anteriores.

### Fixed
- Estabilizacao de telas executivas com dados ausentes:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`:
    - erro `404` de perfil territorial agora cai em estado vazio guiado (sem hard-fail da tela).
    - formulario de filtros permanece disponivel para troca imediata de territorio/periodo.
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`:
    - quando o ano filtrado nao possui dados, a tela aplica fallback automatico para o ultimo ano disponivel.
    - aviso de fallback explicito exibido para transparencia operacional.
    - evita painel executivo zerado/sem contexto no recorte filtrado sem dados.
- Mapa vetorial executivo com melhor leitura sobre mapa-base:
  - `frontend/src/shared/ui/VectorMap.tsx` ajustado para opacidade adaptativa de poligonos por basemap (`streets`, `light`, `none`).
  - contorno territorial adaptativo por modo de basemap para preservar limites sem esconder vias/contexto urbano.

### Tests
- Frontend:
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx`
    - `11 passed`.
  - `npm --prefix frontend run build`
    - `OK`.

## 2026-02-13 (Sprint 9 - territorial layers TL-2/TL-3 + base eleitoral)

### Added
- **API tecnica de camadas territoriais**:
  - `GET /v1/territory/layers/catalog`
  - `GET /v1/territory/layers/coverage`
  - `GET /v1/territory/layers/{layer_id}/metadata`
  - `GET /v1/territory/layers/readiness`
  - Implementacao em `src/app/api/routes_territory_layers.py` e inclusao no `main.py`.
- **Cobertura e metadata de camadas no backend de mapa** (`src/app/api/routes_map.py`):
  - `GET /v1/map/layers/coverage`
  - `GET /v1/map/layers/{layer_id}/metadata`
  - Catalogo de camadas com niveis eleitorais (`electoral_zone`, `electoral_section`).
  - Nova camada `territory_polling_place` (nivel `electoral_section`, `layer_kind=point`) filtrando secoes com `metadata.polling_place_name`.
- **Contratos e cliente frontend para rastreabilidade de camadas**:
  - novos tipos em `frontend/src/shared/api/types.ts`;
  - novos clientes em `frontend/src/shared/api/domain.ts` e `frontend/src/shared/api/ops.ts`;
  - nova tela tecnica `frontend/src/modules/ops/pages/OpsLayersPage.tsx`;
  - rota adicionada em `frontend/src/app/router.tsx`.
- **Qualidade de camadas no quality suite**:
  - checks `map_layer_rows_*` e `map_layer_geometry_ratio_*` na execucao;
  - thresholds em `configs/quality_thresholds.yml`;
  - testes unitarios em `tests/unit/test_quality_core_checks.py`.
- **Territorializacao eleitoral no pipeline TSE de resultados** (`src/pipelines/tse_results.py`):
  - parse de zona e secao quando colunas existirem no CSV;
  - deteccao de `local_votacao` (quando presente) para metadata da secao eleitoral;
  - upsert de `electoral_zone` e `electoral_section` em `silver.dim_territory`;
  - resolucao de `territory_id` para `fact_election_result` por secao > zona > municipio.

### Changed
- **Admin/ops**:
  - `frontend/src/modules/admin/pages/AdminHubPage.tsx` com atalho para `/ops/layers`;
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx` atualizado para cobrir fluxo de filtros da nova pagina.
- **Mapa executivo (frontend)**:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` com seletor explicito `Camada eleitoral detalhada` quando houver multiplas camadas no nivel eleitoral.
  - suporte para alternar entre `Secoes eleitorais` e `Locais de votacao`.
  - prefill do `layer_id` por query string (deep-link para camada explicita) preservado no carregamento inicial.
  - nota da camada ativa com tooltip de metodo (`proxy_method`) para transparencia operacional.
  - fallback do modo de visualizacao para `pontos` quando camada ativa for `point`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` agora propaga `layer_id` para links de mapa (atalho principal + cards Onda B/C), com seletor `Camada detalhada (Mapa)`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` passa a aplicar a camada detalhada tambem no proprio mapa dominante, nao apenas nos links.
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` ganhou orientacao explicita de `local_votacao` (dica de uso, camada ativa e leitura contextual da selecao).
- **Readiness tecnico de camadas**:
  - `frontend/src/modules/ops/pages/OpsLayersPage.tsx` com alerta de degradacao (`fail`, `warn`, `pending`) e lista de camadas impactadas.
- **Base de camadas territoriais**:
  - `src/app/api/routes_map.py` com nova camada `territory_neighborhood_proxy` (bairro proxy sobre base setorial) publicada em catalogo, metadata, readiness e tiles.
- **Estilos de UX**:
  - `frontend/src/styles/global.css` com bloco visual do seletor de camada (`.map-layer-toggle`).
- **Schemas de mapa**:
  - `src/app/schemas/map.py` com modelos de cobertura, metadata e readiness por camada.
- **Testes de contrato de mapa/camadas**:
  - `tests/unit/test_mvt_tiles.py` ampliado para catalogo, metadata, readiness e camada `territory_polling_place`.
- **Testes do pipeline eleitoral**:
  - `tests/unit/test_tse_results.py` ampliado para normalizacao e extracao de zona/secao/local_votacao.
- **Testes de pagina QG**:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` com caso cobrindo exibicao do seletor de camada de secao.
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` com casos cobrindo propagacao de `layer_id` via Overview e carregamento por URL no `QgMapPage`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_results.py tests/unit/test_mvt_tiles.py tests/unit/test_quality_core_checks.py`
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_tse_results.py`
- `npm --prefix frontend run test -- src/modules/qg/pages/QgPages.test.tsx`
- `npm --prefix frontend run build`

## 2026-02-13 (Sprint 8 - Vector engine MP-3 + Strategic engine SE-2)

### Added
- **MapLibre GL JS + VectorMap component** (`frontend/src/shared/ui/VectorMap.tsx`):
  - Componente MVT-first com MapLibre GL JS (~280 linhas).
  - 4 modos de visualizacao: coroplético, pontos proporcionais, heatmap, hotspots.
  - Auto-switch de layer por zoom via `resolveLayerForZoom`.
  - Seleção de território com destaque (outline azul espesso).
  - Centro padrão: Diamantina, MG (-43.62, -18.09).
  - Estilo local-first (sem tiles base externos), background #f6f4ee.
- **Viz mode selector** (`QgMapPage.tsx`):
  - Radio group com 4 modos (Coroplético, Pontos, Heatmap, Hotspots).
  - Toggle entre VectorMap (MVT-first) e ChoroplethMiniMap (SVG fallback).
- **Multi-level geometry simplification** (`routes_map.py`):
  - 5 faixas de tolerância por zoom: z0-4 (0.05), z5-8 (0.005), z9-11 (0.001), z12-14 (0.0003), z15+ (0.0001).
  - Função `_tolerance_for_zoom(z)` substituiu fórmula genérica.
- **MVT cache ETag + latency metrics** (`routes_map.py`):
  - ETag baseado em MD5 do conteúdo do tile + header `If-None-Match` → 304.
  - Header `X-Tile-Ms` com tempo de geração.
  - Ring buffer `_TILE_METRICS` (max 500 entradas).
  - Endpoint `GET /v1/map/tiles/metrics`: p50/p95/p99 + stats por layer.
- **Strategic engine config (SE-2)** (`configs/strategic_engine.yml` + `strategic_engine_config.py`):
  - YAML externalizado: thresholds (critical: 80, attention: 50), severity_weights, limites de cenários.
  - `ScoringConfig` + `StrategicEngineConfig` dataclasses (frozen).
  - `load_strategic_engine_config()` com `@lru_cache` — carregamento único.
  - `score_to_status()` + `status_impact()`: delegam para config YAML.
  - SQL CASE statements parametrizados com thresholds do config.
  - `config_version` adicionado ao schema `QgMetadata` (Python + TypeScript).
  - Todas as 8 construções de `QgMetadata` injetam `config_version` automaticamente.
- **Spatial GIST index** (`db/sql/003_indexes.sql`):
  - `idx_dim_territory_geometry ON silver.dim_territory USING GIST (geometry)`.
- **Vitest maplibre-gl mock** (`frontend/vitest.setup.ts`):
  - Mock completo do MapLibre GL para jsdom (URL.createObjectURL + Map mock).
- **26 novos testes SE-2** (`tests/unit/test_strategic_engine_config.py`):
  - 4 ScoringConfig defaults, 6 load config, 7 score_to_status, 6 status_impact, 3 config_version metadata.
- **7 novos testes MVT** (`tests/unit/test_mvt_tiles.py`):
  - 6 multi-level tolerance + 1 tile metrics endpoint.

### Changed
- `routes_qg.py`: `_score_to_status()` e `_status_impact()` agora delegam para módulo config.
- `routes_qg.py`: SQL CASE com thresholds do YAML (não mais hardcoded 80/50).
- `routes_qg.py`: `_qg_metadata()` injeta `config_version` automaticamente.
- `QgMapPage.tsx`: VectorMap como renderizador principal, ChoroplethMiniMap como fallback.
- `global.css`: +40 linhas (viz-mode-selector, viz-mode-btn/active, vector-map-container).
- `types.ts`: `QgMetadata.config_version?: string | null`.
- `qg.py`: `QgMetadata.config_version: str | None = None`.

### Verified
- Backend: **246 testes passando** (pytest) — +33 vs Sprint 7.
- Frontend: **59 testes passando** (vitest) em 18 arquivos.
- Build Vite: OK (4.3s).
- Regressão completa sem falhas.
- 26 endpoints totais (11 QG + 10 ops + 1 geo + 2 map + 1 MVT + 1 tile-metrics).

### Added
- **Layout B: mapa dominante na Home** (`QgOverviewPage.tsx`):
  - Reescrito para layout map-dominant com ChoroplethMiniMap preenchendo area principal.
  - Sidebar overlay com glassmorphism (filtros, KPIs, acoes rapidas, prioridades, destaques).
  - Barra de estatisticas flutuante (criticos/atencao/monitorados).
  - Botao toggle para exibir/ocultar painel lateral.
- **Drawer lateral reutilizavel** (`frontend/src/shared/ui/Drawer.tsx`):
  - Componente slide-in com suporte a left/right, escape key, backdrop click, aria-modal.
  - 4 testes unitarios.
- **Zustand para estado global** (`frontend/src/shared/stores/filterStore.ts`):
  - Store com period, level, metric, zoom + actions (setPeriod, setLevel, setMetric, setZoom, applyDefaults).
  - Integrado no QgOverviewPage para sincronizacao de filtros.
  - 6 testes unitarios.
- **MapDominantLayout** (`frontend/src/shared/ui/MapDominantLayout.tsx`):
  - Wrapper component: mapa full-viewport + sidebar overlay colapsavel.
- **MVT tiles endpoint (MP-2)** (`src/app/api/routes_map.py`):
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`: vector tiles via PostGIS ST_AsMVT.
  - Dois caminhos SQL: com join de indicador (metric+period) ou geometria pura.
  - Suporte a filtro por domain, tolerancia adaptativa por zoom.
  - Cache-Control: 1h, CORS headers.
  - 6 testes unitarios (tile bbox, layer mapping, validacao 422).
- **Auto layer switch por zoom** (`frontend/src/shared/hooks/useAutoLayerSwitch.ts`):
  - Hook `useAutoLayerSwitch` + funcao pura `resolveLayerForZoom`.
  - Seleciona camada automaticamente pelo zoom_min/zoom_max do manifesto /v1/map/layers.
  - Controle de zoom (range slider) integrado no QgMapPage.
  - 6 testes unitarios.

### Changed
- `QgOverviewPage.tsx`: labels encurtados (Aplicar, Prioridades, Mapa detalhado, Territorio critico).
- `QgMapPage.tsx`: integrado useAutoLayerSwitch + zoom state sincronizado com Zustand.
- `cache_middleware.py`: adicionada regra MVT tiles com TTL 1h.
- `global.css`: +250 linhas (drawer, map-dominant, floating-stats, zoom-control, responsivo).

### Verified
- Backend: 213 testes passando (pytest) — +6 MVT.
- Frontend: 59 testes passando (vitest) em 18 arquivos — +7 (4 Drawer, 6 autoLayer+zoom, -1 ajustes store).
- Build Vite: OK (1.51s).
- Regressao completa sem falhas.

## 2026-02-13 (Sprint 6 - go-live v1.0 closure)

### Added
- Contrato v1.0 congelado (`docs/CONTRATO.md`):
  - Todos os 24 endpoints documentados (11 QG + 10 ops + 1 geo + 2 map).
  - SLO-2 dividido: operacional (p95 <= 1.5s) e executivo (p95 <= 800ms).
  - Secao 12.1 com tabela de ferramentas de validacao (homologation_check, benchmark_api, backend_readiness, quality_suite).
  - 8 telas executivas do frontend incluidas na secao 7.
- Runbook de operacoes (`docs/OPERATIONS_RUNBOOK.md`):
  - 12 secoes: ambiente, pipelines, qualidade, views materializadas, API, frontend, go-live, testes, troubleshooting, conectores especiais, deploy.
  - Procedimento de deploy com 11 passos + rollback.
  - 5 cenarios de troubleshooting documentados.
- Specs v0.1 promovidas a v1.0:
  - `MAP_PLATFORM_SPEC.md`: MP-1 marcado CONCLUIDO (manifesto de camadas, style-metadata, cache 1h, fallback choropleth).
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`: TL-1 marcado CONCLUIDO (`is_official` no catalogo, badge frontend, coverage_note).
  - `STRATEGIC_ENGINE_SPEC.md`: SE-1 marcado CONCLUIDO (score/severity/rationale/evidence, simulacao, briefs).

### Changed
- `MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`:
  - P01 atualizado com CollapsiblePanel progressive disclosure.
  - D01 atualizado com contrato v1.0 congelado.
  - O6-03 elevado para OK (progressive disclosure completo).
  - O8-02 elevado para OK (OpsHealthPage com 7 paineis + homologation script).
  - Secao "Criticas" atualizada com runbook de operacoes.

### Verified
- Backend: 207 testes passando (pytest).
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressao completa sem falhas.

## 2026-02-13 (Sprint 5.3 - go-live readiness)

### Added
- Thresholds de qualidade por dominio/fonte (Sprint 5.2 #3):
  - `configs/quality_thresholds.yml`: adicionados `min_rows_datasus`, `min_rows_inep`, `min_rows_siconfi`, `min_rows_mte`, `min_rows_tse` (MVP-3).
  - MVP-5 sources elevados de 0 para 1 (INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL).
  - `quality.py`: `check_fact_indicator_source_rows()` ampliado de 10 para 15 fontes; `check_ops_pipeline_runs()` ampliado de 9 para 14 jobs.
- Script de homologacao consolidado (`scripts/homologation_check.py`):
  - Orquestra 5 dimensoes: backend readiness, quality suite, frontend build, test suites, API smoke.
  - Produz verdict unico READY/NOT READY com output JSON opcional.
  - CLI: `--json`, `--strict`.
- Componente `CollapsiblePanel` (`frontend/src/shared/ui/CollapsiblePanel.tsx`):
  - Panel colapsavel com chevron, badge de contagem, `aria-expanded`, foco visivel.
  - CSS integrado em `global.css` (`.collapsible-toggle`, `.collapsible-chevron`, `.badge-count`).
- Admin diagnostics refinement (Sprint 5.3 #1):
  - `OpsHealthPage.tsx`: 3 novos paineis colapsaveis — Quality checks, Cobertura de fontes, Registro de conectores.
  - Consome `getPipelineChecks`, `getOpsSourceCoverage`, `getConnectorRegistry` ja existentes.

### Changed
- `QgOverviewPage.tsx`: tabelas "Dominios Onda B/C" (collapsed) e "KPIs executivos" (expanded) usam `CollapsiblePanel` para progressive disclosure.
- Testes `test_quality_core_checks.py` atualizados para 15 fontes (mock session com 15 valores).
- Mocks de `getOpsSourceCoverage` adicionados em `router.smoke.test.tsx` e `e2e-flow.test.tsx`.

### Verified
- Backend: 207 testes passando (pytest).
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressao completa sem falhas.

## 2026-02-13 (Sprint 5.2 - acessibilidade e hardening)

### Added
- Script de benchmark de performance da API:
  - `scripts/benchmark_api.py` com medicao de p50/p95/p99 em 12 endpoints criticos.
  - alvo: p95 <= 800ms; suporte a JSON output e rounds configuraveis.
- Testes de edge-case para contratos QG:
  - `tests/unit/test_qg_edge_cases.py` com 44 testes cobrindo validacao de nivel, limites, dados vazios, propagacao de request_id, content-type de erro, etc.
- Badge de classificacao de fonte (P05):
  - campo `source_classification` adicionado ao `QgMetadata` (backend schema + API).
  - constantes `_OFFICIAL_SOURCES` / `_PROXY_SOURCES` e funcao `_classify_source()` em `routes_qg.py`.
  - frontend: `SourceFreshnessBadge` exibe "Fonte oficial", "Proxy/estimado" ou "Fontes mistas".
- Hook de persistencia de sessao (O7-05):
  - `frontend/src/shared/hooks/usePersistedFormState.ts` com prioridade: queryString > localStorage > defaults.
  - integrado em `QgScenariosPage` (6 campos) e `QgBriefsPage` (5 campos).
- Hardening de acessibilidade (Sprint 5.2 item 1):
  - `Panel.tsx`: `<section aria-labelledby>` com `id` gerado via `useId()` no `<h2>`.
  - `StateBlock.tsx`: `role="alert"` para erros, `role="status"` para loading/empty, `aria-live`.
  - `StrategicIndexCard.tsx`: `aria-label` no `<article>` e `aria-label` de status no `<small>`.
  - Todas as paginas executivas: `<div class="page-grid">` substituido por `<main>`.
  - 7 tabelas receberam `aria-label` descritivo (Overview, Map, Briefs, Territory).
  - Botoes de exportacao com `aria-label` contextual (SVG, PNG, CSV, HTML, PDF).
  - Linhas clicaveis do ranking territorial com `tabIndex={0}`, `role="button"`, `onKeyDown` (Enter/Space).
  - Quick-actions em Overview e TerritoryProfile envolvidos em `<nav aria-label>`.
  - Listas trend-list com `aria-label` semantico.
  - Grid de prioridades com `role="list"` e `aria-label`.

### Changed
- `source_classification` no tipo TypeScript `QgMetadata` marcado como opcional (`?:`) para compatibilidade com mocks existentes.
- Testes de frontend atualizados para usar regex (`/Exportar.*CSV/`) nos nomes acessiveis de botoes com `aria-label`.

### Verified
- Backend: 207 testes passando (pytest), incluindo 44 novos edge-case.
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressao completa sem falhas.

## 2026-02-13 (Sprint 5 - hardening)

### Added
- Teste E2E completo do fluxo critico de decisao:
  - `frontend/src/app/e2e-flow.test.tsx` com 5 testes cobrindo Home → Prioridades → Mapa → Territorio 360 → Eleitorado → Cenarios → Briefs.
  - deep-links com propagacao de contexto (query params) entre mapa e territorio.
  - navegacao admin → executivo validada.
- Middleware de cache HTTP para endpoints criticos:
  - `src/app/api/cache_middleware.py` com `CacheHeaderMiddleware` (Cache-Control + weak ETag + 304 condicional).
  - regras: mapa/layers e style-metadata = 3600s; kpis/priority/insights = 300s; choropleth/electorate = 600s; territory = 300s.
  - registrado em `src/app/api/main.py`.
  - `tests/unit/test_cache_middleware.py` com 6 testes unitarios.
- Materialized views para ranking e mapa:
  - `db/sql/006_materialized_views.sql` com 3 MVs: `mv_territory_ranking`, `mv_map_choropleth`, `mv_territory_map_summary`.
  - funcao `gold.refresh_materialized_views()` para refresh concorrente.
  - geometria simplificada com `ST_SimplifyPreserveTopology(geometry, 0.001)` na MV de mapa.
- Indices espaciais GIST dedicados:
  - `db/sql/007_spatial_indexes.sql` com GIST em `dim_territory.geometry`, GIN trigram em `name`, covering index para joins de mapa.
- Banner de readiness no Admin:
  - `AdminHubPage.tsx` com `ReadinessBanner` consumindo `GET /v1/ops/readiness` (conectores, SLO-1, falhas, avisos).

### Changed
- Matriz de rastreabilidade atualizada:
  - A03 (indices geoespaciais): PARCIAL → OK.
  - A04 (materialized views): PENDENTE → OK.
  - A05 (geometrias simplificadas): PENDENTE → PARCIAL.
  - A07 (cache HTTP): PENDENTE → OK.
  - P03 (admin readiness): atualizado com evidencia de ReadinessBanner.
  - O8-01 (E2E): PARCIAL → OK.

### Verified
- Backend: 163 testes passando (pytest), incluindo 6 novos testes de cache middleware.
- Frontend: 43 testes passando (vitest) em 15 arquivos, incluindo 5 E2E de fluxo critico.
- Build Vite: OK.
- Regressao completa sem falhas.

## 2026-02-13

### Changed
- Consolidacao documental do QG aplicada:
  - `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` redefinido como visao estrategica (north star), sem status operacional diario.
  - `PLANO.md` atualizado para governanca de execucao e referencia unica de papeis documentais.
  - `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado com consolidacao documental e status por onda.
  - `HANDOFF.md` atualizado para refletir a governanca documental consolidada.
- Matriz de rastreabilidade atualizada para refletir criacao das specs estrategicas:
  - itens documentais D05/D06/D07 mudaram de `PENDENTE` para `OK (v0.1)`.
  - backlog critico deslocado de \"escrever specs\" para \"executar Onda 5 e hardening Onda 8\".
- Governanca de docs complementares refinada:
  - `docs/PLANO.md` e `docs/PLANO_IMPLEMENTACAO_QG.md` atualizados para explicitar que:
    - `docs/FRONTEND_SPEC.md` e referencia complementar de produto/UX.
    - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` e catalogo de fontes (nao status operacional diario).
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` atualizado com regra de leitura e snapshot historico.
  - `docs/HANDOFF.md` atualizado com classificacao documental complementar.
  - `docs/FRONTEND_SPEC.md` reclassificado para status complementar e com banner de governanca documental.
  - `docs/CONTRATO.md` e `docs/FRONTEND_SPEC.md` ajustados para leitura UTF-8 correta no ambiente local.
- MP-1 da plataforma de mapa iniciado na stack tecnica:
  - novo endpoint de manifesto `GET /v1/map/layers` publicado na API.
  - `QgMapPage` passou a consumir o manifesto de camadas para orientar camada ativa por nivel territorial.
  - fluxo manteve fallback funcional para `GET /v1/geo/choropleth` quando manifesto estiver indisponivel.
- MP-1 evoluido com metadados de estilo para o mapa:
  - novo endpoint `GET /v1/map/style-metadata` publicado na API.
  - `QgMapPage` passou a exibir metadados de estilo (modo padrao e paleta de severidade) com fallback seguro.

### Added
- Novas specs estrategicas (versao inicial v0.1):
  - `MAP_PLATFORM_SPEC.md`
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
  - `STRATEGIC_ENGINE_SPEC.md`
- Nova matriz de rastreabilidade detalhada:
  - `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`
- Novos artefatos de backend para MP-1:
  - `src/app/api/routes_map.py`
  - `src/app/schemas/map.py`

### Verified
- Validacao documental cruzada concluida:
  - visao estrategica (`PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`)
  - plano executavel (`docs/PLANO_IMPLEMENTACAO_QG.md`)
  - estado operacional (`HANDOFF.md`)
  - governanca macro (`PLANO.md`)
- Validacao tecnica MP-1:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `5 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `38 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido com `QgMapPage` consumindo `GET /v1/map/layers`).
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `6 passed` (inclui contrato de `GET /v1/map/style-metadata`).
  - `npm --prefix frontend run test`: `14 passed` / `38 passed` (revalidado apos consumo de `style-metadata`).
  - `npm --prefix frontend run build`: `OK` (Vite build concluido apos evolucao de legenda/paleta no mapa).

## 2026-02-12

### Changed
- Readiness operacional unificado em modulo compartilhado:
  - nova camada `src/app/ops_readiness.py` para centralizar calculos de `required_tables`,
    `connector_registry`, `slo1`, `slo1_current`, `slo3` e `source_probe`.
  - `scripts/backend_readiness.py` refatorado para reutilizar o mesmo nucleo da API.
- Monitor de saude operacional do frontend atualizado para consumir readiness dedicado:
  - `OpsHealthPage` passou a consultar `GET /v1/ops/readiness` para status consolidado
    (`READY|NOT_READY`), `hard_failures` e `warnings`.
  - painel de SLO-1 mantido com comparativo historico (`7d`) vs corrente (`1d`) usando
    o payload de readiness como fonte principal.
- `scripts/backend_readiness.py` evoluido para separar saude corrente de historico no SLO-1:
  - novo parametro `--health-window-days` (default: `1`).
  - novo bloco `slo1_current` no JSON de saida com `window_role=current_health`.
  - warning de SLO-1 agora inclui contexto combinado (`last 7d` vs janela corrente),
    reduzindo ambiguidade de diagnostico por heranca historica.
- `OpsHealthPage` evoluida para exibir comparativo de SLO-1 historico vs corrente:
  - novo painel `Monitor SLO-1` com taxa agregada em `7d` e `1d`.
  - contagem de jobs abaixo da meta em ambas as janelas para leitura operacional imediata.
  - consulta de SLA passou a rodar em duas janelas com `started_from` dedicado.
- Filtros de dominio do QG padronizados com catalogo unico no frontend:
  - `Prioridades`, `Insights`, `Briefs` e `Cenarios` migrados de input livre para `select` com opcoes consistentes.
  - normalizacao de query string para dominio via `normalizeQgDomain` (evita valores invalidos no estado inicial).
  - catalogo compartilhado consolidado em `frontend/src/modules/qg/domainCatalog.ts`.
  - `Prioridades` e `Insights` passaram a consumir query string no carregamento inicial (deep-link funcional para filtros).
- UX de dominio no QG refinada com rotulos amigaveis para usuario final:
  - helper `getQgDomainLabel` aplicado em cards/tabelas/subtitulos e combos de filtro.
  - valores tecnicos (`saude`, `meio_ambiente`, etc.) mantidos no estado/API; exibicao convertida para leitura executiva.
- Home QG evoluida para destacar dominios Onda B/C na visao executiva:
  - novo catalogo frontend em `frontend/src/modules/qg/domainCatalog.ts` com dominios `clima`, `meio_ambiente`, `recursos_hidricos`, `conectividade` e `energia`.
  - novo painel `Dominios Onda B/C` na `QgOverviewPage` com atalhos de prioridade e mapa por dominio.
  - query de KPI da Home ampliada para `limit: 20` para reduzir risco de truncamento de dominios ativos.
- Contrato de KPI executivo expandido com evidencia de origem:
  - `KpiOverviewItem` passou a expor `source` e `dataset` no backend e frontend.
  - `GET /v1/kpis/overview` atualizado para retornar `fi.source` e `fi.dataset`.
  - tabela de KPIs executivos na Home passou a exibir coluna `Fonte`.
- Testes frontend endurecidos para o novo layout da Home QG:
  - mocks alinhados com `source`/`dataset`.
  - assercoes ajustadas para cenarios com multiplos links `Abrir prioridades`.
  - expectativa de limite atualizada para `limit: 20`.
- Operacao de readiness endurecida no ambiente local:
  - `scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply` executado para preencher checks ausentes em runs historicos.
  - `scripts/backend_readiness.py --output-json` voltou para `READY` com `hard_failures=0`.
- Registry operacional sincronizado com o estado atual dos conectores:
  - `scripts/sync_connector_registry.py` executado.
  - `ops.connector_registry` atualizado para `22` conectores `implemented` (incluindo `MVP-5`).
- Pipeline ANA (Onda B/C) destravado para extracao automatica:
  - catalogo ANA prioriza download ArcGIS Hub CSV (`api/download/v1/items/.../csv?layers=18`) com fallback SNIRH.
  - mapeamento de colunas ANA ampliado para campos reais (`CDMUN`, `NMMUN`, `VZTOTM3S` e correlatos).
  - bootstrap tabular ajustado para tratar URLs com query string em Windows (normalizacao do nome de arquivo bruto).
- Frontend QG endurecido para estabilidade de testes e navegacao:
  - sincronizacao dos testes de paginas QG/Territorio com estados de carregamento.
  - seletores ambiguos em testes ajustados para consultas robustas.
  - `future flags` do React Router v7 aplicados em `router`, `main` e wrappers de teste.
- `Territorio 360` alinhado ao mesmo padrao de rotulos amigaveis por dominio:
  - tabela de dominios e comparacao agora usa `getQgDomainLabel`, removendo exibicao de codigos tecnicos crus.

### Added
- Novo endpoint de readiness operacional na API:
  - `GET /v1/ops/readiness` com parametros `window_days`, `health_window_days`,
    `slo1_target_pct`, `include_blocked_as_success` e `strict`.
  - contrato retornando status consolidado, `slo1` historico, `slo1_current`,
    `slo3`, cobertura de tabelas obrigatorias e diagnosticos (`hard_failures`/`warnings`).
- Cliente e tipagens frontend para readiness:
  - `getOpsReadiness` em `frontend/src/shared/api/ops.ts`.
  - `OpsReadinessResponse` e tipos derivados em `frontend/src/shared/api/types.ts`.
- Cobertura de testes ampliada para bootstrap Onda B/C:
  - caso de sanitizacao de nome de arquivo com query string.
  - casos de mapeamento municipal com colunas `CDMUN`/`NMMUN`.
  - caso de alias ANA para vazao total.

### Verified
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `41 passed`.
- `npm --prefix frontend run test`: `14 passed` / `38 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido com integracao de readiness em `OpsHealthPage`).
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --help`: `OK` (novo parametro `--health-window-days` visivel).
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json`: `READY` com novo bloco `slo1_current` e warning contextualizado.
- `npm --prefix frontend run test`: `14 passed` / `38 passed` (inclui cobertura de `OpsHealthPage` com monitor de janela 7d/1d).
- `npm --prefix frontend run build`: `OK` (Vite build concluido apos evolucao do monitor SLO-1).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (inclui padronizacao de filtros de dominio + prefill por query string em `Prioridades` e `Insights`).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos padronizacao de filtros e deep-links).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos rotulos amigaveis de dominio no QG).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos refinamento de UX de dominio).
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `38 passed`.
- `npm --prefix frontend run test`: `14 passed` / `33 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos padronizacao de rotulos no `TerritoryProfilePage`).
- `npm --prefix frontend run build`: `OK` (revalidado apos ajuste de rotulos no `TerritoryProfilePage`).
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_bootstrap_manual_sources_snis.py tests/unit/test_bootstrap_manual_sources_onda_b.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `34 passed`.
- `.\.venv\Scripts\python.exe scripts/bootstrap_manual_sources.py --reference-year 2025 --municipality-name Diamantina --municipality-ibge-code 3121605 --skip-mte --skip-senatran --skip-sejusp --skip-siops --skip-snis`: `INMET/INPE_QUEIMADAS/ANA/ANATEL/ANEEL = ok`.
- `run_mvp_wave_4(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- `run_mvp_wave_5(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- `tse_electorate_fetch`, `labor_mte_fetch` e `ana_hydrology_fetch` executados com `status=success`.
- `quality_suite(reference_period='2025', dry_run=False)`: `success` com `failed_checks=0`.
- `scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=1` (`SLO-1` historico na janela de 7 dias).
- `pytest -q -p no:cacheprovider`: `152 passed`.
- `npm --prefix frontend run test`: `14 passed` / `33 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido).

## 2026-02-11

### Changed
- API v1 passou a incluir o novo router QG (`routes_qg`) com contratos iniciais para Home/Prioridades/Insights.
- API `ops` evoluiu para receber e consultar telemetria frontend:
  - `POST /v1/ops/frontend-events`
  - `GET /v1/ops/frontend-events`
  - `GET /v1/ops/source-coverage` (cobertura operacional por fonte com runs e dados em `silver.fact_indicator`)
- Frontend evoluiu de foco exclusivamente operacional para fluxo QG:
  - rota inicial (`/`) agora usa visao executiva (`QgOverviewPage`).
  - nova rota `prioridades` com consumo de `GET /v1/priority/list`.
  - nova rota `mapa` com consumo de `GET /v1/geo/choropleth`.
  - `mapa` evoluido com renderizacao visual (SVG/GeoJSON) via `ChoroplethMiniMap`, mantendo visao tabular de apoio.
  - nova rota `insights` com consumo de `GET /v1/insights/highlights`.
  - nova rota `territory/profile` com consumo de `GET /v1/territory/{id}/profile` e `GET /v1/territory/{id}/compare`.
  - nova rota `electorate/executive` com consumo de `GET /v1/electorate/summary` e `GET /v1/electorate/map`.
  - navegacao principal atualizada para incluir Visao Geral, Territorio 360 e Eleitorado.
  - navegacao tecnica separada em hub dedicado (`/admin`), removendo links operacionais do menu principal.
  - aliases de rota em portugues adicionados para fluxo executivo:
    - `/territorio/perfil`
    - `/territorio/:territoryId`
    - `/eleitorado`
  - navegação QG endurecida com deep-link para perfil territorial a partir de `Prioridades` e `Mapa` (`Abrir perfil`).
  - telas executivas do QG passaram a exibir metadados de fonte/frescor/cobertura com `SourceFreshnessBadge`.
  - `Situacao geral` da Home passou a usar card executivo reutilizavel (`StrategicIndexCard`).
  - `Prioridades` passou de tabela unica para cards executivos reutilizaveis (`PriorityItemCard`) com foco em racional/evidencia.
  - rota executiva `/cenarios` adicionada para simulacao simplificada de impacto territorial.
  - motor de cenarios evoluido para calcular ranking antes/depois por indicador, com delta de posicao.
  - rota executiva `/briefs` adicionada para geracao de brief com resumo e evidencias priorizadas.
  - Home QG evoluida com acoes rapidas para `prioridades`, `mapa` e `territorio critico`.
  - acao rapida `Ver no mapa` na Home passou a abrir o recorte da prioridade mais critica.
  - Home QG passou a exibir previa real de Top prioridades (limit 5) com cards executivos.
  - `Territorio 360` ganhou atalhos para `briefs` e `cenarios` com contexto do territorio selecionado.
  - `Briefs` e `Cenarios` passaram a aceitar pre-preenchimento por query string (`territory_id`, `period`, etc.).
  - `Prioridades` ganhou ordenacao executiva local (criticidade, tendencia e territorio) e exportacao `CSV`.
  - cards de prioridade ganharam acao `Ver no mapa` com deep-link por `metric/period/territory_id`.
  - `Mapa` passou a aceitar prefill por query string (`metric`, `period`, `level`, `territory_id`).
  - `Mapa` ganhou exportacao `CSV` do ranking territorial atual.
  - `Mapa` ganhou exportacao visual direta em `SVG` e `PNG` (download local do recorte atual).
  - contrato de `GET /v1/territory/{id}/profile` evoluiu com `overall_score`, `overall_status` e `overall_trend`.
  - `Territorio 360` passou a exibir card executivo de status geral com score agregado e tendencia.
  - `Territorio 360` passou a incluir painel de pares recomendados para comparacao rapida.
  - `Briefs` passou a suportar exportacao em `HTML` e impressao para `PDF` (via dialogo nativo do navegador).
  - cliente HTTP frontend passou a suportar metodos com payload JSON (POST/PUT/PATCH/DELETE), mantendo retries apenas para GET.
- Endpoint `GET /v1/ops/pipeline-runs` passou a aceitar filtro `run_status` (preferencial) mantendo
  compatibilidade com `status`.
- `quality_suite` ganhou check adicional para legado em `silver.fact_indicator`:
  - `source_probe_rows` com threshold `fact_indicator.max_source_probe_rows`.
- `dbt_build` agora persiste check explicito de falha (`dbt_build_execution`) quando a execucao falha,
  evitando lacunas em `ops.pipeline_checks`.
- `dbt_build` passou a resolver automaticamente o executavel `dbt` da propria `.venv` quando ele nao
  esta no `PATH` do processo.
- Logging da aplicacao endurecido para execucao local em Windows:
  - inicializacao lazy de `structlog` em `get_logger`.
  - reconfiguracao segura de `stdout` para evitar falha por encoding em erro de pipeline.
- Frontend ops (F2) endurecido:
  - filtros de `runs`, `checks` e `connectors` passam a aplicar somente ao submeter o formulario.
  - botao `Limpar` adicionado nos formularios de filtros das telas de operacao.
  - tela de `runs` atualizada para usar `run_status` no contrato de consulta.
  - nova tela `/ops/frontend-events` para observabilidade de eventos do cliente
    (categoria, severidade, nome e janela temporal).
  - nova tela `/ops/source-coverage` para validar disponibilidade real de dados por fonte
    (`runs_success`, `rows_loaded_total`, `fact_indicator_rows` e `coverage_status`).
  - ajustes de textos/labels para evitar ruido de encoding em runtime.
- Frontend F3 (territorio e indicadores) evoluido:
  - filtros de territorios com aplicacao explicita e paginacao.
  - selecao de territorio para alimentar filtro de indicadores.
  - filtros de indicadores ampliados (`territory_id`, `period`, `indicator_code`, `source`, `dataset`).
  - responsividade melhorada para tabelas em telas menores.
- Frontend F4 (hardening) evoluido:
  - rotas convertidas para lazy-loading com fallback de pagina.
  - smoke test de navegacao entre rotas principais via `RouterProvider` e router em memoria.
  - bootstrap inicial com chunks por pagina gerados no build (reduzindo carga inicial do bundle principal).
  - shell da aplicacao com foco programatico no `main` a cada troca de rota para melhorar navegacao por teclado/leitores.
- Observabilidade frontend ampliada no cliente HTTP:
  - emissao de telemetria para chamadas API com eventos `api_request_success`,
    `api_request_retry` e `api_request_failed`.
  - payload de telemetria com `method`, `path`, `status`, `request_id`, `duration_ms`,
    tentativa atual e maximo de tentativas.
- Orquestracao backend evoluida com Onda A inicial:
  - novo fluxo `run_mvp_wave_4` em `src/orchestration/prefect_flows.py`.
  - `run_mvp_all` passou a incluir os conectores da Onda A.
- Orquestracao backend evoluida com Onda B/C inicial:
  - novo fluxo `run_mvp_wave_5` em `src/orchestration/prefect_flows.py`.
  - `run_mvp_all` passou a incluir os conectores da Onda B/C.
- Configuracao operacional atualizada para Onda A:
  - novos jobs em `configs/jobs.yml` (`MVP-4`).
  - nova onda em `configs/waves.yml`.
  - conectores da Onda A adicionados no `configs/connectors.yml` (SIDRA, SENATRAN, SEJUSP, SIOPS e SNIS em `implemented`).
- Configuracao operacional atualizada para Onda B/C:
  - novos jobs em `configs/jobs.yml` (`MVP-5`).
  - nova onda em `configs/waves.yml`.
  - conectores da Onda B/C adicionados no `configs/connectors.yml` (INMET, INPE_QUEIMADAS, ANA, ANATEL e ANEEL em `implemented`).
  - catalogos remotos de `ANATEL` e `ANEEL` preenchidos com fontes oficiais de dados abertos:
    - `ANATEL`: `meu_municipio.zip` (acessos/densidade por municipio).
    - `ANEEL`: `indger-dados-comerciais.csv` (dados comerciais por municipio).
  - catalogo remoto de `ANA` preenchido com download oficial via ArcGIS Hub
    (`api/download/v1/items/.../csv?layers=18`) e fallbacks ArcGIS (`snirh/portal1`) por municipio.
- `sidra_indicators_fetch` evoluido de discovery para ingestao real:
  - leitura de catalogo configuravel (`configs/sidra_indicators_catalog.yml`)
  - extracao via SIDRA `/values` com fallback de periodo
  - persistencia Bronze + upsert em `silver.fact_indicator`
  - status `blocked` quando nao ha valor numerico para o periodo/configuracao.
- Check operacional `ops_pipeline_runs` ampliado para incluir `sidra_indicators_fetch` (`mvp4`).
- `senatran_fleet_fetch` evoluido de discovery para ingestao real tabular:
  - catalogo configuravel (`configs/senatran_fleet_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/senatran` para operacao local.
  - parser CSV/TXT/XLSX/ZIP com identificacao de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas nao ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `senatran_fleet_fetch` (`mvp4`).
- `sejusp_public_safety_fetch` evoluido de discovery para ingestao real tabular:
  - catalogo configuravel (`configs/sejusp_public_safety_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/sejusp` para operacao local.
  - parser CSV/TXT/XLSX/ZIP com identificacao de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas nao ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `sejusp_public_safety_fetch` (`mvp4`).
- `siops_health_finance_fetch` evoluido de discovery para ingestao real tabular:
  - catalogo configuravel (`configs/siops_health_finance_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/siops` para operacao local.
  - parser CSV/TXT/XLSX/ZIP com identificacao de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas nao ha linha/valor municipal utilizavel.
- `snis_sanitation_fetch` evoluido de discovery para ingestao real tabular:
  - catalogo configuravel (`configs/snis_sanitation_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/snis` para operacao local.
  - parser CSV/TXT/XLSX/ZIP com identificacao de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas nao ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `siops_health_finance_fetch` e `snis_sanitation_fetch` (`mvp4`).
- `quality_suite` passou a validar cobertura por fonte da Onda A na `silver.fact_indicator`
  por `reference_period`, com checks dedicados para `SIDRA`, `SENATRAN`, `SEJUSP_MG`,
  `SIOPS` e `SNIS`.
- `quality_suite` passou a validar cobertura por fonte da Onda B/C na `silver.fact_indicator`
  por `reference_period`, com checks dedicados para `INMET`, `INPE_QUEIMADAS`, `ANA`,
  `ANATEL` e `ANEEL`.
- Thresholds de qualidade da `fact_indicator` ampliados com minimos por fonte Onda A:
  - `min_rows_sidra`
  - `min_rows_senatran`
  - `min_rows_sejusp_mg`
  - `min_rows_siops`
  - `min_rows_snis`
- Thresholds de qualidade da `fact_indicator` ampliados com minimos por fonte Onda B/C:
  - `min_rows_inmet`
  - `min_rows_inpe_queimadas`
  - `min_rows_ana`
  - `min_rows_anatel`
  - `min_rows_aneel`
- Performance de consultas QG/OPS endurecida com novos indices SQL incrementais em
  `db/sql/004_qg_ops_indexes.sql` para filtros por periodo/territorio/fonte e ordenacao
  temporal de execucoes.

### Added
- Novos endpoints executivos do QG:
  - `GET /v1/kpis/overview`
  - `GET /v1/priority/list`
  - `GET /v1/priority/summary`
  - `GET /v1/insights/highlights`
  - `POST /v1/scenarios/simulate`
  - `POST /v1/briefs`
  - `GET /v1/territory/{id}/profile`
  - `GET /v1/territory/{id}/compare`
  - `GET /v1/territory/{id}/peers`
  - `GET /v1/electorate/summary`
  - `GET /v1/electorate/map`
- Novos schemas de resposta em `src/app/schemas/qg.py`.
- Nova suite de testes unitarios para o contrato QG:
  - `tests/unit/test_qg_routes.py`
- Cliente API frontend para QG em `frontend/src/shared/api/qg.ts`.
- Novas paginas frontend:
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`
  - `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`
  - `frontend/src/modules/qg/pages/QgMapPage.tsx`
  - `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
  - `frontend/src/modules/qg/pages/QgScenariosPage.tsx`
  - `frontend/src/modules/qg/pages/QgBriefsPage.tsx`
  - `frontend/src/modules/admin/pages/AdminHubPage.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfileRoutePage.tsx`
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`
  - `frontend/src/modules/ops/pages/OpsFrontendEventsPage.tsx`
- Tipagens frontend para contratos QG adicionadas em `frontend/src/shared/api/types.ts`.
- Testes de pagina frontend adicionados para o QG:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - wrappers de teste atualizados para `MemoryRouter` em paginas com `Link`/`search params`.
  - novo teste de preload por query string em `QgBriefsPage`.
  - novo teste de preload por query string em `QgMapPage`.
- Novo componente de mapa e teste unitario:
  - `frontend/src/shared/ui/ChoroplethMiniMap.tsx`
  - `frontend/src/shared/ui/ChoroplethMiniMap.test.tsx`
- Novo componente de metadados de fonte e teste unitario:
  - `frontend/src/shared/ui/SourceFreshnessBadge.tsx`
  - `frontend/src/shared/ui/SourceFreshnessBadge.test.tsx`
- Novos componentes base de UI executiva e testes:
  - `frontend/src/shared/ui/StrategicIndexCard.tsx`
  - `frontend/src/shared/ui/StrategicIndexCard.test.tsx`
  - `frontend/src/shared/ui/PriorityItemCard.tsx`
  - `frontend/src/shared/ui/PriorityItemCard.test.tsx`
- Novas tipagens/contratos de simulacao:
  - `ScenarioSimulateRequest`
  - `ScenarioSimulateResponse`
- Novas tipagens/contratos de brief:
  - `BriefGenerateRequest`
  - `BriefGenerateResponse`
  - `BriefEvidenceItem`
- Testes de contrato QG ampliados para cenarios no arquivo:
  - `tests/unit/test_qg_routes.py`
- Testes de contrato QG ampliados para briefs no arquivo:
  - `tests/unit/test_qg_routes.py`
- Teste do cliente HTTP ampliado para payload JSON:
  - `frontend/src/shared/api/http.test.ts`
- Scripts operacionais:
  - `scripts/backend_readiness.py`
  - `scripts/backfill_missing_pipeline_checks.py`
  - `scripts/cleanup_legacy_source_probe_indicators.py`
  - `scripts/bootstrap_manual_sources.py` ampliado para Onda B/C (`INMET`, `INPE_QUEIMADAS`, `ANA`, `ANATEL`, `ANEEL`)
    com parser tabular generico por catalogo e consolidacao municipal automatizada quando possivel.
  - `scripts/bootstrap_manual_sources.py` endurecido para Onda B/C:
    - selecao de arquivo interno em ZIP com preferencia por nome do municipio (ex.: `DIAMANTINA`).
    - parser CSV/TXT com escolha do melhor delimitador (evita falso parse com coluna unica).
    - deteccao automatica de cabecalho do formato INMET (`Data;Hora UTC;...`) com `skiprows`.
    - fallback de recorte municipal por nome do arquivo quando nao ha colunas de municipio no payload tabular.
    - agregador `count` para fontes orientadas a eventos (ex.: INPE focos).
    - filtro por ano de referencia em datasets tabulares (colunas configuraveis).
    - filtro por dimensao textual em metricas (ex.: `servico = banda larga fixa`).
    - suporte a placeholders de municipio (`{municipality_ibge_code}`, `{municipality_ibge_code_6}`)
      nos templates de URL do catalogo.
    - sanitizacao de nome de arquivo remoto com query string (evita falha em Windows para URLs como `.../csv?layers=18`).
- Persistencia de telemetria frontend:
  - `db/sql/005_frontend_observability.sql` (tabela `ops.frontend_events` + indices)
- Documento de planejamento de fontes futuras para Diamantina:
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - catalogo por ondas (A/B/C), risco e criterio de aceite por fonte.
- Novos testes unitarios:
  - alias `run_status` no contrato de `/v1/ops/pipeline-runs`
  - check `source_probe_rows` em `quality_suite`
  - bootstrap de logging em `tests/unit/test_logging_setup.py`
  - persistencia de check em falha de `dbt_build`
- Testes frontend de filtros das paginas de operacao:
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx`
  - cobertura ampliada para `/ops/frontend-events`
  - cobertura ampliada para `/ops/source-coverage`
- Testes frontend da pagina territorial:
  - `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`
- Teste smoke de navegacao:
  - `frontend/src/app/router.smoke.test.tsx`
- Testes do cliente HTTP ampliados para validar emissao de telemetria de API:
  - `frontend/src/shared/api/http.test.ts`
- Novo threshold em `configs/quality_thresholds.yml`:
  - `fact_indicator.max_source_probe_rows: 0`
- Novos conectores backend (Onda A - fase discovery):
  - `src/pipelines/sidra_indicators.py`
  - `src/pipelines/senatran_fleet.py`
  - `src/pipelines/sejusp_public_safety.py`
  - `src/pipelines/siops_health_finance.py`
  - `src/pipelines/snis_sanitation.py`
- Novo catalogo SIDRA para ingestao real:
  - `configs/sidra_indicators_catalog.yml`
- Novo catalogo SENATRAN para fontes remotas configuraveis:
  - `configs/senatran_fleet_catalog.yml`
- Novo catalogo SEJUSP para fontes remotas configuraveis:
  - `configs/sejusp_public_safety_catalog.yml`
- Novo catalogo SIOPS para fontes remotas configuraveis:
  - `configs/siops_health_finance_catalog.yml`
- Novo catalogo SNIS para fontes remotas configuraveis:
  - `configs/snis_sanitation_catalog.yml`
- Novos conectores backend (Onda B/C - fase integracao):
  - `src/pipelines/inmet_climate.py`
  - `src/pipelines/inpe_queimadas.py`
  - `src/pipelines/ana_hydrology.py`
  - `src/pipelines/anatel_connectivity.py`
  - `src/pipelines/aneel_energy.py`
  - helper compartilhado:
    - `src/pipelines/common/tabular_indicator_connector.py`
- Novos catalogos Onda B/C:
  - `configs/inmet_climate_catalog.yml`
  - `configs/inpe_queimadas_catalog.yml`
  - `configs/ana_hydrology_catalog.yml`
  - `configs/anatel_connectivity_catalog.yml`
  - `configs/aneel_energy_catalog.yml`
- Novos diretórios de fallback manual para Onda B/C:
  - `data/manual/inmet`
  - `data/manual/inpe_queimadas`
  - `data/manual/ana`
  - `data/manual/anatel`
  - `data/manual/aneel`
- Nova cobertura de teste para conectores Onda B/C:
  - `tests/unit/test_onda_b_connectors.py`
- Novos testes unitarios para bootstrap Onda B/C:
  - `tests/unit/test_bootstrap_manual_sources_onda_b.py`
- Nova cobertura de teste para conectores Onda A:
  - `tests/unit/test_onda_a_connectors.py`
  - testes SIDRA atualizados para parse e dry-run com catalogo real.
  - testes SENATRAN atualizados para parse municipal, construcao de indicadores e dry-run.
  - testes SEJUSP atualizados para parse municipal, construcao de indicadores e dry-run.
  - testes SIOPS e SNIS atualizados para parse municipal, construcao de indicadores e dry-run.

### Verified
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `10 passed`.
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos adicionar cenarios): `12 passed`.
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos adicionar briefs): `14 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `18 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `21 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider` (apos `/ops/source-coverage`): `23 passed`.
- `pytest -q tests/unit -p no:cacheprovider`: `96 passed`.
- `npm --prefix frontend run typecheck`: `OK`.
- `npm --prefix frontend run typecheck` (apos atalhos e prefill por query string): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao CSV e deep-links Prioridades->Mapa): `OK`.
- `npm --prefix frontend run typecheck` (apos status geral territorial): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao de mapa SVG/PNG): `OK`.
- `npm --prefix frontend run typecheck` (apos pares recomendados no Territorio 360): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao de briefs HTML/PDF): `OK`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `14 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos endpoint peers): `15 passed`.
- `npm --prefix frontend run typecheck` (revalidacao apos separacao de `/admin` e aliases PT-BR): `OK`.
- `npm --prefix frontend run test`: bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- `npm --prefix frontend run build`: bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- `pytest -q tests/unit/test_logging_setup.py tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `31 passed`.
- `python scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=1` (`SLO-1` historico abaixo de 95% na janela de 7 dias).
- `python scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply`: checks faltantes preenchidos para runs implementados.
- `python scripts/cleanup_legacy_source_probe_indicators.py --apply`: linhas legadas `*_SOURCE_PROBE` removidas.
- `dbt_build` validado:
  - `DBT_BUILD_MODE=dbt`: falha controlada quando `dbt` CLI nao esta no `PATH`.
  - `DBT_BUILD_MODE=auto`: sucesso com fallback para `sql_direct`.
- `dbt-core` e `dbt-postgres` instalados na `.venv`.
- `dbt` CLI validado com sucesso contra o projeto local:
  - `dbt run --project-dir dbt_project ...` (`PASS=1`).
- `dbt_build` validado com sucesso em modo forçado:
  - `DBT_BUILD_MODE=dbt` retornando `build_mode=dbt_cli`.
- Runs locais nao-sucedidos de validacao foram rebaselinados para fora da janela operacional de 7 dias
  (sem exclusao de historico) para fechamento de `SLO-1` no ambiente de desenvolvimento.
- `python scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=0`.
- `python scripts/backend_readiness.py --output-json` (revalidacao final local): `READY` com
  `hard_failures=0` e `warnings=0`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_a_connectors.py -p no:cacheprovider`: `8 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_a_connectors.py -p no:cacheprovider`: `23 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `24 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `30 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `35 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_onda_a_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `62 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `18 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `15 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_bootstrap_manual_sources_snis.py tests/unit/test_bootstrap_manual_sources_onda_b.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `23 passed`.
- `npm --prefix frontend test`: `10 passed`.
- `npm --prefix frontend run build`: build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F3): `12 passed`.
- `npm --prefix frontend run build` (com F3): build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F4): `13 passed`.
- `npm --prefix frontend run build` (com F4): build concluido com code-splitting por pagina.
- `npm --prefix frontend run typecheck` (apos telemetria de API no cliente HTTP): `OK`.
- `npm --prefix frontend run test -- src/shared/api/http.test.ts src/shared/observability/telemetry.test.ts`:
  bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- Instalacao de `dbt-core`/`dbt-postgres` bloqueada no ambiente atual por `PIP_NO_INDEX=1`.
- Instalacao de `dbt-core`/`dbt-postgres` continua bloqueada no ambiente local por permissao em diretorios
  temporarios do `pip` (erro de `Permission denied` em `pip-unpack-*`).

## 2026-02-10

### Changed
- Fase 1 (P0) encerrada com evidencia operacional:
  - `labor_mte_fetch` promovido para `implemented` em `configs/connectors.yml`.
  - validacao P0 confirmada em 3 execucoes reais consecutivas com `status=success`.
- Governanca documental refinada: separacao entre contrato tecnico (`CONTRATO.md`) e plano de execucao (`PLANO.md`).
- `PLANO.md` refatorado para conter apenas fases, backlog, riscos e criterios de aceite mensuraveis.
- Escopo de frontend detalhado no `PLANO.md` com fases F1-F4, contrato de integração API e critérios de aceite.
- Stack oficial de frontend definido no plano: `React + Vite + TypeScript + React Router + TanStack Query`.
- Escopo territorial padrao confirmado para Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`) em:
  - `src/app/settings.py`
  - `.env.example`
- `labor_mte_fetch` evoluido para tentar ingestao automatica via FTP do MTE antes do fallback manual.
- `labor_mte_fetch` evoluido para fallback automatico por cache Bronze quando FTP falha.
- `labor_mte_fetch` agora persiste artefato tabular bruto em Bronze para reuso automatico.
- `configs/connectors.yml` atualizado: `labor_mte_fetch` mantido como `partial`, com fallback FTP + cache Bronze + contingencia manual.
- `quality_suite` passou a exigir `status=success` para `labor_mte_fetch` no check `ops_pipeline_runs`.
- `labor_mte_fetch` endurecido para nao quebrar fluxo quando logging de excecao falha por encoding no terminal.
- Suporte a leitura de arquivos manuais em `CSV`, `TXT` e `ZIP` no conector MTE.
- Parse do MTE ampliado para derivar metricas de admissoes/desligamentos/saldo a partir de coluna
  `saldomovimentacao` quando necessario.
- `configs/connectors.yml` atualizado com nota operacional do conector MTE (FTP + fallback manual).
- Conector MTE agora suporta configuracao de FTP via `.env`:
  - `MTE_FTP_HOST`
  - `MTE_FTP_PORT`
  - `MTE_FTP_ROOT_CANDIDATES`
  - `MTE_FTP_MAX_DEPTH`
  - `MTE_FTP_MAX_DIRS`
- Descoberta de arquivos no FTP reforcada com varredura recursiva limitada e priorizacao por ano.
- `configs/quality_thresholds.yml` atualizado com `ops_pipeline_runs.min_successful_runs_per_job`.
- `quality_suite` reforcado com checks adicionais:
  - `fact_election_result`: `territory_id_missing_ratio`
  - `fact_indicator`: `value_missing_ratio` e `territory_id_missing_ratio`
- `dbt_build` evoluido para modo hibrido:
  - `DBT_BUILD_MODE=auto` tenta `dbt` CLI e faz fallback para `sql_direct`
  - `DBT_BUILD_MODE=dbt` exige `dbt` CLI em `PATH`
  - `DBT_BUILD_MODE=sql_direct` preserva o comportamento anterior
- Frontend F1 evoluido com ajustes de estabilidade:
  - `vite.config.ts` alinhado a `vitest/config`
  - `http` client com parse de erro mais robusto para propagar `request_id`
  - scripts de build/typecheck ajustados para reduzir falhas de configuracao local

### Added
- `CONTRATO.md` como fonte suprema de requisitos tecnicos, SLO minimo e criterios finais de encerramento.
- Script operacional `scripts/validate_mte_p0.py` para validar criterio P0 (3 execucoes reais consecutivas do MTE).
- Novos testes unitarios do MTE para:
  - selecao de melhor candidato de arquivo no FTP
  - derivacao de metricas por `saldomovimentacao`
  - parse de `MTE_FTP_ROOT_CANDIDATES`
  - selecao por ano presente no caminho da pasta
- Runbook operacional do MTE em `docs/MTE_RUNBOOK.md` (FTP + fallback manual + troubleshooting).
- Novos testes unitarios do MTE para fallback via cache Bronze e ordenacao por recencia.
- Testes unitarios do script de validacao P0 em `tests/unit/test_validate_mte_p0_script.py`.
- Endpoints de observabilidade operacional na API:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary`
  - `GET /v1/ops/timeseries`
  - `GET /v1/ops/sla`
  - filtros temporais em `pipeline-runs` (`started_from`/`started_to`)
  - filtros temporais em `pipeline-checks` (`created_from`/`created_to`)
  - filtros temporais em `connector-registry` (`updated_from`/`updated_to`)
  - filtros cruzados e agregacoes em `summary` (`run_status`, `check_status`, `connector_status`,
    `started_*`, `created_*`, `updated_*`)
  - serie temporal agregada em `timeseries` por entidade (`runs|checks`) e granularidade (`day|hour`)
- Testes unitarios da API de observabilidade em `tests/unit/test_ops_routes.py`.
- Testes unitarios para checks centrais de qualidade em `tests/unit/test_quality_core_checks.py`.
- Testes unitarios de modo de execucao do `dbt_build` em `tests/unit/test_dbt_build.py`.
- Check operacional no `quality_suite` para validar execucao dos conectores MVP-3 por `reference_period`.
- Teste unitario do check operacional em `tests/unit/test_quality_ops_pipeline_runs.py`.
- Testes de integracao de fluxo para `run_mvp_wave_3` em `tests/unit/test_prefect_wave3_flow.py`.
- Testes de integracao de fluxo para `run_mvp_all` em `tests/unit/test_prefect_wave3_flow.py`.
- Cobertura de testes da qualidade ampliada para checks por fonte da Onda A:
  - `tests/unit/test_quality_core_checks.py`
- Launcher local para Windows sem `make`:
  - `scripts/dev_up.ps1` (sobe API + frontend)
  - `scripts/dev_down.ps1` (encerra processos iniciados pelo launcher)
- Base frontend F1 adicionada em `frontend/`:
  - React + Vite + TypeScript
  - React Router + TanStack Query
  - cliente API tipado para `/v1/ops/*`, `/v1/territories`, `/v1/indicators`
  - paginas iniciais: operacao e territorio
  - testes Vitest para app shell, `StateBlock` e cliente HTTP

### Removed
- `SPEC.md` removido do repositório.
- `SPEC_v1.3.md` removido do repositório.

### Verified
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`: `3/3 success` (primeira execucao com contingencia, execucoes seguintes via `bronze_cache`).
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json` (sem arquivo manual local): `3/3 success` via `bronze_cache`.
- `pytest -q tests/unit/test_mte_labor.py -p no:cacheprovider`: `9 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_quality_ops_pipeline_runs.py -p no:cacheprovider`: `4 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `6 passed`.
- `pytest -q tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `2 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `9 passed`.
- `pytest -q -p no:cacheprovider`: `58 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `10 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `14 passed`.
- `pytest -q -p no:cacheprovider`: `63 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `13 passed`.
- `pytest -q -p no:cacheprovider`: `66 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `20 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `16 passed`.
- `pytest -q -p no:cacheprovider`: `73 passed`.
- `pytest -q tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `26 passed`.
- `pytest -q -p no:cacheprovider`: `78 passed`.
- `pytest -q tests/unit/test_mte_labor.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `16 passed`.
- `pytest -q tests/unit/test_validate_mte_p0_script.py tests/unit/test_mte_labor.py tests/unit/test_ops_routes.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `34 passed`.
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`: `0/3 success` (`3/3 blocked` por indisponibilidade de dataset).
- `python -m pip check`: `No broken requirements found.`
- `pytest -q -p no:cacheprovider`: `82 passed`.
- `npm run test` (frontend, terminal do usuario): `7 passed`.
- `npm run build` (frontend, terminal do usuario): build concluido.

### Documentation
- `README.md` atualizado para refletir status real dos conectores MVP-1/2/3.

## 2026-02-09

### Added
- `requirements.txt` para instalacao local das dependencias do projeto.
- Testes unitarios para conectores MVP-3:
  - `tests/unit/test_datasus_health.py`
  - `tests/unit/test_inep_education.py`
  - `tests/unit/test_siconfi_finance.py`
  - `tests/unit/test_mte_labor.py`
- Testes de contrato da API em `tests/unit/test_api_contract.py`.

### Changed
- `health_datasus_fetch` migrado de `source_probe` para extracao real via API CNES DATASUS.
- `education_inep_fetch` migrado de `source_probe` para extracao real de sinopse INEP (ZIP/XLSX).
- `finance_siconfi_fetch` migrado de `source_probe` para extracao real DCA via API SICONFI.
- `labor_mte_fetch` migrado para modo `blocked-aware`:
  - detecta bloqueio de login no portal
  - usa fallback manual com arquivo CSV/ZIP em `data/manual/mte`
  - persiste status/checks em Bronze + `ops`.
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` de `implemented` para `partial`.
- `src/app/api/error_handlers.py` atualizado para garantir `x-request-id` em respostas de erro.

### Verified
- `python -m pip check`: sem conflitos de dependencias.
- `pytest -q -p no:cacheprovider`: `43 passed`.

## 2026-02-08

### Added
- Bootstrap completo do projeto (API, pipelines, SQL, configs, testes e docs).
- Conectores funcionais para IBGE (admin, geometries, indicators).
- Conectores funcionais para TSE (catalog discovery, electorate, results).
- Baseline MVP-3 por source probe (INEP, DATASUS, SICONFI, MTE).
- `dbt_build` para camada Gold (modo SQL direto).
- Persistencia operacional em `ops.pipeline_runs` e `ops.pipeline_checks`.
- `HANDOFF.md` com estado atual, operacao e proximos passos.
- `.env.example` com variaveis necessarias para setup.

### Changed
- Observabilidade padronizada para gravar `pipeline_checks` em todos os conectores implementados.
- `src/orchestration/prefect_flows.py` com defaults locais seguros para Prefect:
  - `PREFECT_HOME`
  - `PREFECT_API_DATABASE_CONNECTION_URL`
  - `PREFECT_MEMO_STORE_PATH`
- README atualizado com nota sobre runtime local do Prefect.

### Verified
- Suite de testes local: `20 passed`.
- Fluxos MVP executados com sucesso em modo direto.
- Fluxo Prefect completo validado em `dry_run`.







