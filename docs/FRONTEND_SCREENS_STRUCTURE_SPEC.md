# FRONTEND_SCREENS_STRUCTURE_SPEC — QG Estratégico (Diamantina/MG)
Versão: 1.0.0  
Objetivo: definir a **estrutura completa das telas** (front-end) do QG Estratégico (Layout B: mapa dominante), com navegação, componentes, estados, ações e contratos (UI ↔ API).  
Público-alvo: Prefeito / Secretário (execução e decisão).  
Princípio: **percepção imediata** + **território vivo** + **storytelling** + simplicidade (PowerBI-like), sem tecnicismo exposto.

---

## 0) Diretrizes globais (não-negociáveis)
- O mapa é **protagonista**. A Home deve abrir com **leitura pronta** (não exige configurar filtros).
- UI é **executiva e institucional**: minimalista, clara, alta legibilidade, sem poluição visual.
- Navegação deve ser curta: 5–7 itens no máximo.
- Sempre mostrar **Fonte + Data de atualização + Cobertura** (metadados) em todo card/indicador.
- Sem dados individualizados (somente agregados).
- Fallbacks: se uma camada não existir (ex.: bairros oficiais), usar proxy e marcar como “Derivado/Estimado”.

---

## 1) Navegação e layout base

### 1.1 Layout Base (AppShell)
Estrutura:
- `TopBar` (fixo)
- `LeftNav` (colapsável em telas menores)
- `MainContent`

### 1.2 TopBar (global)
Elementos:
- Nome do sistema + contexto (“Diamantina/MG”)
- Seletor de Período (ano/eleição/censo)
- Seletor de Domínio (Geral, Educação, Saúde, Eleitoral, etc.)
- Seletor de Nível territorial (Distrito, Bairro, Setor, Zona, Seção)
- Busca global (“buscar território / serviço / zona / seção”)
- Botão “Camadas” (abre LayerPanel)
- Badge de “Frescor” (data da última atualização do dataset)

Estados globais:
- `selectedPeriod`
- `selectedDomain`
- `selectedTerritoryLevel`
- `globalSearchQuery`
- `layerPanelOpen`

---

## 2) Telas do sistema (estrutura completa)

### 2.1 HOME — “QG” (Layout B obrigatório)
Rota: `/`

Objetivo: em 5–10s, o usuário deve ver:
- onde está o problema (hotspots)
- quais são as prioridades (Top 3/5)
- por que (evidências)
- como explorar (mapa + clique → drawer)

#### 2.1.1 Composição da tela
**A) Painel Estratégico Lateral (30%)**
1) Índice Estratégico Municipal (0–100)
   - status: Estável / Atenção / Crítico
   - tendência: melhora / piora / estável
   - metadados: fonte + data

2) Top 3/5 Prioridades (cards compactos)
   Cada card:
   - território (nome)
   - domínio (educação/saúde/eleitoral)
   - score (0–100)
   - tendência
   - 2–4 bullets “Por quê”
   - CTA: “Ver no mapa” + “Perfil 360”

3) Destaques (3 bullets)
   - frase curta, orientada à decisão (storytelling)

**B) Mapa Estratégico Dominante (70%)**
- já abre com a camada “mais crítica” do período atual
- hotspots visíveis
- controles de camadas/modes
- clique abre Drawer (Perfil rápido)

#### 2.1.2 Drawer do território (clique no mapa)
Conteúdo mínimo:
- Nome do território + tipo (Distrito/Bairro/Setor/Zona/Seção)
- Status + Score + Tendência
- 4 mini-métricas:
  - eleitores / população (se houver)
  - escolas / UBS (ou serviços relevantes)
  - abstenção/participação (se eleitoral)
- Evidências (bullets)
- Ações:
  - “Abrir Perfil 360”
  - “Abrir Cenários”
  - “Adicionar ao Brief”

Critério de aceite:
- Home abre e **já mostra** problema + prioridades + hotspots
- 1 clique no mapa → Drawer com contexto e ações

---

### 2.2 MAPA (Modo Avançado)
Rota: `/mapa`

Objetivo: exploração profunda, comparação e exportação.

Composição:
- Mapa full (maior que na Home)
- LayerPanel sempre disponível (lado esquerdo)
- Modo Comparação (split) opcional (toggle)
- Linha do tempo (slider) opcional (se houver dados temporais)

