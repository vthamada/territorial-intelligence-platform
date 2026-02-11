# Territorial Intelligence Platform - Handoff

Data de referencia: 2026-02-11
Planejamento principal: `PLANO.md`
Contrato tecnico principal: `CONTRATO.md`

## Atualizacao rapida (2026-02-11)

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
  - `POST /v1/scenarios/simulate` (simulacao simplificada por variacao percentual).
  - simulacao evoluida para calcular ranking antes/depois por indicador e delta de posicao.
  - `POST /v1/briefs` para geracao de brief executivo com resumo e evidencias.
- Sprint 3/4 (Onda A) iniciado no backend:
  - `sidra_indicators_fetch` evoluido para ingestao real via SIDRA API (`implemented`).
  - `senatran_fleet_fetch` evoluido para ingestao real tabular (`implemented`).
  - `sejusp_public_safety_fetch` evoluido para ingestao real tabular (`implemented`).
  - `siops_health_finance_fetch` evoluido para ingestao real tabular (`implemented`).
  - `snis_sanitation_fetch` evoluido para ingestao real tabular (`implemented`).
  - Onda A de conectores concluida no backend em modo implementado.
  - todos integrados no orquestrador em `run_mvp_wave_4` e `run_mvp_all`.
- Frontend integrado ao novo contrato QG:
  - rota inicial (`/`) com `QgOverviewPage` consumindo `kpis/overview`, `priority/summary` e `insights/highlights`.
  - rota `prioridades` com `QgPrioritiesPage` consumindo `priority/list`.
  - rota `mapa` com `QgMapPage` consumindo `geo/choropleth`.
  - `mapa` agora possui visualizacao geografica simplificada (SVG) com escala de valor e selecao de territorio.
  - rota `insights` com `QgInsightsPage` consumindo `insights/highlights`.
  - rota `cenarios` com `QgScenariosPage` consumindo `POST /v1/scenarios/simulate`.
  - tela de cenarios passou a exibir score e ranking antes/depois com impacto estimado.
  - rota `briefs` com `QgBriefsPage` consumindo `POST /v1/briefs`.
  - Home QG passou a exibir `Top prioridades` (previsualizacao) e `Acoes rapidas` para fluxo de decisao.
  - acao `Ver no mapa` da Home passou a abrir diretamente o recorte da prioridade mais critica.
  - `Territorio 360` passou a oferecer atalhos para `briefs` e `cenarios` com territorio/periodo pre-preenchidos.
  - `QgBriefsPage` e `QgScenariosPage` passaram a aceitar query string para prefill de filtros.
  - `QgPrioritiesPage` passou a oferecer ordenacao local e exportacao CSV da lista priorizada.
  - `PriorityItemCard` ganhou deep-link `Ver no mapa` para recorte de indicador/periodo/territorio.
  - `QgMapPage` passou a aceitar query string para prefill de filtros e selecao territorial inicial.
  - `QgMapPage` ganhou exportacao CSV do ranking territorial.
  - `QgMapPage` ganhou exportacao visual do mapa em `SVG` e `PNG`.
  - endpoint `GET /v1/territory/{id}/profile` evoluiu com score/status/tendencia agregados do territorio:
    - `overall_score`
    - `overall_status`
    - `overall_trend`
  - `TerritoryProfilePage` passou a exibir card executivo de status geral com score consolidado e tendencia.
  - endpoint `GET /v1/territory/{id}/peers` adicionado para sugerir comparacoes por similaridade de indicadores.
  - `TerritoryProfilePage` passou a exibir painel de pares recomendados com acao direta `Comparar`.
  - `QgBriefsPage` passou a suportar exportacao do brief em `HTML` e impressao para `PDF` pelo navegador.
  - rota `territorio/perfil` (alias legado: `territory/profile`) com `TerritoryProfilePage` (profile + compare).
  - rota dinamica `territorio/:territoryId` (alias legado: `territory/:territoryId`) com `TerritoryProfileRoutePage`.
  - rota `eleitorado` (alias legado: `electorate/executive`) com `ElectorateExecutivePage` (summary + map).
  - links de contexto (`Abrir perfil`) adicionados em `Mapa` e `Prioridades` para navegação direta ao perfil territorial.
  - rota `admin` adicionada como hub tecnico, separando links operacionais (`ops/*`) do menu principal executivo.
  - metadados de fonte/atualizacao/cobertura expostos nas telas executivas com `SourceFreshnessBadge`.
  - Home QG evoluida para usar `StrategicIndexCard` na secao de situacao geral.
  - lista de prioridades evoluida para `PriorityItemCard` (cards com score, racional, evidencia e acao).
  - cliente dedicado em `frontend/src/shared/api/qg.ts` e tipagens QG em `frontend/src/shared/api/types.ts`.
  - cobertura de teste de pagina adicionada para fluxo QG em:
    - `frontend/src/modules/qg/pages/QgPages.test.tsx`
    - `frontend/src/modules/territory/pages/TerritoryProfilePage.test.tsx`
    - `frontend/src/modules/electorate/pages/ElectorateExecutivePage.test.tsx`
  - wrappers de teste com `MemoryRouter` adicionados nas paginas com navegacao interna.
  - testes QG ampliados para validar prefill por query string no mapa e deep-links de prioridade.
