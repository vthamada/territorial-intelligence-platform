# SPEC ROBUSTO (AGENT-READY)
> Addendum ativo: SPEC_v1.3.md (ondas de MVP, API /v1, thresholds de qualidade, observabilidade em banco, naming em ingles).
Plataforma de InteligÃªncia Territorial â€“ Diamantina/MG (MunicÃ­pio + Distritos)

VersÃ£o: 1.2.0  
Status: Ativo (Contrato de ImplementaÃ§Ã£o)  
Data: 2026-02-08  
Escopo: Engenharia de dados + API + Observabilidade (foco em extraÃ§Ã£o automatizada e reprodutÃ­vel)

---

## 1. Objetivo

Construir um sistema reprodutÃ­vel e automatizado para:
- extrair, versionar e validar dados pÃºblicos oficiais
- integrar territorialmente (municÃ­pio + distritos + setores censitÃ¡rios + zonas/seÃ§Ãµes eleitorais quando disponÃ­veis)
- servir dados normalizados/analÃ­ticos via PostGIS + API para dashboards e anÃ¡lises

O sistema deve ser â€œagent-readyâ€: um agente (Copilot/Codex/Claude Code etc.) consegue implementar os conectores e pipelines apenas lendo este documento, sem inferir regras nÃ£o descritas.

---

## 2. Escopo territorial (hard constraints)

### 2.1 MunicÃ­pio alvo
- MunicÃ­pio: Diamantina
- UF: MG
- geocodigo_ibge_municipio: 3121606

### 2.2 Distritos
- O sistema NÃƒO deve usar listas â€œmanuaisâ€ de distritos.
- A lista oficial de distritos DEVE ser obtida automaticamente a partir de fonte IBGE (Localidades / DivisÃ£o Administrativa).
- Cada distrito deve possuir identificador persistente (chave) e vÃ­nculo ao municÃ­pio 3121606.

### 2.3 NÃ­veis territoriais suportados
- municipio (obrigatÃ³rio)
- distrito (obrigatÃ³rio)
- setor_censitario (obrigatÃ³rio quando houver geometria e/ou indicadores)
- zona_eleitoral (quando existir em TSE e for publicamente disponÃ­vel)
- secao_eleitoral (quando existir em TSE e for publicamente disponÃ­vel)

---

## 3. Regras gerais (normas do sistema)

### 3.1 ProibiÃ§Ã£o de ingestÃ£o manual recorrente
- Downloads manuais recorrentes sÃ£o proibidos.
- Admitido apenas: seed inicial de credenciais/variÃ¡veis em `.env` (se aplicÃ¡vel) e setup de banco.

### 3.2 Reprodutibilidade total
O pipeline deve ser capaz de:
- recriar o banco e todas as camadas a partir do zero
- reexecutar idempotentemente (re-runs nÃ£o duplicam registros)

### 3.3 PreservaÃ§Ã£o do bruto
- Toda extraÃ§Ã£o deve ser salva em BRONZE exatamente como recebido (raw).
- BRONZE Ã© imutÃ¡vel por versÃ£o.

### 3.4 Versionamento
- Toda base deve ser versionada por:
  - `source`
  - `dataset`
  - `reference_period` (ano/mÃªs/data conforme fonte)
  - `extracted_at` (timestamp UTC)
  - `checksum_sha256` (do artefato bruto)

### 3.5 Observabilidade mÃ­nima obrigatÃ³ria
Cada job deve registrar:
- inÃ­cio/fim, duraÃ§Ã£o, status
- contagem de linhas extraÃ­das (quando aplicÃ¡vel)
- checksum do bruto
- quantidade carregada no Silver/Gold
- warnings e erros (com stacktrace)
- link/caminho para artefatos BRONZE

### 3.6 Ã‰tica/privacidade
- NÃ£o ingerir dados pessoais identificÃ¡veis (PII) se houver risco de identificaÃ§Ã£o individual.
- Se alguma fonte contiver microdados, o pipeline deve agregar/anonimizar conforme spec da fonte e registrar no manifesto.

---

## 4. Arquitetura de dados (camadas)

