# FRONTEND SPEC (QG ESTRATÉGICO) — AGENT-READY
Plataforma de Inteligência Territorial – Diamantina/MG (Município + Distritos + Eleitorado)

Versão: 2.0.0  
Status: Ativo (Contrato de Produto + Implementação Frontend)  
Data: 2026-02-11  

Base: Este documento substitui e amplia a versão anterior do FRONTEND_SPEC, elevando o frontend de “painel analítico” para “QG Estratégico Municipal”.

---

## 1) Objetivo do Frontend (QG Estratégico)

O frontend é o protagonista e deve operar como um **Centro de Comando Estratégico Municipal (QG)**, para apoiar decisões de prefeito/secretário/gestor com:

- **Diagnóstico** (o que está acontecendo)
- **Priorização** (o que fazer primeiro)
- **Antecipação** (o que tende a piorar / virar crise)
- **Alocação** (onde agir e com qual foco)
- **Governabilidade** (cidadania/eleitorado e participação como contexto institucional)

O sistema deve ser **visual, simples e interpretável** (estilo Power BI): mostrar o essencial, com narrativa e contexto, sem termos técnicos.

---

## 2) Público-alvo (personas)

### Persona Primária — Prefeito / Secretário / Gestor Estratégico
- Quer respostas em <60s: “qual o estado da cidade”, “o que piorou”, “onde agir primeiro”.
- Quer uma lista clara de prioridades, com justificativa e evidência.
- Quer comparar territórios e acompanhar tendências.

### Persona Secundária — Analista de Planejamento
- Explora, faz drill-down, exporta e gera notas técnicas e relatórios.
- Trabalha com séries históricas e comparações.

### Persona Técnica (Admin) — Engenheiro/Operador de Dados
- Acessa apenas /admin (runs/checks/conectores) para manutenção e troubleshooting.
- Não participa do fluxo principal do QG.

---

## 3) Princípios (não-negociáveis)

P1. Cada tela deve responder a uma pergunta de decisão (não “mostrar dado”).  
P2. “Menos é mais”: 5–8 sinais essenciais por tela; a Home deve ser lida em <60s.  
P3. Sempre mostrar contexto: tendência + comparação + metadados (fonte/atualização/cobertura).  
P4. O QG deve **orientar** endpoints: prioridades, alertas e destaques vêm do backend.  
P5. O frontend **não calcula** regras críticas: prioridades, rankings, pares e alertas devem vir prontos da API.  
P6. Mapa é central, mas funcional: legenda clara, tooltip rico, drill-down consistente.  
P7. Linguagem não técnica no produto principal; operação técnica só em /admin.  
P8. Neutralidade institucional na camada eleitoral (perfil/participação), sem recomendações de persuasão/campanha.  
P9. Transparência: toda prioridade/alerta deve ter “por quê” (explicabilidade + evidência).

---

## 4) Conceito do QG: Camadas Estratégicas

O QG é composto por quatro camadas de valor, em ordem:

1. **Situação Geral**: estado da cidade (índices e tendências).
2. **Prioridades**: ranking das ações/territórios/domínios mais críticos.
3. **Mapa/Distribuição**: onde está o problema e como ele se espalha.
4. **Território 360 + Evidências**: histórico, comparação, dados de suporte e export.

---

## 5) Estrutura de navegação (rotas) — mínimo do QG

Rotas obrigatórias:
- `/` — QG / Situação Geral (Home)
- `/prioridades` — Lista estratégica (o que fazer primeiro)
- `/mapa` — Mapa territorial (onde agir)
- `/territorio/:territory_id` — Perfil 360 (diagnóstico profundo)
- `/insights` — Motor de insights (destaques explicáveis)
- `/cenarios` — Cenários (simulações simples e “e se”)
- `/eleitorado` — Cidadania & Participação (contexto institucional)
- `/admin` — Operação de dados (restrito, fora do fluxo principal)

Menu principal (top/lateral):
- QG (Home)
- Prioridades
- Mapa
- Territórios
- Insights
- Cenários
- Eleitorado & Participação
- (Opcional) Metodologia / Fontes
- (Restrito) Admin

Filtros globais persistentes (sempre visíveis):
- Período (ano / intervalo)
- Domínio (Saúde, Educação, Trabalho, Finanças, Assistência, Eleitorado/Participação)
- Nível territorial (município / distrito / zona / seção quando disponível)
- Território selecionado (quando aplicável)

---

## 6) Telas do QG (escopo funcional)

### 6.1 Home — QG / Situação Geral
Pergunta: “Como está a cidade agora? O que mudou? O que exige decisão imediata?”

Componentes obrigatórios:
1. **Faixa de Situação Geral**
   - Índice Estratégico Global (0–100) + tendência (↑ ↓ →)
   - Risco sistêmico (Baixo / Médio / Alto)
   - Frescor dos dados (última atualização geral)

2. **KPIs Executivos (4–8)**
   - agrupados por domínio
   - valor atual + variação vs período anterior
   - status (Estável / Atenção / Crítico) — fornecido pela API

