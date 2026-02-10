# Territorial Intelligence Platform

MVP bootstrap for the Diamantina/MG territorial intelligence platform, aligned with `CONTRATO.md` and `PLANO.md`.

## Stack

- Python 3.11+
- PostgreSQL 16 + PostGIS
- Prefect (job orchestration)
- FastAPI (internal API)
- SQLAlchemy + psycopg
- Frontend oficial (planejado): React + Vite + TypeScript + React Router + TanStack Query

## Quick start

1. Copy environment variables:
   - `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`)
2. Start database:
   - `make up`
3. Install dependencies:
   - `make install`
4. Initialize DB schema:
   - `make db-init`
5. Run API:
   - `make run-api`
6. Validate MTE P0 acceptance (3 real runs):
   - `make validate-mte-p0`
7. Frontend F1 bootstrap:
   - `make frontend-install`
   - `make frontend-test`
   - `make frontend-build`

## API contract

- Versioned base path: `/v1`
- Health endpoint: `/v1/health`
- Ops endpoints:
  - `/v1/ops/pipeline-runs`
  - `/v1/ops/pipeline-checks`
  - `/v1/ops/connector-registry`
  - `/v1/ops/summary`
  - `/v1/ops/timeseries`
  - `/v1/ops/sla`
  - `pipeline-runs` supports `started_from` and `started_to` filters
  - `pipeline-checks` supports `created_from` and `created_to` filters
  - `connector-registry` supports `updated_from` and `updated_to` filters
  - `summary` returns aggregated totals and distributions for runs/checks/connectors
  - `sla` returns success rate and duration percentiles grouped by job/wave
  - `timeseries` returns bucketed trends (`day|hour`) for `runs` or `checks`
- Standard error payload:
  - `{\"error\": {\"code\": \"...\", \"message\": \"...\", \"details\": {...}, \"request_id\": \"...\"}}`

## Current status

- Foundation and schema are implemented with English physical table names.
- Compatibility views exist for previous Portuguese table names.
- MVP-1 connectors implemented:
  - `ibge_admin_fetch`
  - `ibge_geometries_fetch`
  - `ibge_indicators_fetch`
  - `dbt_build`
  - `quality_suite`
- MVP-2 connectors implemented:
  - `tse_catalog_discovery`
  - `tse_electorate_fetch`
  - `tse_results_fetch`
- MVP-3 connectors:
  - `education_inep_fetch`: implemented with real ingestion
  - `health_datasus_fetch`: implemented with real ingestion
  - `finance_siconfi_fetch`: implemented with real ingestion
  - `labor_mte_fetch`: partial, with FTP-first ingestion, Bronze cache fallback, and manual fallback for contingency
- API endpoints from the minimum contract are available under `/v1`.
- `quality_suite` runs with configurable thresholds.
- Operational metadata is persisted in `ops.pipeline_runs` and `ops.pipeline_checks`.
- Frontend is in official scope via `PLANO.md`, with F1 already implemented in `frontend/` and next phases planned (F2-F4).
- `dbt_build` now supports:
  - `DBT_BUILD_MODE=auto` (default): tries `dbt` CLI first and falls back to `sql_direct`
  - `DBT_BUILD_MODE=dbt`: requires `dbt` CLI in `PATH`
  - `DBT_BUILD_MODE=sql_direct`: keeps SQL view build mode

## Paths

- Raw data: `data/bronze/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}/`
- Manifests: `data/manifests/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}.yml`
- SQL schema: `db/sql/`
- Wave definitions: `configs/waves.yml`
- Connector status registry seed: `configs/connectors.yml`
- Bronze operating policy: `docs/BRONZE_POLICY.md`
- MTE operation runbook: `docs/MTE_RUNBOOK.md`
- Technical contract source of truth: `CONTRATO.md`
- Execution plan source of truth: `PLANO.md`

## Run a flow (example)

```bash
python -c "from orchestration.prefect_flows import ibge_admin_fetch; print(ibge_admin_fetch(reference_period='2026', dry_run=True))"
```

Note:
- `src/orchestration/prefect_flows.py` sets safe local defaults for Prefect runtime state in temporary storage (`PREFECT_HOME`, `PREFECT_API_DATABASE_CONNECTION_URL`, `PREFECT_MEMO_STORE_PATH`) when these env vars are not defined.

## Wave-oriented execution

- Wave 1 flow:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_1; print(run_mvp_wave_1(reference_period='2026', dry_run=True))"`
- Wave 2 flow:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_2; print(run_mvp_wave_2(reference_period='2024', dry_run=True))"`
- Wave 3 flow:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_3; print(run_mvp_wave_3(reference_period='2025', dry_run=True))"`

## MTE P0 validation

- Dedicated script for P0 acceptance:
  - `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`
- The script can bootstrap municipality context (`ibge_admin_fetch`) before MTE runs.

## Frontend (F1)

- Location: `frontend/`
- Stack: React + Vite + TypeScript + React Router + TanStack Query
- Environment:
  - copy `frontend/.env.example` to `frontend/.env` and adjust `VITE_API_BASE_URL` if needed
- Commands:
  - `cd frontend && npm run dev`
  - `cd frontend && npm test`
  - `cd frontend && npm run build`
