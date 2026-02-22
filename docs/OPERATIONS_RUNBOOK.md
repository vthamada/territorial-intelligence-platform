# Runbook de Operacoes - Plataforma de Inteligencia Territorial

Data de referencia: 2026-02-13  
Versao: v1.0

## 1) Visao geral

Este documento consolida os procedimentos operacionais para ambiente de homologacao
e producao da plataforma. Complementa o `CONTRATO.md` (requisitos tecnicos) e o
`HANDOFF.md` (estado operacional corrente).

---

## 2) Ambiente de desenvolvimento local

### 2.1 Pre-requisitos

| Componente | Versao minima | Verificacao |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| PostgreSQL + PostGIS | 16 + 3.5 | `psql -c "SELECT PostGIS_Version();"` |
| Docker (opcional) | 24+ | `docker --version` |

### 2.2 Setup inicial

```powershell
# 1. Clonar repositorio e criar venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Instalar frontend
cd frontend && npm install && cd ..

# 3. Inicializar banco (requer PostgreSQL rodando)
python scripts/init_db.py

# 4. Registrar conectores
python scripts/sync_connector_registry.py

# 5. Sincronizar contratos de schema por fonte
python scripts/sync_schema_contracts.py

# 6. Verificar saude
python scripts/backend_readiness.py
```

### 2.3 Subida completa via script

```powershell
# Subir banco + API + frontend
.\scripts\dev_up.ps1

# Parar tudo
.\scripts\dev_down.ps1
```

### 2.4 Subida via Docker Compose

```powershell
docker-compose up -d
```

---

## 3) Execucao de pipelines

### 3.1 Estrutura de jobs

Cada pipeline segue o padrao:

```python
def run(*, reference_period: str, force: bool = False,
        dry_run: bool = False, max_retries: int = 3,
        timeout_seconds: int = 300) -> dict:
```

### 3.2 Execucao individual

```powershell
# Dry-run (nao escreve dados)
python -m pipelines.ibge_indicators --reference-period 2025 --dry-run

# Execucao real
python -m pipelines.ibge_indicators --reference-period 2025

# Com force (ignora cache Bronze)
python -m pipelines.ibge_indicators --reference-period 2025 --force
```

### 3.3 Ondas de conectores

| Onda | Conectores | Comando |
|---|---|---|
| MVP-1 | IBGE admin, geometries, indicators, dbt_build, quality_suite | `make mvp1` |
| MVP-2 | TSE catalog, electorate, results | `make mvp2` |
| MVP-3 | DATASUS, INEP, SICONFI, MTE | `make mvp3` |
| MVP-4 | SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS | `make mvp4` |
| MVP-5 | INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL | `make mvp5` |

### 3.4 Execucao completa

```powershell
# Executar todas as ondas em sequencia
make all-waves

# Quality suite (deve rodar apos carga)
python -m pipelines.quality_suite --reference-period 2025
```

---

## 4) Quality suite

### 4.1 Checks executados

| Check | Tabela | O que valida |
|---|---|---|
| `check_dim_territory` | `dim_territory` | Municipio existe, distritos minimos, geometria valida |
| `check_fact_electorate` | `fact_electorate` | Nao-negativo, referencia e territorio preenchidos |
| `check_fact_election_result` | `fact_election_result` | Nao-negativo, referencia e territorio preenchidos |
| `check_fact_indicator` | `fact_indicator` | Codigo/referencia/valor/territorio validos, probe rows |
| `check_fact_indicator_source_rows` | `fact_indicator` | Min rows por fonte (15 fontes configuradas) |
| `check_source_schema_contracts` | `ops.source_schema_contracts` | Cobertura ativa de contratos por conector implementado/partial |
| `check_source_schema_drift` | `ops.source_schema_contracts` + catalogo PG | Drift de schema (tabela, colunas obrigatorias e tipos por conector) |
| `check_ops_pipeline_runs` | `ops.pipeline_runs` | Presenca de runs para 14 jobs implementados |

### 4.2 Thresholds

Configurados em `configs/quality_thresholds.yml`. Fontes com min_rows:

