# Backlog Tecnico Executavel - Nivel Maximo de Dados

Data de referencia: 2026-02-19  
Status: ativo  
Escopo: plano tecnico para levar a base de dados ao nivel maximo de robustez para inteligencia territorial de Diamantina/MG.

## 1) Objetivo

Sair de um estado "robusto para o MVP" para um estado "robusto maximo", com:
1. cobertura ampliada de fontes e historico.
2. granularidade territorial multi-nivel real.
3. qualidade mensuravel por dominio.
4. automacao operacional sem dependencia manual recorrente.
5. base geoespacial de alto detalhe para mapa estrategico.

## 2) Definition of Done (DoD) - Nivel Maximo

O nivel maximo sera considerado atingido quando TODOS os itens abaixo forem verdadeiros:
1. `ops.connector_registry`: 100% dos conectores priorizados como `implemented`.
2. Historico: minimo de 5 anos por dominio (quando a fonte disponibilizar).
3. Cobertura territorial:
   - `municipality`: 100% dos fatos principais.
   - `district`: minimo 80% dos indicadores elegiveis.
   - `census_sector`: minimo 60% dos indicadores elegiveis.
   - `electoral_zone`: 100% para eleitorado e resultado eleitoral.
4. Qualidade:
   - `quality_suite`: 0 `fail` por 30 dias corridos.
   - checks criticos em `pass` para tabelas fato e dimensao.
5. Frescor:
   - 100% das fontes com SLA definido e medido (`ops`).
6. Operacao:
   - zero carga manual recorrente para execucao diaria/semanal/mensal.
7. Geoespacial:
   - camadas base territoriais + camadas urbanas essenciais (vias, POIs, uso do solo, zonas de risco quando disponiveis).

## 3) Sprint plan (8 sprints de 2 semanas)

### Sprint D0 - Governanca e baseline
Objetivo:
1. congelar contrato de robustez maxima e metricas.
2. criar dashboard de cobertura de dados e qualidade.
Status:
- concluido em 2026-02-18.
Evidencias:
- `docs/CONTRATO.md` (secao 14 atualizada).
- `db/sql/007_data_coverage_scorecard.sql`.
- `scripts/export_data_coverage_scorecard.py`.
- `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`.
- `data/reports/data_coverage_scorecard.json`.

Issues:
1. `BD-001`: publicar DoD no contrato tecnico.
2. `BD-002`: criar scorecard SQL de cobertura historica e territorial.
3. `BD-003`: registrar runbook de monitoramento semanal.

Aceite:
1. query unica de cobertura publicada e versionada.
2. metricas visiveis em endpoint ops ou relatorio versionado.

### Sprint D1 - Historico eleitoral e padronizacao temporal
Objetivo:
1. consolidar historico TSE e padrao de series temporais.
Status:
- concluido em 2026-02-19.
Progresso atual:
- `BD-010` executado com backfill TSE `2024,2022,2020,2018,2016`.
- `BD-011` concluido com checks de integridade de `electoral_zone` no `quality_suite`.
- `BD-012` concluido com checks de continuidade temporal para eleitorado, resultado eleitoral e `fact_indicator` por fonte.
Evidencias:
- `data/reports/robustness_backfill_report.json`:
  - `fact_electorate`: `5` anos distintos (`2016`-`2024`), `3562` linhas.
  - `fact_election_result`: `5` anos distintos (`2016`-`2024`), `180` linhas, `90` linhas por `electoral_zone`.
- `data/reports/data_coverage_scorecard.json`:
  - `electorate_distinct_years`: `pass`.
  - `election_result_distinct_years`: `pass`.
  - `electorate_zone_coverage_pct`: `100.00` (`pass`).
  - `election_result_zone_coverage_pct`: `100.00` (`pass`).
- `scripts/export_data_coverage_scorecard.py`: `pass=11`, `warn=0`.
- `scripts/backend_readiness.py --output-json`: `READY`, `hard_failures=0`, `warnings=0`.

