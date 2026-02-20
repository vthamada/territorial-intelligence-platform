# Pacote de Issues - Backlog Dados Nivel Maximo

Data de referencia: 2026-02-18  
Origem: `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`
Status deste documento: snapshot historico de criacao de issues.

> Fonte oficial de status das tarefas: GitHub Issues/Projects.  
> Os checklists deste arquivo podem estar defasados e devem ser usados apenas como referencia de escopo inicial.

## Como usar
1. Crie labels (se ainda nao existirem):
   - `area:data`
   - `type:feature`
   - `type:infra`
   - `type:quality`
   - `type:docs`
   - `priority:p0`
   - `priority:p1`
   - `priority:p2`
   - `sprint:D0` ate `sprint:D8`
2. Abra as issues abaixo mantendo o `ID` no inicio do titulo.
3. Respeite as dependencias listadas em cada issue.

## Sprint D0

### BD-001 - Formalizar DoD de robustez maxima no contrato tecnico
- Labels: `area:data`, `type:docs`, `priority:p0`, `sprint:D0`
- Dependencias: nenhuma
- Descricao:
  - Publicar no contrato tecnico os criterios mensuraveis de "nivel maximo de dados".
  - Garantir alinhamento entre contrato, plano e handoff.
- Checklist de aceite:
  - [ ] `docs/CONTRATO.md` atualizado com DoD oficial.
  - [ ] Referencias cruzadas para `docs/BACKLOG_DADOS_NIVEL_MAXIMO.md`.
  - [ ] Revisao em `docs/CHANGELOG.md`.

### BD-002 - Publicar scorecard SQL de cobertura historica e territorial
- Labels: `area:data`, `type:infra`, `priority:p0`, `sprint:D0`
- Dependencias: BD-001
- Descricao:
  - Criar consultas SQL versionadas que mostrem cobertura por fonte, ano e nivel territorial.
  - Publicar relatorio padrao em `data/reports`.
- Checklist de aceite:
  - [ ] Script SQL versionado no repositorio.
  - [ ] Relatorio JSON com historico/territorio gerado automaticamente.
  - [ ] Campo de cobertura por `municipality|district|census_sector|electoral_zone`.

### BD-003 - Definir runbook semanal de monitoramento de robustez
- Labels: `area:data`, `type:docs`, `priority:p0`, `sprint:D0`
- Dependencias: BD-002
- Descricao:
  - Definir rotina semanal para conferir cobertura, qualidade e frescor.
  - Padronizar acao corretiva para `fail` em checks criticos.
- Checklist de aceite:
  - [ ] Runbook publicado em `docs`.
  - [ ] Passos de triagem e escalonamento descritos.
  - [ ] Frequencia e dono do processo definidos.

## Sprint D1

### BD-010 - Backfill eleitoral historico (TSE) para janela maxima disponivel
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D1`
- Dependencias: BD-002
- Descricao:
  - Expandir carga TSE para anos anteriores (ex.: 2016-2024, conforme disponibilidade CKAN).
  - Persistir artefatos Bronze + Silver com rastreabilidade completa.
- Checklist de aceite:
  - [ ] `silver.fact_electorate` com >= 5 anos distintos (quando disponivel).
  - [ ] `silver.fact_election_result` com >= 5 anos distintos (quando disponivel).
  - [ ] Relatorio de cobertura atualizado.

### BD-011 - Validar integridade de zonas eleitorais na dimensao territorial
- Labels: `area:data`, `type:quality`, `priority:p0`, `sprint:D1`
- Dependencias: BD-010
- Descricao:
  - Garantir unicidade, parent correto e consistencia de chave para `electoral_zone`.
  - Eliminar duplicidades e lacunas territoriais.
- Checklist de aceite:
  - [ ] Check de integridade de `electoral_zone` adicionado ao `quality_suite`.
  - [ ] Zero duplicidade nas chaves naturais.
  - [ ] Cobertura por zona em `pass`.

### BD-012 - Checks de continuidade temporal por fonte
- Labels: `area:data`, `type:quality`, `priority:p1`, `sprint:D1`
- Dependencias: BD-010
- Descricao:
  - Criar checks que detectem quebra de serie temporal por fonte/dominio.
  - Alertar quando anos/periodos esperados estiverem ausentes.
- Checklist de aceite:
  - [ ] Novos checks no `quality_suite`.
  - [ ] Thresholds no `configs/quality_thresholds.yml`.
  - [ ] Evidencia de execucao em `ops.pipeline_checks`.

## Sprint D2

### BD-020 - Implementar conector CECAD/CadUnico agregado
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D2`
- Dependencias: BD-001
- Descricao:
  - Implementar ingestao social agregada com foco municipal.
  - Respeitar requisitos de governanca e acesso.