- MVP-3: DATASUS, INEP, SICONFI, MTE, TSE (min_rows=1)
- MVP-4: SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS (min_rows=1)
- MVP-5: INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL (min_rows=1)
- Schema contracts:
  - `min_active_coverage_pct: 100.0`
  - `max_missing_connectors: 0`
- Schema drift:
  - `max_missing_required_columns: 0`
  - `max_type_mismatch_columns: 0`
  - `max_connectors_with_drift: 0`

### 4.3 Interpretacao

- `pass`: check dentro dos limites
- `warn`: check abaixo do threshold mas nao critico
- `fail`: requer acao corretiva â€” registrar em HANDOFF.md

---

## 5) Materialized views e indices

### 5.1 Views materializadas

| View | Arquivo SQL | Uso |
|---|---|---|
| `gold.mv_territory_ranking` | `006_materialized_views.sql` | Ranking territorial para prioridades |
| `gold.mv_map_choropleth` | `006_materialized_views.sql` | Dados pre-computados para mapa |
| `gold.mv_territory_map_summary` | `006_materialized_views.sql` | Geometria simplificada para mapa |

### 5.2 Refresh

```sql
-- Refresh concorrente (sem lock de leitura)
SELECT gold.refresh_materialized_views();

-- Refresh individual
REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_territory_ranking;
REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_map_choropleth;
REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_territory_map_summary;
```

**Quando atualizar:** apos carga de novos dados em tabelas Silver (`fact_indicator`, `dim_territory`).

### 5.3 Indices espaciais

Criados em `db/sql/007_spatial_indexes.sql`:
- GIST em `dim_territory.geometry`
- GIN trigram em `dim_territory.name`
- Covering index para joins de mapa

---

## 6) API â€” operacao

### 6.1 Iniciar servidor

```powershell
# Desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producao
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6.2 Health check

```powershell
curl http://localhost:8000/v1/health
# Esperar: {"api":"ok","db":"ok"}
```

### 6.3 Cache HTTP

O `CacheHeaderMiddleware` aplica headers automaticamente:
- `Cache-Control: public, max-age=300` nos endpoints cobertos
- `ETag` (weak) para revalidacao
- `304 Not Modified` quando cache valido

Endpoints com cache: `/map/layers`, `/map/style-metadata`, `/kpis/*`, `/priority/*`,
`/insights/*`, `/geo/choropleth`, `/electorate/*`, `/territory/*/profile`.

---

## 7) Frontend â€” build e deploy

### 7.1 Build

```powershell
cd frontend
npm run build       # tsc --noEmit && vite build
# Artefatos em frontend/dist/
```

### 7.2 Variaveis de ambiente

| Variavel | Default | Descricao |
|---|---|---|
| `VITE_API_BASE_URL` | `/v1` | Base URL da API |

### 7.3 Testes

```powershell
npm --prefix frontend run test   # 43 testes, 15 arquivos
```

---

## 8) Validacao de go-live

### 8.1 Homologacao consolidada

```powershell
python scripts/homologation_check.py
# Ou com output JSON:
python scripts/homologation_check.py --json
```

**5 dimensoes verificadas:**

1. Backend readiness (schema, SLO-1, ops tracking, PostGIS)
2. Quality suite (ultimo run com status success)
3. Frontend build (tsc + vite sem erros)
4. Test suites (backend 207+ + frontend 43+ todos passando)
5. API smoke (GET /v1/health responde ok)

**Verdict:** `READY FOR GO-LIVE` ou `NOT READY`

### 8.2 Benchmark de performance

```powershell
python scripts/benchmark_api.py
# Com mais rounds:
python scripts/benchmark_api.py --rounds 50 --json
# Suite operacional (/v1/ops/*):
python scripts/benchmark_api.py --suite ops --rounds 30 --json-output data/reports/benchmark_ops_api.json
```

**Alvos:**
1. suite `executive`: p95 <= 800ms.
2. suite `urban`: p95 <= 1000ms.
3. suite `ops`: p95 <= 1500ms.

### 8.3 Backend readiness individual

```powershell
python scripts/backend_readiness.py
# Strict mode (warnings = fail):
python scripts/backend_readiness.py --strict
```

---

## 9) Testes

### 9.1 Backend

```powershell
# Suite completa
python -m pytest -q -p no:cacheprovider