- Hardening frontend (Sprint 5) iniciado:
  - acessibilidade minima no shell: `skip link` para conteudo principal e foco visivel padronizado.
  - foco programatico no conteudo principal (`main`) em trocas de rota.
  - observabilidade basica frontend:
    - captura de `window.error` e `unhandledrejection`.
    - captura de metricas de performance/web-vitals (paint, LCP, CLS e navigation timing).
    - evento de navegacao por troca de rota (`route_change`).
  - endpoint de telemetria configuravel por `VITE_FRONTEND_OBSERVABILITY_URL`.
  - cliente HTTP passou a emitir telemetria de chamadas API:
    - `api_request_success`
    - `api_request_retry`
    - `api_request_failed`
    com `method`, `path`, `status`, `request_id`, `duration_ms` e tentativas.
- Validacao frontend:
  - `npm --prefix frontend run typecheck`: `OK`.
  - `npm --prefix frontend run typecheck` (apos telemetria de API no cliente HTTP): `OK`.
  - `npm --prefix frontend run typecheck` (apos hardening de a11y/observabilidade): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao SVG/PNG): `OK`.
  - `npm --prefix frontend run typecheck` (apos exportacao de briefs HTML/PDF): `OK`.
  - `npm --prefix frontend run test`/`build`: bloqueados no ambiente atual por erro `spawn EPERM` ao carregar Vite.
  - `npm --prefix frontend run test -- src/shared/api/http.test.ts src/shared/observability/telemetry.test.ts`:
    bloqueado no ambiente atual por `spawn EPERM` ao carregar Vite.
- Validacao backend do contrato QG:
  - `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_qg_routes.py -p no:cacheprovider`: `15 passed`.
- Router QG integrado ao app em `src/app/api/main.py`.
- Schemas dedicados do QG adicionados em `src/app/schemas/qg.py`.
- Testes unitarios de contrato do QG adicionados em `tests/unit/test_qg_routes.py` e validados.
  - estado atual local: `14 passed` (incluindo cenarios e briefs).
- Testes de orquestracao e conectores Onda A adicionados/atualizados:
  - `tests/unit/test_prefect_wave3_flow.py`
  - `tests/unit/test_onda_a_connectors.py`
  - `tests/unit/test_quality_ops_pipeline_runs.py`
  - validacao local: `35 passed` em `test_onda_a_connectors + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_qg_routes`.
  - validacao local consolidada: `62 passed` em
    `test_qg_routes + test_onda_a_connectors + test_quality_core_checks + test_quality_ops_pipeline_runs + test_prefect_wave3_flow + test_ops_routes`.
