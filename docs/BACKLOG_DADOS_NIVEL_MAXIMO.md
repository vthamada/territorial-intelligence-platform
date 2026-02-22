# Backlog Tecnico Executavel - Nivel Maximo de Dados

Data de referencia: 2026-02-19  
Status: ativo  
Escopo: plano tecnico para levar a base de dados ao nivel maximo de robustez para inteligencia territorial de Diamantina/MG.

Fonte oficial de catalogo/priorizacao de fontes:
1. este proprio documento (substitui `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` para decisao).

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
- `docs/OPERATIONS_RUNBOOK.md` (secao de rotina semanal consolidada).
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
   - deep-link completo no `QgMapPage` para recorte + visualizacao:
     - `metric`, `period`, `level`, `scope`, `layer_id`, `territory_id`, `basemap`, `viz`, `renderer`, `zoom`.
   - code-splitting aplicado no mapa executivo (`React.lazy` para `VectorMap`) para reduzir custo de carregamento inicial.
   - toolbar de controles do mapa ajustada para responsividade (sem overflow horizontal em mobile).
   - build frontend com `manualChunks` para separar vendors e reduzir payload inicial do app.
   - navegacao territorial reforcada no `QgMapPage`:
     - busca rapida (`Buscar territorio`) com foco por nome.
     - controles explicitos (`Focar territorio`, `Focar selecionado`, `Recentrar mapa`).
     - sincronizacao de `territory_id` na URL apos foco por busca.
   - `VectorMap` com controle de viewport por sinais:
     - `focusTerritorySignal` para enquadrar territorio selecionado.
     - `resetViewSignal` para retorno rapido ao centro/zoom base.
     - fallback seguro para ambientes de teste sem `easeTo`/`fitBounds`.
   - Home executiva com `Layout B` ativado:
     - `QgOverviewPage` com mapa dominante e painel lateral colapsavel.
     - filtros/atalhos executivos migrados para o painel lateral do mapa.
     - leitura de territorio selecionado no mesmo painel para reduzir troca de contexto.
   - Home executiva com navegacao vetorial no proprio mapa dominante:
     - `QgOverviewPage` renderizando `VectorMap` com fallback SVG.
     - basemap comutavel (`Ruas`, `Claro`, `Sem base`) e controle de zoom no painel lateral.
     - controles de navegacao rapida (`Focar selecionado`, `Recentrar mapa`) diretamente na Home.
   - hardening de testes de navegacao para nova UI do mapa:
     - `router.smoke.test.tsx` e `e2e-flow.test.tsx` ajustados para duplicidade intencional de links contextuais.
   - contexto urbano com acao operacional no `QgMapPage`:
     - card contextual urbano com links para filtros por classe/categoria:
       - `/v1/map/urban/roads`
       - `/v1/map/urban/pois`
     - link de geocodificacao contextual (`/v1/map/urban/geocode`).
     - link de proximidade por clique (`/v1/map/urban/nearby-pois` com `lon`/`lat`).
   - contrato MVT urbano enriquecido para leitura contextual:
     - `urban_roads`: `road_class`, `is_oneway`, `source`.
     - `urban_pois`: `category`, `subcategory`, `source`.
   - sincronizacao de URL refinada:
     - `territory_id` persistido apenas no escopo territorial.
   - fechamento incremental de lacunas de camada:
     - `territory_neighborhood_proxy` (bairro proxy sobre base setorial) publicado no backend de mapa.
     - `QgMapPage` com fluxo explicito de `local_votacao` (toggle, orientacao e contexto da selecao).
     - `QgOverviewPage` aplicando `layer_id` tambem no mapa dominante da home executiva.
     - `OpsLayersPage` com alerta de degradacao de readiness por camada (`fail`, `warn`, `pending`).

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
Status:
- concluido (BD-050, BD-051 e BD-052 concluidos tecnicamente em 2026-02-21).
Progresso atual:
- `BD-050` implementado com:
  - script dedicado `scripts/backfill_environment_history.py` para bootstrap + carga multi-ano (`INMET`, `INPE_QUEIMADAS`, `ANA`);
  - hardening de integridade temporal em `tabular_indicator_connector` (bloqueio de carga quando ano nao casa com `reference_period`);
  - thresholds explicitos `min_periods_inmet/inpe_queimadas/ana = 5`;
  - scorecard SQL ampliado com metricas de periodos distintos por fonte ambiental.
