# Plano de Fontes Futuras - Diamantina/MG

Data de referencia: 2026-02-11  
Escopo territorial: Diamantina/MG (`MUNICIPALITY_IBGE_CODE=3121605`)

## 1) Estado atual

Backend local validado como pronto para fechamento da etapa tecnica:
- `scripts/backend_readiness.py --output-json` => `READY`
- `hard_failures=0`, `warnings=0`
- `SLO-1` e `SLO-3` atendidos na janela de 7 dias

Fontes ja implementadas no produto:
- IBGE (admin, malhas, indicadores iniciais)
- TSE (eleitorado e resultados)
- INEP (sinopse municipal)
- DATASUS (indicadores de saude atuais)
- SICONFI (DCA)
- MTE (Novo CAGED)

## 2) Criterio para priorizar novas fontes

Cada fonte abaixo foi priorizada por:
1. Valor analitico para diagnostico municipal de Diamantina.
2. Facilidade de extracao automatica e idempotente.
3. Aderencia ao contrato atual (Bronze/Silver/ops + checks).

Escala usada:
- Impacto: alto | medio
- Esforco: baixo | medio | alto

## 3) Catalogo de fontes adicionais recomendadas

### Onda A (entrar primeiro: alto impacto + baixo/medio esforco)

1. IBGE SIDRA API (expansao de indicadores socioeconomicos)
- Impacto: alto
- Esforco: baixo
- Granularidade: municipal
- Link: https://apisidra.ibge.gov.br/
- Uso: renda, trabalho, demografia, estrutura produtiva e series historicas adicionais.

2. SENATRAN (frota por municipio)
- Impacto: alto
- Esforco: baixo
- Granularidade: municipal
- Link: https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2025
- Uso: motorizacao, combustivel, perfil de frota e pressao de mobilidade.

3. SEJUSP-MG (criminalidade por municipio)
- Impacto: alto
- Esforco: baixo/medio
- Granularidade: municipal
- Link: https://www.seguranca.mg.gov.br/index.php/transparencia/dados-abertos
- Uso: crimes violentos, roubos, furtos e dinamica de seguranca local.

4. OpenDataSUS SIOPS (expansao fiscal de saude)
- Impacto: alto
- Esforco: medio
- Granularidade: municipal
- Link: https://dadosabertos.saude.gov.br/dataset/siops
- Uso: despesa e indicadores orcamentarios de saude por periodo.

5. INEP Censo Escolar (microdados)
- Impacto: alto
- Esforco: medio
- Granularidade: escola -> agregacao municipal
- Link: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar
- Uso: matriculas, docentes, infraestrutura escolar, rendimento e distorcoes.

### Onda B (alto impacto + medio esforco)

6. SINISA/SNIS (saneamento)
- Impacto: alto
- Esforco: medio
- Granularidade: municipal
- Link: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/snis/area-do-prestador-e-municipios
- Uso: agua, esgoto, residuos e drenagem.

7. INMET (dados meteorologicos historicos)
- Impacto: alto
- Esforco: medio
- Granularidade: estacao -> agregacao municipal
- Link: https://portal.inmet.gov.br/servicos/bdmep-dados-historicos
- Uso: chuva, temperatura, extremos e sazonalidade climatica.

8. INPE Queimadas (focos/area queimada/risco)
- Impacto: alto
- Esforco: medio
- Granularidade: ponto/poligono -> agregacao municipal
- Link: https://data.inpe.br/queimadas/dados-abertos/
- Uso: risco ambiental e pressao sobre territorio.

9. ANA Dados Abertos (hidrologia e chuva)
- Impacto: medio/alto
- Esforco: medio
- Granularidade: estacao -> agregacao municipal/regional
- Link: https://www.gov.br/ana/pt-br/acesso-a-informacao/dados-abertos
- Uso: nivel/vazao/chuva para contexto hidrico e risco hidrologico.

