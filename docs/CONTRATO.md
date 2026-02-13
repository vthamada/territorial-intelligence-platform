# Contrato Técnico do Sistema

Data de referência: 2026-02-10  
Status: ativo  
Fonte suprema de requisitos técnicos e critérios de aceite do produto.

## 1) Objetivo do sistema

Construir e operar uma plataforma reprodutível de inteligência territorial para Diamantina/MG, com:
- ingestão automatizada de fontes públicas oficiais
- integração territorial padronizada
- disponibilização de dados para análise via API e camada analítica
- interface frontend para consumo operacional e analítico dos dados
- observabilidade e qualidade operacional em nível de produção

## 2) Escopo territorial oficial

- Município-alvo: Diamantina/MG
- Código IBGE oficial do município: `3121605`
- Níveis territoriais suportados:
  - `municipality`
  - `district`
  - `census_sector` (quando disponível)
  - `electoral_zone` (quando disponível)
  - `electoral_section` (quando disponível)

## 3) Princípios obrigatórios

1. Ingestão manual recorrente é proibida.
2. Pipeline deve ser idempotente e reexecutável.
3. Bronze é imutável por timestamp de extração.
4. Todo artefato deve gerar manifesto e checksum.
5. `dry_run=True` não escreve em Bronze nem banco.
6. Dados técnicos em inglês; conteúdo de negócio pode manter idioma da fonte.
7. Toda execução deve registrar metadados em `ops.pipeline_runs` e checks em `ops.pipeline_checks`.

## 4) Arquitetura de dados

Camadas:
- Bronze: artefatos raw versionados
- Silver: dados normalizados e relacionáveis
- Gold: visões/marts analíticos

Padrões de path:
- `data/bronze/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}/`
- `data/manifests/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}.yml`

Banco:
- PostgreSQL + PostGIS
- Schemas principais: `silver`, `gold`, `ops`

## 5) Modelo de dados mínimo (contrato)

Silver:
- `silver.dim_territory`
  - inclui `canonical_key`, `source_system`, `source_entity_id`, `normalized_name`
- `silver.dim_time`
- `silver.fact_indicator`
- `silver.fact_electorate`
- `silver.fact_election_result`

Ops:
- `ops.pipeline_runs`
- `ops.pipeline_checks`
- `ops.connector_registry`

Status de conector permitidos:
- `implemented`, `partial`, `blocked`, `planned`

## 6) Contrato de API

Base versionada:
- `/v1`

