# Plano Integrado de Implementacao (Backend + Frontend QG)

Data de referencia: 2026-02-20  
Status: execucao ativa (fase de estabilizacao UX/mapa + go-live controlado)  
Escopo: plano executavel para consolidar QG estrategico em producao com dados reais.

## 0) Regra de foco operacional (WIP=1)

1. Fila ativa unica de implementacao:
   - trilha corrente: D3 / BD-033 (estabilizacao final de UX/mapa executivo) encerrada em 2026-02-20 (`issue #28` fechada).
   - proxima trilha ativa: a definir (WIP=1, sem execucao paralela).
2. Enquanto a trilha ativa nao fechar gate de saida, nao iniciar:
   - D4, D5, D6, D7, D8;
   - novas frentes de fonte/conector fora do escopo corrente;
   - refinamentos nao criticos sem impacto direto no gate atual.
3. Fonte unica de sequencia de execucao:
   - este arquivo (secoes `5` e `9`).
   - `docs/HANDOFF.md` registra apenas estado corrente e proximo passo imediato da mesma trilha.
4. Demais documentos (`BACKLOG_DADOS_NIVEL_MAXIMO.md`) sao norte macro/catalogo e nao devem abrir fila paralela no ciclo diario.
5. Classificacao oficial de documentos ativos/descontinuados fica em `docs/GOVERNANCA_DOCUMENTAL.md`.

## 0.1) Mapa de governanca documental (fonte unica)

1. `docs/CONTRATO.md`:
   - papel: requisitos tecnicos obrigatorios.
   - pode abrir implementacao nova? nao.
2. `docs/PLANO_IMPLEMENTACAO_QG.md`:
   - papel: fila ativa, sequencia e criterio de aceite da rodada.
   - pode abrir implementacao nova? sim (fonte unica).
3. `docs/HANDOFF.md`:
   - papel: estado corrente da trilha ativa + evidencias recentes.
   - pode abrir implementacao nova? nao (apenas refletir fila do plano executavel).
4. `docs/CHANGELOG.md`:
   - papel: historico do que foi entregue e validado.
   - pode abrir implementacao nova? nao.
5. `docs/VISION.md`:
   - papel: north star de produto (direcao da experiencia e do valor de negocio).
   - pode abrir implementacao nova? nao, sem passagem pela fila deste plano.
6. `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`:
   - papel: backlog tecnico macro D0-D8.
   - pode abrir implementacao nova? nao, sem passagem pelo plano executavel.
7. `docs/GOVERNANCA_DOCUMENTAL.md`:
   - papel: inventario e regra de uso dos docs (ativos, complementares, descontinuados).
   - pode abrir implementacao nova? nao.

## 1) Objetivo

Entregar e estabilizar o QG estrategico municipal de Diamantina/MG, com:

1. Home executiva para leitura rapida.
2. Priorizacao territorial explicavel.
3. Mapa analitico com recorte por indicador/periodo.
4. Territorio 360 com comparacao orientada.
5. Camada institucional de eleitorado.
6. Fluxo tecnico isolado em `/admin`.
7. Extensoes operacionais de decisao (`/cenarios` e `/briefs`).

## 2) Premissas e decisoes vigentes

1. Fonte de verdade tecnica: `CONTRATO.md`.
2. `docs/VISION.md` define a direcao de produto (north star), sem substituir contrato tecnico nem a fila executavel deste plano.
3. Camada tecnica segue separada da UX executiva (sem foco em auth nesta fase).
4. Entrega segue vertical (API + pipeline + UI + teste), por bloco de valor.
5. Modelo principal de integracao de dados continua em `silver.fact_indicator`, com rastreabilidade de `source`, `dataset`, `reference_period` e metadados.
6. O north star de produto e concentrado em `docs/VISION.md`, sem competir com este plano executavel.
7. Catalogo/priorizacao de fontes e consolidado em `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`; validacao de estado atual fica em `HANDOFF.md` e `ops/readiness`.

