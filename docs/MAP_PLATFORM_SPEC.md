# MAP_PLATFORM_SPEC

Versão: 1.1.0  
Data: 2026-03-06  
Escopo: plataforma do mapa executivo do QG.

## 1) Objetivo

Entregar uma plataforma de mapa dominante para decisão executiva, com:

1. render estável e previsível;
2. leitura espacial clara;
3. troca automática de camadas por zoom;
4. suporte a overlays e lentes operacionais;
5. contrato de API e cache previsíveis.

## 2) Estado atual

Já entregue:

1. manifesto de camadas via `GET /v1/map/layers`;
2. metadados de estilo via `GET /v1/map/style-metadata`;
3. tiles vetoriais via `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`;
4. engine vetorial em `QgMapPage`;
5. modos `choropleth`, `points`, `heatmap` e `hotspots`;
6. exportações `CSV`, `SVG` e `PNG`;
7. mapa eleitoral por local de votação integrado ao fluxo executivo.

## 3) Princípios do mapa

1. o mapa é o centro da experiência executiva;
2. o recorte eleitoral principal é `local de votação`, não `seção eleitoral`;
3. filtros e presets devem gerar ganho visível de leitura;
4. camadas sem utilidade analítica não devem poluir a interface;
5. recortes territoriais só devem aparecer com densidade de indicadores suficiente.

## 4) Regras de zoom

| Zoom | Camada principal | Uso esperado |
|---|---|---|
| `z 0-8` | município | leitura agregada |
| `z 9-11` | distrito | comparação territorial |
| `z >= 12` | setor censitário / pontos | leitura fina e overlays |

## 5) Contratos principais

1. `GET /v1/map/layers`
2. `GET /v1/map/style-metadata`
3. `GET /v1/map/tiles/{layer}/{z}/{x}/{y}.mvt`
4. `GET /v1/electorate/map`

## 6) Leitura eleitoral executiva obrigatória

O eixo eleitoral do mapa não deve se limitar a mostrar pontos.

Ele precisa permitir leitura executiva de:

1. concentração de eleitores por local de votação;
2. participação percentual de cada local no município;
3. quantidade e lista de seções por local;
4. vínculo do local com zona eleitoral e distrito quando disponível;
5. proximidade com escolas, UBS e outros serviços essenciais;
6. comportamento eleitoral por local, não apenas volume:
   - comparecimento;
   - abstenção;
   - votos em branco;
   - votos nulos;
7. leitura histórica mínima para comparação entre anos eleitorais.

Regra de produto:

1. `local de votação` continua sendo a unidade espacial principal;
2. `seção eleitoral` permanece como detalhe de drill-down;
3. a tela de eleitorado e o mapa devem compartilhar a mesma narrativa territorial, sem divergência entre resumo, ranking e detalhe cartográfico.

## 7) Lacunas atuais observadas no sistema

Hoje o sistema já sustenta:

1. agregação por `local de votação`;
2. exibição de eleitores, quantidade de seções e lista de seções no mapa;
3. cruzamento visual básico com escolas e UBS;
4. resumo municipal de eleitorado com composição por sexo, idade e escolaridade.

Mas ainda faltam, para defesa plena do produto:

1. ranking executivo de locais de votação;
2. leitura territorial fora do agregado municipal na tela de eleitorado;
3. métricas eleitorais agregadas por local para além de `voters`;
4. série histórica visível de eleitorado e comportamento eleitoral;
5. lentes eleitorais orientadas por acesso, cobertura e prioridade;
6. narrativa mais forte de cobertura/confiança para camadas eleitorais `proxy`.

## 8) Próxima evolução permitida

A próxima evolução funcional do mapa deve priorizar:

1. presets executivos coerentes;
2. leitura de vazios de cobertura;
3. proximidade e acesso a serviços;
4. densidade analítica intraurbana real.

Não priorizar:

1. efeito visual sem valor analítico;
2. multiplicação de controles;
3. recortes territoriais sem narrativa útil.

## 9) Backlog único de UX executiva

Ordem obrigatória de evolução do frontend executivo:

### UX-1) Eleitorado territorial defensável

Objetivo:

1. tirar a tela de eleitorado do estado "resumo municipal" e levá-la para leitura territorial real.

Entregas mínimas:

1. ranking executivo de locais de votação;
2. participação percentual por local no município;
3. série histórica de eleitorado e comportamento eleitoral;
4. detalhamento claro de seções, zona eleitoral, distrito e serviços próximos;
5. suporte backend para métricas eleitorais por local além de `voters`.

Estado do slice:

1. slice 1 concluído:
   - histórico eleitoral anual;
   - ranking executivo de locais de votação;
   - fallback temporal preservado.