Funções:
- Exportar imagem/estado do mapa para Brief
- “Modo Alerta”: mostrar apenas críticos
- “Modo Gap”: eleitores por serviço / população por UBS etc.

Critério de aceite:
- troca de camadas e zoom sem travar
- comparação lado-a-lado (se implementado) com zoom sincronizado

---

### 2.3 PRIORIDADES
Rota: `/prioridades`

Objetivo: ranking explicável para decisão.

Composição:
- Filtros: território, domínio, período, severidade
- Lista ordenada (Top N)
- Cada item:
  - ranking #
  - território
  - score + tendência
  - “Por quê” (bullets)
  - “Ver no mapa”
  - “Perfil 360”
  - “Adicionar ao Brief”

Critério de aceite:
- ordenar por score
- filtrar por domínio/nível territorial

---

### 2.4 INSIGHTS
Rota: `/insights`

Objetivo: storytelling e “o que importa” sem o usuário procurar.

Composição:
- Cards de insights por severidade (crítico/atenção/info)
- Cada insight:
  - título orientado à decisão
  - território(s) afetado(s)
  - evidências (bullets)
  - CTA: “Ver no mapa” + “Ver evidências”

Critério de aceite:
- insights curtos, acionáveis, com evidência.

---

### 2.5 CENÁRIOS
Rota: `/cenarios`

Objetivo: simulação simples (antes/depois) para decisão.

Composição:
- painel de parâmetros:
  - território
  - indicador
  - ajuste (ex.: +5% cobertura)
- painel de resultados:
  - score antes/depois
  - ranking antes/depois
  - “impacto estimado” (texto curto)
- CTA:
  - “Aplicar no mapa (preview)”
  - “Salvar cenário no Brief”

Critério de aceite:
- cenários não precisam ser ML, apenas regras/elasticidades simples.

---

### 2.6 ELEITORADO & PARTICIPAÇÃO (camada política)
Rota: `/eleitorado`

Objetivo: governabilidade e leitura eleitoral territorial.

Composição:
- Resumo executivo:
  - eleitorado total
  - abstenção
  - perfil etário agregado (se disponível)
- Mapa eleitoral (camadas):
  - zonas (zoom médio)
  - seções/locais (zoom alto) com pontos proporcionais
  - heatmap de concentração
- Tabelas/Rankings:
  - Top zonas/seções por eleitorado
  - Top zonas/seções por abstenção

Critério de aceite:
- visualizar concentração eleitoral e padrões territoriais.

---

### 2.7 PERFIL 360 (Território)
Rota: `/territorio/:territoryId`

Objetivo: visão completa daquele território.

Seções:
1) Visão geral (score, tendência, status)
2) Indicadores por domínio (educação/saúde/eleitoral/etc.)
3) Comparação:
   - vs média municipal
   - vs territórios semelhantes
4) Evolução temporal (se houver)
5) Serviços e gaps (serviços por habitante / eleitores por serviço)
6) Evidências + Metadados (fontes/cobertura)

CTAs:
- “Adicionar ao Brief”
- “Abrir no mapa”
- “Simular cenário”

---

### 2.8 BRIEFS (opcional mas recomendado para apresentação)
Rota: `/briefs`

Objetivo: gerar material apresentável para secretário.

Composição:
- lista de briefs salvos
- editor de brief:
  - inserir mapas “snapshots”
  - inserir cards de prioridades/insights
  - exportar PDF/HTML

Critério de aceite:
- exportar documento com fontes e datas.

---

## 3) Componentes essenciais (contratos)

### 3.1 MapStrategic (componente núcleo)
Props mínimas:
- `mode`: choropleth | points | heatmap | gap | alert
- `layers`: admin, electoralZones, electoralSections, servicesSchool, servicesHealth, hotspots
- `selectedPeriod`, `selectedDomain`, `selectedTerritoryLevel`
- `onFeatureClick(feature)` → abre drawer
- `onViewportChange(viewport)` (zoom, center)

Eventos:
- hover → tooltip (valor + tendência + metadados)
- click → drawer (perfil rápido)

Camadas mínimas:
- Admin polygons (Distrito / Setor)
- Eleitoral (pontos proporcionais por seção / local)
- Serviços (escolas/saúde)
- Hotspots (sobreposição)

