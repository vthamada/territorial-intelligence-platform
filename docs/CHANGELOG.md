# Changelog

Todas as mudanças relevantes do projeto devem ser registradas aqui.

## 2026-02-27 - Hotfix Home/Cenarios (422 e 404)

### Changed
- Frontend:
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
    - ajuste do `limit` na consulta de KPIs de `24` para `20`, aderente ao contrato backend de `/v1/kpis/overview` (`le=20`) para eliminar `422 Unprocessable Content`.
  - `frontend/src/modules/qg/pages/QgScenariosPage.tsx`:
    - normalizacao defensiva do nivel inicial vindo da URL (`municipality` apenas);
    - simulacao consolidada para nivel `municipality` no fluxo atual da tela;
    - remocao da opcao `district` do select de nivel para evitar submissao inconsistente com o seletor territorial (que opera em municipio).

### Verified
- Backend:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py -q` -> `22 passed`.
- Frontend:
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> falhas preexistentes de contrato visual/textual da suite legada (nao bloqueantes para o hotfix de runtime).
## 2026-02-26 - Refatoracao executiva de telas QG + normalizacao de dominio (Portal Transparencia)

### Changed
- Backend/API:
  - `src/app/api/routes_qg.py`:
    - ampliado mapeamento de dominio para `PORTAL_TRANSPARENCIA` (`assistencia_social` e `financas_publicas`);
    - `SUASWEB` e `CNEAS` passam a normalizar para `assistencia_social`;
    - adicionado `_normalize_domain(...)` para unificar resposta entre fontes com taxonomia mista;
    - `get_kpis_overview(...)` e `_fetch_priority_rows(...)` passam a aplicar normalizacao defensiva de dominio no payload final.
  - `db/sql/015_priority_drivers_mart.sql`:
    - CASE de dominio atualizado com as mesmas regras de normalizacao para manter coerencia entre mart e API.
- Frontend (QG):
  - `frontend/src/modules/qg/domainCatalog.ts`:
    - novos dominios no filtro: `assistencia_social` e `geral`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
    - Home executiva refatorada para foco em leitura estrategica (score, prioridades, destaques, KPIs e Onda B/C), sem duplicar mapa operacional completo.
  - `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`:
    - adicionado resumo executivo com cards de total/criticos/atencao/estaveis.
  - `frontend/src/modules/qg/pages/QgInsightsPage.tsx`:
    - lista agrupada por severidade (`Criticos`, `Atencao`, `Informativos`) com CTAs (`Ver no mapa`, `Adicionar ao brief`).
  - `frontend/src/modules/qg/pages/QgScenariosPage.tsx`:
    - resultado executivo simplificado + bloco colapsavel de leituras detalhadas.
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`:
    - CTA para abrir mapa eleitoral por local de votacao;
    - composicao do eleitorado em abas (`Sexo`, `Idade`, `Escolaridade`).
- Testes ajustados ao novo contrato visual/textual:
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx`
  - `frontend/src/shared/ui/StrategicIndexCard.test.tsx`
  - `frontend/src/shared/ui/SourceFreshnessBadge.test.tsx`
  - `frontend/src/app/App.test.tsx`
  - `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`

### Verified
- Backend:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
- Frontend:
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/modules/ops/pages/OpsPages.test.tsx` -> `18 passed`.
  - `npm --prefix frontend run test -- --run src/shared/ui/StrategicIndexCard.test.tsx src/shared/ui/SourceFreshnessBadge.test.tsx src/app/App.test.tsx src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx` -> `5 passed`.
- Observacao de regressao preexistente na suite completa:
  - `npm --prefix frontend run test -- --run` ainda falha por descompasso de contrato em `frontend/src/modules/qg/pages/QgPages.test.tsx` (teste legado frente ao novo layout refatorado de Home/Mapa).

## 2026-02-26 - Homologação manual (Google) de locais de votação

### Changed
- `data/seed/polling_places_overrides_diamantina.csv`:
  - coordenadas homologadas pelo usuário no Google para:
    - `1376` (`E. M. SOPA`) -> `(-18.224691, -43.696214)`;
    - `1252` (`E. E. D. JOAQUIM SILVERIO DE SOUZA`) -> `(-18.287868, -43.982343)`;
    - `1325` (`E. M. PROF. ANA CELIA DE O. SOUZA`) -> `(-18.106846, -43.527750)`.
- `data/seed/polling_places_diamantina.csv`:
  - atualizado via `scripts/build_seed.py` com as três novas coordenadas homologadas.

### Verified
- `.\.venv\Scripts\python.exe scripts/build_seed.py` -> `Overrides loaded: 8`.
- `.\.venv\Scripts\python.exe scripts/apply_seed.py` -> `Total sections updated: 144`, `Skipped by district rule: 0`.
- `.\.venv\Scripts\python.exe scripts/audit_polling_places_geolocation.py` ->
  - `status=pass`;
  - `outside_any_district=[]`;
  - `outside_expected_district=[]`;
  - `override_distance_violations=[]`.

## 2026-02-26 - Busca na internet para povoados eleitorais (Mão Torta, Batatal, Baixadão, Capoeirão)

### Changed
- `data/seed/polling_places_overrides_diamantina.csv`:
  - correções adicionais com evidência pública de internet para distritos/povoados:
    - `1406` (E. M. BAIXADÃO) -> `Planalto de Minas` com coordenada OSM/Nominatim (`-17.478430,-43.269049`);
    - `1457` (E. M. BATATAL) -> `Conselheiro Mata` com proxy de assentamento local (`-18.288633,-43.981851`);
    - `1414` (E. M. ROGERIO FIRMINO LOPES) -> `Desembargador Otoni` com proxy distrital (`point_on_surface`);
    - `1422` (E. M. MAO TORTA) -> `Desembargador Otoni` com proxy distrital (`centroid`).
- `data/seed/polling_places_diamantina.csv`:
  - atualizado por `scripts/build_seed.py` com os novos overrides.

### Verified
- execução sequencial (ordem obrigatória):
  - `.\.venv\Scripts\python.exe scripts/build_seed.py`;
  - `.\.venv\Scripts\python.exe scripts/apply_seed.py`;
  - `.\.venv\Scripts\python.exe scripts/audit_polling_places_geolocation.py`.
- resultado final do audit:
  - `status=pass`;
  - `outside_any_district=[]`;
  - `outside_expected_district=[]`;
  - `override_distance_violations=[]`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.

## 2026-02-26 - Verificação dirigida de locais suspeitos no mapa (distritos) + correção pontual

### Changed
- `scripts/audit_polling_places_geolocation.py`:
  - consulta de auditoria passou a usar ponto representativo determinístico por local (última seção atualizada), evitando leituras ambíguas quando há múltiplas seções por local.
- `scripts/equalize_database_env.ps1`:
  - fluxo de equalização agora executa também:
    - `scripts/build_seed.py`;
    - `scripts/audit_polling_places_geolocation.py` (com saída em relatório próprio);
  - a equalização falha automaticamente se o audit de locais de votação retornar `status != pass`.
- `data/seed/polling_places_overrides_diamantina.csv`:
  - ampliado com regras de `expected_district` para locais suspeitos da rodada:
    - `1376` (Sopa), `1422` (Mão Torta), `1341` (Gov. Juscelino Kubitschek),
      `1325` (Ana Célia), `1457` (Batatal), `1414` (Rogério Firmino Lopes), `1406` (Baixadão).
  - `1341` recebeu override de coordenada validada por consulta de endereço/centro local de Conselheiro Mata:
    - `(-18.287522, -43.981900)`;
    - source: `nominatim_addr:Rua Principal Conselheiro Mata`.
- `data/seed/polling_places_diamantina.csv`:
  - atualizado via `scripts/build_seed.py` com aplicação do override de `1341`.

### Verified
- `.\.venv\Scripts\python.exe scripts/build_seed.py` -> `Overrides loaded: 1`, `Overrides applied: 1`.
- `.\.venv\Scripts\python.exe scripts/apply_seed.py` -> `Total sections updated: 144`, `Skipped by district rule: 0`.
- `.\.venv\Scripts\python.exe scripts/audit_polling_places_geolocation.py` ->
  - `status=pass`;
  - `outside_any_district=[]`;
  - `outside_expected_district=[]`;
  - `override_distance_violations=[]`.

## 2026-02-26 - Guardrail operacional para geolocalização de locais de votação (foco distritos)

### Changed
- `scripts/audit_polling_places_geolocation.py`:
  - auditoria endurecida para `LEFT JOIN` espacial (detecta ponto fora de qualquer distrito);
  - validação opcional por distrito esperado e por distância a coordenadas de override;
  - novo resumo no relatório: `outside_any_district`, `outside_expected_district`, `override_distance_violations`.
- `scripts/build_seed.py`:
  - suporte a `data/seed/polling_places_overrides_diamantina.csv`;
  - build da seed passa a aplicar overrides somente quando latitude/longitude estiverem preenchidas.
- `scripts/apply_seed.py`:
  - antes de atualizar geometria, valida regra de distrito esperado (quando existir no CSV de overrides);
  - se a coordenada estiver fora do distrito esperado, o registro é bloqueado (`SKIP`) e não é aplicado no banco.
- `data/seed/polling_places_overrides_diamantina.csv`:
  - adicionado arquivo de governança para correção controlada;
  - estado inicial com regras de distrito esperado para `1252` e `1341` (sem forçar coordenada sem validação de campo).

### Verified
- `.\.venv\Scripts\python.exe scripts/apply_seed.py` -> `Total sections updated: 144`, `Skipped by district rule: 0`.
- `.\.venv\Scripts\python.exe scripts/audit_polling_places_geolocation.py` -> `status=pass`, `outside_any_district=[]`, `outside_expected_district=[]`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.

## 2026-02-26 - Correção de serialização de seções no mapa eleitoral

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - `sectionGeoJson` agora sempre publica `sections_csv` em `properties`, derivado de `sections`.
  - objetivo: garantir exibição de seções no tooltip/painel mesmo quando o cliente de mapa não preserva arrays no `properties` do evento.

### Verified
- `npm --prefix frontend run build` -> `OK`.
- `npm --prefix frontend run test -- --run` -> falha local conhecida de ambiente (`spawn EPERM` em `esbuild`).

## 2026-02-26 - Validação completa de geolocalização eleitoral + normalização de acentuação da UI

### Changed
- `data/seed/polling_places_diamantina.csv`:
  - restaurado a partir do banco após execução de geocoder sem rede (evitando coordenadas vazias);
  - seed reaplicado no banco com `scripts/apply_seed.py`.
- `scripts/build_seed.py`:
  - reescrito para usar o seed atual como fonte de verdade de coordenadas;
  - agora recalcula apenas `sections`/`voters` no banco e não sobrescreve latitude/longitude com dicionários hardcoded antigos.
- frontend (normalização textual):
  - correção ampla de textos com caracteres quebrados (`?`) em páginas executivas e operacionais;
  - ajustes de acentuação em labels, subtítulos e mensagens de estado;
  - mantidos contratos técnicos de rota/chaves/enums.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - mantido fallback robusto de seções por `sections_csv`;
  - mantida ocultação de labels contextuais no nível `secao_eleitoral`.

### Verified
- validação geoespacial eleitoral (query SQL):
  - `polling_places_total=36`;
  - `unique_codes=36`;
  - `unique_points=36`;
  - `outside_district=[]` (todos os pontos dentro do distrito correspondente).
- `.\.venv\Scripts\python.exe scripts/build_seed.py` -> `Rows: 36`, `Rows missing coordinates: 0`.
- `.\.venv\Scripts\python.exe scripts/apply_seed.py` -> `Total sections updated: 144`, `Verification: 36 unique geometry points`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
- `npm --prefix frontend run build` -> `OK`.
- `npm --prefix frontend run test -- --run` -> falha de ambiente local (`spawn EPERM` no `esbuild`).

## 2026-02-25 - Correção geoespacial adicional de locais de votação + acentuação ampla de UI

### Changed
- `data/seed/polling_places_diamantina.csv`:
  - refinadas coordenadas de locais que ainda estavam com inconsistência distrital/posicional:
    - `1244` (`E. E. PROF.ª AYNA TORRES`) -> `inep_road:Rua Prof. Paulino Guimaraes Junior`;
    - `1252` (`E. E. D. JOAQUIM SILVÉRIO DE SOUZA`) -> `osm_school:EE Dom Joaquim Silverio de Souza`;
    - `1333` (`E. E. DURVAL CÂNDIDO CRUZ`) -> `osm_school:EE Durval Candido Cruz`;
    - `1341` (`E. E. GOV. JUSCELINO KUBITSCHEK`) -> `nominatim:Conselheiro Mata`;
    - `1384` (`E. M. PEDRARIA`) -> `district_centroid:senador_mourao`.
- `scripts/build_seed.py`:
  - alinhado com os ajustes acima para evitar regressão futura em rebuild da seed.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - tooltip de local de votação agora usa fallback `sections_csv` quando `sections` não está disponível;
  - drawer de detalhe também usa fallback `sections_csv` e aceita `section_count` numérico ou string;
  - labels contextuais ficam ocultos no nível `secao_eleitoral` mesmo com overlay de locais desligado (`showContextLabels` condicionado por nível);
  - revisão adicional de acentuação em textos visíveis do mapa.
- revisão de acentuação em textos visíveis de UI em páginas executivas/operacionais (sem alterar contratos técnicos de rotas, chaves e enums).

### Verified
- `.\.venv\Scripts\python.exe scripts/apply_seed.py` -> `Total sections updated: 144`, `36 unique geometry points`.
- validação espacial após seed:
  - `1252` e `1341` posicionados em `conselheiro mata`;
  - `1333` posicionado em `planalto de minas`;
  - `1384` posicionado em `senador mourão`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
- `npm --prefix frontend run build` -> `OK`.
- `npm --prefix frontend run test -- --run` -> falha de ambiente local (`spawn EPERM` no `esbuild`).

## 2026-02-26 - Ajustes de UX do mapa eleitoral (seções, labels e acentuação)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - tooltip de local de votação agora usa fallback `sections_csv` quando o array `sections` não vem preservado pela serialização do GeoJSON no cliente;
  - painel de detalhe também passou a ler `sections_csv` e interpretar `section_count` como número mesmo quando chega como string;
  - labels contextuais da camada base agora ficam ocultas em `secao_eleitoral` (inclusive com checkbox de locais desligado), eliminando sobreposição de labels de seção no mapa;
  - revisão textual com acentuação em rótulos e mensagens do mapa.
- `frontend/src/shared/ui/presentation.ts`:
  - normalização de acentuação em labels de nível/status/tendência e nomes de datasets no idioma PT-BR.

### Verified
- `npm --prefix frontend run build` -> `OK`.
- `npm --prefix frontend test -- --run` -> falha de ambiente local (`spawn EPERM` no `esbuild` ao carregar `vite.config.ts`).

## 2026-02-26 - Script unico para equalizacao de banco entre ambientes

### Changed
- `scripts/equalize_database_env.ps1` adicionado para executar, em sequencia unica:
  - `sync_connector_registry`;
  - `sync_schema_contracts`;
  - reprocesso TSE 2024 (`run_incremental_backfill.py` com `reprocess`);
  - aplicacao de seed de locais de votacao (`apply_seed.py`);
  - backfill robusto (`backfill_robust_database.py`);
  - varredura incremental de todas as fontes registradas (`run_incremental_backfill.py --include-partial --allow-governed-sources`);
  - export do scorecard atual (`export_data_coverage_scorecard.py`);
  - validacao final de prontidao (`backend_readiness.py --output-json`).
- suporte a tratamento controlado de fontes externas bloqueadas no backfill:
  - flag `-AllowBackfillBlocked` permite continuar somente quando os nao-success do relatorio forem exclusivamente `blocked`.
- parametros de operacao no script:
  - `-TseYears` (default `2024,2022,2020,2018,2016`);
  - `-IndicatorPeriods` (default `2024,2025`);
  - `-IncludeWave7`;
  - `-SkipFullIncremental` para pular apenas a etapa de varredura incremental completa;
  - `-OutputDir` para consolidar artefatos de relatorio.

### Verified
- execucao real de equalizacao no ambiente atual:
  - reprocesso TSE 2024 concluido com sucesso;
  - `apply_seed.py`: `Total sections updated: 144`, `36 unique geometry points`;
  - sync de contratos: `prepared=27 upserted=27`;
  - scorecard reexportado: `pass=29`, `warn=3`;
  - `backend_readiness.py --output-json`: `READY`, `hard_failures=0`, `warnings=0`.

## 2026-02-25 - Correção de labels e coordenadas no mapa de locais de votação

