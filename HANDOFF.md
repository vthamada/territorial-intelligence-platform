# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-08

## 1) O que foi implementado ate agora

### Arquitetura e base do projeto
- Estrutura MVP por ondas consolidada (MVP-1, MVP-2, MVP-3).
- Camadas Bronze/Silver/Gold operacionais com manifests em `data/manifests/...`.
- Persistencia operacional em:
  - `ops.pipeline_runs`
  - `ops.pipeline_checks`

### Conectores IBGE (MVP-1)
- `ibge_admin_fetch`
  - Resolve municipio alvo e distritos.
  - Upsert em `silver.dim_territory`.
- `ibge_geometries_fetch`
  - Download de malhas IBGE (municipio, distrito, setor censitario).
  - Validacao/reparo de geometria e upsert em `silver.dim_territory.geometry`.
- `ibge_indicators_fetch`
  - Leitura de `configs/indicators_catalog.yml`.
  - Busca via API IBGE com fallback de periodo.
  - Upsert em `silver.fact_indicator`.

### Conectores TSE (MVP-2)
- `tse_catalog_discovery`
  - Descoberta CKAN com bronze + observabilidade.
- `tse_electorate_fetch`
  - Download e parse do eleitorado (ZIP/CSV).
  - Agregacao por municipio alvo e upsert em `silver.fact_electorate`.
- `tse_results_fetch`
  - Download e parse do detalhe de votacao por municipio/zona.
  - Agregacao de metricas e upsert em `silver.fact_election_result`.

### MVP-3 (baseline funcional)
- `education_inep_fetch`
- `health_datasus_fetch`
- `finance_siconfi_fetch`
- `labor_mte_fetch`
- Implementados no padrao `source_probe` (baseline de coleta + indicador minimo em `silver.fact_indicator`).

### Gold e qualidade
- `dbt_build` funcional (modo SQL direto) para views `gold`.
- `quality_suite` com thresholds e checks em `ops.pipeline_checks`.
- Testes automatizados passando (`20 passed`).

### Observabilidade consolidada
- Todos os conectores implementados agora gravam checks em `ops.pipeline_checks` usando:
  - `replace_pipeline_checks_from_dicts(...)`
- Utilitario adicionado em:
  - `src/pipelines/common/observability.py`

### Prefect (estabilidade local)
- Ajuste em `src/orchestration/prefect_flows.py` para defaults locais quando env vars nao existem:
  - `PREFECT_HOME`
  - `PREFECT_API_DATABASE_CONNECTION_URL`
  - `PREFECT_MEMO_STORE_PATH`
- Fluxos Prefect validados com sucesso em `dry_run`.

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcionando.
- Pipelines executam com sucesso em modo direto (`run(...)`).
- Fluxo completo em modo direto validado (todos jobs `success`).
- Fluxo Prefect `run_mvp_all(..., dry_run=True)` validado com `12` jobs `success`.

## 3) Arquivos-chave modificados recentemente

- `src/pipelines/common/observability.py`
- `src/pipelines/ibge_admin.py`
- `src/pipelines/ibge_geometries.py`
- `src/pipelines/ibge_indicators.py`
- `src/pipelines/tse_catalog.py`
- `src/pipelines/tse_electorate.py`
- `src/pipelines/tse_results.py`
- `src/pipelines/common/source_probe.py`
- `src/pipelines/dbt_build.py`
- `src/orchestration/prefect_flows.py`
- `README.md`

## 4) Como retomar rapidamente em outro computador

### 4.1 Pre requisitos
- Python 3.11+
- PostgreSQL 16 + PostGIS
- Dependencias do projeto instaladas

### 4.2 Setup basico
1. Clonar repositorio.
2. Criar `.env` com credenciais locais.
3. Subir banco.
4. Inicializar schema:
   - `python scripts/init_db.py`

### 4.3 Smoke check recomendado
1. Testes:
   - `pytest -q -p no:cacheprovider`
2. Fluxo MVP em dry-run:
   - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2024', dry_run=True))"`

### 4.4 Execucao real (sem Prefect, direta)
- Rodar os `run(...)` dos pipelines conforme necessidade operacional.
- Ao final, validar:
  - `ops.pipeline_runs`
  - `ops.pipeline_checks`

## 5) Proximos passos recomendados

### Prioridade alta
1. Migrar conectores MVP-3 de `source_probe` para ingestao real de datasets finais.
2. Adicionar testes de contrato para cada conector MVP-3 (entrada/saida + idempotencia).
3. Consolidar metadados de qualidade por dominio (educacao, saude, financas, trabalho).

### Prioridade media
1. Evoluir `dbt_build` de SQL direto para execucao dbt completa (com profiles e materializations).
2. Criar dashboard simples para `ops.pipeline_runs` e `ops.pipeline_checks`.
3. Expandir validacoes geoespaciais (topologia, cobertura e consistencia de hierarquia territorial).

### Prioridade baixa
1. Hardening de observabilidade (SLA por job, alertas, retries por tipo de erro).
2. Melhorar documentacao de operacao (runbooks por conector).

## 6) Comandos uteis

- Rodar um fluxo simples:
  - `python -c "from orchestration.prefect_flows import ibge_admin_fetch; print(ibge_admin_fetch(reference_period='2024', dry_run=True))"`
- Rodar fluxo completo (dry run):
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2024', dry_run=True))"`
- Sincronizar registry:
  - `python scripts/sync_connector_registry.py`
- Rodar qualidade:
  - `python -c "from pipelines.quality_suite import run; print(run(reference_period='2024', dry_run=False))"`