### 4.1 Layout de armazenamento (sugestÃ£o obrigatÃ³ria de paths)
- `data/bronze/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}/file.ext`
- `data/manifests/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}.yml`
- `data/silver/` (opcional para parquet intermediÃ¡rio)
- Postgres/PostGIS para Silver/Gold

### 4.2 Camadas
- BRONZE: arquivos raw (csv/json/zip/shp/gpkg)
- SILVER: tabelas normalizadas, chaves padronizadas, tipos corretos
- GOLD: marts analÃ­ticos (agregaÃ§Ãµes, indicadores derivados, views/materialized views)

---

## 5. Manifesto padrÃ£o (obrigatÃ³rio)

Todo job de extraÃ§Ã£o DEVE produzir manifesto YAML:

```yaml
source: <IBGE|TSE|INEP|DATASUS|SICONFI|MTE|OUTRO>
dataset: <nome_dataset>
dataset_version: <quando houver no catÃ¡logo da fonte>
territory_ibge_code: 3121606
territory_scope: <municipio|distrito|setor_censitario|zona_eleitoral|secao_eleitoral|mixed>
reference_period: <YYYY|YYYY-MM|YYYY-MM-DD|custom>
extracted_at_utc: <ISO-8601>
raw:
  format: <csv|json|zip|shp|gpkg|parquet>
  uri: <url_origem>
  local_path: <path_no_repositorio_ou_storage>
  size_bytes: <int>
  checksum_sha256: <hash>
ingestion:
  tool: <python>
  orchestrator: <prefect|dagster|airflow|cron>
  pipeline_version: <semver>
  run_id: <uuid>
validation:
  schema_version: <semver>
  checks:
    - name: <check_name>
      status: <pass|fail|warn|skip>
      details: <text>
load:
  destination: <postgresql://...>
  tables_written:
    - <schema.table>
  rows_written:
    - table: <schema.table>
      rows: <int>
notes: <texto livre>
```

---

## 6. PadrÃµes de implementaÃ§Ã£o (para o agente)

### 6.1 Linguagem e libs
- Python 3.11+
- HTTP: `httpx` (preferÃ­vel) ou `requests`
- Data: `pandas`, `pyarrow` (opcional)
- Geodados: `geopandas`, `shapely`, `pyogrio` (preferÃ­vel) ou `fiona`
- DB: `sqlalchemy` + `psycopg`
- Config: `pydantic-settings` ou `python-dotenv`
- Logging: `structlog` ou logging padrÃ£o com JSON formatter

### 6.2 Robustez de rede
- retry com exponential backoff
- timeouts explÃ­citos
- validaÃ§Ã£o de content-type e tamanho mÃ­nimo do arquivo
- suporte a resume download (quando possÃ­vel)

### 6.3 IdempotÃªncia
- BRONZE: pasta por `extracted_at` + checksum
- SILVER/GOLD: UPSERT por chaves naturais ou `merge` por staging tables
- ReexecuÃ§Ã£o do mesmo `run_id` nÃ£o deve duplicar

### 6.4 SeguranÃ§a
- credenciais por variÃ¡veis de ambiente (nunca hardcode)
- bloquear escrita fora de `data/` e do banco

---

## 7. Modelo de dados (SILVER) â€“ contratos essenciais

### 7.1 dim_territorio (obrigatÃ³ria)
Representa hierarquia territorial unificada.

Campos:
- territory_id (UUID, PK)
- level (enum: municipio|distrito|setor_censitario|zona_eleitoral|secao_eleitoral)
- parent_territory_id (UUID, FK self)
- ibge_geocode (string, nullable; obrigatÃ³rio para municipio/distrito/setor)
- tse_zone (string, nullable)
- tse_section (string, nullable)
- name (string)
- uf (string, nullable)
- municipality_ibge_geocode (string, obrigatÃ³rio para todos os nÃ­veis do escopo)
- valid_from (date, nullable)
- valid_to (date, nullable)
- geometry (PostGIS geometry, nullable; obrigatÃ³rio para municipio/distrito/setor quando disponÃ­vel)

Chaves/constraints:
- unique(level, ibge_geocode, tse_zone, tse_section, municipality_ibge_geocode)

### 7.2 dim_tempo (recomendado)
- date_id (date, PK)
- year (int)
- month (int)
- day (int)
- reference_period (string)

