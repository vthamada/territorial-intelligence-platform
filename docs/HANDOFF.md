# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-21
Planejamento principal: `docs/PLANO_IMPLEMENTACAO_QG.md`
North star de produto: `docs/VISION.md`
Contrato tecnico principal: `CONTRATO.md`

## Trilha ativa unica (executavel no ciclo atual)

1. Trilha ativa oficial (WIP=1):
   - `D5` concluido tecnicamente (`BD-050`, `BD-051`, `BD-052`).
   - `D6` concluido tecnicamente (`BD-060`, `BD-061`, `BD-062`).
   - `D7` concluido tecnicamente (`BD-070`, `BD-071`, `BD-072`).
   - `D8` concluido tecnicamente (`BD-080`, `BD-081`, `BD-082`).
   - `D4-mobilidade/frota` encerrada com entregas `BD-040`, `BD-041` e `BD-042`.
2. Status da trilha anterior (D3-hardening, encerrada em 2026-02-21):
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
   - `npm run test -- --run` (em `frontend/`) -> `78 passed`.
   - `npm run build` (em `frontend/`) -> `OK`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json` -> `ALL PASS`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
3. Validacao de fechamento tecnico de D4 (2026-02-21):
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `47 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 13 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - smoke API: `GET /v1/mobility/access?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
   - GitHub issues encerradas no mesmo ciclo:
     - `#13` (`BD-040`) -> `closed`.
     - `#14` (`BD-041`) -> `closed`.
     - `#15` (`BD-042`) -> `closed`.
4. Criterio de saida (DoD do ciclo D4):
   - suite backend/frontend em `pass`;
   - readiness com `status=READY` e `hard_failures=0`;
   - scorecard de cobertura sem regressao critica;
   - evidencias registradas no proprio `HANDOFF` e em `docs/CHANGELOG.md`.
5. Proximo passo imediato:
   - executar rotina recorrente da janela de 30 dias com `scripts/export_ops_robustness_window.py` ate estabilizar `status=READY` com `gates.all_pass=true`.
6. Governanca de issue:
   - ao concluir item tecnico, encerrar issue correspondente no GitHub na mesma rodada.
7. Regra de leitura:
   - apenas esta secao define "proximo passo executavel" no momento;
   - secoes de "proximos passos" antigas abaixo devem ser lidas como historico.

## Atualizacao tecnica (2026-02-22) - Consolidacao operacional 30d publicada (pos-D8)

1. Consolidacao unica de robustez operacional publicada:
   - novo modulo `src/app/ops_robustness_window.py` para agregar readiness + scorecard + incidentes da janela.
   - novo endpoint `GET /v1/ops/robustness-window` com default operacional `window_days=30` e `health_window_days=7`.
2. Evidencia versionavel da janela:
   - novo script `scripts/export_ops_robustness_window.py` com saida padrao em `data/reports/ops_robustness_window_30d.json`.
