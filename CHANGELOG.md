# Changelog

Todas as mudancas relevantes do projeto devem ser registradas aqui.

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