- Checklist de aceite:
  - [ ] Conector com `dry_run` e idempotencia.
  - [ ] Bronze + manifesto + checksum.
  - [ ] Carga Silver com `territory_id` resolvido.

### BD-021 - Implementar conector Censo SUAS
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D2`
- Dependencias: BD-020
- Descricao:
  - Integrar capacidade de rede socioassistencial (CRAS, CREAS etc.).
  - Mapear dados para consumo analitico territorial.
- Checklist de aceite:
  - [ ] Conector em status `implemented`.
  - [ ] Dados carregados na Silver com chaves territoriais.
  - [ ] Checks de qualidade ativos.

### BD-022 - Criar fatos sociais dedicados na Silver
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D2`
- Dependencias: BD-020, BD-021
- Descricao:
  - Criar tabelas dedicadas:
    - `silver.fact_social_protection`
    - `silver.fact_social_assistance_network`
  - Reduzir sobrecarga semantica em `fact_indicator`.
- Checklist de aceite:
  - [ ] Migrations SQL publicadas.
  - [ ] Upsert idempotente nas novas tabelas.
  - [ ] Testes de contrato SQL adicionados.

## Sprint D3

### BD-030 - Integrar base de vias/logradouros para camada urbana
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D3`
- Dependencias: BD-002
- Descricao:
  - Ingerir vias e logradouros (OSM/IBGE/local) com indexacao espacial.
  - Preparar camadas para tile vetorial.
- Checklist de aceite:
  - [ ] Camada de vias carregada e consultavel.
  - [ ] Indices espaciais criados.
  - [ ] Endpoint de consulta por bbox funcional.

### BD-031 - Integrar POIs essenciais (saude, educacao, seguranca, assistencia)
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D3`
- Dependencias: BD-030
- Descricao:
  - Criar dataset de pontos de interesse com categoria padronizada.
  - Garantir georreferenciamento valido.
- Checklist de aceite:
  - [ ] POIs carregados e categorizados.
  - [ ] Validacao geometrica sem `fail`.
  - [ ] Endpoint para filtro por categoria.

### BD-032 - Camada de geocodificacao local e busca espacial
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D3`
- Dependencias: BD-030, BD-031
- Descricao:
  - Implementar lookup por endereco/logradouro e busca por proximidade.
  - Basear em indices espaciais e normalizacao textual.
- Checklist de aceite:
  - [ ] Endpoint de geocodificacao funcional.
  - [ ] Consulta por raio e bbox com p95 < 1.0s.
  - [ ] Testes de API e performance basica.

## Sprint D4

### BD-040 - Expandir serie historica de mobilidade/frota (SENATRAN)
- Labels: `area:data`, `type:feature`, `priority:p1`, `sprint:D4`
- Dependencias: BD-012
- Descricao:
  - Ampliar anos e categorias de frota para analise longitudinal.
- Checklist de aceite:
  - [ ] Minimo de 5 anos carregados (quando disponivel).
  - [ ] Indicadores por categoria de frota validados.
  - [ ] Checks temporais em `pass`.

### BD-041 - Integrar dados viarios/transportes locais (se disponiveis)
- Labels: `area:data`, `type:feature`, `priority:p1`, `sprint:D4`
- Dependencias: BD-030
- Descricao:
  - Ingerir camadas locais de transporte para contextualizar acesso e deslocamento.
- Checklist de aceite:
  - [ ] Fontes locais catalogadas e versionadas.
  - [ ] Ingestao idempotente com Bronze+Silver.
  - [ ] Mapeamento territorial validado.

### BD-042 - Criar mart Gold de mobilidade e acesso territorial
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D4`
- Dependencias: BD-040, BD-041
- Descricao:
  - Construir `gold.mart_mobility_access` para consumo de prioridades.
- Checklist de aceite:
  - [ ] Mart Gold materializado.
  - [ ] Query de consumo no backend validada.
  - [ ] Teste de contrato e regressao adicionado.

## Sprint D5

### BD-050 - Expandir historico INMET/INPE/ANA multi-ano
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D5`
- Dependencias: BD-012
- Descricao:
  - Backfill ambiental e climatico para janela historica longa.
- Checklist de aceite:
  - [ ] Minimo de 5 anos por fonte (quando disponivel).
  - [ ] Cobertura temporal em `pass`.
  - [ ] Relatorio de cobertura atualizado.

### BD-051 - Agregacoes ambientais por distrito e setor censitario
- Labels: `area:data`, `type:feature`, `priority:p0`, `sprint:D5`
- Dependencias: BD-050
- Descricao:
  - Projetar dados ambientais para niveis territoriais finos.
- Checklist de aceite:
  - [ ] Indicadores por `district` e `census_sector`.
  - [ ] Qualidade territorial sem `fail`.
  - [ ] Endpoints consumindo os novos niveis.

### BD-052 - Criar mart Gold de risco ambiental territorial
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D5`
- Dependencias: BD-050, BD-051
- Descricao:
  - Construir `gold.mart_environment_risk` com score e drivers.