# Apenas contratos
python -m pytest tests/contracts/ -q

# Cobertura de contrato por conector (D6/BD-061)
python -m pytest tests/contracts/test_schema_contract_connector_coverage.py -q

# Apenas quality checks
python -m pytest tests/unit/test_quality_core_checks.py -q

# Edge cases
python -m pytest tests/unit/test_qg_edge_cases.py -q
```

### 9.2 Frontend

```powershell
npm --prefix frontend run test
```

### 9.3 Regressao completa

```powershell
# Backend + frontend + build
python -m pytest -q -p no:cacheprovider && ^
npm --prefix frontend run test && ^
npm --prefix frontend run build
```

---

## 10) Troubleshooting

### 10.1 API nao inicia

1. Verificar `DATABASE_URL` no `.env`
2. Testar conexao: `psql $DATABASE_URL -c "SELECT 1;"`
3. Verificar PostGIS: `psql $DATABASE_URL -c "SELECT PostGIS_Version();"`
4. Rodar init_db: `python scripts/init_db.py`

### 10.2 Pipeline falha com timeout

1. Verificar se a fonte externa esta acessivel
2. Aumentar `timeout_seconds` se necessario
3. Verificar cache Bronze: `ls data/bronze/{source}/`
4. Consultar run: `SELECT * FROM ops.pipeline_runs WHERE job_name='...' ORDER BY started_at_utc DESC LIMIT 5;`

### 10.3 Quality suite com fails

1. Verificar qual check falhou: `SELECT * FROM ops.pipeline_checks WHERE status='fail' ORDER BY created_at_utc DESC;`
2. Verificar thresholds: `cat configs/quality_thresholds.yml`
3. Recarregar dados da fonte problematica com `--force`
4. Registrar acao corretiva em HANDOFF.md

### 10.4 Frontend build falha

1. Verificar versao do Node: `node --version` (requer 20+)
2. Limpar cache: `rm -rf frontend/node_modules && npm --prefix frontend install`
3. Verificar erros TypeScript: `npx --prefix frontend tsc --noEmit`

### 10.5 SLO-1 abaixo do alvo

1. Identificar jobs com taxa de sucesso baixa:
   ```sql
   SELECT job_name, COUNT(*) FILTER (WHERE run_status='success') * 100.0 / COUNT(*) AS success_pct
   FROM ops.pipeline_runs
   WHERE started_at_utc > NOW() - INTERVAL '7 days'
   GROUP BY job_name
   ORDER BY success_pct ASC;
   ```
2. Investigar logs dos jobs mais falhantes
3. Verificar se fonte externa esta com instabilidade
4. Considerar `include_blocked_as_success=true` para fontes com indisponibilidade conhecida

---

## 11) Rotinas especiais consolidadas

### 11.1 Rotina semanal de robustez de dados

Pre-requisitos:
1. `.venv` ativo.
2. PostgreSQL/PostGIS acessivel no `.env`.
3. Schemas `silver` e `ops` inicializados.

Execucao padrao:

```powershell
# Passo A - baseline de cobertura robusta
.\.venv\Scripts\python.exe scripts/backfill_robust_database.py --tse-years 2024,2022,2020 --indicator-periods 2025 --output-json data/reports/robustness_backfill_report.json

# Passo B - scorecard oficial
.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json

# Passo C - readiness operacional
.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json
```

Passo opcional (onda social):

```powershell
.\.venv\Scripts\python.exe scripts/backfill_robust_database.py --include-wave6 --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --indicator-periods 2025 --output-json data/reports/robustness_backfill_report.json
```

Triagem:
1. Critico: `hard_failure` no readiness ou qualquer check `fail`.
2. Alto: `warn` recorrente por 2 semanas na mesma metrica.
3. Medio: oscilacao pontual sem regressao estrutural.

Evidencias obrigatorias:
1. `data/reports/robustness_backfill_report.json`
2. `data/reports/data_coverage_scorecard.json`
3. saida de `scripts/backend_readiness.py --output-json`
4. sintese em `docs/HANDOFF.md`
5. registro relevante em `docs/CHANGELOG.md`

### 11.2 MTE (Novo CAGED)

Fonte primaria:
1. FTP oficial `ftp://ftp.mtps.gov.br/pdet/microdados/`.
2. Roots tentados automaticamente:
   - `/pdet/microdados/NOVO CAGED`
   - `/pdet/microdados/NOVO_CAGED`

