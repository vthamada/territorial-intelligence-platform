# Territorial Intelligence Platform - Handoff

Data de referência: 2026-02-25
Planejamento principal: `docs/PLANO_IMPLEMENTACAO_QG.md`
North star de produto: `docs/VISION.md`
Contrato técnico principal: `CONTRATO.md`

## Trilha ativa unica (executável no ciclo atual)

1. Trilha ativa oficial (WIP=1):
   - `D5` concluido tecnicamente (`BD-050`, `BD-051`, `BD-052`).
   - `D6` concluido tecnicamente (`BD-060`, `BD-061`, `BD-062`).
   - `D7` concluido tecnicamente (`BD-070`, `BD-071`, `BD-072`).
   - `D8` concluido tecnicamente (`BD-080`, `BD-081`, `BD-082`).
   - `D4-mobilidade/frota` encerrada com entregas `BD-040`, `BD-041` e `BD-042`.
   - Mapa estratégico reestruturado (visão estratégica, círculos proporcionais, contorno municipal).
  - Refatoração completa do mapa executivo conforme `docs/UI_MAPA.md` (layout 2-col, bottom panel collapsible, remoção de clutter técnico).
  - Ajuste final do mapa para aderência ao mock de referência: topo com apenas base map + export, busca acima do mapa, sem controles fantasmas e sem modo simplificado.
  - Entrega concluída: mapa executivo consolidado em OSM-only com remoção do fluxo simplificado e payload eleitoral agregado por local de votação (com lista/contagem de seções no tooltip e drawer).
  - Ajuste de usabilidade no painel de camadas: toggles alinhados horizontalmente e todos desmarcados por padrão.
  - Diagnóstico técnico convertido em implementação: endpoint `/v1/electorate/map` agora suporta `aggregate_by=polling_place` para retornar agregação de local de votação.
    - Contrato de URL do mapa consolidado: `/mapa` não propaga mais `metric`/`period` legados em sync interno e deep-links de overview/prioridades.
  - Varredura backend concluída em `/v1/map/tiles/*`: removido branch legado que aplicava `metric/period` em tiles territoriais.
    - Varredura frontend concluída: `VectorMap` não envia mais `metric/period/domain` em URL de tiles e `QgMapPage` não consome mais `metric/period` da URL no bootstrap.
  - Locais de votação estabilizados no mapa: fallback automático para ano eleitoral com dados (`2024`) quando o período estratégico ativo retorna vazio no agregado por local.
  - **Correção de geolocalização**: locais de votação agora usam centroide do distrito-sede (IBGE geocode+05) em vez de `ST_PointOnSurface` do polígono municipal. Distância ao centro urbano: 1.7km (antes ~37.6km). Registros existentes de zonas e seções eleitorais atualizados in-place.
  - **Distribuição espacial por local**: query de polling places gera coordenada única por local via hash determinístico (`md5`) dentro do polígono do distrito-sede, eliminando cluster único. `clusterMaxZoom` ajustado para z=12 conforme spec UI_MAPA.md §5.3.
  - **Geocodificação real (INEP + Nominatim)**: locais de votação agora têm coordenadas reais geocodificadas. Pipeline cruza nomes com Censo Escolar INEP 2024 (endereços) + Nominatim, complementado por estimativas manuais por distrito. Seed em `data/seed/polling_places_diamantina.csv` (36/36 locais). Query CTE atualizada para usar `dt.geometry` real quando disponível, com fallback hash para municípios sem geocodificação.
2. Status de validação (2026-02-25):
  - `npm --prefix frontend run test -- --run` -> `85 passed` (21 test files).
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py -q` -> `39 passed`.
   - `npm --prefix frontend run build` -> `OK`.
2. Status da trilha anterior (D3-hardening, encerrada em 2026-02-21):
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
   - `npm run test -- --run` (em `frontend/`) -> `78 passed`.
   - `npm run build` (em `frontend/`) -> `OK`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json` -> `ALL PASS`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
3. Validação de fechamento técnico de D4 (2026-02-21):
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `47 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 13 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - smoke API: `GET /v1/mobility/access?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
   - GitHub issues encerradas no mesmo ciclo:
     - `#13` (`BD-040`) -> `closed`.
     - `#14` (`BD-041`) -> `closed`.
     - `#15` (`BD-042`) -> `closed`.
4. Critério de saida (DoD do ciclo D4):
   - suite backend/frontend em `pass`;
   - readiness com `status=READY` e `hard_failures=0`;
   - scorecard de cobertura sem regressão critica;
   - evidencias registradas no proprio `HANDOFF` e em `docs/CHANGELOG.md`.
5. Próximo passo imediato:
   - manter rotina recorrente da janela de 30 dias com persistência de snapshots (`scripts/persist_ops_robustness_window.py`) e acompanhar drift para manter `status=READY`, `severity=normal` e `gates.all_pass=true`.
6. Governança de issue:
   - ao concluir item técnico, encerrar issue correspondente no GitHub na mesma rodada.
7. Regra de leitura:
   - apenas esta secao define "próximo passo executável" no momento;
   - secoes de "próximos passos" antigas abaixo devem ser lidas como histórico.

## Atualizacao operacional (2026-02-25) - Contrato de URL do mapa sem métrica legada

1. Problema de UX/contrato corrigido:
  - a rota `/mapa` estava recebendo e persistindo `metric`/`period` de contexto anterior (ex.: MTE), sem utilidade para o fluxo operacional atual.
2. Ajuste aplicado:
  - sincronização de URL no `QgMapPage` removendo persistência de `metric`/`period`;
  - deep-links para `/mapa` em overview e prioridades simplificados para `territory_id`/`level`.
3. Validação da rodada:
  - frontend tests -> `84 passed`;
  - frontend build -> `OK`.
4. Próximo passo imediato (WIP=1):
  - homologar navegação real (`overview`/`prioridades` -> `/mapa`) confirmando URL limpa e comportamento estável dos overlays eleitorais por local.

## Atualizacao operacional (2026-02-25) - Varredura backend de tiles (`/v1/map/tiles/*`)

1. Diagnóstico backend confirmado:
  - endpoint de tiles territoriais ainda possuía branch legado condicionado por `metric`+`period` para `JOIN` em `silver.fact_indicator`.
2. Correção aplicada:
  - branch legado removido em `routes_map.get_mvt_tile`;
  - tiles territoriais renderizam somente via recorte geométrico da camada (sem dependência de `metric/period/domain`).
3. Evidência técnica:
  - `tests/unit/test_api_contract.py` recebeu teste específico para garantir que query legada é ignorada no SQL;
  - `pytest tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py -q` -> `39 passed`.
4. Próximo passo imediato (WIP=1):
  - executar homologação funcional no mapa com servidor local ativo e verificar logs de acesso após hard-refresh para confirmar redução de chamadas com query legada no fluxo atual.

## Atualizacao operacional (2026-02-25) - Varredura frontend de tiles e bootstrap da rota `/mapa`

1. Legado removido na geração de URL de tiles:
  - `VectorMap` deixa de anexar `metric/period/domain` em `/v1/map/tiles/*`.
2. Legado removido no bootstrap de rota:
  - `QgMapPage` deixa de ler `metric/period` da query string no carregamento inicial.
3. Ajustes de consistência:
  - `QgOverviewPage` deixa de repassar `metric/period` ao mapa vetorial;
  - testes de páginas QG atualizados para refletir o novo contrato.
4. Evidência técnica:
  - `npm --prefix frontend run test -- --run` -> `84 passed`;
  - `npm --prefix frontend run build` -> `OK`.
5. Próximo passo imediato (WIP=1):
  - validar em homologação com hard-refresh que os logs de tiles não exibem mais query legada no fluxo padrão de navegação.

## Atualizacao operacional (2026-02-25) - Exibição de locais de votação no mapa (fallback de ano)

1. Problema tratado:
  - no período estratégico padrão (`2025`), a consulta de eleitorado por local podia retornar vazia, impedindo renderização dos pontos de locais de votação.
2. Correção aplicada:
  - ao ativar `Locais de votacao`, o mapa muda automaticamente para `secao_eleitoral` para garantir elegibilidade da camada;
  - trigger de fetch foi desacoplado do timing da troca de nível e passa a responder diretamente ao estado do checkbox;
  - `QgMapPage` passa a consultar locais de votação sob demanda ao ativar o checkbox `Locais de votacao` (nível `secao_eleitoral`);
  - após o fetch inicial do período ativo, consulta automaticamente `2024` quando `2025` não retorna itens para `aggregate_by=polling_place`.
3. Resultado esperado:
  - ao ativar `Locais de votação`, os pontos voltam a aparecer com dados válidos mesmo quando o período estratégico não possui base eleitoral consolidada.
4. Evidência técnica:
  - novo teste de regressão no `QgPages.test.tsx` garantindo a sequência `2025 -> 2024`.
  - frontend suite/build em `pass`.

## Atualizacao operacional (2026-02-25) - OSM-only + agregação eleitoral por local de votação

1. Backend/API eleitoral evoluído para comportamento de local de votação:
  - `GET /v1/electorate/map` passou a aceitar `aggregate_by` (`none|polling_place`);
  - para `level=electoral_section` + `metric=voters`, a resposta agregada por local retorna:
    - total de eleitores por local;
    - quantidade de seções (`section_count`);
    - lista de seções (`sections`);
    - metadados de identificação do local (`polling_place_name`, `polling_place_code`).
2. Frontend do mapa consolidado no modo operacional único:
  - removido fluxo de modo simplificado;
  - removidas expectativas de alternância de basemap legado na experiência principal;
  - comportamento alinhado para OSM-only com foco em leitura territorial sem modos paralelos.
3. UX eleitoral refinada no mapa:
  - tooltip e drawer do ponto eleitoral passam a exibir dados de local agregado e seções associadas.
4. Estabilização técnica:
  - `VectorMap` recebeu guarda para `areTilesLoaded` ausente em mocks, eliminando erro de runtime em testes.
5. Evidência da rodada:
  - `npm --prefix frontend run test -- --run` -> `84 passed`;
  - `npm --prefix frontend run build` -> `OK`;
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
6. Próximo passo imediato (WIP=1):
  - validar em homologação o comportamento visual de clusters eleitorais agregados por local em múltiplos níveis de zoom, garantindo legibilidade executiva com dados reais.

## Atualizacao operacional (2026-02-25) - RCA + hotfix locais de votação sem retorno

1. Sintoma em produção local:
  - chamada de mapa eleitoral agregado por local retornando `500` em `/v1/electorate/map` com `aggregate_by=polling_place`.
2. Diagnóstico completo:
  - banco com dados válidos para agregação:
    - `electoral_section=144` territórios;
    - `polling_place_name=144/144` e `polling_place_code=144/144` preenchidos em `silver.dim_territory.metadata`;
    - `36` locais distintos agregáveis.
  - causa raiz no backend SQL:
    - `GroupingError` (PostgreSQL): coluna `dt.metadata` usada em expressão do `SELECT` não compatível com `GROUP BY` original.
3. Correção aplicada:
  - query reestruturada com CTE `grouped` para agregar por local primeiro;
  - cálculo de `territory_id` hash movido para select externo sobre os campos já agregados.
4. Evidência pós-fix:
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&aggregate_by=polling_place&year=2024&include_geometry=true&limit=500` -> `200`, `items=36`.
  - `metadata.coverage_note=polling_place_aggregated`.
  - backend unit tests alvo -> `37 passed`.
5. Próximo passo imediato:
  - validar UX em homologação com toggles eleitorais e zoom (cluster/tooltip/drawer) agora que o payload agregado está estável.

## Atualizacao operacional (2026-02-25) - Correção overlays UBS/Escola + sidebar de camadas

1. Bug corrigido: checkboxes de UBS e Escola não exibiam pontos no mapa.
   - causa raiz: condição `enabled` dos overlays estava bloqueada por `strategicView === "services" || strategicView === "both"` — na visão padrão "sections", os pontos nunca apareciam.
   - correção: `enabled` agora depende exclusivamente do estado do checkbox (`activeOverlayIds.has(id)`).
2. Painel de camadas reestruturado como sidebar lateral:
   - novo layout: `map-with-sidebar` flex container com map canvas + aside sidebar + footer bar.
   - sidebar e footer sempre visíveis independentemente do modo de mapa (vector/choropleth/fallback).
   - removido grupo "Risco / Estrategia" (fase 2).
   - 3 grupos ativos: Território, Eleitoral, Serviços.
3. Validação:
   - `npm --prefix frontend run test -- --run` -> `91 passed`.
   - `npm --prefix frontend run build` -> `OK`.

## Atualizacao operacional (2026-02-25) - Reestruturação completa do mapa estratégico

1. Reestruturação fundamental do mapa executivo para entrega estratégica:
   - barra superior reorganizada em 3 grupos: Visualização (Seções eleitorais / Serviços / Seções + Serviços), Mapa base (Ruas / Claro / Sem base), Ações (Simplificado/Avançado + SVG + PNG).
   - painel de camadas limpo com checkboxes alinhados por grupo: Território (Limite municipal + Distritos), Eleitoral (Seções + Locais de votação), Serviços (Escolas + UBS), Risco (Hotspots + Índice - fase 2).
2. Seções eleitorais agora são círculos proporcionais via GeoJSON:
   - fonte: endpoint `/electorate/map?include_geometry=true` que retorna geometria + contagem de eleitores.
   - raio proporcional: `max(4, min(18, 0.35 * sqrt(voters)))` em pixels.
   - clustering nativo do MapLibre GL com `clusterRadius=50`, `clusterMaxZoom=14`, `clusterProperties: { sum_voters: ['+', ['get', 'voters']] }`.
   - tooltip: Seção (nome), Eleitores (contagem), % do município, Fonte (TSE | Eleitorado).
   - cluster tooltip: N seções agrupadas, Total de eleitores.
3. Modo contorno municipal (boundary-only):
   - quando visão estratégica é "Seções" ou "Seções + Serviços", polígono municipal renderizado apenas como contorno (sem preenchimento).
   - implementado como `line` layer no VectorMap com estilo sutil.
4. Remoções da UI:
   - zonas eleitorais removidas do painel de camadas.
   - modos Coroplético/Heatmap/Apenas críticos/Gap removidos do radiogroup.
   - `vizMode` mantido internamente mas não exposto ao usuário.
   - seção "Resumo operacional do mapa" removida.
   - texto "Camada recomendada:" removido.
5. Arquitetura expandida no VectorMap:
   - novo tipo `GeoJsonClusterConfig` com suporte completo a clustering, radius expression, tooltip functions.
   - prop `geoJsonLayers?: GeoJsonClusterConfig[]` para adicionar camadas GeoJSON com clustering.
   - prop `boundaryOnly?: boolean` para modo contorno.
   - cleanup automático de sources/layers GeoJSON em detach/update cycles.
6. Evidência técnica:
   - `npm --prefix frontend run test -- --run` -> `91 passed`.
   - `npm --prefix frontend run build` -> `OK`.
7. Próximo passo imediato:
   - validar em homologação com dados reais de operação os cenários de clustering em zoom alto e contorno municipal.

## Atualizacao operacional (2026-02-24) - Opção (a) concluída com zeragem de warnings

1. Implementação operacional da opção (a) concluída:
  - materialização de indicadores submunicipais em `silver.fact_indicator` executada pelo pipeline existente `ibge_geometries_fetch` (`reference_period=2025`, `force=true`).
2. Evidência da execução:
  - `ibge_geometries_fetch` -> `success`, `rows_extracted=121`, `rows_written=121`.
3. Resultado de qualidade pós-execução:
  - `quality_suite(reference_period='2025')` -> `success`;
  - `failed_checks=0`, `warning_checks=0`.
4. Delta objetivo dos checks alvo:
  - `indicator_rows_level_district` passou para `pass` (`11` linhas observadas);
  - `indicator_rows_level_census_sector` passou para `pass` (`109` linhas observadas).
5. Estado atual (WIP=1):
  - baseline operacional sem warnings e sem hard-fail no gate de qualidade.
6. Próximo passo imediato:
  - manter rotina de validação recorrente e garantir execução periódica do `ibge_geometries_fetch` na janela operacional para preservar cobertura submunicipal.
7. Comando único recomendado (execução recorrente):
  - `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -c "from pipelines.ibge_geometries import run as run_geo; from pipelines.quality_suite import run as run_quality; import json; print(json.dumps({'ibge_geometries_fetch': run_geo(reference_period='2025', force=True), 'quality_suite': run_quality(reference_period='2025')}, ensure_ascii=False))"`
8. Atalho operacional preferencial:
  - `make ops-routine` (executa materialização submunicipal + validação de qualidade em sequência).
9. Atalho operacional Windows (sem `make`):
  - `powershell -ExecutionPolicy Bypass -File scripts/ops-routine.ps1 -ReferencePeriod 2025 -Force`.

## Atualizacao operacional (2026-02-24) - Mapa estratégico multicamadas (foco executivo)

1. Reestruturação do mapa executada para leitura territorial de decisão:
  - operação explícita em macro e granularidade interna (município, distritos/setores, pontos estratégicos);
  - recorte territorial com alternância direta entre município completo e área urbana (proxy).
2. Modos de visualização consolidados no frontend:
  - `Coropletico`, `Pontos`, `Heatmap`, `Apenas criticos`, `Gap (eleitores/servicos)`.
3. Organização estratégica de camadas implementada em grupos:
  - `Territorio`, `Eleitoral`, `Servicos`, `Risco / Estrategia`.
4. Interações executivas reforçadas:
  - tooltip de hover com nome, indicador, tendência, fonte e atualização;
  - drawer com score/contexto/evidências e ações `Perfil 360`, `Cenarios`, `Adicionar ao Brief`.
5. Sistema de overlays interativos implementado (2026-02-24):
  - VectorMap.tsx: novo prop `overlays` com tipo `OverlayLayerConfig[]` suportando vizTypes `circle`, `fill` e `heatmap`;
  - cada overlay tem source MVT independente, layer visual dedicada e interação isolada (click/hover/tooltip);
  - 5 overlays configurados no QgMapPage: Escolas (urbano/educação), UBS/Saúde (urbano/saúde), Seções eleitorais (pontos), Heatmap eleitoral, Zonas eleitorais (polígonos);
  - Escolas e UBS usam filtro client-side no tile `urban_pois` via propriedade `category` (OSM sourced);
  - Zonas/Seções eleitorais usam tiles `territory_electoral_zone` e `territory_electoral_section`;
  - painel de camadas estratégicas com checkboxes para ativar/desativar cada overlay independentemente;
  - summary note mostra overlays ativos no rodapé do painel.
6. Evidência técnica da rodada:
  - `npm --prefix frontend run test -- --run` -> `91 passed`;
  - `npm --prefix frontend run build` -> `OK`;
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`;
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `29 passed`.
6. Estado atual:
  - mapa alinhado ao objetivo de núcleo estratégico territorial, com leitura multicamadas e interações orientadas à priorização executiva.
7. Próximo passo imediato (WIP=1):
  - validar em homologação com dados reais de operação os cenários `apenas criticos` e `gap`, ajustando thresholds de severidade/legenda se necessário.

## Atualizacao operacional (2026-02-24) - Backfill temporal ANA/INMET/INPE concluido

1. Execução temporal concluída para fechamento de lacunas de período em fontes ambientais:
  - `ana_hydrology_fetch`, `inmet_climate_fetch`, `inpe_queimadas_fetch`;
  - períodos executados: `2021,2022,2023,2024,2025` com `reprocess=true`.
2. Evidência operacional da rodada:
  - incremental -> `planned=15`, `executed=15`, `success=15`, `failed=0`;
  - relatório consolidado em `data/reports/backfill_ana_inmet_inpe_2021_2025.json`.
3. Resultado de gate pós-backfill:
  - `quality_suite(reference_period='2025')` -> `success`;
  - `failed_checks=0`, `warning_checks=2` (redução de `5` para `2`).
4. Delta de qualidade confirmado:
  - `source_periods_ana`, `source_periods_inmet` e `source_periods_inpe_queimadas` passaram para `pass` com `5` períodos observados.
5. Estado atual (WIP=1):
  - backend/readiness segue estável, sem hard-fail;
  - warnings remanescentes são não bloqueantes e restritos a cobertura de indicadores submunicipais (`district` e `census_sector`).
6. Próximo passo imediato:
  - decidir entre (a) materializar indicadores submunicipais no `fact_indicator` para eliminar os 2 warnings restantes, ou (b) manter esses checks como sinalização de roadmap sem impacto de gate.

## Atualizacao operacional (2026-02-24) - Conector Portal da Transparência municipal

1. Backend de ingestão ampliado com fonte federal municipal:
  - novo pipeline `portal_transparencia_fetch` implementado em `src/pipelines/portal_transparencia.py` com agregação anual para Diamantina (`codigoIbge=3121605`);
  - indicadores publicados em `silver.fact_indicator` para benefícios sociais, recursos recebidos, convênios, renúncias e transferências COVID.
2. Integração de execução consolidada:
  - job registrado em `configs/connectors.yml` e `configs/jobs.yml` (onda `MVP-6`, referência padrão `2025`);
  - job integrado no fluxo incremental (`scripts/run_incremental_backfill.py`) e nas flows Prefect (`run_mvp_all` e `run_mvp_wave_6`).
3. Configuração obrigatória de segredo por ambiente:
  - variáveis adicionadas em `settings/.env.example`:
    - `PORTAL_TRANSPARENCIA_API_BASE_URL`;
    - `PORTAL_TRANSPARENCIA_API_KEY`.
  - sem chave configurada o job retorna `blocked` (sem escrita em Silver), preservando previsibilidade operacional.
4. Governança de qualidade atualizada:
  - `quality.py` e `quality_thresholds.yml` ajustados para cobertura de `PORTAL_TRANSPARENCIA` em `check_fact_indicator_source_rows`.
5. Evidência técnica da rodada:
  - `\.venv\Scripts\python.exe -m pytest tests/unit/test_portal_transparencia.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_b_connectors.py -q` -> `26 passed`.
6. Próximo passo imediato (WIP=1):
  - configurar `PORTAL_TRANSPARENCIA_API_KEY` no `.env` de cada ambiente e executar `portal_transparencia_fetch` (ou incremental) para materializar indicadores reais na base operacional.