Issues:
1. `BD-010`: backfill TSE 2016-2024 (anos disponiveis no CKAN).
2. `BD-011`: validar integridade de zonas eleitorais na `dim_territory`.
3. `BD-012`: adicionar checks de continuidade temporal por fonte.

Aceite:
1. `fact_electorate` com >= 5 anos distintos (se disponivel).
2. `fact_election_result` com >= 5 anos distintos (se disponivel).
3. cobertura de `electoral_zone` em `pass` sem excecao.

### Sprint D2 - Dominio social (CadUnico/CECAD e SUAS)
Objetivo:
1. incluir fontes sociais de alto impacto analitico.
Status:
- concluido tecnicamente com ressalva de governanca externa (2026-02-19).
Progresso atual:
- `BD-020`: conector `cecad_social_protection_fetch` implementado em codigo.
- `BD-021`: conector `censo_suas_fetch` implementado em codigo.
- `BD-022`: tabelas Silver dedicadas criadas:
  - `silver.fact_social_protection`
  - `silver.fact_social_assistance_network`
- endpoints sociais publicados:
  - `GET /v1/social/protection`
  - `GET /v1/social/assistance-network`
- checks sociais adicionados ao `quality_suite`:
  - `social_protection_rows_after_filter`
  - `social_protection_negative_rows`
  - `social_assistance_network_rows_after_filter`
  - `social_assistance_network_negative_rows`
Evidencias:
- migration: `db/sql/008_social_domain.sql`.
- conectores: `src/pipelines/cecad_social_protection.py`, `src/pipelines/censo_suas.py`.
- helper comum: `src/pipelines/common/social_tabular_connector.py`.
- api: `src/app/api/routes_social.py`.
- validacao:
  - `tests/contracts/test_sql_contracts.py` e suites unitarias sociais (`31 passed`).
  - `scripts/init_db.py` com `Applied 8 SQL scripts`.
  - `quality_suite(2025)` com `73 checks`, `0 fail`, `0 warn`.
  - `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --include-wave6 --indicator-periods 2014,2015,2016,2017`:
    - `censo_suas_fetch`: `success` em `2014..2017`.
    - `cecad_social_protection_fetch`: `blocked` em `2014..2017` (esperado sem acesso governado).
  - cobertura social consolidada:
    - `silver.fact_social_assistance_network`: `rows=4`, `distinct_periods=4`.
    - `silver.fact_social_protection`: `rows=0`, `distinct_periods=0`.
Pendencia residual:
- promover conectores sociais de `partial` para `implemented` apos liberacao de acesso governado para CECAD.

Issues:
1. `BD-020`: conector `cecad_social_protection_fetch`.
2. `BD-021`: conector `censo_suas_fetch`.
3. `BD-022`: novas tabelas Silver:
   - `silver.fact_social_protection`
   - `silver.fact_social_assistance_network`

Aceite:
1. conectores sociais em `implemented`.
2. checks de qualidade sociais ativos em `quality_suite`.
3. endpoints de leitura social disponiveis em `/v1`.

### Sprint D3 - Dominio urbano (mapa base avancado)
Objetivo:
1. elevar mapa para nivel "Google Maps-like" orientado a decisao.
Status:
- em andamento (kickoff em 2026-02-19).
Progresso atual:
- trilha definida como foco prioritario apos consolidacao D2.
- escopo inicial do ciclo:
  - DDL e contrato iniciais publicados em `db/sql/009_urban_domain.sql`:
    - `map.urban_road_segment`
    - `map.urban_poi`
    - `map.v_urban_data_coverage`
  - endpoints iniciais publicados em `src/app/api/routes_map.py`:
    - `GET /v1/map/urban/roads` (`bbox`, `road_class`, `limit`)
    - `GET /v1/map/urban/pois` (`bbox`, `category`, `limit`)
    - `GET /v1/map/urban/nearby-pois` (`lon`, `lat`, `radius_m`, `category`, `limit`)
  - validacao inicial:
    - `scripts/init_db.py`: `Applied 9 SQL scripts`.
    - `pytest` (`tests/contracts/test_sql_contracts.py` + `tests/unit/test_api_contract.py`): `18 passed`.
