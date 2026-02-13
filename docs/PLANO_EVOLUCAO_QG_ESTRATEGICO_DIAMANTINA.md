# PLANO DE EVOLUCAO - QG ESTRATEGICO (Diamantina/MG)
Versao: 1.1.0  
Data de referencia: 2026-02-13  
Papel deste arquivo: visao estrategica (north star).  
Fonte de execucao: `docs/PLANO_IMPLEMENTACAO_QG.md`.  
Estado operacional corrente: `HANDOFF.md`.

## 1) Objetivo de produto

Construir um QG estrategico municipal local-first, com mapa dominante, leitura executiva e
motor de decisao (prioridades, insights, cenarios e briefs), focado em Diamantina/MG e distritos.

## 2) Principios nao negociaveis

1. Frontend orientado a decisao (nao apenas dashboard).
2. Mapa como elemento principal da experiencia.
3. Separacao entre camada executiva e camada tecnica (`/admin`).
4. Dados eleitorais apenas agregados; sem dado individualizado.
5. Transparencia de "oficial vs proxy" para camadas derivadas.
6. Desenvolvimento orientado a especificacao e rastreabilidade.
7. Operacao local reproduzivel, sem dependencia obrigatoria de cloud.

## 3) Arquitetura alvo (resumo)

1. Dados em Bronze/Silver/Gold + camada Ops.
2. Postgres + PostGIS com otimizacoes geoespaciais por nivel de zoom.
3. API FastAPI com contratos estaveis e orientados a UI.
4. Frontend React/TypeScript com mapa vetorial e cache de consulta.

## 4) Ondas estrategicas (ordem de valor)

1. Onda 0: fundamentos de operacao local e reprodutibilidade.
2. Onda 1: territorio oficial e base geoespacial.
3. Onda 2: camada eleitoral agregada e participacao.
4. Onda 3: servicos publicos e infraestrutura.
5. Onda 4: motor estrategico explicavel.
6. Onda 5: plataforma de mapa multi-zoom com camadas.
7. Onda 6: UX imersiva orientada por decisao.
8. Onda 7: cenarios e briefs executivos.
9. Onda 8: hardening, QA e defensabilidade.

Nota: status detalhado de cada onda (done/in progress/backlog) fica em
`docs/PLANO_IMPLEMENTACAO_QG.md`.

## 5) Criterios de sucesso do produto

1. Decisor identifica hotspots e prioridades sem navegacao extensa.
2. Navegacao de mapa e filtros funciona com fluidez e consistencia.
3. Prioridades/insights sao explicaveis e auditaveis por evidencia.
4. Integracao territorial cobre administrativo, eleitoral e servicos.
5. Sistema e defensavel tecnicamente (fontes, cobertura, limites, proxies).

## 6) Deltas estrategicos ainda pendentes de especificacao

1. `MAP_PLATFORM_SPEC.md` (tiles, zoom, cache, metas de performance).
2. `TERRITORIAL_LAYERS_SPEC_DIAMANTINA.md` (camadas oficiais/proxy e regras eticas).
3. `STRATEGIC_ENGINE_SPEC.md` (normalizacao, pesos, severidade, thresholds e explicabilidade).

Esses deltas devem ser planejados e executados via `docs/PLANO_IMPLEMENTACAO_QG.md`.

## 7) Regra de governanca documental

1. Se houver conflito entre visao e execucao, prevalece:
   - `CONTRATO.md` para regra tecnica/aceite.
   - `docs/PLANO_IMPLEMENTACAO_QG.md` para priorizacao e sequencia.
   - `HANDOFF.md` para estado atual e proximos passos.
2. Este arquivo nao deve concentrar status operacional diario.