---

## 4) Estados globais (store)
Sugestão (Zustand/Redux/Context):
- `period`
- `domain`
- `territoryLevel`
- `layersEnabled`
- `mapMode`
- `selectedFeature`
- `briefDraft`

---

## 5) Contratos API (mínimos para o front)
> endpoints sugeridos — o agente pode adaptar aos endpoints reais.

- `GET /v1/meta/refresh-status`
- `GET /v1/priority/list?period=&level=&domain=&limit=`
- `GET /v1/insights/highlights?period=&level=&domain=`
- `GET /v1/territory/profile/:id?period=`
- `GET /v1/electoral/summary?period=`
- `GET /v1/electoral/sections?period=&zoom=&bbox=`
- `GET /v1/services?type=school|health&bbox=`
- `GET /v1/map/hotspots?period=&domain=&level=&bbox=`
- `GET /v1/map/tiles/:layer/:z/:x/:y.mvt` (produção)

---

## 6) Critérios de qualidade (UX)
- Primeira renderização útil < 3s local
- Home: 0 cliques para “ver problema”
- Legenda sempre presente
- Tooltip sempre mostra fonte/recência
- Proxies sempre marcados (badge “Estimado/Derivado”)
- Não mais que 2 camadas “pesadas” ligadas por padrão (evitar poluição)

---

## 7) Prioridade de entrega (para demo)
Entrega mínima apresentável para Secretário:
1) Home (QG) com mapa dominante + Top 3 prioridades + Drawer
2) Camadas eleitorais (pontos proporcionais + heatmap)
3) Camadas de serviços (escolas + saúde)
4) Perfil 360 (mínimo com comparação simples)
5) Export (snapshot/brief simples)

----------------------

# UI_DESIGN_SYSTEM_SPEC — QG Estratégico (Diamantina/MG)
Versão: 1.0.0  
Objetivo: garantir consistência visual e orientar o agente na implementação do front-end (layout, cores, tipografia, componentes, estados).

---

## 1) Personalidade visual (guiding principles)
- **Institucional, executivo, minimalista**
- O visual deve comunicar: **controle, clareza, seriedade**
- Evitar: cores vibrantes em excesso, excesso de cards, excesso de sombras, “cara de startup”
- A UI deve ser “PowerBI-like”, mas com **mapa vivo** (centro de comando)

---

## 2) Layout e grid
### 2.1 Breakpoints alvo
- Desktop primário: **1440px**
- Responsivo: 1024px / 768px

### 2.2 Home (Layout B)
- Grade: 12 colunas
- **Mapa 70%** (col 9) + **Painel 30%** (col 3)
- Espaçamento base: 16px (gap-4)
- Cards com borda suave e radius alto (24px)

### 2.3 Densidade
- Home: no máximo **3 blocos** no painel lateral + mapa
- Listas longas ficam fora da Home (Prioridades / Perfil 360)

---

## 3) Tipografia (regras)
- Fonte: Inter / system-ui (padrão do projeto)
- Hierarquia:
  - H1: 24–28px, semibold
  - H2: 18–20px, semibold
  - Body: 14–16px
  - Caption/Meta: 12px (muted)
- Regras:
  - sempre mostrar metadados em 12px
  - evitar textos longos: usar bullets curtos

---

## 4) Paleta de cores (tokens)
> Não codificar cores “soltas”. Usar tokens.

### 4.1 Neutros
- `bg`: #FAFAFA
- `surface`: #FFFFFF
- `border`: rgba(0,0,0,0.10)
- `text`: #111827
- `mutedText`: rgba(17,24,39,0.60)

### 4.2 Institucional (primária)
- `primary`: #0B3B8A (azul institucional)
- `primaryHover`: #08306B

### 4.3 Estados e severidade (uso com parcimônia)
- `critical`: #B91C1C
- `warning`: #D97706
- `stable`: #15803D
- `info`: #1D4ED8

### 4.4 Regras de uso de cor
- **Cor forte só para chamar atenção** (crítico/atenção)
- Nunca depender só de cor → use ícone/borda/rótulo junto
- Mapa:
  - base neutra
  - hotspots com destaque sutil (não neon)
  - heatmap com transparência