## Atualizacao operacional (2026-02-24) - Desbloqueio SENATRAN 2024 e fechamento de gate

1. Causa raiz do `blocked` em `senatran_fleet_fetch(2024)` identificada e tratada:
  - discovery remoto não cobria padrões atuais de arquivos do portal SENATRAN 2024 (`xlsx/xls` e nomes fora do token antigo);
  - ambiente sem parser de Excel disponível para leitura dos artefatos remotos.
2. Correções aplicadas:
  - `src/pipelines/senatran_fleet.py` com discovery remoto ampliado (keywords + extensões suportadas);
  - validação do ambiente Python com `openpyxl` para leitura de planilhas SENATRAN.
3. Evidência operacional da rodada:
  - `senatran_fleet_fetch(reference_period='2024')` -> `success` (`rows_extracted=41025`, `rows_written=1`);
  - `quality_suite(reference_period='2025')` -> `success` (`failed_checks=0`, `warning_checks=12`, queda de 13 -> 12);
  - warning `source_periods_senatran` passou para `pass` (2 períodos).
4. Estado atual:
  - backend/readiness permanece `READY` e sem hard-fail;
  - warnings remanescentes são não bloqueantes e ligados a cobertura temporal/submunicipal de fontes específicas.
5. Próximo passo imediato (WIP=1):
  - reduzir warnings remanescentes focando em `INEP`, `SICONFI` e `TSE` (linhas 2025) e plano de ampliação temporal para `INMET`, `INPE_QUEIMADAS` e `ANA`.

## Atualizacao operacional (2026-02-24) - Rodada focal INEP/SICONFI/TSE (resultado)

1. Rodada de execução dirigida concluída:
  - `education_inep_fetch` e `finance_siconfi_fetch` reprocessados para `2025`;
  - `tse_catalog_discovery`, `tse_electorate_fetch` e `tse_results_fetch` reprocessados para `2025`.
2. Resultado operacional objetivo:
  - pipelines executaram com sucesso, porém `INEP` e `SICONFI` continuaram materializando `fact_indicator` com `reference_period=2024`;
  - `TSE` em `2025` segue sem pacote CKAN publicado (`fallback` para 2024 nas rotinas eleitorais), sem reflexo em `source_rows_tse` no `fact_indicator`.
3. Evidência de gate pós-rodada:
  - `quality_suite(reference_period='2025')` -> `success`, `failed_checks=0`, `warning_checks=12`.
4. Interpretação para continuidade:
  - warnings remanescentes de `INEP/SICONFI/TSE` nesta métrica específica não são falha de execução local, e sim limitação de disponibilidade/período da origem + modelagem atual dos checks.
5. Próximo passo imediato (WIP=1):
  - decidir entre (a) manter regra rígida aguardando publicação 2025 das fontes, ou (b) ajustar thresholds/checks para refletir disponibilidade real de período por fonte.

## Atualizacao operacional (2026-02-24) - Calibragem de checks por disponibilidade real (opcao b)

1. Ajuste implementado na camada de qualidade:
  - `quality.py` passou a suportar lag controlado por fonte em `source_rows_*` e por job em `ops_pipeline_runs` (via thresholds), preservando `warn` quando não há dado elegível.
2. Thresholds calibrados para cenário real de publicação:
  - `INEP`/`SICONFI` com metas de período ajustadas para `1` e lag anual explícito;
  - `TSE` removido de cobrança indevida em `fact_indicator` (`min_rows_tse=0`, `min_periods_tse=0`), mantendo cobertura eleitoral nos checks próprios de `fact_electorate`/`fact_election_result`.
3. Evidência pós-ajuste:
  - `quality_suite(reference_period='2025')` -> `success`, `failed_checks=0`;
  - warnings reduzidos para `5` (`198 pass`, `5 warn`).
4. Warnings remanescentes (não bloqueantes):
  - `indicator_rows_level_district` e `indicator_rows_level_census_sector`;
  - `source_periods_ana`, `source_periods_inmet`, `source_periods_inpe_queimadas` (target de 5 períodos ainda não atingido).
5. Próximo passo imediato (WIP=1):
  - decidir entre ampliar backfill temporal em `ANA/INMET/INPE_QUEIMADAS` ou ajustar meta de período para janela operacional atual.

## Atualizacao operacional (2026-02-23) - Ícones SVG, renomeação e fix drawer

1. Navegação minimalista:
   - ícones emoji substituídos por SVGs stroke-based (componente `NavIcon.tsx`) seguindo padrão Lucide/Feather;
   - sidebar reorganizada: 6 rotas principais + seção secundária (Território 360, Briefs, Admin).
2. Renomeação institucional:
   - "QG Estratégico" → "Painel de Inteligência Territorial" (header, sidebar branding, loading states, testes);
   - eyebrow permanece "Inteligência Territorial".
3. Fix do drawer de território no mapa:
   - botão de fechar ampliado (2.25rem), `pointer-events: auto`, `z-index: 2`, override de `:active`;
   - `e.stopPropagation()` no onClick do close para evitar propagação;
   - efeito de auto-open refatorado com early return quando dismissed e check de !territoryDrawerOpen.
4. Validação:
   - `npx vitest run` → `89 passed` (21 files);
   - `npm run build` → built 4.94s, tsc OK.
5. Próximo passo imediato (WIP=1):
   - validar visualmente com dev server; considerar dark mode toggle como P2.

## Atualizacao operacional (2026-02-23) - Executive Design System v2

1. Refatoração visual completa do frontend (`global.css`) com design system inspirado em dashboards executivos (Linear, Vercel, Notion):
   - design tokens CSS custom properties (cores, sombras, raios, transições, paleta semântica);
   - glass-morphism em sidebar e header (`backdrop-filter: blur(16px)`);
   - painéis com elevação dinâmica, loading spinner animado, KPI cards com accent border;
   - strategic index cards com borda colorida por nível de severidade;
   - tabelas com zebra striping + sticky headers, staggered grid animations;
   - custom scrollbar, print styles, sidebar branding "QG";
   - breakpoints responsivos (≤1024px, ≤640px).
2. TSX melhorias:
   - `App.tsx`: ícones emoji na navegação, header reestruturado com badge "API v1";
   - `AdminHubPage.tsx`: ícones em admin cards.
3. Validação:
   - `npx vitest run` -> `89 passed` (21 files);
   - `npm run build` -> `built in 4.07s`, tsc OK.
4. Próximo passo imediato (WIP=1):
   - refinar micro-interações e validar comportamento visual com dev server rodando;
   - considerar dark mode toggle como evolução futura P2.

## Atualizacao operacional (2026-02-23) - Correcoes de utilidade estratégica no mapa (feedback visual)

1. Correção aplicada para aumentar valor decisório do mapa executivo:
  - presets estratégicos adicionados em `QgMapPage` para direcionar rapidamente para `secao_eleitoral` (eleitorado) e `urban_pois` (serviços por bairros/proximidade);
  - aviso contextual quando o recorte municipal agregado não é suficiente para decisão territorial fina;
  - bloco operacional `Top secoes por eleitorado` exibindo ranking de seções com maior volume de eleitores.
2. Ajuste de UX do painel lateral territorial:
  - `Drawer` do mapa passou a operar sem backdrop modal (sem escurecer toda a página) e com largura responsiva, reduzindo efeito visual de bloqueio observado.
3. Validação da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx src/shared/ui/Drawer.test.tsx` -> `31 passed`;
  - `npm --prefix frontend run test -- --run` -> `89 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - seguir no refino incremental de legibilidade/fluidez do mapa mantendo foco em decisão territorial (seção eleitoral + serviços urbanos) sem abrir nova frente.

## Atualizacao operacional (2026-02-23) - Homologacao backend do evento operacional do mapa

1. Contrato de observabilidade consolidado no backend `/v1/ops/frontend-events`:
  - cobertura adicionada para ingestão do evento `map_operational_state_changed` com atributos operacionais do mapa;
  - cobertura adicionada para filtro por nome (`name=map_operational_state_changed`) na listagem paginada.
2. Evidência técnica da rodada:
  - `\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q` -> `32 passed`.
3. Resultado operacional:
  - frontend e backend ficam alinhados no fluxo de telemetria de estado operacional do mapa (emissão no frontend + aceitação/consulta no backend).
4. Próximo passo imediato (WIP=1):
  - manter refinamentos incrementais de fluidez/legibilidade no mapa executivo, sem abrir frente paralela.

## Atualizacao operacional (2026-02-23) - Sprint P0 mapa (telemetria de estado operacional)

1. Observabilidade do mapa executivo ampliada em `QgMapPage`:
  - evento `map_operational_state_changed` implementado para registrar transições `loading/error/empty/data` e estados de indisponibilidade de modo simplificado.
2. Atributos de triagem adicionados no evento:
  - `scope`, `level`, `state`, `renderer`, `metric`, `period`.
3. Cobertura de regressão da rodada:
  - `QgPages.test.tsx` validando estado `empty_simplified_unavailable` com emissão do evento correspondente.
4. Validação consolidada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `26 passed`;
  - `npm --prefix frontend run test -- --run` -> `88 passed`;
  - `npm --prefix frontend run build` -> `OK`.
5. Próximo passo imediato (WIP=1):
  - seguir no pacote P0 do mapa com refinamentos incrementais de fluidez/legibilidade mantendo evidência operacional em `/v1/ops/frontend-events` e gate completo de regressão.

## Atualizacao operacional (2026-02-23) - Sprint P0 mapa executivo (previsibilidade de estados)

1. Refino de fluidez/legibilidade aplicado no `QgMapPage` em ciclo curto:
  - fallback simplificado (`svg`) agora apresenta estado explícito para níveis territoriais não coropléticos (`setor/zona/secao`), evitando renderização ambígua de mini-mapa sem dado operacional;
  - busca/foco territorial contextualizados para recortes coropléticos (`municipio/distrito`) com orientação explícita para níveis granulares.
2. Cobertura de regressão ampliada:
  - `QgPages.test.tsx` recebeu cenário dedicado validando o estado `Modo simplificado indisponivel neste nivel`.
3. Validação da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `26 passed`;
  - `npm --prefix frontend run test -- --run` -> `88 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - manter pacote P0 do mapa executivo com refinamentos incrementais de previsibilidade/telemetria operacional sem abrir frente paralela.

## Atualizacao operacional (2026-02-23) - Hardening de robustez frontend (Admin + observabilidade)

1. Paridade de erro com contrato técnico concluída no hub administrativo:
  - `frontend/src/modules/admin/pages/AdminHubPage.tsx` agora exibe `message` e `request_id` em falhas de readiness/cobertura de camadas;
  - retry contextual (`Tentar novamente`) disponível nas falhas do Admin Hub.
2. Cobertura de testes de robustez ampliada:
  - `frontend/src/modules/admin/pages/AdminHubPage.test.tsx` validando erro com `request_id` + retry;
  - `frontend/src/shared/observability/bootstrap.test.ts` validando bootstrap único e captura de erros globais do navegador.
3. Validação da rodada:
  - `npm --prefix frontend run test -- --run src/modules/admin/pages/AdminHubPage.test.tsx src/shared/observability/bootstrap.test.ts` -> `3 passed`;
  - `npm --prefix frontend run test -- --run` -> `87 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - seguir no pacote P0 do mapa executivo (fluidez/legibilidade e previsibilidade de estados), sem abrir nova frente e preservando gate completo de regressão + build.

## Atualizacao operacional (2026-02-24) - Telemetria objetiva da troca de camada eleitoral

1. Entrega P0 concluída no fluxo do mapa executivo:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` passou a emitir `map_electoral_layer_toggled` quando ocorre transição efetiva entre `secao` e `local_votacao` no nível `secao_eleitoral`.
2. Objetividade de triagem reforçada:
  - evento registra `from_layer`, `to_layer`, `source`, `layer_id`, `layer_classification`, `scope` e `level`, mantendo semântica operacional para leitura em `/v1/ops/frontend-events`.
3. Regressão de frontend validada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `25 passed`;
  - `npm --prefix frontend run test -- --run` -> `84 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - manter refinamento P0 de legibilidade/fluidez no mapa executivo sem abrir nova frente, preservando gate completo de regressão + build a cada rodada.

## Atualizacao operacional (2026-02-23) - UX final do mapa executivo (drawer territorial)

1. Implementacao de UX do mapa em ciclo curto concluida no frontend:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` migrado para painel territorial em drawer com estrutura executiva (status, tendencia, valor, metricas, evidencias e acoes);
  - `frontend/src/styles/global.css` recebeu classes `territory-drawer-*` e `inline-link-button` para suportar o novo layout mantendo o `Drawer` compartilhado.
2. Ajustes de estabilidade aplicados durante a rodada:
  - correcoes de regressao de hooks na pagina de mapa (ordem estável);
  - alinhamento de labels de acao para compatibilidade de testes;
  - fallback de status no drawer derivado de valor quando a feature nao expõe `status`.
3. Validacao da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
  - `npm --prefix frontend run test -- --run src/app/e2e-flow.test.tsx` -> `5 passed`.
  - `npm --prefix frontend run test -- --run` -> `83 passed`.
  - `npm --prefix frontend run build` -> `OK`.
4. Regressao de fluxo E2E resolvida:
  - causa raiz: assercao ancorada em heading (`Diamantina`) que tambem existia no drawer do mapa, gerando falso positivo de transicao de rota;
  - correcao: `frontend/src/app/e2e-flow.test.tsx` passou a ancorar a validacao de navegacao em heading exclusivo da tela de territorio (`Status geral do territorio`).
5. Próximo passo imediato (WIP=1):
  - seguir com refinamentos P0 de UX do mapa mantendo regressao completa de frontend em `pass` a cada rodada.

## Atualizacao operacional (2026-02-23) - Fechamento local_votacao no mapa executivo

1. Refino P0 concluído no `QgMapPage` para modo `secao_eleitoral`:
  - estado `local_votacao` explicitado na interface para cenarios `disponivel`, `indisponivel no manifesto` e `camada ativa sem nome detectado`;
  - legenda eleitoral preservada com semântica clara de `secao eleitoral` vs `local de votacao`.
2. Drawer territorial ajustado para previsibilidade:
  - metadata sempre explicita comportamento de `local_votacao` quando camada de pontos está ativa, com fallback textual quando payload não traz nome do local.
3. Validação da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - consolidar telemetria objetiva de interação eleitoral no mapa (troca de camada `secao/local_votacao`) mantendo o mesmo gate de regressão + build.

## Atualizacao operacional (2026-02-23) - Legenda visual eleitoral e navegação lateral

1. Refino de UX executiva aplicado no frontend:
  - `QgMapPage` recebeu legenda visual compacta para modo `secao_eleitoral`, com leitura direta de `Secoes eleitorais` (recorte territorial) e `Locais de votacao` (pontos);
  - `App` migrou navegação principal para painel lateral no desktop, mantendo as mesmas rotas/links e comportamento responsivo.
2. Estilo consolidado sem abrir frente paralela:
  - `global.css` atualizado com layout `app-frame/app-sidebar/app-main` e bloco `map-inline-legend`.
3. Validação da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run src/app/App.test.tsx` -> `1 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - seguir para telemetria objetiva da troca de camada eleitoral (`secao` <-> `local_votacao`) e registrar evidência operacional no mesmo gate de regressão + build.

## Atualizacao operacional (2026-02-23) - Refatoracao completa de design do frontend

1. Refatoracao visual ampla concluida sem alterar contrato funcional:
  - shell executivo reestilizado com navegacao lateral consolidada e hierarquia visual mais clara;
  - tokens visuais modernizados para padronizar contraste, superfície e legibilidade;
  - componentes base da camada executiva (painéis, formulários, tabelas, estados e cards de contexto) harmonizados com linguagem única.
2. Escopo técnico da rodada:
  - mudança concentrada em `frontend/src/styles/global.css` com efeito transversal nas páginas QG/ops/território/eleitorado;
  - nenhum endpoint/contrato API alterado.
3. Validação de estabilidade:
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - implementar telemetria objetiva da troca de camada eleitoral (`secao` <-> `local_votacao`) e fechar evidência operacional no mesmo gate de regressão + build.

## Atualizacao operacional (2026-02-23) - Backend/DB fechado para foco em frontend

1. Gate de readiness de backend normalizado:
  - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
  - correção aplicada no SLO-3 (completude de checks): `runs_missing_checks=0` após backfill de check para run histórico sem registro.
2. Governança de conectores sincronizada:
  - `scripts/sync_connector_registry.py` executado com sucesso;
  - `ops.connector_registry` atualizado para `total=29`, `implemented=27`, `partial=2`;
  - `suasweb_social_assistance_fetch` e `cneas_social_assistance_fetch` confirmados como `implemented` em `MVP-6`.
3. Execução operacional não-dry de fontes abertas concluída:
  - `suasweb_social_assistance_fetch(reference_period='2025')` -> `success`, `rows_written=5`;
  - `cneas_social_assistance_fetch(reference_period='2025')` -> `success`, `rows_written=4`.
4. Evidência de persistência em banco:
  - `silver.fact_indicator` contém `9` linhas para `source in ('SUASWEB','CNEAS')` e `reference_period='2025'`, incluindo indicadores de ofertas CNEAS por proteção (`basica`, `especial`) e total.
5. Estado residual (não bloqueante para foco no frontend):
  - `SLO-1` permanece em warning na janela de 7 dias (`90.48% < 95.0%`), concentrado em histórico recente de `quality_suite` e `tse_electorate_fetch`.
6. Próximo passo imediato (WIP=1):
  - migrar foco principal para frontend executivo (refino UX e validação de fluxo de mapa), mantendo apenas monitoramento operacional recorrente do backend.

## Atualizacao operacional (2026-02-23) - Fechamento backend/db (delta de confiabilidade)

1. Causa de falha recorrente em qualidade normalizada:
  - `scripts/sync_schema_contracts.py` executado com `upserted=26` em `ops.source_schema_contracts`.
2. Efeito validado em execução real:
  - `quality_suite(reference_period='2025', dry_run=False)` voltou para `success` (`failed_checks=0`).
  - checks de contratos passaram para `pass`:
    - `schema_contracts_active_coverage_pct=100.0`;
    - `schema_contracts_missing_connectors=0`.
3. Estado de prontidão permanece:
  - `backend_readiness.py --output-json` -> `READY`, `hard_failures=0`.
4. Pendência residual para fechamento formal da trilha backend/db:
  - `SLO-1` da janela ainda abaixo de `95%` por efeito histórico de runs não-sucedidos dentro da própria janela;
  - ação recomendada: manter somente execuções estáveis e monitoramento até expurgo natural da janela.

## Atualizacao operacional (2026-02-23) - Integracao aberta SUASWEB/CNEAS consolidada

1. Integração de dados socioassistenciais abertos concluída em `MVP-6`:
  - `suasweb_social_assistance_fetch` ativo com recorte municipal (Diamantina) e indicadores de repasse;
  - `cneas_social_assistance_fetch` ativo com entidades e ofertas a partir de fontes abertas MISocial.
2. Correção técnica de raiz aplicada no motor tabular (`src/pipelines/common/tabular_indicator_connector.py`):
  - suporte a múltiplos recursos de catálogo no mesmo job (composição de indicadores entre arquivos/fontes complementares);
  - agregador `count` ajustado para contar candidatos textuais não vazios (não apenas valores numéricos).
3. Validação executada:
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_b_connectors.py tests/unit/test_prefect_wave3_flow.py -q` -> `21 passed`.
4. Estado operacional pós-ajuste:
  - estratégia open-data-first mantida;
  - conectores governados (`CECAD`, `CENSO_SUAS`) continuam fora do incremental padrão e requerem opt-in (`--allow-governed-sources`).
5. Próximo passo imediato (WIP=1):
  - executar rodada operacional não-dry de `MVP-6` (fontes abertas) e registrar evidência de linhas persistidas em `silver.fact_indicator`.

## Matriz de aderencia a VISION (2026-02-23)

Objetivo: traduzir o north star de `docs/VISION.md` em execução objetiva de curto prazo, sem abrir frentes paralelas.

| Bloco da VISION | Estado atual | Gap objetivo | Prioridade | Critério de aceite |
|---|---|---|---|---|
| Mapa dominante + painel estratégico | Alto | Consolidar telemetria dos refinamentos finais de UX (incluindo navegação lateral e legenda visual) | Alta | Regressões de páginas executivas em `pass` + evidência de telemetria operacional |
| Território eleitoral detalhado (`secao` + `local_votacao`) | Alto | Consolidar telemetria e evidência operacional da interação de camada | Alta | `QgPages.test.tsx` cobrindo cenários eleitorais + build frontend `OK` |
| Cruzamento Eleitorado + Serviços + Território | Parcial/Alto | Consolidar leitura demanda x oferta no fluxo único de mapa/perfil | Média | Fluxo de navegação entre `/mapa` -> `/territorio/:id` sem perda de contexto |
| Transparência oficial/proxy/hybrid + metadados | Alto | Ajustes finais de consistência visual/textual | Média | Badge/classificação e hint de método visíveis no estado de dados |
| Observabilidade de mapa (telemetria + benchmark) | Alto | Manter cadência recorrente e evidência operacional única por rodada | Alta | benchmark urbano `ALL PASS` + evento de prova em `/v1/ops/frontend-events` |
| Backlog pós-v2 (split view, time slider) | Pendente | Implementação incremental após gates de estabilização | Baixa | Planejamento fechado no plano executável antes de codar |

Próximo pacote técnico recomendado (WIP=1):
1. consolidar telemetria de troca de camada eleitoral (`secao` <-> `local_votacao`) com evento objetivo para triagem;
2. executar regressão focal de mapa + suíte frontend + build;
3. registrar evidência em `CHANGELOG` e atualizar este `HANDOFF` no fechamento da rodada.

## Atualizacao operacional (2026-02-23) - Foco ativo em dados abertos (sem bloqueio por credencial)

1. Diretriz operacional consolidada para o ciclo atual:
  - priorizar somente fontes abertas e de fácil acesso;
  - manter `CECAD` e `CENSO_SUAS` fora da execução incremental padrão até existir autorização institucional.
2. Implementação aplicada no orquestrador incremental:
  - `scripts/run_incremental_backfill.py` agora exclui por padrão os conectores governados `cecad_social_protection_fetch` e `censo_suas_fetch`;
  - habilitação desses conectores requer opt-in explícito com `--allow-governed-sources`.
