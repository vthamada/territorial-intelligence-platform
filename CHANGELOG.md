# Changelog

Todas as mudancas relevantes do projeto devem ser registradas aqui.

## 2026-02-10

### Changed
- `labor_mte_fetch` evoluido para tentar ingestao automatica via FTP do MTE antes do fallback manual.
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

### Added
- Novos testes unitarios do MTE para:
  - selecao de melhor candidato de arquivo no FTP
  - derivacao de metricas por `saldomovimentacao`
  - parse de `MTE_FTP_ROOT_CANDIDATES`
  - selecao por ano presente no caminho da pasta
- Runbook operacional do MTE em `docs/MTE_RUNBOOK.md` (FTP + fallback manual + troubleshooting).
- Endpoints de observabilidade operacional na API:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - filtros temporais em `pipeline-runs` (`started_from`/`started_to`)
  - filtros temporais em `pipeline-checks` (`created_from`/`created_to`)
  - filtros temporais em `connector-registry` (`updated_from`/`updated_to`)
- Testes unitarios da API de observabilidade em `tests/unit/test_ops_routes.py`.
- Check operacional no `quality_suite` para validar execucao dos conectores MVP-3 por `reference_period`.
- Teste unitario do check operacional em `tests/unit/test_quality_ops_pipeline_runs.py`.
- Testes de integracao de fluxo para `run_mvp_wave_3` em `tests/unit/test_prefect_wave3_flow.py`.

### Verified
- `pytest -q tests/unit/test_mte_labor.py -p no:cacheprovider`: `9 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_quality_ops_pipeline_runs.py -p no:cacheprovider`: `4 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `6 passed`.
- `pytest -q tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `2 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `9 passed`.
- `pytest -q -p no:cacheprovider`: `58 passed`.

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