- incremento D3-2 concluido (2026-02-19):
  - conectores urbanos implementados:
    - `urban_roads_fetch` (`src/pipelines/urban_roads.py`)
    - `urban_pois_fetch` (`src/pipelines/urban_pois.py`)
  - catalogos de extração por bbox publicados:
    - `configs/urban_roads_catalog.yml`
    - `configs/urban_pois_catalog.yml`
  - orquestracao atualizada:
    - `run_mvp_all` inclui jobs urbanos.
    - fluxo dedicado `run_mvp_wave_7`.
    - `scripts/backfill_robust_database.py` com `--include-wave7`.
  - geocodificacao local inicial publicada:
    - `GET /v1/map/urban/geocode`.
  - catalogo e cobertura de camadas com dominio urbano no backend de mapa:
    - `GET /v1/map/layers?include_urban=true`
    - `GET /v1/map/layers/coverage?include_urban=true`
    - `GET /v1/map/layers/readiness?include_urban=true`
  - observabilidade tecnica no frontend Ops:
    - `OpsLayersPage` com filtro de escopo para readiness de camadas (`territorial`, `all`, `urban`).
  - tiles vetoriais urbanos multi-zoom habilitados:
    - `GET /v1/map/tiles/urban_roads/{z}/{x}/{y}.mvt`
    - `GET /v1/map/tiles/urban_pois/{z}/{x}/{y}.mvt`
  - governanca de qualidade/cobertura urbana ativa:
    - `check_urban_domain` no `quality_suite`.
    - metricas `urban_road_rows` e `urban_poi_rows` no scorecard.
  - validacao tecnica do incremento:
    - `pytest` focado (`urban_connectors`, `api_contract`, `prefect_wave3_flow`, `quality_*`, `sql_contracts`): `40 passed`.

Issues:
1. `BD-030`: ingestao OSM/IBGE para vias e logradouros.
2. `BD-031`: ingestao de POIs essenciais (saude, educacao, seguranca, assistencia).
3. `BD-032`: camada de geocodificacao local e indexacao espacial.
4. `BD-033`: mapa base estilo navegacao (ruas/claro/sem base) com comutacao no frontend.
5. `BD-033` (parcial entregue em 2026-02-19):
   - seletor de escopo (`Territorial`/`Urbana`) no `QgMapPage`.
   - seletor de camada urbana (`urban_roads`/`urban_pois`) no `QgMapPage`.
   - `VectorMap` renderizando `layer_kind=line` para viario urbano.

Aceite:
1. tiles vetoriais multi-zoom para camadas urbanas.
2. endpoint de consulta espacial por raio/bbox.
3. tempo de resposta p95 < 1.0s para consultas de mapa operacional.
4. mapa executivo com basemap comutavel e camadas vetoriais operacionais sobrepostas.

### Sprint D4 - Dominio de mobilidade e infraestrutura
Objetivo:
1. enriquecer leitura de infraestrutura urbana e acesso.

Issues:
1. `BD-040`: aprofundar SENATRAN (serie historica e categorias de frota).
2. `BD-041`: integrar dados de transporte/viario municipal (quando disponivel).
3. `BD-042`: criar `gold.mart_mobility_access`.

Aceite:
1. serie historica minima de 5 anos para mobilidade (quando disponivel).
2. mart pronto para consumo da camada de prioridades.

### Sprint D5 - Dominio ambiental e risco territorial
Objetivo:
1. consolidar leitura de risco ambiental e hidrologico por territorio.

Issues:
1. `BD-050`: expandir INMET/INPE/ANA para series historicas multi-ano.
2. `BD-051`: criar agregacoes por distrito/setor para risco.
3. `BD-052`: criar `gold.mart_environment_risk`.

