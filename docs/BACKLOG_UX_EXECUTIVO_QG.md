# Backlog UX Executivo QG (ciclo unico)

Data de referencia: 2026-02-20  
Status: proposto para execucao sequencial unica (WIP=1)  
Escopo: consolidar inconsistencias de layout/legibilidade nas telas executivas sem abrir frentes paralelas.

## 1) Objetivo operacional

1. Aumentar legibilidade e hierarquia visual nas telas executivas.
2. Padronizar comportamento de filtros, cards e tabelas.
3. Reduzir densidade cognitiva em listas longas (prioridades, insights, indicadores, evidencias).
4. Tornar estados vazios acionaveis (sempre com proximo passo claro).

## 2) Sequencia unica de execucao

1. Fase A (fundacao visual global): tokens, largura util, header/nav e rhythm de espacamento.
2. Fase B (padrao de interacao): formularios/filtros, botoes, paginacao e estados vazios.
3. Fase DATA (semantica de dados): corrigir scoring mono-territorial, tendencia hardcoded, codigos tecnicos, formatacao de numeros, narrativas e labels.
4. Fase C (ajuste por tela): prioridades, mapa, territorio 360, eleitorado, insights, cenarios, briefs.
5. Fase D (homologacao): QA visual desktop/mobile + regressao frontend/build.

Regra: nao iniciar fase seguinte sem aceite da fase anterior.
Nota: Fase DATA e pre-requisito da Fase C — ajustes visuais por tela so fazem sentido com dados semanticamente corretos.

## 3) Backlog priorizado e mapeado

### P0 (bloqueador de usabilidade executiva)

| ID | Problema | Arquivos/componentes alvo | Implementacao esperada | Criterio de aceite |
|---|---|---|---|---|
| UX-P0-01 | Largura util subaproveitada em desktop grande | `frontend/src/styles/global.css`, `frontend/src/app/App.tsx` | Recalibrar `app-shell`, header e nav para aproveitar viewport sem perder legibilidade. | Em 1440px+ o conteudo principal usa area util maior; navegacao nao fica comprimida. |
| UX-P0-02 | Hierarquia visual fraca entre titulo, subtitulo e conteudo | `frontend/src/styles/global.css`, `frontend/src/shared/ui/Panel.tsx` | Ajustar escala tipografica, espacamentos e contraste de blocos. | Titulos, subtitulos e conteudo secundario ficam claramente distinguiveis em todas as telas. |
| UX-P0-03 | Filtros e botoes com alinhamento inconsistente | `frontend/src/styles/global.css`, `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`, `frontend/src/modules/qg/pages/QgInsightsPage.tsx`, `frontend/src/modules/qg/pages/QgMapPage.tsx`, `frontend/src/modules/qg/pages/QgScenariosPage.tsx`, `frontend/src/modules/qg/pages/QgBriefsPage.tsx`, `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`, `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` | Padronizar `filter-grid`, `filter-actions` e `panel-actions-row` para baseline/altura consistente em desktop e empilhamento previsivel em viewport menor. | Campos e botoes ficam alinhados nas paginas executivas; sem quebra visual em 1280px, 1024px e 768px. |
| UX-P0-04 | Densidade excessiva em cards/listas de Prioridades e Insights | `frontend/src/styles/global.css`, `frontend/src/modules/qg/pages/QgPrioritiesPage.tsx`, `frontend/src/shared/ui/PriorityItemCard.tsx`, `frontend/src/modules/qg/pages/QgInsightsPage.tsx` | Reduzir ruido textual, melhorar distribuicao de card grid e reforcar resumo/paginacao. | Lista fica escaneavel em ate 5 segundos para identificar top itens criticos. |
| UX-P0-05 | Tabelas longas com baixa legibilidade | `frontend/src/styles/global.css`, `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`, `frontend/src/modules/qg/pages/QgBriefsPage.tsx`, `frontend/src/modules/qg/pages/QgMapPage.tsx`, `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx` | Aumentar legibilidade de linhas/cabecalho, espacamento de coluna e leitura de paginacao. | Tabelas mantem leitura clara sem fadiga visual em 100% zoom (desktop). |
| UX-P0-06 | Estados vazios sem CTA acionavel | `frontend/src/modules/electorate/pages/ElectorateExecutivePage.tsx`, `frontend/src/modules/territory/pages/TerritoryProfilePage.tsx`, `frontend/src/modules/qg/pages/QgOverviewPage.tsx`, `frontend/src/modules/qg/pages/QgMapPage.tsx`, `frontend/src/modules/qg/pages/QgInsightsPage.tsx` | Todo `StateBlock tone=\"empty\"` deve sugerir acao objetiva (ex.: limpar filtro, trocar periodo, abrir mapa/perfil). | Nenhum estado vazio termina sem orientar proximo passo. |
| UX-P0-07 | Bloco de Mapa com excesso de controles concorrentes | `frontend/src/modules/qg/pages/QgMapPage.tsx`, `frontend/src/styles/global.css` | Reorganizar toolbar do mapa em grupos claros (filtro/navegacao/render/export/contexto). | Operador encontra a acao principal sem varredura extensa do painel. |

