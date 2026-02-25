# Guia passo a passo (para o agente) — Refatoração do Mapa (Layout + UX + Camadas Eleitorais)

Contexto: a tela `/mapa` hoje está com controles redundantes, elementos que não impactam o mapa, inconsistência visual (desalinhamentos) e foco estratégico diluído. O objetivo é deixar o **mapa protagonista**, com **controles mínimos e úteis**, e representação eleitoral correta considerando que **um local de votação pode ter múltiplas seções**.

---

## 0) Objetivo do produto (definição clara)

O mapa deve funcionar como:
> Ferramenta de leitura territorial estratégica (QG), onde o usuário entende em 3 segundos:
- onde estão os **polos de concentração eleitoral**
- onde estão os **serviços** (escolas/UBS)
- onde há **lacunas** (fase 2)

**Importante:** Seções não têm geometria própria pública. O ponto espacial real é o **Local de votação**.  
Logo, o mapa eleitoral deve representar **Locais de votação agregados por seções**.

---

## 1) Decisões de UX (cortar ruído / eliminar redundâncias)

### 1.1 Remover/ocultar (Fase 1)
**Remover da UI do mapa:**
- Indicador (se não altera estilo/camadas/valor do mapa)
- Período (se não altera estilo/camadas/valor do mapa)
- Recorte/Nível (se não altera o que é renderizado no mapa)
- “Visualização” duplicada (Seções / Serviços / Seções + Serviços) caso já exista painel de camadas
- “Modo simplificado” (não agrega; confunde; gera modo verde sem base)

**Regra:** Controle que não causa impacto visual imediato no mapa = não deve existir na tela do mapa.

### 1.2 Manter apenas controles essenciais no topo (Fase 1)
- Base map: Ruas | Claro | Sem base
- Export: SVG | PNG (opcional, pode ficar no menu de overflow)
- Busca/foco: input “Buscar território/Endereço” (opcional)
- Nada além disso

---

## 2) Layout alvo (mapa protagonista)

### 2.1 Estrutura final da tela `/mapa`
- Header (título + contexto “Diamantina/MG | API v1”)
- Barra compacta de ações (1 linha): Base map + export
- Corpo em **2 colunas**:
  - Coluna esquerda (≈ 75%): **Mapa grande** (sem scroll inicial)
  - Coluna direita (≈ 25%): **Painel de camadas** (único lugar para ligar/desligar layers)
- Rodapé colapsável em tabs (Ranking / Detalhes) — fechado por padrão

**Critério de aceite:** em 1440x900 o mapa aparece grande e o usuário não precisa rolar para “ver o mapa”.

---

## 3) Padronização visual (resolver desorganização)

### 3.1 Tokens mínimos (padrão)
- Altura inputs e botões: **40px**
- Gap padrão: **12–16px**
- Cards: borda 1px, radius 16–20px, padding 16px
- Tipografia:
  - H1: página
  - H2: seção
  - Texto auxiliar menor e discreto

### 3.2 Componentes recomendados
- `SegmentedControl` (Base map)
- `ButtonPrimary`, `ButtonSecondary`
- `LayerGroup` e `LayerToggleRow` (checkbox alinhado + label clicável)
- `Card` (mesma sombra/borda em todos os blocos)

**Critério de aceite:** não existir checkbox “flutuando”, nem labels desalinhados, nem botões com padding diferente.

---

## 4) Painel de camadas (único ponto de controle)

### 4.1 Estrutura fixa do painel (Fase 1)

Obs: Os checkbox e as descrições precisam estar alinhadas horizontalmente

**Território**
- ☐ Limite municipal — **contorno discreto**, sem fill forte
- ☐ Distritos / setores (opcional; somente quando existir dado real)

**Eleitoral**
- ☐ Locais de votação (agregado)
- ☐ Seções (detalhe) (Fase 2 / somente via drill-down)

**Serviços**
- ☐ Escolas
- ☐ UBS / Saúde

**Risco / Estratégia (Fase 2)**
- ☐ Hotspots
- ☐ Índice estratégico

### 4.2 Remover texto técnico do painel
Remover:
- “proxy”, “origem automática”, “geometria limitada”
- “cobertura 144/144 …” (isso é log técnico)

Se precisar, adicionar um bloco discreto “Metadados” colapsável.

---

## 5) Eleitoral: modelagem correta no mapa (Local de votação > Seção)

### 5.1 Premissa
- Um **Local de votação** pode conter **várias seções**
- Todas as seções de um local compartilham **mesma coordenada** (ou quase)
- Se desenhar “seção por seção” como ponto, terá sobreposição/poluição

### 5.2 Representação recomendada (Fase 1)
Representar **UM ponto por Local de votação**, com:
- tamanho proporcional ao **total de eleitores no local (soma das seções)**
- tooltip listando **quantidade de seções** e **lista resumida** (ou “ver detalhes”)