### 7.3 fact_indicador (padrÃ£o long)
Tabela genÃ©rica para indicadores (IBGE, saÃºde, educaÃ§Ã£o, finanÃ§as).

Campos:
- fact_id (UUID, PK)
- territory_id (UUID, FK)
- source (string)
- dataset (string)
- indicator_code (string)
- indicator_name (string)
- unit (string, nullable)
- category (string, nullable)
- value (numeric)
- reference_period (string)
- updated_at (timestamp)

Chaves/constraints:
- unique(territory_id, source, dataset, indicator_code, category, reference_period)

### 7.4 fact_eleitorado (TSE)
Campos:
- territory_id (FK para municipio/zona/secao)
- reference_year (int)
- sex (string, nullable)
- age_range (string, nullable)
- education (string, nullable)
- voters (int)

Chaves:
- unique(territory_id, reference_year, sex, age_range, education)

### 7.5 fact_resultado_eleitoral (TSE)
Campos:
- territory_id (FK para municipio/zona/secao)
- election_year (int)
- election_round (int, nullable)
- office (string, nullable)
- metric (string: votes_valid|votes_null|votes_blank|turnout|abstention|etc)
- value (numeric)

Chaves:
- unique(territory_id, election_year, election_round, office, metric)

---

## 8. FONTES E DATASETS (extraÃ§Ã£o automatizada)

### 8.1 IBGE â€“ Localidades (descoberta de distritos e metadados administrativos)
Objetivo:
- Obter distritos oficiais vinculados ao municÃ­pio 3121606
- Popular `dim_territorio` (level=distrito) e `dim_territorio_admin` (se usar)

MÃ©todo:
- API REST (JSON)

Requisitos do conector:
- O conector deve aceitar `municipality_ibge_geocode=3121606`
- Deve registrar o payload bruto em BRONZE
- Deve produzir lista de distritos com IDs e nomes (e, se existir, geocÃ³digos especÃ­ficos)

ValidaÃ§Ãµes mÃ­nimas:
- MunicÃ­pio retornado deve ser 3121606
- Pelo menos 1 distrito retornado (warn se 0)

Output Silver:
- upsert em `dim_territorio` (municipio e distritos)

### 8.2 IBGE â€“ Malhas territoriais (geometrias)
Objetivo:
- Obter geometrias oficiais para:
  - municÃ­pio
  - distritos (se disponÃ­vel)
  - setores censitÃ¡rios (se disponÃ­vel)

MÃ©todo:
- Download automatizado (HTTP/FTP)
- Import para PostGIS

Requisitos:
- Converter para CRS padrÃ£o do sistema: EPSG:4674 (SIRGAS 2000) OU EPSG:4326 (WGS84). Escolher UM e manter consistente.
- Validar geometria (make_valid quando necessÃ¡rio)
- Cortar/filtrar para municÃ­pio 3121606 e seus distritos/setores

ValidaÃ§Ãµes:
- geometry nÃ£o vazia
- Ã¡rea > 0
- municÃ­pio deve existir

Output Silver:
- `dim_territorio.geometry` preenchida para nÃ­veis suportados

### 8.3 IBGE â€“ Indicadores (Censo, PIB, etc.)
Objetivo:
- Extrair indicadores municipais e, quando existir, por setores/distritos
- Carregar em `fact_indicador` no formato long

MÃ©todo:
- APIs IBGE (JSON) sempre que possÃ­vel
- Caso nÃ£o haja API para um indicador especÃ­fico, usar download automatizado de arquivo oficial

Requisitos do conector:
- Deve suportar â€œcatÃ¡logo de indicadoresâ€ configurÃ¡vel em YAML:
  - indicator_code
  - endpoint/url
  - unit
  - periodicity
  - level (municipio/distrito/setor)
  - transform_rules (mapeamentos)

ValidaÃ§Ãµes:
- value numÃ©rico
- reference_period vÃ¡lido
- territory_id resolvido

Output Silver:
- upsert em `fact_indicador`

### 8.4 TSE â€“ CatÃ¡logo e downloads (CKAN)
Objetivo:
- Descobrir automaticamente os recursos corretos (CSV/ZIP) no portal de dados abertos
- Baixar eleitorado e resultados eleitorais