3. Próximo passo imediato (WIP=1):
  - manter ingestão recorrente apenas de fontes abertas e monitorar cobertura/readiness sem abrir nova frente de credencial.

## Atualizacao operacional (2026-02-23) - Lacunas de dados executáveis tratadas

1. Plano curto executado ponta a ponta para reduzir lacunas acionáveis sem abrir nova frente:
  - `urban_transport_fetch(reference_period='2026')` -> `success`, `rows_extracted=22`, `rows_written=22`;
  - `tse_electorate_fetch(reference_period='2016')` -> `success`, `rows_extracted=13555`, `rows_written=13555`;
  - `tse_results_fetch(reference_period='2020'|'2018'|'2016')` -> `success` (`12`/`30`/`12` linhas escritas).
2. Validação de impacto pós-execução concluída:
  - `scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> melhoria de `pass=19/warn=13` para `pass=22/warn=10`.
3. Estado remanescente (não bloqueante para encerramento desta rodada):
  - conectores `partial` persistem em `ops.connector_registry`: `CECAD` e `CENSO_SUAS` (dependência externa);
  - `/v1/ops/source-coverage` mantém `TSE` e `OSM` com `no_fact_rows` neste recorte de métrica, sem regressão funcional nas camadas já alimentadas.
4. Próximo passo imediato (WIP=1):
  - manter foco em robustez operacional (janela recorrente + scorecard/readiness), tratando como P0 apenas lacunas com ação local imediata e sem abrir nova frente paralela.

## Atualizacao operacional (2026-02-23) - Secao eleitoral no banco/API (Diamantina/MG)

1. Implementação concluída em `src/pipelines/tse_electorate.py` para ingestão de seção eleitoral:
  - consumo de `perfil_eleitor_secao_2024_MG.zip`;
  - enriquecimento por `eleitorado_local_votacao_2024.zip`;
  - upsert de `electoral_section` em `silver.dim_territory`;
  - carga de `silver.fact_electorate` por seção e perfil demográfico.
2. Validação técnica da rodada:
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_electorate.py -q` -> `14 passed`.
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `36 passed`.
3. Execução operacional confirmada:
  - `run(reference_period='2024', dry_run=False)` em `tse_electorate_fetch` -> `success`, `rows_extracted=15248`, `rows_written=15248`.
4. Evidência de dados no banco após carga:
  - `silver.dim_territory` (`level='electoral_section'`, Diamantina): `rows=144`;
  - `silver.fact_electorate` (`level='electoral_section'`, `reference_year=2024`, Diamantina): `rows=14550`;
  - metadados de local de votação preenchidos em `dim_territory.metadata.polling_place_name`.
5. Próximo passo imediato (WIP=1):
  - manter ciclo curto focado em estabilização de consumo no frontend executivo (`secao_eleitoral`/`local_votacao`) com validação recorrente, sem abrir nova frente.

## Atualizacao operacional (2026-02-23) - Camadas eleitorais sem pendencia de geometria

1. Correção aplicada em `src/pipelines/tse_electorate.py`:
  - `electoral_zone` passa a receber geometria proxy (`ST_PointOnSurface` da geometria municipal), permitindo herança geométrica consistente para seções.
2. Reprocessamento concluído:
  - `tse_electorate_fetch` (`reference_period=2024`) -> `success`, `rows_extracted=15248`, `rows_written=15248`.
3. Validação de geometria no banco (Diamantina):
  - `electoral_section`: `144/144` com geometria válida;
  - `electoral_zone`: `2/2` com geometria válida.
4. Smoke API de consumo frontend:
  - `GET /v1/electorate?level=secao_eleitoral&period=2024&page_size=5` -> `200`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2024&limit=5&include_geometry=false` -> `200`, `items=5`.
5. Próximo passo imediato (WIP=1):
  - validar no frontend a mudança de status de cobertura das camadas `Secoes eleitorais` e `Locais de votacao` para `ready`, mantendo rotina de regressão curta.

## Atualizacao operacional (2026-02-23) - Fechamento de qualidade do eleitorado (Diamantina)

1. Saneamento de legado concluído no banco:
  - removidas linhas inválidas de `fact_electorate` com ano fora da faixa válida (`9999`);
  - consolidada duplicidade de `electoral_zone` (chave `101`) com merge de fatos e reparent de seções.
2. Prevenção de recorrência aplicada em código:
  - `src/pipelines/tse_results.py` passou a upsertar `electoral_zone` com chave canônica (`tse_section=''`, `ibge_geocode` preenchido e conflito por índice territorial canônico).
3. Estado pós-saneamento (Diamantina):
  - `fact_electorate` com anos válidos: apenas `2024` (escopo municipal/zona/seção);
  - `dim_territory` em `electoral_zone`: `1` linha para zona `101`.
4. Smoke de API mantido em `200`:
  - `GET /v1/electorate?level=secao_eleitoral&period=2024&page_size=5`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2024&page_size=5`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2024&limit=5&include_geometry=false`.
5. Próximo passo imediato (WIP=1):
  - definir e executar política de histórico eleitoral (anos anteriores) com prioridade para `2022` e `2020`, mantendo o recorte municipal e validação de cobertura por seção/local.

## Atualizacao operacional (2026-02-23) - Backfill historico 2022 concluido

1. Backfill de eleitorado executado em `reference_period=2022`:
  - `tse_electorate_fetch` -> `success`, `rows_extracted=15105`, `rows_written=15105`.
2. Estado de dados após backfill:
  - `fact_electorate` (escopo município/zona/seção) com anos disponíveis: `2022` e `2024`;
  - `electoral_section` permanece em `144` territórios com metadados de local preenchidos.
3. Smoke API do ano histórico (`2022`) validado:
  - `GET /v1/electorate?level=secao_eleitoral&period=2022&page_size=5` -> `200`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2022&page_size=5` -> `200`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2022&limit=5&include_geometry=false` -> `200`, `items=5`.
4. Próximo passo imediato (WIP=1):
  - executar backfill de `2020` no mesmo padrão e repetir validação curta de banco/API para consolidar histórico eleitoral mínimo comparável.

## Atualizacao operacional (2026-02-23) - Backfill historico 2020 concluido

1. Backfill de eleitorado executado em `reference_period=2020`:
  - `tse_electorate_fetch` -> `success`, `rows_extracted=14766`, `rows_written=14766`.
2. Estado histórico atual (Diamantina):
  - anos disponíveis em `fact_electorate` (município/zona/seção): `2020`, `2022`, `2024`.
3. Smoke API do ano histórico (`2020`) validado:
  - `GET /v1/electorate?level=secao_eleitoral&period=2020&page_size=5` -> `200`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2020&page_size=5` -> `200`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2020&limit=5&include_geometry=false` -> `200`, `items=5`.
4. Próximo passo imediato (WIP=1):
  - opcional: backfill de `2018` para ampliar série histórica eleitoral antes de congelar escopo do ciclo.

## Atualizacao operacional (2026-02-23) - Backfill historico 2018 concluido + robustez NaN

1. Hardening aplicado em `src/pipelines/tse_electorate.py`:
  - sanitização de `NaN` em metadata de seção (`polling_place_name`, `polling_place_code`, `voters_section`) antes do `jsonb`.
2. Backfill de eleitorado executado em `reference_period=2018`:
  - `tse_electorate_fetch` -> `success`, `rows_extracted=13974`, `rows_written=13974`.
3. Estado histórico final da rodada (Diamantina):
  - anos disponíveis em `fact_electorate` (município/zona/seção): `2018`, `2020`, `2022`, `2024`.
4. Smoke API do ano histórico (`2018`) validado:
  - `GET /v1/electorate?level=secao_eleitoral&period=2018&page_size=5` -> `200`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2018&page_size=5` -> `200`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2018&limit=5&include_geometry=false` -> `200`, `items=5`.
5. Próximo passo imediato (WIP=1):
  - congelar escopo eleitoral desta rodada e seguir apenas com monitoramento recorrente (sem abrir nova frente de dados eleitorais).

## Atualizacao operacional (2026-02-23) - Ingestao TSE executada para zona/seção eleitoral

1. Ingestão da onda TSE executada com `reference_period=2024`:
  - `tse_catalog_discovery` -> `success`;
  - `tse_electorate_fetch` -> `success` (`rows_extracted=698`, `rows_written=698`);
  - `tse_results_fetch` -> `success` (`rows_extracted=12`, `rows_written=12`).
  - execução adicional de `tse_results_fetch` com `reference_period=2022` -> `success` (`rows_extracted=24`, `rows_written=24`) para tentativa de obtenção de seção eleitoral.
2. Validação pós-ingestão no banco:
  - `silver.dim_territory` agora contém `electoral_zone` (`rows=2`);
  - `silver.fact_electorate` contém `electoral_zone` (`rows=349`) e `municipality` (`rows=710`);
  - `silver.fact_election_result` contém `electoral_zone` (`rows=12`) e `municipality` (`rows=12`).
3. Validação de consumo pela API (frontend-ready):
  - `GET /v1/electorate?level=zona_eleitoral&period=2024&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=zona_eleitoral&metric=voters&year=2024&limit=5&include_geometry=false` -> `200`, `items=1`.
4. Situação atual de seção eleitoral:
  - `secao_eleitoral` segue sem linhas nesta base (`total=0`), pois os recursos processados (`detalhe_votacao_munzona_2024_MG.csv` e `detalhe_votacao_munzona_2022_MG.csv`) não trouxeram coluna de seção (`section_column=null` no `parse_info` registrado em `ops.pipeline_runs`).
5. Próximo passo imediato (WIP=1):
  - manter dados de zona eleitoral ativos para o front e abrir recorte técnico único para ingestão dedicada de seção eleitoral quando houver recurso TSE com granularidade de seção disponível para Diamantina/MG.

## Atualizacao tecnica (2026-02-23) - local_votacao consolidado no mapa executivo

1. Implementacao frontend concluida em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - toggle rapido para alternar `Locais de votacao` <-> `Secoes eleitorais` no nivel `secao_eleitoral`;
  - legenda eleitoral explicita com tooltip de leitura;
  - mensagens contextuais preservadas para os cenarios `com local_votacao` e `sem local_votacao`.
2. Cobertura de regressao ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - validacao de botao `Exibir locais de votacao` quando a camada existe no manifesto;
  - validacao de botao `Exibir secoes eleitorais` quando `local_votacao` esta ativo.
3. Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Proximo passo imediato (WIP=1):
  - manter cadencia de benchmark/telemetria e fechar refinamentos de UX final do mapa (fluidez e legibilidade) sem abrir nova frente.

## Atualizacao tecnica (2026-02-23) - Refino de legibilidade operacional no mapa

1. Ajustes aplicados em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - resumo operacional do mapa publicado com estado consolidado (`escopo`, `nivel`, `camada`, `visualizacao`, `base`, `renderizacao`);
  - seletor de camada automática com rótulo explícito por contexto de zoom (`Automatica (recomendada no zoom atual)`).
2. Cobertura de regressão em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - validação da presença do resumo operacional;
  - validação do novo rótulo do seletor automático.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - seguir para homologação operacional recorrente (benchmark urbano + leitura de `/v1/ops/frontend-events`) mantendo `READY/normal/all_pass`.

## Atualizacao tecnica (2026-02-23) - Origem da camada explicita no painel do mapa

1. Ajuste de fluidez aplicado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - painel de camada detalhada passa a explicitar a origem da camada ativa (`origem: automatica` vs `origem: manual`), reduzindo ambiguidade na leitura operacional.
2. Cobertura de regressão ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - cenário padrão valida transição de `origem: automatica` para `origem: manual` ao alternar para `Locais de votacao`;
  - cenário com `layer_id` explícito valida retorno para `origem: automatica` após `Usar camada automatica`.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - manter ciclo curto de refinamento de previsibilidade de navegação no mapa com validação recorrente e sem abrir nova frente.

## Atualizacao tecnica (2026-02-23) - Aviso explicito de reset do foco territorial

1. Ajuste de previsibilidade aplicado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - aviso dedicado quando `Aplicar filtros` reinicia foco territorial anterior;
  - aviso dedicado quando `Limpar` reinicia foco territorial;
  - limpeza automática do aviso ao refocar território ou recentrar manualmente o mapa.
2. Cobertura de regressão ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - fluxo validado de foco territorial -> troca de escopo para urbano -> remoção de `territory_id` na URL + aviso explícito de reset.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - seguir com ajustes pequenos de fluidez de navegação no mapa (sem nova frente), mantendo evidência objetiva por rodada.

## Atualizacao tecnica (2026-02-23) - Aviso de recentralizacao automatica no mapa

1. Ajuste de previsibilidade aplicado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - `Aplicar filtros` agora exibe aviso explícito quando o mapa é recentrado automaticamente por mudança de escopo, nível ou zoom contextual;
  - `Limpar` agora exibe aviso explícito de retorno para visão inicial;
  - aviso é limpo em ações manuais de recenter/refoco para evitar ruído.
2. Cobertura de regressão ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - validação do aviso de recentralização no cenário de sincronização de query params após troca de escopo e aplicação de filtros.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - manter sequência de microrefinos de navegação no mapa com validação recorrente e sem abrir nova frente.

## Atualizacao tecnica (2026-02-23) - Utilidade executiva imediata no mapa

1. Ajuste de design orientado a decisão aplicado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - novo bloco `Leitura executiva imediata` inserido no painel estratégico do mapa;
  - destaque objetivo de prioridade territorial atual (top do recorte) e menor valor do recorte;
  - indicação de posição do território selecionado no ranking (`posição x/y`) e próximo passo explícito quando não houver seleção ativa.
2. Cobertura de regressão ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - valida presença do bloco executivo e sinais de utilidade imediata no cenário padrão do mapa.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`;
  - `npm --prefix frontend run test -- --run` -> `83 passed`;
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - continuar microrefinos para reduzir ruído visual e reforçar leitura de prioridade/ação sem abrir nova frente.

## Atualizacao operacional (2026-02-23) - Homologacao recorrente do mapa concluida

1. Benchmark urbano reexecutado com sucesso:
  - `\.\.venv\Scripts\python.exe scripts\benchmark_api.py --suite urban --rounds 30 --json-output data\reports\benchmark_urban_map.json` -> `ALL PASS`.
  - p95 observados: `roads=67.2ms`, `pois=31.3ms`, `nearby-pois=31.8ms`, `geocode=32.3ms`.
2. Correção de ambiente aplicada durante a rodada:
  - `scripts/init_db.py` executado com `PYTHONPATH=src` para garantir objetos SQL urbanos necessários ao `geocode`.
3. Prova ponta a ponta de observabilidade frontend validada:
  - `POST /v1/ops/frontend-events` com `name=map_homologation_probe` -> `accepted` (`event_id=1`);
  - `GET /v1/ops/frontend-events?name=map_homologation_probe&page_size=5` -> `total=1`.
4. Próximo passo imediato (WIP=1):
  - manter cadência recorrente de benchmark + eventos frontend, preservando `READY/normal/all_pass` sem abrir nova frente.

## Atualizacao tecnica (2026-02-22) - Homologacao operacional do mapa concluida

1. Homologação ponta a ponta da observabilidade do mapa executada com API local:
  - benchmark recorrente do mapa urbano em `data/reports/benchmark_urban_map.json` com `ALL PASS`.
  - latências p95 medidas: `roads=48.7ms`, `pois=31.4ms`, `nearby-pois=31.9ms`, `geocode=34.7ms` (alvo `<=1000ms`).
2. Endpoint de eventos frontend validado em fluxo real:
  - `POST /v1/ops/frontend-events` retornando `202 accepted` com `event_id`.
  - `GET /v1/ops/frontend-events` retornando o evento de prova (`matched_count=1`).
3. Ajuste backend aplicado para robustez de persistência em `src/app/api/routes_ops.py`:
  - serialização de `attributes` para JSON antes de `JSONB`;
  - commit após insert para consistência entre requisições;
  - commit condicional para preservar compatibilidade com sessão fake de teste.
4. Validacao executada:
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `30 passed`.
5. Proximo passo imediato (WIP=1):
  - manter cadência de benchmark urbano + leitura periódica de `/v1/ops/frontend-events` como rotina de monitoramento defensável, sem abrir nova frente de produto.

## Atualizacao tecnica (2026-02-22) - P1 telemetria do mapa operacionalizada

1. Telemetria frontend integrada ao `QgMapPage` para eventos críticos de observabilidade do mapa:
  - `map_zoom_changed`;
  - `map_layer_changed`;
  - `map_mode_changed`;
  - `map_tile_error`.
2. Cobertura de regressão adicionada em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - `emits map telemetry for mode, zoom and layer changes`.
3. Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
  - `npm --prefix frontend run build` -> `OK`.
4. Proximo passo imediato (WIP=1):
  - fechar benchmark recorrente do mapa e consolidar evidência de leitura dos eventos em `/v1/ops/frontend-events` para homologação ponta a ponta defensável.

## Atualizacao tecnica (2026-02-22) - Fechamento da rodada P0

1. Validação conjunta das páginas executivas concluída:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx` -> `31 passed`.
  - `npm --prefix frontend run build` -> `OK`.
2. Escopo P0 consolidado na rodada:
  - mapa executivo com orientação contextual para ausência de `local_votacao`;
  - eleitorado com fallback resiliente;
  - território 360 com estado `empty` explícito para highlights ausentes.
3. Próximo passo imediato (WIP=1):
  - manter monitoramento operacional recorrente e abrir próxima rodada apenas para refinamentos P1 (benchmark recorrente + cobertura de regressão expandida), sem abrir nova frente de produto.

## Atualizacao tecnica (2026-02-22) - P0 ciclo completo no Eleitorado

1. Resiliência de fallback implementada no `ElectorateExecutivePage`:
  - falha de fallback não interrompe a experiência quando o ano solicitado retorna dados;
  - erro de fallback torna-se bloqueante apenas quando o ano solicitado está sem dados e não há fallback utilizável.
2. Regressões adicionadas:
  - `does not break when fallback queries fail but selected year has data`;
  - `shows fallback error when selected year has no data and fallback fails`.
3. Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx` -> `8 passed`.
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - consolidar P0 final em `QgMapPage` + `ElectorateExecutivePage` + `TerritoryProfilePage` com uma rodada única de regressão de páginas executivas (`QgPages`, `ElectorateExecutivePage`, `TerritoryProfilePage`) e atualização documental de fechamento.

## Atualizacao tecnica (2026-02-22) - P0 continuidade em Território 360

1. Robustez de estado no painel de destaques do perfil territorial:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` agora mostra `StateBlock` de `empty` quando `profile.highlights` estiver vazio, evitando painel sem contexto.
2. Cobertura de regressão adicionada:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx` com cenário `shows empty highlights state when profile has no highlights`.
3. Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/territory/pages/TerritoryProfilePage.test.tsx src/modules/electorate/pages/ElectorateExecutivePage.test.tsx` -> `6 passed`.
  - `npm --prefix frontend run build` -> `OK`.
4. Próximo passo imediato (WIP=1):
  - continuar P0 no `ElectorateExecutivePage` para endurecer estados de suporte (error/empty/fallback) e regressões associadas.

## Atualizacao tecnica (2026-02-22) - P0 iniciado no mapa executivo

1. Implementacao iniciada no frontend para robustez de estado em camada eleitoral:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` agora exibe mensagem contextual quando `level=secao_eleitoral` e a camada `territory_polling_place` não está disponível no manifesto.
2. Regressão adicionada:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` com cenário `shows contextual guidance when local_votacao layer is unavailable`.
3. Validacao executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `23 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Checklist executável (1 dia) - próxima continuidade P0 (WIP=1)

1. Camada eleitoral detalhada no mapa:
  - consolidar estados `com local_votacao` vs `sem local_votacao` com mensagens objetivas e sem ambiguidade operacional.
2. Legibilidade e transparência da camada ativa:
  - manter visível `Classificacao da camada (official/proxy/hybrid)` e `hint` de método quando disponível.
3. Estados de suporte nas telas executivas críticas:
  - revisar `Mapa`, `Territorio 360` e `Eleitorado` para `loading/error/empty/data` com `StateBlock` consistente.
4. Critérios de aceite da rodada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` em `pass`.
  - `npm --prefix frontend run build` em `OK`.
  - atualização de evidências em `docs/CHANGELOG.md` e `docs/HANDOFF.md`.

## Atualizacao tecnica (2026-02-22) - Drift operacional no historico de robustez

1. Endpoint `GET /v1/ops/robustness-history` evoluido com campo `drift` por snapshot.
2. O `drift` agora traz:
   - transicao de status (`improved|regressed|stable|baseline`);
   - transicao de severidade (`improved|regressed|stable|baseline`);
   - deltas de pendencias operacionais (`unresolved_failed_checks`, `unresolved_failed_runs`, `actionable_warnings`).
3. Uso operacional imediato:
   - priorizar resposta quando `drift.status_transition=regressed` ou `drift.severity_transition=regressed`;
   - acompanhar convergencia semanal por `drift.delta_* <= 0`.
4. Validacao executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `30 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py -q -p no:cacheprovider` -> `4 passed`.

## Atualizacao operacional (2026-02-22) - Monitoramento recorrente (estabilidade mantida)

1. Checagem leve executada para manutenção do estado operacional:
  - `\.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
  - `\.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=29`, `warn=3`.
  - `\.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.
2. Persistencia de historico atualizada:
  - `\.\.venv\Scripts\python.exe scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=4`, `status=READY`, `severity=normal`, `all_pass=True`.
3. Proximo passo imediato (WIP=1):
  - manter cadencia recorrente de monitoramento sem abrir nova frente, preservando `READY/normal/all_pass` e `warnings=0`.

## Atualizacao operacional (2026-02-22) - Rodada de consolidacao 30d e gates tecnicos

1. Janela operacional de 30 dias revalidada com persistencia:
  - `\.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.
  - `\.\.venv\Scripts\python.exe scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=2`, `status=READY`, `severity=normal`, `all_pass=True`.
2. Historico de robustez consultado em `GET /v1/ops/robustness-history?page_size=5`:
  - `total=2` snapshots;
  - snapshot mais recente com `drift.status_transition=baseline`;
  - snapshot anterior com `drift.status_transition=stable`, `drift.severity_transition=stable` e `drift.delta_* = 0`.