**Tooltip (hover) obrigatório**
- Local: {nome_local}
- Total eleitores: {total_eleitores}
- Qtd seções: {qtd_secoes}
- Seções: {lista curta} ou “Seções: 10 (abrir)”
- Fonte: TSE | Atualização: {data}

### 5.3 Anti-poluição obrigatório (cluster + zoom)
- Zoom baixo (ex z ≤ 12): clusters automáticos
  - cluster mostra: “X locais | Y eleitores”
- Zoom médio/alto (z ≥ 13): pontos individuais por local

### 5.4 Escala do raio (não linear)
- usar `radius = k * sqrt(total_eleitores)`
- clamps:
  - `radiusMin = 4`
  - `radiusMax = 18` (ajustar)
- opacidade: 0.6–0.75
- borda branca fina (1px)

### 5.5 Click abre Drawer (drill-down)
Ao clicar no **local**:
- Abrir drawer com:
  - Nome do local
  - Total de eleitores
  - Lista de seções (número + eleitores)
  - Ação: “Ver no mapa” / “Adicionar ao Brief”
  - (stub) “Perfil 360” (pode ser placeholder)

**Critério de aceite:** não há sobreposição de “pontos iguais no mesmo lugar” e o mapa continua limpo.

---

## 6) Serviços (manter como está, com ajustes leves)

### 6.1 Manter padrão atual (está bom)
- Escolas: amarelo
- UBS: vermelho
- Tooltip no hover

### 6.2 Melhorias opcionais
- cluster em zoom baixo se muitos pontos
- ícones consistentes (se já existirem)

---

## 7) Limite municipal (polígono grande/verde/azul) — corrigir comportamento

### 7.1 No modo eleitoral, limite municipal não pode “pintar” a tela
- Usar contorno discreto (stroke)
- Fill só se necessário e com opacidade mínima (ex 0.05)

### 7.2 Garantir geometria correta
- Validar que o polígono corresponde ao município de Diamantina (IBGE 3121605)
- Se estiver grande/diferente, revisar fonte/filtro/CRS

---

## 8) Eliminar duplicidade de controles

### 8.1 Se existe painel de camadas, remover “Visualização”
Hoje existem:
- botões “visualização” (seções/serviços/ambos)
- e toggles no painel de camadas

Escolher **um**.  
Recomendação: **painel de camadas** como único ponto de controle.

---

## 9) Revisão de componentes “fantasmas” (não fazem nada)

### 9.1 Indicador/Período/Recorte/Nível
Se esses campos não alteram:
- estilo do mapa
- dados renderizados
- ranking
- camadas

Então devem ser removidos do `/mapa`.

Se forem necessários, mover para:
- Visão Geral (nível executivo)
- Perfil 360 (nível analítico)
- Ranking (para comparação)

---

## 10) Tabs inferiores (Ranking/Detalhes) — colapsáveis e sem poluir a tela

- Por padrão: fechadas
- Abertura via tabs: “Ranking” | “Detalhes do território”
- Não exibir painéis enormes sempre abertos (isso está gerando scroll e confusão)

---

## 11) Ordem recomendada de implementação (para não se perder)

1) Simplificar UI: remover Indicador/Período/Recorte/Nível/Modo simplificado/Visualização redundante  
2) Refatorar layout 2 colunas com mapa dominante  
3) Reestruturar painel de camadas (grupos + alinhamento)  
4) Corrigir limite municipal (contorno discreto)  
5) Implementar eleitoral por **Local de votação agregado** (com cluster + raio sqrt)  
6) Implementar tooltip e drawer do local (com lista de seções)  
7) Garantir serviços como overlay opcional (sem regressão)  
8) Transformar Ranking/Detalhes em tabs colapsáveis  
9) Polimento final de espaçamentos / consistência

---

## 12) Checklist final de aceitação

### UI
- [ ] Sem campos “fantasmas” que não impactam o mapa
- [ ] Sem “modo simplificado”
- [ ] Sem controles duplicados (visualização vs camadas)
- [ ] Painel de camadas alinhado e legível
- [ ] Mapa domina a tela sem scroll inicial

### Eleitoral
- [ ] Ponto por **Local de votação** (não por seção)
- [ ] Tamanho proporcional ao total de eleitores (sqrt)
- [ ] Cluster em zoom baixo
- [ ] Tooltip com total, qtd seções e fonte
- [ ] Click abre drawer com lista de seções

### Serviços
- [ ] Escolas e UBS continuam com tooltip e boa leitura
- [ ] Não polui o mapa quando combinado com eleitoral

---

## Observação final (diretriz de produto)
A tela `/mapa` deve ser operacional e territorial.
Indicadores e análises gerais devem ficar em Visão Geral / Perfil 360.
No mapa, tudo precisa ser “ver e entender”.