- `BD-051` implementado com:
  - agregacao ambiental por `district` e `census_sector` em `map.v_environment_risk_aggregation`;
  - endpoint operacional `GET /v1/map/environment/risk`;
  - checks de qualidade dedicados para cobertura e nulos da agregacao ambiental;
  - scorecard ampliado com metricas `environment_risk_*`.
- `BD-052` implementado com:
  - mart Gold `gold.mart_environment_risk` com cobertura `municipality|district|census_sector`;
  - endpoint executivo `GET /v1/environment/risk` para consumo no QG;
  - checks de qualidade dedicados para cobertura e nulos do mart Gold;
  - scorecard ampliado com metricas `environment_risk_mart_*`.

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
Status:
- concluido em 2026-02-22 (`BD-060`, `BD-061`, `BD-062`).
Progresso atual:
- `BD-060` implementado com:
  - tabela/view de contratos versionados em `ops.source_schema_contracts` e `ops.v_source_schema_contracts_active`;
  - sincronizacao automatica via `scripts/sync_schema_contracts.py` e `configs/schema_contracts.yml`;
  - check dedicado `check_source_schema_contracts` no `quality_suite`;
  - scorecard ampliado com `schema_contracts_active_coverage_pct`.
- `BD-061` implementado com:
  - suite de contratos por conector em `tests/contracts/test_schema_contract_connector_coverage.py`;
  - cobertura minima validada (`>= 90%`) para conectores elegiveis;
  - testes parametrizados por conector com falha explicita para ausencia/quebra de contrato.
- `BD-062` implementado com:
  - check de drift por conector (`check_source_schema_drift`) no `quality_suite`;
  - alerta operacional por `fail` em `ops.pipeline_checks` para drift detectado;
  - scorecard ampliado com `schema_drift_fail_checks_last_7d`.

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
Status:
- concluido (2026-02-22).
Progresso atual:
- `BD-070` implementado com:
  - view `gold.mart_priority_drivers` em `db/sql/015_priority_drivers_mart.sql`;
  - consumo em `GET /v1/priority/list`, `GET /v1/priority/summary` e `GET /v1/insights/highlights`;
  - scorecard ampliado com `priority_drivers_rows` e `priority_drivers_distinct_periods`.
- `BD-071` implementado com:
  - governanca de versao em `ops.strategic_score_versions` + `ops.v_strategic_score_version_active` (`db/sql/016_strategic_score_versions.sql`);
  - pesos por dominio/indicador aplicados no `gold.mart_priority_drivers` com colunas auditaveis de versao e pesos;
  - scorecard ampliado com metricas de versao ativa e rastreabilidade de score.
- `BD-072` implementado com:
  - trilha de explicabilidade estruturada em `GET /v1/priority/list` e `GET /v1/insights/highlights`;
  - payload de explainability com `trail_id`, cobertura territorial, ranking, thresholds e metodo/versao de score;
  - evidencia com `updated_at` e `deep_link` de insights para triagem contextual.

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
Status:
- concluido tecnicamente (2026-02-22), com `BD-080`, `BD-081` e `BD-082` entregues.
Progresso atual:
- `BD-080` implementado com orquestracao incremental em `scripts/run_incremental_backfill.py`:
  - decisao por historico de `ops.pipeline_runs` (`no_previous_run`, `latest_status!=success`, `stale_success`);
  - reprocessamento seletivo por `--reprocess-jobs` e `--reprocess-periods`;
  - pos-carga com `dbt_build` e `quality_suite` por periodo com sucesso;
  - relatorio operacional em `data/reports/incremental_backfill_report.json`.
- `BD-081` implementado com tuning de custo/performance:
  - migration `db/sql/017_d8_performance_tuning.sql` com indices para filtros de ops e geocodificacao urbana;
  - `scripts/benchmark_api.py` ampliado com suite `ops` e alvo `p95 <= 1500ms`;
  - validacao de contrato SQL + aplicacao de migrations atualizadas (`19` scripts).
- `BD-082` implementado com playbook operacional executavel:
  - script `scripts/generate_incident_snapshot.py` para snapshot unico de incidente (readiness + runs/checks falhos + acoes recomendadas);
  - cobertura de teste unitario em `tests/unit/test_generate_incident_snapshot.py`;
  - runbook consolidado com rotina de triagem em `docs/OPERATIONS_RUNBOOK.md` (secao `11.8`).

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