- Checklist de aceite:
  - [ ] Mart Gold pronto e versionado.
  - [ ] Base de explicabilidade documentada.
  - [ ] Consumo no QG validado.

## Sprint D6

### BD-060 - Versionar contratos de schema por fonte
- Labels: `area:data`, `type:quality`, `priority:p0`, `sprint:D6`
- Dependencias: BD-022
- Descricao:
  - Definir contrato de schema para cada conector e versao.
- Checklist de aceite:
  - [ ] Contratos de schema em arquivo versionado.
  - [ ] Validacao automatica em runtime.
  - [ ] Falhas de schema registradas em ops checks.

### BD-061 - Cobertura de testes de contrato por conector
- Labels: `area:data`, `type:quality`, `priority:p0`, `sprint:D6`
- Dependencias: BD-060
- Descricao:
  - Garantir suite de testes de contrato para conectores implementados.
- Checklist de aceite:
  - [ ] Cobertura >= 90% dos conectores.
  - [ ] Pipeline CI executando testes de contrato.
  - [ ] Evidencia no changelog.

### BD-062 - Detectar drift de schema com alerta operacional
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D6`
- Dependencias: BD-060
- Descricao:
  - Detectar alteracao de layout de fonte e alertar automaticamente.
- Checklist de aceite:
  - [ ] Check de drift ativo.
  - [ ] Alerta com contexto de fonte/campo.
  - [ ] Registro de incidentes em runbook.

## Sprint D7

### BD-070 - Construir mart Gold de drivers de prioridade
- Labels: `area:data`, `type:feature`, `priority:p1`, `sprint:D7`
- Dependencias: BD-042, BD-052
- Descricao:
  - Consolidar drivers por dominio para alimentar ranking e insights.
- Checklist de aceite:
  - [ ] `gold.mart_priority_drivers` publicado.
  - [ ] API consumindo mart sem SQL ad-hoc.
  - [ ] Teste de regressao de ranking.

### BD-071 - Versionar score territorial e pesos por referencia
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D7`
- Dependencias: BD-070
- Descricao:
  - Garantir reproducibilidade de score por periodo.
- Checklist de aceite:
  - [ ] Tabela/versionamento de pesos implementado.
  - [ ] Reproducao deterministica validada.
  - [ ] Auditoria de alteracao de pesos registrada.

### BD-072 - Trilhas de explicabilidade para prioridade/insight
- Labels: `area:data`, `type:feature`, `priority:p1`, `sprint:D7`
- Dependencias: BD-070, BD-071
- Descricao:
  - Expor evidencias e racional por prioridade no backend/frontend.
- Checklist de aceite:
  - [ ] Cada prioridade aponta para evidencias concretas.
  - [ ] Endpoint de explicabilidade validado.
  - [ ] UI exibindo racional de forma auditavel.

## Sprint D8

### BD-080 - Carga incremental com reprocessamento seletivo
- Labels: `area:data`, `type:infra`, `priority:p0`, `sprint:D8`
- Dependencias: BD-061
- Descricao:
  - Implementar estrategia de incremental + replay por periodo/fonte.
- Checklist de aceite:
  - [ ] Reprocessamento seletivo funcional.
  - [ ] Sem duplicidade de fatos apos replay.
  - [ ] Evidencia operacional em `ops.pipeline_runs`.

### BD-081 - Tuning de performance e custo da plataforma de dados
- Labels: `area:data`, `type:infra`, `priority:p1`, `sprint:D8`
- Dependencias: BD-080
- Descricao:
  - Revisar indices, particionamento e materialized views criticas.
- Checklist de aceite:
  - [ ] p95 das queries criticas dentro da meta.
  - [ ] Plano de custo/execucao documentado.
  - [ ] Regressao de performance monitorada.

### BD-082 - Playbook de incidentes e operacao assistida
- Labels: `area:data`, `type:docs`, `priority:p1`, `sprint:D8`
- Dependencias: BD-080, BD-081
- Descricao:
  - Fechar operacao assistida com fluxo de incidentes e continuidade.
- Checklist de aceite:
  - [ ] Playbook publicado e validado.
  - [ ] SLOs atendidos por 30 dias corridos.
  - [ ] Fechamento documentado em `docs/HANDOFF.md` e `docs/CHANGELOG.md`.