### P0-DATA (semantica de dados — pre-requisito da Fase C)

| ID | Problema | Arquivos/componentes alvo | Implementacao esperada | Criterio de aceite |
|---|---|---|---|---|
| DATA-P0-01 | Score 100 = "critico" em dataset mono-territorial (ranking degenerado) | `src/app/api/routes_qg.py` (`_fetch_priority_rows`, `_fetch_territory_indicator_scores`, `_score_from_rank`) | Quando `total_rows <= 1`, usar score neutro (50.0, status "stable") em vez de 100.0 ("critical"). Evitar que dataset com 1 municipio force tudo para faixa critica. | Com 1 territorio, scores sao 50.0 e status "stable"; com N>1, ranking funciona normalmente. |
| DATA-P0-02 | Tendencia hardcoded "stable" em priority/list | `src/app/api/routes_qg.py` (`get_priority_list`) | Calcular tendencia real comparando valor atual com periodo anterior via `_previous_reference_period`. Se nao houver dado anterior, manter "stable" explicitamente. | Tendencia reflete variacao real quando ha dados de dois periodos. |
| DATA-P0-03 | Codigos tecnicos expostos ao executivo (DCA_P1_0_0_0_0_00_00) | `src/app/api/routes_qg.py` (rationale, explanation, highlights) | Usar `indicator_name` em vez de `indicator_code` em todas as narrativas voltadas ao usuario. Manter `indicator_code` apenas em campos structured (evidence). | Nenhuma narrativa/rationale/highlight exibe indicator_code bruto. |
| DATA-P0-04 | Numeros grandes sem formatacao nos highlights (603869614.81) | `src/app/api/routes_qg.py` (`get_territory_profile` highlights) | Formatar valores nos highlights com separador de milhar e unidade quando disponivel. | Highlights mostram valores formatados (ex: "R$ 603.869.614,81" ou "603.869.614,81 BRL"). |
| DATA-P0-05 | Filtro de severidade com labels em ingles | `frontend/src/modules/qg/pages/QgInsightsPage.tsx` | Usar `formatStatusLabel()` nas options do select de severidade. | Dropdown mostra "Critico", "Atencao", "Informativo". |
| DATA-P0-06 | Narrativa de insights formulaica e repetitiva | `src/app/api/routes_qg.py` (`get_insight_highlights`) | Diversificar template de narrativa com contexto de dominio, unidade e referencia ao territorio. | Textos de insight proveem contexto diferenciado por dominio/indicador. |
| DATA-P0-07 | Jargao tecnico nos controles do mapa (SVG fallback, Renderizacao) | `frontend/src/modules/qg/pages/QgMapPage.tsx` | Renomear labels para linguagem executiva: "Modo avancado" / "Modo simplificado", ocultar toggle de renderizacao quando desnecessario. | Labels do mapa sao compreensiveis por usuario nao-tecnico. |
| DATA-P0-08 | Duplicacao de logica de formatacao de status/trend | `frontend/src/shared/ui/StrategicIndexCard.tsx` | Usar `formatStatusLabel()` e `formatTrendLabel()` de `presentation.ts` em vez de funcoes locais. | Formatacao centralizada em um unico modulo. |