Regra operacional para evitar bifurcacao de frente:
1. "paralelo parcial" nesta secao indica dependencia/arquitetura, nao execucao simultanea no ciclo diario.
2. no ciclo diario, operar com WIP=1:
   - uma trilha ativa por vez;
   - trilha definida em `docs/PLANO_IMPLEMENTACAO_QG.md`.
3. backlog deste arquivo nao substitui fila ativa de sprint.

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

## 7) Plano operacional sem dispersao (atualizado em 2026-02-19)

Objetivo:
1. fechar primeiro a estabilidade funcional do mapa e telas criticas.
2. travar a entrada em novas frentes ate cumprir os gates de qualidade desta fase.

Fonte de controle de execucao:
1. este bloco define guardrails de foco;
2. a fila ativa e ordem diaria continuam sob `docs/PLANO_IMPLEMENTACAO_QG.md`;
3. `docs/HANDOFF.md` registra apenas o estado da trilha ativa.

### Fase 1 - Estabilizacao de execucao D3 (foco unico)

Escopo:
1. `Mapa` (`/mapa`) sem regressao funcional em fluxo territorial e urbano.
2. `Visao Geral` (`/`) com mapa dominante consistente com filtros e camada detalhada.
3. `Territorio 360` e `Eleitorado` sem estado vazio por falha de contrato/back-end.
4. `OpsLayersPage` com leitura de degradacao (`fail`, `warn`, `pending`) operacional.

Gate de saida da Fase 1:
1. `npm --prefix frontend run test` sem falhas.
2. `npm --prefix frontend run build` concluido.
3. smoke local das telas criticas sem erro de carregamento.

### Fase 2 - Confiabilidade de dados (gate de producao tecnica)

Escopo:
1. consolidar evidencias da janela corrente em scorecard, readiness e benchmark.
2. eliminar divergencia entre "dados existem no banco" e "dados aparecem na UX".

Comandos obrigatorios:
1. `python scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json`
2. `python scripts/backend_readiness.py --output-json`
3. `python scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json`

Gate de saida da Fase 2:
1. `backend_readiness`: `READY`, `hard_failures=0`.
2. benchmark urbano dentro do alvo definido para D3.
3. scorecard atualizado e versionado em `data/reports/`.

### Fase 3 - Fechamento de pendencias de fonte/conector criticas

Escopo:
1. atacar itens `partial/blocked` que impactam diretamente telas executivas.
2. priorizar conectores que afetam mapas e indicadores usados no QG.

Gate de saida da Fase 3:
1. lista de conectores criticos com dono e prazo.
2. reducao objetiva de `partial/blocked` no `ops.connector_registry`.

### Fase 4 - Expansao controlada (D4/D5)

Regra de entrada:
1. so iniciar novas implementacoes amplas de D4/D5 apos gates das Fases 1-3.

Escopo:
1. mobilidade/infraestrutura (D4) e ambiental/risco (D5) com aceite mensuravel por sprint.

## 8) Sequencia logica de implementacao (resumo executivo)

1. estabilizar produto visivel (mapa + telas criticas).
2. validar confiabilidade operacional (readiness + qualidade + benchmark).
3. fechar pendencias de dados/conectores que travam valor de negocio.
4. expandir dominos novos apenas com base estavel.

## 9) Regra de priorizacao para evitar dispersao

Antes de iniciar qualquer nova issue, responder "sim" para todos:
1. esta entrega aumenta confiabilidade das telas criticas agora?
2. existe criterio de aceite objetivo e medivel?
3. existe evidencia automatizavel (teste/script/relatorio)?
4. nao abre nova frente sem fechar uma frente critica atual?

## 10) Catalogo consolidado de fontes (oficial)

Ja implementadas no produto:
1. IBGE (admin, geometrias, indicadores)
2. TSE (eleitorado, resultados)
3. INEP, DATASUS, SICONFI, MTE
4. SIDRA, SENATRAN, SEJUSP-MG, SIOPS, SNIS
5. INMET, INPE Queimadas, ANA, ANATEL, ANEEL
6. Urbano: OSM vias (`urban_roads`) e POIs (`urban_pois`)

Em consolidacao/expansao pela trilha D*:
1. D2: CECAD/CadUnico e Censo SUAS (com governanca de acesso)
2. D4: mobilidade e infraestrutura urbana complementar
3. D5: historico ambiental multi-ano e agregacoes por territorio fino

Regra:
1. qualquer nova fonte deve entrar como issue BD-* neste backlog antes de integrar ao plano executavel.