Parametros `.env`:
1. `MTE_FTP_HOST` (default `ftp.mtps.gov.br`)
2. `MTE_FTP_PORT` (default `21`)
3. `MTE_FTP_ROOT_CANDIDATES`
4. `MTE_FTP_MAX_DEPTH` (default `4`)
5. `MTE_FTP_MAX_DIRS` (default `300`)

Cascata de fallback:
1. Web probe -> FTP download -> Bronze cache -> manual (`data/manual/mte`) -> `blocked`.

Execucao:

```powershell
# Dry-run
python -c "import json; from pipelines.mte_labor import run; print(json.dumps(run(reference_period='2024', dry_run=True), ensure_ascii=False, indent=2, default=str))"

# Carga real
python -c "import json; from pipelines.mte_labor import run; print(json.dumps(run(reference_period='2024', dry_run=False), ensure_ascii=False, indent=2, default=str))"

# Validacao P0
python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json
```

Interpretacao rapida:
1. `status=success` + `source_type=ftp`: ingestao automatica.
2. `status=success` + `source_type=bronze_cache`: fonte indisponivel, cache reutilizado.
3. `status=success` + `source_type=manual`: fallback manual aplicado.
4. `status=blocked`: sem dado em nenhuma camada de fallback.

### 11.3 TSE e MVP-5

1. TSE: discovery automatico via CKAN; fallback por Bronze cache quando necessario.
2. Fontes MVP-5 (`INMET`, `INPE_QUEIMADAS`, `ANA`, `ANATEL`, `ANEEL`): monitorar `min_rows=1` e estabilidade dos runs apos deploy.

### 11.4 Execucao dedicada BD-050 (historico ambiental multi-ano)

Fluxo recomendado para D5:

```powershell
# Bootstrap + carga ambiental (INMET/INPE/ANA) para janela multi-ano
.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --periods 2021,2022,2023,2024,2025 --output-json data/reports/bd050_environment_history_report.json

# Scorecard atualizado com metricas ambientais por fonte
.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json
```

Leitura minima do relatorio `bd050_environment_history_report.json`:
1. `summary.execution_status.success` deve cobrir os 3 jobs para todos os periodos.
2. `coverage` deve mostrar `distinct_periods` crescente por `INMET`, `INPE_QUEIMADAS` e `ANA`.
3. Qualquer `manual_required` ou `blocked` deve abrir triagem imediata no runbook.

### 11.5 BD-051 - agregacao ambiental territorial

Objetivo operacional:
1. garantir disponibilidade da agregacao de risco ambiental por `district` e `census_sector`.

Validacao rapida:

```powershell
# Reaplicar SQL para garantir view atualizada
.\.venv\Scripts\python.exe scripts/init_db.py

# Smoke do endpoint ambiental
.\.venv\Scripts\python.exe -c "from fastapi.testclient import TestClient; from app.api.main import app; c=TestClient(app); r=c.get('/v1/map/environment/risk?level=district&limit=5'); print(r.status_code, r.json().get('period'), r.json().get('count'))"
```

Checks de qualidade esperados no ultimo `quality_suite`:
1. `environment_risk_rows_district` = `pass`.
2. `environment_risk_rows_census_sector` = `pass`.
3. `environment_risk_distinct_periods` = `pass`.
4. `environment_risk_null_score_rows`, `environment_risk_null_hazard_rows`, `environment_risk_null_exposure_rows` = `pass`.

### 11.6 BD-052 - mart Gold de risco ambiental territorial

Objetivo operacional:
1. garantir disponibilidade do mart Gold ambiental para consumo executivo em `/v1/environment/risk`.