MÃ©todo:
- Usar API do catÃ¡logo (CKAN) para encontrar:
  - dataset â€œEleitoradoâ€ por ano
  - dataset â€œResultadosâ€ por ano
  - recursos (resources) com URLs de download

Requisitos do conector:
- Implementar etapa de DISCOVERY:
  - input: `dataset_slug` (ex: eleitorado-YYYY) OU busca por tags/ano
  - output: lista de resources com url, formato, tamanho, last_modified
- Implementar etapa de DOWNLOAD:
  - baixar resource
  - salvar BRONZE e manifesto
- Implementar etapa de PARSE:
  - extrair zip (se aplicÃ¡vel)
  - padronizar encoding
  - mapear colunas para contrato do Silver

Filtros do processamento:
- UF=MG
- MunicÃ­pio=Diamantina ou cÃ³digo municipal correspondente (quando disponÃ­vel no arquivo)
- Se houver zona/secao, manter para drill-down

ValidaÃ§Ãµes mÃ­nimas:
- ano no arquivo deve bater com ano da extraÃ§Ã£o
- voters >= 0
- municÃ­pio resolvido para 3121606
- se houver zona/secao: valores nÃ£o vazios apÃ³s filtro

Output Silver:
- `fact_eleitorado`
- `fact_resultado_eleitoral`
- atualizar `dim_territorio` para nÃ­veis zona/secao com parent correto (municipio ou distrito quando houver mapeamento)

### 8.5 INEP â€“ EducaÃ§Ã£o (Censo Escolar / indicadores agregados)
Objetivo:
- Extrair dados agregados (preferÃ­vel) e/ou microdados se houver risco de PII (nesse caso, agregar)
- Popular `fact_indicador` com indicadores educacionais

MÃ©todo:
- Download automatizado de arquivos oficiais (CSV/ZIP) ou API quando disponÃ­vel

Filtros:
- municÃ­pio 3121606

ValidaÃ§Ãµes:
- contagens nÃ£o negativas
- anos coerentes
- territÃ³rio resolvido

### 8.6 DATASUS / SaÃºde
Objetivo:
- Extrair dados agregados municipais (evitar PII)
- Ex: estabelecimentos, internaÃ§Ãµes agregadas, mortalidade agregada

MÃ©todo:
- API/FTP automatizado conforme disponibilidade da fonte

Filtros:
- municÃ­pio 3121606 (ou cÃ³digo compatÃ­vel da fonte)

ValidaÃ§Ãµes:
- valores nÃ£o negativos
- consistÃªncia temporal

### 8.7 SICONFI â€“ FinanÃ§as municipais
Objetivo:
- Receita/despesa/investimento municipal por ano

MÃ©todo:
- API do Tesouro/SICONFI (quando disponÃ­vel)

Filtros:
- municÃ­pio 3121606
- anos configurÃ¡veis

ValidaÃ§Ãµes:
- numÃ©ricos e nÃ£o negativos quando aplicÃ¡vel

### 8.8 MTE (RAIS/CAGED) â€“ Trabalho
Objetivo:
- Emprego formal e remuneraÃ§Ã£o agregada

MÃ©todo:
- Download automatizado de arquivos pÃºblicos ou API, conforme disponibilidade

Filtros:
- municÃ­pio 3121606

ValidaÃ§Ãµes:
- valores nÃ£o negativos
- anos coerentes

---

## 9. IntegraÃ§Ã£o territorial (regras de matching)

### 9.1 Regra geral
Toda entidade territorial deve ser resolvida para `dim_territorio.territory_id`.

### 9.2 Matching IBGE
- municÃ­pio/distrito/setor devem ser vinculados via `ibge_geocode`
- se o dado vier com nome apenas, tentar resolver por:
  - (uf, municÃ­pio, nome normalizado) com fallback para lista oficial
  - se ambÃ­guo, FAIL com erro explÃ­cito

### 9.3 Matching TSE
- zona/secao devem existir como nÃ­vel prÃ³prio, vinculados ao municÃ­pio
- se existir mapeamento para distrito (raro/complexo), isso Ã© FUTURO; no MVP, parent de zona/secao Ã© municÃ­pio

---

