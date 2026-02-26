# Plataforma de Inteligência Territorial

Plataforma de inteligência territorial para Diamantina/MG, alinhada ao contrato tecnico em `docs/CONTRATO.md`, ao plano de execucao em `docs/PLANO_IMPLEMENTACAO_QG.md` e ao north star de produto em `docs/VISION.md`.

## Estado atual (20/02/2026)

- Backend e frontend estaveis em desenvolvimento local.
- API versionada em `/v1` com saude operacional, QG executivo, geografia e observabilidade.
- Plataforma de mapa com manifesto de camadas (`GET /v1/map/layers`), metadata de estilo (`GET /v1/map/style-metadata`) e tiles vetoriais MVT com fallback SVG no frontend (`/mapa`).
- Metadados de estilo do mapa ativos em `GET /v1/map/style-metadata` (modo padrao, paleta e ranges de legenda).
- Conectores implementados ate `MVP-5` (ondas A e B/C) com persistencia em Bronze/Silver e metadados operacionais em `ops`.
- Frontend executivo ativo com paginas de:
  - Visao geral (QG)
  - Prioridades
  - Mapa
  - Insights
  - Cenarios
  - Briefs
  - Territorio 360
  - Eleitorado
  - Hub tecnico/Admin (ops)
- Readiness local: `READY` (com warning historico de SLO-1 na janela de 7 dias).
- Validacoes recentes:
  - `pytest -q -p no:cacheprovider`: `55 passed` (suite alvo de rotas qg/tse + mvt/cache)
  - `npm --prefix frontend run test`: `72 passed`
  - `npm --prefix frontend run build`: `OK`

## Stack

- Python 3.11+
- PostgreSQL 16 + PostGIS
- FastAPI + SQLAlchemy + psycopg
- Prefect (orquestracao)
- React + Vite + TypeScript + React Router + TanStack Query

## Conectores por onda

- `MVP-1`
  - `ibge_admin_fetch`
  - `ibge_geometries_fetch`
  - `ibge_indicators_fetch`
  - `dbt_build`
  - `quality_suite`
- `MVP-2`
  - `tse_catalog_discovery`
  - `tse_electorate_fetch`
  - `tse_results_fetch`
- `MVP-3`
  - `education_inep_fetch`
  - `health_datasus_fetch`
  - `finance_siconfi_fetch`
  - `labor_mte_fetch`
- `MVP-4` (Onda A)
  - `sidra_indicators_fetch`
  - `senatran_fleet_fetch`
  - `sejusp_public_safety_fetch`
  - `siops_health_finance_fetch`
  - `snis_sanitation_fetch`
- `MVP-5` (Onda B/C)
  - `inmet_climate_fetch`
  - `inpe_queimadas_fetch`
  - `ana_hydrology_fetch`
  - `anatel_connectivity_fetch`
  - `aneel_energy_fetch`

## Setup rapido (Windows)

1. Copiar ambiente:
   - `Copy-Item .env.example .env`
2. Criar e ativar venv (se necessario):
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
3. Instalar dependencias:
   - `python -m pip install -e .[dev]`
4. Subir banco:
   - `docker compose up -d postgres`
5. Inicializar schema:
   - `python scripts/init_db.py`
6. Sincronizar registry de conectores:
   - `python scripts/sync_connector_registry.py`
7. Subir API:
   - `python -m uvicorn app.api.main:app --app-dir src --reload --host 0.0.0.0 --port 8000`
8. Subir frontend (novo terminal):
   - `npm --prefix frontend install`
   - `npm --prefix frontend run dev`

## Setup rapido (Linux/macOS com make)

- `make up`
- `make install`
- `make db-init`
- `make sync-connectors`
- `make run-api`
- `make frontend-install`
- `make frontend-test`
- `make frontend-build`

## Endpoints principais

- Saude:
  - `GET /v1/health`
- Territorio e indicadores:
  - `GET /v1/territories`
  - `GET /v1/territories/{territory_id}`
  - `GET /v1/indicators`
  - `GET /v1/geo/choropleth`
  - `GET /v1/map/layers`
  - `GET /v1/map/style-metadata`
- QG executivo:
  - `GET /v1/kpis/overview`
  - `GET /v1/priority/list`
  - `GET /v1/priority/summary`
  - `GET /v1/insights/highlights`
  - `POST /v1/scenarios/simulate`
  - `POST /v1/briefs`
  - `GET /v1/territory/{territory_id}/profile`
  - `GET /v1/territory/{territory_id}/compare`
  - `GET /v1/territory/{territory_id}/peers`
  - `GET /v1/electorate/summary`
  - `GET /v1/electorate/map`
- Operacao/observabilidade:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary`
  - `GET /v1/ops/source-coverage`
  - `GET /v1/ops/sla`
  - `GET /v1/ops/timeseries`
  - `POST /v1/ops/frontend-events`
  - `GET /v1/ops/frontend-events`

## Qualidade e validacao

- Suite backend:
  - `python -m pytest -q -p no:cacheprovider`
- Suite frontend:
  - `npm --prefix frontend run test`
- Build frontend:
  - `npm --prefix frontend run build`
- Readiness backend:
  - `python scripts/backend_readiness.py --output-json`

## Execucao de fluxos (exemplos)

- Onda 4:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_4; print(run_mvp_wave_4(reference_period='2025', dry_run=False))"`
- Onda 5:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_5; print(run_mvp_wave_5(reference_period='2025', dry_run=False))"`
- Fluxo completo:
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2025', dry_run=False))"`

## Estrutura importante

- SQL incremental e schema: `db/sql/`
- Configuracoes de ondas/jobs/conectores: `configs/`
- Pipelines: `src/pipelines/`
- API: `src/app/api/`
- Frontend: `frontend/`
- Dados Bronze: `data/bronze/`
- Manifestos Bronze: `data/manifests/`
- Fallback/manual de fontes: `data/manual/`
- Handoff tecnico: `docs/HANDOFF.md`
- Historico de mudancas: `docs/CHANGELOG.md`
