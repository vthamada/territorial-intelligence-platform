# Guia passo a passo — Refatoração de TODAS as telas (QG Diamantina)
Objetivo: refatorar cada tela para ficar **executiva, coerente, limpa**, sem controles “fantasmas”, com hierarquia visual forte e UX consistente.

## Regras globais (valem para todas as telas)
1. **Remover controles que não causam efeito visível** (filtro que não muda nada = ruído).
2. **Uma única fonte de controle por coisa** (sem duplicar “visualização” e “camadas”, por exemplo).
3. **Filtros sempre em 1 linha** (altura padrão 40px, botões alinhados).
4. **Metadados (fonte/atualização/cobertura)**: sempre discretos (caption), nunca poluir o conteúdo.
5. **Conteúdo longo vira colapsável** (accordion/tabs). Nada de telas com scroll infinito por padrão.
6. **Linguagem executiva**: esconder campos técnicos (IDs, códigos) em “Metadados técnicos” colapsável.
7. **CTAs padronizados**: “Ver no mapa”, “Perfil 360”, “Adicionar ao Brief” sempre com o mesmo estilo.

---

# 1) Visão Geral (Home)
## Diagnóstico atual
- Home está com muita coisa: mapa situacional + filtros + prioridades + destaques + domínios + KPI grande.
- O mapa na Home **não agrega** se não mostra algo estratégico diferente do /mapa.

## Refatoração passo a passo
1. **Remover o mapa interativo da Home** (deixar apenas o da aba Mapa).
2. Criar um topo executivo com 3 blocos:
   - **Score geral do município** (card grande) + status (crítico/atenção/estável)
   - **Contagem de itens por severidade** (chips: críticos/atenção/estáveis)
   - **Tendência geral** (se houver)
3. **Top prioridades**:
   - limitar a 3–5 cards
   - cada card: título + 2–3 bullets “por quê” + CTAs (“Ver no mapa”, “Perfil 360”)
4. **Destaques**:
   - exibir 5 itens no máximo + botão “Ver mais”
5. **Domínios Onda B/C**:
   - manter tabela curta com CTA “Abrir no mapa”
6. **KPIs executivos**:
   - virar **accordion colapsável** (fechado por padrão) ou mover para “Território 360”.

✅ Aceite: Home vira um painel de leitura em 60 segundos, sem “mapa de enfeite”.

Obs: Abrir no mapa 

---

# 2) Mapa (aba /mapa)
## Diagnóstico atual
- Já está muito bem estruturado: mapa dominante, camadas à direita, tabs embaixo.
- Falta polimento de linguagem e micro-UX (detalhes ainda parecem debug).

## Refatoração passo a passo
1. Topo do mapa: manter só o essencial:
   - Base map (Ruas/Claro/Sem base)
   - Export (SVG/PNG)
   - Busca (autocomplete para local/serviço)
2. Painel de camadas (único ponto de controle):
   - Território: Limite municipal (contorno discreto, mas deixar o usuário ativar ou não)
   - Eleitoral: **Locais de votação (agregado)** 
   - Serviços: Escolas / UBS 
   - Fase 2: Hotspots / Índice
3. **Eleitoral**:
   - manter como está: local de votação com total de eleitores agregado
   - garantir anti-poluição: cluster em zoom baixo, pontos proporcionais em zoom alto
4. **Detalhes do território** (aba inferior):
   - trocar labels técnicas por executivas:
     - “Eleitores no local: 202” (sem decimais)
     - “Seções no local: 1”
   - esconder `polling_place_code` e afins em “Metadados técnicos” colapsável
5. Ranking indisponível:
   - adicionar CTA “Ver ranking no nível Município/Distrito”
6. Ajuste visual:
   - remover qualquer “fill” forte do município no modo eleitoral (usar contorno)

✅ Aceite: mapa é centro de comando, sem termos técnicos aparentes e com leitura imediata.

---

# 3) Prioridades
## Diagnóstico atual
- Muitos cards e repetição. Falta síntese e melhor navegação.
- Precisa reduzir fadiga e melhorar filtros.

## Refatoração passo a passo
1. Filtros em 1 linha:
   - período, domínio, severidade, ordenação, busca
2. Adicionar **Resumo** acima da lista:
   - “X itens — Y críticos, Z atenção”
3. Cards:
   - padronizar altura e bullets (máximo 3)
   - CTA fixo: “Ver no mapa”, “Perfil 360”, “Brief”