Aceite:
1. indicadores de risco ambiental com cobertura multi-nivel.
2. checks de anomalia temporal habilitados para clima/ambiente.

### Sprint D6 - Qualidade avancada e confiabilidade
Objetivo:
1. reduzir risco de regressao e inconsistencias de fonte.

Issues:
1. `BD-060`: contratos de schema por fonte (versionados).
2. `BD-061`: testes de contrato automatizados por conector.
3. `BD-062`: detecao automatica de drift de schema e alerta.

Aceite:
1. toda quebra de schema gera `fail` explicito em `ops.pipeline_checks`.
2. cobertura de testes de contrato >= 90% dos conectores implementados.

### Sprint D7 - Marts de decisao e explicabilidade
Objetivo:
1. transformar base robusta em decisao robusta.

Issues:
1. `BD-070`: `gold.mart_priority_drivers` por dominio.
2. `BD-071`: versionamento de score territorial e pesos.
3. `BD-072`: trilha de explicabilidade por insight/prioridade.

Aceite:
1. cada prioridade no frontend aponta para evidencias auditaveis no backend.
2. reproducao deterministica de score por referencia_period.

### Sprint D8 - Hardening final e operacao assistida
Objetivo:
1. fechar estabilidade de producao para nivel maximo.

Issues:
1. `BD-080`: carga incremental confiavel + reprocessamento seletivo.
2. `BD-081`: custo/performance tuning (indices, particoes, materialized views).
3. `BD-082`: playbook de incidentes e continuidade operacional.

Aceite:
1. SLOs tecnicos cumpridos por 30 dias corridos.
2. readiness `READY` sem hard failures na janela alvo.
3. release de base robusta documentado em `CHANGELOG.md` e `HANDOFF.md`.

## 4) Ordem de execucao (caminho critico)

1. D0 -> D1 (temporal + governanca).
2. D2 e D3 em paralelo parcial (social e mapa urbano).
3. D4 e D5 em paralelo parcial (infraestrutura e ambiente).
4. D6 obrigatorio antes de D7.
5. D8 fecha operacao.

Dependencias criticas:
1. acesso e governanca para fontes sociais (CECAD/Censo SUAS).
2. definicao de politica de dados para camadas urbanas externas.
3. capacidade de processamento para tiles vetoriais multi-camada.

## 5) Backlog de issues (modelo pronto para tracker)

Padrao de issue:
1. `ID`: BD-XXX
2. `Titulo`: objetivo tecnico claro
3. `Descricao`: problema, abordagem, escopo
4. `Dependencias`: IDs bloqueantes
5. `Entregaveis`: codigo + teste + doc + evidencias
6. `Aceite`: criterio mensuravel
7. `Estimativa`: S/M/L

## 6) Metricas obrigatorias de acompanhamento (semanal)

1. cobertura historica por fonte (% anos disponiveis carregados).
2. cobertura territorial por nivel (% indicadores elegiveis por nivel).
3. taxa de sucesso por conector (`SLO-1`).
4. checks criticos `pass/fail` por dominio.
5. lag de atualizacao por fonte (horas/dias).

## 7) Proximo passo imediato

Executar Sprint D3 nesta ordem:
1. executar primeira carga urbana real:
   - `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --include-wave7 --indicator-periods 2026 --output-json data/reports/robustness_backfill_report.json`
2. validar qualidade e readiness apos carga urbana:
   - `scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json`
   - `scripts/backend_readiness.py --output-json`
3. executar `BD-032` de performance:
   - medir p95 dos endpoints `roads`, `pois`, `nearby-pois`, `geocode`.
   - aplicar tuning de indices/consulta se p95 > 1.0s.
4. preparar camada de tiles urbanos multi-zoom (aceite final D3).
5. iniciar `BD-033` para aproximar UX de navegacao (basemap comutavel no mapa executivo).



