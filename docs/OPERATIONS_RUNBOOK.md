# Runbook de Operacoes — Plataforma de Inteligencia Territorial

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

# 5. Verificar saude
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
| `check_ops_pipeline_runs` | `ops.pipeline_runs` | Presenca de runs para 14 jobs implementados |

### 4.2 Thresholds

Configurados em `configs/quality_thresholds.yml`. Fontes com min_rows:

- MVP-3: DATASUS, INEP, SICONFI, MTE, TSE (min_rows=1)
- MVP-4: SIDRA, SENATRAN, SEJUSP_MG, SIOPS, SNIS (min_rows=1)
- MVP-5: INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL (min_rows=1)

### 4.3 Interpretacao

- `pass`: check dentro dos limites
- `warn`: check abaixo do threshold mas nao critico
- `fail`: requer acao corretiva — registrar em HANDOFF.md

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

## 6) API — operacao

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

## 7) Frontend — build e deploy

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
```

**Alvo:** p95 <= 800ms nos 12 endpoints executivos.

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

## 11) Conectores com procedimento especial

### 11.1 MTE (Novo CAGED)

Procedimento detalhado em `docs/MTE_RUNBOOK.md`. Cascata de fallback:
1. Web probe → FTP download → Bronze cache → Manual fallback → `blocked`

### 11.2 TSE

Discovery automatico via CKAN. Se CKAN indisponivel, usar Bronze cache.

### 11.3 Fontes MVP-5

INMET, INPE, ANA, ANATEL, ANEEL — fontes mais novas, min_rows=1.
Monitorar runs iniciais apos deploy para garantir estabilidade.

---

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
