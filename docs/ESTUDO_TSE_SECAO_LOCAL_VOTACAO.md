# Estudo de Viabilidade TSE - Voto Nominal por Seção e Local de Votação

Data de referência: 2026-03-07  
Status: concluído  
Escopo: verificar se o TSE disponibiliza base nominal suficiente para migrar o eixo eleitoral do produto de `zona eleitoral` para `seção eleitoral` e `local de votação`.

## 1) Resposta executiva

Sim. Para os anos atualmente suportados pelo sistema (`2016`, `2018`, `2020`, `2022` e `2024`), o TSE disponibiliza base oficial de `votação por seção eleitoral`.

No recorte de Minas Gerais, os arquivos oficiais baixados contêm, de forma consistente:

- `NR_SECAO`
- `NR_LOCAL_VOTACAO`
- `NM_LOCAL_VOTACAO`
- `DS_LOCAL_VOTACAO_ENDERECO`
- `SQ_CANDIDATO`
- `QT_VOTOS`

Isso significa que:

1. é viável carregar voto nominal por `seção eleitoral`;
2. é viável derivar voto nominal por `local de votação` a partir da agregação das seções;
3. a limitação atual do sistema em `zona eleitoral` não é uma limitação estrutural da fonte oficial para a série `2016-2024`;
4. a limitação atual decorre da escolha do conector `tse_votacao_candidato_munzona`.

## 2) Evidência oficial da internet

Páginas oficiais do Portal de Dados Abertos do TSE consultadas:

- `https://dadosabertos.tse.jus.br/dataset/resultados-2016`
- `https://dadosabertos.tse.jus.br/dataset/resultados-2020`
- `https://dadosabertos.tse.jus.br/dataset/resultados-2022`
- `https://dadosabertos.tse.jus.br/dataset/resultados-2024`

As páginas acima indicam explicitamente a existência de:

- `Votação por seção eleitoral`
- `Detalhe da apuração por seção eleitoral`

Para `2022`, o próprio portal informa que os arquivos de votação por seção eleitoral separados por UF trazem a totalização dos cargos estaduais/federais por estado e o arquivo `BR` traz o cargo de Presidente.

## 3) Evidência oficial validada em arquivo bruto

Arquivos oficiais baixados do CDN do TSE para Minas Gerais:

- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2016_MG.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2018_MG.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2020_MG.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_MG.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2024_MG.zip`

Resultado da inspeção de schema:

| Ano | Arquivo MG existe | `NR_SECAO` | `NR_LOCAL_VOTACAO` | `NM_LOCAL_VOTACAO` | Endereço do local | `SQ_CANDIDATO` | `QT_VOTOS` | Viabilidade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | sim | sim | sim | sim | sim | sim | sim | alta |
| 2018 | sim | sim | sim | sim | sim | sim | sim | alta |
| 2020 | sim | sim | sim | sim | sim | sim | sim | alta |
| 2022 | sim | sim | sim | sim | sim | sim | sim | alta |
| 2024 | sim | sim | sim | sim | sim | sim | sim | alta |

Conclusão objetiva: a estrutura necessária para `seção eleitoral` e `local de votação` está presente de forma consistente em toda a série histórica atualmente usada pelo projeto.

## 4) Estado do projeto no momento do estudo

No momento em que o estudo foi feito, o projeto estava preso à granularidade de `zona eleitoral` por escolha de ingestão, não por falta de fonte.

Evidências internas:

- `src/pipelines/tse_candidate_votes.py`
  - usava `DATASET_NAME = "tse_votacao_candidato_munzona"`
- `src/app/api/routes_qg.py`
  - retorna `candidate_territories_unavailable|source_level=electoral_zone|requested_aggregate=polling_place`
- Bronze TSE hoje presente no repositório:
  - `data/bronze/tse/tse_votacao_candidato_munzona/...`
  - `data/bronze/tse/tse_detalhe_votacao_munzona/...`
  - `data/bronze/tse/tse_perfil_eleitorado/...`
  - não havia ingestão equivalente de `tse_votacao_secao` no fluxo ativo

Nota de atualização:

- em `2026-03-08`, o conector nominal começou a ser reorientado em código para `tse_votacao_secao`;
- o estudo permanece válido como justificativa da mudança, mas o próximo foco deixa de ser “migrar o conector” e passa a ser “executar backfill histórico e validar a nova carga”.

## 5) Leitura correta para o produto

Para Diamantina/MG, a prioridade correta é:

1. `seção eleitoral` como nível nominal primário;
2. `local de votação` como agregado operacional principal derivado das seções;
3. `zona eleitoral` apenas como fallback técnico ou camada institucional secundária.

Isso é mais coerente com:

- `docs/VISION.md`
- `docs/MAP_PLATFORM_SPEC.md`
- a proposta do mapa executivo como leitura territorial defensável

## 6) O que ainda falta validar

O estudo já responde a viabilidade estrutural. Ainda falta validar na implementação:

1. volume e performance de ingestão para todos os anos;
2. modelagem idempotente da fato nominal por seção;
3. regra de agregação por `local de votação` preservando consistência histórica;
4. relação entre `votacao_secao` e `detalhe_votacao_secao` para enriquecer:
   - comparecimento
   - abstenção
   - válidos
   - brancos
   - nulos
5. estratégia de compatibilidade para anos/cargos que possam exigir arquivos complementares (`BR` vs `UF` em eleições gerais).

## 7) Recomendação objetiva

O próximo passo correto não é espalhar a base nominal atual por `zona eleitoral` para mais telas.

O próximo passo correto é:

1. criar ou substituir o conector nominal para usar `votacao_secao`;
2. reprocessar a série `2016-2024` nessa granularidade;
3. remodelar `silver.fact_candidate_vote` para chave primária em `electoral_section`;
4. derivar `polling_place` por agregação de seções;
5. só depois reabrir a expansão nominal em `Home`, `Prioridades` e mapa.

## 8) Decisão recomendada

Decisão recomendada para a trilha ativa:

- interromper a expansão de UX baseada em nominal por `zona eleitoral`;
- reorientar o backlog nominal para `seção eleitoral` e `local de votação`;
- manter `zona eleitoral` apenas como fallback provisório até a migração de fonte.
