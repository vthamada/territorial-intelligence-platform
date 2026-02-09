# Territorial Intelligence Platform

MVP bootstrap for the Diamantina/MG territorial intelligence platform, aligned with `SPEC.md` and `SPEC_v1.3.md`.

## Stack

- Python 3.11+
- PostgreSQL 16 + PostGIS
- Prefect (job orchestration)
- FastAPI (internal API)
- SQLAlchemy + psycopg

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

## API contract

- Versioned base path: `/v1`
- Health endpoint: `/v1/health`
- Standard error payload:
  - `{\"error\": {\"code\": \"...\", \"message\": \"...\", \"details\": {...}, \"request_id\": \"...\"}}`

## Current status

- Foundation and schema are implemented with English physical table names.
- Compatibility views exist for previous Portuguese table names.
- `ibge_admin_fetch` is implemented (municipality + district discovery and upsert).
- Remaining source connectors are scaffolded and return `not_implemented`.
- API endpoints from the minimum contract are available under `/v1`.
- `quality_suite` runs with configurable thresholds.
- Operational metadata is persisted in `ops.pipeline_runs` and `ops.pipeline_checks`.

## Paths

- Raw data: `data/bronze/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}/`
- Manifests: `data/manifests/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}.yml`
- SQL schema: `db/sql/`
- Wave definitions: `configs/waves.yml`
- Connector status registry seed: `configs/connectors.yml`
- Bronze operating policy: `docs/BRONZE_POLICY.md`

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