### Onda C (alto potencial + maior acoplamento de negocio)

10. ANATEL Dados Abertos (conectividade)
- Impacto: alto
- Esforco: medio/alto
- Granularidade: varia por conjunto (alguns municipais)
- Link: https://www.gov.br/anatel/pt-br/dados/dados-abertos
- Uso: banda larga fixa/movel, cobertura e inclusao digital.

11. ANEEL Dados Abertos (energia)
- Impacto: alto
- Esforco: medio/alto
- Granularidade: varia por conjunto
- Link: https://dadosabertos.aneel.gov.br/
- Uso: distribuicao, qualidade de fornecimento e indicadores setoriais.

12. CECAD / CadUnico agregado
- Impacto: alto
- Esforco: alto (acesso e governanca)
- Granularidade: municipal/agregada
- Link: https://cecad.cidadania.gov.br/sobre.php
- Uso: vulnerabilidade social, perfil de renda e familias.
- Observacao: dados completos podem exigir fluxo formal de acesso/governanca.

13. Censo SUAS
- Impacto: medio/alto
- Esforco: medio/alto
- Granularidade: municipal/unidade
- Link: https://www.gov.br/mds/pt-br/acoes-e-programas/suas/gestao-do-suas/vigilancia-socioassistencial-1/censo-suas
- Uso: capacidade instalada de assistencia social (CRAS/CREAS etc.).

## 4) Modelo de dados futuro sugerido

Novas tabelas Silver recomendadas:
- `silver.fact_public_safety`
- `silver.fact_sanitation`
- `silver.fact_health_finance`
- `silver.fact_climate_daily`
- `silver.fact_environment`
- `silver.fact_mobility_fleet`
- `silver.fact_connectivity`
- `silver.fact_energy`
- `silver.fact_social_protection`

Padrao minimo por fato:
- `territory_id` (FK em `silver.dim_territory`)
- `reference_period`
- `indicator_code`
- `value`
- `source`
- `metadata_json`

## 5) Plano de integracao futura (sem bloquear o frontend atual)

Sprint P1 (2 semanas):
1. SIDRA + SENATRAN + SEJUSP-MG.
2. Contratos de qualidade e thresholds por fonte.
3. Backfill de 3-5 anos quando houver historico.

Sprint P2 (2 semanas):
1. SIOPS + Censo Escolar + SINISA/SNIS.
2. Novos endpoints internos para consumo da camada analitica/frontend.
3. Marts Gold iniciais por dominio social e infraestrutura.

Sprint P3 (2 semanas):
1. INMET + INPE + ANA.
2. Agregacao geoespacial por municipio.
3. Alertas de variacao anomala em indicadores ambientais.

Sprint P4 (2 semanas):
1. ANATEL + ANEEL + CECAD + Censo SUAS.
2. Score territorial multipilar consolidado.
3. Hardening de qualidade, performance e operacao.

## 6) Riscos principais e mitigacao

1. Mudanca de layout/formato dos datasets.
- Mitigacao: contrato de schema por versao + teste de contrato por conector.

2. Fonte sem API estavel (download manual em portal web).
- Mitigacao: parser resiliente + fallback controlado + alerta de quebra.

3. Restricao de acesso/governanca (especialmente social).
- Mitigacao: trilha de acesso formal, segregacao de dados, compliance e auditoria.

4. Diferentes frequencias de atualizacao.
- Mitigacao: `source_updated_at` + semaforo de frescor por indicador no frontend.

## 7) Criterio de aceite para cada nova fonte

1. Conector idempotente com `dry_run=True` sem escrita.
2. Persistencia Bronze com manifesto e checksum.
3. Carga Silver com `territory_id` resolvido.
4. Check de qualidade ativo em `configs/quality_thresholds.yml`.
5. Logs em `ops.pipeline_runs` e `ops.pipeline_checks`.
6. Endpoint/API interno pronto para consumo sem SQL manual.