3. **Top Prioridades (prévia)**
   - Top 5 itens (território + domínio + criticidade)
   - cada item deve ter: “por que está aqui” (2–3 bullets) + link “ver detalhes”

4. **Destaques (storytelling)**
   - Top 3 pioras relevantes
   - Top 3 melhorias relevantes (se existir)
   - Top 3 territórios em aceleração negativa (tendência persistente)

Ações rápidas:
- “Abrir Prioridades”
- “Ver no Mapa” (já com indicador e nível)
- “Abrir Perfil do território mais crítico”

Regras:
- Sem tabelas longas.
- Todo alerta/prioridade deve ter explicação e evidência (tooltip/modal).

### 6.2 Prioridades — Lista Estratégica
Pergunta: “O que fazer primeiro e onde?”

Componentes obrigatórios:
- Lista ranqueada (Top N) com:
  - território (nível e nome)
  - domínio
  - score de criticidade (0–100)
  - tendência (piora/melhora/estável)
  - justificativa curta (2–4 bullets)
  - evidências (links para indicadores e séries no Perfil 360)
  - recomendação institucional (texto neutro do tipo “área crítica exige atenção”)

Filtros:
- domínio
- nível territorial
- “somente críticos”
- período
- ordenar por: criticidade | tendência | impacto estimado (se existir)

Ações:
- “Ver no mapa” (aplica o recorte)
- “Abrir perfil”
- “Exportar lista” (CSV/PDF simples)

Observação:
- A recomendação deve ser neutra e baseada em regras públicas do backend (sem linguagem partidária).

### 6.3 Mapa Territorial
Pergunta: “Onde está o problema e como ele se distribui?”

Requisitos:
- Mapa coroplético por indicador/período/nível territorial.
- Legenda obrigatória (escala + unidade + método de corte: quantis/intervalos).
- Tooltip rico:
  - território
  - valor
  - variação vs período anterior
  - status (Estável/Atenção/Crítico)
  - fonte + atualização + cobertura
- Clique seleciona território e abre drawer com:
  - resumo (2–3 KPIs do domínio)
  - tendência curta
  - links: Perfil 360 / Comparar / Adicionar à “pasta” (Brief)
- Hotspots (opcional, recomendado):
  - lista lateral “Territórios críticos neste indicador” sincronizada com o mapa

Ações:
- trocar indicador, período, nível
- exportar recorte (CSV) e imagem (PNG)

Restrições:
- no máximo 1 camada temática ativa + limites administrativos.
- geometria deve ser simplificada por nível (backend fornece).

### 6.4 Perfil 360 do Território
Pergunta: “O que está acontecendo aqui, por quê e como evolui?”

Estrutura mínima:
- Header:
  - nome, nível, metadados (fonte/atualização/cobertura)
  - população/eleitorado (quando disponível)
  - “status geral do território” (score + tendência)

- Seções por domínio (cards + mini charts):
  - Saúde
  - Educação
  - Trabalho/Economia
  - Assistência/Vulnerabilidade
  - Finanças (quando fizer sentido)
  - Cidadania/Eleitorado

Cada seção:
- 1 KPI principal + variação
- sparkline (série temporal)
- link “ver evidências” (abre modal com gráficos + tabela curta + fonte)

Comparação:
- dropdown “comparar com” + “pares” (definidos pela API)
- gráfico padrão: barras lado a lado + delta
- texto curto: “acima/abaixo da referência”

Export:
- “Gerar Brief do território” (PDF/HTML simples — ver seção 6.7)

### 6.5 Insights — Motor de Insights
Pergunta: “O que eu preciso saber sem procurar?”

Conteúdo:
- cards de insight (máx. 10 por período/filtro)
- cada insight deve conter:
  - título curto
  - severidade (info/atenção/crítico)
  - território(s) afetado(s)
  - domínio
  - explicação (2–4 bullets)
  - evidências (links para mapa/perfil/indicadores)
  - “robustez do insight” (alta/média/baixa) baseado em cobertura e consistência

Filtros:
- domínio, severidade, nível, período

Regra:
- insights devem ser gerados pelo backend; frontend apenas exibe e navega.

### 6.6 Cenários — Simulação simples (“e se”)
Pergunta: “Se mudarmos X, o que acontece com as prioridades?”

Modelo (sem ML; regras e sensibilidade):
- Selecionar:
  - território
  - domínio/indicador
  - ajuste (ex: +5%, -10%)
- Mostrar:
  - efeito no score do território
  - efeito no ranking de prioridades (antes/depois)
  - notas de limitação (ex: “simulação simplificada”)

Regra:
- cálculo deve vir do backend para consistência; frontend só controla inputs e visualiza resultados.

### 6.7 Briefs (opcional recomendado) — “Pasta de decisão”
Objetivo: permitir ao gestor salvar e exportar uma seleção de evidências para reunião.

Funcionalidade:
- usuário marca:
  - territórios
  - prioridades
  - mapas (indicador/período)
  - gráficos do perfil
- gera um “Brief” com:
  - resumo executivo
  - evidências (cards e gráficos)
  - fontes e datas
- exportar: PDF/HTML

### 6.8 Eleitorado & Participação
Pergunta: “Como está a participação cívica e o perfil do eleitorado por território?”

