# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-10

## 1) O que foi implementado ate agora

### Arquitetura e operacao
- Estrutura por ondas (MVP-1, MVP-2, MVP-3) mantida.
- Bronze/Silver/Gold operacionais com manifestos em `data/manifests/...`.
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
  - conector em modo `partial` (bloqueio de login no portal)
  - tentativa automatica via FTP `ftp://ftp.mtps.gov.br/pdet/microdados/`
  - fallback manual por `data/manual/mte` (CSV/TXT/ZIP)
  - suporte a derivacao de admissoes/desligamentos/saldo a partir de `saldomovimentacao`
  - configuracao via `.env` para host/porta/raizes/profundidade/limite de varredura FTP

### Registro de conectores
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` marcado como `partial`
  - nota operacional com tentativa FTP + fallback manual documentado
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
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - `tests/unit/test_prefect_wave3_flow.py`
- Suite validada: `58 passed`.

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcional.
- Conectores MVP-1 e MVP-2: `implemented`.
- Conectores MVP-3:
  - INEP, DATASUS, SICONFI: `implemented` com ingestao real.
  - MTE: `partial` por restricao de autenticacao no portal web; operacao via FTP e fallback manual.
- `pip check`: sem dependencias quebradas.

## 3) Arquivos-chave alterados neste ciclo

- `src/app/api/error_handlers.py`
- `src/pipelines/datasus_health.py`
- `src/pipelines/inep_education.py`
- `src/pipelines/siconfi_finance.py`
- `src/pipelines/mte_labor.py`
- `src/app/api/routes_ops.py`
- `src/app/api/main.py`
- `src/pipelines/common/quality.py`
- `src/pipelines/quality_suite.py`
- `src/app/settings.py`
- `configs/connectors.yml`
- `configs/quality_thresholds.yml`
- `requirements.txt`
- `tests/unit/test_api_contract.py`
- `tests/unit/test_datasus_health.py`
- `tests/unit/test_inep_education.py`
- `tests/unit/test_siconfi_finance.py`
- `tests/unit/test_mte_labor.py`
- `tests/unit/test_ops_routes.py`
- `tests/unit/test_quality_ops_pipeline_runs.py`
- `tests/unit/test_prefect_wave3_flow.py`
- `docs/MTE_RUNBOOK.md`
- `README.md`

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
1. O conector tenta baixar automaticamente via FTP do MTE.
2. Se nao encontrar arquivo via FTP, usar arquivo manual de Novo CAGED (CSV/TXT/ZIP) em `data/manual/mte`.
3. Executar `labor_mte_fetch`:
   - `dry_run=True` para validar
   - `dry_run=False` para gravar Silver/Bronze/ops

## 5) Proximos passos recomendados

### Prioridade alta
1. Validar em ambiente real o padrao de nomes de arquivos do FTP para otimizar a selecao automatica.
2. Adicionar endpoint consolidado de resumo (ex: runs por status e por wave).
3. Expandir os testes de integracao para tambem cobrir `run_mvp_all`.

### Prioridade media
1. Evoluir `dbt_build` para execucao dbt completa (profiles/materializations).
2. Criar visualizacao simples para `ops.pipeline_runs` e `ops.pipeline_checks`.
3. Expandir checks de qualidade por dominio com thresholds por dataset.

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