Contrato de erro obrigatório:
```json
{
  "error": {
    "code": "validation_error|http_error|internal_error",
    "message": "human readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

Regras:
- toda resposta deve incluir header `x-request-id`
- paginação e filtros explícitos em endpoints listáveis

Endpoints mínimos de domínio:
- `GET /v1/territories`
- `GET /v1/territories/{id}`
- `GET /v1/indicators`
- `GET /v1/electorate`
- `GET /v1/elections/results`
- `GET /v1/geo/choropleth`

Endpoints operacionais:
- `GET /v1/ops/pipeline-runs`
- `GET /v1/ops/pipeline-checks`
- `GET /v1/ops/connector-registry`
- `GET /v1/ops/summary`
- `GET /v1/ops/timeseries`
- `GET /v1/ops/sla`

## 7) Contrato de frontend

Objetivo:
- disponibilizar interface web para operação e exploração dos dados sem dependência de SQL manual.

Escopo funcional mínimo:
1. Tela de saúde operacional:
- consumo de `/v1/health`, `/v1/ops/summary`, `/v1/ops/sla`, `/v1/ops/timeseries`
2. Tela de execução de pipelines:
- listagem e filtros via `/v1/ops/pipeline-runs`
- detalhe de checks via `/v1/ops/pipeline-checks`
3. Tela territorial/indicadores:
- consulta de territórios e indicadores com filtros por período e nível territorial

Requisitos de qualidade:
- responsivo (desktop e mobile)
- tratamento consistente de erro com `request_id`
- estado de carregamento e vazio em todas as telas de dados
- configuração de URL da API via variável de ambiente

Stack oficial:
- React + Vite + TypeScript
- React Router para navegação
- TanStack Query para cache e sincronização de dados remotos
- cliente HTTP com timeout e retry leve para leitura
- Vitest + Testing Library para testes unitários e de integração de UI

Contrato de integração frontend/API:
- o frontend não pode acessar banco diretamente
- toda leitura de dados deve passar pelos endpoints `/v1`
- tratamento de erro deve exibir `error.message` e `error.request_id`
- filtros e paginação devem respeitar os contratos:
  - `/v1/ops/pipeline-runs`: `job_name`, `run_status`, `wave`, `started_from`, `started_to`, `page`, `page_size`
  - `/v1/ops/pipeline-checks`: `job_name`, `status`, `check_name`, `created_from`, `created_to`, `page`, `page_size`
  - `/v1/ops/connector-registry`: `connector_name`, `status`, `wave`, `updated_from`, `updated_to`, `page`, `page_size`

## 8) Contratos de ingestão por fonte

IBGE:
- descoberta automática de distritos
- malhas com recorte territorial e validação geométrica
- indicadores por catálogo configurável

TSE:
- discovery via CKAN
- download + parse + carga eleitoral/resultados
- filtro territorial MG + Diamantina

INEP / DATASUS / SICONFI:
- ingestão automatizada por API/arquivo oficial
- filtro para município-alvo
- carga em `silver.fact_indicator`

MTE:
- objetivo final: ingestão automatizada sem ação manual recorrente
- qualquer exceção operacional temporária deve ser registrada em `HANDOFF.md`

## 9) Contrato de qualidade de dados

Regras:
- checks com `observed_value`, `threshold_value`, `status` (`pass|warn|fail`)
- thresholds em `configs/quality_thresholds.yml`

Mínimo por tabela:
- `dim_territory`: município existe, distritos mínimos, geometria válida
- `fact_electorate`: não-negativo, referência preenchida, território resolvido
- `fact_election_result`: não-negativo, referência preenchida, território resolvido
- `fact_indicator`: código/referência/valor/território válidos

## 10) Contrato de orquestração

Parâmetros obrigatórios por job:
- `reference_period`
- `force`
- `dry_run`
- `max_retries`
- `timeout_seconds`

Job `dbt_build`:
- `DBT_BUILD_MODE=auto|dbt|sql_direct`
- `auto`: tenta dbt CLI e cai para `sql_direct` se necessário
- `dbt`: exige dbt CLI no ambiente

## 11) SLO operacional mínimo (inicial)

SLO-1: taxa de sucesso dos jobs `implemented`
- métrica: `% runs com run_status=successful`
- janela: 7 dias corridos
- alvo: `>= 95%`

SLO-2: latência de API operacional
- métrica: p95 de resposta dos endpoints `/v1/ops/*`
- janela: 7 dias
- alvo: `<= 1.5s` (sem carga de stress)

SLO-3: atualização de dados por execução
- métrica: presença de `ops.pipeline_runs` e `ops.pipeline_checks` para cada job executado
- alvo: `100%` das execuções

SLO-4: qualidade mínima
- métrica: checks críticos por tabela de fato/dimensão
- alvo: `100%` dos checks críticos em `pass` ou `warn`; `fail` requer ação corretiva registrada

## 12) Critérios finais de encerramento do sistema

O sistema é considerado finalizado quando:
1. Todos os conectores MVP estão `implemented`.
2. Pipeline completo roda sem intervenção manual recorrente.
3. API v1 está estável e aderente ao contrato.
4. Qualidade cobre tabelas críticas com thresholds ativos.
5. Frontend MVP operacional está integrado aos endpoints v1.
6. SLOs mínimos estão atendidos por janela de 7 dias.
7. Documentação e runbooks estão completos e atualizados.

## 13) Governança documental

1. Mudanças de requisito técnico devem ser feitas em `CONTRATO.md`.
2. Mudanças de execução e sequência de entregas devem ser feitas em `PLANO.md`.
3. Estado atual e decisões operacionais transitórias devem ser registradas em `HANDOFF.md`.
4. Evidências históricas e validações executadas devem ser registradas em `CHANGELOG.md`.