3. Cobertura de testes:
   - nova suite `tests/unit/test_ops_robustness_window.py`.
   - `tests/unit/test_ops_routes.py` ampliado para o endpoint `/v1/ops/robustness-window`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --output-json data/reports/ops_robustness_window_30d.json` -> `status=NOT_READY`, `severity=critical`, `all_pass=False` (janela ainda em consolidacao).
5. Proximo passo operacional:
   - reduzir `failed_checks` e estabilizar execucao para convergir a janela de 30 dias para `READY`.

## Atualizacao tecnica (2026-02-22) - D8 BD-082 implementado (playbook de incidentes e operacao assistida)

1. Snapshot operacional unico para triagem de incidente:
   - novo script `scripts/generate_incident_snapshot.py`;
   - consolida:
     - readiness backend;
     - runs recentes `failed|blocked`;
     - checks recentes com `status=fail`;
     - classificacao de severidade (`critical|high|normal`) e acoes recomendadas.
2. Runbook operacional consolidado:
   - `docs/OPERATIONS_RUNBOOK.md` recebeu secao `11.8` com fluxo executavel de triagem.
3. Cobertura de teste:
   - nova suite `tests/unit/test_generate_incident_snapshot.py` para classificacao e acoes.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_generate_incident_snapshot.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `16 passed`.
   - `.\.venv\Scripts\python.exe scripts/generate_incident_snapshot.py --help` -> `OK`.
5. Governanca de issue na trilha unica:
   - `BD-082` concluido tecnicamente.
   - trilha D8 encerrada tecnicamente; proximo passo e consolidacao operacional (janela de 30 dias).

## Atualizacao tecnica (2026-02-22) - D8 BD-081 implementado (tuning de performance e custo da plataforma)

1. Tuning SQL aplicado para caminhos quentes de operacao e mapa:
   - nova migration `db/sql/017_d8_performance_tuning.sql` com indices:
     - `ops.pipeline_checks` por status/check_name/created_at;
     - `ops.connector_registry` por `updated_at_utc + wave/status/source`;
     - `ops.frontend_events` por `name + event_timestamp_utc`;
     - trigram (`pg_trgm`) em nomes de `map.urban_road_segment`, `map.urban_poi` e `map.urban_transport_stop` para acelerar `geocode`.
2. Benchmark operacional ampliado:
   - `scripts/benchmark_api.py` passou a suportar `--suite ops`;
   - endpoints ops incluidos na medicao (`summary`, `readiness`, `pipeline-runs`, `pipeline-checks`, `connector-registry`, `source-coverage`, `sla`, `timeseries`);
   - alvo default da suite ops: `p95 <= 1500ms` (alinhado ao contrato dos endpoints `/v1/ops/*`).
3. Cobertura de contrato para tuning SQL:
   - `tests/contracts/test_sql_contracts.py` ganhou assert dedicado para `017_d8_performance_tuning.sql`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `13 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 19 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --help` -> `suite {executive,urban,ops,all}`.
5. Governanca de issue na trilha unica:
   - `#26` (`BD-081`) encerrada.
   - `#27` (`BD-082`) encerrada.
   - proximo passo operacional: consolidacao pos-D8 na janela de 30 dias.

## Atualizacao tecnica (2026-02-22) - D8 BD-080 implementado (carga incremental confiavel + reprocessamento seletivo)

1. Orquestracao incremental operacional publicada:
   - novo script `scripts/run_incremental_backfill.py` com selecao automatica de jobs baseada em historico de `ops.pipeline_runs`.
   - regra de decisao por par `job + reference_period`:
     - executa quando nao ha run previo;
     - executa quando ultimo status nao e `success`;
     - executa quando sucesso ficou "stale" (padrao `--stale-after-hours=168`);
     - permite reprocessamento seletivo com `--reprocess-jobs` e `--reprocess-periods`.
2. Hardening de operacao:
   - filtros de escopo por `--jobs` e `--exclude-jobs`;
   - suporte a fonte `partial` via `--include-partial`;
   - pos-carga condicional por periodo com `dbt_build` e `quality_suite` (toggle por `--skip-dbt` e `--skip-quality`);
   - relatorio padrao em `data/reports/incremental_backfill_report.json`.
3. Cobertura de teste da logica incremental:
   - nova suite `tests/unit/test_run_incremental_backfill.py` cobrindo:
     - parse de filtros CSV;
     - decisao `no_previous_run`;
     - decisao `fresh_success` (skip);
     - decisao `stale_success` (execute);
     - decisao por `latest_status != success`;
     - override de reprocessamento seletivo.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_incremental_backfill.py tests/unit/test_backfill_environment_history.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `9 passed`.
   - `.\.venv\Scripts\python.exe scripts/run_incremental_backfill.py --help` -> `OK`.
5. Governanca de issue na trilha unica:
   - `#25` (`BD-080`) encerrada.
   - `#26` (`BD-081`) promovida para `status:active`.
   - proximo item da fila unica: `D8/BD-081`.

## Acordo de foco (2026-02-22)

1. Trilha unica obrigatoria:
   - `#22` (`BD-070`) -> `#23` (`BD-071`) -> `#24` (`BD-072`).
2. Escopo congelado ate demo defensavel:
   - sem novas frentes de fonte/dominio que nao impactem diretamente o mapa executivo.
3. Entrega esperada para demonstracao:
   - valor visivel no mapa com prioridade explicavel por territorio;
   - fluxo estavel em estados `loading/error/empty/data`;
   - evidencias tecnicas registradas em `CHANGELOG` e neste `HANDOFF`.

## Atualizacao tecnica (2026-02-22) - D7 BD-072 implementado (trilhas de explicabilidade para prioridade/insight)

1. Explainability estruturada em prioridade e insights:
   - `src/app/schemas/qg.py` ganhou contratos:
     - `ExplainabilityCoverage`
     - `ExplainabilityTrail`.
   - `PriorityItem` e `InsightHighlightItem` agora retornam `explainability`.
2. Evidencia expandida para auditoria:
   - `PriorityEvidence` e `BriefEvidenceItem` passam a incluir `updated_at`.
   - trilha retorna metadados de score: versao/metodo/thresholds/ranking/pesos.
3. Cobertura territorial explicita por dominio:
   - `src/app/api/routes_qg.py` calcula cobertura por `reference_period + level + domain`:
     - `covered_territories`
     - `total_territories`
     - `coverage_pct`.
4. Navegacao de insight para triagem:
   - `GET /v1/insights/highlights` passa a retornar `deep_link` por item.
5. Rationale orientada a trilha:
   - `GET /v1/priority/list` adiciona contexto de ranking e cobertura na justificativa.
6. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py -q -p no:cacheprovider` -> `19 passed`.
7. Governanca de issue na trilha unica:
   - `BD-072` concluido tecnicamente.
   - proximo item da fila unica: `D8/BD-080`.

## Atualizacao tecnica (2026-02-22) - D7 BD-071 implementado (versionamento de score territorial e pesos)

1. Governanca de versao de score publicada:
   - migration nova `db/sql/016_strategic_score_versions.sql` com:
     - tabela `ops.strategic_score_versions`;
     - indice de unicidade para versao ativa (`uq_strategic_score_versions_active`);
     - view ativa `ops.v_strategic_score_version_active`;
     - seed idempotente da versao `v1.0.0`.
2. Mart Gold de prioridade evoluido para score versionado:
   - `db/sql/015_priority_drivers_mart.sql` agora aplica pesos por dominio/indicador e expande colunas:
     - `score_version`, `config_version`, `critical_threshold`, `attention_threshold`,
     - `domain_weight`, `indicator_weight`, `weighted_magnitude`.
   - compatibilidade de migracao preservada mantendo a ordem historica das colunas-base da view.
3. Config e automacao operacional:
   - `configs/strategic_engine.yml` com pesos default e mapas `domain_weights`/`indicator_weights`;
   - novo script `scripts/sync_strategic_score_versions.py` para sincronizacao idempotente no banco;
   - `scripts/backfill_robust_database.py` passa a sincronizar `strategic_score_versions` e reportar cobertura.
4. API executiva e contratos:
   - `src/app/api/routes_qg.py` passa a expor metadados/evidencias com `score_version`, `scoring_method` e pesos;
   - `src/app/schemas/qg.py` atualizado com campos opcionais de versao/pesos em prioridade, insights e briefs;
   - `src/app/api/strategic_engine_config.py` atualizado para carregar pesos versionados.
5. Scorecard e testes:
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com metricas:
     - `priority_drivers_missing_score_version_rows`
     - `strategic_score_total_versions`
     - `strategic_score_active_versions_min`
     - `strategic_score_active_versions_max`.
   - `tests/contracts/test_sql_contracts.py` ampliado para `015`/`016` e novas metricas.
   - `tests/unit/test_strategic_engine_config.py` ampliado para validar parsing de pesos.
6. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_strategic_engine_config.py -q -p no:cacheprovider -p no:tmpdir` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `12 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 18 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/sync_strategic_score_versions.py` -> `score_version=v1.0.0`, `upserted=1`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=28`, `warn=4`.
7. Governanca de issue na trilha unica:
   - `BD-071` concluido tecnicamente.
   - sequencia da fila unica avancou para `BD-072` (concluido na atualizacao superior deste documento).

## Atualizacao tecnica (2026-02-22) - D7 BD-070 implementado (mart Gold de drivers de prioridade)

1. Camada Gold de prioridade publicada:
   - migration nova `db/sql/015_priority_drivers_mart.sql` com view:
     - `gold.mart_priority_drivers`.
   - score deterministico por `reference_period + territory_level + domain` com:
     - `driver_rank`, `driver_total`, `driver_magnitude`;
     - `priority_score`, `priority_status`, `driver_percentile`;
     - `scoring_method='rank_abs_value_v1'`.
2. Endpoints executivos de prioridade migrados para o mart Gold:
   - `GET /v1/priority/list`
   - `GET /v1/priority/summary`
   - `GET /v1/insights/highlights`
   - metadados de resposta agora indicam `source_name=gold.mart_priority_drivers`.
3. Governanca operacional ampliada:
   - scorecard SQL (`db/sql/007_data_coverage_scorecard.sql`) com metricas:
     - `priority_drivers_rows`
     - `priority_drivers_distinct_periods`.
   - `scripts/init_db.py` com dependencia explicita de `007_data_coverage_scorecard.sql` para `015_priority_drivers_mart.sql`.
   - `scripts/backfill_robust_database.py` com bloco `coverage.priority_drivers_mart`.
4. Cobertura de contrato SQL adicionada:
   - `tests/contracts/test_sql_contracts.py` com assert dos objetos de `015_priority_drivers_mart.sql` e metricas de scorecard do mart.
5. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `78 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `11 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 17 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=24`, `warn=4`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
6. Governanca de issue na trilha unica:
   - `BD-070` concluido tecnicamente.
   - tentativa de sincronizacao no GitHub bloqueada por restricao de rede/proxy do ambiente local.
   - proximo item da fila unica: `BD-071`.

## Atualizacao tecnica (2026-02-22) - D6 BD-062 implementado (detectar drift de schema com alerta operacional)

1. Deteccao de drift integrada ao `quality_suite`:
   - novo check `check_source_schema_drift` em `src/pipelines/common/quality.py`;
   - validacoes por conector:
     - existencia da tabela alvo;
     - colunas obrigatorias ausentes;
     - incompatibilidade de tipo por coluna;
     - agregado `schema_drift_connectors_with_issues`.
2. Alerta operacional automatico habilitado:
   - drifts geram `fail` em `ops.pipeline_checks` via `quality_suite`;
   - scorecard SQL ampliado com metrica `schema_drift_fail_checks_last_7d` em `db/sql/007_data_coverage_scorecard.sql`.
3. Governanca de thresholds:
   - `configs/quality_thresholds.yml` com secao `schema_drift`:
     - `max_missing_required_columns`
     - `max_type_mismatch_columns`
     - `max_connectors_with_drift`.
4. Cobertura de teste adicionada:
   - `tests/unit/test_schema_drift_checks.py` (pass/fail para drift de colunas e tipos);
   - `tests/unit/test_quality_suite.py` atualizado para o novo check;
   - `tests/contracts/test_sql_contracts.py` atualizado com metrica de drift no scorecard.
5. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_schema_drift_checks.py tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/contracts/test_sql_contracts.py tests/contracts/test_schema_contract_connector_coverage.py -q -p no:cacheprovider` -> `78 passed`.
   - `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`, `total_checks=188`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=22`, `warn=4`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1` (SLO-1 abaixo da meta na janela).
6. Regra operacional da trilha:
   - issue implementada encerrada na mesma rodada:
     - `#21` (`BD-062`) -> `closed`.
     - `#22` (`BD-070`) promovida para `status:active`.
   - proximo item da fila unica: `BD-070`.

## Atualizacao tecnica (2026-02-22) - D6 BD-061 implementado (cobertura de testes de contrato por conector)

1. Cobertura de contratos por conector automatizada:
   - nova suite `tests/contracts/test_schema_contract_connector_coverage.py`;
   - validacao de cobertura minima `>= 90%` para conectores elegiveis (`implemented|partial`, nao internos, sem discovery interno).
2. Granularidade por conector adicionada:
   - testes parametrizados para garantir contrato por conector elegivel;
   - falha explicita com nome do conector ausente/quebrado.
3. Estrutura minima de contrato validada por conector:
   - `required_columns` nao vazio;
   - `column_types` nao vazio;
   - `schema_version` com padrao versionado (`v*`).
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_schema_contract_connector_coverage.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `61 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
5. Regra operacional da trilha D6:
   - issue implementada encerrada na mesma rodada:
     - `#20` (`BD-061`) -> `closed`.
     - `#21` (`BD-062`) promovida para `status:active`.
   - proximo item da fila unica: `BD-062`.

## Atualizacao tecnica (2026-02-22) - D6 BD-060 implementado (contratos de schema versionados por fonte)

1. Governanca de contratos de schema publicada:
   - migration nova `db/sql/014_source_schema_contracts.sql` com:
     - tabela `ops.source_schema_contracts`;
     - view ativa `ops.v_source_schema_contracts_active`;
     - suporte a versionamento por `connector_name + target_table + schema_version`.
2. Automacao de sincronizacao implementada:
   - novo modulo `src/pipelines/common/schema_contracts.py` para inferencia/normalizacao de contratos;
   - novo arquivo `configs/schema_contracts.yml` com defaults e overrides por conector;
   - novo script `scripts/sync_schema_contracts.py` para upsert/deprecacao de versoes.
3. Operacao e qualidade integradas:
   - `scripts/backfill_robust_database.py` passa a sincronizar contratos e reportar cobertura de `schema_contracts`;
   - `src/pipelines/common/quality.py` com check `check_source_schema_contracts`;
   - `src/pipelines/quality_suite.py` passa a executar checks de cobertura de contratos ativos;
   - `configs/quality_thresholds.yml` com secao `schema_contracts`;
   - `db/sql/007_data_coverage_scorecard.sql` com metrica `schema_contracts_active_coverage_pct`;
   - filtros de cobertura ajustados para excluir conectores de discovery/internos (`quality_suite`, `dbt_build`, `tse_catalog_discovery`).
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 16 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/sync_schema_contracts.py` -> `prepared=24`, `upserted=24`, `deprecated=0`.
   - `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=23`, `warn=2`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Regra operacional da trilha D6:
   - issue implementada encerrada na mesma rodada:
     - `#19` (`BD-060`) -> `closed`.
     - `#20` (`BD-061`) promovida para `status:active`.
   - proximo item da fila unica: `BD-061`.

## Atualizacao tecnica (2026-02-21) - D5 BD-052 implementado (mart Gold de risco ambiental territorial)

1. Camada Gold ambiental publicada no banco:
   - migration nova `db/sql/013_environment_risk_mart.sql` com view:
     - `gold.mart_environment_risk`.
   - cobertura por `territory_level`:
     - `municipality`
     - `district`
     - `census_sector`.
   - metrica executiva no mart:
     - `environment_risk_score`
     - `risk_percentile`
     - `risk_priority_rank`
     - `priority_status`.
2. API executiva de risco ambiental adicionada:
   - endpoint novo `GET /v1/environment/risk` em `src/app/api/routes_qg.py`;
   - filtros: `period`, `level` (`municipality|district|census_sector`), `limit`;
   - fallback de periodo para ultimo `reference_period` disponivel;
   - contrato em `src/app/schemas/qg.py`:
     - `EnvironmentRiskItem`
     - `EnvironmentRiskResponse`.
3. Governanca operacional e qualidade reforcadas:
   - `src/pipelines/common/quality.py` com check novo:
     - `check_environment_risk_mart`.
   - `src/pipelines/quality_suite.py` passa a incluir checks do mart Gold ambiental.
   - `configs/quality_thresholds.yml` ampliado com thresholds `environment_risk_mart_*`.
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com metricas:
     - `environment_risk_mart_municipality_rows`
     - `environment_risk_mart_district_rows`
     - `environment_risk_mart_census_sector_rows`
     - `environment_risk_mart_distinct_periods`.
   - `scripts/init_db.py` atualizado para ordenar dependencia `007 -> 013`.
   - `scripts/backfill_robust_database.py` ampliado com `coverage.environment_risk_mart`.
   - `src/app/api/cache_middleware.py` com cache para `GET /v1/environment/risk`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `102 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `51 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 15 SQL scripts`.
   - smoke API real:
     - `GET /v1/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
   - scorecard/readiness:
     - `scripts/export_data_coverage_scorecard.py` -> `pass=23`, `warn=1`.
     - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - quality checks do mart no ultimo run:
     - `environment_risk_mart_rows_municipality=pass` (`5`)
     - `environment_risk_mart_rows_district=pass` (`55`)
     - `environment_risk_mart_rows_census_sector=pass` (`545`)
     - `environment_risk_mart_distinct_periods=pass` (`5`)
     - `environment_risk_mart_null_score_rows=pass` (`0`).
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#18` (`BD-052`) -> `closed`.
     - `#19` (`BD-060`) promovida para `status:active`.
   - proximo item da fila unica: `BD-060`.

## Atualizacao tecnica (2026-02-21) - D5 BD-051 implementado (agregacoes ambientais distrito/setor)

1. Agregacao ambiental territorial publicada no banco:
   - migration nova `db/sql/012_environment_risk_aggregation.sql` com view:
     - `map.v_environment_risk_aggregation`.
   - cobertura por `territory_level`:
     - `district`
     - `census_sector`.
   - metrica sintetica por territorio:
     - `hazard_score`
     - `exposure_score`
     - `environment_risk_score`
     - `priority_status`.
2. API de mapa para risco ambiental adicionada:
   - endpoint novo `GET /v1/map/environment/risk` em `src/app/api/routes_map.py`;
   - filtros: `level` (`district|census_sector`), `period`, `include_geometry`, `limit`;
   - fallback de periodo para ultimo `reference_period` disponivel;
   - contrato em `src/app/schemas/map.py`:
     - `EnvironmentRiskItem`
     - `EnvironmentRiskCollectionResponse`.
3. Governanca operacional e qualidade reforcadas:
   - `scripts/init_db.py` atualizado para ordenar dependencia `007 -> 012` (scorecard depende da view ambiental).
   - `src/pipelines/common/quality.py` com check novo:
     - `check_environment_risk_aggregation`.
   - `src/pipelines/quality_suite.py` passa a incluir checks ambientais agregados.
   - `configs/quality_thresholds.yml` com secao `environment_risk`.
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com metricas:
     - `environment_risk_district_rows`
     - `environment_risk_census_sector_rows`
     - `environment_risk_distinct_periods`.
   - `scripts/backfill_robust_database.py` ampliado com bloco `coverage.environment_risk_aggregation`.
   - `src/app/api/cache_middleware.py` com cache para `GET /v1/map/environment/risk`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `49 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_mvt_tiles.py -q -p no:cacheprovider` -> `33 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 14 SQL scripts`.
   - smoke API real:
     - `GET /v1/map/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `count=5`.
   - scorecard/readiness:
     - `scripts/export_data_coverage_scorecard.py` -> `pass=19`, `warn=1`.
     - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - quality checks ambientais no ultimo run:
     - `environment_risk_rows_district=pass` (`55`)
     - `environment_risk_rows_census_sector=pass` (`545`)
     - `environment_risk_distinct_periods=pass` (`5`)
     - checks de nulos (`risk/hazard/exposure`) em `pass`.
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#17` (`BD-051`) -> `closed`.
     - `#18` (`BD-052`) promovida para `status:active`.
   - proximo item da fila unica: `BD-052`.

## Atualizacao tecnica (2026-02-21) - D5 BD-050 implementado (historico ambiental multi-ano)

1. Orquestracao dedicada para BD-050 publicada:
   - novo script `scripts/backfill_environment_history.py` com fluxo unico de:
     - bootstrap manual multi-ano (`INMET`, `INPE_QUEIMADAS`, `ANA`);
     - execucao dos conectores ambientais por periodo;
     - execucao opcional de `quality_suite` por periodo;
     - consolidacao de cobertura por fonte no relatorio final.
2. Hardening de integridade temporal no conector tabular:
   - `src/pipelines/common/tabular_indicator_connector.py` agora bloqueia carga quando houver coluna de ano com sinal valido e nenhum match com `reference_period`.
   - fallback anterior foi preservado apenas para payloads sem qualquer sinal temporal.
3. Governanca de cobertura ambiental reforcada:
   - `configs/quality_thresholds.yml` com metas explicitas:
     - `min_periods_inmet: 5`
     - `min_periods_inpe_queimadas: 5`
     - `min_periods_ana: 5`
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com metricas:
     - `inmet_distinct_periods`
     - `inpe_queimadas_distinct_periods`
     - `ana_distinct_periods`
   - `scripts/backfill_robust_database.py` agora exporta `coverage.environmental_sources` com `rows`, `distinct_periods`, `min_period`, `max_period`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_backfill_environment_history.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_coverage_checks.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `26 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_quality_suite.py -q -p no:cacheprovider` -> `12 passed`.
   - `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --help` -> `OK`.
   - smoke BD-050:
     - `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --periods 2025 --dry-run --skip-bootstrap --skip-quality --allow-blocked --output-json data/reports/bd050_environment_history_report.json` -> `success=2`, `blocked=1` (`INMET` com `403`), report gerado.
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#16` (`BD-050`) -> `closed`.
     - `#17` (`BD-051`) promovida para `status:active`.
   - proximo item da fila unica: `BD-051`.

## Atualizacao tecnica (2026-02-21) - D4 BD-042 implementacao de mart de mobilidade

1. Camada Gold de mobilidade entregue:
   - `db/sql/011_mobility_access_mart.sql` com `gold.mart_mobility_access`.
   - score de acesso e deficit por territorio (`municipality` e `district`) com:
     - densidade de pontos de transporte;
     - densidade viaria;
     - POIs de mobilidade;
     - metodo de alocacao explicito (`direct_measurement` vs `district_allocation_by_road_length_share`).
2. Hardening tecnico aplicado no SQL:
   - agregacoes separadas por dominio espacial (vias, transporte, POIs) para evitar sobrecontagem por join multiplo;
   - amarracao de populacao por periodo do SENATRAN com fallback para ultima populacao disponivel;
   - casts explicitos de `ROUND(..., 2)` para compatibilidade com Postgres.
3. API executiva entregue:
   - endpoint novo `GET /v1/mobility/access` em `src/app/api/routes_qg.py`;
   - filtros: `period`, `level`, `limit`;
   - metadata padronizada (`source_name=gold.mart_mobility_access`) e retorno vazio contratual quando nao houver dados.
4. Contratos e cache:
   - schemas novos em `src/app/schemas/qg.py` (`MobilityAccessItem`, `MobilityAccessResponse`);
   - `src/app/api/cache_middleware.py` atualizado para cachear `GET /v1/mobility/access`.
5. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `79 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 13 SQL scripts`.
   - smoke local via `TestClient`: `GET /v1/mobility/access?level=district&limit=5` -> `200`.

## Atualizacao tecnica (2026-02-21) - D4 BD-041 implementacao de transporte urbano

1. Conector novo de mobilidade municipal:
   - `src/pipelines/urban_transport.py` (`urban_transport_fetch`) com:
     - discovery remoto via Overpass para pontos de transporte (`bus_stop`, `public_transport`, `railway`, `ferry_terminal`);
     - fallback manual em `data/manual/urban/transport`;
     - Bronze snapshot + checks + carga idempotente em `map.urban_transport_stop`.
2. Dominio de mapa ampliado:
   - migration nova `db/sql/010_urban_transport_domain.sql`:
     - tabela `map.urban_transport_stop`;
     - indice GIST;
     - camada `urban_transport_stops` no catalogo;
     - view `map.v_urban_data_coverage` atualizada.
   - endpoint novo:
     - `GET /v1/map/urban/transport-stops`.
   - geocode urbano ampliado para `kind=transport` em `GET /v1/map/urban/geocode`.
   - tiles MVT ampliados para camada `urban_transport_stops`.
3. Orquestracao e qualidade:
   - `src/orchestration/prefect_flows.py` com `urban_transport_fetch` em `run_mvp_all` e `run_mvp_wave_7`.
   - `scripts/backfill_robust_database.py` com `urban_transport_fetch` no `wave7` e cobertura no report.
   - `src/pipelines/common/quality.py` com checks:
     - `urban_transport_stops_rows_after_filter`
     - `urban_transport_stops_invalid_geometry_rows`
   - `configs/quality_thresholds.yml` com `min_transport_rows`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -c "import json; from pipelines.urban_transport import run; print(json.dumps(run(reference_period='2026', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `rows_written=22`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_urban_connectors.py tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/contracts/test_sql_contracts.py -q` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Estado de encerramento de `BD-041`:
   - carga real validada em `map.urban_transport_stop`;
   - proxima execucao oficial da trilha D4: `BD-042`.

## Atualizacao operacional (2026-02-21) - BD-040 executado com backfill real

1. Bootstrap historico SENATRAN concluido:
   - script novo: `scripts/bootstrap_senatran_history.py`.
   - fontes oficiais coletadas para `2021..2024` e materializadas em:
     - `data/manual/senatran/senatran_diamantina_2021.csv`
     - `data/manual/senatran/senatran_diamantina_2022.csv`
     - `data/manual/senatran/senatran_diamantina_2023.csv`
     - `data/manual/senatran/senatran_diamantina_2024.csv`
   - evidencias em `data/reports/bootstrap_senatran_history_report.json`.
2. Backfill real do conector `senatran_fleet_fetch` executado para `2021..2025`:
   - `5/5` runs com `status=success`;
   - `rows_written=4` por ano em `silver.fact_indicator`.
3. Cobertura de `SENATRAN` validada no banco:
   - `reference_period` disponivel em `2021,2022,2023,2024,2025`.
4. Validacao operacional:
   - `scripts/export_data_coverage_scorecard.py` -> `pass=10`, `warn=1`.
   - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Dependencias de parsing Excel formalizadas no projeto:
   - `openpyxl` e `xlrd` adicionados em `requirements.txt` e `pyproject.toml`.

## Atualizacao tecnica (2026-02-21) - D4 BD-040 hardening SENATRAN

1. Conector SENATRAN endurecido para serie historica:
   - descoberta automatica de CSV remoto por ano na pagina oficial;
   - filtro de ano em URI remota para evitar carga com periodo divergente;
   - priorizacao de arquivo manual por `reference_period` no nome;
   - bloqueio de fallback manual com ano divergente (integridade temporal);
   - parser dedicado para CSV oficial com preambulo + parse numerico por milhares.
2. Cobertura de testes ampliada para SENATRAN:
   - discovery remoto por ano;
   - selecao/bloqueio de fallback manual por ano;
   - parse de CSV oficial com preambulo;
   - resolucao remota quando catalogo estatico esta vazio.
3. Infra de banco corrigida para execucao real:
   - `src/app/db.py` passou a cachear por `database_url` (string), eliminando erro `unhashable type: 'Settings'`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_db_cache.py tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
5. Dry-run multi-ano do conector:
   - `2021..2024`: `blocked` (sem fonte anual valida descoberta).
   - `2025`: `success` com fonte remota oficial.
6. Proximo passo operacional da trilha D4:
   - coletar/publicar arquivos SENATRAN anuais `2021..2024` em `data/manual/senatran/` (ou catalogo estatico versionado) e executar backfill real `2021..2025`.

## Atualizacao operacional (2026-02-20) - Filtro rigoroso de documentos

1. Governanca documental centralizada em `docs/GOVERNANCA_DOCUMENTAL.md`.
2. Nucleo ativo de decisao reforcado:
   - `docs/CONTRATO.md`
   - `docs/VISION.md`
   - `docs/PLANO_IMPLEMENTACAO_QG.md`
   - `docs/HANDOFF.md`
   - `docs/CHANGELOG.md`
3. Documentos descontinuados para decisao:
   - removidos do repositorio em 2026-02-20 (ver `docs/GOVERNANCA_DOCUMENTAL.md` secao 6).
4. Regra obrigatoria:
   - nenhum desses documentos descontinuados abre prioridade, trilha ou backlog.

## Atualizacao tecnica (2026-02-20) — Fase UX-P0 entregue

1. Escopo: corrigir todas as inconsistencias de UI/UX identificadas por auditoria visual de 10 telas.
2. Itens entregues (22 correcoes):
   - **UX-P0-01/02**: Helpers `formatValueWithUnit()`, `humanizeSourceName()`, `humanizeCoverageNote()`, `humanizeDatasetSource()` em `presentation.ts`.
   - **UX-P0-03/04**: SourceFreshnessBadge humanizado (source_name + coverage_note).
   - **UX-P0-05/06/07**: Home — "SVG fallback" renomeado; colunas tecnicas removidas de KPIs e Onda B/C.
   - **UX-P0-08/09**: Insights — severity + source humanizados.
   - **UX-P0-10/11/12**: Briefs — Brief ID removido, "Linha" → "Ponto", source humanizado.
   - **UX-P0-13/14/15**: Cenarios — indicator_name no subtitulo, "Leitura" → "Analise", label do campo.
   - **UX-P0-16**: Territorio 360 — coluna Codigo removida.
   - **UX-P0-17**: Eleitorado — zero display → "-".
   - **UX-P0-18**: PriorityItemCard — source humanizado.
   - **UX-P0-19/20**: Mapa — label e coluna tecnica removidos.
   - **UX-P0-21/22**: Backend — `_format_highlight_value()` melhorado + cenarios em pt-BR.
3. Arquivos modificados:
   - `frontend/src/shared/ui/presentation.ts` (helpers novos + unit mapping).
   - `frontend/src/shared/ui/SourceFreshnessBadge.tsx` (humanizacao).
   - `frontend/src/shared/ui/PriorityItemCard.tsx` (source humanizado).
   - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` (SVG label + colunas).
   - `frontend/src/modules/qg/pages/QgInsightsPage.tsx` (severity + source).
   - `frontend/src/modules/qg/pages/QgBriefsPage.tsx` (Brief ID + Linha + source).
   - `frontend/src/modules/qg/pages/QgScenariosPage.tsx` (indicator_name + Leitura + label).
   - `frontend/src/modules/qg/pages/QgMapPage.tsx` (label + coluna Metrica).
   - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` (coluna Codigo).
   - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` (zero display).
   - `src/app/api/routes_qg.py` (format + impact pt-BR).
   - Testes atualizados: `SourceFreshnessBadge.test.tsx`, `QgPages.test.tsx`.

## Atualizacao tecnica (2026-02-20) — Fase DATA entregue

1. Escopo: corrigir 8 inconsistencias de semantica de dados identificadas por auditoria visual.
2. Itens entregues:
   - **DATA-P0-01**: Score mono-territorial 100->50 (3 locais em routes_qg.py).
   - **DATA-P0-02**: Trend real via `_compute_trend()` + `_fetch_previous_values()`.
   - **DATA-P0-03**: Codigos tecnicos removidos de narrativas (5 endpoints).
   - **DATA-P0-04**: Formatacao pt-BR via `_format_highlight_value()`.
   - **DATA-P0-05**: Severidade em pt-BR no filtro de Insights.
   - **DATA-P0-06**: Narrativa de insights diversificada por dominio e severidade via `_build_insight_explanation()`.
   - **DATA-P0-07**: Jargao tecnico do mapa substituido por termos executivos.
   - **DATA-P0-08**: Dedup de formatadores em StrategicIndexCard.
3. Arquivos modificados:
   - `src/app/api/routes_qg.py` (backend — 6 alteracoes + 4 funcoes novas).
   - `frontend/src/modules/qg/pages/QgInsightsPage.tsx` (import + labels traduzidos).
   - `frontend/src/modules/qg/pages/QgMapPage.tsx` (8 substituicoes de labels).
   - `frontend/src/shared/ui/StrategicIndexCard.tsx` (rewrite para usar presentation.ts).
   - `tests/unit/test_qg_routes.py` (mock atualizado).
   - `frontend/src/modules/qg/pages/QgPages.test.tsx` (assertion atualizada).
   - `docs/BACKLOG_UX_EXECUTIVO_QG.md` (Fase DATA adicionada).

## Atualizacao de planejamento (2026-02-20) - Backlog UX executivo unificado

1. Backlog unico consolidado para correcoes de layout/legibilidade:
   - `docs/BACKLOG_UX_EXECUTIVO_QG.md`.
2. Ordem de execucao definida:
   - `P0` (estrutural/legibilidade) -> `P1` (harmonizacao visual) -> `P2` (refinamento).
3. Regra de foco:
   - nao iniciar novas frentes enquanto itens `UX-P0-*` nao estiverem entregues e validados.
4. Mapeamento de escopo:
   - backlog ja inclui arquivos/componentes alvo por pagina (`Prioridades`, `Mapa`, `Territorio 360`, `Insights`, `Cenarios`, `Briefs`, `Eleitorado`, `App shell`).

## Atualizacao operacional (2026-02-20) - Governanca de issues GitHub

1. Trilha ativa oficial no GitHub:
   - `BD-033` criada em `#28` com label `status:active`.
2. Fechamento de item concluido:
   - `BD-021` (`#8`) encerrada por entrega tecnica concluida.
3. Bloqueios explicitados por sequencia:
   - labels `status:blocked` e `status:external` criadas para leitura operacional.
   - `BD-020` (`#7`) marcada como `status:external` + `status:blocked` (dependencia externa CECAD).
   - issues abertas de D4-D8 marcadas como `status:blocked` ate fechamento da trilha ativa.
4. Regra operacional mantida:
   - nenhuma reativacao de item bloqueado antes do gate de saida de `BD-033` (`#28`).

## Atualizacao operacional (2026-02-20) - Fechamento de gate BD-033 + fase 2

1. Gate tecnico da trilha ativa revalidado:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.
2. Pacote de confiabilidade (fase 2) executado:
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json`
     -> `pass=5`, `warn=8`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json`
     -> `READY`, `hard_failures=0`, `warnings=0`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json`
     -> `ALL PASS`, p95 urbano entre `103.7ms` e `123.5ms`.
3. Evidencias atualizadas:
   - `data/reports/data_coverage_scorecard.json`
   - `data/reports/benchmark_urban_map.json`
4. Estado de issue:
   - `BD-033` encerrada no GitHub em `2026-02-20` (`issue #28`).

## Atualizacao tecnica (2026-02-20) - Hotfix UX mapa (legibilidade + area util)

1. Correcoes de legibilidade dos controles do mapa:
   - `frontend/src/styles/global.css` ajustado para garantir contraste dos botoes em:
     - `Modo de visualizacao`;
     - `Mapa base`;
     - toggle da sidebar (`map-sidebar-toggle`) na Home.
   - impacto: botoes nao selecionados deixaram de ficar visualmente "invisiveis".
2. Correcoes de dimensao/utilizacao de area do mapa:
   - `frontend/src/styles/global.css` com altura ampliada em `map-canvas-shell`.
   - `map-dominant` e `map-dominant-canvas` ajustados para evitar area vazia abaixo do mapa.
   - classe `map-overview-canvas` passou a ocupar a altura util do layout dominante.
3. Correcoes de zoom inicial/contextual:
   - `frontend/src/modules/qg/pages/QgMapPage.tsx`:
     - `resolveContextualZoom` passa a respeitar piso do contexto (territorial/urbano), evitando abertura em `z0`.
     - zoom inicial do mapa aplica piso contextual ao ler query string.
   - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
     - zoom inicial/minimo da Home passa a usar piso recomendado por nivel.
4. Regressao de testes atualizada:
   - `frontend/src/modules/qg/pages/QgPages.test.tsx` ajustado para novo comportamento de piso de zoom.
5. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-20) - Painel de filtros do mapa situacional (layout e formatacao)

1. Reposicionamento do painel de filtros na Home:
   - `frontend/src/styles/global.css` deixou de usar painel sobreposto ao mapa no desktop.
   - `map-dominant-sidebar` passou a operar como coluna lateral (docked), mantendo controle por `Ocultar/Mostrar filtros`.
   - `frontend/src/shared/ui/MapDominantLayout.tsx` atualizado para refletir semantica de layout dominante com sidebar colapsavel.
2. Formatacao interna do menu lateral:
   - botoes de `Aplicar/Limpar` alinhados em grade com largura consistente.
   - botoes de navegacao (`Focar selecionado` e `Recentrar mapa`) padronizados em largura e empilhamento no painel.
   - seletor de `Mapa base` reorganizado em grade para evitar desalinhamento.
3. Controle de overflow visual:
   - cards e blocos do painel (`Situacao geral`, metadados de fonte, notas) receberam quebra de linha segura (`overflow-wrap`) para evitar texto vazando.
   - ajuste de topo do botao de toggle para fora da area do mapa (sem sobreposicao no canvas).
4. Validacao executada:
   - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao tecnica (2026-02-20) - Transparencia de classificacao de camadas (mapa)

- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - classificacao de camada (`oficial`, `proxy`, `hibrida`) agora aparece de forma explicita em:
    - camada recomendada do contexto atual;
    - camada ativa no seletor detalhado;
    - metadados visuais do painel do mapa.
  - tooltip da camada ativa passou a priorizar metodologia (`proxy_method`) para leitura rapida de limitacoes.
  - fluxo de `local_votacao` foi preservado, com transparencia adicional sobre a natureza `proxy` da camada.
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - painel lateral da Home executiva passou a exibir classificacao da camada detalhada ativa, com hint de metodologia.
  - objetivo: manter consistencia de leitura entre `Visao Geral` e `Mapa`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - regressao ampliada para validar exibicao de classificacao no fluxo eleitoral detalhado (`territory_polling_place`).
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao tecnica (2026-02-20) - Quality Suite (ativacao de checks de camadas do mapa)

- `src/pipelines/quality_suite.py`:
  - `quality_suite` passou a executar `check_map_layers` dentro do fluxo padrao.
  - impacto: checks de cobertura/geom de camadas territoriais (`map_layer_rows_*` e `map_layer_geometry_ratio_*`) voltam a ser persistidos em `ops.pipeline_checks` a cada rodada de qualidade.
  - alinhamento com backlog D3/D6: readiness de camadas e governanca de qualidade ficam acoplados ao pipeline oficial.
- `tests/unit/test_quality_suite.py`:
  - novo teste unitario garantindo que `check_map_layers` e executado e serializado no resultado da `quality_suite`.
- `tests/unit/test_quality_coverage_checks.py`:
  - ajuste do teste de cobertura temporal por fonte para refletir o mapa atual de fontes do `fact_indicator` (`DATASUS..CENSO_SUAS`), evitando falso negativo por ordem incompleta.
- Validacao executada:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-20) - Home QG (degradacao parcial de prioridades/destaques)

- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - Home executiva deixou de falhar por completo quando apenas `Top prioridades` ou `Destaques` estiverem indisponiveis.
  - hard-fail da pagina permanece restrito ao nucleo de leitura (`kpis_overview` + `priority_summary`).
  - blocos `Top prioridades` e `Destaques` agora possuem estados independentes `loading/error/empty` com `request_id` e `Tentar novamente`.
  - objetivo: preservar navegacao do mapa, situacao geral e acoes rapidas mesmo com falha parcial de dados secundarios.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - nova regressao valida falha simultanea de `priority preview` e `insights highlights` sem derrubar a Home.
  - cobertura inclui exibicao de `request_id` e retry dedicado por bloco.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao tecnica (2026-02-20) - Mapa executivo (estados de suporte padronizados)

- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - estados auxiliares do mapa (manifesto de camadas, cobertura e metadados de estilo) padronizados com `StateBlock`.
  - erros desses componentes agora exibem mensagem de API + `request_id` quando disponivel.
  - cada estado de erro recebeu acao `Tentar novamente` com `refetch` dedicado.
  - estados de carregamento explicitos adicionados para manifesto/cobertura/estilo, evitando lacunas de feedback no fluxo operacional.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - novas regressões cobrindo:
    - erro de manifesto + metadados de estilo com retry e `request_id`;
    - erro de cobertura com retry sem quebrar a interacao principal do mapa.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `21 passed`.
  - `npm --prefix frontend run test -- --run` -> `77 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao tecnica (2026-02-20) - Boundary de erro por rota (frontend)

- `frontend/src/app/RouteRuntimeErrorBoundary.tsx`:
  - novo error boundary de runtime para telas roteadas, com fallback padronizado via `StateBlock`.
  - exibicao de contexto de falha por rota (`Falha na tela: <rota>`) + acao de retry sem reload total.
  - emissao de telemetria `frontend_error/route_runtime_error` com `route_label`, `message` e `component_stack`.
- `frontend/src/app/router.tsx`:
  - `withPageFallback` passou a encapsular cada pagina em `RouteRuntimeErrorBoundary` com rotulo explicito.
  - objetivo: evitar tela branca em erro de render e manter navegacao operacional previsivel.
- `frontend/src/app/RouteRuntimeErrorBoundary.test.tsx`:
  - novo teste cobrindo:
    - exibicao de estado de erro e emissao de telemetria em crash de render;
    - recuperacao da tela apos `Tentar novamente`.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/app/RouteRuntimeErrorBoundary.test.tsx src/app/router.smoke.test.tsx src/modules/qg/pages/QgPages.test.tsx src/modules/ops/pages/OpsPages.test.tsx` -> `32 passed`.
  - `npm --prefix frontend run test -- --run` -> `75 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao tecnica (2026-02-20) - Ops Health (refresh + regressao readiness)

- `frontend/src/modules/ops/pages/OpsHealthPage.tsx`:
  - adicionado botao `Atualizar painel` no bloco `Status geral` para refetch manual dos datasets operacionais da tela.
  - fluxo de recarga consolidado em funcao unica (`refetchAll`) reutilizada no erro (`onRetry`) e no refresh manual para manter comportamento consistente.
- `frontend/src/modules/ops/pages/OpsPages.test.tsx`:
  - novo teste de regressao cobrindo transicao de readiness no `OpsHealthPage`:
    - estado inicial `READY`;
    - refresh manual via botao;
    - atualizacao para `NOT_READY` com exibicao de `Hard failures`.
- Validacao executada:
  - `npm --prefix frontend run test -- --run` -> `73 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-20) - Home QG (camada detalhada coerente)

- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - seletor `Camada detalhada (Mapa)` agora aparece somente quando `Nivel territorial` estiver em `secao_eleitoral`.
  - propagacao de camada detalhada para links deixa de ocorrer fora do contexto eleitoral detalhado.
  - links de `Mapa detalhado` com camada detalhada passam a forcar contexto coerente com `level=secao_eleitoral`, evitando deep-link ambiguo.
  - ao trocar para nivel diferente de `secao_eleitoral`, a selecao local de camada detalhada e limpa para evitar estado residual.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - regressao atualizada para validar exibicao condicional do seletor detalhado e propagacao coerente de `layer_id` + `level`.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-20) - Estabilizacao mapa + eleitorado

- Mapa vetorial:
  - `frontend/src/shared/ui/VectorMap.tsx` corrigido para evitar recenter forcado durante zoom.
  - erros de abort/cancelamento deixam de acionar fluxo de erro visual.
  - `QgMapPage` e `QgOverviewPage` nao derrubam mais automaticamente para SVG em erro transitorio do vetor.
- Backend de tiles:
  - `src/app/api/routes_map.py` passou a usar geometria saneada (`ST_IsValid`/`ST_MakeValid`) no caminho territorial de tiles MVT para reduzir `503`.
- Eleitorado:
  - `src/app/api/routes_qg.py` com fallback de binding de ano logico x ano de armazenamento outlier.
  - resultado pratico: requests `year=2024` voltam a responder com dados mesmo em base com `reference_year=9999`.
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` recebeu tratamento de estado vazio/erro mais explicito para cenarios sem dados.
- Correcao de regressao de render:
  - erro de hooks (`Rendered more hooks than during the previous render`) removido em:
    - `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
    - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
- Usabilidade:
  - paginacao adicionada em Insights e na tabela de indicadores do Territorio 360 para evitar listas extensas sem controle.

## Validacao executada (2026-02-20)

- Backend:
  - `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
- Frontend:
  - `npm --prefix frontend run test -- --run` -> `72 passed`.
  - `npm --prefix frontend run build` -> `OK`.
- Smoke API (eleitorado):
  - `GET /v1/electorate/summary?level=municipality&year=2024` -> `200`, `38127` eleitores.
  - `GET /v1/electorate/map?level=municipality&year=2024&metric=voters` -> `200`, com itens retornados.

## Atualizacao tecnica (2026-02-20) - Mapa semantico (sem dado)

- `frontend/src/shared/ui/VectorMap.tsx`:
  - coropletico vetorial deixou de mapear ausencia de valor para faixa baixa.
  - features sem metrica agora usam cor neutra (`#d1d5db`), separando claramente "sem dado" de "baixo desempenho".
  - modos `points` e `heatmap` passaram a considerar somente features com valor presente.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - legenda visual ganhou chip `Sem dado`, alinhado ao comportamento do mapa vetorial.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-20) - Mapa com rotulos e zoom contextual

- `frontend/src/shared/ui/VectorMap.tsx`:
  - camada ativa agora exibe rotulos contextuais a partir de propriedades disponiveis (`label`, `name`, `tname`, `territory_name`, `road_name`, `poi_name`, `category`).
  - camadas lineares urbanas usam `symbol-placement=line` para leitura mais natural de vias.
  - atribuicao de basemap normalizada:
    - `(c) OpenStreetMap contributors`
    - `(c) OpenStreetMap contributors (c) CARTO`
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - `Aplicar filtros` agora respeita zoom minimo contextual por escopo/nivel.
  - piso de zoom explicito para camadas urbanas e ajuste por metadata de camada (`zoom_min`).
  - leitura de apoio adicionada na UI: `Zoom contextual minimo recomendado`.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Diretriz operacional sem dispersao (2026-02-19)

- Diretriz oficial de foco publicada e consolidada em `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` (secoes 7, 8 e 9).
- Ordem de execucao obrigatoria no ciclo atual:
  - 1) estabilizar telas e fluxo de decisao (`/visao-geral`, `/mapa`, `/territorio-360`, `/eleitorado`);
  - 2) fechar gates de confiabilidade (qualidade/readiness/smokes e evidencias operacionais);
  - 3) fechar lacunas criticas de conectores e cobertura territorial;
  - 4) so entao ampliar escopo (D4/D5) com novas frentes.
- Regra de priorizacao ativa:
  - nao abrir nova frente enquanto houver pendencia critica em UX, dados ou contrato tecnico da etapa corrente.
  - qualquer item novo fora da trilha principal entra como backlog, sem interromper o fechamento da etapa em andamento.

## Atualizacao tecnica (2026-02-19) - QG Prioridades (paginacao)

- `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`:
  - lista de prioridades passou a suportar paginacao client-side com:
    - seletor `Itens por pagina` (`12`, `24`, `48`);
    - controles `Anterior`/`Proxima`;
    - indicador `Pagina X de Y`.
  - pagina atual reinicia ao aplicar/limpar filtros e ao alterar tamanho de pagina.
  - resumo da lista agora evidencia `visiveis`, `filtradas` e `retorno bruto`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - novo teste de regressao para cenario com `30` prioridades, validando navegacao entre paginas.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx` -> `11 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-19) - Mapa vetorial (controles de navegacao)

- `frontend/src/shared/ui/VectorMap.tsx`:
  - controle nativo de navegacao configurado com zoom + bussola.
  - `FullscreenControl` habilitado quando disponivel no runtime.
  - `ScaleControl` habilitado (unidade metrica) no canto inferior esquerdo.
  - `AttributionControl` compacto habilitado no canto inferior direito.
  - atribuicao dos basemaps aplicada na fonte raster:
    - `streets`: `(c) OpenStreetMap contributors`
    - `light`: `(c) OpenStreetMap contributors (c) CARTO`
- `frontend/src/styles/global.css`:
  - refinamento visual dos controles `maplibregl` (grupo, botoes, escala e atribuicao).
  - ajustes de posicionamento e responsividade para reduzir sobreposicao em viewport menor.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao tecnica (2026-02-19) - Estabilizacao de telas criticas

- `Territorio 360`:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` agora trata `404` do perfil como estado vazio orientado (sem quebrar a tela).
  - filtros permanecem ativos no estado vazio para troca imediata de territorio/periodo.
  - regressao coberta em `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`.
- `Eleitorado`:
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` passou a aplicar fallback automatico para o ultimo ano com dados quando o ano filtrado retorna vazio.
  - aviso explicito de fallback exibido na tela, mantendo leitura executiva (KPIs/tabela/composicao) sem tela morta.
  - cobertura de teste ampliada em `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`.
- `Mapa executivo`:
  - `frontend/src/shared/ui/VectorMap.tsx` com opacidade de preenchimento e contorno territorial adaptativos por basemap.
  - objetivo: reduzir efeito de "bloco chapado" do coropletico e preservar contexto de navegacao no mapa-base.
- Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx` -> `11 passed`.
  - `npm --prefix frontend run build` -> `OK`.

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
  - tiles urbanos multi-zoom habilitados no endpoint vetorial existente:
    - `GET /v1/map/tiles/urban_roads/{z}/{x}/{y}.mvt`
    - `GET /v1/map/tiles/urban_pois/{z}/{x}/{y}.mvt`
    - suporte mantido para cache/ETag (`Cache-Control`, `ETag`, `X-Tile-Ms`).
  - catalogo e cobertura de camadas no backend de mapa ampliados para dominio urbano via query param:
    - `GET /v1/map/layers?include_urban=true`
    - `GET /v1/map/layers/coverage?include_urban=true`
    - `GET /v1/map/layers/readiness?include_urban=true`
  - contrato tecnico territorial mantido sem mistura de escopos:
    - `GET /v1/territory/layers/*` opera com `include_urban=false`.
  - monitor tecnico de camadas atualizado no frontend Ops:
    - `OpsLayersPage` agora consulta `GET /v1/map/layers/readiness`.
    - filtro de escopo suportado: `Territorial`, `Territorial + Urbano`, `Somente urbano`.
    - resumo operacional adicional publicado na tela:
      - cards agregados (`Camadas no recorte`, `Readiness pass|warn|fail|pending`).
      - grade de "Resumo rapido das camadas" por item com chips de `rows`, `geom` e `readiness`.
    - cobertura de teste frontend ampliada em `frontend/src/modules/ops/pages/OpsPages.test.tsx`.
  - politica de cache HTTP para camadas ajustada:
    - `/v1/map/layers/readiness` e `/v1/map/layers/coverage` com `max-age=60`.
    - `/v1/map/layers` mantido em `max-age=3600`.
  - qualidade ampliada:
    - `quality_suite` executa `check_urban_domain`.
    - thresholds urbanos em `configs/quality_thresholds.yml`.
  - scorecard de cobertura ampliado:
    - `urban_road_rows` e `urban_poi_rows` em `ops.v_data_coverage_scorecard`.
  - validacao deste incremento:
    - `pytest` focado em connectors/map/quality/flows/contracts: `40 passed`.
    - `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`: `9 passed`.
    - `npm --prefix frontend run test`: `66 passed`.
    - `npm --prefix frontend run build`: `OK`.
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
    - escopo explicito de camada no `QgMapPage`:
      - `Territorial` (manifestao de camadas por nivel)
      - `Urbana` (`urban_roads` / `urban_pois`)
    - `VectorMap` atualizado para renderizar camadas lineares (`layer_kind=line`) para viario urbano.
  - fechamento de lacunas de estrutura de camadas (2026-02-19):
    - backend de mapa com camada proxy de bairro: `territory_neighborhood_proxy` (base setorial) no catalogo, metadata, readiness e tiles.
    - `QgMapPage` com orientacao explicita para `local_votacao` no fluxo eleitoral:
      - seletor `Camada eleitoral detalhada`
      - nota de camada ativa para `Locais de votacao`
      - leitura contextual `local_votacao` no card de selecao.
    - `QgOverviewPage` passou a aplicar `Camada detalhada (Mapa)` no proprio mapa dominante, alem dos links para `/mapa`.
    - `OpsLayersPage` ganhou alerta de degradacao por camada (`fail`, `warn`, `pending`) para triagem tecnica imediata.
    - fallback SVG bloqueado para escopo urbano com mensagem orientativa (somente modo vetorial).
    - teste de regressao para URL prefill urbana em `frontend/src/modules/qg/pages/QgPages.test.tsx`.
    - overrides por ambiente em `frontend/.env.example`:
      - `VITE_MAP_BASEMAP_STREETS_URL`
      - `VITE_MAP_BASEMAP_LIGHT_URL`
  - `BD-033` avancado (iteracao atual) com deep-link completo:
    - `QgMapPage` sincroniza query string com recorte aplicado e estado de visualizacao:
      - `metric`, `period`, `level`, `scope`, `layer_id`, `territory_id`, `basemap`, `viz`, `renderer`, `zoom`.
    - `QgMapPage` passou a ler `viz`, `renderer` e `zoom` no carregamento inicial.
    - botao `Limpar` reseta baseline visual (`streets`, `choropleth`, mapa vetorial, `zoom=4`).
    - cobertura de teste ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx` para prefill e sync de URL.
    - `VectorMap` passou a ser carregado sob demanda (`React.lazy` + `Suspense`) no `QgMapPage`.
    - efeito imediato no build frontend:
      - `QgMapPage-*.js` ~`19KB` (antes ~`1.0MB`).
      - chunk pesado isolado em `VectorMap-*.js`.
    - refinamento de UX responsiva no mapa executivo:
      - toolbar de controles organizada em blocos (`modo`, `mapa base`, `renderizacao`) com layout responsivo.
      - selectors e controle de zoom ajustados para evitar overflow horizontal em viewport menor.
      - shell visual do mapa com altura fluida (`.map-canvas-shell`) para consistencia desktop/mobile.
    - navegacao territorial ampliada para aproximar UX de mapa operacional:
      - busca rapida de territorio no `QgMapPage` (`Buscar territorio` + `Focar territorio`).
      - acoes diretas no painel de filtro:
        - `Focar selecionado`
        - `Recentrar mapa`
      - `VectorMap` com foco por territorio selecionado via ajuste de camera (`fitBounds`/`easeTo`).
      - `VectorMap` com sinais de controle de viewport:
        - `focusTerritorySignal`
        - `resetViewSignal`
      - fallback seguro para ambiente de testes quando mocks nao expoem:
        - `easeTo`
        - `fitBounds`
        - `GeolocateControl`
    - acoes contextuais urbanas publicadas no card de selecao:
      - filtro rapido por classe/categoria (`/v1/map/urban/roads` e `/v1/map/urban/pois`).
      - geocodificacao contextual (`/v1/map/urban/geocode`).
      - consulta de POIs proximos ao ponto clicado (`/v1/map/urban/nearby-pois`).
      - links territoriais (`/territorio`, `/prioridades`, `/briefs`) mantidos apenas para escopo territorial.
    - contrato de tiles urbanos enriquecido para contexto operacional:
      - `urban_roads` inclui `road_class`, `is_oneway`, `source`.
      - `urban_pois` inclui `category`, `subcategory`, `source`.
      - `VectorMap` passou a propagar `lon`/`lat` da selecao para habilitar consulta por proximidade.
    - `QgOverviewPage` evoluida para `Layout B` (mapa dominante):
      - uso de `MapDominantLayout` para destacar o mapa na Home executiva.
      - painel lateral colapsavel com filtros principais, cards de status e acoes rapidas.
      - leitura do territorio selecionado diretamente no painel lateral.
      - ajustes de CSS para reduzir overflow e melhorar responsividade do painel do mapa.
    - Home executiva evoluida para modo vetorial no mapa dominante:
      - `QgOverviewPage` agora usa `VectorMap` na area principal da Home com fallback SVG.
      - basemap comutavel (`Ruas`, `Claro`, `Sem base`) e zoom adicionados no painel lateral.
      - controles de navegacao adicionados no painel lateral:
        - `Focar selecionado`
        - `Recentrar mapa`
      - clique no mapa vetorial sincroniza territorio selecionado no contexto lateral.
    - suites de navegacao ajustadas para nova estrutura de links no mapa:
      - `router.smoke.test.tsx` atualizado para selecionar link `Abrir perfil` de forma robusta.
      - `e2e-flow.test.tsx` atualizado para o mesmo comportamento.
    - cobertura de teste ampliada:
      - `QgPages.test.tsx` valida foco por busca e sincronizacao de `territory_id` na URL.
    - build frontend com chunking manual configurado (`frontend/vite.config.ts`):
      - chunks dedicados para `vendor-react`, `vendor-router`, `vendor-query`, `vendor-maplibre`, `vendor-misc`.
      - `index` reduzido para ~`12KB` (gzip ~`4.3KB`) com melhor carregamento inicial.
    - validacao adicional:
      - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx`: `18 passed`.
      - `npm --prefix frontend run test`: `69 passed`.
      - `npm --prefix frontend run build`: `OK`.

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

## [HISTORICO] Proximos passos imediatos (apos iteracao readiness API)

1. Expor `GET /v1/ops/readiness` tambem no painel tecnico `/admin` como card de status unico
   para triagem rapida de ambiente.
2. Adicionar teste E2E curto cobrindo o fluxo `OpsHealthPage` com transicao
   `READY -> NOT_READY` por mocks de readiness.
3. Consolidar janela operacional padrao do time (historico x corrente) em `CONTRATO.md`
   para evitar divergencia de leitura entre scripts, API e frontend.
4. Avancar no fechamento de UX/QG (error boundaries por rota + mensagens de estado)
   antes do go-live controlado.

## [HISTORICO] Proximos passos imediatos (trilha de robustez maxima de dados)

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

## [HISTORICO] 5) Proximos passos recomendados

### Prioridade alta
1. Fechar estabilizacao de UX nas telas executivas (`/mapa`, `/territorio/:id`, `/eleitorado`) e registrar evidencias de teste.
2. Revalidar homologacao ponta a ponta em ambiente limpo (backend + frontend + benchmark + readiness).
3. Concluir exposicao operacional da camada eleitoral territorial (`local_votacao`) no frontend.

### Prioridade media
1. Consolidar runbooks de operacao e rotina semanal de robustez de dados.
2. Fortalecer cobertura de testes de regressao para fluxos de erro/vazio do frontend.
3. Executar ciclo de revisao de performance com metas p95 (executivo e urbano).

### Prioridade baixa
1. Evoluir backlog pos-v2 do mapa (split view, time slider, comparacao temporal).
2. Ajustar ergonomia final do `/admin` sem misturar UX tecnica com UX executiva.

## 6) Comandos uteis

- Testes:
  - `pytest -q -p no:cacheprovider`
- Fluxo completo em dry-run:
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2025', dry_run=True))"`
- Sincronizar registry:
  - `python scripts/sync_connector_registry.py`
- Rodar qualidade:
  - `python -c "from pipelines.quality_suite import run; print(run(reference_period='2025', dry_run=False))"`
- Subir API + frontend no Windows sem `make`:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_up.ps1`
- Encerrar API + frontend iniciados pelo launcher:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_down.ps1`







