# Plano de Execucao do Projeto

Data de referencia: 2026-02-20  
Status: ativo  
Escopo deste arquivo: governanca de execucao, fases, prioridades e sequencia de entrega.

## 1) Referencias e papeis documentais

1. `CONTRATO.md`: requisitos tecnicos e criterios finais de aceite.
2. `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`: visao estrategica (north star) do produto.
3. `docs/PLANO_IMPLEMENTACAO_QG.md`: plano executavel com status por onda/sprint e proximas entregas.
4. `HANDOFF.md`: estado operacional corrente e proximos passos imediatos.
5. `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`: evidenciacao item a item do plano de evolucao.
6. `CHANGELOG.md`: historico de mudancas e evidencias de validacao.
7. `FRONTEND_SPEC.md`: referencia complementar de UX/produto para debate; nao substitui contrato nem plano executavel.
8. `PLANO_FONTES_DADOS_DIAMANTINA.md`: catalogo e priorizacao de fontes; status operacional corrente fica em `HANDOFF.md`.
9. `BACKLOG_DADOS_NIVEL_MAXIMO.md`: backlog tecnico executavel para atingir robustez maxima de base de dados.

Regra: este arquivo nao detalha estado diario; ele define como executar e priorizar.

## 2) Estrategia por ondas (MVP)

MVP-1:
- `ibge_admin_fetch`
- `ibge_geometries_fetch`
- `ibge_indicators_fetch`
- `dbt_build`
- `quality_suite`
- API v1 + observabilidade ops

MVP-2:
- `tse_catalog_discovery`
- `tse_electorate_fetch`
- `tse_results_fetch`

MVP-3:
- `education_inep_fetch`
- `health_datasus_fetch`
- `finance_siconfi_fetch`
- `labor_mte_fetch`

MVP-4:
- `sidra_indicators_fetch`
- `senatran_fleet_fetch`
- `sejusp_public_safety_fetch`
- `siops_health_finance_fetch`
- `snis_sanitation_fetch`

MVP-5:
- `inmet_climate_fetch`
- `inpe_queimadas_fetch`
- `ana_hydrology_fetch`
- `anatel_connectivity_fetch`
- `aneel_energy_fetch`

## 3) Fases de execucao

### Fase 0 - Baseline tecnico
Objetivo:
- garantir ambiente reproduzivel para execucao de ponta a ponta.

Aceite:
1. `python -m pip check` sem conflitos.
2. `python scripts/init_db.py` sem erro em banco limpo.
3. testes unitarios base aprovados.

### Fase 1 - Fechamento funcional critico
Objetivo:
- estabilizar conectores e contrato API essenciais para decisao.

Aceite:
1. conectores MVP-1/2/3 operacionais com rastreio em `ops.pipeline_runs` e `ops.pipeline_checks`.
2. API executiva QG funcional (`overview`, `priorities`, `mapa`, `insights`, `territorio`, `eleitorado`).

### Fase 2 - Fechamento operacional
Objetivo:
- consolidar observabilidade, readiness e qualidade para operacao diaria.

Aceite:
1. `GET /v1/ops/readiness` funcional e consumido no frontend operacional.
2. SLO-3 sem hard fail na janela alvo.
3. pipeline de qualidade com checks por fonte e por referencia_period.

### Fase 3 - Frontend QG robusto
Objetivo:
- transformar o frontend em centro de comando (mapa + decisao).

Aceite:
1. fluxo principal funcional: Home -> Prioridades -> Mapa -> Territorio 360 -> Cenarios/Briefs.
2. estados de loading/error/empty consistentes e com rastreabilidade de erro.
3. testes frontend e build verdes em ciclo de release.

### Fase 4 - Go-live controlado
Objetivo:
- operar em homologacao com defensabilidade tecnica e previsibilidade.

Aceite:
1. E2E dos fluxos criticos aprovado.
2. documentacao de operacao e limites atualizada.
3. release com evidencias em `CHANGELOG.md` + `HANDOFF.md`.

## 4) Prioridades atuais (ordem)

P0:
1. Fechar homologacao ponta a ponta com dados reais.
2. Consolidar baseline de testes (backend + frontend) em ambiente limpo.

P1:
1. Evoluir UX do mapa dominante (Home "B") e performance geoespacial.
2. Fechar E2E dos caminhos de decisao.
3. Padronizar consumo de readiness em toda camada tecnica.

P2:
1. Alertas operacionais e runbooks de suporte.
2. Evolucoes analiticas incrementais por dominio.

## 5) Deltas incorporados do plano de evolucao

Specs estrategicas consolidadas (v1.0):
1. `MAP_PLATFORM_SPEC.md`
2. `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
3. `STRATEGIC_ENGINE_SPEC.md`

Proximo passo: executar backlog tecnico pos-v1 (estabilizacao UX/mapa, robustez de dados e operacao),
com priorizacao em `docs/PLANO_IMPLEMENTACAO_QG.md` e acompanhamento diario em `HANDOFF.md`.

## 6) Riscos principais e mitigacao

1. Instabilidade de fonte externa:
- mitigacao: fallback por catalogo/manual + bronze cache + testes de conector.

2. Divergencia entre visao e execucao:
- mitigacao: governanca documental clara e revisao por contrato.

3. Regressao de UX sob alta cadencia:
- mitigacao: smoke + E2E nos fluxos principais antes de consolidar release.

## 7) Governanca de atualizacao

1. Atualizar `docs/PLANO_IMPLEMENTACAO_QG.md` a cada mudanca de prioridade/status por onda.
2. Atualizar `HANDOFF.md` a cada ciclo de implementacao com estado real e proximos passos.
3. Atualizar `CHANGELOG.md` com evidencias objetivas de validacao.
4. Revisar este `PLANO.md` somente quando houver mudanca de estrategia (nao a cada PR).
