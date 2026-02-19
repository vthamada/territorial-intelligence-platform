# Runbook Semanal - Robustez de Dados

Data de referencia: 2026-02-18  
Escopo: rotina operacional para manter a base no caminho de robustez maxima.

## 1) Objetivo

Executar uma rotina semanal padronizada para:
1. medir cobertura historica e territorial.
2. validar qualidade e readiness operacional.
3. tratar desvios antes de impactar API/frontend.

## 2) Pre-requisitos

1. Ambiente com `.venv` ativo.
2. Banco PostgreSQL/PostGIS acessivel pelo `.env`.
3. Tabelas de `silver` e `ops` inicializadas.

## 3) Comandos da rotina semanal

### Passo A - Atualizar baseline de cobertura robusta

```powershell
.\.venv\Scripts\python.exe scripts/backfill_robust_database.py --tse-years 2024,2022,2020 --indicator-periods 2025 --output-json data/reports/robustness_backfill_report.json
```

### Passo B - Exportar scorecard oficial de cobertura

```powershell
.\.venv\Scripts\python.exe scripts/export_data_coverage_scorecard.py --output-json data/reports/data_coverage_scorecard.json
```

### Passo C - Validar readiness operacional

```powershell
.\.venv\Scripts\python.exe scripts/backend_readiness.py --output-json
```

### Passo D (opcional) - Executar pilotos da Onda Social (D2)

```powershell
.\.venv\Scripts\python.exe scripts/backfill_robust_database.py --include-wave6 --skip-wave1 --skip-tse --skip-wave4 --skip-wave5 --indicator-periods 2025 --output-json data/reports/robustness_backfill_report.json
```

## 4) Regras de triagem

Classificacao:
1. Critico:
   - `hard_failures` no readiness.
   - qualquer check `fail` no `quality_suite`.
2. Alto:
   - `warn` recorrente por 2 semanas na mesma metrica.
   - queda de cobertura em serie temporal (anos/periodos).
3. Medio:
   - oscilacao pontual sem regressao estrutural.

Prazo de resposta:
1. Critico: iniciar mitigacao no mesmo dia.
2. Alto: plano de correcao em ate 2 dias uteis.
3. Medio: incluir no proximo ciclo semanal.

## 5) Acoes corretivas padrao

1. Falha de schema/fonte:
   - revisar conector e contrato de coluna.
   - reexecutar job em `dry_run=True`.
   - corrigir parser e reprocessar periodo afetado.
2. Falha de cobertura territorial:
   - validar `dim_territory` (niveis/chaves).
   - verificar join por `territory_id`.
   - reprocessar job de geometria/base territorial.
3. Falha de cobertura temporal:
   - revisar `reference_period` alvo no job.
   - executar backfill para anos faltantes.
4. Falha operacional (`ops`):
   - validar registro de run/check.
   - aplicar script de backfill de checks quando aplicavel.

## 6) Evidencias obrigatorias da rotina

Registrar no fim de cada ciclo:
1. `data/reports/robustness_backfill_report.json` atualizado.
2. `data/reports/data_coverage_scorecard.json` atualizado.
3. Saida de `scripts/backend_readiness.py --output-json`.
4. Registro sintese em `docs/HANDOFF.md`.
5. Registro de mudancas relevantes em `docs/CHANGELOG.md`.

## 7) Definicao de concluido da semana

A semana e considerada concluida quando:
1. nenhum `hard_failure` ativo.
2. sem `fail` no `quality_suite`.
3. scorecard exportado com rastreabilidade de data/hora.
4. riscos e pendencias documentados com proxima acao.