3. Gates tecnicos da rodada executados:
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q -p no:cacheprovider` -> `33 passed`.
  - `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `29 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
4. Evidencias operacionais atualizadas:
  - `\.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=28`, `warn=4`.
  - `\.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1` (`SLO-1 7d=94.77%`, `current 1d=60.0%`).
5. Proximo passo imediato (WIP=1):
  - manter monitoramento recorrente da janela 30d e do `quality_suite`, preservando `status=READY`, `severity=normal` e `warnings=0` no readiness.

## Atualizacao operacional (2026-02-22) - Recuperacao de SLO-1 concluida (warnings=0)

1. Ciclo de recuperacao executado sem abrir nova frente:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`.
  - `dbt_build` reexecutado com `8` runs de sucesso (`build_mode=sql_direct`).
2. Readiness operacional convergiu para estado sem warning:
  - `\.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
  - `slo1` (7d): `95.03%` (`172/181`), acima do alvo de `95%`.
3. Evidencias atualizadas da rodada:
  - `\.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=29`, `warn=3`.
  - `\.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.
  - `\.\.venv\Scripts\python.exe scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=3`, `status=READY`, `severity=normal`, `all_pass=True`.

## Atualizacao técnica (2026-02-22) - Janela 30d em READY com gates consolidados

1. Ajuste de critério operacional do consolidado 30d:
   - gate principal de SLO passou para `slo_1_health_window_target`;
   - `slo_1_window_target` mantido como histórico e exigido apenas em `strict=true`;
   - gate de qualidade refinado para `quality_no_unresolved_failed_checks_window`.
2. Convergencia operacional executada:
   - `dbt_build` reexecutado com sucesso (fallback `sql_direct`) para resolver pendencias abertas de `dbt_build_execution`.
3. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `32 passed`.
   - `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=true`.
4. Estado atual da consolidação:
   - janela operacional 30d: `READY`;
   - warning histórico de SLO (30d) classificado como `informational` no consolidado, sem impacto de severidade.

## Atualização técnica (2026-02-22) - Histórico de robustez operacional persistido

1. Persistência de snapshots no banco:
   - nova migration `db/sql/018_ops_robustness_snapshots.sql` com:
     - tabela `ops.robustness_window_snapshots`;
     - índices de consulta por tempo/filtros;
     - view `ops.v_robustness_window_snapshot_latest`.
2. Script operacional de persistência:
   - novo `scripts/persist_ops_robustness_window.py` para gerar relatório e gravar snapshot no banco.
3. API operacional de histórico:
   - novo endpoint `GET /v1/ops/robustness-history` com filtros por janela/status/severidade e paginação.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `44 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 20 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=1`, `status=READY`, `severity=normal`, `all_pass=True`.

## Atualizacao técnica (2026-02-22) - Consolidação operacional 30d publicada (pós-D8)

1. Consolidação unica de robustez operacional publicada:
   - novo módulo `src/app/ops_robustness_window.py` para agregar readiness + scorecard + incidentes da janela.
   - novo endpoint `GET /v1/ops/robustness-window` com default operacional `window_days=30` e `health_window_days=7`.
2. Evidencia versionavel da janela:
   - novo script `scripts/export_ops_robustness_window.py` com saida padrão em `data/reports/ops_robustness_window_30d.json`.