4. Paginação:
   - limitar itens por página e não renderizar tudo

✅ Aceite: lista rápida e acionável.

---

# 4) Insights
## Diagnóstico atual
- Lista longa com repetição. Falta narrativa e agrupamento.

## Refatoração passo a passo
1. Filtros em 1 linha:
   - período, domínio, severidade
2. Agrupar insights por severidade:
   - Crítico / Atenção / Info (cada um colapsável)
3. Cada insight:
   - título “orientado à decisão”
   - 1 linha de evidência + metadados discretos
   - CTA: “Ver no mapa”, “Adicionar ao Brief”
4. Paginação

✅ Aceite: storytelling executivo, não feed infinito.

---

# 5) Cenários
## Diagnóstico atual
- Muitos cards de resultado e “análises” sempre abertas.

## Refatoração passo a passo
1. Simplificar entrada:
   - território, período, domínio (opcional), ajuste (%) com slider + input
2. Resultado: manter só 4 KPIs:
   - Score antes/depois
   - Status antes/depois
   - Variação ranking
   - Impacto resumido (texto)
3. “Análises 1..n”:
   - colocar em accordion colapsável

✅ Aceite: simulação clara e defensável.

---

# 6) Eleitorado
## Diagnóstico atual
- Muito bom como painel tabular, mas desconecta do mapa eleitoral.

## Refatoração passo a passo
1. Manter resumo executivo (cards)
2. Composição (sexo/idade/escolaridade):
   - colocar filtro por grupo (tabs: Sexo | Idade | Escolaridade) para não ser tabela gigante
3. Adicionar CTA principal:
   - “Abrir mapa eleitoral (locais de votação)” → abre /mapa com camadas eleitorais ON e foco urbano
4. Tabela “Mapa tabular por território”:
   - colapsável

✅ Aceite: Eleitorado = análise, Mapa = ação.

---

# 7) Território 360
## Diagnóstico atual
- Estrutura boa, mas precisa síntese e controle de densidade.

## Refatoração passo a passo
1. Topo: filtros mínimos
2. “Status geral”:
   - manter 3–4 cards (score, domínios, indicadores, tendência)
3. “Destaques”:
   - 3–5 itens + “ver mais”
4. “Domínios e indicadores”:
   - tabela com busca + paginação + altura limitada
   - nada de scroll infinito

✅ Aceite: perfil executivo numa tela, detalhes sob demanda.

---

# 8) Briefs
## Diagnóstico atual
- Bom, mas pode ficar mais “produto” e menos “form”.

## Refatoração passo a passo
1. Simplificar filtros:
   - período, território, limite evidências
2. “Gerar brief” como CTA primário destacado
3. Saída:
   - Resumo executivo em cards
   - Evidências em tabela paginada
   - Export HTML e Imprimir/PDF bem evidentes

✅ Aceite: pronto para apresentar ao secretário.

---

# 9) Admin
## Diagnóstico atual
- Está no caminho certo (técnico/operacional).
- Só precisa consistência visual.

## Refatoração passo a passo
1. Manter cards de readiness
2. Tabela de cobertura de camadas:
   - ok manter
3. Ferramentas operacionais:
   - padronizar cards (altura, ícone, CTA)
4. Garantir que Admin é “modo técnico” (copy e visual mais neutros)

✅ Aceite: área técnica sólida, sem interferir no fluxo executivo.

---

# Ordem recomendada para o agente (pra não se perder)
1) **Mapa** (polimento final + linguagem executiva + cluster/zoom + detalhes sem debug)  
2) **Visão Geral** (remover mapa interativo e virar painel executivo)  
3) **Eleitorado** (tabelas em tabs + CTA para abrir mapa eleitoral)  
4) **Prioridades** (resumo + paginação + cards padronizados)  
5) **Insights** (agrupamento por severidade + paginação)  
6) **Território 360** (síntese + tabela paginada)  
7) **Briefs** (polir export e layout)  
8) **Cenários** (reduzir cards e colapsar análises)  
9) **Admin** (padronização visual)

---

# Checklist final (definição de “pronto”)
- [ ] Nenhum controle fantasma em nenhuma tela
- [ ] Filtros sempre alinhados (1 linha, altura 40px)
- [ ] Metadados discretos e consistentes
- [ ] Conteúdo longo sempre colapsável/paginado
- [ ] Mapa com linguagem executiva (sem campos técnicos expostos)
- [ ] CTAs padronizados e coerentes