### P1 (ganho relevante apos estabilidade)

| ID | Problema | Arquivos/componentes alvo | Implementacao esperada | Criterio de aceite |
|---|---|---|---|---|
| UX-P1-01 | Inconsistencia de escala entre telas (Eleitorado x Territorio 360 x Insights) | `frontend/src/styles/global.css` | Definir matriz de escala unica para fonte, espacamento e densidade por tipo de bloco. | Transicao entre telas sem salto perceptivel de escala. |
| UX-P1-02 | Cards KPI com peso visual muito parecido entre status | `frontend/src/styles/global.css`, `frontend/src/shared/ui/StrategicIndexCard.tsx` | Reforcar contraste semantico para `critical/attention/stable/info` mantendo acessibilidade. | Status critico chama atencao imediata sem depender de leitura textual detalhada. |
| UX-P1-03 | Metadados de fonte extensos e pouco escaneaveis | `frontend/src/styles/global.css`, `frontend/src/shared/ui/SourceFreshnessBadge.tsx` | Melhorar quebra de linha, agrupamento e prioridade visual dos metadados. | Badge de fonte permanece legivel sem overflow em desktop e tablet. |
| UX-P1-04 | Header global com pouca orientacao contextual | `frontend/src/app/App.tsx`, `frontend/src/styles/global.css` | Reforcar relacao entre titulo, rota ativa e contexto municipal/API. | Contexto da pagina e do ambiente fica evidente no primeiro olhar. |

### P2 (refinamento)

| ID | Problema | Arquivos/componentes alvo | Implementacao esperada | Criterio de aceite |
|---|---|---|---|---|
| UX-P2-01 | Micro-copy inconsistente entre telas executivas | `frontend/src/modules/qg/pages/*.tsx`, `frontend/src/modules/territory/pages/*.tsx`, `frontend/src/modules/electorate/pages/*.tsx` | Harmonizar textos de apoio, mensagens de erro e rotulos de acao com tom unico executivo. | Mensagens convergem para padrao unico e objetivo. |
| UX-P2-02 | Falta de sinais de leitura progressiva para blocos longos | `frontend/src/styles/global.css`, telas com `trend-list` e `table-wrap` | Aplicar refinamentos de separadores, ritmo vertical e pontos de ancoragem visual. | Leitura de blocos extensos fica mais fluida e previsivel. |

## 4) Plano de entrega em ciclo unico

1. Entrega 1 (P0 estrutural): UX-P0-01, UX-P0-02, UX-P0-03.
2. Entrega 2 (P0 de densidade): UX-P0-04, UX-P0-05.
3. Entrega 3 (P0 contextual): UX-P0-06, UX-P0-07.
4. Entrega DATA (semantica): DATA-P0-01 a DATA-P0-08 (backend + frontend).
5. Entrega 5 (P1/P2): somente apos validacao completa de P0 + DATA.

## 5) Validacao obrigatoria por entrega

1. `npm --prefix frontend run test -- --run src/modules/qg/pages/QgPages.test.tsx`
2. `npm --prefix frontend run test -- --run src/modules/territory/pages/TerritoryProfilePage.test.tsx src/modules/electorate/pages/ElectorateExecutivePage.test.tsx src/modules/ops/pages/OpsPages.test.tsx`
3. `npm --prefix frontend run test -- --run`
4. `npm --prefix frontend run build`
5. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_qg_routes.py -q` (para entrega DATA)
6. `.\.venv\Scripts\python.exe -m pytest tests/unit/ -q` (regressao completa backend)

## 6) Checklist de aceite visual (manual)

1. Desktop 1440px: sem bloco central subutilizado, sem compressao de nav e filtros.
2. Desktop 1280px: filtros e botoes alinhados, sem quebra abrupta.
3. Tablet 1024px: stacks previsiveis, sem sobreposicao.
4. Mobile 768px: leitura vertical continua, sem overflow horizontal.
5. Estados `loading/error/empty/data` legiveis em Prioridades, Mapa, Territorio 360, Insights, Cenarios, Briefs e Eleitorado.