## 10. Qualidade de dados (checks obrigatÃ³rios por tabela)

### 10.1 dim_territorio
- municipio 3121606 existe (fail se nÃ£o)
- pelo menos 1 distrito (warn se nÃ£o)
- geometria vÃ¡lida quando carregada (warn se invÃ¡lida e corrigida)

### 10.2 fact_eleitorado
- voters >= 0 (fail se negativo)
- reference_year preenchido (fail se nulo)
- territory_id resolvido (fail se nulo)
- apÃ³s filtro MG+Diamantina, linhas > 0 (warn se 0)

### 10.3 fact_resultado_eleitoral
- value >= 0 (fail se negativo)
- election_year preenchido
- territory_id resolvido

### 10.4 fact_indicador
- value numÃ©rico (fail se invÃ¡lido)
- reference_period preenchido
- indicator_code preenchido
- territory_id resolvido

---

## 11. OrquestraÃ§Ã£o (padrÃ£o de jobs)

### 11.1 Jobs obrigatÃ³rios (nomes recomendados)
1. `ibge_admin_fetch` (municÃ­pio + distritos)
2. `ibge_geometries_fetch` (malhas + import PostGIS)
3. `ibge_indicators_fetch` (Censo/PIB e demais indicadores configurados)
4. `tse_catalog_discovery` (descobrir resources por ano)
5. `tse_electorate_fetch` (eleitorado por ano)
6. `tse_results_fetch` (resultados por ano)
7. `education_inep_fetch` (educaÃ§Ã£o por ano)
8. `health_datasus_fetch` (saÃºde por perÃ­odo)
9. `finance_siconfi_fetch` (finanÃ§as por ano)
10. `labor_mte_fetch` (RAIS/CAGED por ano)
11. `dbt_build` (transformaÃ§Ãµes gold, se usar dbt)
12. `quality_suite` (rodar checks e gerar relatÃ³rio)

### 11.2 ParÃ¢metros obrigatÃ³rios por job
- `reference_period` (ou `years: [..]`)
- `force: bool` (rebaixa cache e reextrai)
- `dry_run: bool` (simula sem persistir no banco)
- `max_retries: int`
- `timeout_seconds: int`

---

## 12. API (contrato mÃ­nimo para consumo)

A API Ã© interna e serve dashboards e anÃ¡lises.

Endpoints mÃ­nimos:
- `GET /territories` (lista nÃ­veis + hierarquia)
- `GET /territories/{id}` (detalhe + geometry opcional)
- `GET /indicators?territory_id=&indicator_code=&period=`
- `GET /electorate?level=municipio|zona|secao&period=YYYY&breakdown=sex|age|education`
- `GET /elections/results?level=municipio|zona|secao&year=YYYY&office=&round=`
- `GET /geo/choropleth?metric=&period=&level=municipio|distrito`

Regras:
- paginaÃ§Ã£o
- filtros explÃ­citos
- respostas JSON estÃ¡veis (versionadas futuramente)

---

## 13. CritÃ©rios de aceitaÃ§Ã£o (Definition of Done)

Um dataset Ã© considerado â€œimplementadoâ€ quando:
- hÃ¡ conector com discovery (se aplicÃ¡vel) + download automatizado
- hÃ¡ armazenamento BRONZE com manifesto e checksum
- hÃ¡ carga SILVER com esquema e constraints
- hÃ¡ pelo menos 3 checks de qualidade especÃ­ficos
- o job Ã© idempotente e reexecutÃ¡vel
- logs e mÃ©tricas bÃ¡sicas existem
- documentaÃ§Ã£o (esta spec) menciona o dataset com clareza

---

## 14. Backlog futuro (fora do MVP, mas previsto)
- vincular zonas/seÃ§Ãµes a distritos por geocodificaÃ§Ã£o (seÃ§Ã£o -> endereÃ§o/coord. quando houver)
- incorporar dados municipais locais (prefeitura) com catalog discovery
- cache HTTP e ETags
- materialized views para mapas e sÃ©ries
- catÃ¡logo de metadados (DataHub/OpenMetadata) opcional

---

## 15. Regra final (autoridade do contrato)
Se houver conflito entre cÃ³digo e este documento:
ESTA SPEC PREVALECE.

