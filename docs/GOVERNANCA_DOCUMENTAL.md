# Governanca Documental (Fonte Oficial)

Data de referencia: 2026-02-20  
Status: ativo

## 1) Objetivo

Reduzir dispersao e garantir trilha unica de execucao documental.

## 2) Hierarquia de verdade

1. `docs/CONTRATO.md` (requisitos tecnicos obrigatorios)
2. `docs/VISION.md` (north star de produto)
3. `docs/PLANO_IMPLEMENTACAO_QG.md` (fila unica executavel)
4. `docs/HANDOFF.md` (estado da trilha ativa)
5. `docs/CHANGELOG.md` (evidencia historica)

## 3) Nucleo ativo (leitura obrigatoria)

1. `docs/CONTRATO.md`
2. `docs/VISION.md`
3. `docs/PLANO_IMPLEMENTACAO_QG.md`
4. `docs/HANDOFF.md`
5. `docs/CHANGELOG.md`

## 4) Ativo por dominio

1. `docs/MAP_PLATFORM_SPEC.md`
2. `docs/TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md`
3. `docs/STRATEGIC_ENGINE_SPEC.md`
4. `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`
5. `docs/OPERATIONS_RUNBOOK.md`

## 5) Complementar (nao executavel)

1. nenhum documento complementar ativo no momento

## 6) Descontinuados (removidos do repositorio)

Arquivos removidos em 2026-02-20:
1. `FRONTEND_SPEC.md`
2. `PLANO_EVOLUCAO_QG_ESTRATEGICO_DIAMANTINA.md`
3. `MATRIZ_RASTREABILIDADE_EVOLUCAO_QG.md`
4. `GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md`
5. `PLANO_FONTES_DADOS_DIAMANTINA.md`
6. `RUNBOOK_ROBUSTEZ_DADOS_SEMANAL.md`
7. `MTE_RUNBOOK.md`
8. `BRONZE_POLICY.md`
9. `BACKLOG_UX_EXECUTIVO_QG.md`
10. `PLANO.md`

Consolidacoes oficiais:
1. fontes e priorizacao -> `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`
2. runbooks operacionais -> `docs/OPERATIONS_RUNBOOK.md`
3. politica Bronze -> `docs/CONTRATO.md` (secao `4.1`)

## 7) Regras obrigatorias

1. Documento descontinuado nao abre backlog nem prioridade.
2. Somente `docs/PLANO_IMPLEMENTACAO_QG.md` define ordem da trilha ativa.
3. `docs/HANDOFF.md` so registra estado corrente e proximo passo.
4. Toda rodada concluida deve atualizar `docs/CHANGELOG.md` e `docs/HANDOFF.md`.
5. `docs/VISION.md` deve existir como unico north star e permanecer enxuto (produto, nao backlog).