---

## 5) Componentes padrão (como devem parecer)
### 5.1 Card (default)
- background: `surface` com leve transparência opcional
- borda: `border`
- radius: 24px
- padding: 16px
- shadow: mínima (ou nenhuma)

### 5.2 Button
- Primary:
  - bg `primary`, texto branco, radius 16–20px
- Outline:
  - borda `border`, bg branco
- Estados:
  - hover: leve darken
  - disabled: opacidade 0.6

### 5.3 Badge / Pill
- Para status e metadados
- `secondary`: fundo cinza claro
- `critical`: fundo leve vermelho + borda vermelha
- texto sempre curto

### 5.4 Drawer (painel lateral ao clicar no mapa)
- largura: 360–420px
- fundo: branco 95% + blur
- deve sempre mostrar: título + status + 4 stats + evidências + ações

### 5.5 Tooltip
- compacto, sem texto longo
- sempre com:
  - nome
  - valor
  - tendência (se houver)
  - fonte/recência (caption)

---

## 6) Mapa: UX e UI obrigatórias
### 6.1 Controles fixos no mapa
- Layer panel (toggle de camadas)
- Mode switch:
  - Coroplético
  - Pontos proporcionais
  - Heatmap
  - (opcional) Gap
  - (opcional) Somente críticos

### 6.2 Elementos obrigatórios
- Legenda sempre visível
- Tooltip no hover
- Drawer no click
- “Foco” (quando vindo de prioridade)
- Indicação de proxy (badge “Estimado”) quando aplicável

### 6.3 Camadas padrão
- Território (admin): ligado
- Hotspots: ligado
- Eleitoral: ligado no modo C
- Serviços: ligado no modo C

---

## 7) Direção de “storytelling”
### 7.1 Home deve responder:
- “Qual é o estado da cidade?”
- “Onde está o problema?”
- “Quais são as 3 prioridades?”
- “Por quê?”

### 7.2 Prioridades/Insights
- Frases curtas, orientadas à decisão
- Sempre linkáveis ao mapa (CTA “Ver no mapa”)

---

## 8) Checklist de implementação (para o agente)
- [ ] Criar tokens de cor/estilo (CSS variables ou Tailwind theme)
- [ ] Implementar componentes base (Card/Button/Pill/Drawer/Tooltip)
- [ ] Implementar layout Home 70/30
- [ ] Implementar mapa com:
  - [ ] controles
  - [ ] camadas
  - [ ] modos
  - [ ] tooltip
  - [ ] drawer
  - [ ] legenda
- [ ] Garantir consistência visual em todas as telas
- [ ] Garantir metadados em todos os cards

---

## 9) Critérios de aceite visual
- Um secretário entende a Home em < 10s
- Mapa domina a percepção (não é aba secundária)
- Alertas aparecem com sobriedade (sem poluição)
- Tudo tem fonte/recência
- Estilo consistente entre telas (mesma paleta e componentes)

----------------

# WIREFRAMES_TEXTUAIS — QG Estratégico (Diamantina/MG)
Versão: 1.0.0  
Objetivo: descrever **a planta (wireframe)** de cada tela em formato textual para guiar implementação consistente (Layout, hierarquia, componentes e comportamento).  
Paradigma: **Layout B** (Mapa dominante) + **storytelling executivo**.

---

## 0) Convenções deste documento

### 0.1 Notação
- `[COMP]` = componente
- `(STATE)` = estado/controle
- `{DATA}` = dados exibidos
- `->` = ação/navegação
- `(*)` = obrigatório para demo