2. slice 2 concluído:
   - comportamento eleitoral por local refletido diretamente no mapa executivo;
   - ranking, tooltip e detalhe sincronizados com a mesma métrica eleitoral;
   - fallback temporal preservado no fluxo cartográfico e no ranking.
3. slice 3 pendente:
   - incorporar contexto de eleição e voto nominal de forma territorialmente defensável.

Detalhamento técnico oficial da expansão eleitoral:

1. `slice 2` opera com dois contratos complementares:
   - `GET /v1/electorate/map` com `aggregate_by=polling_place` para geometria e interação cartográfica;
   - `GET /v1/electorate/polling-places` para ranking executivo, share municipal, distrito, zonas e seções.
2. Tooltip, ranking e drawer devem compartilhar a mesma métrica eleitoral ativa:
   - `voters`;
   - `turnout`;
   - `abstention_rate`;
   - `blank_rate`;
   - `null_rate`.
3. A troca de métrica eleitoral não altera a unidade espacial principal:
   - `local de votação` continua sendo o ponto principal;
   - `seção eleitoral` continua apenas como drill-down.
4. O fallback temporal precisa permanecer coerente entre mapa e ranking:
   - ano solicitado primeiro;
   - fallback automático para o último ano com dados eleitorais utilizáveis quando necessário.
5. O ranking do mapa não pode regredir para tabela municipal quando o overlay eleitoral estiver ativo:
   - o ranking muda para `locais de votação`;
   - a seleção da linha precisa focar o mesmo item no mapa;
   - o drawer precisa refletir o mesmo `territory_id`.

Expansão eleitoral recomendada:

1. adicionar contexto institucional do ano:
   - tipo da eleição;
   - turno;
   - cargo principal analisado.
2. adicionar leitura territorial por candidato:
   - votação por candidato em município, zona, local de votação e seção;
   - participação relativa do candidato por território;
   - margem entre primeiro e segundo colocado;
   - concentração e fragmentação de voto.
3. restringir a exposição inicial ao que melhora leitura executiva:
   - vencedor;
   - top candidatos;
   - disputa;
   - abstenção;
   - concentração territorial.
4. não transformar a camada eleitoral em consulta bruta de apuração.

Modelo de dados recomendado para essa expansão:

1. `silver.dim_election`
2. `silver.dim_candidate`
3. `silver.fact_candidate_vote`

Regra de produto para a expansão:

1. o mapa continua centrado em território;
2. candidato é contexto analítico, não protagonista isolado;
3. seção eleitoral continua como drill-down;
4. a leitura inicial deve privilegiar o cargo principal do ano, evitando somar cargos distintos no mesmo resumo;
5. qualquer detalhamento completo por candidato deve entrar como camada analítica secundária, não como tela principal do eixo executivo.
6. endpoints e tabelas de candidato/voto nominal só entram no `CONTRATO` quando houver implementação real; até lá permanecem como desenho futuro desta spec.

### UX-2) Mapa executivo orientado por lentes

Objetivo:

1. transformar o mapa em motor principal de leitura e decisão.

Entregas mínimas:

1. presets eleitorais e de cobertura;
2. leitura de vazios de cobertura;
3. proximidade e acesso a serviços;
4. ranking sincronizado com seleção cartográfica;
5. badges e mensagens claras para camadas `official`, `proxy` e `hybrid`.

### UX-3) Home, Prioridades e Insights alinhados ao mapa

Objetivo:

1. fazer as telas executivas derivarem da leitura territorial, e não competirem com ela.

Entregas mínimas:

1. Home como síntese orientada pelo mapa;
2. Prioridades com agrupamento territorial e CTA operacional;
3. Insights com vínculo direto entre evidência, território e lente cartográfica.

### UX-4) Cenários e Briefs ancorados no território

Objetivo:

1. fechar o ciclo decisão -> simulação -> comunicação.

Entregas mínimas:

1. cenários com impacto espacial legível;
2. briefs gerados a partir de seleção territorial/mapa;
3. exportação com contexto geográfico e hotspots priorizados.

## 10) Regra de execução

1. não iniciar `UX-2` antes de fechar o núcleo de `UX-1`;
2. não refinar Home/Prioridades/Insights sem a gramática do mapa consolidada;
3. não expandir visuais antes de consolidar leitura territorial defensável;
4. qualquer nova tela ou refinamento deve se encaixar nesta sequência, sem abrir trilha paralela.

Atualizacao 2026-03-07:

1. o backend nominal deixou de ser apenas recomendacao;
2. ja existem:
   - `silver.dim_election`
   - `silver.dim_candidate`
   - `silver.fact_candidate_vote`
   - `GET /v1/electorate/election-context`
   - `GET /v1/electorate/candidate-territories`
3. o slice 3 continua aberto apenas na camada executiva/frontend.