- Hardening aplicado no backend:
  - alias `run_status` em `/v1/ops/pipeline-runs` (compatibilidade com `status`).
  - check `source_probe_rows` no `quality_suite` com threshold versionado.
  - checks de cobertura por fonte Onda A no `quality_suite` (SIDRA, SENATRAN, SEJUSP_MG, SIOPS e SNIS)
    por `reference_period`.
  - thresholds da `fact_indicator` calibrados com minimo de linhas por fonte Onda A.
  - novos indices SQL incrementais para consultas QG/OPS em `db/sql/004_qg_ops_indexes.sql`.
  - telemetria frontend persistida no backend:
    - `POST /v1/ops/frontend-events` (ingestao)
    - `GET /v1/ops/frontend-events` (consulta paginada)
    - tabela `ops.frontend_events` em `db/sql/005_frontend_observability.sql`.
  - scripts de operacao: readiness, backfill de checks e cleanup de legados.
  - `dbt_build` persiste check de falha em `ops.pipeline_checks` quando run falha.
  - logging robusto para execucao local em Windows (sem quebra por encoding).
- Estado operacional atual do backend:
  - `scripts/backend_readiness.py --output-json` retorna `READY` com `hard_failures=0` e `warnings=0`.
  - `SLO-1` e `SLO-3` atendidos na janela operacional de 7 dias no ambiente local.