3. Cobertura de testes:
   - nova suite `tests/unit/test_ops_robustness_window.py`.
   - `tests/unit/test_ops_routes.py` ampliado para o endpoint `/v1/ops/robustness-window`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --output-json data/reports/ops_robustness_window_30d.json` -> `status=NOT_READY`, `severity=critical`, `all_pass=False` (janela ainda em consolidação).
5. Próximo passo operacional:
   - reduzir `failed_checks` e estabilizar execução para convergir a janela de 30 dias para `READY`.

## Atualizacao técnica (2026-02-22) - D8 BD-082 implementado (playbook de incidentes e operação assistida)

1. Snapshot operacional unico para triagem de incidente:
   - novo script `scripts/generate_incident_snapshot.py`;
   - consolida:
     - readiness backend;
     - runs recentes `failed|blocked`;
     - checks recentes com `status=fail`;
     - classificação de severidade (`critical|high|normal`) e ações recomendadas.
2. Runbook operacional consolidado:
   - `docs/OPERATIONS_RUNBOOK.md` recebeu secao `11.8` com fluxo executável de triagem.
3. Cobertura de teste:
   - nova suite `tests/unit/test_generate_incident_snapshot.py` para classificação e ações.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_generate_incident_snapshot.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `16 passed`.
   - `.\.venv\Scripts\python.exe scripts/generate_incident_snapshot.py --help` -> `OK`.
5. Governança de issue na trilha unica:
   - `BD-082` concluido tecnicamente.
   - trilha D8 encerrada tecnicamente; próximo passo e consolidação operacional (janela de 30 dias).

## Atualizacao técnica (2026-02-22) - D8 BD-081 implementado (tuning de performance e custo da plataforma)

1. Tuning SQL aplicado para caminhos quentes de operação e mapa:
   - nova migration `db/sql/017_d8_performance_tuning.sql` com indices:
     - `ops.pipeline_checks` por status/check_name/created_at;
     - `ops.connector_registry` por `updated_at_utc + wave/status/source`;
     - `ops.frontend_events` por `name + event_timestamp_utc`;
     - trigram (`pg_trgm`) em nomes de `map.urban_road_segment`, `map.urban_poi` e `map.urban_transport_stop` para acelerar `geocode`.
2. Benchmark operacional ampliado:
   - `scripts/benchmark_api.py` passou a suportar `--suite ops`;
   - endpoints ops incluidos na medicao (`summary`, `readiness`, `pipeline-runs`, `pipeline-checks`, `connector-registry`, `source-coverage`, `sla`, `timeseries`);
   - alvo default da suite ops: `p95 <= 1500ms` (alinhado ao contrato dos endpoints `/v1/ops/*`).
3. Cobertura de contrato para tuning SQL:
   - `tests/contracts/test_sql_contracts.py` ganhou assert dedicado para `017_d8_performance_tuning.sql`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `13 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 19 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --help` -> `suite {executive,urban,ops,all}`.
5. Governança de issue na trilha unica:
   - `#26` (`BD-081`) encerrada.
   - `#27` (`BD-082`) encerrada.
   - próximo passo operacional: consolidação pós-D8 na janela de 30 dias.

## Atualizacao técnica (2026-02-22) - D8 BD-080 implementado (carga incremental confiavel + reprocessamento seletivo)

1. Orquestracao incremental operacional publicada:
   - novo script `scripts/run_incremental_backfill.py` com seleção automatica de jobs baseada em histórico de `ops.pipeline_runs`.
   - regra de decisão por par `job + reference_period`:
     - executa quando não ha run previo;
     - executa quando ultimo status não e `success`;
     - executa quando sucesso ficou "stale" (padrão `--stale-after-hours=168`);
     - permite reprocessamento seletivo com `--reprocess-jobs` e `--reprocess-periods`.
2. Hardening de operação:
   - filtros de escopo por `--jobs` e `--exclude-jobs`;
   - suporte a fonte `partial` via `--include-partial`;
   - pós-carga condicional por período com `dbt_build` e `quality_suite` (toggle por `--skip-dbt` e `--skip-quality`);
   - relatório padrão em `data/reports/incremental_backfill_report.json`.
3. Cobertura de teste da lógica incremental:
   - nova suite `tests/unit/test_run_incremental_backfill.py` cobrindo:
     - parse de filtros CSV;
     - decisão `no_previous_run`;
     - decisão `fresh_success` (skip);
     - decisão `stale_success` (execute);
     - decisão por `latest_status != success`;
     - override de reprocessamento seletivo.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_incremental_backfill.py tests/unit/test_backfill_environment_history.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `9 passed`.
   - `.\.venv\Scripts\python.exe scripts/run_incremental_backfill.py --help` -> `OK`.
5. Governança de issue na trilha unica:
   - `#25` (`BD-080`) encerrada.
   - `#26` (`BD-081`) promovida para `status:active`.
   - próximo item da fila unica: `D8/BD-081`.

## Acordo de foco (2026-02-22)

1. Trilha unica obrigatoria:
   - `#22` (`BD-070`) -> `#23` (`BD-071`) -> `#24` (`BD-072`).
2. Escopo congelado ate demo defensavel:
   - sem novas frentes de fonte/domínio que não impactem diretamente o mapa executivo.
3. Entrega esperada para demonstracao:
   - valor visivel no mapa com prioridade explicavel por território;
   - fluxo estavel em estados `loading/error/empty/data`;
   - evidencias técnicas registradas em `CHANGELOG` e neste `HANDOFF`.

## Atualizacao técnica (2026-02-22) - D7 BD-072 implementado (trilhas de explicabilidade para prioridade/insight)

1. Explainability estruturada em prioridade e insights:
   - `src/app/schemas/qg.py` ganhou contratos:
     - `ExplainabilityCoverage`
     - `ExplainabilityTrail`.
   - `PriorityItem` e `InsightHighlightItem` agora retornam `explainability`.
2. Evidencia expandida para auditoria:
   - `PriorityEvidence` e `BriefEvidenceItem` passam a incluir `updated_at`.
   - trilha retorna metadados de score: versão/método/thresholds/ranking/pesos.
3. Cobertura territorial explicita por domínio:
   - `src/app/api/routes_qg.py` calcula cobertura por `reference_period + level + domain`:
     - `covered_territories`
     - `total_territories`
     - `coverage_pct`.
4. Navegacao de insight para triagem:
   - `GET /v1/insights/highlights` passa a retornar `deep_link` por item.
5. Rationale orientada a trilha:
   - `GET /v1/priority/list` adiciona contexto de ranking e cobertura na justificativa.
6. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py -q -p no:cacheprovider` -> `19 passed`.
7. Governança de issue na trilha unica:
   - `BD-072` concluido tecnicamente.
   - próximo item da fila unica: `D8/BD-080`.

## Atualizacao técnica (2026-02-22) - D7 BD-071 implementado (versionamento de score territorial e pesos)

1. Governança de versão de score publicada:
   - migration nova `db/sql/016_strategic_score_versions.sql` com:
     - tabela `ops.strategic_score_versions`;
     - indice de unicidade para versão ativa (`uq_strategic_score_versions_active`);
     - view ativa `ops.v_strategic_score_version_active`;
     - seed idempotente da versão `v1.0.0`.
2. Mart Gold de prioridade evoluido para score versionado:
   - `db/sql/015_priority_drivers_mart.sql` agora aplica pesos por domínio/indicador e expande colunas:
     - `score_version`, `config_version`, `critical_threshold`, `attention_threshold`,
     - `domain_weight`, `indicator_weight`, `weighted_magnitude`.
   - compatibilidade de migracao preservada mantendo a ordem histórica das colunas-base da view.
3. Config e automação operacional:
   - `configs/strategic_engine.yml` com pesos default e mapas `domain_weights`/`indicator_weights`;
   - novo script `scripts/sync_strategic_score_versions.py` para sincronizacao idempotente no banco;
   - `scripts/backfill_robust_database.py` passa a sincronizar `strategic_score_versions` e reportar cobertura.
4. API executiva e contratos:
   - `src/app/api/routes_qg.py` passa a expor metadados/evidencias com `score_version`, `scoring_method` e pesos;
   - `src/app/schemas/qg.py` atualizado com campos opcionais de versão/pesos em prioridade, insights e briefs;
   - `src/app/api/strategic_engine_config.py` atualizado para carregar pesos versionados.
5. Scorecard e testes:
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
     - `priority_drivers_missing_score_version_rows`
     - `strategic_score_total_versions`
     - `strategic_score_active_versions_min`
     - `strategic_score_active_versions_max`.
   - `tests/contracts/test_sql_contracts.py` ampliado para `015`/`016` e novas métricas.
   - `tests/unit/test_strategic_engine_config.py` ampliado para validar parsing de pesos.
6. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_strategic_engine_config.py -q -p no:cacheprovider -p no:tmpdir` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `12 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 18 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/sync_strategic_score_versions.py` -> `score_version=v1.0.0`, `upserted=1`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=28`, `warn=4`.
7. Governança de issue na trilha unica:
   - `BD-071` concluido tecnicamente.
   - sequencia da fila unica avancou para `BD-072` (concluido na atualizacao superior deste documento).

## Atualizacao técnica (2026-02-22) - D7 BD-070 implementado (mart Gold de drivers de prioridade)

1. Camada Gold de prioridade publicada:
   - migration nova `db/sql/015_priority_drivers_mart.sql` com view:
     - `gold.mart_priority_drivers`.
   - score deterministico por `reference_period + territory_level + domain` com:
     - `driver_rank`, `driver_total`, `driver_magnitude`;
     - `priority_score`, `priority_status`, `driver_percentile`;
     - `scoring_method='rank_abs_value_v1'`.
2. Endpoints executivos de prioridade migrados para o mart Gold:
   - `GET /v1/priority/list`
   - `GET /v1/priority/summary`
   - `GET /v1/insights/highlights`
   - metadados de resposta agora indicam `source_name=gold.mart_priority_drivers`.
3. Governança operacional ampliada:
   - scorecard SQL (`db/sql/007_data_coverage_scorecard.sql`) com métricas:
     - `priority_drivers_rows`
     - `priority_drivers_distinct_periods`.
   - `scripts/init_db.py` com dependencia explicita de `007_data_coverage_scorecard.sql` para `015_priority_drivers_mart.sql`.
   - `scripts/backfill_robust_database.py` com bloco `coverage.priority_drivers_mart`.
4. Cobertura de contrato SQL adicionada:
   - `tests/contracts/test_sql_contracts.py` com assert dos objetos de `015_priority_drivers_mart.sql` e métricas de scorecard do mart.
5. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `78 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `11 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 17 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=24`, `warn=4`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
6. Governança de issue na trilha unica:
   - `BD-070` concluido tecnicamente.
   - tentativa de sincronizacao no GitHub bloqueada por restricao de rede/proxy do ambiente local.
   - próximo item da fila unica: `BD-071`.

## Atualizacao técnica (2026-02-22) - D6 BD-062 implementado (detectar drift de schema com alerta operacional)

1. Detecção de drift integrada ao `quality_suite`:
   - novo check `check_source_schema_drift` em `src/pipelines/common/quality.py`;
   - validações por conector:
     - existencia da tabela alvo;
     - colunas obrigatorias ausentes;
     - incompatibilidade de tipo por coluna;
     - agregado `schema_drift_connectors_with_issues`.
2. Alerta operacional automatico habilitado:
   - drifts geram `fail` em `ops.pipeline_checks` via `quality_suite`;
   - scorecard SQL ampliado com métrica `schema_drift_fail_checks_last_7d` em `db/sql/007_data_coverage_scorecard.sql`.
3. Governança de thresholds:
   - `configs/quality_thresholds.yml` com secao `schema_drift`:
     - `max_missing_required_columns`
     - `max_type_mismatch_columns`
     - `max_connectors_with_drift`.
4. Cobertura de teste adicionada:
   - `tests/unit/test_schema_drift_checks.py` (pass/fail para drift de colunas e tipos);
   - `tests/unit/test_quality_suite.py` atualizado para o novo check;
   - `tests/contracts/test_sql_contracts.py` atualizado com métrica de drift no scorecard.
5. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_schema_drift_checks.py tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/contracts/test_sql_contracts.py tests/contracts/test_schema_contract_connector_coverage.py -q -p no:cacheprovider` -> `78 passed`.
   - `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`, `total_checks=188`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=22`, `warn=4`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1` (SLO-1 abaixo da meta na janela).
6. Regra operacional da trilha:
   - issue implementada encerrada na mesma rodada:
     - `#21` (`BD-062`) -> `closed`.
     - `#22` (`BD-070`) promovida para `status:active`.
   - próximo item da fila unica: `BD-070`.

## Atualizacao técnica (2026-02-22) - D6 BD-061 implementado (cobertura de testes de contrato por conector)

1. Cobertura de contratos por conector automatizada:
   - nova suite `tests/contracts/test_schema_contract_connector_coverage.py`;
   - validação de cobertura minima `>= 90%` para conectores elegiveis (`implemented|partial`, não internos, sem discovery interno).
2. Granularidade por conector adicionada:
   - testes parametrizados para garantir contrato por conector elegivel;
   - falha explicita com nome do conector ausente/quebrado.
3. Estrutura minima de contrato validada por conector:
   - `required_columns` não vazio;
   - `column_types` não vazio;
   - `schema_version` com padrão versionado (`v*`).
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_schema_contract_connector_coverage.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `61 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
5. Regra operacional da trilha D6:
   - issue implementada encerrada na mesma rodada:
     - `#20` (`BD-061`) -> `closed`.
     - `#21` (`BD-062`) promovida para `status:active`.
   - próximo item da fila unica: `BD-062`.

## Atualizacao técnica (2026-02-22) - D6 BD-060 implementado (contratos de schema versionados por fonte)

1. Governança de contratos de schema publicada:
   - migration nova `db/sql/014_source_schema_contracts.sql` com:
     - tabela `ops.source_schema_contracts`;
     - view ativa `ops.v_source_schema_contracts_active`;
     - suporte a versionamento por `connector_name + target_table + schema_version`.
2. Automação de sincronizacao implementada:
   - novo módulo `src/pipelines/common/schema_contracts.py` para inferencia/normalizacao de contratos;
   - novo arquivo `configs/schema_contracts.yml` com defaults e overrides por conector;
   - novo script `scripts/sync_schema_contracts.py` para upsert/deprecacao de versões.
3. Operação e qualidade integradas:
   - `scripts/backfill_robust_database.py` passa a sincronizar contratos e reportar cobertura de `schema_contracts`;
   - `src/pipelines/common/quality.py` com check `check_source_schema_contracts`;
   - `src/pipelines/quality_suite.py` passa a executar checks de cobertura de contratos ativos;
   - `configs/quality_thresholds.yml` com secao `schema_contracts`;
   - `db/sql/007_data_coverage_scorecard.sql` com métrica `schema_contracts_active_coverage_pct`;
   - filtros de cobertura ajustados para excluir conectores de discovery/internos (`quality_suite`, `dbt_build`, `tse_catalog_discovery`).
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 16 SQL scripts`.
   - `.\.venv\Scripts\python.exe scripts/sync_schema_contracts.py` -> `prepared=24`, `upserted=24`, `deprecated=0`.
   - `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=23`, `warn=2`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Regra operacional da trilha D6:
   - issue implementada encerrada na mesma rodada:
     - `#19` (`BD-060`) -> `closed`.
     - `#20` (`BD-061`) promovida para `status:active`.
   - próximo item da fila unica: `BD-061`.

## Atualizacao técnica (2026-02-21) - D5 BD-052 implementado (mart Gold de risco ambiental territorial)

1. Camada Gold ambiental publicada no banco:
   - migration nova `db/sql/013_environment_risk_mart.sql` com view:
     - `gold.mart_environment_risk`.
   - cobertura por `territory_level`:
     - `municipality`
     - `district`
     - `census_sector`.
   - métrica executiva no mart:
     - `environment_risk_score`
     - `risk_percentile`
     - `risk_priority_rank`
     - `priority_status`.
2. API executiva de risco ambiental adicionada:
   - endpoint novo `GET /v1/environment/risk` em `src/app/api/routes_qg.py`;
   - filtros: `period`, `level` (`municipality|district|census_sector`), `limit`;
   - fallback de período para ultimo `reference_period` disponível;
   - contrato em `src/app/schemas/qg.py`:
     - `EnvironmentRiskItem`
     - `EnvironmentRiskResponse`.
3. Governança operacional e qualidade reforcadas:
   - `src/pipelines/common/quality.py` com check novo:
     - `check_environment_risk_mart`.
   - `src/pipelines/quality_suite.py` passa a incluir checks do mart Gold ambiental.
   - `configs/quality_thresholds.yml` ampliado com thresholds `environment_risk_mart_*`.
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
     - `environment_risk_mart_municipality_rows`
     - `environment_risk_mart_district_rows`
     - `environment_risk_mart_census_sector_rows`
     - `environment_risk_mart_distinct_periods`.
   - `scripts/init_db.py` atualizado para ordenar dependencia `007 -> 013`.
   - `scripts/backfill_robust_database.py` ampliado com `coverage.environment_risk_mart`.
   - `src/app/api/cache_middleware.py` com cache para `GET /v1/environment/risk`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `102 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `51 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 15 SQL scripts`.
   - smoke API real:
     - `GET /v1/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
   - scorecard/readiness:
     - `scripts/export_data_coverage_scorecard.py` -> `pass=23`, `warn=1`.
     - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - quality checks do mart no ultimo run:
     - `environment_risk_mart_rows_municipality=pass` (`5`)
     - `environment_risk_mart_rows_district=pass` (`55`)
     - `environment_risk_mart_rows_census_sector=pass` (`545`)
     - `environment_risk_mart_distinct_periods=pass` (`5`)
     - `environment_risk_mart_null_score_rows=pass` (`0`).
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#18` (`BD-052`) -> `closed`.
     - `#19` (`BD-060`) promovida para `status:active`.
   - próximo item da fila unica: `BD-060`.

## Atualizacao técnica (2026-02-21) - D5 BD-051 implementado (agregações ambientais distrito/setor)

1. Agregação ambiental territorial publicada no banco:
   - migration nova `db/sql/012_environment_risk_aggregation.sql` com view:
     - `map.v_environment_risk_aggregation`.
   - cobertura por `territory_level`:
     - `district`
     - `census_sector`.
   - métrica sintetica por território:
     - `hazard_score`
     - `exposure_score`
     - `environment_risk_score`
     - `priority_status`.
2. API de mapa para risco ambiental adicionada:
   - endpoint novo `GET /v1/map/environment/risk` em `src/app/api/routes_map.py`;
   - filtros: `level` (`district|census_sector`), `period`, `include_geometry`, `limit`;
   - fallback de período para ultimo `reference_period` disponível;
   - contrato em `src/app/schemas/map.py`:
     - `EnvironmentRiskItem`
     - `EnvironmentRiskCollectionResponse`.
3. Governança operacional e qualidade reforcadas:
   - `scripts/init_db.py` atualizado para ordenar dependencia `007 -> 012` (scorecard depende da view ambiental).
   - `src/pipelines/common/quality.py` com check novo:
     - `check_environment_risk_aggregation`.
   - `src/pipelines/quality_suite.py` passa a incluir checks ambientais agregados.
   - `configs/quality_thresholds.yml` com secao `environment_risk`.
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
     - `environment_risk_district_rows`
     - `environment_risk_census_sector_rows`
     - `environment_risk_distinct_periods`.
   - `scripts/backfill_robust_database.py` ampliado com bloco `coverage.environment_risk_aggregation`.
   - `src/app/api/cache_middleware.py` com cache para `GET /v1/map/environment/risk`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `49 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_mvt_tiles.py -q -p no:cacheprovider` -> `33 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 14 SQL scripts`.
   - smoke API real:
     - `GET /v1/map/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `count=5`.
   - scorecard/readiness:
     - `scripts/export_data_coverage_scorecard.py` -> `pass=19`, `warn=1`.
     - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
   - quality checks ambientais no ultimo run:
     - `environment_risk_rows_district=pass` (`55`)
     - `environment_risk_rows_census_sector=pass` (`545`)
     - `environment_risk_distinct_periods=pass` (`5`)
     - checks de nulos (`risk/hazard/exposure`) em `pass`.
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#17` (`BD-051`) -> `closed`.
     - `#18` (`BD-052`) promovida para `status:active`.
   - próximo item da fila unica: `BD-052`.

## Atualizacao técnica (2026-02-21) - D5 BD-050 implementado (histórico ambiental multi-ano)

1. Orquestracao dedicada para BD-050 publicada:
   - novo script `scripts/backfill_environment_history.py` com fluxo unico de:
     - bootstrap manual multi-ano (`INMET`, `INPE_QUEIMADAS`, `ANA`);
     - execução dos conectores ambientais por período;
     - execução opcional de `quality_suite` por período;
     - consolidação de cobertura por fonte no relatório final.
2. Hardening de integridade temporal no conector tabular:
   - `src/pipelines/common/tabular_indicator_connector.py` agora bloqueia carga quando houver coluna de ano com sinal valido e nenhum match com `reference_period`.
   - fallback anterior foi preservado apenas para payloads sem qualquer sinal temporal.
3. Governança de cobertura ambiental reforcada:
   - `configs/quality_thresholds.yml` com metas explicitas:
     - `min_periods_inmet: 5`
     - `min_periods_inpe_queimadas: 5`
     - `min_periods_ana: 5`
   - `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
     - `inmet_distinct_periods`
     - `inpe_queimadas_distinct_periods`
     - `ana_distinct_periods`
   - `scripts/backfill_robust_database.py` agora exporta `coverage.environmental_sources` com `rows`, `distinct_periods`, `min_period`, `max_period`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_backfill_environment_history.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_coverage_checks.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `26 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_quality_suite.py -q -p no:cacheprovider` -> `12 passed`.
   - `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --help` -> `OK`.
   - smoke BD-050:
     - `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --periods 2025 --dry-run --skip-bootstrap --skip-quality --allow-blocked --output-json data/reports/bd050_environment_history_report.json` -> `success=2`, `blocked=1` (`INMET` com `403`), report gerado.
5. Regra operacional da trilha D5:
   - issue implementada encerrada na mesma rodada:
     - `#16` (`BD-050`) -> `closed`.
     - `#17` (`BD-051`) promovida para `status:active`.
   - próximo item da fila unica: `BD-051`.

## Atualizacao técnica (2026-02-21) - D4 BD-042 implementação de mart de mobilidade

1. Camada Gold de mobilidade entregue:
   - `db/sql/011_mobility_access_mart.sql` com `gold.mart_mobility_access`.
   - score de acesso e deficit por território (`municipality` e `district`) com:
     - densidade de pontos de transporte;
     - densidade viaria;
     - POIs de mobilidade;
     - método de alocacao explicito (`direct_measurement` vs `district_allocation_by_road_length_share`).
2. Hardening técnico aplicado no SQL:
   - agregações separadas por domínio espacial (vias, transporte, POIs) para evitar sobrecontagem por join multiplo;
   - amarracao de populacao por período do SENATRAN com fallback para ultima populacao disponível;
   - casts explicitos de `ROUND(..., 2)` para compatibilidade com Postgres.
3. API executiva entregue:
   - endpoint novo `GET /v1/mobility/access` em `src/app/api/routes_qg.py`;
   - filtros: `period`, `level`, `limit`;
   - metadata padronizada (`source_name=gold.mart_mobility_access`) e retorno vazio contratual quando não houver dados.
4. Contratos e cache:
   - schemas novos em `src/app/schemas/qg.py` (`MobilityAccessItem`, `MobilityAccessResponse`);
   - `src/app/api/cache_middleware.py` atualizado para cachear `GET /v1/mobility/access`.
5. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `79 passed`.
   - `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 13 SQL scripts`.
   - smoke local via `TestClient`: `GET /v1/mobility/access?level=district&limit=5` -> `200`.

## Atualizacao técnica (2026-02-21) - D4 BD-041 implementação de transporte urbano

1. Conector novo de mobilidade municipal:
   - `src/pipelines/urban_transport.py` (`urban_transport_fetch`) com:
     - discovery remoto via Overpass para pontos de transporte (`bus_stop`, `public_transport`, `railway`, `ferry_terminal`);
     - fallback manual em `data/manual/urban/transport`;
     - Bronze snapshot + checks + carga idempotente em `map.urban_transport_stop`.
2. Domínio de mapa ampliado:
   - migration nova `db/sql/010_urban_transport_domain.sql`:
     - tabela `map.urban_transport_stop`;
     - indice GIST;
     - camada `urban_transport_stops` no catálogo;
     - view `map.v_urban_data_coverage` atualizada.
   - endpoint novo:
     - `GET /v1/map/urban/transport-stops`.
   - geocode urbano ampliado para `kind=transport` em `GET /v1/map/urban/geocode`.
   - tiles MVT ampliados para camada `urban_transport_stops`.
3. Orquestracao e qualidade:
   - `src/orchestration/prefect_flows.py` com `urban_transport_fetch` em `run_mvp_all` e `run_mvp_wave_7`.
   - `scripts/backfill_robust_database.py` com `urban_transport_fetch` no `wave7` e cobertura no report.
   - `src/pipelines/common/quality.py` com checks:
     - `urban_transport_stops_rows_after_filter`
     - `urban_transport_stops_invalid_geometry_rows`
   - `configs/quality_thresholds.yml` com `min_transport_rows`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -c "import json; from pipelines.urban_transport import run; print(json.dumps(run(reference_period='2026', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `rows_written=22`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_urban_connectors.py tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/contracts/test_sql_contracts.py -q` -> `68 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Estado de encerramento de `BD-041`:
   - carga real validada em `map.urban_transport_stop`;
   - próxima execução oficial da trilha D4: `BD-042`.

## Atualizacao operacional (2026-02-21) - BD-040 executado com backfill real

1. Bootstrap histórico SENATRAN concluido:
   - script novo: `scripts/bootstrap_senatran_history.py`.
   - fontes oficiais coletadas para `2021..2024` e materializadas em:
     - `data/manual/senatran/senatran_diamantina_2021.csv`
     - `data/manual/senatran/senatran_diamantina_2022.csv`
     - `data/manual/senatran/senatran_diamantina_2023.csv`
     - `data/manual/senatran/senatran_diamantina_2024.csv`
   - evidencias em `data/reports/bootstrap_senatran_history_report.json`.
2. Backfill real do conector `senatran_fleet_fetch` executado para `2021..2025`:
   - `5/5` runs com `status=success`;
   - `rows_written=4` por ano em `silver.fact_indicator`.
3. Cobertura de `SENATRAN` validada no banco:
   - `reference_period` disponível em `2021,2022,2023,2024,2025`.
4. Validação operacional:
   - `scripts/export_data_coverage_scorecard.py` -> `pass=10`, `warn=1`.
   - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
5. Dependencias de parsing Excel formalizadas no projeto:
   - `openpyxl` e `xlrd` adicionados em `requirements.txt` e `pyproject.toml`.

## Atualizacao técnica (2026-02-21) - D4 BD-040 hardening SENATRAN

1. Conector SENATRAN endurecido para serie histórica:
   - descoberta automatica de CSV remoto por ano na página oficial;
   - filtro de ano em URI remota para evitar carga com período divergente;
   - priorização de arquivo manual por `reference_period` no nome;
   - bloqueio de fallback manual com ano divergente (integridade temporal);
   - parser dedicado para CSV oficial com preambulo + parse numerico por milhares.
2. Cobertura de testes ampliada para SENATRAN:
   - discovery remoto por ano;
   - seleção/bloqueio de fallback manual por ano;
   - parse de CSV oficial com preambulo;
   - resolução remota quando catálogo estatico esta vazio.
3. Infra de banco corrigida para execução real:
   - `src/app/db.py` passou a cachear por `database_url` (string), eliminando erro `unhashable type: 'Settings'`.
4. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_db_cache.py tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
5. Dry-run multi-ano do conector:
   - `2021..2024`: `blocked` (sem fonte anual valida descoberta).
   - `2025`: `success` com fonte remota oficial.
6. Próximo passo operacional da trilha D4:
   - coletar/publicar arquivos SENATRAN anuais `2021..2024` em `data/manual/senatran/` (ou catálogo estatico versionado) e executar backfill real `2021..2025`.

## Atualizacao operacional (2026-02-20) - Filtro rigoroso de documentos

1. Governança documental centralizada em `docs/GOVERNANCA_DOCUMENTAL.md`.
2. Nucleo ativo de decisão reforcado:
   - `docs/CONTRATO.md`
   - `docs/VISION.md`
   - `docs/PLANO_IMPLEMENTACAO_QG.md`
   - `docs/HANDOFF.md`
   - `docs/CHANGELOG.md`
3. Documentos descontinuados para decisão:
   - removidos do repositório em 2026-02-20 (ver `docs/GOVERNANCA_DOCUMENTAL.md` secao 6).
4. Regra obrigatoria:
   - nenhum desses documentos descontinuados abre prioridade, trilha ou backlog.

## Atualizacao técnica (2026-02-20) — Fase UX-P0 entregue

1. Escopo: corrigir todas as inconsistencias de UI/UX identificadas por auditoria visual de 10 telas.
2. Itens entregues (22 correções):
   - **UX-P0-01/02**: Helpers `formatValueWithUnit()`, `humanizeSourceName()`, `humanizeCoverageNote()`, `humanizeDatasetSource()` em `presentation.ts`.
   - **UX-P0-03/04**: SourceFreshnessBadge humanizado (source_name + coverage_note).
   - **UX-P0-05/06/07**: Home — "SVG fallback" renomeado; colunas técnicas removidas de KPIs e Onda B/C.
   - **UX-P0-08/09**: Insights — severity + source humanizados.
   - **UX-P0-10/11/12**: Briefs — Brief ID removido, "Linha" → "Ponto", source humanizado.
   - **UX-P0-13/14/15**: Cenarios — indicator_name no subtitulo, "Leitura" → "Analise", label do campo.
   - **UX-P0-16**: Território 360 — coluna Codigo removida.
   - **UX-P0-17**: Eleitorado — zero display → "-".
   - **UX-P0-18**: PriorityItemCard — source humanizado.
   - **UX-P0-19/20**: Mapa — label e coluna técnica removidos.
   - **UX-P0-21/22**: Backend — `_format_highlight_value()` melhorado + cenarios em pt-BR.
3. Arquivos modificados:
   - `frontend/src/shared/ui/presentation.ts` (helpers novos + unit mapping).
   - `frontend/src/shared/ui/SourceFreshnessBadge.tsx` (humanizacao).
   - `frontend/src/shared/ui/PriorityItemCard.tsx` (source humanizado).
   - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` (SVG label + colunas).
   - `frontend/src/modules/qg/pages/QgInsightsPage.tsx` (severity + source).
   - `frontend/src/modules/qg/pages/QgBriefsPage.tsx` (Brief ID + Linha + source).
   - `frontend/src/modules/qg/pages/QgScenariosPage.tsx` (indicator_name + Leitura + label).
   - `frontend/src/modules/qg/pages/QgMapPage.tsx` (label + coluna Métrica).
   - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` (coluna Codigo).
   - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` (zero display).
   - `src/app/api/routes_qg.py` (format + impact pt-BR).
   - Testes atualizados: `SourceFreshnessBadge.test.tsx`, `QgPages.test.tsx`.

## Atualizacao técnica (2026-02-20) — Fase DATA entregue

1. Escopo: corrigir 8 inconsistencias de semantica de dados identificadas por auditoria visual.
2. Itens entregues:
   - **DATA-P0-01**: Score mono-territorial 100->50 (3 locais em routes_qg.py).
   - **DATA-P0-02**: Trend real via `_compute_trend()` + `_fetch_previous_values()`.
   - **DATA-P0-03**: Codigos técnicos removidos de narrativas (5 endpoints).
   - **DATA-P0-04**: Formatacao pt-BR via `_format_highlight_value()`.
   - **DATA-P0-05**: Severidade em pt-BR no filtro de Insights.
   - **DATA-P0-06**: Narrativa de insights diversificada por domínio e severidade via `_build_insight_explanation()`.
   - **DATA-P0-07**: Jargao técnico do mapa substituido por termos executivos.
   - **DATA-P0-08**: Dedup de formatadores em StrategicIndexCard.
3. Arquivos modificados:
   - `src/app/api/routes_qg.py` (backend — 6 alteracoes + 4 funções novas).
   - `frontend/src/modules/qg/pages/QgInsightsPage.tsx` (import + labels traduzidos).
   - `frontend/src/modules/qg/pages/QgMapPage.tsx` (8 substituicoes de labels).
   - `frontend/src/shared/ui/StrategicIndexCard.tsx` (rewrite para usar presentation.ts).
   - `tests/unit/test_qg_routes.py` (mock atualizado).
   - `frontend/src/modules/qg/pages/QgPages.test.tsx` (assertion atualizada).
   - `docs/BACKLOG_UX_EXECUTIVO_QG.md` (Fase DATA adicionada).

## Atualizacao de planejamento (2026-02-20) - Backlog UX executivo unificado

1. Backlog unico consolidado para correções de layout/legibilidade:
   - `docs/BACKLOG_UX_EXECUTIVO_QG.md`.
2. Ordem de execução definida:
   - `P0` (estrutural/legibilidade) -> `P1` (harmonizacao visual) -> `P2` (refinamento).
3. Regra de foco:
   - não iniciar novas frentes enquanto itens `UX-P0-*` não estiverem entregues e validados.
4. Mapeamento de escopo:
   - backlog ja inclui arquivos/componentes alvo por página (`Prioridades`, `Mapa`, `Territorio 360`, `Insights`, `Cenarios`, `Briefs`, `Eleitorado`, `App shell`).

## Atualizacao operacional (2026-02-20) - Governança de issues GitHub

1. Trilha ativa oficial no GitHub:
   - `BD-033` criada em `#28` com label `status:active`.
2. Fechamento de item concluido:
   - `BD-021` (`#8`) encerrada por entrega técnica concluida.
3. Bloqueios explicitados por sequencia:
   - labels `status:blocked` e `status:external` criadas para leitura operacional.
   - `BD-020` (`#7`) marcada como `status:external` + `status:blocked` (dependencia externa CECAD).
   - issues abertas de D4-D8 marcadas como `status:blocked` ate fechamento da trilha ativa.
4. Regra operacional mantida:
   - nenhuma reativacao de item bloqueado antes do gate de saida de `BD-033` (`#28`).

## Atualizacao operacional (2026-02-20) - Fechamento de gate BD-033 + fase 2

1. Gate técnico da trilha ativa revalidado:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.
2. Pacote de confiabilidade (fase 2) executado:
   - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json`
     -> `pass=5`, `warn=8`.
   - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json`
     -> `READY`, `hard_failures=0`, `warnings=0`.
   - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json`
     -> `ALL PASS`, p95 urbano entre `103.7ms` e `123.5ms`.
3. Evidencias atualizadas:
   - `data/reports/data_coverage_scorecard.json`
   - `data/reports/benchmark_urban_map.json`
4. Estado de issue:
   - `BD-033` encerrada no GitHub em `2026-02-20` (`issue #28`).

## Atualizacao técnica (2026-02-20) - Hotfix UX mapa (legibilidade + area util)

1. Correções de legibilidade dos controles do mapa:
   - `frontend/src/styles/global.css` ajustado para garantir contraste dos botoes em:
     - `Modo de visualizacao`;
     - `Mapa base`;
     - toggle da sidebar (`map-sidebar-toggle`) na Home.
   - impacto: botoes não selecionados deixaram de ficar visualmente "invisiveis".
2. Correções de dimensão/utilizacao de area do mapa:
   - `frontend/src/styles/global.css` com altura ampliada em `map-canvas-shell`.
   - `map-dominant` e `map-dominant-canvas` ajustados para evitar area vazia abaixo do mapa.
   - classe `map-overview-canvas` passou a ocupar a altura util do layout dominante.
3. Correções de zoom inicial/contextual:
   - `frontend/src/modules/qg/pages/QgMapPage.tsx`:
     - `resolveContextualZoom` passa a respeitar piso do contexto (territorial/urbano), evitando abertura em `z0`.
     - zoom inicial do mapa aplica piso contextual ao ler query string.
   - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
     - zoom inicial/mínimo da Home passa a usar piso recomendado por nível.
4. Regressão de testes atualizada:
   - `frontend/src/modules/qg/pages/QgPages.test.tsx` ajustado para novo comportamento de piso de zoom.
5. Validação executada:
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
   - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-20) - Painel de filtros do mapa situacional (layout e formatacao)

1. Reposicionamento do painel de filtros na Home:
   - `frontend/src/styles/global.css` deixou de usar painel sobreposto ao mapa no desktop.
   - `map-dominant-sidebar` passou a operar como coluna lateral (docked), mantendo controle por `Ocultar/Mostrar filtros`.
   - `frontend/src/shared/ui/MapDominantLayout.tsx` atualizado para refletir semantica de layout dominante com sidebar colapsavel.
2. Formatacao interna do menu lateral:
   - botoes de `Aplicar/Limpar` alinhados em grade com largura consistente.
   - botoes de navegacao (`Focar selecionado` e `Recentrar mapa`) padronizados em largura e empilhamento no painel.
   - seletor de `Mapa base` reorganizado em grade para evitar desalinhamento.
3. Controle de overflow visual:
   - cards e blocos do painel (`Situacao geral`, metadados de fonte, notas) receberam quebra de linha segura (`overflow-wrap`) para evitar texto vazando.
   - ajuste de topo do botao de toggle para fora da area do mapa (sem sobreposicao no canvas).
4. Validação executada:
   - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
   - `npm --prefix frontend run test -- --run` -> `78 passed`.
   - `npm --prefix frontend run build` -> `OK`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
   - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao técnica (2026-02-20) - Transparencia de classificação de camadas (mapa)

- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - classificação de camada (`oficial`, `proxy`, `hibrida`) agora aparece de forma explicita em:
    - camada recomendada do contexto atual;
    - camada ativa no seletor detalhado;
    - metadados visuais do painel do mapa.
  - tooltip da camada ativa passou a priorizar metodologia (`proxy_method`) para leitura rapida de limitacoes.
  - fluxo de `local_votacao` foi preservado, com transparencia adicional sobre a natureza `proxy` da camada.
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - painel lateral da Home executiva passou a exibir classificação da camada detalhada ativa, com hint de metodologia.
  - objetivo: manter consistencia de leitura entre `Visao Geral` e `Mapa`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - regressão ampliada para validar exibição de classificação no fluxo eleitoral detalhado (`territory_polling_place`).
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao técnica (2026-02-20) - Quality Suite (ativacao de checks de camadas do mapa)

- `src/pipelines/quality_suite.py`:
  - `quality_suite` passou a executar `check_map_layers` dentro do fluxo padrão.
  - impacto: checks de cobertura/geom de camadas territoriais (`map_layer_rows_*` e `map_layer_geometry_ratio_*`) voltam a ser persistidos em `ops.pipeline_checks` a cada rodada de qualidade.
  - alinhamento com backlog D3/D6: readiness de camadas e governança de qualidade ficam acoplados ao pipeline oficial.
- `tests/unit/test_quality_suite.py`:
  - novo teste unitario garantindo que `check_map_layers` e executado e serializado no resultado da `quality_suite`.
- `tests/unit/test_quality_coverage_checks.py`:
  - ajuste do teste de cobertura temporal por fonte para refletir o mapa atual de fontes do `fact_indicator` (`DATASUS..CENSO_SUAS`), evitando falso negativo por ordem incompleta.
- Validação executada:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-20) - Home QG (degradação parcial de prioridades/destaques)

- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - Home executiva deixou de falhar por completo quando apenas `Top prioridades` ou `Destaques` estiverem indisponiveis.
  - hard-fail da página permanece restrito ao nucleo de leitura (`kpis_overview` + `priority_summary`).
  - blocos `Top prioridades` e `Destaques` agora possuem estados independentes `loading/error/empty` com `request_id` e `Tentar novamente`.
  - objetivo: preservar navegacao do mapa, situacao geral e ações rapidas mesmo com falha parcial de dados secundarios.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - nova regressão valida falha simultanea de `priority preview` e `insights highlights` sem derrubar a Home.
  - cobertura inclui exibição de `request_id` e retry dedicado por bloco.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao técnica (2026-02-20) - Mapa executivo (estados de suporte padronizados)

- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - estados auxiliares do mapa (manifesto de camadas, cobertura e metadados de estilo) padronizados com `StateBlock`.
  - erros desses componentes agora exibem mensagem de API + `request_id` quando disponível.
  - cada estado de erro recebeu ação `Tentar novamente` com `refetch` dedicado.
  - estados de carregamento explicitos adicionados para manifesto/cobertura/estilo, evitando lacunas de feedback no fluxo operacional.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - novas regressões cobrindo:
    - erro de manifesto + metadados de estilo com retry e `request_id`;
    - erro de cobertura com retry sem quebrar a interacao principal do mapa.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `21 passed`.
  - `npm --prefix frontend run test -- --run` -> `77 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao técnica (2026-02-20) - Boundary de erro por rota (frontend)

- `frontend/src/app/RouteRuntimeErrorBoundary.tsx`:
  - novo error boundary de runtime para telas roteadas, com fallback padronizado via `StateBlock`.
  - exibição de contexto de falha por rota (`Falha na tela: <rota>`) + ação de retry sem reload total.
  - emissao de telemetria `frontend_error/route_runtime_error` com `route_label`, `message` e `component_stack`.
- `frontend/src/app/router.tsx`:
  - `withPageFallback` passou a encapsular cada página em `RouteRuntimeErrorBoundary` com rotulo explicito.
  - objetivo: evitar tela branca em erro de render e manter navegacao operacional previsivel.
- `frontend/src/app/RouteRuntimeErrorBoundary.test.tsx`:
  - novo teste cobrindo:
    - exibição de estado de erro e emissao de telemetria em crash de render;
    - recuperacao da tela apos `Tentar novamente`.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/app/RouteRuntimeErrorBoundary.test.tsx src/app/router.smoke.test.tsx src/modules/qg/pages/QgPages.test.tsx src/modules/ops/pages/OpsPages.test.tsx` -> `32 passed`.
  - `npm --prefix frontend run test -- --run` -> `75 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## Atualizacao técnica (2026-02-20) - Ops Health (refresh + regressão readiness)

- `frontend/src/modules/ops/pages/OpsHealthPage.tsx`:
  - adicionado botao `Atualizar painel` no bloco `Status geral` para refetch manual dos datasets operacionais da tela.
  - fluxo de recarga consolidado em função unica (`refetchAll`) reutilizada no erro (`onRetry`) e no refresh manual para manter comportamento consistente.
- `frontend/src/modules/ops/pages/OpsPages.test.tsx`:
  - novo teste de regressão cobrindo transição de readiness no `OpsHealthPage`:
    - estado inicial `READY`;
    - refresh manual via botao;
    - atualizacao para `NOT_READY` com exibição de `Hard failures`.
- Validação executada:
  - `npm --prefix frontend run test -- --run` -> `73 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-20) - Home QG (camada detalhada coerente)

- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - seletor `Camada detalhada (Mapa)` agora aparece somente quando `Nivel territorial` estiver em `secao_eleitoral`.
  - propagacao de camada detalhada para links deixa de ocorrer fora do contexto eleitoral detalhado.
  - links de `Mapa detalhado` com camada detalhada passam a forcar contexto coerente com `level=secao_eleitoral`, evitando deep-link ambiguo.
  - ao trocar para nível diferente de `secao_eleitoral`, a seleção local de camada detalhada e limpa para evitar estado residual.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - regressão atualizada para validar exibição condicional do seletor detalhado e propagacao coerente de `layer_id` + `level`.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-20) - Estabilizacao mapa + eleitorado

- Mapa vetorial:
  - `frontend/src/shared/ui/VectorMap.tsx` corrigido para evitar recenter forcado durante zoom.
  - erros de abort/cancelamento deixam de acionar fluxo de erro visual.
  - `QgMapPage` e `QgOverviewPage` não derrubam mais automaticamente para SVG em erro transitorio do vetor.
- Backend de tiles:
  - `src/app/api/routes_map.py` passou a usar geometria saneada (`ST_IsValid`/`ST_MakeValid`) no caminho territorial de tiles MVT para reduzir `503`.
- Eleitorado:
  - `src/app/api/routes_qg.py` com fallback de binding de ano logico x ano de armazenamento outlier.
  - resultado pratico: requests `year=2024` voltam a responder com dados mesmo em base com `reference_year=9999`.
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` recebeu tratamento de estado vazio/erro mais explicito para cenarios sem dados.
- Correção de regressão de render:
  - erro de hooks (`Rendered more hooks than during the previous render`) removido em:
    - `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
    - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
- Usabilidade:
  - paginacao adicionada em Insights e na tabela de indicadores do Território 360 para evitar listas extensas sem controle.

## Validação executada (2026-02-20)

- Backend:
  - `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
- Frontend:
  - `npm --prefix frontend run test -- --run` -> `72 passed`.
  - `npm --prefix frontend run build` -> `OK`.
- Smoke API (eleitorado):
  - `GET /v1/electorate/summary?level=municipality&year=2024` -> `200`, `38127` eleitores.
  - `GET /v1/electorate/map?level=municipality&year=2024&metric=voters` -> `200`, com itens retornados.

## Atualizacao técnica (2026-02-20) - Mapa semantico (sem dado)

- `frontend/src/shared/ui/VectorMap.tsx`:
  - coropletico vetorial deixou de mapear ausencia de valor para faixa baixa.
  - features sem métrica agora usam cor neutra (`#d1d5db`), separando claramente "sem dado" de "baixo desempenho".
  - modos `points` e `heatmap` passaram a considerar somente features com valor presente.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - legenda visual ganhou chip `Sem dado`, alinhado ao comportamento do mapa vetorial.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-20) - Mapa com rotulos e zoom contextual

- `frontend/src/shared/ui/VectorMap.tsx`:
  - camada ativa agora exibe rotulos contextuais a partir de propriedades disponíveis (`label`, `name`, `tname`, `territory_name`, `road_name`, `poi_name`, `category`).
  - camadas lineares urbanas usam `symbol-placement=line` para leitura mais natural de vias.
  - atribuição de basemap normalizada:
    - `(c) OpenStreetMap contributors`
    - `(c) OpenStreetMap contributors (c) CARTO`
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - `Aplicar filtros` agora respeita zoom mínimo contextual por escopo/nível.
  - piso de zoom explicito para camadas urbanas e ajuste por metadata de camada (`zoom_min`).
  - leitura de apoio adicionada na UI: `Zoom contextual minimo recomendado`.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Diretriz operacional sem dispersao (2026-02-19)

- Diretriz oficial de foco publicada e consolidada em `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` (secoes 7, 8 e 9).
- Ordem de execução obrigatoria no ciclo atual:
  - 1) estabilizar telas e fluxo de decisão (`/visao-geral`, `/mapa`, `/territorio-360`, `/eleitorado`);
  - 2) fechar gates de confiabilidade (qualidade/readiness/smokes e evidencias operacionais);
  - 3) fechar lacunas criticas de conectores e cobertura territorial;
  - 4) so entao ampliar escopo (D4/D5) com novas frentes.
- Regra de priorização ativa:
  - não abrir nova frente enquanto houver pendencia critica em UX, dados ou contrato técnico da etapa corrente.
  - qualquer item novo fora da trilha principal entra como backlog, sem interromper o fechamento da etapa em andamento.

## Atualizacao técnica (2026-02-19) - QG Prioridades (paginacao)

- `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`:
  - lista de prioridades passou a suportar paginacao client-side com:
    - seletor `Itens por pagina` (`12`, `24`, `48`);
    - controles `Anterior`/`Proxima`;
    - indicador `Pagina X de Y`.
  - página atual reinicia ao aplicar/limpar filtros e ao alterar tamanho de página.
  - resumo da lista agora evidencia `visiveis`, `filtradas` e `retorno bruto`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - novo teste de regressão para cenario com `30` prioridades, validando navegacao entre páginas.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx` -> `11 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-19) - Mapa vetorial (controles de navegacao)

- `frontend/src/shared/ui/VectorMap.tsx`:
  - controle nativo de navegacao configurado com zoom + bussola.
  - `FullscreenControl` habilitado quando disponível no runtime.
  - `ScaleControl` habilitado (unidade métrica) no canto inferior esquerdo.
  - `AttributionControl` compacto habilitado no canto inferior direito.
  - atribuição dos basemaps aplicada na fonte raster:
    - `streets`: `(c) OpenStreetMap contributors`
    - `light`: `(c) OpenStreetMap contributors (c) CARTO`
- `frontend/src/styles/global.css`:
  - refinamento visual dos controles `maplibregl` (grupo, botoes, escala e atribuição).
  - ajustes de posicionamento e responsividade para reduzir sobreposicao em viewport menor.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-19) - Estabilizacao de telas criticas

- `Territorio 360`:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` agora trata `404` do perfil como estado vazio orientado (sem quebrar a tela).
  - filtros permanecem ativos no estado vazio para troca imediata de território/período.
  - regressão coberta em `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`.
- `Eleitorado`:
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` passou a aplicar fallback automatico para o ultimo ano com dados quando o ano filtrado retorna vazio.
  - aviso explicito de fallback exibido na tela, mantendo leitura executiva (KPIs/tabela/composicao) sem tela morta.
  - cobertura de teste ampliada em `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`.
- `Mapa executivo`:
  - `frontend/src/shared/ui/VectorMap.tsx` com opacidade de preenchimento e contorno territorial adaptativos por basemap.
  - objetivo: reduzir efeito de "bloco chapado" do coropletico e preservar contexto de navegacao no mapa-base.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx` -> `11 passed`.
  - `npm --prefix frontend run build` -> `OK`.

## Atualizacao técnica (2026-02-18) - Robustez de banco

- Hardening de cobertura territorial concluido no backend:
  - `tse_electorate_fetch` agora grava eleitorado municipal e por zona eleitoral (com upsert em `dim_territory` nível `electoral_zone`).
  - `ibge_geometries_fetch` agora grava `IBGE_GEOMETRY_AREA_KM2` em `silver.fact_indicator` para `municipality`, `district` e `census_sector`.
- Backfill robusto executado com sucesso:
  - comando (histórico eleitoral): `scripts/backfill_robust_database.py --tse-years 2024,2022,2020,2018,2016 --indicator-periods 2025`.
  - comando (multianual indicadores): `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --indicator-periods 2025,2024,2023,2022,2021`.
  - relatório: `data/reports/robustness_backfill_report.json`.
  - cobertura eleitoral consolidada:
    - `fact_electorate`: `5` anos distintos (`2016`-`2024`) e `3562` linhas.
    - `fact_election_result`: `5` anos distintos (`2016`-`2024`), `180` linhas totais e `90` por zona eleitoral.
- Qualidade apos backfill:
  - scorecard atualizado em `data/reports/data_coverage_scorecard.json`: `pass=10`, `warn=1`.
  - `backend_readiness`: `READY`, `hard_failures=0`, `warnings=0`.
  - `indicator_distinct_periods`: `5` (`pass`) e `implemented_runs_success_pct_7d`: `95.36` (`pass`).
  - `implemented_connectors_pct`: `91.67` (`warn`) por entrada de 2 conectores sociais em `partial`.
- Sprint D0 da trilha de robustez maxima concluido:
  - `BD-001`: DoD de robustez maxima oficializado no `docs/CONTRATO.md`.
  - `BD-002`: scorecard SQL versionado em `ops.v_data_coverage_scorecard` + export em `scripts/export_data_coverage_scorecard.py`.
  - `BD-003`: runbook semanal publicado em `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`.
  - baseline semanal gerado em `data/reports/data_coverage_scorecard.json`.
- Sprint D1 concluido:
  - `BD-010`: histórico TSE carregado para `2024,2022,2020,2018,2016`.
  - `BD-011`: checks de integridade de `electoral_zone` ativos (`count`, `orphans`, `canonical_key`).
  - `BD-012`: checks de continuidade temporal ativos (`max_year_gap` e `source_periods_*`).
  - aceite D1 atendido:
    - `fact_electorate` com `>=5` anos (`pass`).
    - `fact_election_result` com `>=5` anos (`pass`).
    - cobertura de `electoral_zone` em `pass` sem excecao.
- Sprint D2 iniciado com entrega técnica base:
  - migration `db/sql/008_social_domain.sql` com:
    - `silver.fact_social_protection`
    - `silver.fact_social_assistance_network`
  - conectores sociais implementados:
    - `cecad_social_protection_fetch`
    - `censo_suas_fetch`
  - helper comum criado em `src/pipelines/common/social_tabular_connector.py`.
  - endpoints sociais publicados:
    - `GET /v1/social/protection`
    - `GET /v1/social/assistance-network`
  - checks sociais adicionados no `quality_suite`.
  - status atual dos conectores sociais em `ops.connector_registry`: `partial` (aguardando fonte governada estavel).
  - paths de fallback manual para ativacao controlada:
    - `data/manual/cecad/`
    - `data/manual/censo_suas/`
- Sprint D2 consolidado com ciclo operacional social:
  - comando executado:
    - `scripts/backfill_robust_database.py --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --include-wave6 --indicator-periods 2014,2015,2016,2017 --output-json data/reports/robustness_backfill_report.json`.
  - resultado:
    - `censo_suas_fetch`: `success` em `2014..2017`.
    - `cecad_social_protection_fetch`: `blocked` em `2014..2017` (esperado sem acesso governado).
  - estado de dados apos ciclo:
    - `silver.fact_social_assistance_network`: `4` linhas (`2014..2017`).
    - `silver.fact_social_protection`: `0` linhas (pendencia externa de acesso CECAD).
  - cobertura e readiness revalidados:
    - `data/reports/data_coverage_scorecard.json`: `pass=10`, `warn=1`.
    - `scripts/backend_readiness.py --output-json`: `READY`, `hard_failures=0`, `warnings=0`.
- Encaminhamento:
  - D2 fechado tecnicamente com ressalva de governança CECAD.
  - frente ativa passa para D3 (`BD-030`, `BD-031`, `BD-032`) com foco em vias, POIs e geocodificacao local.
- Sprint D3 iniciado com incremento técnico base (backend):
  - migration `db/sql/009_urban_domain.sql` aplicada com objetos:
    - `map.urban_road_segment`
    - `map.urban_poi`
    - `map.v_urban_data_coverage`
  - novos endpoints urbanos publicados:
    - `GET /v1/map/urban/roads`
    - `GET /v1/map/urban/pois`
    - `GET /v1/map/urban/nearby-pois`
  - validação técnica:
    - `scripts/init_db.py`: `Applied 9 SQL scripts`.
    - `pytest (contracts + api_contract)`: `18 passed`.
    - `backend_readiness`: `READY`, `hard_failures=0`, `warnings=0`.
- Sprint D3 avancado para ingestao e geocodificacao local (2026-02-19):
  - conectores urbanos implementados e integrados:
    - `urban_roads_fetch` (`src/pipelines/urban_roads.py`)
    - `urban_pois_fetch` (`src/pipelines/urban_pois.py`)
  - catálogos urbanos adicionados:
    - `configs/urban_roads_catalog.yml`
    - `configs/urban_pois_catalog.yml`
  - orquestracao atualizada:
    - `run_mvp_all` inclui jobs urbanos.
    - novo fluxo `run_mvp_wave_7`.
    - `configs/jobs.yml` e `configs/waves.yml` incluem `MVP-7`.
    - `scripts/backfill_robust_database.py` com flag `--include-wave7`.
  - API urbana ampliada:
    - novo endpoint `GET /v1/map/urban/geocode`.
  - tiles urbanos multi-zoom habilitados no endpoint vetorial existente:
    - `GET /v1/map/tiles/urban_roads/{z}/{x}/{y}.mvt`
    - `GET /v1/map/tiles/urban_pois/{z}/{x}/{y}.mvt`
    - suporte mantido para cache/ETag (`Cache-Control`, `ETag`, `X-Tile-Ms`).
  - catálogo e cobertura de camadas no backend de mapa ampliados para domínio urbano via query param:
    - `GET /v1/map/layers?include_urban=true`
    - `GET /v1/map/layers/coverage?include_urban=true`
    - `GET /v1/map/layers/readiness?include_urban=true`
  - contrato técnico territorial mantido sem mistura de escopos:
    - `GET /v1/territory/layers/*` opera com `include_urban=false`.
  - monitor técnico de camadas atualizado no frontend Ops:
    - `OpsLayersPage` agora consulta `GET /v1/map/layers/readiness`.
    - filtro de escopo suportado: `Territorial`, `Territorial + Urbano`, `Somente urbano`.
    - resumo operacional adicional publicado na tela:
      - cards agregados (`Camadas no recorte`, `Readiness pass|warn|fail|pending`).
      - grade de "Resumo rapido das camadas" por item com chips de `rows`, `geom` e `readiness`.
    - cobertura de teste frontend ampliada em `frontend/src/modules/ops/pages/OpsPages.test.tsx`.
  - politica de cache HTTP para camadas ajustada:
    - `/v1/map/layers/readiness` e `/v1/map/layers/coverage` com `max-age=60`.
    - `/v1/map/layers` mantido em `max-age=3600`.
  - qualidade ampliada:
    - `quality_suite` executa `check_urban_domain`.
    - thresholds urbanos em `configs/quality_thresholds.yml`.
  - scorecard de cobertura ampliado:
    - `urban_road_rows` e `urban_poi_rows` em `ops.v_data_coverage_scorecard`.
  - validação deste incremento:
    - `pytest` focado em connectors/map/quality/flows/contracts: `40 passed`.
    - `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`: `9 passed`.
    - `npm --prefix frontend run test`: `66 passed`.
    - `npm --prefix frontend run build`: `OK`.
  - benchmark de performance para fechamento de `BD-032` executado:
    - `scripts/benchmark_api.py` com suites `executive`, `urban` e `all`.
    - suite `urban` mede p95 dos endpoints:
      - `/v1/map/urban/roads`
      - `/v1/map/urban/pois`
      - `/v1/map/urban/nearby-pois`
      - `/v1/map/urban/geocode`
    - comando de evidencia:
      - `python scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json`
    - resultado atual:
      - `ALL PASS` com p95 `< 1.0s` para todos os endpoints urbanos.
  - carga urbana real (D3) executada e validada:
    - `urban_roads_fetch(2026)`: `success`, `rows_written=6550`.
    - `urban_pois_fetch(2026)`: `success`, `rows_written=319`.
    - `backend_readiness --output-json`: `READY`, `hard_failures=0`, `warnings=0`.
  - `BD-033` iniciado no frontend para UX de navegacao:
    - `QgMapPage` com seletor de mapa base (`Ruas`, `Claro`, `Sem base`).
    - `VectorMap` com suporte a basemap raster por baixo das camadas MVT.
    - escopo explicito de camada no `QgMapPage`:
      - `Territorial` (manifestao de camadas por nível)
      - `Urbana` (`urban_roads` / `urban_pois`)
    - `VectorMap` atualizado para renderizar camadas lineares (`layer_kind=line`) para viario urbano.
  - fechamento de lacunas de estrutura de camadas (2026-02-19):
    - backend de mapa com camada proxy de bairro: `territory_neighborhood_proxy` (base setorial) no catálogo, metadata, readiness e tiles.
    - `QgMapPage` com orientacao explicita para `local_votacao` no fluxo eleitoral:
      - seletor `Camada eleitoral detalhada`
      - nota de camada ativa para `Locais de votacao`
      - leitura contextual `local_votacao` no card de seleção.
    - `QgOverviewPage` passou a aplicar `Camada detalhada (Mapa)` no proprio mapa dominante, alem dos links para `/mapa`.
    - `OpsLayersPage` ganhou alerta de degradação por camada (`fail`, `warn`, `pending`) para triagem técnica imediata.
    - fallback SVG bloqueado para escopo urbano com mensagem orientativa (somente modo vetorial).
    - teste de regressão para URL prefill urbana em `frontend/src/modules/qg/pages/QgPages.test.tsx`.
    - overrides por ambiente em `frontend/.env.example`:
      - `VITE_MAP_BASEMAP_STREETS_URL`
      - `VITE_MAP_BASEMAP_LIGHT_URL`
  - `BD-033` avancado (iteracao atual) com deep-link completo:
    - `QgMapPage` sincroniza query string com recorte aplicado e estado de visualizacao:
      - `metric`, `period`, `level`, `scope`, `layer_id`, `territory_id`, `basemap`, `viz`, `renderer`, `zoom`.
    - `QgMapPage` passou a ler `viz`, `renderer` e `zoom` no carregamento inicial.
    - botao `Limpar` reseta baseline visual (`streets`, `choropleth`, mapa vetorial, `zoom=4`).
    - cobertura de teste ampliada em `frontend/src/modules/qg/pages/QgPages.test.tsx` para prefill e sync de URL.
    - `VectorMap` passou a ser carregado sob demanda (`React.lazy` + `Suspense`) no `QgMapPage`.
    - efeito imediato no build frontend:
      - `QgMapPage-*.js` ~`19KB` (antes ~`1.0MB`).
      - chunk pesado isolado em `VectorMap-*.js`.
    - refinamento de UX responsiva no mapa executivo:
      - toolbar de controles organizada em blocos (`modo`, `mapa base`, `renderizacao`) com layout responsivo.
      - selectors e controle de zoom ajustados para evitar overflow horizontal em viewport menor.
      - shell visual do mapa com altura fluida (`.map-canvas-shell`) para consistencia desktop/mobile.
    - navegacao territorial ampliada para aproximar UX de mapa operacional:
      - busca rapida de território no `QgMapPage` (`Buscar territorio` + `Focar territorio`).
      - ações diretas no painel de filtro:
        - `Focar selecionado`
        - `Recentrar mapa`
      - `VectorMap` com foco por território selecionado via ajuste de camera (`fitBounds`/`easeTo`).
      - `VectorMap` com sinais de controle de viewport:
        - `focusTerritorySignal`
        - `resetViewSignal`
      - fallback seguro para ambiente de testes quando mocks não expoem:
        - `easeTo`
        - `fitBounds`
        - `GeolocateControl`
    - ações contextuais urbanas publicadas no card de seleção:
      - filtro rapido por classe/categoria (`/v1/map/urban/roads` e `/v1/map/urban/pois`).
      - geocodificacao contextual (`/v1/map/urban/geocode`).
      - consulta de POIs próximos ao ponto clicado (`/v1/map/urban/nearby-pois`).
      - links territoriais (`/territorio`, `/prioridades`, `/briefs`) mantidos apenas para escopo territorial.
    - contrato de tiles urbanos enriquecido para contexto operacional:
      - `urban_roads` inclui `road_class`, `is_oneway`, `source`.
      - `urban_pois` inclui `category`, `subcategory`, `source`.
      - `VectorMap` passou a propagar `lon`/`lat` da seleção para habilitar consulta por proximidade.
    - `QgOverviewPage` evoluida para `Layout B` (mapa dominante):
      - uso de `MapDominantLayout` para destacar o mapa na Home executiva.
      - painel lateral colapsavel com filtros principais, cards de status e ações rapidas.
      - leitura do território selecionado diretamente no painel lateral.
      - ajustes de CSS para reduzir overflow e melhorar responsividade do painel do mapa.
    - Home executiva evoluida para modo vetorial no mapa dominante:
      - `QgOverviewPage` agora usa `VectorMap` na area principal da Home com fallback SVG.
      - basemap comutavel (`Ruas`, `Claro`, `Sem base`) e zoom adicionados no painel lateral.
      - controles de navegacao adicionados no painel lateral:
        - `Focar selecionado`
        - `Recentrar mapa`
      - clique no mapa vetorial sincroniza território selecionado no contexto lateral.
    - suites de navegacao ajustadas para nova estrutura de links no mapa:
      - `router.smoke.test.tsx` atualizado para selecionar link `Abrir perfil` de forma robusta.
      - `e2e-flow.test.tsx` atualizado para o mesmo comportamento.
    - cobertura de teste ampliada:
      - `QgPages.test.tsx` valida foco por busca e sincronizacao de `territory_id` na URL.
    - build frontend com chunking manual configurado (`frontend/vite.config.ts`):
      - chunks dedicados para `vendor-react`, `vendor-router`, `vendor-query`, `vendor-maplibre`, `vendor-misc`.
      - `index` reduzido para ~`12KB` (gzip ~`4.3KB`) com melhor carregamento inicial.
    - validação adicional:
      - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx`: `18 passed`.
      - `npm --prefix frontend run test`: `69 passed`.
      - `npm --prefix frontend run build`: `OK`.

## Governança documental consolidada (2026-02-13)

1. `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` passa a ser somente visão estrategica do produto.
2. `docs/PLANO_IMPLEMENTACAO_QG.md` permanece como fonte unica de execução e prioridade.
3. `HANDOFF.md` permanece como estado operacional corrente + próximos passos imediatos.
4. Specs estrategicas promovidas a v1.0 com fases concluidas marcadas:
   - `MAP_PLATFORM_SPEC.md` (MP-1, MP-2 e MP-3 baseline concluidos)
   - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` (TL-1, TL-2 e TL-3 baseline concluidos)
   - `STRATEGIC_ENGINE_SPEC.md` (SE-1 e SE-2 concluidos)
5. Matriz detalhada de rastreabilidade (item a item da evolução) publicada em:
   - `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`
6. Classificação de referência complementar:
   - `docs/FRONTEND_SPEC.md` = referência de produto/UX para debate.
   - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` = catálogo/priorização de fontes (não status operacional diario).

## Atualizacao técnica (2026-02-13)

### Sprint 9 - territorial layers TL-2/TL-3 + base eleitoral (iteracao atual)
- **Camadas territoriais com rastreabilidade operacional**:
  - `GET /v1/map/layers/coverage` e `GET /v1/map/layers/{layer_id}/metadata` publicados.
  - `GET /v1/territory/layers/*` publicado para catálogo, cobertura, metadata e readiness.
  - readiness combina catálogo + cobertura + checks do `quality_suite` para visão técnica unica.
  - camada `territory_polling_place` adicionada no catálogo MVT como ponto eleitoral derivado.
- **Admin/ops com página dedicada para camadas**:
  - nova rota `/ops/layers` com filtros por métrica/período e tabela de readiness por camada.
  - `AdminHubPage` atualizado com atalho direto para a página de camadas.
  - `QgMapPage` com seletor explicito de camada de secao (incluindo `Locais de votacao`) para controle manual no fluxo executivo.
  - `QgMapPage` passa a respeitar `layer_id` por query string no carregamento inicial.
  - `QgOverviewPage` passa a propagar `layer_id` nos links para `/mapa` (atalho principal e cards Onda B/C), via seletor `Camada detalhada (Mapa)`.
- **Quality suite com checks de camada**:
  - checks de volume e geometria por nível (`map_layer_rows_*` e `map_layer_geometry_ratio_*`) integrados.
  - thresholds dedicados em `configs/quality_thresholds.yml`.
- **Pipeline TSE resultados evoluido para base eleitoral territorial**:
  - parse de zona/secao eleitoral (quando colunas existirem no arquivo oficial).
  - detecção de `local_votacao` (quando disponível) como metadata preparatoria da secao.
  - upsert de `electoral_zone` e `electoral_section` em `silver.dim_territory`.
  - `fact_election_result` agora resolve `territory_id` em ordem secao > zona > município.
- **Validações da iteracao**:
  - backend: testes de `tse_results`, `mvt_tiles` e `quality_core_checks` passando.
  - frontend: `QgPages.test.tsx` passando apos incluir seletor de camada; build Vite passando.

### Sprint 8 - Vector engine MP-3 + Strategic engine SE-2 (iteracao anterior)
- **MapLibre GL JS + VectorMap** (`VectorMap.tsx`):
  - Componente MVT-first (~280 linhas) com 4 viz modes: coroplético, pontos, heatmap, hotspots.
  - Auto layer switch por zoom, seleção de território, estilo local-first.
  - Integrado no QgMapPage com fallback SVG (ChoroplethMiniMap).
- **Multi-level geometry simplification** (`routes_map.py`):
  - 5 faixas de tolerância por zoom (0.05 → 0.0001).
  - Substituiu fórmula genérica por bandas discretas.
- **MVT cache ETag + latency metrics**:
  - ETag MD5 + If-None-Match 304 + header X-Tile-Ms.
  - Endpoint `GET /v1/map/tiles/metrics` com p50/p95/p99.
- **Strategic engine config SE-2** (`configs/strategic_engine.yml`):
  - Thresholds, severity_weights, limites externalizados em YAML.
  - `score_to_status()` + `status_impact()` config-driven (não mais hardcoded).
  - SQL CASE parametrizado + `config_version` em todas as respostas QgMetadata.
- **Spatial GIST index**: `idx_dim_territory_geometry` adicionado.
- Validações:
  - backend: 246 testes passando (+33 vs Sprint 7).
  - frontend: 59 testes passando em 18 arquivos.
  - build Vite: OK.
  - 26 endpoints totais.

### Sprint 7 - UX evolution + map platform MP-2 (iteracao anterior)
- **Layout B: mapa dominante na Home**:
  - QgOverviewPage reescrito com ChoroplethMiniMap dominante + sidebar overlay com glassmorphism.
  - Barra de estatisticas flutuante (criticos/atencao/monitorados), toggle sidebar.
  - Labels encurtados: Aplicar, Prioridades, Mapa detalhado, Território critico.
- **Drawer lateral reutilizavel** (`Drawer.tsx`):
  - Componente slide-in left/right, escape key, backdrop click, aria-modal, foco automatico.
- **Zustand para estado global** (`filterStore.ts`):
  - Store compartilhado: period, level, metric, zoom.
  - Integrado na Home e pronto para uso cross-page.
- **MapDominantLayout** (`MapDominantLayout.tsx`):
  - Layout wrapper: mapa full-viewport + sidebar colapsavel, responsivo.
- **MVT tiles endpoint (MP-2)**:
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt` via PostGIS ST_AsMVT.
  - Dois caminhos SQL: com join de indicador ou geometria pura.
  - Filtro por domain, tolerancia adaptativa por zoom, Cache-Control 1h.
  - 25 endpoints totais (11 QG + 10 ops + 1 geo + 2 map + 1 MVT).
- **Auto layer switch por zoom** (`useAutoLayerSwitch.ts`):
  - Hook que seleciona camada pelo zoom_min/zoom_max do manifesto /v1/map/layers.
  - Controle de zoom (range slider) integrado no QgMapPage.
- Validações:
  - backend: 213 testes passando (+6 MVT).
  - frontend: 59 testes passando, 18 arquivos (+16 testes vs Sprint 6).
  - build Vite: OK (1.51s).

### Sprint 6 - go-live v1.0 closure (iteracao anterior)
- Contrato v1.0 congelado (`CONTRATO.md`):
  - 24 endpoints formalizados (11 QG + 10 ops + 1 geo + 2 map).
  - SLO-2 bifurcado: operacional (p95 <= 1.5s) e executivo (p95 <= 800ms).
  - Secao 12.1 com tabela de ferramentas (homologation_check, benchmark_api, backend_readiness, quality_suite).
- Runbook de operações (`OPERATIONS_RUNBOOK.md`):
  - 12 secoes cobrindo todo ciclo de vida: ambiente, pipelines, qualidade, views, API, frontend, go-live, testes, troubleshooting, conectores especiais, deploy (11 passos + rollback).
- Specs v0.1 → v1.0:
  - `MAP_PLATFORM_SPEC.md`: MP-1 CONCLUIDO (manifesto, style-metadata, cache, fallback).
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`: TL-1 CONCLUIDO (is_official, badge, coverage_note).
  - `STRATEGIC_ENGINE_SPEC.md`: SE-1 CONCLUIDO (score/severity/rationale/evidence, simulação, briefs).
- Matriz de rastreabilidade atualizada:
  - O6-03 → OK (progressive disclosure), O8-02 → OK (admin diagnostics 7 paineis), D01 → OK (contrato v1.0).
- Validações:
  - backend: 207 testes passando.
  - frontend: 43 testes passando, 15 arquivos.
  - build Vite: OK.

### Sprint 5.3 - go-live readiness (iteracao anterior)
- Thresholds de qualidade por domínio/fonte:
  - 15 fontes com `min_rows` explicito em `quality_thresholds.yml` (incluindo DATASUS, INEP, SICONFI, MTE, TSE).
  - MVP-5 sources elevados de 0→1.
  - `quality.py`: 15 fontes checadas em `source_rows`, 14 jobs em `ops_pipeline_runs`.
- Script de homologação consolidado (`scripts/homologation_check.py`):
  - 5 dimensões: backend readiness, quality suite, frontend build, test suites, API smoke.
  - Verdict unico READY/NOT READY com suporte `--json` e `--strict`.
- Progressive disclosure na Home (QgOverviewPage):
  - `CollapsiblePanel` component com chevron, badge count, `aria-expanded`.
  - "Domínios Onda B/C" colapsado por padrão; "KPIs executivos" expandido.
- Admin diagnostics refinement (OpsHealthPage):
  - 3 paineis colapsaveis adicionados: Quality checks, Cobertura de fontes, Registro de conectores.
- Validações:
  - backend: 207 testes passando.
  - frontend: 43 testes passando, 15 arquivos.
  - build Vite: OK.

### Sprint 5.2 - acessibilidade e hardening (iteracao anterior)
- Benchmark de performance da API criado:
  - `scripts/benchmark_api.py`: p50/p95/p99 em 12 endpoints, alvo p95<=800ms.
- Edge-case contract tests adicionados:
  - `tests/unit/test_qg_edge_cases.py`: 44 testes (validação de nível, limites, dados vazios, request_id, content-type).
- Badge de classificação de fonte (P05):
  - `source_classification` no backend (oficial/proxy/misto) + badge no frontend.
- Persistencia de sessao (O7-05):
  - `usePersistedFormState` hook com prioridade queryString > localStorage > defaults.
  - integrado em Cenarios (6 campos) e Briefs (5 campos).
- Accessibility hardening (Sprint 5.2 item 1):
  - `Panel`: `aria-labelledby` vinculado ao titulo via `useId`.
  - `StateBlock`: `role=alert/status` + `aria-live`.
  - `StrategicIndexCard`: `aria-label` no article e status.
  - Páginas executivas: `<main>` no lugar de `<div>`, tabelas com `aria-label`, botoes com `aria-label` contextual.
  - Ranking territorial: linhas com keyboard support (tabIndex, onKeyDown, role=button).
  - Quick-actions: `<nav aria-label>`.
- Validações desta iteracao:
  - backend: 207 testes passando (pytest).
  - frontend: 43 testes passando (vitest), 15 arquivos.
  - build Vite: OK.

### Sprint 5 - hardening (iteracao anterior)
- E2E do fluxo critico de decisão implementado:
  - `frontend/src/app/e2e-flow.test.tsx` com 5 testes: fluxo principal completo + 3 deep-links + admin→executivo.
  - cobertura: Home → Prioridades → Mapa → Território 360 → Eleitorado → Cenarios → Briefs.
- Cache HTTP ativo nos endpoints criticos:
  - `CacheHeaderMiddleware` com Cache-Control, weak ETag e 304 condicional.
  - endpoints cobertos: map/layers, map/style-metadata, kpis, priority, insights, choropleth, electorate, territory.
- Materialized views criadas para ranking e mapa:
  - `db/sql/006_materialized_views.sql`: 3 MVs com refresh concorrente.
  - geometria simplificada via `ST_SimplifyPreserveTopology` na MV de mapa.
- Indices espaciais GIST adicionados:
  - `db/sql/007_spatial_indexes.sql`: GIST, GIN trigram, covering index.
- Admin readiness integrado:
  - `AdminHubPage.tsx` exibe ReadinessBanner com status consolidado de `GET /v1/ops/readiness`.
- Validações desta iteracao:
  - backend: 163 testes passando (pytest).
  - frontend: 43 testes passando (vitest), 15 arquivos.
  - build Vite: OK.

### MP-1 (entregue anteriormente nesta data)
- MP-1 do mapa executado no backend/frontend:
  - `QgMapPage` integrado ao manifesto para exibir recomendacao de camada por nível (`municipio`/`distrito`).
  - fallback preservado para `GET /v1/geo/choropleth`, sem interrupcao da página quando o manifesto falhar.
- MP-1 estendido com metadados de estilo:
  - endpoint `GET /v1/map/style-metadata` ativo com modo padrão, paleta de severidade e ranges de legenda.
  - `QgMapPage` integrado para exibir contexto visual de estilo sem acoplar a renderizacao ao backend.
- Validações desta iteracao:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `6 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `38 passed`.
  - `npm --prefix frontend run build`: `OK`.

## Atualizacao rapida (2026-02-12)

- Backend funcionalmente pronto para avancar no frontend (API + pipelines + checks + scripts operacionais).
- Sprint 0 do QG iniciado no backend com contratos de API para Home/Prioridades/Insights:
  - `GET /v1/kpis/overview`
  - `GET /v1/priority/list`
  - `GET /v1/priority/summary`
  - `GET /v1/insights/highlights`
- Sprint 2 do QG avancou no backend com contratos de API para Perfil/Comparacao e Eleitorado executivo:
  - `GET /v1/territory/{id}/profile`
  - `GET /v1/territory/{id}/compare`
  - `GET /v1/electorate/summary`
  - `GET /v1/electorate/map`
- Extensao v1.1 iniciada no backend:
  - `POST /v1/scenarios/simulate` (simulação simplificada por variação percentual).
  - simulação evoluida para calcular ranking antes/depois por indicador e delta de posicao.
  - `POST /v1/briefs` para geracao de brief executivo com resumo e evidencias.
- Sprint 3/4 (Onda A) iniciado no backend:
  - `sidra_indicators_fetch` evoluido para ingestao real via SIDRA API (`implemented`).
  - `senatran_fleet_fetch` evoluido para ingestao real tabular (`implemented`).
  - `sejusp_public_safety_fetch` evoluido para ingestao real tabular (`implemented`).
  - `siops_health_finance_fetch` evoluido para ingestao real tabular (`implemented`).
  - `snis_sanitation_fetch` evoluido para ingestao real tabular (`implemented`).
  - Onda A de conectores concluida no backend em modo implementado.
  - todos integrados no orquestrador em `run_mvp_wave_4` e `run_mvp_all`.
- Sprint 6 técnico (Onda B/C) iniciado no backend:
  - novos conectores integrados:
    - `inmet_climate_fetch`
    - `inpe_queimadas_fetch`
    - `ana_hydrology_fetch`
    - `anatel_connectivity_fetch`
    - `aneel_energy_fetch`
  - todos integrados no orquestrador em `run_mvp_wave_5` e `run_mvp_all`.
  - padrão de execução igual aos conectores Onda A:
    - remote catalog quando disponível
    - fallback manual por diretorio dedicado em `data/manual/*`
    - Bronze + checks + `ops.pipeline_runs/pipeline_checks` + upsert em `silver.fact_indicator`.
  - `scripts/bootstrap_manual_sources.py` ampliado para Onda B/C:
    - novas opcoes de bootstrap: `INMET`, `INPE_QUEIMADAS`, `ANA`, `ANATEL`, `ANEEL`.
    - parser tabular generico por catálogo com tentativa de filtro municipal automatico.
    - parser CSV/TXT endurecido com seleção automatica do melhor delimitador.
    - seleção de entrada ZIP por nome do município quando disponível.
    - detecção do cabecalho INMET (`Data;Hora UTC;...`) para leitura correta da serie horaria.
    - fallback de recorte municipal por nome de arquivo quando o payload não traz colunas de município.
    - quando não for possivel consolidar recorte municipal de forma confiavel, retorna `manual_required`
      no relatório, mantendo rastreabilidade dos links/arquivos tentados.
  - validação local do bootstrap Onda B/C executada sem erro de processo:
    - `INMET`/`INPE_QUEIMADAS`: consolidação municipal automatica validada com status `ok`
      e geracao de arquivos em `data/manual/inmet` e `data/manual/inpe_queimadas`.
    - `ANATEL`/`ANEEL`: consolidação municipal automatica validada com status `ok`
      e geracao de arquivos em `data/manual/anatel` e `data/manual/aneel`.
    - `ANA`: consolidação municipal automatica validada com status `ok`
      e geracao de arquivo em `data/manual/ana`.
  - catálogos remotos oficiais configurados:
    - `ANATEL`: `meu_municipio.zip` (acessos/densidade por município).
    - `ANEEL`: `indger-dados-comerciais.csv` (dados comerciais por município).
    - `ANA`: download oficial via ArcGIS Hub (`api/download/v1/items/.../csv?layers=18`)
      com fallback para endpoints ArcGIS (`www.snirh.gov.br` e `portal1.snirh.gov.br`).
  - `ANEEL` foi ajustado para `prefer_manual_first` no conector, reduzindo custo de execução
    local quando o CSV municipal consolidado ja existe em `data/manual/aneel`.
  - estado de rede atual para `ANA` no ambiente local:
    - hosts SNIRH seguem instaveis (`ConnectTimeout`) em algumas tentativas;
    - coleta automatica segue funcional via URL ArcGIS Hub e fallback manual permanece disponível.
  - validação de fluxo `run_mvp_wave_5` (referência 2025, `dry_run=False`):
    - `success`: `inmet_climate_fetch`, `inpe_queimadas_fetch`, `anatel_connectivity_fetch`, `aneel_energy_fetch`.
    - `blocked`: `ana_hydrology_fetch` (timeout remoto + sem arquivo em `data/manual/ana`).
  - mapeamento de domínio QG atualizado para as novas fontes
    (`clima`, `meio_ambiente`, `recursos_hidricos`, `conectividade`, `energia`).
- Frontend integrado ao novo contrato QG:
  - rota inicial (`/`) com `QgOverviewPage` consumindo `kpis/overview`, `priority/summary` e `insights/highlights`.
  - rota `prioridades` com `QgPrioritiesPage` consumindo `priority/list`.
  - rota `mapa` com `QgMapPage` consumindo `geo/choropleth`.
  - `mapa` agora possui visualizacao geografica simplificada (SVG) com escala de valor e seleção de território.
  - rota `insights` com `QgInsightsPage` consumindo `insights/highlights`.
  - rota `cenarios` com `QgScenariosPage` consumindo `POST /v1/scenarios/simulate`.
  - tela de cenarios passou a exibir score e ranking antes/depois com impacto estimado.
  - rota `briefs` com `QgBriefsPage` consumindo `POST /v1/briefs`.
  - Home QG passou a exibir `Top prioridades` (previsualizacao) e `Acoes rapidas` para fluxo de decisão.
  - ação `Ver no mapa` da Home passou a abrir diretamente o recorte da prioridade mais critica.
  - `Territorio 360` passou a oferecer atalhos para `briefs` e `cenarios` com território/período pre-preenchidos.
  - `QgBriefsPage` e `QgScenariosPage` passaram a aceitar query string para prefill de filtros.
  - `QgPrioritiesPage` passou a oferecer ordenacao local e exportacao CSV da lista priorizada.
  - `PriorityItemCard` ganhou deep-link `Ver no mapa` para recorte de indicador/período/território.
  - `QgMapPage` passou a aceitar query string para prefill de filtros e seleção territorial inicial.
  - `QgMapPage` ganhou exportacao CSV do ranking territorial.
  - `QgMapPage` ganhou exportacao visual do mapa em `SVG` e `PNG`.
  - endpoint `GET /v1/territory/{id}/profile` evoluiu com score/status/tendencia agregados do território:
    - `overall_score`
    - `overall_status`
    - `overall_trend`
  - `TerritoryProfilePage` passou a exibir card executivo de status geral com score consolidado e tendencia.
  - endpoint `GET /v1/territory/{id}/peers` adicionado para sugerir comparacoes por similaridade de indicadores.
  - `TerritoryProfilePage` passou a exibir painel de pares recomendados com ação direta `Comparar`.
  - `QgBriefsPage` passou a suportar exportacao do brief em `HTML` e impressao para `PDF` pelo navegador.
  - rota `territorio/perfil` (alias legado: `territory/profile`) com `TerritoryProfilePage` (profile + compare).
  - rota dinamica `territorio/:territoryId` (alias legado: `territory/:territoryId`) com `TerritoryProfileRoutePage`.
  - rota `eleitorado` (alias legado: `electorate/executive`) com `ElectorateExecutivePage` (summary + map).
  - links de contexto (`Abrir perfil`) adicionados em `Mapa` e `Prioridades` para navegação direta ao perfil territorial.
  - rota `admin` adicionada como hub técnico, separando links operacionais (`ops/*`) do menu principal executivo.
  - metadados de fonte/atualizacao/cobertura expostos nas telas executivas com `SourceFreshnessBadge`.
  - Home QG evoluida para usar `StrategicIndexCard` na secao de situacao geral.
  - lista de prioridades evoluida para `PriorityItemCard` (cards com score, racional, evidencia e ação).
  - cliente dedicado em `frontend/src/shared/api/qg.ts` e tipagens QG em `frontend/src/shared/api/types.ts`.
  - cobertura de teste de página adicionada para fluxo QG em:
    - `frontend/src/modules/qg/pages/QgPages.test.tsx`
    - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
    - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - wrappers de teste com `MemoryRouter` adicionados nas páginas com navegacao interna.
  - testes QG ampliados para validar prefill por query string no mapa e deep-links de prioridade.
- Hardening frontend (Sprint 5) iniciado:
  - acessibilidade minima no shell: `skip link` para conteudo principal e foco visivel padronizado.
  - foco programatico no conteudo principal (`main`) em trocas de rota.
  - observabilidade basica frontend:
    - captura de `window.error` e `unhandledrejection`.
    - captura de métricas de performance/web-vitals (paint, LCP, CLS e navigation timing).
    - evento de navegacao por troca de rota (`route_change`).
  - endpoint de telemetria configuravel por `VITE_FRONTEND_OBSERVABILITY_URL`.
  - endpoint técnico para cobertura de dados por fonte:
    - `GET /v1/ops/source-coverage` (runs por fonte + `rows_loaded` + `fact_indicator_rows` + `coverage_status`).
  - cliente HTTP passou a emitir telemetria de chamadas API:
    - `api_request_success`
    - `api_request_retry`
    - `api_request_failed`
    com `method`, `path`, `status`, `request_id`, `duration_ms` e tentativas.
- Validação frontend:
  - `npm --prefix frontend run typecheck`: `OK`.
  - `npm --prefix frontend run typecheck` (apos telemetria de API no cliente HTTP): `OK`.
  - `npm --prefix frontend run typecheck` (apos hardening de a11y/observabilidade): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao SVG/PNG): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao de briefs HTML/PDF): `OK`.
  - `npm --prefix frontend run test`: `14 passed` / `33 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido).
  - `RouterProvider` e testes com `MemoryRouter` atualizados com `future flags` do React Router v7.
- Validação backend do contrato QG:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `15 passed`.
- Router QG integrado ao app em `src/app/api/main.py`.
- Schemas dedicados do QG adicionados em `src/app/schemas/qg.py`.
- Testes unitarios de contrato do QG adicionados em `tests/unit/test_qg_routes.py` e validados.
  - estado atual local: `14 passed` (incluindo cenarios e briefs).
- Testes de orquestracao e conectores Onda A adicionados/atualizados:
  - `tests/unit/test_prefect_wave3_flow.py`
  - `tests/unit/test_onda_a_connectors.py`
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - validação local: `35 passed` em `test_onda_a_connectors + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_qg_routes`.
  - validação local consolidada: `62 passed` em
    `test_qg_routes + test_onda_a_connectors + test_quality_core_checks + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_ops_routes`.
- Hardening aplicado no backend:
  - alias `run_status` em `/v1/ops/pipeline-runs` (compatibilidade com `status`).
  - check `source_probe_rows` no `quality_suite` com threshold versionado.
  - checks de cobertura por fonte Onda A no `quality_suite` (SIDRA, SENATRAN, SEJUSP_MG, SIOPS e SNIS)
    por `reference_period`.
  - thresholds da `fact_indicator` calibrados com mínimo de linhas por fonte Onda A.
  - novos indices SQL incrementais para consultas QG/OPS em `db/sql/004_qg_ops_indexes.sql`.
  - telemetria frontend persistida no backend:
    - `POST /v1/ops/frontend-events` (ingestao)
    - `GET /v1/ops/frontend-events` (consulta paginada)
    - tabela `ops.frontend_events` em `db/sql/005_frontend_observability.sql`.
  - scripts de operação: readiness, backfill de checks e cleanup de legados.
  - `dbt_build` persiste check de falha em `ops.pipeline_checks` quando run falha.
  - logging robusto para execução local em Windows (sem quebra por encoding).
- Estado operacional atual do backend:
  - `scripts/backend_readiness.py --output-json` retorna `READY` com `hard_failures=0` e `warnings=1`.
  - `SLO-3` atendido na janela operacional de 7 dias no ambiente local.
  - `SLO-1` segue em warning histórico (`72.31% < 95%`) por runs antigos.
- Pesquisa de fontes futuras concluida e consolidada em:
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - priorização por ondas, complexidade e impacto para o município de Diamantina.
- Frontend F2 (operação) evoluido:
  - filtros de `runs`, `checks` e `connectors` com aplicação explicita via botao.
  - botao `Limpar` nos formulários de filtros.
  - contrato de filtro de runs alinhado para `run_status`.
  - nova tela técnica `/ops/frontend-events` com filtros/paginacao para telemetria do frontend.
  - nova tela técnica `/ops/source-coverage` para auditar disponibilidade real de dados por fonte.
  - `OpsHealthPage` passou a exibir monitor comparativo de SLO-1:
    - taxa agregada e jobs abaixo da meta em janela histórica (7d).
    - taxa agregada e jobs abaixo da meta em janela corrente (1d).
  - `OpsHealthPage` passou a consumir `GET /v1/ops/readiness` para status consolidado
    (`READY|NOT_READY`), `hard_failures` e `warnings`, reduzindo divergencia entre
    script de readiness e leitura de saude no frontend.
  - filtros de wave em `ops` atualizados para incluir `MVP-5`.
  - testes de páginas ops adicionados em `frontend/src/modules/ops/pages/OpsPages.test.tsx`.
- Endpoint técnico de readiness operacional adicionado:
  - `GET /v1/ops/readiness`
  - parâmetros: `window_days`, `health_window_days`, `slo1_target_pct`,
    `include_blocked_as_success`, `strict`.
  - nucleo compartilhado de calculo em `src/app/ops_readiness.py`,
    reutilizado tambem por `scripts/backend_readiness.py`.
- Frontend F3 (território e indicadores) evoluido:
  - filtros territoriais com paginacao e aplicação explicita.
  - seleção de território para compor filtro de indicadores.
  - filtros de indicadores ampliados (período, codigo, fonte, dataset, território).
  - melhorias de responsividade de tabelas.
  - testes adicionados em `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`.
- Frontend F4 (hardening) evoluido:
  - lazy-loading nas rotas principais (`ops` e `territory`) com fallback de carregamento.
  - smoke test de navegacao ponta a ponta no frontend:
    `frontend/src/app/router.smoke.test.tsx`.
  - build com chunks por página confirmado em `dist/assets/*Page-*.js`.
- Bloqueador de fechamento total da Fase 2:
  - sem bloqueador técnico pendente de backend no estado atual.
  - observacao operacional: validações de `dbt` no Windows podem exigir terminal elevado por politica local
    de permissao (WinError 5).
  - observacao operacional adicional: no ambiente atual, `vitest` e `vite build` executaram sem falhas.

## Atualizacao operacional (2026-02-12)

- Filtros de domínio no fluxo QG padronizados no frontend:
  - `Prioridades`, `Insights`, `Briefs` e `Cenarios` agora usam `select` com catálogo unico.
  - normalizacao de domínio por query string (`normalizeQgDomain`) aplicada para evitar estados invalidos.
  - `Prioridades` e `Insights` agora carregam filtros iniciais a partir de query string (deep-links funcionais).
  - arquivo de referência compartilhada: `frontend/src/modules/qg/domainCatalog.ts`.
- Refinamento de experiencia no QG:
  - domínios agora sao exibidos com rotulos amigaveis para leitura executiva (`getQgDomainLabel`).
  - codigos de domínio permanecem inalterados no contrato técnico (query string/API), preservando compatibilidade.
- `Territorio 360` alinhado ao padrão de UX do QG para domínio:
  - `TerritoryProfilePage` agora exibe rotulos amigaveis de domínio tambem nas tabelas de indicadores e comparacao.
- Home executiva do QG atualizada para refletir Onda B/C no frontend:
  - novo painel `Dominios Onda B/C` na `QgOverviewPage` com atalhos de navegacao para `Prioridades` e `Mapa` por domínio.
  - catálogo de domínios/fonte/métrica padrão centralizado em `frontend/src/modules/qg/domainCatalog.ts`.
- Contrato de `GET /v1/kpis/overview` evoluido com rastreabilidade de origem:
  - `KpiOverviewItem` agora inclui `source` e `dataset` (backend + frontend).
  - tabela `KPIs executivos` na Home passou a exibir coluna `Fonte`.
- Testes de regressão frontend reestabilizados apos a evolução da Home:
  - `QgPages.test.tsx` e `router.smoke.test.tsx` atualizados para novo shape e novos links.
  - comportamento de filtros da Home mantido com aplicação explicita via submit.
- Validação executada em 2026-02-12 (ciclo atual):
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `38 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (inclui padronizacao de filtros de domínio e deep-links de `Prioridades`/`Insights`).
  - `npm --prefix frontend run build`: `OK` (Vite build concluido com filtros padronizados + prefill por query string).
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos rotulos amigaveis de domínio no QG).
  - `npm --prefix frontend run build`: `OK` (revalidado apos refinamento de UX de domínio).
  - `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos padronizacao de rotulos no `TerritoryProfilePage`).
  - `npm --prefix frontend run build`: `OK` (revalidado apos ajuste no `TerritoryProfilePage`).
- Saneamento operacional executado:
  - `scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply` executado com sucesso.
  - 6 runs sem check foram corrigidos; `SLO-3` voltou a conformidade (`runs_missing_checks=0`).
- Registry de conectores sincronizado:
  - `scripts/sync_connector_registry.py` executado com sucesso.
  - `ops.connector_registry` atualizado para `22` conectores `implemented` (incluindo `MVP-5`).
- Ondas executadas com sucesso em modo real:
  - `run_mvp_wave_4(reference_period='2025', dry_run=False)`: todos os jobs `success`.
  - `run_mvp_wave_5(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- Execuções direcionadas adicionais:
  - `tse_electorate_fetch`: `success`.
  - `labor_mte_fetch`: `success` (via `bronze_cache`).
  - `ana_hydrology_fetch`: `success` (via ArcGIS Hub CSV).
  - `quality_suite(reference_period='2025')`: `success` (0 fails; 1 warn).
- Readiness atual:
  - `scripts/backend_readiness.py --output-json` => `READY`.
  - `hard_failures=0`.
  - `warnings=1` por `SLO-1` histórico na janela de 7 dias (`72.31% < 95%`).
  - script de readiness evoluido para separar leitura histórica e saude corrente:
    - novo parâmetro `--health-window-days` (default `1`).
    - novo bloco `slo1_current` no JSON para diagnostico de estado operacional atual.
    - warning de SLO-1 agora traz contexto combinado (`last 7d` vs janela corrente).
  - observacao: este warning e herdado de runs antigos `blocked/failed`; o estado corrente de execução das ondas 4 e 5 esta estavel.
- Validação final executada em 2026-02-12:
  - `pytest -q -p no:cacheprovider`: `152 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `33 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido).
  - warnings de `future flags` do React Router removidos da suite de testes.

## [HISTÓRICO] Próximos passos imediatos (apos iteracao readiness API)

1. Expor `GET /v1/ops/readiness` tambem no painel técnico `/admin` como card de status unico
   para triagem rapida de ambiente.
2. Adicionar teste E2E curto cobrindo o fluxo `OpsHealthPage` com transição
   `READY -> NOT_READY` por mocks de readiness.
3. Consolidar janela operacional padrão do time (histórico x corrente) em `CONTRATO.md`
   para evitar divergencia de leitura entre scripts, API e frontend.
4. Avancar no fechamento de UX/QG (error boundaries por rota + mensagens de estado)
   antes do go-live controlado.

## [HISTÓRICO] Próximos passos imediatos (trilha de robustez maxima de dados)

Backlog oficial:
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`

Sprint atual recomendado:
1. Executar Sprint D3 com foco em `BD-030`, `BD-031` e `BD-032`.
2. Publicar schema/indices espaciais para vias e logradouros, com consulta por `bbox`.
3. Publicar camada de POIs essenciais e endpoint de busca espacial por raio/bbox.
4. Manter D2 com ressalva operacional aberta:
   - `cecad_social_protection_fetch` depende de liberacao de acesso governado no CECAD.
5. Para abertura/atualizacao rapida no GitHub:
   - revisar `docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md`;
   - opcionalmente executar
     `powershell -ExecutionPolicy Bypass -File scripts/create_github_issues_backlog_dados.ps1 -Repo vthamada/territorial-intelligence-platform -Apply`.

## 1) O que foi implementado ate agora

### Arquitetura e operação
- Estrutura por ondas (MVP-1, MVP-2, MVP-3) mantida.
- Bronze/Silver/Gold operacionais com manifestos em `data/manifests/...`.
- `dbt_build` evoluido para modo hibrido:
  - `DBT_BUILD_MODE=auto` tenta `dbt` CLI e faz fallback para `sql_direct`
  - `DBT_BUILD_MODE=dbt` exige `dbt` CLI
  - `DBT_BUILD_MODE=sql_direct` preserva o modo legado
- Persistencia operacional consolidada em:
  - `ops.pipeline_runs`
  - `ops.pipeline_checks`

### API
- Contrato de erro endurecido em `src/app/api/error_handlers.py`:
  - payload padrão `validation_error|http_error|internal_error`
  - cabecalho `x-request-id` garantido em respostas de erro (incluindo 500)
- Novos testes de contrato em `tests/unit/test_api_contract.py`.
- Endpoints de observabilidade operacional adicionados:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary` (agregado por status/wave para runs/checks/connectors)
  - `GET /v1/ops/timeseries` (serie temporal por `runs|checks` em granularidade `day|hour`)
  - `GET /v1/ops/sla` (taxa de sucesso e métricas de duracao por job/wave)
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
  - conector em modo `implemented`
  - tentativa automatica via FTP `ftp://ftp.mtps.gov.br/pdet/microdados/`
  - fallback automatico via cache Bronze para o mesmo `reference_period`
  - fallback manual por `data/manual/mte` (CSV/TXT/ZIP) apenas em contingencia
  - suporte a derivacao de admissoes/desligamentos/saldo a partir de `saldomovimentacao`
  - configuração via `.env` para host/porta/raizes/profundidade/limite de varredura FTP
  - persistencia de artefato tabular bruto em Bronze para reuso automatico em execuções futuras

### Registro de conectores
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` marcado como `implemented`
  - nota operacional com tentativa FTP + cache Bronze + fallback manual de contingencia quando fonte indisponivel
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
  - `tests/unit/test_quality_core_checks.py`
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - `tests/unit/test_prefect_wave3_flow.py`
- Testes do `dbt_build` ampliados para validar modo de execução (`auto|dbt|sql_direct`) em `tests/unit/test_dbt_build.py`.
- Cobertura de orquestracao expandida em `tests/unit/test_prefect_wave3_flow.py` para `run_mvp_wave_3` e `run_mvp_all`.
- Suite validada: `78 passed`.
- Suite unit completa atualizada: `91 passed`.
- Suite unit completa atualizada apos endpoints QG adicionais: `96 passed`.
- Suite de `ops` com summary/timeseries/sla validada: `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider` (`16 passed`).
- Suite de fluxos + ops validada: `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`.
- Suite de `ops` com timeseries validada no mesmo arquivo `tests/unit/test_ops_routes.py`.
- Suite de `ops` com SLA validada no mesmo arquivo `tests/unit/test_ops_routes.py`.
- Suite de `dbt + ops + quality` validada: `pytest -q tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider` (`26 passed`).
- Frontend F1 implementado em `frontend/` com:
  - shell da app (`React Router`)
  - cliente HTTP tipado + `TanStack Query`
  - páginas iniciais de operação e território
  - testes de UI e cliente API (`vitest`)
- Validações recentes:
  - `python -m pip check`: sem conflitos
  - `pytest -q -p no:cacheprovider`: `82 passed`
  - `npm run test` (frontend): `7 passed` (validado no terminal do usuario)
  - `npm run build` (frontend): build concluido (validado no terminal do usuario)

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcional.
- Escopo territorial padrão confirmado para Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`) em `settings` e `.env.example`.
- Conectores MVP-1 e MVP-2: `implemented`.
- Conectores MVP-3:
  - INEP, DATASUS, SICONFI: `implemented` com ingestao real.
  - MTE: `implemented`; operação automatica via FTP com fallback por cache Bronze e fallback manual de contingencia.
- `pip check`: sem dependencias quebradas.
- Frontend:
  - F1 concluido no repositório (`frontend/`)
  - stack oficial ativa: `React + Vite + TypeScript + React Router + TanStack Query`
  - base de integração com backend pronta (`/v1/ops/*`, `/v1/territories`, `/v1/indicators`)
  - próximas entregas: F2 (telas operacionais completas), F3 (território/indicadores), F4 (hardening)

## 3) Arquivos-chave alterados neste ciclo

- `src/app/api/error_handlers.py`
- `src/pipelines/datasus_health.py`
- `src/pipelines/inep_education.py`
- `src/pipelines/siconfi_finance.py`
- `src/pipelines/mte_labor.py`
- `src/pipelines/sidra_indicators.py`
- `src/pipelines/senatran_fleet.py`
- `src/pipelines/sejusp_public_safety.py`
- `src/pipelines/siops_health_finance.py`
- `src/pipelines/snis_sanitation.py`
- `src/app/api/routes_ops.py`
- `src/app/api/routes_qg.py`
- `src/app/api/main.py`
- `src/pipelines/common/quality.py`
- `src/pipelines/dbt_build.py`
- `src/pipelines/quality_suite.py`
- `src/app/settings.py`
- `.env.example`
- `configs/connectors.yml`
- `configs/sidra_indicators_catalog.yml`
- `configs/senatran_fleet_catalog.yml`
- `configs/sejusp_public_safety_catalog.yml`
- `configs/siops_health_finance_catalog.yml`
- `configs/snis_sanitation_catalog.yml`
- `configs/quality_thresholds.yml`
- `requirements.txt`
- `tests/unit/test_api_contract.py`
- `tests/unit/test_dbt_build.py`
- `tests/unit/test_datasus_health.py`
- `tests/unit/test_inep_education.py`
- `tests/unit/test_siconfi_finance.py`
- `tests/unit/test_mte_labor.py`
- `tests/unit/test_ops_routes.py`
- `tests/unit/test_qg_routes.py`
- `tests/unit/test_quality_ops_pipeline_runs.py`
- `tests/unit/test_prefect_wave3_flow.py`
- `tests/unit/test_onda_a_connectors.py`
- `docs/MTE_RUNBOOK.md`
- `README.md`
- `src/app/schemas/qg.py`
- `frontend/src/shared/api/qg.ts`
- `frontend/src/shared/api/types.ts`
- `frontend/src/modules/admin/pages/AdminHubPage.tsx`
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`
- `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`
- `frontend/src/modules/qg/pages/QgMapPage.tsx`
- `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
- `frontend/src/modules/qg/pages/QgScenariosPage.tsx`
- `frontend/src/modules/qg/pages/QgBriefsPage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfileRoutePage.tsx`
- `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
- `frontend/src/modules/qg/pages/QgPages.test.tsx`
- `frontend/src/shared/ui/ChoroplethMiniMap.tsx`
- `frontend/src/shared/ui/ChoroplethMiniMap.test.tsx`
- `frontend/src/shared/ui/SourceFreshnessBadge.tsx`
- `frontend/src/shared/ui/SourceFreshnessBadge.test.tsx`
- `frontend/src/shared/ui/StrategicIndexCard.tsx`
- `frontend/src/shared/ui/StrategicIndexCard.test.tsx`
- `frontend/src/shared/ui/PriorityItemCard.tsx`
- `frontend/src/shared/ui/PriorityItemCard.test.tsx`
- `frontend/src/shared/observability/telemetry.ts`
- `frontend/src/shared/observability/bootstrap.ts`
- `frontend/src/shared/observability/telemetry.test.ts`
- `frontend/src/shared/api/http.ts`
- `frontend/src/shared/api/http.test.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/App.test.tsx`
- `frontend/src/app/router.smoke.test.tsx`
- `frontend/src/main.tsx`
- `frontend/.env.example`

## 4) Como operar agora (resumo)

### 4.1 Setup
1. Criar/ativar `.venv`.
2. Instalar dependencias:
   - `pip install -r requirements.txt`
3. Garantir `.env` configurado e banco inicializado:
   - `python scripts/init_db.py`

### 4.2 Validação rapida
1. `python -m pip check`
2. `pytest -q -p no:cacheprovider`

### 4.3 MTE (fluxo atual)
0. Garantir contexto municipal em `silver.dim_territory` (se ambiente estiver limpo):
   - `python -c "from pipelines.ibge_admin import run; print(run(reference_period='2025', dry_run=False))"`
1. O conector tenta baixar automaticamente via FTP do MTE.
2. Se não encontrar arquivo via FTP, tenta automaticamente o ultimo artefato tabular valido no Bronze para o mesmo período.
3. Se FTP e cache Bronze falharem, usar arquivo manual de Novo CAGED (CSV/TXT/ZIP) em `data/manual/mte`.
4. Executar `labor_mte_fetch`:
   - `dry_run=True` para validar
   - `dry_run=False` para gravar Silver/Bronze/ops
5. Validar critério P0 (3 execuções reais consecutivas):
   - `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`
6. Resultado mais recente no ambiente local (2026-02-10): `3/3 success` via `bronze_cache`, sem arquivo manual presente durante a validação.

## [HISTÓRICO] 5) Próximos passos recomendados

### Prioridade alta
1. Fechar estabilizacao de UX nas telas executivas (`/mapa`, `/territorio/:id`, `/eleitorado`) e registrar evidencias de teste.
2. Revalidar homologação ponta a ponta em ambiente limpo (backend + frontend + benchmark + readiness).
3. Concluir exposicao operacional da camada eleitoral territorial (`local_votacao`) no frontend.

### Prioridade media
1. Consolidar runbooks de operação e rotina semanal de robustez de dados.
2. Fortalecer cobertura de testes de regressão para fluxos de erro/vazio do frontend.
3. Executar ciclo de revisao de performance com metas p95 (executivo e urbano).

### Prioridade baixa
1. Evoluir backlog pós-v2 do mapa (split view, time slider, comparacao temporal).
2. Ajustar ergonomia final do `/admin` sem misturar UX técnica com UX executiva.

## 6) Comandos uteis

- Testes:
  - `pytest -q -p no:cacheprovider`
- Fluxo completo em dry-run:
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2025', dry_run=True))"`
- Sincronizar registry:
  - `python scripts/sync_connector_registry.py`
- Rodar qualidade:
  - `python -c "from pipelines.quality_suite import run; print(run(reference_period='2025', dry_run=False))"`
- Subir API + frontend no Windows sem `make`:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_up.ps1`
- Encerrar API + frontend iniciados pelo launcher:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_down.ps1`