Conteúdos (agregados e institucionais):
- eleitorado total por território
- perfil do eleitorado (idade/sexo/escolaridade)
- participação: comparecimento/abstenção, brancos/nulos (por território e no tempo)
- mapas: eleitorado, % jovens, % idosos, abstenção, brancos/nulos
- storytelling: envelhecimento, hotspots de abstenção persistente, concentração de jovens

### 6.9 Admin 
Fora do fluxo principal, apenas para operação técnica.

---

## 7) Componentes padrão (design system)

Obrigatórios:
- Strategic Index Card (0–100) + tendência + status
- KPI Card (valor, unidade, delta, status, tooltip metodologia)
- Priority Item (score, tendência, “por quê”, links de evidência)
- Insight Card (severidade, explicação, evidências, robustez)
- Trend MiniChart (sparkline)
- Choropleth Map Container (legenda, tooltip, drawer, hotspots, loading)
- Comparison Panel (lado a lado + delta + referência)
- Data Table (paginada, download CSV)
- Source & Freshness Badge (sempre presente)
- Empty/Loading/Error states (mensagens não técnicas)

Direção visual:
- legibilidade alta, hierarquia forte, espaçamento consistente
- codificação visual consistente por domínio
- acessibilidade (contraste, foco, labels, teclado)
- evitar “overdesign”; priorizar clareza executiva

---

## 8) Contrato de dados (frontend ↔ API)

Regra central:
- O frontend NÃO calcula regras críticas (prioridades, alertas, pares, rankings, cenários).
- O backend fornece valores + derivados + narrativa/justificativa (curta e neutra).

Metadados obrigatórios em todas as respostas:
- source_name
- updated_at
- coverage_note
- unit
- notes (curtas)

Endpoints mínimos esperados (exemplos):
- GET /v1/territories?level=&parent_id=
- GET /v1/territories/{id}
- GET /v1/kpis/overview?period=
- GET /v1/priority/list?period=&level=&domain=&limit=
- GET /v1/priority/summary?period=
- GET /v1/geo/choropleth?metric=&period=&level=
- GET /v1/territory/{id}/profile?period=
- GET /v1/territory/{id}/compare?with_id=&period=
- GET /v1/insights/highlights?period=&domain=&severity=&limit=
- POST /v1/scenarios/simulate
- GET /v1/electorate/summary?level=&period=&breakdown=
- GET /v1/electorate/map?metric=&period=&level=
- (Opcional) POST /v1/briefs

Cache:
- mapa/perfil/prioridades/insights devem ser cacheáveis por (period, domain, level, metric).
- frontend usa cache local (React Query) para navegação fluida.

---

## 9) Requisitos não funcionais

### 9.1 Performance
- Home: <2s em máquina local média (cache quente)
- Prioridades: <2s (cache quente)
- Mapa: <3s para render inicial (cache quente)
- evitar payloads enormes com geometria simplificada por nível (backend)
- paginação em tabelas
- sempre exibir loading, nunca “congelar”

### 9.2 Acessibilidade
- teclado, foco visível, contraste, labels
- tooltips acessíveis (não só hover)
- responsivo mínimo (tablet)

### 9.3 Local-first
- rodar localmente com um clique (launcher) e abrir no navegador
- sem dependência externa para funcionar (mapa base deve ter fallback)

### 9.4 Segurança mínima
- /admin protegido (basic auth ou token local)
- sanitização de parâmetros
- erro amigável para usuário final; logs técnicos separados

---

## 10) Fases de implementação (prioridade do QG)

Fase A (QG mínimo viável — alto impacto)
1. Home com KPIs + Top Prioridades + Destaques
2. Prioridades (lista completa) via /v1/priority/list
3. Mapa coroplético com tooltip + drawer via /v1/geo/choropleth
4. Metadados (fonte/atualização/cobertura) em todas as telas

Fase B (QG completo — decisão)
1. Perfil 360 com comparações e evidências
2. Insights (highlights) via /v1/insights/highlights
3. Eleitorado & Participação (camada institucional)

Fase C (antecipação e hardening)
1. Cenários (simulação simples) via /v1/scenarios/simulate
2. E2E dos fluxos críticos
3. Observabilidade de frontend + acessibilidade + responsividade
4. (Opcional) Briefs e export PDF/HTML

---

## 11) Critérios de aceitação (Definition of Done)

O frontend é considerado “QG Estratégico” quando:
1. Home responde “estado da cidade + principais prioridades” em <60s.
2. Prioridades apresenta ranking explicável, com evidências e filtros.
3. Mapa permite localizar gargalos com leitura clara (legenda + tooltip + drawer).
4. Perfil 360 explica território com histórico, comparação e evidências.
5. Insights traz “o que importa” sem o usuário procurar (com evidências).
6. Cenários permite simulação simples (antes/depois) e altera visão de prioridade.
7. Eleitorado & participação existe como camada institucional neutra.
8. Metadados (fonte/atualização/cobertura) aparecem em todas as telas.
9. /admin existe e é separado/oculto do usuário decisor.
10. Build local abre sem terminal (launcher) e fluxos críticos passam em E2E.

