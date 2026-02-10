# Runbook MTE (Novo CAGED)

## Objetivo

Operar o conector `labor_mte_fetch` com automacao via FTP, fallback por cache Bronze e fallback manual apenas em contingencia.

## Fonte primaria

- FTP oficial: `ftp://ftp.mtps.gov.br/pdet/microdados/`
- Pastas tentadas automaticamente pelo conector:
  - `/pdet/microdados/NOVO CAGED`
  - `/pdet/microdados/NOVO_CAGED`

## Parametros de configuracao (.env)

- `MTE_FTP_HOST` (default: `ftp.mtps.gov.br`)
- `MTE_FTP_PORT` (default: `21`)
- `MTE_FTP_ROOT_CANDIDATES` (lista separada por virgula)
- `MTE_FTP_MAX_DEPTH` (default: `4`)
- `MTE_FTP_MAX_DIRS` (default: `300`)

## Comportamento do conector

1. Faz probe da pagina web do MTE (apenas observabilidade de bloqueio/login).
2. Tenta descobrir e baixar arquivo de dados no FTP para o ano de `reference_period`.
3. Se FTP nao retornar arquivo utilizavel, tenta reutilizar ultimo arquivo tabular valido do Bronze para o mesmo `reference_period`.
4. Se ainda nao houver dado utilizavel, tenta fallback manual em `data/manual/mte`.
5. Se nao houver FTP, cache Bronze nem arquivo manual, retorna `status=blocked`.

## Formatos aceitos

- `CSV`
- `TXT`
- `ZIP` (contendo `CSV` ou `TXT`)

## Execucao recomendada

1. Dry-run:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import json; from pipelines.mte_labor import run; print(json.dumps(run(reference_period='2024', dry_run=True), ensure_ascii=False, indent=2, default=str))"
```

2. Carga real:

```powershell
python -c "import json; from pipelines.mte_labor import run; print(json.dumps(run(reference_period='2024', dry_run=False), ensure_ascii=False, indent=2, default=str))"
```

3. Validacao P0 (3 execucoes reais consecutivas):

```powershell
python scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json
```

Opcional via Makefile:

```powershell
make validate-mte-p0
```

## Interpretacao rapida do resultado

- `status=success` e `preview/source_type=ftp`: ingestao automatica via FTP.
- `status=success` e `preview/source_type=bronze_cache`: FTP indisponivel, mas foi usado cache Bronze automaticamente.
- `status=success` e `preview/source_type=manual`: fallback manual usado.
- `status=blocked`: nao encontrou dado no FTP e nao havia arquivo manual.

## Fallback manual

Se necessario, salve o arquivo em:

- `data/manual/mte`

Dica operacional:

1. Deixe apenas um arquivo-alvo na pasta para evitar ambiguidades.
2. O conector seleciona o arquivo mais recente por data de modificacao.

## Indicadores carregados

- `MTE_NOVO_CAGED_ADMISSOES_TOTAL`
- `MTE_NOVO_CAGED_DESLIGAMENTOS_TOTAL`
- `MTE_NOVO_CAGED_SALDO_TOTAL`
- `MTE_NOVO_CAGED_REGISTROS_TOTAL`

## Troubleshooting

1. `No MTE FTP dataset file was discovered...`
   - Verifique conectividade FTP no ambiente.
   - O conector tentara cache Bronze automaticamente.
   - Se ainda falhar, rode com fallback manual.

2. `Could not parse tabular file...`
   - Validar delimitador e encoding do arquivo.
   - Confirmar que ZIP contem `CSV`/`TXT` valido.

3. `MTE dataset has no rows for municipality...`
   - Verificar se o arquivo contem Diamantina/MG.
   - Confirmar codigo municipal esperado no banco (`settings.municipality_ibge_code`).
