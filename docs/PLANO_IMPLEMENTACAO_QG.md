# Plano Integrado de Implementação (QG Estratégico)

Data de referência: 2026-03-06  
Status: execução ativa  
Escopo: fila única executável do produto.

## 1) Regra de operação

Este documento é a única fonte que define a trilha ativa.  
`VISION` define direção de produto.  
`HANDOFF` registra estado corrente.  
`CHANGELOG` registra histórico validado.

Regras:

- não abrir frentes paralelas;
- não reabrir blocos concluídos sem regressão comprovada;
- toda rodada deve fechar com evidência técnica e atualização documental.

## 2) Estado consolidado

Os blocos `D4` a `D8` estão concluídos tecnicamente.

Isso inclui:

- mapa executivo em fluxo único;
- agregação eleitoral por local de votação;
- geolocalização eleitoral homologada por seed e auditoria;
- telas executivas QG refatoradas;
- explicabilidade e auditoria de pesos de score;
- readiness operacional já funcional;
- operação assistida no Admin para validação e sincronização governadas do ambiente, com histórico persistido em `ops`.

Não há fila funcional aberta nesses blocos neste momento.

## 3) Trilha ativa única

Até nova decisão formal, a trilha ativa é operacional e de governança.

### 3.1 Objetivo da rodada atual

Sustentar o sistema em estado estável e preparar o terreno para a próxima rodada funcional sem reabrir trabalho já concluído.

### 3.2 Itens ativos

1. Executar e manter a rotina da janela de robustez de 30 dias.
2. Sustentar `backend_readiness` em `READY` com `hard_failures=0`.
3. Acompanhar drift em `/v1/ops/robustness-history`.
4. Encerrar as issues já implementadas e ainda abertas no GitHub.
5. Manter a issue `#7` bloqueada até desbloqueio externo da fonte.

## 4) Gate de saída da rodada atual

O ciclo só pode ser considerado encerrado quando:

1. `scripts/persist_ops_robustness_window.py` executar sem regressão operacional.
2. `scripts/backend_readiness.py --output-json` retornar `READY`.
3. o snapshot mais recente de robustez mantiver `gates.all_pass=true`, ou o desvio ficar explicitamente registrado em `HANDOFF` e `CHANGELOG`.
4. se houver mudança em backend ou frontend, os testes e builds pertinentes forem reexecutados.

## 5) Próxima frente funcional permitida

A próxima frente funcional só deve ser aberta depois que a cadência operacional estiver estável.

Atualização 2026-03-07:

- `UX-1` foi iniciado em slice controlado, sem abrir `UX-2`;
- o slice 1 já entregou:
  - `GET /v1/electorate/history`
  - `GET /v1/electorate/polling-places`
  - reformulação da `ElectorateExecutivePage` com histórico anual e ranking de locais;
- o slice 2 passou a entregar no mapa executivo:
  - seletor de métrica eleitoral por local de votação;
  - sincronização entre mapa, ranking e drawer;
  - ranking executivo por local também dentro da experiência cartográfica;
- o próximo passo funcional de `UX-1` passa a ser:
  - estruturar a expansão eleitoral com `tipo de eleição`, `cargo principal`, `candidatos` e `voto territorial por candidato`;
  - conectar essa leitura à narrativa de `Home` e `Prioridades`;
  - manter a unidade principal em `local de votação`.

Regra explícita para essa expansão:

- não abrir uma interface de apuração genérica;
- qualquer evolução de candidato/voto deve reforçar leitura territorial e mapa;
- o primeiro recorte deve privilegiar o cargo principal do ano e a disputa territorial entre candidatos.

Quando isso ocorrer, a ordem recomendada é:

1. `UX-1` — fortalecer o eixo de eleitorado com leitura territorial defensável;
2. `UX-2` — consolidar o mapa executivo com lentes, presets e leitura de cobertura;
3. `UX-3` — alinhar `Home`, `Prioridades` e `Insights` ao mapa como centro da experiência;
4. `UX-4` — ancorar `Cenários` e `Briefs` no território e na seleção cartográfica.