### 0.2 Estrutura global (todas as telas)
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]  Logo+Nome | (Período) (Domínio) (Nível) (Busca) [Camadas]      │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]        │ [MainContent]                                          │
│                  │                                                        │
└──────────────────┴────────────────────────────────────────────────────────┘
```

### 0.3 Hierarquia visual padrão
1) Estado/Diagnóstico (o que importa agora)  
2) Onde está (mapa/hotspots)  
3) Por quê (evidências)  
4) O que fazer (CTAs)  

---

## 1) HOME — QG (Layout B) (*)  
Rota: `/`  
Meta: “Em 5–10s o secretário entende onde está o problema e qual é a prioridade.”

### 1.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌──────────────────────────────┬───────────────────────────┐ │
│            │ │ [Painel Estratégico 30%]      │ [Mapa Estratégico 70%]    │ │
│            │ │                              │                           │ │
│            │ │ 1) [Card Índice Municipal]   │  [MapCanvas]              │ │
│            │ │    {Score 0-100} {Status}    │   - Admin polygons        │ │
│            │ │    {Trend} {Metadados}       │   - Hotspots overlay (*)  │ │
│            │ │                              │   - Eleitoral points (*) │ │
│            │ │ 2) [Card Top Prioridades]    │   - Serviços points (*)   │ │
│            │ │    Lista Top 3/5 (*)         │                           │ │
│            │ │    - {Território} {Domínio}  │  [LayerPanel] (dock) (*)  │ │
│            │ │    - {Score} {Trend}         │  [ModeSwitch] (*)         │ │
│            │ │    - bullets “Por quê”       │  [Legend] (*)             │ │
│            │ │    - [Ver no mapa] [Perfil]  │                           │ │
│            │ │                              │  hover -> [Tooltip] (*)   │ │
│            │ │ 3) [Card Destaques]          │  click -> [Drawer] (*)    │ │
│            │ │    3 bullets (storytelling)  │                           │ │
│            │ └──────────────────────────────┴───────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Comportamento obrigatório
- Ao abrir:
  - Mapa já inicia em **Modo C**: Eleitorado + Serviços + Território (*)
  - Hotspots ligados (*)
  - Legenda visível (*)
- Hover em feature -> Tooltip com: `{nome} {valor} {tendência} {fonte/recência}`
- Click em feature -> abre Drawer

### 1.3 Drawer (Perfil rápido) (*)
```
┌───────────────────────────── Drawer (direita) ───────────────────────────┐
│ {Território / Tipo}              [Badge Status]                           │
│ {Score} {Trend}                                                       [X] │
│ ┌──────────┬──────────┬──────────┬──────────┐                            │
│ │ Eleitores│ População│ Escolas   │ UBS      │   (ou métricas do domínio) │
│ └──────────┴──────────┴──────────┴──────────┘                            │
│ Evidências (bullets)                                                     │
│ - ...                                                                    │
│ - ...                                                                    │
│ [Abrir Perfil 360] [Cenários] [Adicionar ao Brief]                       │
│ Metadados: fonte | data | cobertura | proxy?                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2) MAPA — Modo Avançado (*)  
Rota: `/mapa`  
Meta: exploração, comparação, export e análise visual profunda.

### 2.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ [MapWorkspace] (full)                                    │ │
│            │ │                                                         │ │
│            │ │ [LayerPanel] (lado)  [ModeSwitch]  [AlertMode] [Export]  │ │
│            │ │                                                         │ │
│            │ │ [MapCanvas]                                              │ │
│            │ │  - zoom multi-nível                                      │ │
│            │ │  - clustering (opcional)                                 │ │
│            │ │  - split view (opcional)                                 │ │
│            │ │  - time slider (opcional)                                │ │
│            │ │                                                         │ │
│            │ │ [Legend] (fixo)                                          │ │
│            │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Funções
- Modo Alerta: “mostrar apenas críticos”
- Modo Gap: “eleitores por serviço / população por UBS” (proxy simples)
- Export: snapshot para Brief (imagem + metadados)

---

## 3) PRIORIDADES (*)  
Rota: `/prioridades`  
Meta: ranking explicável e acionável.

### 3.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ Header: “Prioridades Estratégicas”                       │ │
│            │ │ (Filtros) Domínio | Nível | Território | Severidade       │ │
│            │ │ [Buscar]                               [Export]          │ │
│            │ ├─────────────────────────────────────────────────────────┤ │
│            │ │ Lista ordenada (Top N)                                   │ │
│            │ │  #1 {Território} {Domínio} {Score} {Trend}               │ │
│            │ │     Por quê: • ... • ...                                 │ │
│            │ │     [Ver no mapa] [Perfil 360] [Adicionar ao Brief]      │ │
│            │ │  #2 ...                                                  │ │
│            │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4) INSIGHTS (*)  
Rota: `/insights`  
Meta: storytelling e highlights com evidências.