- Pesquisa de fontes futuras concluida e consolidada em:
  - `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
  - priorizacao por ondas, complexidade e impacto para o municipio de Diamantina.
- Frontend F2 (operacao) evoluido:
  - filtros de `runs`, `checks` e `connectors` com aplicacao explicita via botao.
  - botao `Limpar` nos formularios de filtros.
  - contrato de filtro de runs alinhado para `run_status`.
  - nova tela tecnica `/ops/frontend-events` com filtros/paginacao para telemetria do frontend.
  - testes de paginas ops adicionados em `frontend/src/modules/ops/pages/OpsPages.test.tsx`.
- Frontend F3 (territorio e indicadores) evoluido:
  - filtros territoriais com paginacao e aplicacao explicita.
  - selecao de territorio para compor filtro de indicadores.
  - filtros de indicadores ampliados (periodo, codigo, fonte, dataset, territorio).
  - melhorias de responsividade de tabelas.
  - testes adicionados em `frontend/src/modules/territory/pages/TerritoryIndicatorsPage.test.tsx`.
- Frontend F4 (hardening) evoluido:
  - lazy-loading nas rotas principais (`ops` e `territory`) com fallback de carregamento.
  - smoke test de navegacao ponta a ponta no frontend:
    `frontend/src/app/router.smoke.test.tsx`.
  - build com chunks por pagina confirmado em `dist/assets/*Page-*.js`.
- Bloqueador de fechamento total da Fase 2:
  - sem bloqueador tecnico pendente de backend no estado atual.
  - observacao operacional: validacoes de `dbt` no Windows podem exigir terminal elevado por politica local
    de permissao (WinError 5).

## 1) O que foi implementado ate agora

### Arquitetura e operacao
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
  - payload padrao `validation_error|http_error|internal_error`
  - cabecalho `x-request-id` garantido em respostas de erro (incluindo 500)
- Novos testes de contrato em `tests/unit/test_api_contract.py`.
- Endpoints de observabilidade operacional adicionados:
  - `GET /v1/ops/pipeline-runs`
  - `GET /v1/ops/pipeline-checks`
  - `GET /v1/ops/connector-registry`
  - `GET /v1/ops/summary` (agregado por status/wave para runs/checks/connectors)
  - `GET /v1/ops/timeseries` (serie temporal por `runs|checks` em granularidade `day|hour`)
  - `GET /v1/ops/sla` (taxa de sucesso e metricas de duracao por job/wave)
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
  - configuracao via `.env` para host/porta/raizes/profundidade/limite de varredura FTP
  - persistencia de artefato tabular bruto em Bronze para reuso automatico em execucoes futuras

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
- Testes do `dbt_build` ampliados para validar modo de execucao (`auto|dbt|sql_direct`) em `tests/unit/test_dbt_build.py`.
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
  - paginas iniciais de operacao e territorio
  - testes de UI e cliente API (`vitest`)
- Validacoes recentes:
  - `python -m pip check`: sem conflitos
  - `pytest -q -p no:cacheprovider`: `82 passed`
  - `npm run test` (frontend): `7 passed` (validado no terminal do usuario)
  - `npm run build` (frontend): build concluido (validado no terminal do usuario)

## 2) Estado operacional atual

- Banco PostgreSQL/PostGIS conectado e funcional.
- Escopo territorial padrao confirmado para Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`) em `settings` e `.env.example`.
- Conectores MVP-1 e MVP-2: `implemented`.
- Conectores MVP-3:
  - INEP, DATASUS, SICONFI: `implemented` com ingestao real.
  - MTE: `implemented`; operacao automatica via FTP com fallback por cache Bronze e fallback manual de contingencia.
- `pip check`: sem dependencias quebradas.
- Frontend:
  - F1 concluido no repositorio (`frontend/`)
  - stack oficial ativa: `React + Vite + TypeScript + React Router + TanStack Query`
  - base de integracao com backend pronta (`/v1/ops/*`, `/v1/territories`, `/v1/indicators`)
  - proximas entregas: F2 (telas operacionais completas), F3 (territorio/indicadores), F4 (hardening)

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

### 4.2 Validacao rapida
1. `python -m pip check`
2. `pytest -q -p no:cacheprovider`

### 4.3 MTE (fluxo atual)
0. Garantir contexto municipal em `silver.dim_territory` (se ambiente estiver limpo):
   - `python -c "from pipelines.ibge_admin import run; print(run(reference_period='2025', dry_run=False))"`
1. O conector tenta baixar automaticamente via FTP do MTE.
2. Se nao encontrar arquivo via FTP, tenta automaticamente o ultimo artefato tabular valido no Bronze para o mesmo periodo.
3. Se FTP e cache Bronze falharem, usar arquivo manual de Novo CAGED (CSV/TXT/ZIP) em `data/manual/mte`.
4. Executar `labor_mte_fetch`:
   - `dry_run=True` para validar
   - `dry_run=False` para gravar Silver/Bronze/ops
5. Validar criterio P0 (3 execucoes reais consecutivas):
   - `python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json`
6. Resultado mais recente no ambiente local (2026-02-10): `3/3 success` via `bronze_cache`, sem arquivo manual presente durante a validacao.

## 5) Proximos passos recomendados

### Prioridade alta
1. Rodar suite completa em ambiente limpo e consolidar baseline de regressao.
2. Publicar frontend em homologacao integrado a API real.
3. Planejar kickoff da Onda A de novas fontes apos estabilizacao do frontend.

### Prioridade media
1. Consolidar execucao `dbt` CLI em ambiente alvo (profiles, target e permissao de runtime).
2. Entregar telas frontend de saude operacional e pipelines com dados reais.
3. Expandir checks de qualidade por dominio com thresholds por dataset.
4. Entregar tela frontend de territorios/indicadores com filtros por periodo e nivel.

### Prioridade baixa
1. Hardening de observabilidade (SLA por job e alertas).
2. Revisao de politicas de retencao Bronze por ambiente.

## 6) Comandos uteis

- Testes:
  - `pytest -q -p no:cacheprovider`
- Fluxo completo em dry-run:
  - `python -c "from orchestration.prefect_flows import run_mvp_all; print(run_mvp_all(reference_period='2024', dry_run=True))"`
- Sincronizar registry:
  - `python scripts/sync_connector_registry.py`
- Rodar qualidade:
  - `python -c "from pipelines.quality_suite import run; print(run(reference_period='2024', dry_run=False))"`
- Subir API + frontend no Windows sem `make`:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_up.ps1`
- Encerrar API + frontend iniciados pelo launcher:
  - `powershell -ExecutionPolicy Bypass -File scripts/dev_down.ps1`

