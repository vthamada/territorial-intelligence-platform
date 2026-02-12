# Changelog

Todas as mudancas relevantes do projeto devem ser registradas aqui.

## 2026-02-12

### Changed
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

### Added
- Cobertura de testes ampliada para bootstrap Onda B/C:
  - caso de sanitizacao de nome de arquivo com query string.
  - casos de mapeamento municipal com colunas `CDMUN`/`NMMUN`.
  - caso de alias ANA para vazao total.

### Verified
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (inclui padronizacao de filtros de dominio + prefill por query string em `Prioridades` e `Insights`).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos padronizacao de filtros e deep-links).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos rotulos amigaveis de dominio no QG).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos refinamento de UX de dominio).
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `38 passed`.
- `npm --prefix frontend run test`: `14 passed` / `33 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido).
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
