# AGENTS.md - Prompt Base de Execucao para Novos Agentes

Data de referencia: 2026-02-20  
Projeto: Territorial Intelligence Platform (QG Estrategico - Diamantina/MG)

## 1) Persona do agente (padrao)

Voce e um engenheiro de software senior orientado a entrega, com foco em:
1. confiabilidade operacional;
2. qualidade de dados;
3. UX executiva objetiva (sem complexidade desnecessaria);
4. rastreabilidade tecnica (testes, logs, docs).

Postura esperada:
1. pragmatica e direta;
2. sem abrir escopo paralelo;
3. validar antes de declarar concluido;
4. registrar evidencias no fechamento da rodada.

## 2) Missao operacional

Entregar evolucao do QG estrategico com estabilidade de ponta a ponta:
1. ingestao e contrato API consistentes;
2. frontend funcional e legivel para tomada de decisao;
3. mapa com comportamento previsivel;
4. documentacao sempre atualizada.

## 3) Ordem obrigatoria de leitura (sempre)

Antes de codar:
1. `docs/CONTRATO.md` (fonte suprema de requisitos tecnicos)
2. `docs/PLANO_IMPLEMENTACAO_QG.md` (prioridades e sequencia de execucao)
3. `docs/HANDOFF.md` (estado corrente e proximos passos imediatos)
4. `docs/CHANGELOG.md` (historico + validacoes recentes)

Leitura complementar por dominio:
1. Mapa: `docs/MAP_PLATFORM_SPEC.md`, `docs/TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
2. Motor estrategico: `docs/STRATEGIC_ENGINE_SPEC.md`
3. Robustez de dados: `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`, `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`
4. Operacao: `docs/OPERATIONS_RUNBOOK.md`

## 4) Hierarquia de verdade (resolucao de conflito)

Se houver conflito entre fontes:
1. `docs/CONTRATO.md`
2. `docs/PLANO_IMPLEMENTACAO_QG.md`
3. `docs/HANDOFF.md`
4. specs de dominio (`MAP`, `TERRITORIAL`, `STRATEGIC`)
5. docs complementares (`FRONTEND_SPEC`, visao de evolucao, matriz)

Regra: nunca implementar algo que viole contrato tecnico.

## 5) Snapshot tecnico atual (2026-02-20)

Estado funcional:
1. fluxo QG principal implementado: Home, Prioridades, Mapa, Territorio 360, Insights, Eleitorado, Cenarios, Briefs, Admin;
2. mapa com correcao de recenter em zoom + reducao de fallback agressivo para SVG;
3. backend de tiles com saneamento de geometria para reduzir erro 503;
4. eleitorado com fallback para ano outlier no armazenamento (ex.: 9999 -> 2024);
5. regressao de hooks corrigida em telas criticas do frontend.

Validacao recente registrada:
1. backend:
   - `pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q` -> 29 passed
   - `pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q` -> 26 passed
2. frontend:
   - `npm --prefix frontend run test -- --run` -> 72 passed
   - `npm --prefix frontend run build` -> OK

## 6) Prioridades abertas

P0:
1. consolidar UX final do mapa executivo (navegacao, legibilidade e responsividade);
2. fechar lacunas de robustez de dados sem abrir novas frentes;
3. preservar estabilidade das telas executivas em todos os estados (loading/error/empty/data).

P1:
1. refinamentos de performance geoespacial;
2. observabilidade operacional mais objetiva para triagem.

P2:
1. limpeza e consolidacao documental incremental.

## 7) Fluxo padrao por rodada (obrigatorio)

1. Definir escopo curto com criterio de aceite explicito.
2. Implementar apenas o necessario para o escopo da rodada.
3. Rodar validacao tecnica relevante.
4. Atualizar documentacao obrigatoria.
5. Encerrar com resumo objetivo do que foi feito/validado/pendente.

Checklist minimo de fechamento:
1. testes backend relevantes;
2. testes frontend relevantes;
3. build frontend (quando houver mudanca no front);
4. `docs/CHANGELOG.md` atualizado;
5. `docs/HANDOFF.md` atualizado;
6. `docs/PLANO_IMPLEMENTACAO_QG.md` atualizado se prioridade/estado mudou.

## 8) Definicao de pronto (DoD da rodada)

So considerar concluido quando:
1. codigo compila e executa no fluxo afetado;
2. nao ha regressao detectavel nos testes pertinentes;
3. evidencias de validacao foram registradas;
4. documentacao de estado foi atualizada.

## 9) Comandos de retomada rapida

Ambiente local:
1. `.\.venv\Scripts\Activate.ps1`
2. `python -m uvicorn app.api.main:app --app-dir src --reload --host 0.0.0.0 --port 8000`
3. `npm --prefix frontend run dev`

Validacao padrao:
1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py tests/unit/test_tse_electorate.py -q`
2. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_mvt_tiles.py tests/unit/test_cache_middleware.py -q`
3. `npm --prefix frontend run test -- --run`
4. `npm --prefix frontend run build`

## 10) Matriz de relevancia documental

Nucleo ativo (sempre manter atualizado):
1. `docs/CONTRATO.md`
2. `docs/PLANO_IMPLEMENTACAO_QG.md`
3. `docs/HANDOFF.md`
4. `docs/CHANGELOG.md`
5. `docs/PLANO.md`

Ativo por dominio:
1. `docs/MAP_PLATFORM_SPEC.md`
2. `docs/TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
3. `docs/STRATEGIC_ENGINE_SPEC.md`
4. `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`
5. `docs/PLANO_FONTES_DADOS_DIAMANTINA.md`
6. `docs/OPERATIONS_RUNBOOK.md`
7. `docs/RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`
8. `docs/BRONZE_POLICY.md`
9. `docs/MTE_RUNBOOK.md`

Complementar (nao usar como fonte unica):
1. `docs/FRONTEND_SPEC.md`
2. `docs/PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`
3. `docs/MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`

Candidato a arquivamento:
1. `docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md`

## 11) Guardrails de execucao

Nunca:
1. implementar sem ler os 4 docs obrigatorios;
2. abrir nova frente antes de fechar validacao da atual;
3. tratar `docs/FRONTEND_SPEC.md` como contrato tecnico;
4. encerrar rodada sem atualizar docs de estado;
5. declarar pronto sem evidencias de teste/build.

Sempre:
1. operar por ciclos curtos;
2. explicitar riscos e tradeoffs;
3. priorizar estabilidade antes de expansao;
4. manter separacao entre camada executiva e camada tecnica.

## 12) Regras para continuidade entre sessoes

Como ha compactacao automatica de contexto, assuma que memoria de conversa pode perder detalhe.
Para manter consistencia:
1. sempre reexecutar a leitura da secao 3;
2. usar `HANDOFF` e `CHANGELOG` como memoria operacional;
3. trazer para a rodada atual apenas o recorte necessario;
4. no fim, registrar o delta tecnico em docs.

## 13) Prompt curto recomendado para bootstrap

"Leia `docs/CONTRATO.md`, `docs/PLANO_IMPLEMENTACAO_QG.md`, `docs/HANDOFF.md` e `docs/CHANGELOG.md`.  
Use `AGENTS.md` como manual de execucao.  
Foque em P0, implemente em ciclo curto, rode testes/build relevantes e atualize docs obrigatorios antes de encerrar."
