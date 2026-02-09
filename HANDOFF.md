# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-09

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
  - probe remoto + fallback manual por `data/manual/mte` (CSV/ZIP)
  - carga de indicadores quando dataset manual esta disponivel

### Registro de conectores
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` marcado como `partial`
  - nota operacional com fallback manual documentado

### Testes e ambiente
- `requirements.txt` adicionado para instalacao no ambiente local.
- Novos testes unitarios:
  - `tests/unit/test_datasus_health.py`
  - `tests/unit/test_inep_education.py`
  - `tests/unit/test_siconfi_finance.py`
  - `tests/unit/test_mte_labor.py`
  - `tests/unit/test_api_contract.py`
- Suite validada: `43 passed`.

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcional.
- Conectores MVP-1 e MVP-2: `implemented`.
- Conectores MVP-3:
  - INEP, DATASUS, SICONFI: `implemented` com ingestao real.
  - MTE: `partial` por restricao de autenticacao no portal web; operacao via fallback manual.
- `pip check`: sem dependencias quebradas.

## 3) Arquivos-chave alterados neste ciclo

- `src/app/api/error_handlers.py`
- `src/pipelines/datasus_health.py`
- `src/pipelines/inep_education.py`
- `src/pipelines/siconfi_finance.py`
- `src/pipelines/mte_labor.py`
- `configs/connectors.yml`
- `requirements.txt`
- `tests/unit/test_api_contract.py`
- `tests/unit/test_datasus_health.py`
- `tests/unit/test_inep_education.py`
- `tests/unit/test_siconfi_finance.py`
- `tests/unit/test_mte_labor.py`

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
1. Obter arquivo manual de Novo CAGED (CSV/ZIP) e salvar em `data/manual/mte`.
2. Executar `labor_mte_fetch`:
   - `dry_run=True` para validar
   - `dry_run=False` para gravar Silver/Bronze/ops

## 5) Proximos passos recomendados

### Prioridade alta
1. Implementar ingestao automatica do MTE via FTP `ftp://ftp.mtps.gov.br/pdet/microdados/` (sem depender de pagina restrita).
2. Adicionar parser padrao para microdados Novo CAGED bruto (TXT delimitado por `;`) com agregacao municipal.
3. Criar runbook operacional do MTE (manual + fallback) em `docs/`.

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