Validacao rapida:

```powershell
# Reaplicar SQL para garantir mart atualizado
.\.venv\Scripts\python.exe scripts/init_db.py

# Smoke do endpoint executivo ambiental
.\.venv\Scripts\python.exe -c "from fastapi.testclient import TestClient; from app.api.main import app; c=TestClient(app); r=c.get('/v1/environment/risk?level=district&limit=5'); print(r.status_code, r.json().get('period'), len(r.json().get('items', [])))"
```

Checks de qualidade esperados no ultimo `quality_suite`:
1. `environment_risk_mart_rows_municipality` = `pass`.
2. `environment_risk_mart_rows_district` = `pass`.
3. `environment_risk_mart_rows_census_sector` = `pass`.
4. `environment_risk_mart_distinct_periods` = `pass`.
5. `environment_risk_mart_null_score_rows` = `pass`.

### 11.7 BD-080 - carga incremental + reprocessamento seletivo

Objetivo operacional:
1. evitar reprocessamento desnecessario por `job + reference_period` sem perder capacidade de atualizar periodos stale.
2. permitir reprocessamento pontual de conectores/periodos com controle explicito.

Execucao recomendada:

```powershell
# Incremental padrao (stale >= 168h), com dbt/quality pos-carga
.\.venv\Scripts\python.exe scripts/run_incremental_backfill.py --output-json data/reports/incremental_backfill_report.json

# Reprocessamento seletivo por job e periodo
.\.venv\Scripts\python.exe scripts/run_incremental_backfill.py --jobs sidra_indicators_fetch,senatran_fleet_fetch --reprocess-jobs sidra_indicators_fetch --reprocess-periods 2025 --output-json data/reports/incremental_backfill_report.json
```

Leitura minima do relatorio:
1. `plan[*].execute` define o que foi executado vs skip por sucesso fresco.
2. `summary.execution_status` deve ficar sem `failed` (ou sem status fora de `success`/`blocked` quando `--allow-blocked`).
3. `summary.post_load_runs` confirma disparo de `dbt_build`/`quality_suite` por periodo com sucesso incremental.

### 11.8 BD-082 - playbook de incidentes e operacao assistida

Objetivo operacional:
1. consolidar triagem unica de incidente com severidade e acoes recomendadas.
2. reduzir tempo de resposta em falhas de pipeline/qualidade/readiness.

Execucao recomendada:

```powershell
# Snapshot unico para triagem operacional
.\.venv\Scripts\python.exe scripts/generate_incident_snapshot.py --output-json data/reports/incident_snapshot.json
```

Leitura minima do relatorio `incident_snapshot.json`:
1. `severity` deve orientar o modo de resposta (`critical`, `high`, `normal`).
2. `summary` concentra volume de `hard_failures`, `warnings`, `failed_runs`, `failed_checks`.
3. `recommended_actions` define o plano minimo de mitigacao antes do proximo ciclo de carga.
## 12) Procedimento de deploy

### 12.1 Pre-deploy checklist

- [ ] Rodar `homologation_check.py` com verdict READY
- [ ] Rodar `benchmark_api.py` com p95 <= 800ms
- [ ] Todos os testes passando (backend + frontend)
- [ ] Build frontend sem erros
- [ ] CHANGELOG atualizado
- [ ] HANDOFF atualizado

### 12.2 Sequencia de deploy

1. Parar API
2. Executar migrations SQL pendentes (`db/sql/`)
3. Atualizar dependencias Python (`pip install -r requirements.txt`)
4. Atualizar dependencias frontend (`npm --prefix frontend install`)
5. Build frontend (`npm --prefix frontend run build`)
6. Iniciar API
7. Verificar health: `curl /v1/health`
8. Executar pipelines pendentes
9. Refresh materialized views: `SELECT gold.refresh_materialized_views();`
10. Rodar quality suite
11. Verificar readiness: `python scripts/backend_readiness.py`

### 12.3 Rollback

1. Reverter codigo para commit anterior
2. Restaurar backup do banco se migrations foram aplicadas
3. Rebuild frontend
4. Reiniciar API
5. Verificar health

