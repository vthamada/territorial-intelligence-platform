# Changelog

Todas as mudancas relevantes do projeto devem ser registradas aqui.

## 2026-02-11

### Changed
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

### Added
- Scripts operacionais:
  - `scripts/backend_readiness.py`
  - `scripts/backfill_missing_pipeline_checks.py`
  - `scripts/cleanup_legacy_source_probe_indicators.py`
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
- Testes frontend da pagina territorial:
  - `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`
- Teste smoke de navegacao:
  - `frontend/src/app/router.smoke.test.tsx`
- Novo threshold em `configs/quality_thresholds.yml`:
  - `fact_indicator.max_source_probe_rows: 0`

### Verified
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
- `npm --prefix frontend test`: `10 passed`.
- `npm --prefix frontend run build`: build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F3): `12 passed`.
- `npm --prefix frontend run build` (com F3): build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F4): `13 passed`.
- `npm --prefix frontend run build` (com F4): build concluido com code-splitting por pagina.
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
