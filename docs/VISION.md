# VISÃO DO PRODUTO
## QG Estratégico Territorial — Diamantina/MG

Data de referência: 2026-03-06  
Status: ativo  
Papel: north star de produto e experiência.

## 1) Propósito

Construir um centro de comando estratégico municipal para Diamantina/MG baseado em dados públicos, capaz de:

- transformar dados dispersos em inteligência territorial clara;
- localizar gargalos e vazios de cobertura;
- cruzar território, eleitorado e serviços públicos;
- apoiar decisão executiva com evidência espacial.

O sistema não deve ser apenas um dashboard.  
Ele deve funcionar como uma plataforma geoespacial de leitura executiva.

## 2) Problema que o produto resolve

Hoje o gestor público até possui dados, mas não possui:

- integração territorial clara;
- leitura espacial consolidada;
- conexão entre demanda territorial e oferta de serviços;
- uma ferramenta que mostre onde estão os desequilíbrios relevantes.

O resultado sem o QG é previsível:

- decisões fragmentadas;
- baixa priorização territorial;
- dificuldade de enxergar a cidade como sistema.

## 3) Princípio central

O sistema deve permitir que Prefeito, Secretário ou assessor estratégico:

- entendam a cidade em minutos;
- identifiquem problemas territorialmente;
- sustentem decisão com evidência;
- transformem leitura em ação.

A experiência esperada é:

- clara;
- orientada;
- visualmente forte;
- defensável institucionalmente.

## 4) Estrutura conceitual

O produto opera sobre territórios paralelos que podem ser cruzados.

### 4.1 Território administrativo

- município;
- distritos;
- bairros, se houver camada confiável;
- setores censitários, quando houver densidade analítica real.

### 4.2 Território eleitoral

- zonas eleitorais;
- seções eleitorais;
- locais de votação.

### 4.3 Território de serviços

- escolas;
- unidades de saúde;
- equipamentos públicos e pontos de interesse relevantes.

### 4.4 Confiabilidade da camada

Nem todo recorte territorial tem o mesmo nível de confiança.

O produto deve distinguir com clareza:

- camada oficial;
- camada proxy;
- camada híbrida.

Essa distinção não é detalhe técnico.  
Ela influencia a força da leitura executiva.

Regra de produto:

- camadas oficiais podem sustentar leitura principal;
- camadas proxy ou híbridas podem apoiar a análise, mas devem expor metodologia e limitação de forma visível;
- nenhuma camada proxy deve parecer equivalente a uma camada oficial sem aviso explícito.

## 5) Princípios de produto

### 5.1 O mapa é o centro

O mapa não é complemento.  
O mapa é o centro da experiência executiva.

Ele deve permitir:

- localizar concentração eleitoral;
- cruzar serviços públicos com demanda territorial;
- identificar hotspots e vazios de cobertura;
- sustentar leitura rápida e drill-down coerente;
- mostrar acesso, proximidade e distribuição intraurbana quando houver base suficiente.

### 5.2 Visão Geral é síntese, não catálogo

A Visão Geral deve responder rapidamente:

- como está o território;
- quais são as prioridades;
- onde estão os principais problemas;
- qual a próxima ação recomendada.

Ela não deve usar como protagonismo:

- zona eleitoral;
- seção eleitoral;
- local de votação;
- atributos cadastrais sem valor analítico, como área territorial isolada.

### 5.3 Recorte territorial só entra quando há densidade

Geometria sozinha não gera valor.  
Um nível territorial só deve ser exposto como leitura estratégica quando houver:

- geometria confiável;
- atributos úteis;
- comparação possível;
- narrativa decisória;
- cobertura estável o suficiente para não induzir erro.

Se distrito ou setor censitário não tiverem indicadores fortes, o produto deve:

- esconder o recorte; ou
- exibir estado vazio inteligente explicando a limitação.

Distrito e setor censitário não devem entrar apenas porque a geometria existe.  
Eles entram quando ajudarem a responder onde está o problema, qual sua intensidade e qual ação faz sentido.

### 5.4 Gramática operacional do mapa

O mapa deve obedecer uma progressão clara de leitura:

- zoom mais aberto: município e síntese agregada;
- zoom intermediário: distritos, quando houver densidade analítica suficiente;
- zoom fino: setores censitários, locais de votação e serviços, quando a leitura intraurbana for realmente útil.

Essa progressão deve evitar dois erros:

- mostrar granularidade fina sem contexto;
- manter agregação excessiva quando a leitura local já é necessária.

### 5.5 Linguagem executiva

- o conteúdo principal deve usar linguagem executiva;
- IDs, chaves técnicas e detalhes de debug devem ficar em metadados colapsáveis;
- CTAs devem existir apenas quando geram ganho real de compreensão.

## 6) Regra atual do mapa

No fluxo eleitoral, a unidade espacial principal deve ser:

- local de votação.

Justificativa:

- um local pode concentrar várias seções;
- isso evita sobreposição artificial;
- melhora a leitura de concentração eleitoral;
- permite cruzamento mais útil com escolas, UBS e outros serviços.

Detalhes de seção podem existir em:

- tooltip;
- painel de detalhe;
- drill-down.

Mas seção eleitoral não deve ser o ponto principal do mapa executivo.

## 7) Lentes prioritárias

O produto deve caminhar para presets claros e operacionais, como:

- eleitoral;
- serviços;
- eleitoral + serviços;
- locais prioritários;
- vazios de cobertura.

Essas lentes são importantes porque transformam o mapa em leitura orientada, não em exploração solta.

Lentes prioritárias mais úteis:

- eleitoral;
- serviços essenciais;
- eleitoral + serviços;
- mobilidade e acesso;
- vulnerabilidade social;
- risco ambiental;
- locais prioritários;
- vazios de cobertura.

## 8) Dados intraurbanos que realmente agregam valor

Distritos e setores censitários só passam a ser estratégicos quando o sistema conseguir produzir, por geometria:

- população;
- domicílios;
- composição etária;
- alfabetização;
- água, esgoto e lixo;
- proxies de vulnerabilidade;
- acesso e proximidade de serviços;
- comparações territoriais consistentes.

Sem isso, o produto deve priorizar município, local de votação e overlays de serviços.

Base urbana que fortalece essa leitura:

- vias e logradouros;
- pontos de interesse essenciais;
- equipamentos públicos georreferenciados;
- métricas de proximidade e cobertura;
- leitura de vazio territorial e concentração de oferta.

## 9) Limites éticos e técnicos

- apenas dados agregados e públicos;
- nenhuma identificação individual;
- transparência sobre proxies, fontes e limitações;
- distinção clara entre dado oficial, proxy, derivado e estimado.

## 10) Declaração final

Objetivo final do QG Estratégico:

**Permitir que Diamantina seja compreendida como território vivo e que decisões sejam tomadas com base em evidência espacial clara, útil e defensável.**