### 4.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ Header: “Insights”                                        │ │
│            │ │ (Filtros) Domínio | Nível | Severidade                    │ │
│            │ ├─────────────────────────────────────────────────────────┤ │
│            │ │ Grid Cards                                                │ │
│            │ │ [Card] {Severidade} {Território}                          │ │
│            │ │        Título acionável                                   │ │
│            │ │        Evidências: • • •                                  │ │
│            │ │        [Ver no mapa] [Ver evidências] [Brief]             │ │
│            │ │ ...                                                      │ │
│            │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5) CENÁRIOS (*)  
Rota: `/cenarios`  
Meta: simulação simples e defensável (sem ML obrigatório).

### 5.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ Header: “Cenários”                                        │ │
│            │ ├───────────────────┬─────────────────────────────────────┤ │
│            │ │ [Painel Parâmetros]│ [Painel Resultado]                  │ │
│            │ │ Território         │ Score antes/depois                  │ │
│            │ │ Indicador          │ Ranking antes/depois                │ │
│            │ │ Ajuste (+/-)       │ Impacto estimado (texto curto)      │ │
│            │ │ [Simular]          │ [Aplicar no mapa] [Salvar no Brief] │ │
│            │ └───────────────────┴─────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 6) ELEITORADO & PARTICIPAÇÃO (*)  
Rota: `/eleitorado`  
Meta: leitura política territorial (governabilidade).

### 6.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌──────────────────────────────┬───────────────────────────┐ │
│            │ │ [Painel Resumo 30%]           │ [Mapa Eleitoral 70%]      │ │
│            │ │ Eleitorado total              │ - zonas (zoom médio)      │ │
│            │ │ Abstenção                     │ - seções/locais (zoom alto│ │
│            │ │ Perfil etário agregado         │ - pontos proporcionais (*)│ │
│            │ │ Metadados                      │ - heatmap (*)            │ │
│            │ │                                │ - rankings laterais (op) │ │
│            │ └──────────────────────────────┴───────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7) PERFIL 360 (Território)  
Rota: `/territorio/:territoryId`  
Meta: visão completa e comparativa do território.

### 7.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ Header: {Território}  [Status] [Score] [Trend]           │ │
│            │ │ [Abrir no mapa] [Cenários] [Adicionar ao Brief]          │ │
│            │ ├─────────────────────────────────────────────────────────┤ │
│            │ │ Seção 1: Visão Geral                                     │ │
│            │ │ - 4–6 métricas chave + metadados                          │ │
│            │ │ Seção 2: Indicadores por Domínio                          │ │
│            │ │ - cards por domínio (Educação, Saúde, Eleitoral...)       │ │
│            │ │ Seção 3: Comparação                                       │ │
│            │ │ - vs média municipal; vs pares                            │ │
│            │ │ Seção 4: Evolução temporal (se houver)                    │ │
│            │ │ Seção 5: Serviços e Gaps                                  │ │
│            │ │ Seção 6: Evidências + Metadados + Proxies                 │ │
│            │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 8) ADMIN (operação técnica — não expor ao decisor)  
Rota: `/admin`  
Meta: status do pipeline, fontes, cobertura, erros.

### 8.1 Wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [TopBar]                                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ [LeftNav]  │ ┌─────────────────────────────────────────────────────────┐ │
│            │ │ Cards:                                                   │ │
│            │ │ - Última carga / erros / conectores                       │ │
│            │ │ - Cobertura por fonte                                     │ │
│            │ │ - Execuções recentes (runs)                               │ │
│            │ └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 9) Regras de UX para o agente seguir (resumo)
- Home deve ser “0 cliques para ver o problema”
- Sempre ter `Legenda`, `Tooltip`, `Drawer`
- Camadas agrupadas: Território / Eleitoral / Serviços / Risco
- Nunca expor termos técnicos (PostGIS, tiles, etc.) na UI executiva
- Metadados sempre visíveis: `fonte | data | cobertura | proxy?`

---

## 10) Critérios de aceite da implementação (demo)
- (*) Home com Mapa dominante, Top 3 prioridades, hotspots e drawer.
- (*) Mapa com modos: pontos proporcionais + heatmap.
- (*) Serviços (escola/saúde) visíveis e filtráveis no mapa.
- Eleitorado com resumo + mapa e rankings.
- Perfil 360 navegável a partir do drawer.