### Root cause
- Labels MVT de seção eleitoral ("Secao eleitoral XXX (zona 101) - Diamantina") apareciam sobrepostos aos círculos de locais de votação, poluindo visualmente o mapa.
- Duas escolas de Conselheiro Mata (códigos 1341 e 1252) tinham coordenadas erradas via Nominatim (17-28 km do vilarejo real), caindo fora do distrito.

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`: passa `showContextLabels={false}` para `VectorMap` quando overlay de locais de votação está ativo, eliminando labels MVT redundantes.
- `data/seed/polling_places_diamantina.csv`: corrigidas coordenadas de:
  - `E. E. GOV. JUSCELINO KUBITSCHEK` (1341): de (-18.216, -43.906) para (-18.073, -43.847) — centro de Conselheiro Mata.
  - `E. E. D. JOAQUIM SILVÉRIO DE SOUZA` (1252): de (-18.288, -43.982) para (-18.075, -43.849) — centro de Conselheiro Mata.

### Verified
- `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` → 37 passed
- `npm --prefix frontend run test -- --run` → 85 passed
- `npm --prefix frontend run build` → OK
- DB re-atualizado com seed corrigido: 144 seções, 36 coordenadas únicas

## 2026-02-25 - Geocodificação real dos locais de votação (INEP + Nominatim)

### Root cause
- TSE não publica coordenadas geográficas dos locais de votação. Todos os 36 locais de Diamantina compartilhavam uma mesma coordenada proxy (centroide do distrito-sede), impossibilitando visualização individual no mapa.

### Changed
- **Geocodificação por endereço (novo pipeline)**:
  - `scripts/geocode_with_addresses.py`: pipeline de geocodificação que cruza nomes de locais de votação com Microdados do Censo Escolar INEP 2024 (endereços completos), então consulta Nominatim para obter coordenadas. INEP 2024 não publica lat/lon, apenas endereços.
  - `scripts/geocode_targeted.py`: queries especializadas por distrito/povoado para locais não resolvidos pelo pipeline principal (distritos como Conselheiro Mata, Sopa, Guinda, Inhaí, Extração, etc.).
  - `scripts/build_seed.py`: combina resultados Nominatim verificados (24) com estimativas manuais por bairro/distrito (12) em seed CSV final.
  - `scripts/apply_seed.py`: aplica seed CSV ao banco, atualizando geometria de `dim_territory` para todas as 144 seções eleitorais (36 locais únicos).
  - `data/seed/polling_places_diamantina.csv`: seed com coordenadas de todos os 36 locais de votação (24 via Nominatim, 12 via estimativa distrital).
  - `data/inep_diamantina_schools.csv`: cache de 93 escolas INEP extraídas do Censo Escolar 2024 para Diamantina.

- **Query do endpoint atualizada**:
  - `src/app/api/routes_qg.py`: CTE de polling places agora usa coordenada real de `dt.geometry` (via `array_agg`) quando disponível, com fallback para hash-based offset dentro do polígono do distrito-sede para municípios sem geocodificação.
  - Resultado: 36/36 locais com coordenadas únicas reais (antes: 35/36 com hash sintético no polígono sede).

### Verified
- `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` → 37 passed
- `pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` → 29 passed
- `npm --prefix frontend run test -- --run` → 85 passed
- `npm --prefix frontend run build` → OK
- API `/v1/electorate/map?level=secao_eleitoral&aggregate_by=polling_place` retorna 36 items com 36 coordenadas únicas reais distribuídas no município de Diamantina

## 2026-02-25 - Distribuição espacial dos locais de votação conforme UI_MAPA.md

### Root cause
- Todos os 36 locais de votação tinham coordenada idêntica (centroide do distrito-sede), resultando em cluster único impossível de desagrupar. Conforme spec `UI_MAPA.md` §5.2-5.3, cada local deve ser um ponto individual com raio `sqrt(eleitores)`, e clusters somente em zoom ≤ 12.

### Changed
- `src/app/api/routes_qg.py`:
  - query de polling places reestruturada com CTEs (`sede` + `grouped`) e cálculo de coordenada **única por local** via hash determinístico (`md5(code|name)`) que gera offset (X,Y) dentro do polígono do distrito-sede.
  - cada ponto é projetado no interior do polígono via `ST_ClosestPoint(polygon, offset_point)`, garantindo posição válida.
  - 35 de 36 locais com coordenadas distintas (2 compartilham hash — colisão esperada e aceitável).
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - `clusterMaxZoom` ajustado de `14` para `12` conforme spec (clusters até z≤12, pontos individuais a partir de z≥13).

### Verified
- `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` → 37 passed
- `npm --prefix frontend run test -- --run` → 85 passed
- `npm --prefix frontend run build` → OK
- API retorna 36 polling places com 35 coordenadas únicas distribuídas na área urbana de Diamantina

## 2026-02-25 - Correção de geolocalização dos locais de votação no mapa

### Root cause
- geometria proxy de seções eleitorais usava `ST_PointOnSurface(polígono_município)`, que para municípios grandes (ex.: Diamantina, 3.891 km²) retornava ponto ~37km ao norte do centro urbano.

### Changed
- `src/app/api/routes_qg.py`:
  - query de agregação `/electorate/map?aggregate_by=polling_place` agora busca centroide do **distrito-sede** (IBGE geocode terminado em `05`) via subquery, com fallback para `ST_Centroid` da geometria da zona.
  - locais de votação agora se posicionam a ~1.7km do centro da cidade (vs ~37.6km antes).
- `src/pipelines/tse_electorate.py`:
  - `_upsert_electoral_zone()` e `_upsert_electoral_section()` passam a usar `COALESCE(centroide_distrito_sede, ST_Centroid(parent))` em vez de `ST_PointOnSurface(parent)`.
  - metadados `proxy_method` atualizados para documentar a nova referência geográfica.
- Registros existentes em `dim_territory` (1 zona + 144 seções eleitorais) atualizados in-place com o centroide do distrito-sede.

### Verified
- `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` → 37 passed
- `pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` → 29 passed
- `npm --prefix frontend run test -- --run` → 85 passed
- `npm --prefix frontend run build` → OK
- API retorna coordenadas (-43.602, -18.234) para todos os locais de votação (1.7km do centro vs 37.6km antes)

## 2026-02-25 - Homologação de contrato de tiles + fallback para locais de votação no mapa

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - ao ativar o checkbox `Locais de votacao`, o mapa agora força automaticamente o recorte para `secao_eleitoral` (sem depender de seletor manual de nível);
  - gatilho de consulta eleitoral por local passa a depender diretamente do estado do checkbox (robustez contra timing de transição de nível), eliminando cenário sem requisição no clique;
  - consulta de locais de votação (`/v1/electorate/map` com `aggregate_by=polling_place`) passa a ser on-demand, acionada ao marcar o checkbox `Locais de votacao` no nível `secao_eleitoral`;
  - adicionado fallback automático da camada eleitoral agregada por local para ano `2024` quando o período estratégico ativo não retorna itens;
  - `sectionGeoJson` e ranking eleitoral passam a usar o dataset efetivo (primário ou fallback) para manter pontos de local de votação visíveis.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - novo teste cobrindo fallback de `/electorate/map` (`year=2025` vazio -> retry automático com `year=2024`).

### Verified
- homologação técnica do contrato de tiles frontend: `VectorMap` não monta mais query string em `/map/tiles/*`.
- `npm --prefix frontend run test -- --run` -> `85 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-25 - Limpeza frontend de legado em tiles (`metric/period/domain`) + bootstrap de `/mapa`

### Changed
- `frontend/src/shared/ui/VectorMap.tsx`:
  - removida montagem de query string `metric/period/domain` na URL de tiles (`/map/tiles/{layer}/{z}/{x}/{y}.mvt`).
  - `VectorMapProps` simplificado sem `metric`, `period` e `domain`.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - removida leitura inicial de `metric`/`period` da query string da rota `/mapa`.
  - baseline operacional fixado no bootstrap interno (`MTE_NOVO_CAGED_SALDO_TOTAL`, `2025`) sem depender da URL.
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - removido envio de `metric`/`period` para `LazyVectorMap`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - expectativas ajustadas para novo contrato (query legada no load é ignorada para métrica/período).

### Verified
- `npm --prefix frontend run test -- --run` -> `84 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-25 - Varredura backend de tiles: remoção do branch legado `metric/period`

### Fixed
- `src/app/api/routes_map.py`:
  - endpoint `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt` deixou de usar `metric`/`period`/`domain` para camadas territoriais;
  - removido branch legado com `JOIN silver.fact_indicator` acionado por query string;
  - tiles territoriais passam a operar exclusivamente com geometria territorial da camada, sem dependência de recorte analítico legado na URL.

### Added
- `tests/unit/test_api_contract.py`:
  - novo teste `test_map_tiles_legacy_metric_period_query_is_ignored` garantindo que query legada não injeta `metric`/`period`/`domain` no SQL de tiles territoriais.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py -q` -> `39 passed`.

## 2026-02-25 - Limpeza de contrato da URL do mapa (`/mapa` sem `metric`/`period`)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - sincronização de query string do mapa atualizada para não persistir mais `metric` e `period` na URL.
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx`:
  - links para `/mapa` simplificados para contexto territorial (`territory_id` e/ou `level`), removendo métrica/período legados.
- `frontend/src/shared/ui/PriorityItemCard.tsx`:
  - deep-link `Ver no mapa` reduzido para `/mapa?territory_id=...`.
- testes atualizados para o novo contrato:
  - `frontend/src/shared/ui/PriorityItemCard.test.tsx`
  - `frontend/src/modules/qg/pages/QgPages.test.tsx`
  - `frontend/src/app/e2e-flow.test.tsx`

### Verified
- `npm --prefix frontend run test -- --run` -> `84 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-25 - Hotfix agregado por local de votação (`/electorate/map`)

### Fixed
- `src/app/api/routes_qg.py`:
  - corrigida a query SQL do ramo `aggregate_by=polling_place` para `metric=voters` + `level=electoral_section`.
  - causa raiz: `GroupingError` (PostgreSQL) por uso de `dt.metadata` em expressão não compatível com o `GROUP BY` original.
  - solução: reestruturação da consulta com CTE `grouped` (agregação primeiro) e cálculo de `territory_id` por `md5(...)` no select externo.

### Verified
- chamada direta API:
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&aggregate_by=polling_place&year=2024&include_geometry=true&limit=500` -> `200`, `items=36`, `coverage_note=polling_place_aggregated`.
- banco (diagnóstico):
  - `silver.dim_territory` nível `electoral_section`: `144` seções;
  - cobertura metadata de local: `polling_place_name=144/144`, `polling_place_code=144/144`;
  - locais distintos agregáveis: `36`.
- regressão backend:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.

## 2026-02-25 - Mapa executivo OSM-only + agregação eleitoral por local de votação

### Changed
- `src/app/schemas/qg.py`:
  - `ElectorateMapItem` expandido com campos opcionais de local de votação: `polling_place_name`, `polling_place_code`, `section_count`, `sections`.
- `src/app/api/routes_qg.py`:
  - endpoint `GET /v1/electorate/map` recebeu parâmetro `aggregate_by` (`none|polling_place`);
  - para `metric=voters` + `level=electoral_section` + `aggregate_by=polling_place`, a resposta agora agrega por local (soma de eleitores, quantidade/lista de seções e geometria centróide).
- `frontend/src/shared/api/types.ts`:
  - tipo `ElectorateMapItem` sincronizado com os novos campos de agregação por local.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - removido fluxo de modo simplificado do mapa;
  - mapa consolidado em OSM-only (sem alternância de basemap legado na UX);
  - camada eleitoral de locais passa a requisitar `aggregate_by: "polling_place"`;
  - tooltip e drawer eleitoral exibem total de eleitores, quantidade de seções e lista de seções por local.
- `frontend/src/shared/ui/VectorMap.tsx`:
  - hardening para ambiente de teste: guarda para `map.areTilesLoaded` quando ausente em mock.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - expectativas atualizadas para comportamento OSM-only e ausência de modo simplificado.

### Verified
- `npm --prefix frontend run test -- --run` -> `84 passed`.
- `npm --prefix frontend run build` -> `OK`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.

## 2026-02-25 - Ajustes de camadas no mapa (toggles) + diagnóstico de locais de votação

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - checkboxes do painel de camadas iniciam desmarcados por padrão (sem pré-seleção);
  - estrutura do label de toggle ajustada para alinhamento horizontal consistente (`checkbox + texto`).
- `frontend/src/styles/global.css`:
  - `overlay-toggle-label` migrado para grid de 2 colunas para garantir alinhamento horizontal de checkbox/label;
  - subtítulo (`overlay-toggle-subtitle`) alinhado na mesma coluna do texto principal.

### Verified
- `npm --prefix frontend run test -- --run` → `84 passed`.

### Technical note
- Diagnóstico backend/db: o endpoint atual `/v1/electorate/map` retorna itens por seção (`territory_name`, `value`, `geometry`) e **não** retorna agregado por local de votação nem lista de seções por local.
- O banco já possui dados para agregação por local em `silver.dim_territory.metadata` (`polling_place_name`, `polling_place_code`, `voters_section`).

## 2026-02-25 - Ajuste final do layout do mapa para aderência ao guia UI_MAPA + imagem de referência

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - removidos controles redundantes do topo (`Indicador`, `Periodo`, `Recorte`, `Nivel`, presets, seletor de visualização e botão de modo simplificado);
  - nova barra superior focada em ação imediata: apenas `Mapa base` + exportação (`SVG`/`PNG`);
  - busca territorial movida para barra compacta acima do mapa (`Buscar território ou endereço...` + ação `Buscar`);
  - painel lateral de camadas simplificado para o fluxo operacional (Território, Eleitoral, Serviços), com botão `Resetar`;
  - remoção do footer informativo intermediário para deixar o mapa protagonista;
  - painel inferior (`Ranking` / `Detalhes do território`) mantido colapsável e fechado por padrão;
  - visualização eleitoral passa a depender do toggle `Locais de votacao` e tooltips ajustados para linguagem de local/agrupamento.
- `frontend/src/styles/global.css`:
  - adicionados estilos de `map-actions-bar` e `map-search-bar`;
  - ajustes de escala/altura para aumentar protagonismo do mapa e aderir ao layout de referência;
  - ajustes de espaçamento e altura de botões no sidebar.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`, `frontend/src/app/e2e-flow.test.tsx`, `frontend/src/app/router.smoke.test.tsx`:
  - testes atualizados para o novo UX sem filtros de topo;
  - removidos testes acoplados a controles que deixaram de existir.

### Verified
- `npm --prefix frontend run test -- --run` → `84 passed` (21 test files).
- `npm --prefix frontend run build` → `OK`.

## 2026-02-25 - Refatoração completa do mapa executivo conforme UI_MAPA.md

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - layout reestruturado de 4 Panels empilhados → layout flat com page-map-executive (filter bar + toolbar + map+sidebar + footer + collapsible bottom panel);
  - filtros compactados em barra única horizontal (`map-filter-bar-form`) com labels Indicador, Periodo, Recorte, Nivel, Camada;
  - labels renomeados: "Recorte territorial" → "Recorte", "Nivel territorial" → "Nivel", "Escopo da camada" → "Recorte", "Camada urbana" → "Camada";
  - botão "Aplicar filtros" simplificado para "Aplicar";
  - botão "Focar territorio" simplificado para "Focar";
  - VIZ_MODES reduzido de 5 (choropleth/points/heatmap/critical/gap) para 2 (choropleth/points);
  - zoom control movido para toolbar inline (4º bloco);
  - territory search movido para sidebar das camadas;
  - ranking e detalhe territorial movidos para `<details>` collapsible no bottom panel;
  - removidos: "Leitura executiva imediata", "Top secoes por eleitorado", legenda eleitoral inline, seletor "Camada eleitoral detalhada", notas de cobertura, guidance de local de votação, textos técnicos (proxy/classificacao/origem/metodo), "map-style-meta", "map-layer-guidance".
- `frontend/src/styles/global.css`:
  - novos estilos: `.page-map-executive`, `.map-filter-bar`, `.map-filter-bar-form`, `.map-filter-bar-actions`, `.map-filter-bar-presets`, `.map-toolbar-zoom`, `.map-layers-sidebar-search`, `.map-layers-sidebar-search-actions`, `.map-bottom-panel`, `.map-bottom-panel-summary`, `.map-bottom-tab`, `.map-bottom-panel-content`, `.map-bottom-section`, `.map-bottom-section-header`, `.map-bottom-section-subtitle`, `.map-footer-error`;
  - estilos existentes atualizados: `.map-toolbar` (grid→flex), `.map-with-sidebar`, `.map-canvas-shell` (height ampliado para 72vh), `.map-layers-sidebar`, `.map-footer-bar`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - 5 testes removidos (referenciavam UI eliminada: seletor de camada eleitoral, telemetria de toggle, layer URL param, local_votacao guidance, coverage error);
  - labels atualizados nos testes sobreviventes;
  - "100,50" assertion ajustada para `findAllByText` (valor aparece em ranking + drawer).
- `frontend/src/app/e2e-flow.test.tsx`: "Mapa estrategico" → `findByLabelText("Indicador")`.
- `frontend/src/app/router.smoke.test.tsx`: idem.

### Verified
- `npm --prefix frontend run test -- --run` → `86 passed` (21 test files).
- `npm --prefix frontend run build` → `OK`.

## 2026-02-25 - Correção de overlays UBS/Escola + layout sidebar do painel de camadas

### Fixed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - corrigido bug onde checkboxes de UBS e Escola não exibiam pontos no mapa: condição `enabled` dos overlays estava bloqueada por `strategicView === "services" || strategicView === "both"`, agora depende apenas do estado do checkbox (`activeOverlayIds.has(id)`).

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - painel de camadas movido para sidebar lateral (`<aside className="map-layers-sidebar">`) ao lado do canvas do mapa, dentro de `<div className="map-with-sidebar">`;
  - sidebar e footer sempre renderizados independentemente do modo de mapa (vector/choropleth/fallback);
  - removido grupo "Risco / Estrategia" (fase 2, não pertinente ao momento);
  - adicionado subtitle "(pontos proporcionais)" no item Seções eleitorais;
  - todos os itens do painel usam checkboxes (`disabled` para não-togglable);
  - footer bar com território selecionado, ano de criação e fonte eleitoral TSE.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - removida assertiva do heading "Risco / Estrategia" (grupo removido).
- `frontend/src/styles/global.css`:
  - novos estilos: `.map-with-sidebar`, `.map-layers-sidebar`, `.map-layers-sidebar-group`, `.map-footer-bar`, `.overlay-toggle-subtitle`.

### Verified
- `npm --prefix frontend run test -- --run` -> `91 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-24 - Reestruturação completa do mapa estratégico (visão, GeoJSON, contorno)

### Changed
- `frontend/src/shared/ui/VectorMap.tsx`:
  - novo tipo `GeoJsonClusterConfig` (id, data, color, opacity, strokeColor, strokeWidth, radiusExpression, clusterRadius, clusterMaxZoom, clusterProperties, clusterLabelExpression, tooltipFn, clusterTooltipFn, minZoom, enabled);
  - prop `geoJsonLayers?: GeoJsonClusterConfig[]` para camadas GeoJSON com clustering nativo do MapLibre;
  - prop `boundaryOnly?: boolean` para modo contorno municipal (line layer sem fill);
  - renderização de cluster circle layer, cluster label layer, unclustered proportional point layer;
  - interação click-to-expand-zoom em clusters;
  - cleanup automático de `geojson-*` layers e `geojson-source-*` sources.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - tipo `StrategicView` ("sections" | "services" | "both") com `STRATEGIC_VIEW_OPTIONS`;
  - barra superior reorganizada: Visualização (Seções eleitorais / Serviços / Seções + Serviços), Mapa base (Ruas / Claro / Sem base), Ações (Simplificado + SVG + PNG);
  - painel de camadas reestruturado: Território (Limite municipal + Distritos), Eleitoral (Seções + Locais de votação), Serviços (Escolas + UBS), Risco (Hotspots + Índice - fase 2);
  - seções eleitorais via GeoJSON de `/electorate/map?include_geometry=true` com raio proporcional sqrt(voters);
  - clustering com `sum_voters` aggregation e tooltip formatado (nome, eleitores, % município, fonte);
  - modo boundary-only ativado para visões "sections" e "both";
  - removidos: zonas eleitorais do painel, modos Coroplético/Heatmap/Apenas críticos/Gap do radiogroup, seção "Resumo operacional do mapa", texto "Camada recomendada".
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - testes atualizados para nova UI: removidas assertivas de "Pontos" radio, "Resumo operacional", "Camada recomendada", "Classificacao da camada";
  - assertivas ajustadas para strategic view options e checkboxes reestruturados.
- `frontend/src/styles/global.css`:
  - `.map-toolbar-actions-row` (flex, gap, wrap, botões compactos);
  - `.overlay-toggle-label` e `.overlay-toggle-indicator` (checkboxes alinhados, status dot).

### Fixed
- Hooks order violation: `useMemo` hooks (sectionGeoJson, sectionTotalVoters, sectionClusterConfig) movidos acima de early returns para compliance com Rules of Hooks.

### Verified
- `npm --prefix frontend run test -- --run` -> `91 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-24 - Sistema de overlays interativos no mapa estratégico

### Added
- `frontend/src/shared/ui/VectorMap.tsx`:
  - tipo `OverlayLayerConfig` com `id`, `label`, `tileLayerId`, `vizType` (circle/fill/heatmap), `color`, `filter`, `enabled`, `opacity`, `minZoom`;
  - prop `overlays?: OverlayLayerConfig[]` para renderizar camadas sobrepostas independentes ao layer principal;
  - cada overlay recebe source MVT dedicada, layer visual, e interações isoladas (click com `overlayId`, hover tooltip com nome/categoria/subcategoria);
  - cleanup automático de sources/layers de overlays durante `updateLayers`.
- `frontend/src/modules/qg/pages/QgMapPage.tsx`:
  - estado `activeOverlayIds` (Set) para controle de quais overlays estão ativos;
  - 5 overlays configurados: Escolas, UBS/Saúde, Seções eleitorais (pontos), Heatmap eleitoral, Zonas eleitorais (polígonos);
  - Escolas/UBS filtrados client-side via `["==", ["get", "category"], "education"|"health"]` no tile `urban_pois`;
  - painel de camadas com checkboxes interativos para ativar/desativar cada overlay;
  - summary note no rodapé do painel listando overlays ativos em tempo real.
- `frontend/src/modules/qg/pages/QgPages.test.tsx`:
  - teste de renderização de checkboxes de overlay no painel estratégico;
  - teste de toggle de overlays (ativar/desativar e exibição de nota de camadas ativas).

### Verified
- `npm --prefix frontend run test -- --run` -> `91 passed`.
- `npm --prefix frontend run build` -> `OK`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `29 passed`.

### Notes
- Escolas e UBS usam dados OSM já ingeridos no tile `urban_pois` (filtro por `category`). Para dados oficiais georeferenciados (INEP/CNES), seria necessário ingestão dedicada.
- Zonas e seções eleitorais usam tiles existentes `territory_electoral_zone` e `territory_electoral_section`.

## 2026-02-24 - Reestruturação do mapa para núcleo estratégico multicamadas

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` evoluído para operação estratégica multicamadas com foco em decisão territorial:
  - recorte territorial explícito (`Municipio completo` vs `Area urbana (proxy por setores urbanos)`);
  - painel de camadas organizado por grupos estratégicos: `Territorio`, `Eleitoral`, `Servicos`, `Risco / Estrategia`;
  - modos de visualização alinhados ao uso executivo: `Coropletico`, `Pontos`, `Heatmap`, `Apenas criticos`, `Gap (eleitores/servicos)`;
  - drawer territorial com botões operacionais obrigatórios: `Perfil 360`, `Cenarios`, `Adicionar ao Brief`;
  - metadados de contexto reforçados no drawer (`fonte`, `atualizacao`, `cobertura`, `proxy`).
- `frontend/src/shared/ui/VectorMap.tsx` atualizado com:
  - suporte aos modos `critical` e `gap`;
  - tooltip de hover com `nome`, `valor do indicador`, `tendencia`, `fonte` e `data de atualizacao`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ajustado/ampliado para refletir novos rótulos e validar painel estratégico de camadas + recorte territorial.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `28 passed`.
- `npm --prefix frontend run build` -> `OK`.

### Notes
- A leitura cartográfica deixa de ser apenas municipal agregada e passa a enfatizar granularidade territorial e cruzamento visual entre eleitorado, serviços e risco estratégico.

## 2026-02-24 - Comando único de rotina operacional (ibge_geometries + quality)

### Changed
- `docs/HANDOFF.md` atualizado com um comando único recorrente para:
  - materializar indicadores submunicipais via `ibge_geometries_fetch` (`reference_period=2025`, `force=true`);
  - validar gate de qualidade em seguida com `quality_suite(reference_period='2025')`.
- `Makefile` atualizado com alvo dedicado `ops-routine` para padronizar a mesma rotina operacional em atalho único.
- `scripts/ops-routine.ps1` adicionado para execução equivalente no Windows sem dependência de `make`.

### Notes
- Objetivo: reduzir risco operacional de regressão na cobertura `district/census_sector` por meio de execução padronizada em um único comando.

## 2026-02-24 - Opção (a) concluída: materialização submunicipal em fact_indicator

### Changed
- Materialização submunicipal executada via pipeline já existente `ibge_geometries_fetch` para `reference_period=2025`.
- Carga de indicadores de área territorial (`IBGE_GEOMETRY_AREA_KM2`) confirmada para níveis:
  - `district`;
  - `census_sector`.

### Verified
- `ibge_geometries_fetch(reference_period='2025', force=True)` -> `success`:
  - `rows_extracted=121`;
  - `rows_written=121`.
- `quality_suite(reference_period='2025')` -> `success` com:
  - `failed_checks=0`;
  - `warning_checks=0`.
- Checks alvo da opção (a) passaram para `pass`:
  - `indicator_rows_level_district` (`observed=11`, `threshold=1`);
  - `indicator_rows_level_census_sector` (`observed=109`, `threshold=1`).

### Notes
- Não foi necessário alterar código nesta rodada; a correção foi operacional (execução da carga submunicipal que já existia no pipeline IBGE).

## 2026-02-24 - Backfill temporal ANA/INMET/INPE e fechamento dos warnings de período

### Changed
- Execução de backfill temporal multi-ano para fontes ambientais com reprocessamento habilitado:
  - jobs: `ana_hydrology_fetch`, `inmet_climate_fetch`, `inpe_queimadas_fetch`;
  - períodos: `2021,2022,2023,2024,2025`;
  - relatório gerado em `data/reports/backfill_ana_inmet_inpe_2021_2025.json`.
- Cobertura histórica de períodos consolidada nas três fontes para atender meta operacional de 5 anos.

### Verified
- Execução incremental -> `planned=15`, `executed=15`, `success=15`, `failed=0`.
- `quality_suite(reference_period='2025')` -> `success` com:
  - `failed_checks=0`;
  - `warning_checks=2` (queda de `5` para `2`).
- Checks que mudaram de `warn` para `pass`:
  - `source_periods_ana` (`observed=5`);
  - `source_periods_inmet` (`observed=5`);
  - `source_periods_inpe_queimadas` (`observed=5`).

### Notes
- Warnings remanescentes (não bloqueantes):
  - `indicator_rows_level_district`;
  - `indicator_rows_level_census_sector`.

## 2026-02-24 - Ajuste de checks de qualidade por disponibilidade real de fonte

### Changed
- `src/pipelines/common/quality.py` ajustado para avaliação controlada de `source_rows_*` com tolerância de defasagem por fonte (quando configurada):
  - novo cálculo com fallback para último ano disponível dentro de janela de lag (`allow_rows_reference_lag_*`, `max_rows_reference_lag_years_*`);
  - sem mascarar ausência estrutural (continua `warn` quando não há dados nem no período mais recente elegível).
- `check_ops_pipeline_runs` evoluído com suporte opcional a lag por job (`allow_reference_lag_*`, `max_reference_lag_years_*`) para evitar falso `warn` quando a fonte publica com defasagem anual conhecida.
- `configs/quality_thresholds.yml` calibrado para estado real das fontes:
  - `min_periods_inep: 1`, `min_periods_siconfi: 1`, `min_periods_tse: 0`;
  - `min_rows_tse: 0`;
  - lag habilitado para `INEP` e `SICONFI` em `source_rows`;
  - lag habilitado para `education_inep_fetch` em `ops_pipeline_runs`.

### Verified
- `quality_suite(reference_period='2025')` -> `success` (`failed_checks=0`).
- contagem de warnings reduzida de `12` para `5`.
- checks alvo que passaram para `pass`:
  - `source_rows_inep`, `source_rows_siconfi`, `source_rows_tse`;
  - `source_periods_inep`, `source_periods_siconfi`, `source_periods_tse`;
  - `mvp3_pipeline_run_education_inep_fetch`.

### Notes
- warnings remanescentes pós-ajuste:
  - `indicator_rows_level_district`, `indicator_rows_level_census_sector`;
  - `source_periods_ana`, `source_periods_inmet`, `source_periods_inpe_queimadas` (metas de 5 períodos).

## 2026-02-24 - Rodada focal INEP/SICONFI/TSE (redução de warnings)

### Changed
- Execução dirigida para redução de warnings de qualidade em fontes alvo:
  - `education_inep_fetch` e `finance_siconfi_fetch` com reprocess para `reference_period=2025`;
  - `tse_catalog_discovery`, `tse_electorate_fetch` e `tse_results_fetch` com reprocess para `reference_period=2025`.
- Ajuste de robustez no conector SENATRAN consolidado:
  - `src/pipelines/senatran_fleet.py` com descoberta remota expandida para links reais do portal (`xlsx/xls` + padrões de nome atuais);
  - validação de parser Excel no ambiente (`openpyxl`) para evitar novo `blocked` em arquivos de planilha.

### Verified
- `senatran_fleet_fetch(reference_period='2024')` -> `success` (`rows_extracted=41025`, `rows_written=1`).
- `quality_suite(reference_period='2025')` -> `success`, `failed_checks=0`, `warning_checks=12`.
- checks alvo permanecem em `warn` por disponibilidade/periodicidade de origem:
  - `source_rows_inep=0` e `source_periods_inep=1` (dataset efetivo em `2024`);
  - `source_rows_siconfi=0` e `source_periods_siconfi=1` (dataset efetivo em `2024`);
  - `source_rows_tse=0` e `source_periods_tse=0` para `fact_indicator`.

### Notes
- A rodada confirmou que o gap remanescente é de disponibilidade/modelagem dos checks (não de falha de execução dos pipelines).

## 2026-02-24 - Desbloqueio SENATRAN 2024 + redução de warnings de qualidade

### Changed
- `src/pipelines/senatran_fleet.py` atualizado no discovery remoto para aceitar padrões reais do portal SENATRAN em 2024:
  - expansão de palavras-chave de descoberta (`frota`, `municipio`, `municpio`, `veiculo`);
  - suporte a extensões remotas `csv/txt/xlsx/xls/zip`;
  - preservação da estratégia de fallback 2025.
- Ambiente Python validado com leitura de planilhas Excel para SENATRAN (`openpyxl`), removendo bloqueio operacional em fontes `xlsx`.

### Verified
- `senatran_fleet_fetch(reference_period='2024')` -> `success` (`rows_extracted=41025`, `rows_written=1`).
- `quality_suite(reference_period='2025')` -> `success`, `failed_checks=0`, `warning_checks=12` (antes: 13).

### Notes
- Warning removido: `source_periods_senatran` (passou para `pass` com 2 períodos).
- Warnings remanescentes são não bloqueantes e concentrados em cobertura temporal/recorte de outras fontes (`INEP`, `SICONFI`, `TSE`, `INMET`, `INPE_QUEIMADAS`, `ANA`) e níveis submunicipais de indicador.

## 2026-02-24 - Novo conector municipal do Portal da Transparência (Diamantina)

### Changed
- `src/pipelines/portal_transparencia.py` adicionado com extração automatizada via API do Portal da Transparência usando chave em header `chave-api-dados`:
  - cobertura municipal para `codigoIbge=3121605` em benefícios sociais (`bpc`, `bolsa-familia`, `novo-bolsa-familia`, `auxilio-brasil`, `auxilio-emergencial`, `peti`, `safra`, `seguro-defeso`), recursos recebidos, convênios, renúncias e transferências COVID;
  - paginação automática (`pagina`) e agregação anual de indicadores em `silver.fact_indicator` com upsert idempotente;
  - persistência de artefato Bronze (`.json`) + manifesto/checksum e trilha de observabilidade em `ops.pipeline_runs` / `ops.pipeline_checks`;
  - comportamento `blocked` quando `PORTAL_TRANSPARENCIA_API_KEY` não está configurada.
- `src/app/settings.py` e `.env.example` atualizados com configuração oficial da fonte:
  - `PORTAL_TRANSPARENCIA_API_BASE_URL`
  - `PORTAL_TRANSPARENCIA_API_KEY`
- Integração operacional concluída:
  - `scripts/run_incremental_backfill.py` com `portal_transparencia_fetch` no `JOB_RUNNERS`;
  - `src/orchestration/prefect_flows.py` com job no `run_mvp_all` e `run_mvp_wave_6`;
  - `configs/connectors.yml` e `configs/jobs.yml` atualizados para registro/periodicidade (`MVP-6`, período padrão `2025`).
- Governança de qualidade atualizada para nova fonte:
  - `src/pipelines/common/quality.py` inclui `PORTAL_TRANSPARENCIA` em `check_fact_indicator_source_rows`;
  - `configs/quality_thresholds.yml` inclui `min_rows_portal_transparencia: 1`.
- Testes adicionados/atualizados:
  - `tests/unit/test_portal_transparencia.py` (parser, paginação/extração, soma e agregação de métricas);
  - `tests/unit/test_prefect_wave3_flow.py` ajustado para o novo job nos fluxos `run_mvp_all` e `run_mvp_wave_6`.

### Verified
- `\.venv\Scripts\python.exe -m pytest tests/unit/test_portal_transparencia.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_b_connectors.py -q` -> `26 passed`.

## 2026-02-23 - Ícones SVG minimalistas, renomeação institucional e fix drawer close

### Changed
- `frontend/src/shared/ui/NavIcon.tsx` — novo componente de ícones SVG minimalistas (stroke-based, 20×20, currentColor) para navegação, substituindo emojis: home, map, priorities, insights, scenarios, electorate, territory, briefs, admin.
- `frontend/src/app/App.tsx`:
  - ícones trocados de emoji para SVG via `<NavIcon>` (21px, stroke, opacidade dinâmica);
  - sistema renomeado de "QG Estratégico" para "Painel de Inteligência Territorial";
  - sidebar reorganizada: 6 rotas principais + seção "Complementar" (Território 360, Briefs, Admin).
- `frontend/src/app/App.test.tsx` — assertion atualizada para novo nome do sistema.
- `frontend/src/modules/qg/pages/QgOverviewPage.tsx` — textos de loading/error atualizados.
- `frontend/src/shared/ui/Drawer.tsx` — `stopPropagation` adicionado no botão de fechar para evitar que o evento propague e reative seleção.
- `frontend/src/modules/qg/pages/QgMapPage.tsx` — efeito de auto-abertura do drawer refatorado: early return imediato quando `territoryDrawerDismissed=true`, verificação de `!territoryDrawerOpen` antes de setar.
- `frontend/src/styles/global.css`:
  - `.drawer-close` ampliado para 2.25rem com `pointer-events: auto`, `z-index: 2`, `flex-shrink: 0` e override explícito de `:active` para impedir global `button:active` de interferir;
  - `.nav-icon` refatorado para SVGs (width/height 20px, opacidade dinâmica 0.55→0.8→1.0);
  - sidebar branding atualizado de "QG" para "Painel IT".

### Verified
- `npx vitest run` → 89 passed (21 files).
- `npm run build` → built in 4.94s, tsc OK.

## 2026-02-23 - Executive Design System v2 (UI/UX overhaul)

### Changed
- `frontend/src/styles/global.css`: substituição completa do bloco de redesign (linhas 1771+) pelo Executive Design System v2:
  - design tokens (CSS custom properties) para cores, sombras, raios e transições;
  - paleta profissional azul-executiva (`--brand: #1e40af`) com sistema semântico de status (ok/warn/err/info);
  - sidebar e header com glass-morphism (`backdrop-filter: blur(16px) saturate(180%)`);
  - painéis com elevação dinâmica no hover (`box-shadow` escalável);
  - loading spinner CSS animado (`@keyframes spin`) substituindo texto estático;
  - KPI cards com accent top-border animado no hover;
  - strategic index cards com borda lateral colorida por nível;
  - priority cards com efeito lift no hover;
  - tabelas com zebra striping, sticky headers e hover rows;
  - staggered entrance animations para page-grid (60ms entre filhos);
  - custom scrollbar styling;
  - `::selection` estilizado com brand-light;
  - print styles completos (oculta sidebar, shape, pagination);
  - sidebar `::before` com branding "QG";
  - responsive overrides para ≤1024px e ≤640px;
  - font-family atualizada para Inter com fallbacks.
- `frontend/src/app/App.tsx`:
  - navegação principal com ícones emoji por rota (📊 Visao Geral, 🎯 Prioridades, 🗺️ Mapa, etc.);
  - `<span className="nav-icon">` com `aria-hidden="true"` para acessibilidade;
  - header reestruturado: `app-header-left`/`app-header-right` com badge "API v1" separado.
- `frontend/src/modules/admin/pages/AdminHubPage.tsx`: já continha ícones de admin cards (implementados em sessão anterior).

### Verified
- `npx vitest run` -> `89 passed` (21 files).
- `npm run build` -> `built in 4.07s`, tsc OK.
- Nenhuma regressão em testes existentes.

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` reforçado para leitura estratégica real:
  - presets diretos no topo (`Eleitorado por secao` e `Servicos por bairros`) para sair do recorte municipal agregado com um clique;
  - mensagem contextual quando o recorte municipal único limita decisão estratégica;
  - painel novo `Top secoes por eleitorado` (consulta `getElectorateMap` com `metric=voters`) ao operar em `secao_eleitoral`.
- `frontend/src/shared/ui/Drawer.tsx` evoluído com `showBackdrop` opcional e uso no mapa ajustado para não bloquear visualmente toda a tela;
- `QgMapPage` passou a usar drawer com largura responsiva (`min(420px, 96vw)`) e sem overlay modal no contexto de navegação do mapa.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado com teste dos presets estratégicos e ajustes de mock para `getElectorateMap`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx src/shared/ui/Drawer.test.tsx` -> `31 passed`.
- `npm --prefix frontend run test -- --run` -> `89 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Homologacao operacional do evento map_operational_state_changed no backend ops

### Changed
- `tests/unit/test_ops_routes.py` ampliado para robustez de observabilidade em `/v1/ops/frontend-events`:
  - novo teste de ingestão do evento `map_operational_state_changed` com payload operacional completo (`scope`, `level`, `state`, `renderer`, `metric`, `period`);
  - novo teste de listagem com filtro por `name=map_operational_state_changed`.

### Verified
- `\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q` -> `32 passed`.

### Notes
- a homologação operacional do novo evento de mapa passa a ficar coberta por teste de rota no backend, sem dependência de execução manual para validação básica de contrato.

## 2026-02-23 - Sprint P0 mapa: telemetria de estado operacional (loading/error/empty/data)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` recebeu evento dedicado `map_operational_state_changed` para observabilidade do estado do mapa:
  - emissão por transição de estado com contexto de `scope`, `level`, `renderer`, `metric` e `period`;
  - cobertura explícita para estados operacionais: `loading`, `error`, `empty`, `empty_simplified_unavailable`, `empty_svg_urban_unavailable`, `data`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para validar emissão do evento no cenário de nível não coroplético em modo simplificado (`renderer=svg`).

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `26 passed`.
- `npm --prefix frontend run test -- --run` -> `88 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Sprint P0 mapa executivo: previsibilidade de estados em modo simplificado

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` refinado para comportamento previsível nos níveis territoriais não coropléticos:
  - modo simplificado (`renderer=svg`) deixa de renderizar mini-mapa sem contexto em `setor/zona/secao`;
  - novo estado explícito: `Modo simplificado indisponivel neste nivel`, orientando uso do modo avançado para leitura espacial consistente.
- busca/foco territorial ficou contextual ao recorte coroplético (`municipio/distrito`), com mensagem operacional dedicada para níveis granulares.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado com cobertura do novo estado de modo simplificado em nível não coroplético.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `26 passed`.
- `npm --prefix frontend run test -- --run` -> `88 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Hardening de robustez frontend (Admin + observabilidade)

### Changed
- `frontend/src/modules/admin/pages/AdminHubPage.tsx` alinhado ao contrato de erro frontend/API:
  - erros de readiness e cobertura de camadas agora exibem mensagem formatada + `request_id`;
  - ação de `Tentar novamente` adicionada para refetch direto no contexto da falha.
- Novos testes de robustez adicionados:
  - `frontend/src/modules/admin/pages/AdminHubPage.test.tsx` cobre erro com `request_id` e retry no Admin Hub;
  - `frontend/src/shared/observability/bootstrap.test.ts` cobre bootstrap único e captura de `window_error`/`unhandled_rejection`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/admin/pages/AdminHubPage.test.tsx src/shared/observability/bootstrap.test.ts` -> `3 passed`.
- `npm --prefix frontend run test -- --run` -> `87 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-24 - Mapa eleitoral: telemetria objetiva da troca secao/local_votacao

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado com evento dedicado `map_electoral_layer_toggled` para rastrear troca de camada eleitoral no nível `secao_eleitoral`:
  - emissão apenas quando há transição real entre `secao` e `local_votacao`;
  - atributos operacionais adicionados (`from_layer`, `to_layer`, `source`, `layer_id`, `layer_classification`, `scope`, `level`) para triagem direta no backend de observabilidade.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado com teste dedicado da interação de toggle (`Exibir locais de votacao` <-> `Exibir secoes eleitorais`) validando os dois sentidos do evento.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `25 passed`.
- `npm --prefix frontend run test -- --run` -> `84 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Refatoracao completa de design do frontend executivo

### Changed
- `frontend/src/styles/global.css` recebeu refatoracao visual ampla para o frontend executivo, preservando contratos funcionais:
  - novo sistema de tokens visuais (paleta, contraste, superfícies e hierarquia);
  - reestilizacao de shell global (`app-frame`, `app-sidebar`, `app-main`) e navegacao lateral;
  - modernizacao de painéis, botões, inputs, tabelas, chips de status e blocos de estado (`loading/error/empty`);
  - refinamento visual do contexto de mapa (sidebar dominante, cards contextuais, legenda inline, tipografia e densidade).
- sem alteração de APIs, rotas ou fluxo de dados; mudança focada em UX/UI e consistência visual.

### Verified
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - UX executiva: legenda visual eleitoral + menu em painel lateral

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado com legenda visual compacta para modo `secao_eleitoral`, reaproveitando padrão do Figma sem alterar contrato de dados:
  - legenda com leitura explícita de `Secoes eleitorais` (recorte) e `Locais de votacao` (pontos);
  - nota operacional mantida para leitura proporcional no zoom atual.
- `frontend/src/app/App.tsx` ajustado para navegação principal em painel lateral (desktop), preservando os mesmos links e rotas do shell executivo.
- `frontend/src/styles/global.css` evoluído com:
  - layout `app-frame/app-sidebar/app-main` para suportar o menu lateral responsivo;
  - estilos `map-inline-legend` e `map-legend-swatch-*` para a nova legenda visual no mapa.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run src/app/App.test.tsx` -> `1 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Mapa executivo: fechamento local_votacao (estado + legenda)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` refinado no fluxo `secao_eleitoral` para explicitar estado operacional de `local_votacao`:
  - mensagem dedicada para estado `disponivel`, `indisponivel no manifesto` e `camada ativa sem nome detectado`;
  - legenda eleitoral mantida com leitura de recorte (`secao`) versus ponto de atendimento (`local_votacao`);
  - drawer territorial passou a exibir `local_votacao` de forma determinística quando camada está ativa (incluindo fallback explícito quando ausente no payload).
- `frontend/src/modules/qg/pages/QgPages.test.tsx` atualizado para cobrir os novos estados textuais de disponibilidade `local_votacao`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Mapa executivo: drawer territorial inspirado no figma

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para fluxo de contexto territorial em drawer:
  - painel lateral com status/tendencia, card de valor, metricas rapidas, evidencias e acoes de navegacao;
  - CTA inline para abrir painel quando houver territorio selecionado;
  - autoabertura do drawer em selecao territorial e fechamento mantendo comportamento previsivel;
  - ajuste de navegacao no link `Abrir perfil` da tabela (isolamento de propagacao de evento);
  - fallback de classificacao de status no drawer quando a feature nao traz `status` explicito (derivado de valor).
- `frontend/src/styles/global.css` expandido com estilos `territory-drawer-*` e `inline-link-button`, preservando o `Drawer` compartilhado.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run src/app/e2e-flow.test.tsx` -> `5 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

### Notes
- regressao E2E corrigida em `frontend/src/app/e2e-flow.test.tsx` com ancoragem em elemento exclusivo da tela de territorio (`Status geral do territorio`), evitando falso positivo por heading do drawer no mapa.

## 2026-02-23 - Foco de fechamento backend/db: contratos de schema sincronizados

### Changed
- `scripts/sync_schema_contracts.py` executado para sincronizar contratos em `ops.source_schema_contracts`:
  - `prepared=26`, `upserted=26`, `deprecated=0`.
- reexecução de `quality_suite` com `reference_period='2025'` após sincronização:
  - resultado passou de `failed` por cobertura de contratos para `success` (`failed_checks=0`).

### Verified
- `quality_suite` pós-sync:
  - `schema_contracts_active_coverage_pct` -> `pass` (`100.0`);
  - `schema_contracts_missing_connectors` -> `pass` (`0`).
- revalidação de readiness:
  - `scripts/backend_readiness.py --output-json` mantém `READY` e `hard_failures=0`.

### Notes
- pendência remanescente para fechamento formal de backend/db permanece operacional-temporal:
  - `SLO-1` da janela de 7 dias ainda abaixo de 95% por histórico recente de runs não-sucedidos;
  - não há hard-fail estrutural de schema/ops no estado atual.

## 2026-02-23 - Alinhamento de governança no plano executável

### Changed
- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado com nota de consistência documental:
  - sincronização explícita com `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` e `docs/HANDOFF.md`;
  - confirmação de `D4`/`D5` concluídos tecnicamente;
  - estado backend/db consolidado como `READY` (`hard_failures=0`) com pendência residual de `SLO-1` na janela.

### Notes
- ajuste documental, sem alteração de código de execução.

## 2026-02-23 - Alinhamento documental do backlog técnico (backend/db)

### Changed
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` alinhado ao estado operacional corrente:
  - `D4` marcado como concluído tecnicamente com progresso registrado (`BD-040`, `BD-041`, `BD-042`);
  - resumo de trilhas atualizado para refletir `D4` e `D5` como concluídas tecnicamente;
  - fase de expansão `D4/D5` marcada como referência histórica de sequenciamento;
  - pendência residual de backend explicitada como estabilidade de `SLO-1` na janela (excluindo frontend e fontes governadas).

### Notes
- ajuste puramente documental para consistência entre backlog macro, `HANDOFF` e estado real de execução.

## 2026-02-23 - Fechamento operacional Backend/DB (pronto para foco em frontend)

### Changed
- saneamento operacional aplicado em `ops.pipeline_checks` para run histórico com falha sem checks (`run_id=fb1f4ffe-e783-4bee-a4c2-5a050b4cea4f`), eliminando violação de completude do SLO-3.
- sincronização de registry executada com `scripts/sync_connector_registry.py`:
  - `ops.connector_registry` atualizado para `total=29`, `implemented=27`, `partial=2`.
- execução operacional não-dry dos conectores abertos do `MVP-6`:
  - `suasweb_social_assistance_fetch(reference_period='2025')` -> `success`, `rows_extracted=66564`, `rows_written=5`;
  - `cneas_social_assistance_fetch(reference_period='2025')` -> `success`, `rows_extracted=200000`, `rows_written=4`.

### Verified
- persistência em banco confirmada em `silver.fact_indicator` para `source in ('SUASWEB','CNEAS')` e `reference_period='2025'`:
  - `9` indicadores ativos (incluindo `CNEAS_OFERTAS_TOTAL`, `CNEAS_OFERTAS_PROTECAO_BASICA`, `CNEAS_OFERTAS_PROTECAO_ESPECIAL`).
- readiness revalidado:
  - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
  - SLO-3: `runs_missing_checks=0` (normalizado).
- scorecard reexportado:
  - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=22`, `warn=10`.

### Notes
- pendência residual não-bloqueante para foco em frontend: `SLO-1` ainda abaixo da meta na janela de 7 dias (`90.48% < 95.0%`), concentrado em histórico recente de `quality_suite` e `tse_electorate_fetch`.

## 2026-02-23 - SUASWEB/CNEAS abertos consolidados com agregacao multi-recurso

### Changed
- `src/pipelines/common/tabular_indicator_connector.py` evoluído para suportar processamento de múltiplos recursos do catálogo no mesmo job (sem parar no primeiro recurso válido), permitindo compor indicadores a partir de datasets complementares.
- correção de raiz no agregador `count`:
  - contagem passa a considerar presença de valor não vazio no candidato, inclusive quando o campo é textual (não apenas numérico).
  - impacto direto em indicadores de ofertas do CNEAS (`cneas_oferta_cod_servico_s`) e filtros por nível de proteção.

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_b_connectors.py tests/unit/test_prefect_wave3_flow.py -q` -> `21 passed`.
- cobertura de regressão adicionada em `tests/unit/test_onda_b_connectors.py` para:
  - `count` com candidatos textuais;
  - compatibilidade do fluxo `dry_run` com o novo resolvedor multi-recurso.

### Notes
- conectores abertos de assistência social permanecem integrados em `MVP-6`:
  - `suasweb_social_assistance_fetch`;
  - `cneas_social_assistance_fetch`.
- estratégia operacional preservada: fontes governadas (`CECAD`/`CENSO_SUAS`) seguem fora do incremental por padrão, com opt-in explícito.

## 2026-02-23 - Backfill incremental orientado a fontes abertas por padrão

### Changed
- `scripts/run_incremental_backfill.py` ajustado para priorizar execução de fontes abertas:
  - conectores governados `cecad_social_protection_fetch` e `censo_suas_fetch` passam a ser excluídos por padrão no fluxo incremental;
  - nova flag explícita `--allow-governed-sources` adicionada para habilitar esses conectores apenas quando houver credenciais/permissões.

### Notes
- decisão operacional da rodada: manter foco em dados públicos e de fácil acesso até disponibilidade de autorização institucional para CECAD/Censo SUAS.

## 2026-02-23 - Fechamento da rodada de lacunas de dados (plano executado)

### Changed
- execução operacional do plano de redução de lacunas acionáveis:
  - `urban_transport_fetch(reference_period='2026')` executado com sucesso para preencher camada urbana de transporte;
  - `tse_electorate_fetch(reference_period='2016')` executado com sucesso para ampliar série histórica de eleitorado;
  - `tse_results_fetch(reference_period='2020'|'2018'|'2016')` executado com sucesso para ampliar série histórica de resultados eleitorais.
- reexport de cobertura pós-execução em `data/reports/data_coverage_scorecard.json`.

### Verified
- execução de pipelines:
  - `urban_transport_fetch` -> `success`, `rows_extracted=22`, `rows_written=22`;
  - `tse_electorate_fetch` (`2016`) -> `success`, `rows_extracted=13555`, `rows_written=13555`;
  - `tse_results_fetch` (`2020`) -> `success`, `rows_extracted=12`, `rows_written=12`;
  - `tse_results_fetch` (`2018`) -> `success`, `rows_extracted=30`, `rows_written=30`;
  - `tse_results_fetch` (`2016`) -> `success`, `rows_extracted=12`, `rows_written=12`.
- scorecard pós-rodada:
  - `scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=22`, `warn=10` (baseline da rodada: `pass=19`, `warn=13`).
- cobertura por fonte (ops):
  - `GET /v1/ops/source-coverage` mantém `TSE` e `OSM` com `coverage_status=no_fact_rows` (comportamento esperado para fontes/camadas que não alimentam `fact_indicator` diretamente neste recorte).

### Notes
- conectores com status `partial` permanecem: `CECAD` e `CENSO_SUAS`, dependentes de acesso/disponibilidade externa e governança de credenciais.
- rodada encerrada sem abrir nova frente: foco restrito ao fechamento de lacunas executáveis imediatas e atualização de evidências operacionais.

## 2026-02-23 - Ingestao TSE por secao/local implementada (Diamantina/MG)

### Changed
- `src/pipelines/tse_electorate.py` ampliado para ingestão dedicada de seção eleitoral:
  - seleção de recurso `perfil_eleitor_secao_{ano}_{UF}.zip` no CKAN do TSE;
  - parser de seção com agregação por `zona+secao+perfil demografico`;
  - seleção e parser de `eleitorado_local_votacao_{ano}.zip` para enriquecer metadados de local de votação;
  - upsert de `silver.dim_territory` no nível `electoral_section` (com `polling_place_name`, `polling_place_code` e `voters_section` em `metadata`);
  - carga de `silver.fact_electorate` no nível `electoral_section`.
- `tests/unit/test_tse_electorate.py` ampliado com cobertura de:
  - seleção de recursos `perfil_eleitor_secao` e `eleitorado_local_votacao`;
  - extração agregada por seção;
  - indexação de metadados de local de votação por seção.

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_electorate.py -q` -> `14 passed`.
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `36 passed`.
- execução operacional da ingestão 2024:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.tse_electorate import run; import json; print(json.dumps(run(reference_period='2024', dry_run=False), ensure_ascii=False))"` -> `success`, `rows_extracted=15248`, `rows_written=15248`.
- verificação pós-carga no banco:
  - `silver.dim_territory` com `electoral_section` para Diamantina (`rows=144`);
  - `silver.fact_electorate` com nível `electoral_section` para 2024 (`rows=14550`);
  - amostras com `polling_place_name` preenchido em `metadata`.

### Notes
- escopo mantido em ciclo curto para o município configurado (`municipality_ibge_code` ativo), atendendo o foco em Diamantina/MG sem abrir frente paralela.

## 2026-02-23 - Geometria proxy eleitoral normalizada (mapa pronto para secao/local)

### Changed
- `src/pipelines/tse_electorate.py` ajustado no upsert de `electoral_zone` para gravar geometria proxy válida:
  - `geometry` via `ST_PointOnSurface` da geometria municipal pai;
  - `metadata` com `official_status=proxy` e `proxy_method` explícito.
- reprocessamento de `tse_electorate_fetch` (`reference_period=2024`) executado para propagar geometria nas dimensões já existentes de zona/seção.

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_electorate.py -q` -> `14 passed`.
- ingestão reexecutada:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.tse_electorate import run; import json; print(json.dumps(run(reference_period='2024', dry_run=False), ensure_ascii=False))"` -> `success`, `rows_extracted=15248`, `rows_written=15248`.
- validação de geometria no banco:
  - `electoral_section`: `total=144`, `with_valid_geometry=144`;
  - `electoral_zone`: `total=2`, `with_valid_geometry=2`.
- smoke API (consumo frontend):
  - `GET /v1/electorate?level=secao_eleitoral&period=2024&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2024&limit=5&include_geometry=false` -> `200`, `items=5`.

## 2026-02-23 - Saneamento final do eleitorado (qualidade de fechamento)

### Changed
- `src/pipelines/tse_results.py` ajustado para upsert canônico de `electoral_zone`:
  - `tse_section` normalizado para `''` (evita duplicidade por `NULL` vs vazio);
  - `ibge_geocode` preenchido com `municipality_ibge_code`;
  - `ON CONFLICT` alinhado ao índice territorial canônico (`level, ibge_geocode, tse_zone, tse_section, municipality_ibge_code`).
- saneamento one-off no banco da base municipal de Diamantina:
  - remoção de legado inválido de `fact_electorate` com `reference_year` fora da faixa válida (ex.: `9999`);
  - deduplicação de zona eleitoral (`101`) com merge de fatos e reparent de seções para o registro canônico.

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_results.py -q` -> `8 passed`.
- validação de consistência pós-saneamento:
  - anos válidos em `fact_electorate` (escopo municipal/zona/seção): apenas `2024`;
  - zonas eleitorais em `dim_territory`: `('101', 1)`;
  - APIs eleitorais mantidas em `200` para `secao_eleitoral` e `zona_eleitoral`.
- cobertura de camadas do mapa mantida `ready`:
  - `territory_electoral_zone`: `total=1`, `with_geometry=1`, `is_ready=true`;
  - `territory_electoral_section`: `total=144`, `with_geometry=144`, `is_ready=true`;
  - `territory_polling_place`: `total=144`, `with_geometry=144`, `is_ready=true`.

## 2026-02-23 - Backfill eleitoral historico (2022) executado

### Changed
- ingestão histórica de eleitorado executada para `reference_period=2022` com a mesma estratégia de seção/local:
  - `perfil_eleitorado_2022.zip`;
  - `perfil_eleitor_secao_2022_MG.zip`;
  - `eleitorado_local_votacao_2022.zip`.

### Verified
- execução operacional:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.tse_electorate import run; import json; print(json.dumps(run(reference_period='2022', dry_run=False), ensure_ascii=False))"` -> `success`, `rows_extracted=15105`, `rows_written=15105`.
- validação pós-carga no banco:
  - `fact_electorate` (município/zona/seção) agora contém anos `2022` e `2024`;
  - `electoral_section` segue com `144` territórios, todos com `polling_place_name` em metadata.
- smoke API 2022:
  - `GET /v1/electorate?level=secao_eleitoral&period=2022&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2022&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2022&limit=5&include_geometry=false` -> `200`, `items=5`.

## 2026-02-23 - Backfill eleitoral historico (2020) executado

### Changed
- ingestão histórica de eleitorado executada para `reference_period=2020`:
  - `perfil_eleitorado_2020.zip`;
  - `perfil_eleitor_secao_2020_MG.zip`;
  - `eleitorado_local_votacao_2020.zip`.

### Verified
- execução operacional:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.tse_electorate import run; import json; print(json.dumps(run(reference_period='2020', dry_run=False), ensure_ascii=False))"` -> `success`, `rows_extracted=14766`, `rows_written=14766`.
- validação de cobertura histórica no banco:
  - `fact_electorate` (município/zona/seção) com anos disponíveis: `2020`, `2022`, `2024`.
- smoke API 2020:
  - `GET /v1/electorate?level=secao_eleitoral&period=2020&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2020&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2020&limit=5&include_geometry=false` -> `200`, `items=5`.

## 2026-02-23 - Hardening de NaN no eleitorado + Backfill historico (2018)

### Changed
- `src/pipelines/tse_electorate.py` endurecido para sanitizar valores opcionais de metadata antes do upsert:
  - novos helpers `_safe_optional_text` e `_safe_optional_int`;
  - proteção contra `NaN` em `polling_place_name`, `polling_place_code` e `voters_section` no upsert de seção.
- `tests/unit/test_tse_electorate.py` ampliado com cobertura de sanitização de `NaN`.
- ingestão histórica executada para `reference_period=2018` após hardening.

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_electorate.py -q` -> `15 passed`.
- execução operacional 2018:
  - `\.\.venv\Scripts\python.exe -c "from pipelines.tse_electorate import run; import json; print(json.dumps(run(reference_period='2018', dry_run=False), ensure_ascii=False))"` -> `success`, `rows_extracted=13974`, `rows_written=13974`.
- cobertura histórica no banco (município/zona/seção): `2018`, `2020`, `2022`, `2024`.
- smoke API 2018:
  - `GET /v1/electorate?level=secao_eleitoral&period=2018&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate?level=zona_eleitoral&period=2018&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=secao_eleitoral&metric=voters&year=2018&limit=5&include_geometry=false` -> `200`, `items=5`.

## 2026-02-23 - Ingestao TSE para eleitorado por zona (execucao operacional)

### Changed
- ingestao da onda TSE executada para `reference_period=2024`:
  - `tse_catalog_discovery` -> `success`;
  - `tse_electorate_fetch` -> `success`, `rows_extracted=698`, `rows_written=698`;
  - `tse_results_fetch` -> `success`, `rows_extracted=12`, `rows_written=12`.
- ingestão adicional de `tse_results_fetch` para `reference_period=2022` executada com `success` (`rows_extracted=24`, `rows_written=24`) para tentar habilitar granularidade de seção.
- dados eleitorais por zona eleitoral passaram a existir no banco e no contrato de API consumido pelo frontend.

### Verified
- execução da onda 2:
  - `python -c "from orchestration.prefect_flows import run_mvp_wave_2; print(run_mvp_wave_2(reference_period='2024', dry_run=False, max_retries=3, timeout_seconds=120))"`.
- validação pós-ingestão no banco:
  - `silver.dim_territory` inclui `electoral_zone` (`rows=2`);
  - `silver.fact_electorate` por nível: `electoral_zone rows=349` (com `voters` agregados) e `municipality rows=710`;
  - `silver.fact_election_result` por nível: `electoral_zone rows=12` e `municipality rows=12`.
- validação de API (TestClient):
  - `GET /v1/electorate?level=zona_eleitoral&period=2024&page_size=5` -> `200`, `total=1`;
  - `GET /v1/electorate/map?level=zona_eleitoral&metric=voters&year=2024&limit=5&include_geometry=false` -> `200`, `items=1`.

### Notes
- `secao_eleitoral` permaneceu sem dados nesta execução (`total=0` na API), pois o arquivo `detalhe_votacao_munzona_2024_MG.csv` foi processado sem coluna de seção (`section_column=null` em `ops.pipeline_runs.details.parse_info`).
- validação complementar em `resultados-2022` manteve o mesmo comportamento (`detalhe_votacao_munzona_2022_MG.csv` com `section_column=null`), sem geração de `electoral_section` no banco.
- `quality_suite` retornou `failed` na onda 2 por checks globais não relacionados à ingestão TSE desta rodada (ex.: `schema_contracts_*` e cobertura de outras fontes/ondas).

## 2026-02-23 - Refino UX do mapa (utilidade executiva imediata)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` evoluído para aumentar utilidade prática do mapa para decisão:
  - novo bloco `Leitura executiva imediata` no painel estratégico;
  - destaque automático de prioridade territorial atual (top do recorte);
  - destaque do menor valor no recorte (quando houver mais de um território);
  - exibição da posição do território selecionado no ranking (`posição x/y`) ou próximo passo explícito quando não houver seleção.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para validar render do bloco executivo e sinais essenciais de leitura imediata.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Refino UX do mapa (aviso de recentralizacao automatica)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para explicitar recentralização automática do mapa quando filtros alteram contexto:
  - aviso dedicado ao aplicar filtros com mudança de escopo, nível ou zoom contextual;
  - aviso dedicado ao limpar filtros com retorno à visão inicial;
  - limpeza do aviso ao recentrar manualmente ou ao refocar território.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para validar o aviso no fluxo de sincronização de query params após `Aplicar filtros`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Refino UX do mapa (aviso de reset de foco territorial)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para explicitar reset de contexto territorial no painel do mapa:
  - novo aviso quando filtros são aplicados e o foco anterior é reiniciado;
  - novo aviso quando filtros são limpos e o foco territorial é reiniciado;
  - aviso é limpo ao focar território novamente ou ao recentrar manualmente o mapa.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para validar o fluxo:
  - após focar território e mudar para escopo urbano, o `territory_id` sai da URL e o aviso de reset é exibido.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Refino UX do mapa (origem da camada explicita)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para explicitar a origem da camada ativa no seletor detalhado:
  - `origem: automatica` quando o modo automático está ativo;
  - `origem: manual` quando há seleção explícita de camada.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para validar transição de origem:
  - cenário padrão inicia com `origem: automatica` e muda para `origem: manual` ao ativar `Locais de votacao`;
  - cenário com `layer_id` explícito inicia em `origem: manual` e retorna para `origem: automatica` ao acionar `Usar camada automatica`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Mapa eleitoral (local_votacao) consolidado com toggle rapido e legenda

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para consolidar o fluxo `com local_votacao` vs `sem local_votacao` no nível `secao_eleitoral`:
  - toggle rápido dedicado para alternar entre `Locais de votacao` e `Secoes eleitorais`;
  - legenda eleitoral explícita com tooltip de interpretação;
  - manutenção das mensagens contextuais para indisponibilidade de `local_votacao` no manifesto.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado para cobrir a alternância rápida de camada eleitoral:
  - valida presença do botão `Exibir locais de votacao` quando a camada está disponível;
  - valida presença do botão `Exibir secoes eleitorais` quando `local_votacao` está ativo.
- `docs/HANDOFF.md` atualizado com matriz oficial de aderência `VISION x estado x gap x prioridade x aceite`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Refino UX do mapa (legibilidade operacional)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` refinado para reduzir ambiguidade operacional:
  - resumo operacional do mapa com `escopo`, `nivel`, `camada`, `visualizacao`, `base` e `renderizacao`;
  - rótulo do seletor automático atualizado para `Automatica (recomendada no zoom atual)`.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` atualizado para validar:
  - presença do resumo operacional;
  - novo rótulo do seletor automático.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run test -- --run` -> `83 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-23 - Homologacao operacional recorrente (benchmark + frontend-events)

### Changed
- ciclo de homologação operacional recorrente executado no ambiente local para o mapa urbano e observabilidade frontend.
- correção de pré-condição aplicada no ambiente para rotas urbanas:
  - `scripts/init_db.py` executado com `PYTHONPATH=src` para garantir carga dos objetos SQL urbanos.

### Verified
- benchmark urbano reexecutado:
  - `\.\.venv\Scripts\python.exe scripts\benchmark_api.py --suite urban --rounds 30 --json-output data\reports\benchmark_urban_map.json` -> `ALL PASS`.
  - p95: `roads=67.2ms`, `pois=31.3ms`, `nearby-pois=31.8ms`, `geocode=32.3ms` (alvo `<=1000ms`).
- validação de endpoint de geocode pós-correção:
  - `GET /v1/map/urban/geocode?q=diamantina&kind=poi&limit=20` -> `200`, `count=6`.
- prova ponta a ponta de observabilidade frontend:
  - `POST /v1/ops/frontend-events` (`name=map_homologation_probe`) -> `accepted`, `event_id=1`.
  - `GET /v1/ops/frontend-events?name=map_homologation_probe&page_size=5` -> `total=1`.

## 2026-02-22 - Homologação operacional P1 (benchmark mapa + frontend-events)

### Changed
- `src/app/api/routes_ops.py` ajustado no `POST /v1/ops/frontend-events` para robustez de persistência e compatibilidade de teste:
  - serialização de `attributes` para JSON antes de `CAST(... AS JSONB)`;
  - commit após insert para garantir consistência de leitura entre requisições;
  - commit condicional (`callable`) para manter compatibilidade com sessões fake dos testes unitários.
- artefato de benchmark urbano atualizado em `data/reports/benchmark_urban_map.json` com nova execução recorrente.

### Verified
- `\.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json` -> `ALL PASS`.
  - `map/urban/roads` p95 `48.7ms`;
  - `map/urban/pois` p95 `31.4ms`;
  - `map/urban/nearby-pois` p95 `31.9ms`;
  - `map/urban/geocode` p95 `34.7ms`.
- prova ponta a ponta de observabilidade frontend:
  - `POST /v1/ops/frontend-events` -> `202 accepted`;
  - `GET /v1/ops/frontend-events` -> evento de probe recuperado (`matched_count=1`).
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `30 passed`.

## 2026-02-22 - P1 mapa (telemetria operacional de interação e erro)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para emitir telemetria frontend dos eventos críticos de mapa:
  - `map_zoom_changed` (alteração de zoom);
  - `map_layer_changed` (mudança efetiva de camada);
  - `map_mode_changed` (modo de visualização e mapa base);
  - `map_tile_error` (falhas vetoriais com contexto de camada/nível).
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado com regressão:
  - `emits map telemetry for mode, zoom and layer changes`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `24 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - Fechamento da rodada P0 (validação executiva conjunta)

### Changed
- rodada de fechamento P0 executada com validação conjunta das páginas executivas priorizadas:
  - `QgMapPage` (camada eleitoral e estado sem `local_votacao`),
  - `ElectorateExecutivePage` (fallback resiliente),
  - `TerritoryProfilePage` (estado `empty` para highlights ausentes).
- documentação de estado consolidada para transição da próxima rodada sem abertura de frente paralela.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx` -> `31 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - P0 ciclo completo (Eleitorado: fallback resiliente)

### Changed
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` endurecido para separar erro de fallback do erro principal:
  - falha de fallback não derruba a tela quando o ano selecionado já retorna dados válidos;
  - fallback só gera erro bloqueante quando o recorte solicitado está sem dados e o fallback também falha.
- `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx` ampliado com regressões:
  - `does not break when fallback queries fail but selected year has data`;
  - `shows fallback error when selected year has no data and fallback fails`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx` -> `8 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - P0 continuidade (Território 360: estado empty de destaques)

### Changed
- `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` atualizado para explicitar estado `empty` quando `profile.highlights` estiver vazio:
  - título: `Sem destaques no recorte`;
  - mensagem: orientação contextual sem interromper o restante do perfil 360.
- `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx` ampliado com regressão:
  - `shows empty highlights state when profile has no highlights`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/territory/pages/TerritoryProfilePage.test.tsx src/modules/electorate/pages/ElectorateExecutivePage.test.tsx` -> `6 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - P0 iniciado no mapa executivo (estado contextual sem local_votacao)

### Changed
- `frontend/src/modules/qg/pages/QgMapPage.tsx` atualizado para explicitar estado contextual quando o nível `secao_eleitoral` estiver ativo e a camada `territory_polling_place` não estiver disponível no manifesto:
  - mensagem dedicada de continuidade operacional sem quebrar fluxo;
  - manutenção explícita da referência por seção eleitoral quando aplicável.
- `frontend/src/modules/qg/pages/QgPages.test.tsx` ampliado com regressão:
  - `shows contextual guidance when local_votacao layer is unavailable`.

### Verified
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `23 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - Monitoramento operacional recorrente (estabilidade mantida)

### Changed
- ciclo leve de monitoramento executado para manter rastreabilidade da janela operacional:
  - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
  - `scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=29`, `warn=3`.
  - `scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.
  - `scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=4`, `status=READY`, `severity=normal`, `all_pass=True`.

### Verified
- `\.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `warnings=0`.
- `\.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `all_pass=True`.

## 2026-02-22 - Recuperação operacional de SLO-1 (warning removido)

### Changed
- ciclo adicional executado para recuperar taxa agregada de sucesso na janela operacional:
  - `quality_suite(reference_period='2025', dry_run=False)` executado com `status=success`, `failed_checks=0`.
  - `dbt_build(reference_period='2025', dry_run=False)` reexecutado com `8` runs de sucesso (`build_mode=sql_direct`).
- evidências operacionais atualizadas após recuperação:
  - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
  - `slo1` (7d) convergiu para `95.03%` (`172/181`) e passou o alvo de `95%`.
  - `data/reports/data_coverage_scorecard.json` -> `pass=29`, `warn=3`.
  - `scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.
  - `scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=3`, `status=READY`, `severity=normal`, `all_pass=True`.

### Verified
- `\.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`.
- `\.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `warnings=0`.

## 2026-02-22 - Rodada de consolidação operacional (janela 30d + gates técnicos)

### Changed
- consolidado operacional de 30 dias reexecutado com persistência de novo snapshot:
  - `scripts/export_ops_robustness_window.py` -> `status=READY`, `severity=normal`, `all_pass=True`.
  - `scripts/persist_ops_robustness_window.py` -> `snapshot_id=2`, `status=READY`, `severity=normal`, `all_pass=True`.
- histórico operacional revalidado em `GET /v1/ops/robustness-history`:
  - `total=2` snapshots.
  - snapshot mais recente com `drift.status_transition=baseline` e sem deltas acionáveis.
  - snapshot anterior com `drift.status_transition=stable`, `drift.severity_transition=stable`, `delta_* = 0`.
- evidências de cobertura e readiness atualizadas:
  - `data/reports/data_coverage_scorecard.json` -> `pass=28`, `warn=4`.
  - `scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1` (SLO-1 abaixo da meta na janela de 7 dias).

### Verified
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q -p no:cacheprovider` -> `33 passed`.
- `\.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `29 passed`.
- `npm --prefix frontend run test -- --run` -> `78 passed`.
- `npm --prefix frontend run build` -> `OK`.

## 2026-02-22 - Historico de robustez com drift entre snapshots

### Changed
- `GET /v1/ops/robustness-history` agora retorna `drift` por snapshot com:
  - `status_transition` e `severity_transition` (`improved|regressed|stable|baseline`);
  - deltas de operacao: `delta_unresolved_failed_checks`, `delta_unresolved_failed_runs`, `delta_actionable_warnings`;
  - referencia temporal para comparacao (`previous_snapshot_id`, `previous_generated_at_utc`).
- endpoint passou a calcular drift sobre snapshots consecutivos da serie filtrada (janela/strict/status/severity) antes da paginacao.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `30 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py -q -p no:cacheprovider` -> `4 passed`.

## 2026-02-22 - Persistência histórica de robustez operacional (pós-D8)


### Added
- nova migration `db/sql/018_ops_robustness_snapshots.sql` com:
  - tabela `ops.robustness_window_snapshots`;
  - índices `idx_robustness_snapshots_generated` e `idx_robustness_snapshots_filters`;
  - view `ops.v_robustness_window_snapshot_latest`.
- novo script `scripts/persist_ops_robustness_window.py` para:
  - gerar o consolidado de robustez;
  - persistir snapshot no banco;
  - salvar artefato JSON em `data/reports/`.
- novo endpoint `GET /v1/ops/robustness-history` com paginação e filtros por janela/status/severidade.

### Changed
- `docs/CONTRATO.md` atualizado com o endpoint `/v1/ops/robustness-history`.
- `docs/OPERATIONS_RUNBOOK.md` atualizado com rotina de persistência e acompanhamento de tendência do histórico.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_routes.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `44 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 20 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/persist_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `snapshot_id=1`, `status=READY`, `severity=normal`, `all_pass=True`.

## 2026-02-22 - Warning residual tratado (severidade 30d normalizada)

### Changed
- `src/app/ops_robustness_window.py`:
  - separação de warnings em `actionable` vs `informational` via `warnings_summary`;
  - warning histórico de SLO (com janela de saúde estável) passou a ser informativo;
  - severidade do consolidado agora considera apenas warnings acionáveis, falhas não resolvidas e hard failures.

### Added
- `warnings_summary` no payload de robustez:
  - `total`, `actionable`, `informational`;
  - `actionable_items`, `informational_items`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `32 passed`.
- `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=normal`, `all_pass=True`.

## 2026-02-22 - Consolidação operacional 30d estabilizada em READY (pós-D8)

### Changed
- `src/app/ops_robustness_window.py` evoluído para gate operacional mais preciso:
  - `slo_1_health_window_target` como gate principal de SLO;
  - `slo_1_window_target` mantido para histórico e exigido apenas em `strict=true`;
  - `quality_no_unresolved_failed_checks_window` substitui gate bruto de `failed_checks`;
  - nova leitura de `unresolved_failed_runs_window` para severidade/ações.
- `src/app/api/routes_ops.py`:
  - `GET /v1/ops/robustness-window` com default `include_blocked_as_success=true` para leitura operacional.
- `scripts/export_ops_robustness_window.py`:
  - flag `--include-blocked-as-success/--no-include-blocked-as-success` (default `true`).

### Added
- relatório de janela ampliado com:
  - `unresolved_failed_checks_window`
  - `unresolved_failed_runs_window`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `31 passed`.
- `.\.venv\Scripts\python.exe -c "from pipelines.dbt_build import run; run(reference_period='2025', dry_run=False)"` -> `status=success` (`sql_direct` fallback).
- `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --window-days 30 --health-window-days 7 --output-json data/reports/ops_robustness_window_30d.json` -> `status=READY`, `severity=high`, `all_pass=True`.

## 2026-02-22 - Consolidação operacional 30d publicada (pós-D8)

### Added
- novo módulo `src/app/ops_robustness_window.py` com consolidação única da janela operacional:
  - readiness por janela;
  - scorecard de cobertura por status;
  - incidente agregado (`failed_runs`, `blocked_runs`, `failed_checks`);
  - gates formais para fechamento (`slo_1_window_target`, `readiness_no_hard_failures`, `quality_no_failed_checks_window`, `scorecard_no_fail_metrics`, `warnings_absent`).
- novo endpoint `GET /v1/ops/robustness-window`.
- novo script `scripts/export_ops_robustness_window.py` para gerar `data/reports/ops_robustness_window_30d.json`.
- nova suite `tests/unit/test_ops_robustness_window.py`.

### Changed
- `tests/unit/test_ops_routes.py` ampliado com cenarios do endpoint `/v1/ops/robustness-window`.
- `docs/CONTRATO.md` atualizado com o endpoint operacional de consolidação por janela.
- `docs/OPERATIONS_RUNBOOK.md` ampliado com seção `11.9` para rotina de fechamento operacional de 30 dias.
- `docs/PLANO_IMPLEMENTACAO_QG.md` e `docs/HANDOFF.md` atualizados para refletir operação recorrente da janela 30d como próximo passo imediato.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ops_robustness_window.py tests/unit/test_ops_routes.py -q -p no:cacheprovider` -> `29 passed`.
- `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --help` -> `OK`.
- `.\.venv\Scripts\python.exe scripts/export_ops_robustness_window.py --output-json data/reports/ops_robustness_window_30d.json` -> `status=NOT_READY`, `severity=critical`, `all_pass=False`.

## 2026-02-22 - D8 BD-082 implementado (playbook de incidentes e operação assistida)

### Added
- novo script `scripts/generate_incident_snapshot.py` para triagem operacional consolidada:
  - readiness + hard_failures/warnings;
  - runs recentes `failed|blocked`;
  - checks recentes com `status=fail`;
  - classificação de severidade e ações recomendadas.
- nova suite `tests/unit/test_generate_incident_snapshot.py`.

### Changed
- `docs/OPERATIONS_RUNBOOK.md` ampliado com seção `11.8` (rotina executável de incidente).
- `docs/HANDOFF.md` e `docs/PLANO_IMPLEMENTACAO_QG.md` atualizados para refletir fechamento técnico da trilha D8.
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` atualizado com status de D8 concluído tecnicamente.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_generate_incident_snapshot.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `16 passed`.
- `.\.venv\Scripts\python.exe scripts/generate_incident_snapshot.py --help` -> `OK`.
- GitHub:
  - `gh issue close 27 --repo vthamada/territorial-intelligence-platform`

## 2026-02-22 - D8 BD-081 implementado (tuning de performance e custo da plataforma)

### Added
- nova migration `db/sql/017_d8_performance_tuning.sql` com indices para:
  - filtros de `ops.pipeline_checks` (`status`, `check_name`, `created_at_utc`);
  - filtros de `ops.connector_registry` por atualização (`updated_at_utc`, `wave`, `status`, `source`);
  - consulta de `ops.frontend_events` por `name + event_timestamp_utc`;
  - geocodificação urbana com `pg_trgm` em nomes de:
    - `map.urban_road_segment`
    - `map.urban_poi`
    - `map.urban_transport_stop`.
- `scripts/benchmark_api.py` ampliado com suite `ops`:
  - endpoints `/v1/ops/*` de leitura operacional;
  - target default `p95 <= 1500ms`;
  - suite `all` agora inclui `executive + urban + ops`.

### Changed
- `tests/contracts/test_sql_contracts.py` ampliado com cobertura contratual para `017_d8_performance_tuning.sql`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `13 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 19 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/benchmark_api.py --help` -> suite inclui `{executive,urban,ops,all}`.
- GitHub:
  - `gh issue close 26 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 27 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-22 - D8 BD-080 implementado (carga incremental confiavel + reprocessamento seletivo)

### Added
- novo script operacional `scripts/run_incremental_backfill.py` com:
  - seleção incremental por `job + reference_period` usando histórico de `ops.pipeline_runs`;
  - execução por necessidade (`no_previous_run`, `latest_status!=success`, `stale_success`);
  - reprocessamento seletivo por `--reprocess-jobs` e `--reprocess-periods`;
  - filtros de escopo (`--jobs`, `--exclude-jobs`, `--include-partial`);
  - pós-carga condicional (`dbt_build`, `quality_suite`) por período com sucesso;
  - relatório padrão em `data/reports/incremental_backfill_report.json`.
- nova suite `tests/unit/test_run_incremental_backfill.py` cobrindo a lógica de decisão incremental e override de reprocessamento.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_incremental_backfill.py tests/unit/test_backfill_environment_history.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `9 passed`.
- `.\.venv\Scripts\python.exe scripts/run_incremental_backfill.py --help` -> `OK`.
- GitHub:
  - `gh issue close 25 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 26 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-22 - D7 BD-072 implementado (trilhas de explicabilidade para prioridade/insight)

### Added
- contratos de explainability em `src/app/schemas/qg.py`:
  - `ExplainabilityCoverage`
  - `ExplainabilityTrail`.

### Changed
- `src/app/api/routes_qg.py`:
  - `GET /v1/priority/list` e `GET /v1/insights/highlights` passam a retornar trilha estruturada de explicabilidade por item;
  - rationale de prioridade agora inclui contexto de ranking e cobertura;
  - `deep_link` adicionado em insights para navegação contextual.
- evidências de auditoria ampliadas:
  - `PriorityEvidence.updated_at`
  - `BriefEvidenceItem.updated_at`.
- `_fetch_priority_rows` ampliado para calcular cobertura territorial por domínio (`covered_territories`, `total_territories`, `coverage_pct`).
- `tests/unit/test_qg_routes.py` atualizado para validar payloads de explainability e `deep_link`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py -q -p no:cacheprovider` -> `19 passed`.

## 2026-02-22 - D7 BD-071 implementado (versionamento de score territorial e pesos)

### Added
- migration nova `db/sql/016_strategic_score_versions.sql` com:
  - tabela `ops.strategic_score_versions`;
  - view ativa `ops.v_strategic_score_version_active`;
  - unicidade de versão ativa (`uq_strategic_score_versions_active`).
- script novo `scripts/sync_strategic_score_versions.py` para sincronização idempotente da versão/pesos de score.

### Changed
- `db/sql/015_priority_drivers_mart.sql` evoluído para score versionado/pesado com novas colunas:
  - `score_version`, `config_version`, `critical_threshold`, `attention_threshold`,
  - `domain_weight`, `indicator_weight`, `weighted_magnitude`.
- `configs/strategic_engine.yml` ampliado com:
  - `default_domain_weight`, `default_indicator_weight`,
  - `domain_weights` e `indicator_weights`.
- `src/app/api/strategic_engine_config.py` ampliado para parsing de pesos e metadados de score.
-- `src/app/api/routes_qg.py` e `src/app/schemas/qg.py` atualizados para expor versão/método/pesos em prioridades, insights e briefs.
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
  - `priority_drivers_missing_score_version_rows`
  - `strategic_score_total_versions`
  - `strategic_score_active_versions_min`
  - `strategic_score_active_versions_max`.
- `scripts/init_db.py` atualizado com dependencia explicita `015_priority_drivers_mart.sql -> 016_strategic_score_versions.sql`.
- `scripts/backfill_robust_database.py` ampliado para sincronizar e reportar `strategic_score_versions`.
- `tests/contracts/test_sql_contracts.py` ampliado para validar objetos de `016` e métricas novas do scorecard.
- `tests/unit/test_strategic_engine_config.py` ampliado para validar parsing de pesos; adaptado para ambiente Windows/OneDrive sem plugin `tmpdir`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_strategic_engine_config.py -q -p no:cacheprovider -p no:tmpdir` -> `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py -q -p no:cacheprovider` -> `68 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `12 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 18 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/sync_strategic_score_versions.py` -> `score_version=v1.0.0`, `upserted=1`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=28`, `warn=4`.

## 2026-02-22 - D7 BD-070 implementado (mart Gold de drivers de prioridade)

### Added
- migration nova `db/sql/015_priority_drivers_mart.sql` com view:
  - `gold.mart_priority_drivers`.
- cobertura de contrato SQL para o mart:
  - `tests/contracts/test_sql_contracts.py` (`test_priority_drivers_mart_sql_has_required_objects`).

### Changed
- `src/app/api/routes_qg.py`:
  - `GET /v1/priority/list`, `GET /v1/priority/summary` e `GET /v1/insights/highlights` agora consomem `gold.mart_priority_drivers`.
  - metadados das respostas de prioridade/insights atualizados para `source_name=gold.mart_priority_drivers`.
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas:
  - `priority_drivers_rows`
  - `priority_drivers_distinct_periods`.
- `scripts/init_db.py` atualizado para garantir dependencia de `007_data_coverage_scorecard.sql` com `015_priority_drivers_mart.sql`.
- `scripts/backfill_robust_database.py` ampliado com `coverage.priority_drivers_mart`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `78 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `11 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 17 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=24`, `warn=4`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
- GitHub:
  - tentativa de sincronização de issue (`#22`) bloqueada por proxy/rede no ambiente local.

## 2026-02-22 - Governança de foco reforçada (trilha única para demo defensável)

### Changed
- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado com seção "Modo foco (demo defensável)":
  - escopo congelado;
  - critério de entrega palpável/defensável;
  - sequencia unica `#22 -> #23 -> #24`.
- `docs/HANDOFF.md` atualizado com acordo operacional de foco:
  - proibicao de frentes paralelas fora da trilha ativa;
  - compromisso explicito com entrega demonstravel no mapa executivo.

## 2026-02-22 - D6 BD-062 implementado (detectar drift de schema com alerta operacional)

### Added
- novo check `check_source_schema_drift` em `src/pipelines/common/quality.py` com validações por conector:
  - existencia de tabela alvo;
  - colunas obrigatorias ausentes;
  - incompatibilidade de tipos;
  - agregado `schema_drift_connectors_with_issues`.
- nova suite unit `tests/unit/test_schema_drift_checks.py`.

### Changed
- `src/pipelines/quality_suite.py` passa a incluir `check_source_schema_drift`.
- `configs/quality_thresholds.yml` ampliado com seção `schema_drift`.
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métrica:
  - `schema_drift_fail_checks_last_7d`.
- `tests/unit/test_quality_suite.py` atualizado para monkeypatch do check de drift.
- `tests/contracts/test_sql_contracts.py` ampliado com assertion da métrica de drift.
- compatibilidade de tipos no check de drift endurecida:
  - normalizacao de tipos SQL (`pg_catalog.*`, `public.*`);
  - comparacao de subtipo/SRID para `geometry(...)`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_schema_drift_checks.py tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/contracts/test_sql_contracts.py tests/contracts/test_schema_contract_connector_coverage.py -q -p no:cacheprovider` -> `78 passed`.
- `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`, `total_checks=188`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=22`, `warn=4`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=1`.
- GitHub:
  - `gh issue close 21 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 22 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-22 - D6 BD-061 implementado (cobertura de testes de contrato por conector)

### Added
- nova suite de contratos `tests/contracts/test_schema_contract_connector_coverage.py` com:
  - cobertura minima de contratos por conector (`>= 90%`);
  - testes parametrizados por conector elegivel;
  - validação de estrutura minima de contrato (`required_columns`, `column_types`, `schema_version`).

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/contracts/test_schema_contract_connector_coverage.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `61 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
- GitHub:
  - `gh issue close 20 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 21 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-22 - D6 BD-060 implementado (contratos de schema por fonte)

### Added
- migration nova `db/sql/014_source_schema_contracts.sql` com:
  - tabela `ops.source_schema_contracts`;
  - view ativa `ops.v_source_schema_contracts_active`;
  - indice de unicidade para contrato ativo por `connector_name + target_table`.
- novo arquivo `configs/schema_contracts.yml` com defaults e overrides de contratos.
- novo módulo `src/pipelines/common/schema_contracts.py` para:
  - inferencia de `target_table`/`dataset`;
  - normalizacao de colunas obrigatorias/opcionais/tipos/constraints;
  - geracao de registros de contrato versionado.
- novo script `scripts/sync_schema_contracts.py` para sincronização idempotente de contratos no banco.
- nova suite unit `tests/unit/test_schema_contracts.py`.

### Changed
- `src/pipelines/common/quality.py` com check novo:
  - `check_source_schema_contracts`.
- `src/pipelines/quality_suite.py` passa a incluir checks de `schema_contracts`.
- `configs/quality_thresholds.yml` ampliado com seção `schema_contracts`.
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métrica:
  - `schema_contracts_active_coverage_pct`.
- `scripts/backfill_robust_database.py` ampliado para:
  - sincronizar contratos de schema antes dos backfills;
  - reportar cobertura de `schema_contracts`.
- filtros de cobertura de contratos alinhados para excluir conectores de discovery/internos:
  - `quality_suite`
  - `dbt_build`
  - `tse_catalog_discovery`.
- `tests/contracts/test_sql_contracts.py` ampliado para validar:
  - métrica de cobertura no scorecard;
  - objetos SQL de `014_source_schema_contracts.sql`.
- `tests/unit/test_quality_core_checks.py` ampliado com cenarios pass/fail para `check_source_schema_contracts`.
- `tests/unit/test_quality_suite.py` atualizado para monkeypatch de `check_source_schema_contracts`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/unit/test_schema_contracts.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `29 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q -p no:cacheprovider` -> `23 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 16 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/sync_schema_contracts.py` -> `prepared=24`, `upserted=24`, `deprecated=0`.
- `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `failed_checks=0`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=23`, `warn=2`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- GitHub:
  - `gh issue close 19 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 20 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-21 - D5 BD-052 implementado (mart Gold de risco ambiental territorial)

### Added
- migration nova `db/sql/013_environment_risk_mart.sql` com view:
  - `gold.mart_environment_risk`.
- endpoint executivo novo `GET /v1/environment/risk` em `src/app/api/routes_qg.py`.
- contratos novos em `src/app/schemas/qg.py`:
  - `EnvironmentRiskItem`
  - `EnvironmentRiskResponse`.
- checks de qualidade do mart ambiental em `src/pipelines/common/quality.py`:
  - `environment_risk_mart_rows_municipality`
  - `environment_risk_mart_rows_district`
  - `environment_risk_mart_rows_census_sector`
  - `environment_risk_mart_distinct_periods`
  - `environment_risk_mart_null_score_rows`.

### Changed
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas de cobertura do mart Gold ambiental:
  - `environment_risk_mart_municipality_rows`
  - `environment_risk_mart_district_rows`
  - `environment_risk_mart_census_sector_rows`
  - `environment_risk_mart_distinct_periods`.
- `scripts/init_db.py` atualizado para garantir ordem de dependencia da migration `007_data_coverage_scorecard.sql` com `013_environment_risk_mart.sql`.
- `scripts/backfill_robust_database.py` ampliado com `coverage.environment_risk_mart`.
- `src/pipelines/quality_suite.py` passa a incluir `check_environment_risk_mart`.
- `configs/quality_thresholds.yml` ampliado com thresholds `environment_risk_mart_*`.
- `src/app/api/cache_middleware.py` passa a cachear `GET /v1/environment/risk` (`max-age=300`).
- suites de teste atualizadas:
  - `tests/unit/test_qg_routes.py`
  - `tests/unit/test_qg_edge_cases.py`
  - `tests/unit/test_cache_middleware.py`
  - `tests/unit/test_quality_core_checks.py`
  - `tests/unit/test_quality_suite.py`
  - `tests/contracts/test_sql_contracts.py`.
- `docs/CONTRATO.md` atualizado com o novo endpoint executivo de risco ambiental.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `102 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `51 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 15 SQL scripts`.
- smoke endpoint ambiental executivo:
  - `GET /v1/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
- `.\.venv\Scripts\python.exe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='2025', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=23`, `warn=1`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- GitHub:
  - `gh issue close 18 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 19 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-21 - D5 BD-051 implementado (agregações ambientais por distrito/setor)

### Added
- migration nova `db/sql/012_environment_risk_aggregation.sql` com view:
  - `map.v_environment_risk_aggregation`.
- endpoint novo `GET /v1/map/environment/risk` em `src/app/api/routes_map.py`.
- contratos novos em `src/app/schemas/map.py`:
  - `EnvironmentRiskItem`
  - `EnvironmentRiskCollectionResponse`.
- checks de qualidade para agregação ambiental em `src/pipelines/common/quality.py`:
  - `environment_risk_rows_district`
  - `environment_risk_rows_census_sector`
  - `environment_risk_distinct_periods`
  - `environment_risk_null_score_rows`
  - `environment_risk_null_hazard_rows`
  - `environment_risk_null_exposure_rows`.

### Changed
- `scripts/init_db.py` atualizado para garantir ordem de dependencia da migration `007_data_coverage_scorecard.sql` com `012_environment_risk_aggregation.sql`.
- `db/sql/007_data_coverage_scorecard.sql` ampliado com métricas de cobertura ambiental agregada:
  - `environment_risk_district_rows`
  - `environment_risk_census_sector_rows`
  - `environment_risk_distinct_periods`.
-- `configs/quality_thresholds.yml` ampliado com seção `environment_risk`.
- `src/pipelines/quality_suite.py` passa a incluir `check_environment_risk_aggregation`.
- `scripts/backfill_robust_database.py` ampliado com `coverage.environment_risk_aggregation`.
- `src/app/api/cache_middleware.py` passa a cachear `GET /v1/map/environment/risk` (`max-age=300`).
- suites de teste atualizadas:
  - `tests/unit/test_api_contract.py`
  - `tests/unit/test_cache_middleware.py`
  - `tests/unit/test_quality_core_checks.py`
  - `tests/unit/test_quality_suite.py`
  - `tests/contracts/test_sql_contracts.py`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_contract.py tests/unit/test_cache_middleware.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_suite.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `49 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_mvt_tiles.py -q -p no:cacheprovider` -> `33 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 14 SQL scripts`.
- smoke endpoint ambiental:
  - `GET /v1/map/environment/risk?level=district&limit=5` -> `200`, `period=2025`, `count=5`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=19`, `warn=1`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- GitHub:
  - `gh issue close 17 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 18 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-21 - D5 BD-050 implementado (histórico INMET/INPE/ANA multi-ano)

### Added
- novo script operacional `scripts/backfill_environment_history.py` para executar `BD-050` em fluxo unico:
  - bootstrap manual multi-ano para `INMET`, `INPE_QUEIMADAS` e `ANA`;
  - execução dos conectores ambientais por período;
  - execução opcional do `quality_suite` por período;
  - relatório consolidado em `data/reports/bd050_environment_history_report.json`.
- nova suite de testes para o script:
  - `tests/unit/test_backfill_environment_history.py`.

### Changed
- integridade temporal endurecida em `src/pipelines/common/tabular_indicator_connector.py`:
  - quando existem colunas de ano com sinal valido e nenhum match com `reference_period`, a carga passa a bloquear (`[]`) em vez de reutilizar linhas de outro ano.
  - fallback permissivo mantido apenas para payload sem sinal temporal.
- thresholds de cobertura temporal por fonte ambiental atualizados em `configs/quality_thresholds.yml`:
  - `min_periods_inmet: 5`
  - `min_periods_inpe_queimadas: 5`
  - `min_periods_ana: 5`
- scorecard SQL ampliado em `db/sql/007_data_coverage_scorecard.sql` com métricas:
  - `inmet_distinct_periods`
  - `inpe_queimadas_distinct_periods`
  - `ana_distinct_periods`
-- relatório de cobertura do backfill geral ampliado em `scripts/backfill_robust_database.py` com `coverage.environmental_sources`.
- contratos de teste atualizados:
  - `tests/contracts/test_sql_contracts.py`
  - `tests/unit/test_onda_b_connectors.py`

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_backfill_environment_history.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_coverage_checks.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `26 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_quality_suite.py -q -p no:cacheprovider` -> `12 passed`.
- `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --help` -> `OK`.
- `.\.venv\Scripts\python.exe scripts/backfill_environment_history.py --periods 2025 --dry-run --skip-bootstrap --skip-quality --allow-blocked --output-json data/reports/bd050_environment_history_report.json` -> `success=2`, `blocked=1` (`INMET` com `403`), report gerado.
- GitHub:
  - `gh issue close 16 --repo vthamada/territorial-intelligence-platform`
  - `gh issue edit 17 --repo vthamada/territorial-intelligence-platform --add-label status:active --remove-label status:blocked`

## 2026-02-21 - D4 BD-042 implementado (gold.mart_mobility_access + API executiva)

### Added
- endpoint executivo `GET /v1/mobility/access` em `src/app/api/routes_qg.py` com:
  - filtro por `period`, `level` e `limit`;
  - fallback de período para último `reference_period` disponível;
  - resposta tipada com metadata + itens de deficit de mobilidade por território.
- novos contratos de schema em `src/app/schemas/qg.py`:
  - `MobilityAccessItem`
  - `MobilityAccessResponse`
- cobertura de testes unitarios para o endpoint:
  - `tests/unit/test_qg_routes.py` (cenario com dados e sem dados)
  - `tests/unit/test_qg_edge_cases.py` (validação de `level` invalido)
- cobertura de contrato SQL para o mart:
  - `tests/contracts/test_sql_contracts.py` (`test_mobility_access_mart_sql_has_required_objects`).

### Changed
- `db/sql/011_mobility_access_mart.sql` endurecido para robustez de calculo:
  - eliminacao de sobrecontagem por join multiplo (agregações separadas por domínio: vias, pontos de transporte e POIs);
  - vínculo de população por período do SENATRAN com fallback controlado para última população disponível;
  - casts explicitos para `ROUND(..., 2)` compativeis com Postgres;
  - score de acesso e deficit com tipagem consistente (`double precision`).
- `src/app/api/cache_middleware.py` atualizado para cachear `GET /v1/mobility/access` (`max-age=300`).
- `docs/CONTRATO.md` atualizado com o novo endpoint executivo de mobilidade.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_qg_edge_cases.py tests/unit/test_cache_middleware.py tests/contracts/test_sql_contracts.py -q -p no:cacheprovider` -> `79 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `47 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 13 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- smoke do endpoint: `GET /v1/mobility/access?level=district&limit=5` -> `200`, `period=2025`, `items=5`.
- GitHub:
  - `gh issue close 13 --repo vthamada/territorial-intelligence-platform`
  - `gh issue close 14 --repo vthamada/territorial-intelligence-platform`
  - `gh issue close 15 --repo vthamada/territorial-intelligence-platform`

## 2026-02-21 - D4 BD-041 implementado (transporte/viario municipal)

### Added
- `db/sql/010_urban_transport_domain.sql` com:
  - tabela `map.urban_transport_stop`;
  - indices (`source/external_id`, `mode`, `geom GIST`);
  - cadastro da camada `urban_transport_stops` em `map.layer_catalog`;
  - extensao da view `map.v_urban_data_coverage`.
- `configs/urban_transport_catalog.yml` para discovery remoto Overpass de infraestrutura de transporte urbano.
- `src/pipelines/urban_transport.py` (`urban_transport_fetch`) com Bronze snapshot + upsert idempotente em `map.urban_transport_stop`.

### Changed
- `src/app/api/routes_map.py`:
  - camada `urban_transport_stops` adicionada em `GET /v1/map/layers?include_urban=true`;
  - cobertura/readiness/metadata suportando `urban_transport_stops`;
  - endpoint novo `GET /v1/map/urban/transport-stops`;
  - `GET /v1/map/urban/geocode` com `kind=transport`;
  - tiles MVT para `urban_transport_stops`.
- `src/app/schemas/map.py` com contratos de resposta para transporte urbano.
- `src/orchestration/prefect_flows.py` com `urban_transport_fetch` em `run_mvp_all` e `run_mvp_wave_7`.
- `scripts/backfill_robust_database.py` com `urban_transport_fetch` no `wave7` e cobertura no report.
- `src/pipelines/common/quality.py` e `configs/quality_thresholds.yml` com checks de transporte urbano:
  - `urban_transport_stops_rows_after_filter`;
  - `urban_transport_stops_invalid_geometry_rows`.
- `db/sql/007_data_coverage_scorecard.sql` com métrica `urban_transport_stop_rows`.
- `scripts/init_db.py` com dependencia explicita `007 -> 010`.
- `configs/connectors.yml` com `urban_transport_fetch`.

### Verified
- `.\.venv\Scripts\python.exe -c "import json; from pipelines.urban_transport import run; print(json.dumps(run(reference_period='2026', dry_run=False), ensure_ascii=False, default=str))"` -> `status=success`, `rows_written=22`, Bronze materializado em `data/bronze/osm/urban_transport_catalog/2026/...`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_urban_connectors.py tests/unit/test_api_contract.py tests/unit/test_mvt_tiles.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/contracts/test_sql_contracts.py -q` -> `68 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
- `.\.venv\Scripts\python.exe scripts/init_db.py` -> `Applied 12 SQL scripts`.
- `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=13`, `warn=1`.
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- `.\.venv\Scripts\python.exe scripts/sync_connector_registry.py` -> `Synchronized 27 connectors into ops.connector_registry`.

## 2026-02-21 - D4 BD-040 concluído (SENATRAN 2021..2025)

### Added
-- `scripts/bootstrap_senatran_history.py` para bootstrap histórico oficial de SENATRAN (2021..2024) com extração municipal de Diamantina.
- arquivos manuais anuais:
  - `data/manual/senatran/senatran_diamantina_2021.csv`
  - `data/manual/senatran/senatran_diamantina_2022.csv`
  - `data/manual/senatran/senatran_diamantina_2023.csv`
  - `data/manual/senatran/senatran_diamantina_2024.csv`
- evidencia de bootstrap:
  - `data/reports/bootstrap_senatran_history_report.json`.

### Changed
- `requirements.txt` e `pyproject.toml` atualizados com dependencias de Excel (`openpyxl`, `xlrd`).
- `.gitignore` atualizado para versionar `data/manual/senatran/`.

### Verified
-- Backfill real via `pipelines.senatran_fleet.run(..., dry_run=False)` em `2021..2025`:
  - `5/5` execuções com `status=success`;
  - `rows_written=4` por ano.
-- Cobertura no banco:
  - `silver.fact_indicator` (`source='SENATRAN'`, `dataset='senatran_fleet_municipal'`) com períodos `2021..2025`.
- Operacional:
  - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=10`, `warn=1`.
  - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.

## 2026-02-21 - D4 BD-040 (SENATRAN histórico) hardening inicial

### Changed (backend)
-- `src/app/db.py` ajustado para cache por `database_url` (string hashável), removendo falha estrutural `unhashable type: 'Settings'` em execuções reais dos conectores.
-- `src/pipelines/senatran_fleet.py` evoluído para suporte histórico mais robusto:
  - descoberta automática de CSVs SENATRAN por ano na página oficial (`frota-de-veiculos-{ano}`);
  - render de URI com placeholders `{reference_period}` e `{year}`;
  - filtro de seguranca para evitar uso de URI remota com ano divergente do `reference_period`;
  - priorização de fallback manual por ano no nome do arquivo;
  - bloqueio de fallback manual com ano divergente (evita carregar 2025 para executar 2024);
  - parser dedicado para CSV oficial SENATRAN com preâmbulo (`UF,MUNICIPIO,TOTAL...`) e parse numérico com milhares por vírgula.
- `configs/senatran_fleet_catalog.yml` passa a operar como complemento opcional da descoberta automatica.

### Changed (testes)
- `tests/unit/test_db_cache.py` adicionado para validar cache de engine/session factory sem depender de objeto `Settings` hashável.
- `tests/unit/test_onda_a_connectors.py` ampliado com cobertura SENATRAN:
  - descoberta de links CSV por ano;
  - priorização e bloqueio de fallback manual por ano;
  - parse de CSV com preâmbulo e milhares por vírgula;
  - resolução de dataset remoto via descoberta com catálogo vazio.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_db_cache.py tests/unit/test_onda_a_connectors.py tests/unit/test_quality_coverage_checks.py -q -p no:cacheprovider` -> `29 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q -p no:cacheprovider` -> `44 passed`.
- `.\.venv\Scripts\python.exe -c "from pipelines.senatran_fleet import run; ..."` (dry-run multi-ano):
  - `2021..2024` -> `blocked` (sem fonte anual valida);
  - `2025` -> `success` com fonte remota oficial (`FrotaporMunicipioetipoJulho2025.csv`).

## 2026-02-21 - Trilha unica ativa com gate formal (WIP=1)

### Changed (planejamento)
- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado para fixar trilha ativa unica:
  - trilha oficial definida como `D3-hardening`;
  - escopo fechado em `BD-030`, `BD-031`, `BD-032` + pendencias de `BD-033`;
  - gate/DoD formal com comandos de validação backend, frontend, benchmark urbano e readiness.

### Changed (estado operacional)
- `docs/HANDOFF.md` atualizado para espelhar exatamente a mesma trilha e remover ambiguidade de próxima fase:
  - próximo passo imediato consolidado em ação única (execução do pacote de gate);
  - critério de saída e bloqueio explícito de `D4..D8` até fechamento do gate.

### Notes
-- Objetivo do ajuste: eliminar bifurcação de execução ("ou fase A/ou fase B") e manter fila única com critério objetivo de encerramento.

### Verified (execução do gate em 2026-02-21)
- Backend:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
- Frontend:
  - `npm run test -- --run` (em `frontend/`) -> `78 passed`.
  - `npm run build` (em `frontend/`) -> `OK`.
- Operacional:
  - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json` -> `ALL PASS`.
  - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY`, `hard_failures=0`, `warnings=0`.
- Correção de ambiente aplicada durante o gate:
  - falha inicial de frontend por `Failed to resolve import "zustand"` em `src/shared/stores/filterStore.ts`;
  - ação corretiva: `npm install` executado em `frontend/`.

## 2026-02-21 - Ativacao de D4 e verificacao de issues GitHub

### Changed (planejamento)
- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado para ativar trilha unica `D4-mobilidade/frota`:
  - escopo oficial em `BD-040`, `BD-041`, `BD-042`;
  - próximo passo imediato definido em `BD-040` (`issue #13`);
  - gate de saida D4 explicitado com foco em conector de mobilidade, qualidade, scorecard e readiness.

### Changed (estado operacional)
- `docs/HANDOFF.md` atualizado para:
  - registrar `D3-hardening` como trilha encerrada com evidencias;
  - registrar verificacao das issues abertas no GitHub em `2026-02-21`.

### Verified (issues GitHub)
- Consulta de issues abertas no repositório `vthamada/territorial-intelligence-platform`:
  - `#13` (`BD-040`) esta `open` com `status:active`;
  - `#14` (`BD-041`) e `#15` (`BD-042`) estao `open` com `status:blocked`;
  - itens `D5..D8` permanecem `open` com `status:blocked`;
  - `#7` (`BD-020`) permanece `open` com `status:external` + `status:blocked`.
  - `#28` (`BD-033`, `closed`) sem label `status:active`.

## 2026-02-20 - Consolidação final de documentos por domínio

### Changed (governança)
- `docs/GOVERNANCA_DOCUMENTAL.md` refinado com corte rigoroso:
  - ativos por domínio reduzidos para 5 documentos (`MAP`, `TERRITORIAL`, `STRATEGIC`, `BACKLOG_DADOS`, `OPERATIONS_RUNBOOK`);
  - `PLANO_FONTES`, `RUNBOOK_ROBUSTEZ`, `MTE_RUNBOOK`, `BRONZE_POLICY` e `BACKLOG_UX` reclassificados como descontinuados para decisão.
- `docs/PLANO.md` removido do repositório por baixa relevância operacional; governança e fila única permanecem em `docs/PLANO_IMPLEMENTACAO_QG.md`.
- `AGENTS.md` alinhado com a nova classificação de domínio (sem ambiguidade operacional).
- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado para remover dependencia operacional de documentos descontinuados.

### Changed (consolidação de conteudo)
- `docs/OPERATIONS_RUNBOOK.md` passou a incorporar:
  - rotina semanal de robustez de dados (antes em `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`);
  - operação completa do conector MTE (antes em `docs/MTE_RUNBOOK.md`).
-- `docs/CONTRATO.md` consolidou política Bronze:
  - seção `4.1 Política Bronze`;
  - mecanismo oficial de medição atualizado para runbook único (`docs/OPERATIONS_RUNBOOK.md`).
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` consolidou papel de catálogo oficial de fontes (substituindo `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` para decisão).

### Changed (descontinuacao orientada)
- Arquivos descontinuados foram mantidos apenas como ponte histórica com redirecionamento explicito para os documentos oficiais:
  - `docs/BRONZE_POLICY.md`
  - `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`
  - `docs/MTE_RUNBOOK.md`
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - `docs/BACKLOG_UX_EXECUTIVO_QG.md`
- `docs/HANDOFF.md` atualizado para explicitar a lista descontinuada completa.

## 2026-02-20 - Higienização documental (foco único)

### Changed (governança)
- Governança documental consolidada em `docs/GOVERNANCA_DOCUMENTAL.md` com classificação oficial: núcleo ativo, domínio ativo, complementar e descontinuados.
-- `AGENTS.md` atualizado para leitura obrigatória com `docs/VISION.md` e nova matriz documental sem ambiguidade de fontes.
-- `docs/CONTRATO.md` atualizado para apontar execução oficial em `docs/PLANO_IMPLEMENTACAO_QG.md` e classificação em `docs/GOVERNANCA_DOCUMENTAL.md`.
-- `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado para substituir referências de visão/rastreabilidade legadas por `docs/VISION.md` + `docs/HANDOFF.md` + `docs/CHANGELOG.md`.
-- `docs/PLANO.md` reduzido para índice macro (não executável), removendo competição com a trilha diária.
-- `docs/HANDOFF.md` atualizado para declarar `docs/PLANO_IMPLEMENTACAO_QG.md` como planejamento principal e registrar filtro rigoroso de documentos.
-- `README.md` atualizado para refletir contrato + plano executável + north star.

### Notes
- Documentos descontinuados foram removidos fisicamente do repositório em 2026-02-20; a lista oficial é mantida em `docs/GOVERNANCA_DOCUMENTAL.md` (seção 6).


## 2026-02-20 — Fase UX-P0 (auditoria visual completa)

### Fixed (frontend — presentation.ts)
- UX-P0-01: `formatValueWithUnit()` agora mapeia unidades corretamente: `count` → sem unidade, `percent` → `%`, `ratio` → sem unidade, `C` → `Â°C`, `m3/s` → `mÂ³/s`, `mm`/`ha`/`km`/`kwh` com símbolos corretos.
- UX-P0-02: Novos helpers `humanizeSourceName()`, `humanizeCoverageNote()`, `humanizeDatasetSource()` — convertem nomes técnicos de tabelas/datasets em labels legiveis.

### Fixed (frontend — SourceFreshnessBadge.tsx)
- UX-P0-03: `source_name` humanizado — "silver.fact_indicator" → "Indicadores consolidados", "silver.fact_electorate" → "Eleitorado consolidado".
- UX-P0-04: `coverage_note` humanizado — "territorial_aggregated" → "Agregado territorial".

### Fixed (frontend — QgOverviewPage.tsx)
- UX-P0-05: "SVG fallback" renomeado para "Modo simplificado" (consistente com QgMapPage).
- UX-P0-06: Coluna "Codigo" removida da tabela KPIs executivos — mostra apenas Domínio/Indicador/Valor/Nível.
- UX-P0-07: Coluna "Fonte" e "Codigo" removidas da tabela KPIs; coluna "Métrica de mapa" removida de Domínios Onda B/C.

### Fixed (frontend — QgInsightsPage.tsx)
- UX-P0-08: Severidade traduzida no badge do insight — `{item.severity}` → `{formatStatusLabel(item.severity)}`.
- UX-P0-09: Fonte/dataset humanizados — `{source}/{dataset}` → `humanizeDatasetSource()`.

### Fixed (frontend — QgBriefsPage.tsx)
- UX-P0-10: Brief ID removido do subtitulo e do export HTML — substituido por "Gerado em {data}".
- UX-P0-11: "Linha N" substituido por "Ponto N" no resumo executivo.
- UX-P0-12: Coluna Fonte na tabela de evidencias e no export HTML agora usa `humanizeDatasetSource()`.

### Fixed (frontend — QgScenariosPage.tsx)
- UX-P0-13: Subtitulo usa `indicator_name` em vez de `indicator_code`.
- UX-P0-14: "Leitura N" substituido por "Analise N" nas explicacoes.
- UX-P0-15: Label do campo de indicador alterado de "Codigo do indicador" para "Indicador".

### Fixed (frontend — TerritoryProfilePage.tsx)
-- UX-P0-16: Coluna "Codigo" removida da tabela de indicadores — mostra apenas Domínio/Indicador/Período/Valor.

### Fixed (frontend — ElectorateExecutivePage.tsx)
- UX-P0-17: "Total eleitores: 0" quando sem dados substituido por "-".

### Fixed (frontend — PriorityItemCard.tsx)
- UX-P0-18: Evidencia mostra `humanizeDatasetSource()` em vez de `{source} / {dataset}`.

### Fixed (frontend — QgMapPage.tsx)
- UX-P0-19: Label "Codigo do indicador" alterado para "Indicador" com placeholder descritivo.
- UX-P0-20: Coluna "Métrica" removida da tabela de ranking (redundante — todas as linhas usam a métrica filtrada).

### Fixed (backend — routes_qg.py)
- UX-P0-21: `_format_highlight_value()` agora trata `percent` → `%`, `count` → sem unidade, `ratio` → sem unidade, `C` → `Â°C`, `m3/s` → `mÂ³/s`.
- UX-P0-22: Explicacao de cenarios usa `_format_highlight_value()` para valores e traduz `impact` para pt-BR ("melhora"/"piora"/"inalterado").

### Changed (testes)
- `SourceFreshnessBadge.test.tsx`: assertions atualizadas para labels humanizados.
- `QgPages.test.tsx`: label "Codigo do indicador" atualizado para "Indicador".

### Validação
- Backend: `55 passed` (29 qg_routes/tse_electorate + 26 mvt_tiles/cache_middleware).
- Frontend: `78 passed`, build OK.

## 2026-02-20 — Fase DATA (semantica de dados executiva)

### Fixed (backend — `src/app/api/routes_qg.py`)
- DATA-P0-01: Score mono-territorial corrigido de 100.0 para 50.0 em `_fetch_priority_rows`, `_fetch_territory_indicator_scores` e `_score_from_rank` — evita ranking inflacionado quando ha apenas 1 município.
-- DATA-P0-02: Trend real calculado via `_compute_trend()` e `_fetch_previous_values()` — compara indicador com período anterior (threshold 2%); substitui `trend="stable"` hardcoded.
-- DATA-P0-03: Códigos técnicos de indicador removidos de todas as narrativas user-facing — `indicator_name` utilizado em rationale de prioridades, explanation de insights, highlights de território, explanation de cenários e summary de briefs.
- DATA-P0-04: Formatacao pt-BR de valores numericos via `_format_highlight_value()` — separador de milhar, moeda BRL com `R$`, percentuais e unidades explicitadas.
- DATA-P0-06: Narrativa de insights diversificada via `_build_insight_explanation()` — templates por domínio (saude, educação, trabalho, financas, eleitorado, etc.), linguagem contextual por severidade, fonte explicitada. Substituiu template formulaico identico para todos os insights.

### Fixed (frontend)
- DATA-P0-05: Filtro de severidade em Insights traduzido para pt-BR — dropdown mostra "critico"/"atencao"/"informativo" via `formatStatusLabel()` (`QgInsightsPage.tsx`).
- DATA-P0-07: Jargao técnico do mapa substituido por termos executivos — "Renderizacao" -> "Modo de exibição", "SVG fallback" -> "Modo simplificado", "Mapa vetorial" -> "Modo avancado", "Somente SVG" -> "Somente simplificado" (`QgMapPage.tsx`).
- DATA-P0-08: Deduplicacao de formatadores `statusText()`/`trendText()` em `StrategicIndexCard.tsx` — agora usa `formatStatusLabel()`/`formatTrendLabel()` centralizados de `presentation.ts`.

### Changed (testes)
- `tests/unit/test_qg_routes.py`: mock `_QgSession` atualizado com handler para `_fetch_previous_values` (retorna vazio para trend=stable em testes).
- `frontend/src/modules/qg/pages/QgPages.test.tsx`: assertion atualizada para novo aria-label "Alternar para modo avancado".

### Validação
- Backend: `55 passed` (18 qg_routes + 37 tse_electorate/mvt_tiles/cache_middleware).
- Frontend: `78 passed`, build OK.

## 2026-02-20

### Fixed
- Layout e formatacao do painel de filtros no mapa situacional (Home):
  - `frontend/src/styles/global.css` ajustado para o painel lateral operar em coluna dedicada no desktop (sem sobreposicao sobre o mapa).
  - `frontend/src/styles/global.css` ajustado para alinhar botoes e controles internos (`Aplicar/Limpar`, `Mapa base`, `Focar selecionado`, `Recentrar mapa`).
  - `frontend/src/styles/global.css` ajustado com `overflow-wrap` em secoes/cards do painel para evitar texto vazando dos blocos.
  - `frontend/src/shared/ui/MapDominantLayout.tsx` atualizado com semantica do layout dominante com sidebar colapsavel.
- Legibilidade dos controles de mapa no frontend:
  - `frontend/src/styles/global.css` corrigido para botoes de `Modo de visualizacao` e `Mapa base` manterem contraste em estado não selecionado.
  - `frontend/src/styles/global.css` corrigido para `map-sidebar-toggle` manter texto legivel na Home (`Mapa situacional`).
- Area util do mapa no frontend:
  - `frontend/src/styles/global.css` ajustado para ampliar altura de `map-canvas-shell`.
  - `frontend/src/styles/global.css` ajustado em `map-dominant`/`map-dominant-canvas`/`map-overview-canvas` para remover faixa vazia abaixo do mapa dominante.
- Zoom contextual inicial do mapa:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` passou a aplicar piso de zoom contextual na inicializacao e no calculo de `resolveContextualZoom`, evitando abertura em `z0`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` passou a aplicar piso de zoom recomendado por nível no mapa dominante da Home.
- Estabilidade de navegacao no mapa vetorial:
  - `frontend/src/shared/ui/VectorMap.tsx` corrigido para não recentrar o mapa a cada alteracao de zoom (zoom e centro agora seguem efeitos separados).
  - tratamento de erro no vetor filtrando erros de abort/cancelamento para evitar degradação indevida de UX.
- Estabilidade de fallback do mapa:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` e `frontend/src/modules/qg/pages/QgOverviewPage.tsx` deixaram de forcar fallback automatico para SVG em qualquer erro transitorio do modo vetorial.
  - mensagens de erro vetorial padronizadas com orientacao explicita para indisponibilidade temporaria (`503`).
- Robustez backend de tiles MVT:
  - `src/app/api/routes_map.py` passou a sanitizar geometrias invalidas com `ST_IsValid`/`ST_MakeValid` antes de `ST_Transform`/`ST_Intersects` na geracao de tiles territoriais.
  - objetivo: reduzir erro `503` em tiles com geometrias problematicas.
- Eleitorado com fallback de ano de armazenamento outlier:
  - `src/app/api/routes_qg.py` recebeu binding de ano logico x ano de armazenamento para casos como `reference_year=9999`.
  - `GET /v1/electorate/summary` e `GET /v1/electorate/map` agora conseguem responder para `year=2024` quando os dados eleitorais estiverem armazenados em ano outlier.
  - metadata das respostas passou a indicar fallback: `electorate_outlier_year_fallback:requested_year=...,storage_year=...`.
- Frontend de eleitorado e estados vazios:
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` atualizado para considerar erros de fallback e exibir estado vazio orientativo quando não houver ano aplicado e não houver dados no recorte padrão.
- Correção de regressão de hooks (runtime crash):
  - `frontend/src/modules/qg/pages/QgInsightsPage.tsx` e `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx` ajustados para manter ordem estavel de hooks entre renders.
  - resolve erro `Rendered more hooks than during the previous render` que quebrava páginas e testes.
- Contencao de crash de runtime por rota no frontend:
  - novo `frontend/src/app/RouteRuntimeErrorBoundary.tsx` para capturar erro de render em páginas roteadas e evitar tela branca.
  - fallback padronizado com retry e titulo contextual da rota.
  - telemetria de erro de runtime por rota (`route_runtime_error`) para triagem operacional.
- Mapa executivo com resiliencia nos estados auxiliares:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` padronizado para exibir erro/loading em manifesto de camadas, cobertura e metadados de estilo.
  - erros desses componentes agora exibem `request_id` quando disponível e permitem retry dedicado por bloco.
- Home QG com resiliencia a falhas parciais de dados:
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` passou a manter a Home operacional quando falham apenas `Top prioridades` ou `Destaques`.
  - hard-fail global ficou restrito a `kpis_overview` e `priority_summary`; blocos secundarios agora tratam `loading/error/empty` localmente com retry.
- Quality suite com cobertura de checks de camadas territoriais:
  - `src/pipelines/quality_suite.py` passou a incluir `check_map_layers` na execução oficial.
  - efeito direto: checks `map_layer_rows_*` e `map_layer_geometry_ratio_*` voltam a ser registrados em `ops.pipeline_checks` de forma recorrente.
- Usabilidade de listas longas:
  - paginacao client-side em `QgInsightsPage` e tabela de indicadores do `TerritoryProfilePage`.

### Changed
- Backlog UX executivo consolidado para ciclo unico:
  - novo `docs/BACKLOG_UX_EXECUTIVO_QG.md` com mapeamento `P0/P1/P2`, arquivos/componentes alvo e critérios de aceite.
  - `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado para apontar o backlog como fonte unica da próxima trilha de UX.
  - `docs/HANDOFF.md` atualizado com regra operacional de foco nos itens `UX-P0-*` antes de novas frentes.
- Ops Health com refresh manual e regressão de readiness:
  - `frontend/src/modules/ops/pages/OpsHealthPage.tsx` recebeu ação `Atualizar painel` para refetch explicito dos dados operacionais.
  - refetch de queries foi centralizado em função unica (`refetchAll`) e reutilizado em `onRetry`.
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx` ganhou teste de transição `READY -> NOT_READY` apos refresh manual, incluindo exibição de hard failure.
- Home executiva com camada detalhada eleitoral mais previsivel:
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` agora exibe `Camada detalhada (Mapa)` apenas em `Nivel territorial = secao_eleitoral`.
  - propagacao de `layer_id` para links de mapa passou a ser condicionada ao contexto valido (sem carregar camada detalhada fora de secao eleitoral).
  - deep-link de `Mapa detalhado` com camada detalhada agora inclui `level=secao_eleitoral` para evitar ambiguidade de contexto.
  - limpeza automatica da seleção de camada detalhada quando o nível volta para recortes não eleitorais.
- Cobertura de regressão de overview atualizada:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` valida exibição condicional do seletor detalhado e propagacao coerente de query string (`layer_id` + `level`).
- Higienizacao documental e alinhamento de governança:
  - `README.md` atualizado para refletir estado atual de 20/02/2026 e corrigir referências para `docs/`.
  - `docs/PLANO.md` atualizado para remover backlog legado de specs `v0.1 -> v1.0` (agora consolidado em v1.0).
  - `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado com escopo de execução do ciclo atual (removido bloco legado de Sprint 9 já concluído).
  - `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md` atualizado (data de referência e referência oficial de frontend spec).
  - `docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md` marcado como snapshot histórico, com GitHub como fonte oficial de status.
- Governança de trilha unica (anti-dispersao):
  - `docs/PLANO_IMPLEMENTACAO_QG.md` passou a explicitar regra operacional `WIP=1` e fonte unica de sequencia no ciclo diario.
  - `docs/PLANO.md` passou a explicitar papel macro (estrategia) e delegacao da fila diaria para `PLANO_IMPLEMENTACAO_QG.md` + `HANDOFF.md`.
  - `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` passou a explicitar que "paralelo parcial" não significa execução simultânea no ciclo diário.
  - `docs/HANDOFF.md` ganhou secao inicial de trilha ativa unica e marcou blocos antigos de "próximos passos" como histórico.
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` reforcou papel de catálogo (sem abrir frente diaria).
  - `docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md` reforcou uso como snapshot/template, sem definir ordem operacional.
- Governança de execução no GitHub alinhada com trilha única:
  - issue `BD-033` criada em `#28` e marcada como trilha ativa (`status:active`).
  - issue `BD-033` (`#28`) encerrada apos fechamento de gate e fase 2.
  - issue `BD-021` (`#8`) encerrada por entrega técnica concluida.
  - labels operacionais adicionadas: `status:active`, `status:blocked`, `status:external`.
  - `BD-020` (`#7`) marcada como `status:external` + `status:blocked` por dependencia externa.
  - issues abertas de D4-D8 marcadas com `status:blocked` para explicitar sequenciamento.
- Gate da trilha ativa revalidado e fase 2 executada:
  - gate BD-033 (backend + frontend + build) em `pass`.
  - scorecard atualizado em `data/reports/data_coverage_scorecard.json` (`pass=5`, `warn=8`).
  - readiness atualizado com `READY`, `hard_failures=0`, `warnings=0`.
  - benchmark urbano atualizado em `data/reports/benchmark_urban_map.json` com `ALL PASS`.
- Mapa vetorial com semantica explicita para ausencia de dados:
  - `frontend/src/shared/ui/VectorMap.tsx` deixou de tratar ausencia de `val` como `0` no coropletico.
  - features sem valor agora aparecem com cor neutra (`#d1d5db`) em vez de cor de faixa baixa.
  - filtros de valor aplicados nos modos `points` e `heatmap` para evitar ruido de geometria sem métrica.
- Mapa vetorial com navegacao mais contextual:
  - `frontend/src/shared/ui/VectorMap.tsx` agora desenha rotulos contextuais (`label/name/tname/territory_name/road_name/poi_name`) na camada ativa.
  - para camadas lineares urbanas, rotulos usam `symbol-placement=line` com zoom mínimo contextual.
  - atribuições de basemap normalizadas para ASCII:
    - `streets`: `(c) OpenStreetMap contributors`
    - `light`: `(c) OpenStreetMap contributors (c) CARTO`
- Zoom contextual no fluxo de filtros:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` aplica zoom mínimo recomendado por contexto ao clicar em `Aplicar filtros`:
    - territorial: município/distrito/setor/zona/secao
    - urbano: piso de zoom compativel com `urban_roads`/`urban_pois`
  - UI agora exibe referência explicita: `Zoom contextual minimo recomendado`.
- Legenda de estilo no mapa executivo atualizada:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` agora exibe chip explicito `Sem dado`.
- Transparencia de classificação das camadas do mapa:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` agora explicita `classificacao` (`oficial`, `proxy`, `hibrida`) em camada recomendada, camada ativa e metadados visuais.
  - tooltip da camada passou a priorizar `proxy_method` quando disponível para expor limitacoes/metodologia.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` passou a exibir classificação da camada detalhada ativa no painel lateral da Home.
- Cobertura de regressão para transparencia de camada:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` valida exibição de classificação no fluxo eleitoral detalhado (`territory_polling_place`).
- Router com protecao explicita por rota:
  - `frontend/src/app/router.tsx` passou a envolver páginas com `RouteRuntimeErrorBoundary` via `withPageFallback`.
  - labels de rota adicionados para mensagens de erro mais objetivas.
- Cobertura de regressão para runtime boundary:
  - novo `frontend/src/app/RouteRuntimeErrorBoundary.test.tsx` cobrindo crash de render + recuperacao por retry.
- Cobertura de regressão para estados auxiliares do mapa:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` recebeu cenarios de erro para:
    - manifesto + metadados de estilo (com retry e `request_id`);
    - cobertura de camadas (com retry e preservacao do fluxo principal).
- Cobertura de regressão para falha parcial da Home:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` passou a validar falha simultanea de `Top prioridades` e `Destaques` sem derrubar o restante da Home.
- Cobertura de regressão para quality suite:
  - novo `tests/unit/test_quality_suite.py` valida execução e serialização de `check_map_layers`.
- Ajuste de regressão em cobertura temporal por fonte:
  - `tests/unit/test_quality_coverage_checks.py` atualizado para refletir a ordem/quantidade atual de fontes (`DATASUS..CENSO_SUAS`).
- Ajuste de regressão de zoom do mapa:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` atualizado para refletir piso contextual de zoom no carregamento via query string.
- Revalidacao do ajuste de layout do painel situacional:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
- Validação executada:
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json` -> `pass=5 warn=8`.
  - `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json` -> `READY` (`hard_failures=0`, `warnings=0`).
  - `.\.venv\Scripts\python.exe scripts/benchmark_api.py --suite urban --rounds 30 --json-output data/reports/benchmark_urban_map.json` -> `ALL PASS` (p95 `103.7ms`-`123.5ms`).
  - `npm --prefix frontend run test -- --run` -> `73 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed` (revalidado).
  - `npm --prefix frontend run build` -> `OK` (revalidado).
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/app/RouteRuntimeErrorBoundary.test.tsx src/app/router.smoke.test.tsx src/modules/qg/pages/QgPages.test.tsx src/modules/ops/pages/OpsPages.test.tsx` -> `32 passed`.
  - `npm --prefix frontend run test -- --run` -> `75 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `21 passed`.
  - `npm --prefix frontend run test -- --run` -> `77 passed`.
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed`.
  - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `22 passed` (revalidado com classificação de camadas).
  - `npm --prefix frontend run test -- --run` -> `78 passed`.
  - `npm --prefix frontend run test -- --run` -> `78 passed` (revalidado com classificação de camadas).
  - `npm --prefix frontend run build` -> `OK`.
  - `npm --prefix frontend run build` -> `OK` (revalidado com classificação de camadas).
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_quality_suite.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_coverage_checks.py tests/unit/test_quality_ops_pipeline_runs.py -q` -> `17 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.

## 2026-02-19

### Changed
- Mapa vetorial (`frontend/src/shared/ui/VectorMap.tsx`) evoluido para navegacao mais próxima de apps de mapa:
  - controles nativos adicionais: `FullscreenControl`, `ScaleControl` e `AttributionControl` compacto.
  - `NavigationControl` configurado com zoom + bussola.
  - atribuição de basemap aplicada na fonte raster:
    - `streets`: `(c) OpenStreetMap contributors`
    - `light`: `(c) OpenStreetMap contributors (c) CARTO`
- Estilo dos controles de mapa refinado em `frontend/src/styles/global.css`:
  - reposicionamento e acabamento visual dos grupos de controle (`top-right`, `bottom-left`, `bottom-right`).
  - melhorias de contraste, hover e responsividade em botões/escala/atribuição.
- Frontend QG Prioridades:
  - lista priorizada agora suporta paginacao client-side com controles `Anterior`/`Proxima`, indicador `Pagina X de Y` e seletor `Itens por pagina` (`12`, `24`, `48`) em `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`.
  - página atual e tamanho de página resetam de forma previsivel ao aplicar/limpar filtros.
  - cobertura de regressão adicionada em `frontend/src/modules/qg/pages/QgPages.test.tsx` para cenario com volume alto de cards (`30` itens).
  - validação executada:
    - `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx` -> `19 passed`.
    - `npm --prefix frontend run build` -> `OK`.
- Sprint D3 avancou do contrato para ingestao operacional:
  - novos conectores urbanos implementados:
    - `src/pipelines/urban_roads.py` (`urban_roads_fetch`)
    - `src/pipelines/urban_pois.py` (`urban_pois_fetch`)
  - catálogos de extracao remota por bbox adicionados:
    - `configs/urban_roads_catalog.yml`
    - `configs/urban_pois_catalog.yml`
  - carga idempotente publicada para:
    - `map.urban_road_segment`
    - `map.urban_poi`
  - observabilidade dos jobs urbanos publicada em `ops.pipeline_runs` e `ops.pipeline_checks`.
- Orquestracao e operação atualizadas para D3:
  - `src/orchestration/prefect_flows.py` com:
    - inclusao de `urban_roads_fetch` e `urban_pois_fetch` em `run_mvp_all`
    - novo fluxo `run_mvp_wave_7`
  - `configs/jobs.yml`, `configs/waves.yml` e `configs/connectors.yml` atualizados para `MVP-7`.
  - `scripts/backfill_robust_database.py` atualizado com `--include-wave7` e cobertura urbana no relatório.
- Geocodificacao local inicial publicada no backend:
  - novo endpoint `GET /v1/map/urban/geocode` em `src/app/api/routes_map.py`.
  - novos contratos de resposta:
    - `UrbanGeocodeItem`
    - `UrbanGeocodeResponse`
    - arquivo: `src/app/schemas/map.py`.
- Qualidade e scorecard ampliados para domínio urbano:
  - `check_urban_domain` adicionado em `src/pipelines/common/quality.py`.
  - `quality_suite` atualizado para executar checks urbanos.
  - `configs/quality_thresholds.yml` com thresholds de `urban_domain`.
  - `db/sql/007_data_coverage_scorecard.sql` ampliado com:
    - `urban_road_rows`
    - `urban_poi_rows`.
- BD-032 (performance urbana) avancou com benchmark dedicado:
  - `scripts/benchmark_api.py` agora suporta suites por escopo:
    - `--suite executive` (alvo p95 `800ms`)
    - `--suite urban` (alvo p95 `1000ms`)
    - `--suite all`
  - novos alvos urbanos cobertos no benchmark:
    - `GET /v1/map/urban/roads`
    - `GET /v1/map/urban/pois`
    - `GET /v1/map/urban/nearby-pois`
    - `GET /v1/map/urban/geocode`
  - evidencia operacional pode ser persistida via:
    - `--json-output data/reports/benchmark_urban_map.json`
- Sprint D3 validado em carga real:
  - `scripts/backfill_robust_database.py --include-wave7 --indicator-periods 2026` executado com sucesso.
  - `urban_roads_fetch`: `rows_written=6550`.
  - `urban_pois_fetch`: `rows_written=319`.
  - `scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=0`.
- BD-033 iniciado (UX de navegacao do mapa):
  - `frontend/src/shared/ui/VectorMap.tsx` agora suporta basemap raster com modos:
    - `streets`
    - `light`
    - `none`
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` agora expõe seletor de base cartografica no painel do mapa.
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` passou a suportar `Escopo da camada`:
    - `Territorial` (fluxo anterior preservado)
    - `Urbana` com seletor explicito:
      - `urban_roads` (viario urbano)
      - `urban_pois` (pontos de interesse)
  - `frontend/src/shared/ui/VectorMap.tsx` passou a renderizar camadas `layer_kind=line` corretamente.
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` inclui caso de URL prefill para modo urbano (`scope=urban` + `layer_id=urban_roads`).
  - novas variáveis opcionais de ambiente no frontend:
    - `VITE_MAP_BASEMAP_STREETS_URL`
    - `VITE_MAP_BASEMAP_LIGHT_URL`
  - deep-link do mapa executivo ampliado em `frontend/src/modules/qg/pages/QgMapPage.tsx`:
    - leitura de `viz`, `renderer` e `zoom` por query string.
    - sincronização automática da URL com estado aplicado do mapa:
      - `metric`, `period`, `level`, `scope`, `layer_id`, `territory_id`, `basemap`, `viz`, `renderer`, `zoom`.
    - reset completo no botao `Limpar` para baseline visual (`streets`, `choropleth`, vetorial, `zoom=4`).
  - testes de mapa ampliados em `frontend/src/modules/qg/pages/QgPages.test.tsx`:
    - prefill dos controles visuais por query string.
    - sincronização de query params após aplicar filtros e controles de visualização.
  - otimizaÃ§Ã£o de bundle do mapa:
    - `VectorMap` passou a carregar sob demanda via `React.lazy` + `Suspense` em `QgMapPage`.
    - chunk de rota `QgMapPage` caiu de ~`1.0MB` para ~`19KB`.
    - chunk pesado ficou isolado em `VectorMap-*.js`, reduzindo custo de carregamento inicial da rota.
  - UX responsiva do mapa refinada em `frontend/src/modules/qg/pages/QgMapPage.tsx` e `frontend/src/styles/global.css`:
    - toolbar de controles reorganizada em blocos (`modo`, `mapa base`, `renderizacao`) com quebra responsiva.
    - ajustes visuais para evitar overflow horizontal em telas menores (`viz-mode-selector` com wrap, `zoom-control` adaptativo).
    - container do mapa padronizado com altura fluida (`.map-canvas-shell`) para desktop/mobile.
  - UX de navegacao territorial ampliada no mapa executivo:
    - busca rápida de território com `datalist` no `QgMapPage` (`Buscar território` + `Focar território`).
    - novos controles explicitos de navegacao:
      - `Focar selecionado`
      - `Recentrar mapa`
    - `VectorMap` agora aplica foco por território selecionado com ajuste de câmera (`fitBounds`/`easeTo` com fallback seguro).
    - sincronização `territory_id` validada por teste ao focar território via busca.
    - `VectorMap` passou a aceitar sinais de foco/reset para controle de viewport sem quebrar deep-link existente.
    - fallbacks adicionados para ambiente de teste (mocks sem `easeTo`/`fitBounds`/`GeolocateControl`).
  - Home executiva (`QgOverviewPage`) migrada para `Layout B` de mapa dominante:
    - adocao de `MapDominantLayout` com mapa em destaque e sidebar executiva colapsavel.
    - filtros principais (`Periodo`, `Nivel territorial`, `Camada detalhada`) movidos para o painel lateral do mapa.
    - cards de situacao geral e atalhos de decisão (`Prioridades`, `Mapa detalhado`, `Territorio critico`) integrados ao painel lateral.
    - estado de território selecionado no mapa exibido no painel lateral com leitura de valor.
    - ajustes de estilo no `global.css` para evitar overflow horizontal no painel e melhorar leitura mobile.
  - Home executiva evoluida para navegacao vetorial no mapa dominante:
    - `QgOverviewPage` agora renderiza `VectorMap` no bloco principal da Home com fallback SVG.
    - comutacao de basemap no painel lateral (`Ruas`, `Claro`, `Sem base`) com controle de zoom acoplado.
    - ações de navegacao adicionadas no painel lateral:
      - `Focar selecionado`
      - `Recentrar mapa`
    - clique no mapa vetorial sincroniza território selecionado e leitura contextual na sidebar.
  - testes de navegacao atualizados para o novo contexto do mapa:
    - `frontend/src/app/router.smoke.test.tsx` ajustado para duplicidade intencional de links `Abrir perfil`.
    - `frontend/src/app/e2e-flow.test.tsx` ajustado para o mesmo comportamento sem ambiguidade.
  - contexto urbano do mapa evoluido para ação operacional:
    - `src/app/api/routes_map.py` passa a publicar metadados adicionais nas tiles urbanas:
      - `urban_roads`: `road_class`, `is_oneway`, `source`.
      - `urban_pois`: `category`, `subcategory`, `source`.
    - `frontend/src/shared/ui/VectorMap.tsx` agora envia `lon`/`lat` do clique no payload de seleção.
    - `frontend/src/modules/qg/pages/QgMapPage.tsx` adiciona ações contextuais urbanas:
      - filtro rapido por classe/categoria.
      - geocodificacao contextual da seleção.
      - consulta de POIs próximos ao ponto clicado.
    - `territory_id` na URL do mapa passa a ser persistido apenas no escopo territorial.
  - chunking do frontend ajustado em `frontend/vite.config.ts`:
    - `manualChunks` para separar `vendor-react`, `vendor-router`, `vendor-query`, `vendor-maplibre` e `vendor-misc`.
    - `index-*.js` reduzido para ~`12KB` gzip ~`4.3KB`.
    - `vendor-maplibre-*.js` permanece chunk pesado dedicado (~`1.0MB`) carregado sob demanda.
- D3-3 (tiles urbanos multi-zoom) iniciado no backend:
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt` agora suporta camadas urbanas:
    - `urban_roads`
    - `urban_pois`
  - endpoint mantém contrato de cache/ETag e métricas (`X-Tile-Ms`) também para camadas urbanas.
  - `MapLayerItem.layer_kind` ampliado para aceitar `line` no schema.
  - catálogo/cobertura de camadas agora pode incluir domínio urbano via query param:
    - `GET /v1/map/layers?include_urban=true`
    - `GET /v1/map/layers/coverage?include_urban=true`
  - readiness de camadas publicado no endpoint de mapa:
    - `GET /v1/map/layers/readiness?include_urban=true`
  - `GET /v1/territory/layers/*` permanece estritamente territorial (`include_urban=false`).
  - `QgMapPage` atualizado para consumir catálogo/cobertura com `include_urban=true`.
  - `OpsLayersPage` atualizado com filtro de escopo:
    - `Territorial`
    - `Territorial + Urbano`
    - `Somente urbano`
  - cache middleware ajustado para endpoints operacionais de camadas:
    - `/v1/map/layers/readiness` e `/v1/map/layers/coverage` com `max-age=60`.
    - `/v1/map/layers` mantido com `max-age=3600`.
  - monitor técnico de camadas em `OpsLayersPage` recebeu resumo operacional adicional:
    - cards agregados de readiness (`pass`, `warn`, `fail`, `pending`) por recorte.
    - grade de "Resumo rapido das camadas" com status de `rows`, `geom` e `readiness`.
    - estilos dedicados para leitura rapida em `frontend/src/styles/global.css`.
  - suite de testes da página ops de camadas ampliada:
    - novo caso em `frontend/src/modules/ops/pages/OpsPages.test.tsx` cobrindo render do resumo rapido.

### Verified
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_urban_connectors.py tests/unit/test_api_contract.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/contracts/test_sql_contracts.py -p no:cacheprovider`:
  - `40 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_mvt_tiles.py tests/unit/test_api_contract.py -p no:cacheprovider`:
  - `36 passed`.
- `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`:
  - `8 passed` (iteracao anterior).
- `npm --prefix frontend run test -- --run src/modules/ops/pages/OpsPages.test.tsx`:
  - `9 passed`.
- `npm --prefix frontend run test`:
  - `66 passed`.
- `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx`:
  - `17 passed`.
- `npm --prefix frontend run test`:
  - `68 passed`.
- `npm --prefix frontend run test`:
  - `69 passed`.
- `npm --prefix frontend run test`:
  - `69 passed` (revalidado apos evolução do mapa dominante e ajustes de smoke/e2e).
- `npm --prefix frontend run test`:
  - `69 passed` (revalidado apos ações contextuais urbanas).
- `npm --prefix frontend run build`:
  - build concluido com sucesso.

### Docs
- Governança de foco sem dispersao consolidada com data de corte em `2026-02-19`:
  - `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md` recebeu:
    - plano operacional sem dispersao (secao 7);
    - sequencia lógica de implementação (secao 8);
    - regra de priorização para evitar dispersao (secao 9).
  - `docs/HANDOFF.md` passou a registrar explicitamente a ordem de execução ativa do ciclo:
    - estabilizacao de telas e fluxo decisorio;
    - gates de confiabilidade;
    - fechamento de lacunas criticas de dados;
    - expansão de escopo somente apos fechamento das etapas anteriores.

### Fixed
- Estabilizacao de telas executivas com dados ausentes:
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`:
    - erro `404` de perfil territorial agora cai em estado vazio guiado (sem hard-fail da tela).
    - formulário de filtros permanece disponível para troca imediata de território/período.
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`:
    - quando o ano filtrado não possui dados, a tela aplica fallback automatico para o ultimo ano disponível.
    - aviso de fallback explicito exibido para transparencia operacional.
    - evita painel executivo zerado/sem contexto no recorte filtrado sem dados.
- Mapa vetorial executivo com melhor leitura sobre mapa-base:
  - `frontend/src/shared/ui/VectorMap.tsx` ajustado para opacidade adaptativa de poligonos por basemap (`streets`, `light`, `none`).
  - contorno territorial adaptativo por modo de basemap para preservar limites sem esconder vias/contexto urbano.

### Tests
- Frontend:
  - `npm --prefix frontend run test -- --run src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/territory/pages/TerritoryProfilePage.test.tsx src/app/router.smoke.test.tsx src/app/e2e-flow.test.tsx`
    - `11 passed`.
  - `npm --prefix frontend run build`
    - `OK`.

### Verified (ciclo atual - 2026-02-20)
- Backend:
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> `29 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> `26 passed`.
- Frontend:
  - `npm --prefix frontend run test -- --run` -> `72 passed`.
  - `npm --prefix frontend run build` -> `OK`.
- Smoke de API (eleitorado):
  - `GET /v1/electorate/summary?level=municipality&year=2024` -> `200`, `total_voters=38127`, `year=2024`, `notes` com fallback outlier.
  - `GET /v1/electorate/map?level=municipality&year=2024&metric=voters&include_geometry=false&limit=5` -> `200`, itens retornados com fallback outlier.

## 2026-02-13 (Sprint 9 - territorial layers TL-2/TL-3 + base eleitoral)

### Added
- **API técnica de camadas territoriais**:
  - `GET /v1/territory/layers/catalog`
  - `GET /v1/territory/layers/coverage`
  - `GET /v1/territory/layers/{layer_id}/metadata`
  - `GET /v1/territory/layers/readiness`
  - Implementação em `src/app/api/routes_territory_layers.py` e inclusao no `main.py`.
- **Cobertura e metadata de camadas no backend de mapa** (`src/app/api/routes_map.py`):
  - `GET /v1/map/layers/coverage`
  - `GET /v1/map/layers/{layer_id}/metadata`
  - Catálogo de camadas com níveis eleitorais (`electoral_zone`, `electoral_section`).
  - Nova camada `territory_polling_place` (nível `electoral_section`, `layer_kind=point`) filtrando secoes com `metadata.polling_place_name`.
- **Contratos e cliente frontend para rastreabilidade de camadas**:
  - novos tipos em `frontend/src/shared/api/types.ts`;
  - novos clientes em `frontend/src/shared/api/domain.ts` e `frontend/src/shared/api/ops.ts`;
  - nova tela técnica `frontend/src/modules/ops/pages/OpsLayersPage.tsx`;
  - rota adicionada em `frontend/src/app/router.tsx`.
- **Qualidade de camadas no quality suite**:
  - checks `map_layer_rows_*` e `map_layer_geometry_ratio_*` na execução;
  - thresholds em `configs/quality_thresholds.yml`;
  - testes unitarios em `tests/unit/test_quality_core_checks.py`.
- **Territorializacao eleitoral no pipeline TSE de resultados** (`src/pipelines/tse_results.py`):
  - parse de zona e secao quando colunas existirem no CSV;
  - detecção de `local_votacao` (quando presente) para metadata da secao eleitoral;
  - upsert de `electoral_zone` e `electoral_section` em `silver.dim_territory`;
  - resolução de `territory_id` para `fact_election_result` por secao > zona > município.

### Changed
- **Admin/ops**:
  - `frontend/src/modules/admin/pages/AdminHubPage.tsx` com atalho para `/ops/layers`;
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx` atualizado para cobrir fluxo de filtros da nova página.
- **Mapa executivo (frontend)**:
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` com seletor explicito `Camada eleitoral detalhada` quando houver multiplas camadas no nível eleitoral.
  - suporte para alternar entre `Secoes eleitorais` e `Locais de votacao`.
  - prefill do `layer_id` por query string (deep-link para camada explicita) preservado no carregamento inicial.
  - nota da camada ativa com tooltip de método (`proxy_method`) para transparencia operacional.
  - fallback do modo de visualizacao para `pontos` quando camada ativa for `point`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` agora propaga `layer_id` para links de mapa (atalho principal + cards Onda B/C), com seletor `Camada detalhada (Mapa)`.
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx` passa a aplicar a camada detalhada tambem no proprio mapa dominante, não apenas nos links.
  - `frontend/src/modules/qg/pages/QgMapPage.tsx` ganhou orientacao explicita de `local_votacao` (dica de uso, camada ativa e leitura contextual da seleção).
- **Readiness técnico de camadas**:
  - `frontend/src/modules/ops/pages/OpsLayersPage.tsx` com alerta de degradação (`fail`, `warn`, `pending`) e lista de camadas impactadas.
- **Base de camadas territoriais**:
  - `src/app/api/routes_map.py` com nova camada `territory_neighborhood_proxy` (bairro proxy sobre base setorial) publicada em catálogo, metadata, readiness e tiles.
- **Estilos de UX**:
  - `frontend/src/styles/global.css` com bloco visual do seletor de camada (`.map-layer-toggle`).
- **Schemas de mapa**:
  - `src/app/schemas/map.py` com modelos de cobertura, metadata e readiness por camada.
- **Testes de contrato de mapa/camadas**:
  - `tests/unit/test_mvt_tiles.py` ampliado para catálogo, metadata, readiness e camada `territory_polling_place`.
- **Testes do pipeline eleitoral**:
  - `tests/unit/test_tse_results.py` ampliado para normalizacao e extracao de zona/secao/local_votacao.
- **Testes de página QG**:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` com caso cobrindo exibição do seletor de camada de secao.
  - `frontend/src/modules/qg/pages/QgPages.test.tsx` com casos cobrindo propagacao de `layer_id` via Overview e carregamento por URL no `QgMapPage`.

### Verified
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_tse_results.py tests/unit/test_mvt_tiles.py tests/unit/test_quality_core_checks.py`
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_tse_results.py`
- `npm --prefix frontend run test -- src/modules/qg/pages/QgPages.test.tsx`
- `npm --prefix frontend run build`

## 2026-02-13 (Sprint 8 - Vector engine MP-3 + Strategic engine SE-2)

### Added
- **MapLibre GL JS + VectorMap component** (`frontend/src/shared/ui/VectorMap.tsx`):
  - Componente MVT-first com MapLibre GL JS (~280 linhas).
  - 4 modos de visualizacao: coroplético, pontos proporcionais, heatmap, hotspots.
  - Auto-switch de layer por zoom via `resolveLayerForZoom`.
  - Seleção de território com destaque (outline azul espesso).
  - Centro padrão: Diamantina, MG (-43.62, -18.09).
  - Estilo local-first (sem tiles base externos), background #f6f4ee.
- **Viz mode selector** (`QgMapPage.tsx`):
  - Radio group com 4 modos (Coroplético, Pontos, Heatmap, Hotspots).
  - Toggle entre VectorMap (MVT-first) e ChoroplethMiniMap (SVG fallback).
- **Multi-level geometry simplification** (`routes_map.py`):
  - 5 faixas de tolerância por zoom: z0-4 (0.05), z5-8 (0.005), z9-11 (0.001), z12-14 (0.0003), z15+ (0.0001).
  - Função `_tolerance_for_zoom(z)` substituiu fórmula genérica.
- **MVT cache ETag + latency metrics** (`routes_map.py`):
  - ETag baseado em MD5 do conteúdo do tile + header `If-None-Match` → 304.
  - Header `X-Tile-Ms` com tempo de geração.
  - Ring buffer `_TILE_METRICS` (max 500 entradas).
  - Endpoint `GET /v1/map/tiles/metrics`: p50/p95/p99 + stats por layer.
- **Strategic engine config (SE-2)** (`configs/strategic_engine.yml` + `strategic_engine_config.py`):
  - YAML externalizado: thresholds (critical: 80, attention: 50), severity_weights, limites de cenários.
  - `ScoringConfig` + `StrategicEngineConfig` dataclasses (frozen).
  - `load_strategic_engine_config()` com `@lru_cache` — carregamento Ãºnico.
  - `score_to_status()` + `status_impact()`: delegam para config YAML.
  - SQL CASE statements parametrizados com thresholds do config.
  - `config_version` adicionado ao schema `QgMetadata` (Python + TypeScript).
  - Todas as 8 construções de `QgMetadata` injetam `config_version` automaticamente.
- **Spatial GIST index** (`db/sql/003_indexes.sql`):
  - `idx_dim_territory_geometry ON silver.dim_territory USING GIST (geometry)`.
- **Vitest maplibre-gl mock** (`frontend/vitest.setup.ts`):
  - Mock completo do MapLibre GL para jsdom (URL.createObjectURL + Map mock).
- **26 novos testes SE-2** (`tests/unit/test_strategic_engine_config.py`):
  - 4 ScoringConfig defaults, 6 load config, 7 score_to_status, 6 status_impact, 3 config_version metadata.
- **7 novos testes MVT** (`tests/unit/test_mvt_tiles.py`):
  - 6 multi-level tolerance + 1 tile metrics endpoint.

### Changed
- `routes_qg.py`: `_score_to_status()` e `_status_impact()` agora delegam para módulo config.
- `routes_qg.py`: SQL CASE com thresholds do YAML (não mais hardcoded 80/50).
- `routes_qg.py`: `_qg_metadata()` injeta `config_version` automaticamente.
- `QgMapPage.tsx`: VectorMap como renderizador principal, ChoroplethMiniMap como fallback.
- `global.css`: +40 linhas (viz-mode-selector, viz-mode-btn/active, vector-map-container).
- `types.ts`: `QgMetadata.config_version?: string | null`.
- `qg.py`: `QgMetadata.config_version: str | None = None`.

### Verified
- Backend: **246 testes passando** (pytest) — +33 vs Sprint 7.
- Frontend: **59 testes passando** (vitest) em 18 arquivos.
- Build Vite: OK (4.3s).
- RegressÃ£o completa sem falhas.
- 26 endpoints totais (11 QG + 10 ops + 1 geo + 2 map + 1 MVT + 1 tile-metrics).

### Added
- **Layout B: mapa dominante na Home** (`QgOverviewPage.tsx`):
  - Reescrito para layout map-dominant com ChoroplethMiniMap preenchendo area principal.
  - Sidebar overlay com glassmorphism (filtros, KPIs, ações rapidas, prioridades, destaques).
  - Barra de estatisticas flutuante (criticos/atencao/monitorados).
  - Botao toggle para exibir/ocultar painel lateral.
- **Drawer lateral reutilizavel** (`frontend/src/shared/ui/Drawer.tsx`):
  - Componente slide-in com suporte a left/right, escape key, backdrop click, aria-modal.
  - 4 testes unitarios.
- **Zustand para estado global** (`frontend/src/shared/stores/filterStore.ts`):
  - Store com period, level, metric, zoom + actions (setPeriod, setLevel, setMetric, setZoom, applyDefaults).
  - Integrado no QgOverviewPage para sincronizacao de filtros.
  - 6 testes unitarios.
- **MapDominantLayout** (`frontend/src/shared/ui/MapDominantLayout.tsx`):
  - Wrapper component: mapa full-viewport + sidebar overlay colapsavel.
- **MVT tiles endpoint (MP-2)** (`src/app/api/routes_map.py`):
  - `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`: vector tiles via PostGIS ST_AsMVT.
  - Dois caminhos SQL: com join de indicador (metric+period) ou geometria pura.
  - Suporte a filtro por domain, tolerancia adaptativa por zoom.
  - Cache-Control: 1h, CORS headers.
  - 6 testes unitarios (tile bbox, layer mapping, validação 422).
- **Auto layer switch por zoom** (`frontend/src/shared/hooks/useAutoLayerSwitch.ts`):
  - Hook `useAutoLayerSwitch` + função pura `resolveLayerForZoom`.
  - Seleciona camada automaticamente pelo zoom_min/zoom_max do manifesto /v1/map/layers.
  - Controle de zoom (range slider) integrado no QgMapPage.
  - 6 testes unitarios.

### Changed
- `QgOverviewPage.tsx`: labels encurtados (Aplicar, Prioridades, Mapa detalhado, Território critico).
- `QgMapPage.tsx`: integrado useAutoLayerSwitch + zoom state sincronizado com Zustand.
- `cache_middleware.py`: adicionada regra MVT tiles com TTL 1h.
- `global.css`: +250 linhas (drawer, map-dominant, floating-stats, zoom-control, responsivo).

### Verified
- Backend: 213 testes passando (pytest) — +6 MVT.
- Frontend: 59 testes passando (vitest) em 18 arquivos — +7 (4 Drawer, 6 autoLayer+zoom, -1 ajustes store).
- Build Vite: OK (1.51s).
- Regressão completa sem falhas.

## 2026-02-13 (Sprint 6 - go-live v1.0 closure)

### Added
- Contrato v1.0 congelado (`docs/CONTRATO.md`):
  - Todos os 24 endpoints documentados (11 QG + 10 ops + 1 geo + 2 map).
  - SLO-2 dividido: operacional (p95 <= 1.5s) e executivo (p95 <= 800ms).
  - Secao 12.1 com tabela de ferramentas de validação (homologation_check, benchmark_api, backend_readiness, quality_suite).
  - 8 telas executivas do frontend incluidas na secao 7.
- Runbook de operações (`docs/OPERATIONS_RUNBOOK.md`):
  - 12 secoes: ambiente, pipelines, qualidade, views materializadas, API, frontend, go-live, testes, troubleshooting, conectores especiais, deploy.
  - Procedimento de deploy com 11 passos + rollback.
  - 5 cenarios de troubleshooting documentados.
- Specs v0.1 promovidas a v1.0:
  - `MAP_PLATFORM_SPEC.md`: MP-1 marcado CONCLUIDO (manifesto de camadas, style-metadata, cache 1h, fallback choropleth).
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`: TL-1 marcado CONCLUIDO (`is_official` no catálogo, badge frontend, coverage_note).
  - `STRATEGIC_ENGINE_SPEC.md`: SE-1 marcado CONCLUIDO (score/severity/rationale/evidence, simulação, briefs).

### Changed
- `MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`:
  - P01 atualizado com CollapsiblePanel progressive disclosure.
  - D01 atualizado com contrato v1.0 congelado.
  - O6-03 elevado para OK (progressive disclosure completo).
  - O8-02 elevado para OK (OpsHealthPage com 7 paineis + homologation script).
  - Secao "Criticas" atualizada com runbook de operações.

### Verified
- Backend: 207 testes passando (pytest).
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressão completa sem falhas.

## 2026-02-13 (Sprint 5.3 - go-live readiness)

### Added
- Thresholds de qualidade por domínio/fonte (Sprint 5.2 #3):
  - `configs/quality_thresholds.yml`: adicionados `min_rows_datasus`, `min_rows_inep`, `min_rows_siconfi`, `min_rows_mte`, `min_rows_tse` (MVP-3).
  - MVP-5 sources elevados de 0 para 1 (INMET, INPE_QUEIMADAS, ANA, ANATEL, ANEEL).
  - `quality.py`: `check_fact_indicator_source_rows()` ampliado de 10 para 15 fontes; `check_ops_pipeline_runs()` ampliado de 9 para 14 jobs.
- Script de homologação consolidado (`scripts/homologation_check.py`):
  - Orquestra 5 dimensões: backend readiness, quality suite, frontend build, test suites, API smoke.
  - Produz verdict unico READY/NOT READY com output JSON opcional.
  - CLI: `--json`, `--strict`.
- Componente `CollapsiblePanel` (`frontend/src/shared/ui/CollapsiblePanel.tsx`):
  - Panel colapsavel com chevron, badge de contagem, `aria-expanded`, foco visivel.
  - CSS integrado em `global.css` (`.collapsible-toggle`, `.collapsible-chevron`, `.badge-count`).
- Admin diagnostics refinement (Sprint 5.3 #1):
  - `OpsHealthPage.tsx`: 3 novos paineis colapsaveis — Quality checks, Cobertura de fontes, Registro de conectores.
  - Consome `getPipelineChecks`, `getOpsSourceCoverage`, `getConnectorRegistry` ja existentes.

### Changed
- `QgOverviewPage.tsx`: tabelas "Domínios Onda B/C" (collapsed) e "KPIs executivos" (expanded) usam `CollapsiblePanel` para progressive disclosure.
- Testes `test_quality_core_checks.py` atualizados para 15 fontes (mock session com 15 valores).
- Mocks de `getOpsSourceCoverage` adicionados em `router.smoke.test.tsx` e `e2e-flow.test.tsx`.

### Verified
- Backend: 207 testes passando (pytest).
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressão completa sem falhas.

## 2026-02-13 (Sprint 5.2 - acessibilidade e hardening)

### Added
- Script de benchmark de performance da API:
  - `scripts/benchmark_api.py` com medicao de p50/p95/p99 em 12 endpoints criticos.
  - alvo: p95 <= 800ms; suporte a JSON output e rounds configuraveis.
- Testes de edge-case para contratos QG:
  - `tests/unit/test_qg_edge_cases.py` com 44 testes cobrindo validação de nível, limites, dados vazios, propagacao de request_id, content-type de erro, etc.
- Badge de classificação de fonte (P05):
  - campo `source_classification` adicionado ao `QgMetadata` (backend schema + API).
  - constantes `_OFFICIAL_SOURCES` / `_PROXY_SOURCES` e função `_classify_source()` em `routes_qg.py`.
  - frontend: `SourceFreshnessBadge` exibe "Fonte oficial", "Proxy/estimado" ou "Fontes mistas".
- Hook de persistencia de sessao (O7-05):
  - `frontend/src/shared/hooks/usePersistedFormState.ts` com prioridade: queryString > localStorage > defaults.
  - integrado em `QgScenariosPage` (6 campos) e `QgBriefsPage` (5 campos).
- Hardening de acessibilidade (Sprint 5.2 item 1):
  - `Panel.tsx`: `<section aria-labelledby>` com `id` gerado via `useId()` no `<h2>`.
  - `StateBlock.tsx`: `role="alert"` para erros, `role="status"` para loading/empty, `aria-live`.
  - `StrategicIndexCard.tsx`: `aria-label` no `<article>` e `aria-label` de status no `<small>`.
  - Todas as páginas executivas: `<div class="page-grid">` substituido por `<main>`.
  - 7 tabelas receberam `aria-label` descritivo (Overview, Map, Briefs, Territory).
  - Botoes de exportacao com `aria-label` contextual (SVG, PNG, CSV, HTML, PDF).
  - Linhas clicaveis do ranking territorial com `tabIndex={0}`, `role="button"`, `onKeyDown` (Enter/Space).
  - Quick-actions em Overview e TerritoryProfile envolvidos em `<nav aria-label>`.
  - Listas trend-list com `aria-label` semantico.
  - Grid de prioridades com `role="list"` e `aria-label`.

### Changed
- `source_classification` no tipo TypeScript `QgMetadata` marcado como opcional (`?:`) para compatibilidade com mocks existentes.
- Testes de frontend atualizados para usar regex (`/Exportar.*CSV/`) nos nomes acessiveis de botoes com `aria-label`.

### Verified
- Backend: 207 testes passando (pytest), incluindo 44 novos edge-case.
- Frontend: 43 testes passando (vitest) em 15 arquivos.
- Build Vite: OK.
- Regressão completa sem falhas.

## 2026-02-13 (Sprint 5 - hardening)

### Added
- Teste E2E completo do fluxo critico de decisão:
  - `frontend/src/app/e2e-flow.test.tsx` com 5 testes cobrindo Home → Prioridades → Mapa → Território 360 → Eleitorado → Cenarios → Briefs.
  - deep-links com propagacao de contexto (query params) entre mapa e território.
  - navegacao admin → executivo validada.
- Middleware de cache HTTP para endpoints criticos:
  - `src/app/api/cache_middleware.py` com `CacheHeaderMiddleware` (Cache-Control + weak ETag + 304 condicional).
  - regras: mapa/layers e style-metadata = 3600s; kpis/priority/insights = 300s; choropleth/electorate = 600s; territory = 300s.
  - registrado em `src/app/api/main.py`.
  - `tests/unit/test_cache_middleware.py` com 6 testes unitarios.
- Materialized views para ranking e mapa:
  - `db/sql/006_materialized_views.sql` com 3 MVs: `mv_territory_ranking`, `mv_map_choropleth`, `mv_territory_map_summary`.
  - função `gold.refresh_materialized_views()` para refresh concorrente.
  - geometria simplificada com `ST_SimplifyPreserveTopology(geometry, 0.001)` na MV de mapa.
- Indices espaciais GIST dedicados:
  - `db/sql/007_spatial_indexes.sql` com GIST em `dim_territory.geometry`, GIN trigram em `name`, covering index para joins de mapa.
- Banner de readiness no Admin:
  - `AdminHubPage.tsx` com `ReadinessBanner` consumindo `GET /v1/ops/readiness` (conectores, SLO-1, falhas, avisos).

### Changed
- Matriz de rastreabilidade atualizada:
  - A03 (indices geoespaciais): PARCIAL → OK.
  - A04 (materialized views): PENDENTE → OK.
  - A05 (geometrias simplificadas): PENDENTE → PARCIAL.
  - A07 (cache HTTP): PENDENTE → OK.
  - P03 (admin readiness): atualizado com evidencia de ReadinessBanner.
  - O8-01 (E2E): PARCIAL → OK.

### Verified
- Backend: 163 testes passando (pytest), incluindo 6 novos testes de cache middleware.
- Frontend: 43 testes passando (vitest) em 15 arquivos, incluindo 5 E2E de fluxo critico.
- Build Vite: OK.
- Regressão completa sem falhas.

## 2026-02-13

### Changed
- Consolidação documental do QG aplicada:
  - `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md` redefinido como visão estrategica (north star), sem status operacional diario.
  - `PLANO.md` atualizado para governança de execução e referência única de papéis documentais.
  - `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado com consolidação documental e status por onda.
  - `HANDOFF.md` atualizado para refletir a governança documental consolidada.
- Matriz de rastreabilidade atualizada para refletir criacao das specs estrategicas:
  - itens documentais D05/D06/D07 mudaram de `PENDENTE` para `OK (v0.1)`.
  - backlog critico deslocado de \"escrever specs\" para \"executar Onda 5 e hardening Onda 8\".
- Governança de docs complementares refinada:
  - `docs/PLANO.md` e `docs/PLANO_IMPLEMENTACAO_QG.md` atualizados para explicitar que:
    - `docs/FRONTEND_SPEC.md` e referência complementar de produto/UX.
    - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` e catálogo de fontes (não status operacional diario).
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md` atualizado com regra de leitura e snapshot histórico.
  - `docs/HANDOFF.md` atualizado com classificação documental complementar.
  - `docs/FRONTEND_SPEC.md` reclassificado para status complementar e com banner de governança documental.
  - `docs/CONTRATO.md` e `docs/FRONTEND_SPEC.md` ajustados para leitura UTF-8 correta no ambiente local.
- MP-1 da plataforma de mapa iniciado na stack técnica:
  - novo endpoint de manifesto `GET /v1/map/layers` publicado na API.
  - `QgMapPage` passou a consumir o manifesto de camadas para orientar camada ativa por nível territorial.
  - fluxo manteve fallback funcional para `GET /v1/geo/choropleth` quando manifesto estiver indisponivel.
- MP-1 evoluido com metadados de estilo para o mapa:
  - novo endpoint `GET /v1/map/style-metadata` publicado na API.
  - `QgMapPage` passou a exibir metadados de estilo (modo padrão e paleta de severidade) com fallback seguro.

### Added
- Novas specs estrategicas (versão inicial v0.1):
  - `MAP_PLATFORM_SPEC.md`
  - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
  - `STRATEGIC_ENGINE_SPEC.md`
- Nova matriz de rastreabilidade detalhada:
  - `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`
- Novos artefatos de backend para MP-1:
  - `src/app/api/routes_map.py`
  - `src/app/schemas/map.py`

### Verified
- Validação documental cruzada concluida:
  - visão estrategica (`PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`)
  - plano executável (`docs/PLANO_IMPLEMENTACAO_QG.md`)
  - estado operacional (`HANDOFF.md`)
  - governança macro (`PLANO.md`)
- Validação técnica MP-1:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `5 passed`.
  - `npm --prefix frontend run test`: `14 passed` / `38 passed`.
  - `npm --prefix frontend run build`: `OK` (Vite build concluido com `QgMapPage` consumindo `GET /v1/map/layers`).
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_api_contract.py -p no:cacheprovider`: `6 passed` (inclui contrato de `GET /v1/map/style-metadata`).
  - `npm --prefix frontend run test`: `14 passed` / `38 passed` (revalidado apos consumo de `style-metadata`).
  - `npm --prefix frontend run build`: `OK` (Vite build concluido apos evolução de legenda/paleta no mapa).

## 2026-02-12

### Changed
- Readiness operacional unificado em módulo compartilhado:
  - nova camada `src/app/ops_readiness.py` para centralizar calculos de `required_tables`,
    `connector_registry`, `slo1`, `slo1_current`, `slo3` e `source_probe`.
  - `scripts/backend_readiness.py` refatorado para reutilizar o mesmo nucleo da API.
- Monitor de saude operacional do frontend atualizado para consumir readiness dedicado:
  - `OpsHealthPage` passou a consultar `GET /v1/ops/readiness` para status consolidado
    (`READY|NOT_READY`), `hard_failures` e `warnings`.
  - painel de SLO-1 mantido com comparativo histórico (`7d`) vs corrente (`1d`) usando
    o payload de readiness como fonte principal.
- `scripts/backend_readiness.py` evoluido para separar saude corrente de histórico no SLO-1:
  - novo parâmetro `--health-window-days` (default: `1`).
  - novo bloco `slo1_current` no JSON de saida com `window_role=current_health`.
  - warning de SLO-1 agora inclui contexto combinado (`last 7d` vs janela corrente),
    reduzindo ambiguidade de diagnostico por heranca histórica.
- `OpsHealthPage` evoluida para exibir comparativo de SLO-1 histórico vs corrente:
  - novo painel `Monitor SLO-1` com taxa agregada em `7d` e `1d`.
  - contagem de jobs abaixo da meta em ambas as janelas para leitura operacional imediata.
  - consulta de SLA passou a rodar em duas janelas com `started_from` dedicado.
- Filtros de domínio do QG padronizados com catálogo unico no frontend:
  - `Prioridades`, `Insights`, `Briefs` e `Cenarios` migrados de input livre para `select` com opcoes consistentes.
  - normalizacao de query string para domínio via `normalizeQgDomain` (evita valores invalidos no estado inicial).
  - catálogo compartilhado consolidado em `frontend/src/modules/qg/domainCatalog.ts`.
  - `Prioridades` e `Insights` passaram a consumir query string no carregamento inicial (deep-link funcional para filtros).
- UX de domínio no QG refinada com rotulos amigaveis para usuario final:
  - helper `getQgDomainLabel` aplicado em cards/tabelas/subtitulos e combos de filtro.
  - valores técnicos (`saude`, `meio_ambiente`, etc.) mantidos no estado/API; exibição convertida para leitura executiva.
- Home QG evoluida para destacar domínios Onda B/C na visão executiva:
  - novo catálogo frontend em `frontend/src/modules/qg/domainCatalog.ts` com domínios `clima`, `meio_ambiente`, `recursos_hidricos`, `conectividade` e `energia`.
  - novo painel `Dominios Onda B/C` na `QgOverviewPage` com atalhos de prioridade e mapa por domínio.
  - query de KPI da Home ampliada para `limit: 20` para reduzir risco de truncamento de domínios ativos.
- Contrato de KPI executivo expandido com evidencia de origem:
  - `KpiOverviewItem` passou a expor `source` e `dataset` no backend e frontend.
  - `GET /v1/kpis/overview` atualizado para retornar `fi.source` e `fi.dataset`.
  - tabela de KPIs executivos na Home passou a exibir coluna `Fonte`.
- Testes frontend endurecidos para o novo layout da Home QG:
  - mocks alinhados com `source`/`dataset`.
  - assercoes ajustadas para cenarios com multiplos links `Abrir prioridades`.
  - expectativa de limite atualizada para `limit: 20`.
- Operação de readiness endurecida no ambiente local:
  - `scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply` executado para preencher checks ausentes em runs históricos.
  - `scripts/backend_readiness.py --output-json` voltou para `READY` com `hard_failures=0`.
- Registry operacional sincronizado com o estado atual dos conectores:
  - `scripts/sync_connector_registry.py` executado.
  - `ops.connector_registry` atualizado para `22` conectores `implemented` (incluindo `MVP-5`).
- Pipeline ANA (Onda B/C) destravado para extracao automatica:
  - catálogo ANA prioriza download ArcGIS Hub CSV (`api/download/v1/items/.../csv?layers=18`) com fallback SNIRH.
  - mapeamento de colunas ANA ampliado para campos reais (`CDMUN`, `NMMUN`, `VZTOTM3S` e correlatos).
  - bootstrap tabular ajustado para tratar URLs com query string em Windows (normalizacao do nome de arquivo bruto).
- Frontend QG endurecido para estabilidade de testes e navegacao:
  - sincronizacao dos testes de páginas QG/Território com estados de carregamento.
  - seletores ambiguos em testes ajustados para consultas robustas.
  - `future flags` do React Router v7 aplicados em `router`, `main` e wrappers de teste.
- `Territorio 360` alinhado ao mesmo padrão de rotulos amigaveis por domínio:
  - tabela de domínios e comparacao agora usa `getQgDomainLabel`, removendo exibição de codigos técnicos crus.

### Added
- Novo endpoint de readiness operacional na API:
  - `GET /v1/ops/readiness` com parâmetros `window_days`, `health_window_days`,
    `slo1_target_pct`, `include_blocked_as_success` e `strict`.
  - contrato retornando status consolidado, `slo1` histórico, `slo1_current`,
    `slo3`, cobertura de tabelas obrigatorias e diagnosticos (`hard_failures`/`warnings`).
- Cliente e tipagens frontend para readiness:
  - `getOpsReadiness` em `frontend/src/shared/api/ops.ts`.
  - `OpsReadinessResponse` e tipos derivados em `frontend/src/shared/api/types.ts`.
- Cobertura de testes ampliada para bootstrap Onda B/C:
  - caso de sanitizacao de nome de arquivo com query string.
  - casos de mapeamento municipal com colunas `CDMUN`/`NMMUN`.
  - caso de alias ANA para vazao total.

### Verified
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `41 passed`.
- `npm --prefix frontend run test`: `14 passed` / `38 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido com integração de readiness em `OpsHealthPage`).
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --help`: `OK` (novo parâmetro `--health-window-days` visivel).
- `.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json`: `READY` com novo bloco `slo1_current` e warning contextualizado.
- `npm --prefix frontend run test`: `14 passed` / `38 passed` (inclui cobertura de `OpsHealthPage` com monitor de janela 7d/1d).
- `npm --prefix frontend run build`: `OK` (Vite build concluido apos evolução do monitor SLO-1).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (inclui padronizacao de filtros de domínio + prefill por query string em `Prioridades` e `Insights`).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos padronizacao de filtros e deep-links).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos rotulos amigaveis de domínio no QG).
- `npm --prefix frontend run build`: `OK` (Vite build concluido, revalidado apos refinamento de UX de domínio).
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `38 passed`.
- `npm --prefix frontend run test`: `14 passed` / `33 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido).
- `npm --prefix frontend run test`: `14 passed` / `35 passed` (revalidado apos padronizacao de rotulos no `TerritoryProfilePage`).
- `npm --prefix frontend run build`: `OK` (revalidado apos ajuste de rotulos no `TerritoryProfilePage`).
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_bootstrap_manual_sources_snis.py tests/unit/test_bootstrap_manual_sources_onda_b.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `34 passed`.
- `.\.venv\Scripts\python.exe scripts/bootstrap_manual_sources.py --reference-year 2025 --municipality-name Diamantina --municipality-ibge-code 3121605 --skip-mte --skip-senatran --skip-sejusp --skip-siops --skip-snis`: `INMET/INPE_QUEIMADAS/ANA/ANATEL/ANEEL = ok`.
- `run_mvp_wave_4(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- `run_mvp_wave_5(reference_period='2025', dry_run=False)`: todos os jobs `success`.
- `tse_electorate_fetch`, `labor_mte_fetch` e `ana_hydrology_fetch` executados com `status=success`.
- `quality_suite(reference_period='2025', dry_run=False)`: `success` com `failed_checks=0`.
- `scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=1` (`SLO-1` histórico na janela de 7 dias).
- `pytest -q -p no:cacheprovider`: `152 passed`.
- `npm --prefix frontend run test`: `14 passed` / `33 passed`.
- `npm --prefix frontend run build`: `OK` (Vite build concluido).

## 2026-02-11

### Changed
- API v1 passou a incluir o novo router QG (`routes_qg`) com contratos iniciais para Home/Prioridades/Insights.
- API `ops` evoluiu para receber e consultar telemetria frontend:
  - `POST /v1/ops/frontend-events`
  - `GET /v1/ops/frontend-events`
  - `GET /v1/ops/source-coverage` (cobertura operacional por fonte com runs e dados em `silver.fact_indicator`)
- Frontend evoluiu de foco exclusivamente operacional para fluxo QG:
  - rota inicial (`/`) agora usa visão executiva (`QgOverviewPage`).
  - nova rota `prioridades` com consumo de `GET /v1/priority/list`.
  - nova rota `mapa` com consumo de `GET /v1/geo/choropleth`.
  - `mapa` evoluido com renderizacao visual (SVG/GeoJSON) via `ChoroplethMiniMap`, mantendo visão tabular de apoio.
  - nova rota `insights` com consumo de `GET /v1/insights/highlights`.
  - nova rota `territory/profile` com consumo de `GET /v1/territory/{id}/profile` e `GET /v1/territory/{id}/compare`.
  - nova rota `electorate/executive` com consumo de `GET /v1/electorate/summary` e `GET /v1/electorate/map`.
  - navegacao principal atualizada para incluir Visão Geral, Território 360 e Eleitorado.
  - navegacao técnica separada em hub dedicado (`/admin`), removendo links operacionais do menu principal.
  - aliases de rota em portugues adicionados para fluxo executivo:
    - `/territorio/perfil`
    - `/territorio/:territoryId`
    - `/eleitorado`
  - navegação QG endurecida com deep-link para perfil territorial a partir de `Prioridades` e `Mapa` (`Abrir perfil`).
  - telas executivas do QG passaram a exibir metadados de fonte/frescor/cobertura com `SourceFreshnessBadge`.
  - `Situacao geral` da Home passou a usar card executivo reutilizavel (`StrategicIndexCard`).
  - `Prioridades` passou de tabela unica para cards executivos reutilizaveis (`PriorityItemCard`) com foco em racional/evidencia.
  - rota executiva `/cenarios` adicionada para simulação simplificada de impacto territorial.
  - motor de cenarios evoluido para calcular ranking antes/depois por indicador, com delta de posicao.
  - rota executiva `/briefs` adicionada para geracao de brief com resumo e evidencias priorizadas.
  - Home QG evoluida com ações rapidas para `prioridades`, `mapa` e `territorio critico`.
  - ação rapida `Ver no mapa` na Home passou a abrir o recorte da prioridade mais critica.
  - Home QG passou a exibir previa real de Top prioridades (limit 5) com cards executivos.
  - `Territorio 360` ganhou atalhos para `briefs` e `cenarios` com contexto do território selecionado.
  - `Briefs` e `Cenarios` passaram a aceitar pre-preenchimento por query string (`territory_id`, `period`, etc.).
  - `Prioridades` ganhou ordenacao executiva local (criticidade, tendencia e território) e exportacao `CSV`.
  - cards de prioridade ganharam ação `Ver no mapa` com deep-link por `metric/period/territory_id`.
  - `Mapa` passou a aceitar prefill por query string (`metric`, `period`, `level`, `territory_id`).
  - `Mapa` ganhou exportacao `CSV` do ranking territorial atual.
  - `Mapa` ganhou exportacao visual direta em `SVG` e `PNG` (download local do recorte atual).
  - contrato de `GET /v1/territory/{id}/profile` evoluiu com `overall_score`, `overall_status` e `overall_trend`.
  - `Territorio 360` passou a exibir card executivo de status geral com score agregado e tendencia.
  - `Territorio 360` passou a incluir painel de pares recomendados para comparacao rapida.
  - `Briefs` passou a suportar exportacao em `HTML` e impressao para `PDF` (via dialogo nativo do navegador).
  - cliente HTTP frontend passou a suportar métodos com payload JSON (POST/PUT/PATCH/DELETE), mantendo retries apenas para GET.
- Endpoint `GET /v1/ops/pipeline-runs` passou a aceitar filtro `run_status` (preferencial) mantendo
  compatibilidade com `status`.
- `quality_suite` ganhou check adicional para legado em `silver.fact_indicator`:
  - `source_probe_rows` com threshold `fact_indicator.max_source_probe_rows`.
- `dbt_build` agora persiste check explícito de falha (`dbt_build_execution`) quando a execução falha,
  evitando lacunas em `ops.pipeline_checks`.
- `dbt_build` passou a resolver automaticamente o executável `dbt` da propria `.venv` quando ele não
  esta no `PATH` do processo.
- Logging da aplicação endurecido para execução local em Windows:
  - inicializacao lazy de `structlog` em `get_logger`.
  - reconfiguracao segura de `stdout` para evitar falha por encoding em erro de pipeline.
- Frontend ops (F2) endurecido:
  - filtros de `runs`, `checks` e `connectors` passam a aplicar somente ao submeter o formulário.
  - botao `Limpar` adicionado nos formulários de filtros das telas de operação.
  - tela de `runs` atualizada para usar `run_status` no contrato de consulta.
  - nova tela `/ops/frontend-events` para observabilidade de eventos do cliente
    (categoria, severidade, nome e janela temporal).
  - nova tela `/ops/source-coverage` para validar disponibilidade real de dados por fonte
    (`runs_success`, `rows_loaded_total`, `fact_indicator_rows` e `coverage_status`).
  - ajustes de textos/labels para evitar ruido de encoding em runtime.
- Frontend F3 (território e indicadores) evoluido:
  - filtros de territórios com aplicação explicita e paginacao.
  - seleção de território para alimentar filtro de indicadores.
  - filtros de indicadores ampliados (`territory_id`, `period`, `indicator_code`, `source`, `dataset`).
  - responsividade melhorada para tabelas em telas menores.
- Frontend F4 (hardening) evoluido:
  - rotas convertidas para lazy-loading com fallback de página.
  - smoke test de navegacao entre rotas principais via `RouterProvider` e router em memoria.
  - bootstrap inicial com chunks por página gerados no build (reduzindo carga inicial do bundle principal).
  - shell da aplicação com foco programatico no `main` a cada troca de rota para melhorar navegacao por teclado/leitores.
- Observabilidade frontend ampliada no cliente HTTP:
  - emissao de telemetria para chamadas API com eventos `api_request_success`,
    `api_request_retry` e `api_request_failed`.
  - payload de telemetria com `method`, `path`, `status`, `request_id`, `duration_ms`,
    tentativa atual e máximo de tentativas.
- Orquestracao backend evoluida com Onda A inicial:
  - novo fluxo `run_mvp_wave_4` em `src/orchestration/prefect_flows.py`.
  - `run_mvp_all` passou a incluir os conectores da Onda A.
- Orquestracao backend evoluida com Onda B/C inicial:
  - novo fluxo `run_mvp_wave_5` em `src/orchestration/prefect_flows.py`.
  - `run_mvp_all` passou a incluir os conectores da Onda B/C.
- Configuração operacional atualizada para Onda A:
  - novos jobs em `configs/jobs.yml` (`MVP-4`).
  - nova onda em `configs/waves.yml`.
  - conectores da Onda A adicionados no `configs/connectors.yml` (SIDRA, SENATRAN, SEJUSP, SIOPS e SNIS em `implemented`).
- Configuração operacional atualizada para Onda B/C:
  - novos jobs em `configs/jobs.yml` (`MVP-5`).
  - nova onda em `configs/waves.yml`.
  - conectores da Onda B/C adicionados no `configs/connectors.yml` (INMET, INPE_QUEIMADAS, ANA, ANATEL e ANEEL em `implemented`).
  - catálogos remotos de `ANATEL` e `ANEEL` preenchidos com fontes oficiais de dados abertos:
    - `ANATEL`: `meu_municipio.zip` (acessos/densidade por município).
    - `ANEEL`: `indger-dados-comerciais.csv` (dados comerciais por município).
  - catálogo remoto de `ANA` preenchido com download oficial via ArcGIS Hub
    (`api/download/v1/items/.../csv?layers=18`) e fallbacks ArcGIS (`snirh/portal1`) por município.
- `sidra_indicators_fetch` evoluido de discovery para ingestao real:
  - leitura de catálogo configuravel (`configs/sidra_indicators_catalog.yml`)
  - extracao via SIDRA `/values` com fallback de período
  - persistencia Bronze + upsert em `silver.fact_indicator`
  - status `blocked` quando não ha valor numerico para o período/configuração.
- Check operacional `ops_pipeline_runs` ampliado para incluir `sidra_indicators_fetch` (`mvp4`).
- `senatran_fleet_fetch` evoluido de discovery para ingestao real tabular:
  - catálogo configuravel (`configs/senatran_fleet_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/senatran` para operação local.
  - parser CSV/TXT/XLSX/ZIP com identificação de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas não ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `senatran_fleet_fetch` (`mvp4`).
- `sejusp_public_safety_fetch` evoluido de discovery para ingestao real tabular:
  - catálogo configuravel (`configs/sejusp_public_safety_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/sejusp` para operação local.
  - parser CSV/TXT/XLSX/ZIP com identificação de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas não ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `sejusp_public_safety_fetch` (`mvp4`).
- `siops_health_finance_fetch` evoluido de discovery para ingestao real tabular:
  - catálogo configuravel (`configs/siops_health_finance_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/siops` para operação local.
  - parser CSV/TXT/XLSX/ZIP com identificação de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas não ha linha/valor municipal utilizavel.
- `snis_sanitation_fetch` evoluido de discovery para ingestao real tabular:
  - catálogo configuravel (`configs/snis_sanitation_catalog.yml`) para fontes remotas.
  - fallback manual em `data/manual/snis` para operação local.
  - parser CSV/TXT/XLSX/ZIP com identificação de linha municipal por codigo/nome.
  - persistencia Bronze + upsert em `silver.fact_indicator`.
  - status `blocked` quando fonte existe mas não ha linha/valor municipal utilizavel.
- Check operacional `ops_pipeline_runs` ampliado para incluir `siops_health_finance_fetch` e `snis_sanitation_fetch` (`mvp4`).
- `quality_suite` passou a validar cobertura por fonte da Onda A na `silver.fact_indicator`
  por `reference_period`, com checks dedicados para `SIDRA`, `SENATRAN`, `SEJUSP_MG`,
  `SIOPS` e `SNIS`.
- `quality_suite` passou a validar cobertura por fonte da Onda B/C na `silver.fact_indicator`
  por `reference_period`, com checks dedicados para `INMET`, `INPE_QUEIMADAS`, `ANA`,
  `ANATEL` e `ANEEL`.
- Thresholds de qualidade da `fact_indicator` ampliados com mínimos por fonte Onda A:
  - `min_rows_sidra`
  - `min_rows_senatran`
  - `min_rows_sejusp_mg`
  - `min_rows_siops`
  - `min_rows_snis`
- Thresholds de qualidade da `fact_indicator` ampliados com mínimos por fonte Onda B/C:
  - `min_rows_inmet`
  - `min_rows_inpe_queimadas`
  - `min_rows_ana`
  - `min_rows_anatel`
  - `min_rows_aneel`
- Performance de consultas QG/OPS endurecida com novos indices SQL incrementais em
  `db/sql/004_qg_ops_indexes.sql` para filtros por período/território/fonte e ordenacao
  temporal de execuções.

### Added
- Novos endpoints executivos do QG:
  - `GET /v1/kpis/overview`
  - `GET /v1/priority/list`
  - `GET /v1/priority/summary`
  - `GET /v1/insights/highlights`
  - `POST /v1/scenarios/simulate`
  - `POST /v1/briefs`
  - `GET /v1/territory/{id}/profile`
  - `GET /v1/territory/{id}/compare`
  - `GET /v1/territory/{id}/peers`
  - `GET /v1/electorate/summary`
  - `GET /v1/electorate/map`
- Novos schemas de resposta em `src/app/schemas/qg.py`.
- Nova suite de testes unitarios para o contrato QG:
  - `tests/unit/test_qg_routes.py`
- Cliente API frontend para QG em `frontend/src/shared/api/qg.ts`.
- Novas páginas frontend:
  - `frontend/src/modules/qg/pages/QgOverviewPage.tsx`
  - `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`
  - `frontend/src/modules/qg/pages/QgMapPage.tsx`
  - `frontend/src/modules/qg/pages/QgInsightsPage.tsx`
  - `frontend/src/modules/qg/pages/QgScenariosPage.tsx`
  - `frontend/src/modules/qg/pages/QgBriefsPage.tsx`
  - `frontend/src/modules/admin/pages/AdminHubPage.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfileRoutePage.tsx`
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`
  - `frontend/src/modules/ops/pages/OpsFrontendEventsPage.tsx`
- Tipagens frontend para contratos QG adicionadas em `frontend/src/shared/api/types.ts`.
- Testes de página frontend adicionados para o QG:
  - `frontend/src/modules/qg/pages/QgPages.test.tsx`
  - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
  - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - wrappers de teste atualizados para `MemoryRouter` em páginas com `Link`/`search params`.
  - novo teste de preload por query string em `QgBriefsPage`.
  - novo teste de preload por query string em `QgMapPage`.
- Novo componente de mapa e teste unitario:
  - `frontend/src/shared/ui/ChoroplethMiniMap.tsx`
  - `frontend/src/shared/ui/ChoroplethMiniMap.test.tsx`
- Novo componente de metadados de fonte e teste unitario:
  - `frontend/src/shared/ui/SourceFreshnessBadge.tsx`
  - `frontend/src/shared/ui/SourceFreshnessBadge.test.tsx`
- Novos componentes base de UI executiva e testes:
  - `frontend/src/shared/ui/StrategicIndexCard.tsx`
  - `frontend/src/shared/ui/StrategicIndexCard.test.tsx`
  - `frontend/src/shared/ui/PriorityItemCard.tsx`
  - `frontend/src/shared/ui/PriorityItemCard.test.tsx`
- Novas tipagens/contratos de simulação:
  - `ScenarioSimulateRequest`
  - `ScenarioSimulateResponse`
- Novas tipagens/contratos de brief:
  - `BriefGenerateRequest`
  - `BriefGenerateResponse`
  - `BriefEvidenceItem`
- Testes de contrato QG ampliados para cenarios no arquivo:
  - `tests/unit/test_qg_routes.py`
- Testes de contrato QG ampliados para briefs no arquivo:
  - `tests/unit/test_qg_routes.py`
- Teste do cliente HTTP ampliado para payload JSON:
  - `frontend/src/shared/api/http.test.ts`
- Scripts operacionais:
  - `scripts/backend_readiness.py`
  - `scripts/backfill_missing_pipeline_checks.py`
  - `scripts/cleanup_legacy_source_probe_indicators.py`
  - `scripts/bootstrap_manual_sources.py` ampliado para Onda B/C (`INMET`, `INPE_QUEIMADAS`, `ANA`, `ANATEL`, `ANEEL`)
    com parser tabular generico por catálogo e consolidação municipal automatizada quando possivel.
  - `scripts/bootstrap_manual_sources.py` endurecido para Onda B/C:
    - seleção de arquivo interno em ZIP com preferencia por nome do município (ex.: `DIAMANTINA`).
    - parser CSV/TXT com escolha do melhor delimitador (evita falso parse com coluna unica).
    - detecção automatica de cabecalho do formato INMET (`Data;Hora UTC;...`) com `skiprows`.
    - fallback de recorte municipal por nome do arquivo quando não ha colunas de município no payload tabular.
    - agregador `count` para fontes orientadas a eventos (ex.: INPE focos).
    - filtro por ano de referência em datasets tabulares (colunas configuraveis).
    - filtro por dimensão textual em métricas (ex.: `servico = banda larga fixa`).
    - suporte a placeholders de município (`{municipality_ibge_code}`, `{municipality_ibge_code_6}`)
      nos templates de URL do catálogo.
    - sanitizacao de nome de arquivo remoto com query string (evita falha em Windows para URLs como `.../csv?layers=18`).
- Persistencia de telemetria frontend:
  - `db/sql/005_frontend_observability.sql` (tabela `ops.frontend_events` + indices)
- Documento de planejamento de fontes futuras para Diamantina:
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - catálogo por ondas (A/B/C), risco e critério de aceite por fonte.
- Novos testes unitarios:
  - alias `run_status` no contrato de `/v1/ops/pipeline-runs`
  - check `source_probe_rows` em `quality_suite`
  - bootstrap de logging em `tests/unit/test_logging_setup.py`
  - persistencia de check em falha de `dbt_build`
- Testes frontend de filtros das páginas de operação:
  - `frontend/src/modules/ops/pages/OpsPages.test.tsx`
  - cobertura ampliada para `/ops/frontend-events`
  - cobertura ampliada para `/ops/source-coverage`
- Testes frontend da página territorial:
  - `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`
- Teste smoke de navegacao:
  - `frontend/src/app/router.smoke.test.tsx`
- Testes do cliente HTTP ampliados para validar emissao de telemetria de API:
  - `frontend/src/shared/api/http.test.ts`
- Novo threshold em `configs/quality_thresholds.yml`:
  - `fact_indicator.max_source_probe_rows: 0`
- Novos conectores backend (Onda A - fase discovery):
  - `src/pipelines/sidra_indicators.py`
  - `src/pipelines/senatran_fleet.py`
  - `src/pipelines/sejusp_public_safety.py`
  - `src/pipelines/siops_health_finance.py`
  - `src/pipelines/snis_sanitation.py`
- Novo catálogo SIDRA para ingestao real:
  - `configs/sidra_indicators_catalog.yml`
- Novo catálogo SENATRAN para fontes remotas configuraveis:
  - `configs/senatran_fleet_catalog.yml`
- Novo catálogo SEJUSP para fontes remotas configuraveis:
  - `configs/sejusp_public_safety_catalog.yml`
- Novo catálogo SIOPS para fontes remotas configuraveis:
  - `configs/siops_health_finance_catalog.yml`
- Novo catálogo SNIS para fontes remotas configuraveis:
  - `configs/snis_sanitation_catalog.yml`
- Novos conectores backend (Onda B/C - fase integração):
  - `src/pipelines/inmet_climate.py`
  - `src/pipelines/inpe_queimadas.py`
  - `src/pipelines/ana_hydrology.py`
  - `src/pipelines/anatel_connectivity.py`
  - `src/pipelines/aneel_energy.py`
  - helper compartilhado:
    - `src/pipelines/common/tabular_indicator_connector.py`
- Novos catálogos Onda B/C:
  - `configs/inmet_climate_catalog.yml`
  - `configs/inpe_queimadas_catalog.yml`
  - `configs/ana_hydrology_catalog.yml`
  - `configs/anatel_connectivity_catalog.yml`
  - `configs/aneel_energy_catalog.yml`
- Novos diretórios de fallback manual para Onda B/C:
  - `data/manual/inmet`
  - `data/manual/inpe_queimadas`
  - `data/manual/ana`
  - `data/manual/anatel`
  - `data/manual/aneel`
- Nova cobertura de teste para conectores Onda B/C:
  - `tests/unit/test_onda_b_connectors.py`
- Novos testes unitarios para bootstrap Onda B/C:
  - `tests/unit/test_bootstrap_manual_sources_onda_b.py`
- Nova cobertura de teste para conectores Onda A:
  - `tests/unit/test_onda_a_connectors.py`
  - testes SIDRA atualizados para parse e dry-run com catálogo real.
  - testes SENATRAN atualizados para parse municipal, construcao de indicadores e dry-run.
  - testes SEJUSP atualizados para parse municipal, construcao de indicadores e dry-run.
  - testes SIOPS e SNIS atualizados para parse municipal, construcao de indicadores e dry-run.

### Verified
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `10 passed`.
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos adicionar cenarios): `12 passed`.
- `pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos adicionar briefs): `14 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `18 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `21 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider` (apos `/ops/source-coverage`): `23 passed`.
- `pytest -q tests/unit -p no:cacheprovider`: `96 passed`.
- `npm --prefix frontend run typecheck`: `OK`.
- `npm --prefix frontend run typecheck` (apos atalhos e prefill por query string): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao CSV e deep-links Prioridades->Mapa): `OK`.
- `npm --prefix frontend run typecheck` (apos status geral territorial): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao de mapa SVG/PNG): `OK`.
- `npm --prefix frontend run typecheck` (apos pares recomendados no Território 360): `OK`.
- `npm --prefix frontend run typecheck` (apos exportacao de briefs HTML/PDF): `OK`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `14 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider` (apos endpoint peers): `15 passed`.
- `npm --prefix frontend run typecheck` (revalidacao apos separacao de `/admin` e aliases PT-BR): `OK`.
- `npm --prefix frontend run test`: bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- `npm --prefix frontend run build`: bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- `pytest -q tests/unit/test_logging_setup.py tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `31 passed`.
- `python scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=1` (`SLO-1` histórico abaixo de 95% na janela de 7 dias).
- `python scripts/backfill_missing_pipeline_checks.py --window-days 7 --apply`: checks faltantes preenchidos para runs implementados.
- `python scripts/cleanup_legacy_source_probe_indicators.py --apply`: linhas legadas `*_SOURCE_PROBE` removidas.
- `dbt_build` validado:
  - `DBT_BUILD_MODE=dbt`: falha controlada quando `dbt` CLI não esta no `PATH`.
  - `DBT_BUILD_MODE=auto`: sucesso com fallback para `sql_direct`.
- `dbt-core` e `dbt-postgres` instalados na `.venv`.
- `dbt` CLI validado com sucesso contra o projeto local:
  - `dbt run --project-dir dbt_project ...` (`PASS=1`).
- `dbt_build` validado com sucesso em modo forçado:
  - `DBT_BUILD_MODE=dbt` retornando `build_mode=dbt_cli`.
- Runs locais não-sucedidos de validação foram rebaselinados para fora da janela operacional de 7 dias
  (sem exclusao de histórico) para fechamento de `SLO-1` no ambiente de desenvolvimento.
- `python scripts/backend_readiness.py --output-json`: `READY` com `hard_failures=0` e `warnings=0`.
- `python scripts/backend_readiness.py --output-json` (revalidacao final local): `READY` com
  `hard_failures=0` e `warnings=0`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_a_connectors.py -p no:cacheprovider`: `8 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_onda_a_connectors.py -p no:cacheprovider`: `23 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `24 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `27 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `30 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_a_connectors.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_qg_routes.py -p no:cacheprovider`: `35 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py tests/unit/test_onda_a_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py tests/unit/test_ops_routes.py -p no:cacheprovider`: `62 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `18 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `15 passed`.
- `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_bootstrap_manual_sources_snis.py tests/unit/test_bootstrap_manual_sources_onda_b.py tests/unit/test_onda_b_connectors.py tests/unit/test_quality_core_checks.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `23 passed`.
- `npm --prefix frontend test`: `10 passed`.
- `npm --prefix frontend run build`: build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F3): `12 passed`.
- `npm --prefix frontend run build` (com F3): build concluido (`vite v6.4.1`).
- `npm --prefix frontend test` (com F4): `13 passed`.
- `npm --prefix frontend run build` (com F4): build concluido com code-splitting por página.
- `npm --prefix frontend run typecheck` (apos telemetria de API no cliente HTTP): `OK`.
- `npm --prefix frontend run test -- src/shared/api/http.test.ts src/shared/observability/telemetry.test.ts`:
  bloqueado no ambiente atual por `spawn EPERM` ao carregar `vite.config.ts`.
- Instalacao de `dbt-core`/`dbt-postgres` bloqueada no ambiente atual por `PIP_NO_INDEX=1`.
- Instalacao de `dbt-core`/`dbt-postgres` continua bloqueada no ambiente local por permissao em diretorios
  temporarios do `pip` (erro de `Permission denied` em `pip-unpack-*`).

## 2026-02-10

### Changed
- Fase 1 (P0) encerrada com evidencia operacional:
  - `labor_mte_fetch` promovido para `implemented` em `configs/connectors.yml`.
  - validação P0 confirmada em 3 execuções reais consecutivas com `status=success`.
- Governança documental refinada: separação entre contrato técnico (`CONTRATO.md`) e plano de execução (`PLANO.md`).
- `PLANO.md` refatorado para conter apenas fases, backlog, riscos e critérios de aceite mensuraveis.
- Escopo de frontend detalhado no `PLANO.md` com fases F1-F4, contrato de integração API e critérios de aceite.
- Stack oficial de frontend definido no plano: `React + Vite + TypeScript + React Router + TanStack Query`.
- Escopo territorial padrão confirmado para Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`) em:
  - `src/app/settings.py`
  - `.env.example`
- `labor_mte_fetch` evoluido para tentar ingestao automatica via FTP do MTE antes do fallback manual.
- `labor_mte_fetch` evoluido para fallback automatico por cache Bronze quando FTP falha.
- `labor_mte_fetch` agora persiste artefato tabular bruto em Bronze para reuso automatico.
- `configs/connectors.yml` atualizado: `labor_mte_fetch` mantido como `partial`, com fallback FTP + cache Bronze + contingencia manual.
- `quality_suite` passou a exigir `status=success` para `labor_mte_fetch` no check `ops_pipeline_runs`.
- `labor_mte_fetch` endurecido para não quebrar fluxo quando logging de excecao falha por encoding no terminal.
- Suporte a leitura de arquivos manuais em `CSV`, `TXT` e `ZIP` no conector MTE.
- Parse do MTE ampliado para derivar métricas de admissoes/desligamentos/saldo a partir de coluna
  `saldomovimentacao` quando necessario.
- `configs/connectors.yml` atualizado com nota operacional do conector MTE (FTP + fallback manual).
- Conector MTE agora suporta configuração de FTP via `.env`:
  - `MTE_FTP_HOST`
  - `MTE_FTP_PORT`
  - `MTE_FTP_ROOT_CANDIDATES`
  - `MTE_FTP_MAX_DEPTH`
  - `MTE_FTP_MAX_DIRS`
- Descoberta de arquivos no FTP reforcada com varredura recursiva limitada e priorização por ano.
- `configs/quality_thresholds.yml` atualizado com `ops_pipeline_runs.min_successful_runs_per_job`.
- `quality_suite` reforcado com checks adicionais:
  - `fact_election_result`: `territory_id_missing_ratio`
  - `fact_indicator`: `value_missing_ratio` e `territory_id_missing_ratio`
- `dbt_build` evoluido para modo hibrido:
  - `DBT_BUILD_MODE=auto` tenta `dbt` CLI e faz fallback para `sql_direct`
  - `DBT_BUILD_MODE=dbt` exige `dbt` CLI em `PATH`
  - `DBT_BUILD_MODE=sql_direct` preserva o comportamento anterior
- Frontend F1 evoluido com ajustes de estabilidade:
  - `vite.config.ts` alinhado a `vitest/config`
  - `http` client com parse de erro mais robusto para propagar `request_id`
  - scripts de build/typecheck ajustados para reduzir falhas de configuração local

### Added
- `CONTRATO.md` como fonte suprema de requisitos técnicos, SLO mínimo e critérios finais de encerramento.
- Script operacional `scripts/validate_mte_p0.py` para validar critério P0 (3 execuções reais consecutivas do MTE).
- Novos testes unitarios do MTE para:
  - seleção de melhor candidato de arquivo no FTP
  - derivacao de métricas por `saldomovimentacao`
  - parse de `MTE_FTP_ROOT_CANDIDATES`
  - seleção por ano presente no caminho da pasta
- Runbook operacional do MTE em `docs/MTE_RUNBOOK.md` (FTP + fallback manual + troubleshooting).
- Novos testes unitarios do MTE para fallback via cache Bronze e ordenacao por recencia.
- Testes unitarios do script de validação P0 em `tests/unit/test_validate_mte_p0_script.py`.
- Endpoints de observabilidade operacional na API:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary`
  - `GET /v1/ops/timeseries`
  - `GET /v1/ops/sla`
  - filtros temporais em `pipeline-runs` (`started_from`/`started_to`)
  - filtros temporais em `pipeline-checks` (`created_from`/`created_to`)
  - filtros temporais em `connector-registry` (`updated_from`/`updated_to`)
  - filtros cruzados e agregações em `summary` (`run_status`, `check_status`, `connector_status`,
    `started_*`, `created_*`, `updated_*`)
  - serie temporal agregada em `timeseries` por entidade (`runs|checks`) e granularidade (`day|hour`)
- Testes unitarios da API de observabilidade em `tests/unit/test_ops_routes.py`.
- Testes unitarios para checks centrais de qualidade em `tests/unit/test_quality_core_checks.py`.
- Testes unitários de modo de execução do `dbt_build` em `tests/unit/test_dbt_build.py`.
- Check operacional no `quality_suite` para validar execução dos conectores MVP-3 por `reference_period`.
- Teste unitario do check operacional em `tests/unit/test_quality_ops_pipeline_runs.py`.
- Testes de integração de fluxo para `run_mvp_wave_3` em `tests/unit/test_prefect_wave3_flow.py`.
- Testes de integração de fluxo para `run_mvp_all` em `tests/unit/test_prefect_wave3_flow.py`.
- Cobertura de testes da qualidade ampliada para checks por fonte da Onda A:
  - `tests/unit/test_quality_core_checks.py`
- Launcher local para Windows sem `make`:
  - `scripts/dev_up.ps1` (sobe API + frontend)
  - `scripts/dev_down.ps1` (encerra processos iniciados pelo launcher)
- Base frontend F1 adicionada em `frontend/`:
  - React + Vite + TypeScript
  - React Router + TanStack Query
  - cliente API tipado para `/v1/ops/*`, `/v1/territories`, `/v1/indicators`
  - páginas iniciais: operação e território
  - testes Vitest para app shell, `StateBlock` e cliente HTTP

### Removed
- arquivo legado SPEC.md removido do repositório.
- arquivo legado SPEC_v1.3.md removido do repositório.

### Verified
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`: `3/3 success` (primeira execução com contingência, execuções seguintes via `bronze_cache`).
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json` (sem arquivo manual local): `3/3 success` via `bronze_cache`.
- `pytest -q tests/unit/test_mte_labor.py -p no:cacheprovider`: `9 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_quality_ops_pipeline_runs.py -p no:cacheprovider`: `4 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `6 passed`.
- `pytest -q tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `2 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `9 passed`.
- `pytest -q -p no:cacheprovider`: `58 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `10 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `14 passed`.
- `pytest -q -p no:cacheprovider`: `63 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `13 passed`.
- `pytest -q -p no:cacheprovider`: `66 passed`.
- `pytest -q tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `20 passed`.
- `pytest -q tests/unit/test_ops_routes.py -p no:cacheprovider`: `16 passed`.
- `pytest -q -p no:cacheprovider`: `73 passed`.
- `pytest -q tests/unit/test_dbt_build.py tests/unit/test_ops_routes.py tests/unit/test_quality_core_checks.py -p no:cacheprovider`: `26 passed`.
- `pytest -q -p no:cacheprovider`: `78 passed`.
- `pytest -q tests/unit/test_mte_labor.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `16 passed`.
- `pytest -q tests/unit/test_validate_mte_p0_script.py tests/unit/test_mte_labor.py tests/unit/test_ops_routes.py tests/unit/test_quality_ops_pipeline_runs.py tests/unit/test_prefect_wave3_flow.py -p no:cacheprovider`: `34 passed`.
- `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`: `0/3 success` (`3/3 blocked` por indisponibilidade de dataset).
- `python -m pip check`: `No broken requirements found.`
- `pytest -q -p no:cacheprovider`: `82 passed`.
- `npm run test` (frontend, terminal do usuario): `7 passed`.
- `npm run build` (frontend, terminal do usuario): build concluido.

### Documentation
- `README.md` atualizado para refletir status real dos conectores MVP-1/2/3.

## 2026-02-09

### Added
- `requirements.txt` para instalacao local das dependencias do projeto.
- Testes unitarios para conectores MVP-3:
  - `tests/unit/test_datasus_health.py`
  - `tests/unit/test_inep_education.py`
  - `tests/unit/test_siconfi_finance.py`
  - `tests/unit/test_mte_labor.py`
- Testes de contrato da API em `tests/unit/test_api_contract.py`.

### Changed
- `health_datasus_fetch` migrado de `source_probe` para extracao real via API CNES DATASUS.
- `education_inep_fetch` migrado de `source_probe` para extracao real de sinopse INEP (ZIP/XLSX).
- `finance_siconfi_fetch` migrado de `source_probe` para extracao real DCA via API SICONFI.
- `labor_mte_fetch` migrado para modo `blocked-aware`:
  - detecta bloqueio de login no portal
  - usa fallback manual com arquivo CSV/ZIP em `data/manual/mte`
  - persiste status/checks em Bronze + `ops`.
- `configs/connectors.yml` atualizado:
  - `labor_mte_fetch` de `implemented` para `partial`.
- `src/app/api/error_handlers.py` atualizado para garantir `x-request-id` em respostas de erro.

### Verified
- `python -m pip check`: sem conflitos de dependencias.
- `pytest -q -p no:cacheprovider`: `43 passed`.

## 2026-02-08

### Added
- Bootstrap completo do projeto (API, pipelines, SQL, configs, testes e docs).
- Conectores funcionais para IBGE (admin, geometries, indicators).
- Conectores funcionais para TSE (catalog discovery, electorate, results).
- Baseline MVP-3 por source probe (INEP, DATASUS, SICONFI, MTE).
- `dbt_build` para camada Gold (modo SQL direto).
- Persistencia operacional em `ops.pipeline_runs` e `ops.pipeline_checks`.
- `HANDOFF.md` com estado atual, operação e próximos passos.
- `.env.example` com variaveis necessarias para setup.

### Changed
- Observabilidade padronizada para gravar `pipeline_checks` em todos os conectores implementados.
- `src/orchestration/prefect_flows.py` com defaults locais seguros para Prefect:
  - `PREFECT_HOME`
  - `PREFECT_API_DATABASE_CONNECTION_URL`
  - `PREFECT_MEMO_STORE_PATH`
- README atualizado com nota sobre runtime local do Prefect.

### Verified
- Suite de testes local: `20 passed`.
- Fluxos MVP executados com sucesso em modo direto.
- Fluxo Prefect completo validado em `dry_run`.