Essa frente deve seguir estritamente o norte definido em `docs/VISION.md`.

Detalhamento oficial da sequência:

- `docs/MAP_PLATFORM_SPEC.md`

## 6) Critério de prioridade funcional futura

Uma nova implementação só entra na fila se atender simultaneamente aos critérios abaixo:

- melhora o valor executivo do produto;
- reforça o mapa como centro de comando;
- aumenta explicabilidade, cobertura ou leitura territorial;
- não cria uma segunda trilha concorrente;
- respeita a ordem `UX-1 -> UX-2 -> UX-3 -> UX-4`.

## 7) Critério de pronto por rodada

Cada rodada deve encerrar com:

- código funcionando no fluxo afetado;
- validação técnica relevante executada;
- `docs/HANDOFF.md` atualizado;
- `docs/CHANGELOG.md` atualizado.

## 8) Referências de decisão

- requisitos técnicos: `docs/CONTRATO.md`
- north star de produto: `docs/VISION.md`
- estado corrente: `docs/HANDOFF.md`
- histórico validado: `docs/CHANGELOG.md`

Atualização complementar 2026-03-07:

- `UX-1 slice 3` deixou de ser apenas desenho futuro.
- A base backend nominal foi entregue com:
  - `silver.dim_election`
  - `silver.dim_candidate`
  - `silver.fact_candidate_vote`
  - `GET /v1/electorate/election-context`
  - `GET /v1/electorate/candidate-territories`
- O slice 3 já foi exposto no frontend executivo com contexto da eleição, top candidatos e distribuição territorial do candidato selecionado.
- O estudo `docs/ESTUDO_TSE_SECAO_LOCAL_VOTACAO.md` concluiu que o TSE já publica `votacao_secao` com `NR_SECAO`, `NR_LOCAL_VOTACAO`, `NM_LOCAL_VOTACAO`, endereço do local, `SQ_CANDIDATO` e `QT_VOTOS` para `2016`, `2018`, `2020`, `2022` e `2024`.
- Portanto, a granularidade nominal atual em `zona eleitoral` deve ser tratada como provisória.
- O próximo passo funcional de `UX-1` deixa de ser propagar a base nominal atual para `Home` e `Prioridades`.
- O próximo passo funcional passa a ser:
  - limpar ou descontinuar explicitamente o residual legado em `electoral_zone` após a migração para `electoral_section`;
  - auditar a necessidade de complementar eleições gerais com recurso nacional (`BR`) após a primeira carga histórica por `votacao_secao`;
  - só depois reabrir a propagação nominal para `Home`, `Prioridades` e demais telas.
- Estado atual do slice 3:
  - o conector nominal foi reorientado em código para `votacao_secao` e o backfill `2016-2024` já foi executado neste ambiente;
  - o Bronze `tse_votacao_secao` está materializado para os cinco anos da série ativa;
  - a cobertura nominal atual do banco já mostra `electoral_section` como nível principal, com `142` seções e `36` locais de votação derivados;
  - o `source_level=electoral_section` já está ativo em `GET /v1/electorate/election-context`;
  - o residual legado de `2024` em `electoral_zone` foi limpo com `scripts/cleanup_candidate_vote_zone_legacy.py`;
  - `2018` e `2022` já foram reprocessados com suplemento presidencial (`BR`) e agora expõem `Presidente` como cargo principal dos anos gerais;
  - a `ElectorateExecutivePage` agora também permite alternar cargo/turno quando o ano possui mais de um cargo nominal, mantendo contexto e distribuição territorial sincronizados;
  - `Home` e `Prioridades` já passaram a consumir o contexto eleitoral nominal validado;
  - o próximo passo funcional passa a ser estender a mesma leitura para `Insights` e deep-links executivos relacionados, sem reabrir infraestrutura do nominal.