## 2.1 Consolidacao documental (feito em 2026-02-13)

1. Visao estrategica consolidada em `docs/VISION.md`.
2. Execucao e priorizacao consolidada neste arquivo.
3. Estado operacional e validacoes correntes consolidadas em `HANDOFF.md`.
4. Rastreabilidade operacional consolidada em `docs/HANDOFF.md` + `docs/CHANGELOG.md`.
5. Specs-base da visao estrategica consolidadas (v1.0):
   - `MAP_PLATFORM_SPEC.md`
   - `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
   - `STRATEGIC_ENGINE_SPEC.md`
6. Proximo passo documental: manter sincronia continua das specs com cada entrega vertical (codigo + teste + operacao).

## 2.2 Status por onda (fonte unica)

1. Onda 0: concluida.
2. Onda 1: concluida.
3. Onda 2: concluida.
4. Onda 3: concluida.
5. Onda 4: concluida.
6. Onda 5: em andamento avancado (MP-1, MP-2 e MP-3 entregues; pendente consolidacao UX final e recursos pos-v1).
7. Onda 6: em andamento (UX imersiva com mapa dominante + ajuste de usabilidade em telas executivas).
8. Onda 7: concluida v1 (cenarios/briefs), com refinamentos pendentes.
9. Onda 8: em andamento (E2E fluxo critico concluido, cache HTTP ativo, MVs e GIST criados, benchmark p95 criado, edge-cases 44 testes, acessibilidade concluida).

## 3) Estado consolidado atual

## 3.1 Backend/API

1. Contratos QG implementados e ativos:
   - `GET /v1/kpis/overview`
   - `GET /v1/priority/list`
   - `GET /v1/priority/summary`
   - `GET /v1/insights/highlights`
   - `GET /v1/geo/choropleth`
   - `GET /v1/territory/{id}/profile`
   - `GET /v1/territory/{id}/compare`
   - `GET /v1/territory/{id}/peers`
   - `GET /v1/electorate/summary`
   - `GET /v1/electorate/map`
   - `POST /v1/scenarios/simulate`
   - `POST /v1/briefs`
2. Camada ops/observabilidade ativa:
   - `GET /v1/ops/*`
   - `POST /v1/ops/frontend-events`
   - `GET /v1/ops/frontend-events`
   - `GET /v1/ops/source-coverage`
3. Readiness local atual: `READY` com `hard_failures=0` e `warnings=1` (SLO-1 historico na janela de 7 dias).

## 3.2 Frontend

1. Rotas executivas ativas:
   - `/`
   - `/prioridades`
   - `/mapa`
   - `/territorio/:territoryId`
   - `/insights`
   - `/eleitorado`
   - `/cenarios`
   - `/briefs`
   - `/admin`
2. Recursos ja entregues:
   - deep-link por query string (mapa/prioridades/insights/briefs/cenarios).
   - exportacoes no mapa (CSV/SVG/PNG).
   - exportacao de brief (HTML + print para PDF).
   - metadados de fonte/frescor/cobertura nas telas executivas.
   - padronizacao de dominios e rotulos amigaveis (QG e Territorio 360).
3. Testes e build do frontend estaveis no ciclo atual.

## 3.3 Pipelines e fontes

1. Ondas Onda A e Onda B/C implementadas e integradas no orquestrador (`run_mvp_wave_4`, `run_mvp_wave_5`, `run_mvp_all`).
2. Estado de conectores sincronizado em `ops.connector_registry` com 22 conectores `implemented`.
3. Fluxos reais recentes executados com sucesso para ondas 4 e 5.

## 3.4 Atualizacao de estabilizacao (2026-02-20)

1. Mapa vetorial:
   - correcao de recenter indevido no zoom em `VectorMap`.
   - reducao de fallback agressivo para SVG em erros transitorios.
   - hardening de tiles MVT territoriais com saneamento de geometria no backend.
2. Eleitorado:
   - fallback de ano logico (`requested_year`) para ano de armazenamento outlier (`storage_year`) em endpoints de resumo e mapa.
   - tela executiva de eleitorado com estados vazios/erros mais claros.
3. Estabilidade de frontend:
   - regressao de hooks corrigida em `QgInsightsPage` e `TerritoryProfilePage` (erro: `Rendered more hooks than during the previous render`).
   - paginacao adicionada para listas longas em Insights e Territorio 360.
4. Validacao consolidada:
   - backend: `55 passed` (rotas qg/tse + mvt/cache).
   - frontend: `72 passed` + build `OK`.
5. Revalidacao operacional (2026-02-20 - ciclo atual):
   - gate BD-033 reexecutado:
     - backend: `29 passed` + `26 passed`;
     - frontend: `78 passed` + build `OK`.
   - fase 2 executada:
     - scorecard exportado em `data/reports/data_coverage_scorecard.json` (`pass=5`, `warn=8`);
     - readiness `READY` (`hard_failures=0`, `warnings=0`);
     - benchmark urbano `ALL PASS` em `data/reports/benchmark_urban_map.json` (p95 entre `103.7ms` e `123.5ms`).
6. Hotfix de UX de mapa (2026-02-20 - pos-gate):
   - contraste corrigido para botoes de `Modo de visualizacao` e `Mapa base` no frontend;
   - toggle da sidebar da Home com texto legivel;
   - layout dominante ajustado para eliminar faixa vazia sob o mapa;
   - piso de zoom contextual aplicado no carregamento do mapa para evitar `z0`;
   - painel de filtros da Home reposicionado para coluna lateral dedicada no desktop (sem sobrepor o mapa);
   - alinhamento interno dos controles do painel revisado (acoes, mapa base, navegacao) com correcao de overflow textual em cards.

## 4) Status por sprint

1. Sprint 0 (contratos e base): concluida.
2. Sprint 1 (Home + Prioridades): concluida.
3. Sprint 2 (Mapa + Territorio 360): concluida.
4. Sprint 3 (Onda A parte 1 + Insights): concluida.
5. Sprint 4 (Onda A parte 2 + Eleitorado): concluida.
6. Sprint 5 (hardening QG v1): em andamento.
7. Sprint 6 (extensoes v1.1: cenarios/briefs): concluida.

## 5) Escopo de proxima execucao (ciclo atual)

## 5.1 Prioridade alta

1. Fechar estabilizacao de UX nas telas executivas com foco em mapa, Territorio 360 e Eleitorado:
   - eliminar estados vazios sem contexto;
   - melhorar distribuicao visual de filtros, cards e tabelas;
   - garantir comportamento previsivel de paginacao em listas longas.
2. Consolidar navegacao do mapa vetorial para uso operacional continuo:
   - manter zoom/drag sem recentralizacao indevida;
   - reduzir degradacao para SVG apenas em indisponibilidade real do vetor;
   - reforcar feedback de erro para tiles indisponiveis (`503`) sem quebrar o fluxo.
3. Completar cobertura de camada eleitoral territorial no frontend:
   - expor `local_votacao` com toggle/legenda/tooltip;
   - manter transparencia de `official/proxy/hybrid` nas camadas.
4. Executar homologacao ponta a ponta com dados reais e registrar evidencia unica em `docs/HANDOFF.md`.
5. Executar backlog UX executivo unificado em ciclo unico:
   - fonte de execucao: secoes de prioridade deste plano (`5.1`, `5.2`, `5.3`);
   - ordem obrigatoria: `P0 -> P1 -> P2`;
   - sem abrir nova frente antes de concluir os itens de prioridade alta.

## 5.2 Prioridade media

1. Revalidar desempenho das rotas executivas e de mapa com benchmark recorrente:
   - alvo p95 <= 800ms (executivo) e <= 1000ms (urbano), conforme runbook vigente.
2. Fechar consolidacao operacional de runbooks:
   - `docs/OPERATIONS_RUNBOOK.md` (runbook unico)
3. Fortalecer cobertura de testes:
   - backend: rotas qg/map/electorate para cenarios limite e regressao;
   - frontend: fluxos completos de navegacao e estados de erro/vazio.

## 5.3 Prioridade baixa

1. Refinar painel tecnico `/admin` para diagnostico rapido sem poluir UX executiva.
2. Evoluir backlog pos-v2 do mapa (split view, time slider e comparacao temporal), sem abrir nova frente antes dos gates de estabilizacao.

## 6) Matriz de fontes e consumo no QG

## Onda A

1. SIDRA (`sidra_indicators_fetch`): Home, Prioridades, Perfil.
2. SENATRAN (`senatran_fleet_fetch`): Home, Perfil, Insights.
3. SEJUSP-MG (`sejusp_public_safety_fetch`): Home, Mapa, Prioridades.
4. SIOPS (`siops_health_finance_fetch`): Home, Perfil, Insights.
5. SNIS (`snis_sanitation_fetch`): Home, Mapa, Perfil.

## Onda B/C

1. INMET (`inmet_climate_fetch`): Home, Insights, Perfil.
2. INPE Queimadas (`inpe_queimadas_fetch`): Home, Mapa, Insights.
3. ANA (`ana_hydrology_fetch`): Home, Mapa, Perfil.
4. ANATEL (`anatel_connectivity_fetch`): Home, Perfil, Prioridades.
5. ANEEL (`aneel_energy_fetch`): Home, Perfil, Insights.

## 7) Criterios de aceite para go-live controlado

1. Endpoints executivos e extensoes (`cenarios`/`briefs`) estaveis com testes de contrato.
2. Ondas A e B/C operando com:
   - Bronze + manifesto/checksum
   - Silver com `territory_id`
   - checks de qualidade ativos
   - rastreio em `ops.pipeline_runs` e `ops.pipeline_checks`
3. Frontend com testes e build estaveis no ciclo de entrega.
4. Fluxo executivo separado da camada tecnica (`/admin`).
5. Homologacao executada com dados reais e sem bloqueador critico aberto.
6. Metas operacionais objetivas registradas e validadas:
   - API executiva p95 <= 800ms em homologacao para endpoints criticos.
   - render inicial da Home executiva <= 3s em ambiente de referencia.
   - E2E do fluxo principal com taxa de sucesso >= 95% no ciclo de release.

## 8) Riscos atuais e mitigacoes

1. Instabilidade eventual de fonte externa:
   - mitigacao: fallback por catalogo/manual + bronze cache + testes de conector.
2. SLO operacional distorcido por historico antigo:
   - mitigacao: separar leitura de saude corrente e historica nos relatorios.
3. Divergencia entre narrativa e dado:
   - mitigacao: manter regras de prioridade/insight versionadas e auditaveis no backend.
4. Regressao de UX em evolucoes rapidas:
   - mitigacao: ampliar E2E dos caminhos de decisao e manter smoke de roteamento.

## 9) Ordem recomendada para os proximos passos

1. Finalizar estabilizacao visual/UX nas telas executivas com evidencias de teste.
2. Revalidar readiness completo (backend + frontend + benchmark) em ambiente limpo.
3. Fechar pendencias de camada eleitoral territorial no mapa (`local_votacao`).
4. Consolidar runbooks e rotina semanal de robustez de dados.
5. Planejar proximo ciclo incremental (mapa pos-v2 e evolucoes analiticas controladas).

## 10) Trilha oficial para nivel maximo de dados

Backlog executavel:
- `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`

Regra de execucao:
1. a trilha D0-D8 do backlog de dados passa a ser o caminho oficial de evolucao de robustez.
2. qualquer nova fonte fora do backlog precisa de registro de justificativa e impacto.
3. o status de cada sprint D* deve ser refletido em `docs/HANDOFF.md` e `docs/CHANGELOG.md`.
