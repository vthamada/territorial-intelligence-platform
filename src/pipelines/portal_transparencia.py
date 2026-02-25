from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import session_scope
from app.logging import get_logger
from app.settings import Settings, get_settings
from pipelines.common.bronze_store import artifact_to_dict, persist_raw_bytes
from pipelines.common.http_client import HttpClient
from pipelines.common.observability import replace_pipeline_checks_from_dicts, upsert_pipeline_run

JOB_NAME = "portal_transparencia_fetch"
SOURCE = "PORTAL_TRANSPARENCIA"
DATASET_NAME = "portal_transparencia_municipal"
WAVE = "MVP-6"


@dataclass(frozen=True)
class IndicatorMetric:
    code: str
    name: str
    unit: str
    category: str
    value: Decimal


def _parse_reference_year(reference_period: str) -> int:
    token = str(reference_period).strip()
    if not token:
        raise ValueError("reference_period is empty")
    year_token = token.split("-")[0]
    if not year_token.isdigit() or len(year_token) != 4:
        raise ValueError(f"Invalid reference_period '{reference_period}'. Expected year (YYYY).")
    return int(year_token)


def _month_tokens(year: int) -> list[str]:
    return [f"{year}{month:02d}" for month in range(1, 13)]


def _month_mm_yyyy(token: str) -> str:
    year = token[:4]
    month = token[4:]
    return f"{month}/{year}"


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))

    token = str(value).strip()
    if not token:
        return None
    normalized = token.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return [payload]
    return []


def _fetch_paginated(
    client: HttpClient,
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    max_pages: int = 300,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    page = 1
    pages = 0
    while page <= max_pages:
        payload = client.get_json(url, headers=headers, params={**params, "pagina": page})
        page_rows = _extract_items(payload)
        pages += 1
        if not page_rows:
            break
        rows.extend(page_rows)
        page += 1
    return rows, pages


def _sum_field(rows: list[dict[str, Any]], field: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        parsed = _to_decimal(row.get(field))
        if parsed is None:
            continue
        total += parsed
    return total


def _count_distinct_people(rows: list[dict[str, Any]], *fields: str) -> int:
    seen: set[str] = set()
    for row in rows:
        for field in fields:
            raw = str(row.get(field, "") or "").strip()
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                seen.add(digits)
                break
    return len(seen)


def _resolve_municipality_context(settings: Settings) -> tuple[str, str, str, str]:
    with session_scope(settings) as session:
        row = session.execute(
            text(
                """
                SELECT territory_id::text, name, municipality_ibge_code, uf
                FROM silver.dim_territory
                WHERE level = 'municipality'
                  AND municipality_ibge_code = :municipality_ibge_code
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"municipality_ibge_code": settings.municipality_ibge_code},
        ).first()
    if row is None:
        raise RuntimeError("Municipality territory not found. Run ibge_admin_fetch first.")
    territory_id = str(row[0]).strip()
    municipality_name = str(row[1]).strip()
    municipality_ibge_code = str(row[2]).strip()
    uf = str(row[3]).strip().upper()
    if not territory_id or not municipality_name or not municipality_ibge_code or not uf:
        raise RuntimeError("Invalid municipality context in dim_territory.")
    return territory_id, municipality_name, municipality_ibge_code, uf


def _build_url(settings: Settings, endpoint: str) -> str:
    base = settings.portal_transparencia_api_base_url.rstrip("/")
    suffix = endpoint.lstrip("/")
    return f"{base}/{suffix}"


def _collect_monthly_rows(
    client: HttpClient,
    *,
    settings: Settings,
    endpoint: str,
    year: int,
    municipality_ibge_code: str,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    pages = 0
    for mes_ano in _month_tokens(year):
        batch_rows, batch_pages = _fetch_paginated(
            client,
            url=_build_url(settings, endpoint),
            headers=headers,
            params={"mesAno": int(mes_ano), "codigoIbge": municipality_ibge_code},
        )
        pages += batch_pages
        rows.extend(batch_rows)
    return rows, pages


def _collect_resources_rows(
    client: HttpClient,
    *,
    settings: Settings,
    year: int,
    municipality_ibge_code: str,
    uf: str,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    pages = 0
    for mes_ano in _month_tokens(year):
        month_ref = _month_mm_yyyy(mes_ano)
        batch_rows, batch_pages = _fetch_paginated(
            client,
            url=_build_url(settings, "despesas/recursos-recebidos"),
            headers=headers,
            params={
                "mesAnoInicio": month_ref,
                "mesAnoFim": month_ref,
                "uf": uf,
                "codigoIBGE": municipality_ibge_code,
            },
        )
        pages += batch_pages
        rows.extend(batch_rows)
    return rows, pages


def _collect_convenios_rows(
    client: HttpClient,
    *,
    settings: Settings,
    year: int,
    municipality_ibge_code: str,
    uf: str,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    warnings: list[str] = []
    default_params = {
        "codigoIBGE": municipality_ibge_code,
        "uf": uf,
        "dataInicial": f"01/01/{year}",
        "dataFinal": f"31/12/{year}",
    }
    try:
        rows, pages = _fetch_paginated(
            client,
            url=_build_url(settings, "convenios"),
            headers=headers,
            params=default_params,
        )
        return rows, pages, warnings
    except Exception as exc:
        warnings.append(f"convenios with date range failed: {exc}. Retrying without date filters.")
        rows, pages = _fetch_paginated(
            client,
            url=_build_url(settings, "convenios"),
            headers=headers,
            params={"codigoIBGE": municipality_ibge_code, "uf": uf},
        )
        return rows, pages, warnings


def _collect_renuncias_rows(
    client: HttpClient,
    *,
    settings: Settings,
    year: int,
    municipality_ibge_code: str,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    rows, pages = _fetch_paginated(
        client,
        url=_build_url(settings, "renuncias-valor"),
        headers=headers,
        params={"codigoIbge": municipality_ibge_code},
    )
    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_year = str(row.get("ano", "")).strip()
        if row_year and row_year != str(year):
            continue
        filtered.append(row)
    return filtered, pages


def _collect_coronavirus_rows(
    client: HttpClient,
    *,
    settings: Settings,
    year: int,
    municipality_ibge_code: str,
    uf: str,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    pages = 0
    for mes_ano in _month_tokens(year):
        batch_rows, batch_pages = _fetch_paginated(
            client,
            url=_build_url(settings, "coronavirus/transferencias"),
            headers=headers,
            params={"mesAno": int(mes_ano), "uf": uf, "codigoIbge": municipality_ibge_code},
        )
        pages += batch_pages
        rows.extend(batch_rows)
    return rows, pages


def _build_metrics(*, rows_by_key: dict[str, list[dict[str, Any]]]) -> list[IndicatorMetric]:
    bpc_rows = rows_by_key.get("bpc", [])
    bolsa_rows = rows_by_key.get("bolsa", [])
    nbf_rows = rows_by_key.get("novo_bolsa", [])
    aux_brasil_rows = rows_by_key.get("auxilio_brasil", [])
    aux_emerg_rows = rows_by_key.get("auxilio_emergencial", [])
    peti_rows = rows_by_key.get("peti", [])
    safra_rows = rows_by_key.get("safra", [])
    defeso_rows = rows_by_key.get("defeso", [])
    recursos_rows = rows_by_key.get("recursos", [])
    convenios_rows = rows_by_key.get("convenios", [])
    renuncias_rows = rows_by_key.get("renuncias", [])
    covid_rows = rows_by_key.get("covid_transferencias", [])

    return [
        IndicatorMetric(
            code="PT_BPC_VALOR_TOTAL",
            name="Portal Transparencia BPC valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(bpc_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_BPC_BENEFICIARIOS_TOTAL",
            name="Portal Transparencia BPC beneficiarios",
            unit="count",
            category="assistencia_social",
            value=Decimal(_sum_field(bpc_rows, "quantidadeBeneficiados")),
        ),
        IndicatorMetric(
            code="PT_BOLSA_FAMILIA_VALOR_TOTAL",
            name="Portal Transparencia Bolsa Familia valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(bolsa_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_BOLSA_FAMILIA_BENEFICIARIOS_TOTAL",
            name="Portal Transparencia Bolsa Familia beneficiarios",
            unit="count",
            category="assistencia_social",
            value=Decimal(_sum_field(bolsa_rows, "quantidadeBeneficiados")),
        ),
        IndicatorMetric(
            code="PT_NOVO_BOLSA_FAMILIA_VALOR_TOTAL",
            name="Portal Transparencia Novo Bolsa Familia valor saque",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(nbf_rows, "valorSaque"),
        ),
        IndicatorMetric(
            code="PT_NOVO_BOLSA_FAMILIA_BENEFICIARIOS_UNICOS",
            name="Portal Transparencia Novo Bolsa Familia beneficiarios unicos",
            unit="count",
            category="assistencia_social",
            value=Decimal(_count_distinct_people(nbf_rows, "nis", "cpfFormatado")),
        ),
        IndicatorMetric(
            code="PT_AUXILIO_BRASIL_VALOR_TOTAL",
            name="Portal Transparencia Auxilio Brasil valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(aux_brasil_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_AUXILIO_BRASIL_BENEFICIARIOS_TOTAL",
            name="Portal Transparencia Auxilio Brasil beneficiarios",
            unit="count",
            category="assistencia_social",
            value=Decimal(_sum_field(aux_brasil_rows, "quantidadeBeneficiados")),
        ),
        IndicatorMetric(
            code="PT_AUXILIO_EMERGENCIAL_VALOR_TOTAL",
            name="Portal Transparencia Auxilio Emergencial valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(aux_emerg_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_AUXILIO_EMERGENCIAL_BENEFICIARIOS_TOTAL",
            name="Portal Transparencia Auxilio Emergencial beneficiarios",
            unit="count",
            category="assistencia_social",
            value=Decimal(_sum_field(aux_emerg_rows, "quantidadeBeneficiados")),
        ),
        IndicatorMetric(
            code="PT_PETI_VALOR_TOTAL",
            name="Portal Transparencia PETI valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(peti_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_SAFRA_VALOR_TOTAL",
            name="Portal Transparencia Garantia Safra valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(safra_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_SEGURO_DEFESO_VALOR_TOTAL",
            name="Portal Transparencia Seguro Defeso valor total",
            unit="BRL",
            category="assistencia_social",
            value=_sum_field(defeso_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_RECURSOS_RECEBIDOS_VALOR_TOTAL",
            name="Portal Transparencia recursos recebidos valor total",
            unit="BRL",
            category="financas_publicas",
            value=_sum_field(recursos_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_CONVENIOS_VALOR_TOTAL",
            name="Portal Transparencia convenios valor total",
            unit="BRL",
            category="financas_publicas",
            value=_sum_field(convenios_rows, "valor"),
        ),
        IndicatorMetric(
            code="PT_CONVENIOS_VALOR_LIBERADO_TOTAL",
            name="Portal Transparencia convenios valor liberado total",
            unit="BRL",
            category="financas_publicas",
            value=_sum_field(convenios_rows, "valorLiberado"),
        ),
        IndicatorMetric(
            code="PT_CONVENIOS_QUANTIDADE",
            name="Portal Transparencia quantidade de convenios",
            unit="count",
            category="financas_publicas",
            value=Decimal(len(convenios_rows)),
        ),
        IndicatorMetric(
            code="PT_RENUNCIAS_VALOR_TOTAL",
            name="Portal Transparencia renuncias fiscais valor total",
            unit="BRL",
            category="financas_publicas",
            value=_sum_field(renuncias_rows, "valorRenunciado"),
        ),
        IndicatorMetric(
            code="PT_COVID_TRANSFERENCIAS_VALOR_TOTAL",
            name="Portal Transparencia COVID transferencias valor total",
            unit="BRL",
            category="financas_publicas",
            value=_sum_field(covid_rows, "valor"),
        ),
    ]


def _upsert_indicators(settings: Settings, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with session_scope(settings) as session:
        for row in rows:
            session.execute(
                text(
                    """
                    INSERT INTO silver.fact_indicator (
                        territory_id,
                        source,
                        dataset,
                        indicator_code,
                        indicator_name,
                        unit,
                        category,
                        value,
                        reference_period
                    )
                    VALUES (
                        CAST(:territory_id AS uuid),
                        :source,
                        :dataset,
                        :indicator_code,
                        :indicator_name,
                        :unit,
                        :category,
                        :value,
                        :reference_period
                    )
                    ON CONFLICT (
                        territory_id,
                        source,
                        dataset,
                        indicator_code,
                        category,
                        reference_period
                    )
                    DO UPDATE SET
                        indicator_name = EXCLUDED.indicator_name,
                        unit = EXCLUDED.unit,
                        value = EXCLUDED.value,
                        updated_at = NOW()
                    """
                ),
                {
                    **row,
                    "value": str(row["value"]),
                },
            )
    return len(rows)


def run(
    *,
    reference_period: str,
    force: bool = False,
    dry_run: bool = False,
    max_retries: int = 3,
    timeout_seconds: int = 30,
    settings: Settings | None = None,
) -> dict[str, Any]:
    del force
    settings = settings or get_settings()
    logger = get_logger(JOB_NAME)
    run_id = str(uuid4())
    started_at_utc = datetime.now(UTC)
    started_at = time.perf_counter()
    warnings: list[str] = []

    try:
        reference_year = _parse_reference_year(reference_period)
        territory_id, municipality_name, municipality_ibge_code, uf = _resolve_municipality_context(settings)
    except Exception as exc:
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": 0.0,
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [str(exc)],
        }

    if not settings.portal_transparencia_api_key:
        warning = "PORTAL_TRANSPARENCIA_API_KEY is not configured."
        warnings.append(warning)
        elapsed = time.perf_counter() - started_at
        if not dry_run:
            with session_scope(settings) as session:
                upsert_pipeline_run(
                    session=session,
                    run_id=run_id,
                    job_name=JOB_NAME,
                    source=SOURCE,
                    dataset=DATASET_NAME,
                    wave=WAVE,
                    reference_period=str(reference_year),
                    started_at_utc=started_at_utc,
                    finished_at_utc=datetime.now(UTC),
                    status="blocked",
                    rows_extracted=0,
                    rows_loaded=0,
                    warnings_count=1,
                    errors_count=0,
                    details={"reason": "missing_api_key"},
                )
                replace_pipeline_checks_from_dicts(
                    session=session,
                    run_id=run_id,
                    checks=[
                        {
                            "name": "portal_transparencia_api_key_configured",
                            "status": "warn",
                            "details": warning,
                            "observed_value": 0,
                            "threshold_value": 1,
                        }
                    ],
                )
        return {
            "job": JOB_NAME,
            "status": "blocked",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [],
        }

    client = HttpClient.from_settings(
        settings,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    try:
        headers = {"chave-api-dados": settings.portal_transparencia_api_key}

        endpoint_rows: dict[str, list[dict[str, Any]]] = {}
        endpoint_stats: dict[str, dict[str, Any]] = {}

        endpoint_specs: tuple[tuple[str, str], ...] = (
            ("bpc", "bpc-por-municipio"),
            ("bolsa", "bolsa-familia-por-municipio"),
            ("novo_bolsa", "novo-bolsa-familia-por-municipio"),
            ("auxilio_brasil", "auxilio-brasil-por-municipio"),
            ("auxilio_emergencial", "auxilio-emergencial-por-municipio"),
            ("peti", "peti-por-municipio"),
            ("safra", "safra-por-municipio"),
            ("defeso", "seguro-defeso-por-municipio"),
        )

        rows_extracted = 0
        for metric_key, endpoint in endpoint_specs:
            try:
                rows, pages = _collect_monthly_rows(
                    client,
                    settings=settings,
                    endpoint=endpoint,
                    year=reference_year,
                    municipality_ibge_code=municipality_ibge_code,
                    headers=headers,
                )
                endpoint_rows[metric_key] = rows
                endpoint_stats[metric_key] = {"endpoint": endpoint, "rows": len(rows), "pages": pages}
                rows_extracted += len(rows)
            except Exception as exc:
                endpoint_rows[metric_key] = []
                endpoint_stats[metric_key] = {"endpoint": endpoint, "rows": 0, "error": str(exc)}
                warnings.append(f"{endpoint} failed: {exc}")

        try:
            recursos_rows, recursos_pages = _collect_resources_rows(
                client,
                settings=settings,
                year=reference_year,
                municipality_ibge_code=municipality_ibge_code,
                uf=uf,
                headers=headers,
            )
            endpoint_rows["recursos"] = recursos_rows
            endpoint_stats["recursos"] = {
                "endpoint": "despesas/recursos-recebidos",
                "rows": len(recursos_rows),
                "pages": recursos_pages,
            }
            rows_extracted += len(recursos_rows)
        except Exception as exc:
            endpoint_rows["recursos"] = []
            endpoint_stats["recursos"] = {"endpoint": "despesas/recursos-recebidos", "rows": 0, "error": str(exc)}
            warnings.append(f"despesas/recursos-recebidos failed: {exc}")

        try:
            convenios_rows, convenios_pages, convenios_warnings = _collect_convenios_rows(
                client,
                settings=settings,
                year=reference_year,
                municipality_ibge_code=municipality_ibge_code,
                uf=uf,
                headers=headers,
            )
            warnings.extend(convenios_warnings)
            endpoint_rows["convenios"] = convenios_rows
            endpoint_stats["convenios"] = {"endpoint": "convenios", "rows": len(convenios_rows), "pages": convenios_pages}
            rows_extracted += len(convenios_rows)
        except Exception as exc:
            endpoint_rows["convenios"] = []
            endpoint_stats["convenios"] = {"endpoint": "convenios", "rows": 0, "error": str(exc)}
            warnings.append(f"convenios failed: {exc}")

        try:
            renuncias_rows, renuncias_pages = _collect_renuncias_rows(
                client,
                settings=settings,
                year=reference_year,
                municipality_ibge_code=municipality_ibge_code,
                headers=headers,
            )
            endpoint_rows["renuncias"] = renuncias_rows
            endpoint_stats["renuncias"] = {"endpoint": "renuncias-valor", "rows": len(renuncias_rows), "pages": renuncias_pages}
            rows_extracted += len(renuncias_rows)
        except Exception as exc:
            endpoint_rows["renuncias"] = []
            endpoint_stats["renuncias"] = {"endpoint": "renuncias-valor", "rows": 0, "error": str(exc)}
            warnings.append(f"renuncias-valor failed: {exc}")

        try:
            covid_rows, covid_pages = _collect_coronavirus_rows(
                client,
                settings=settings,
                year=reference_year,
                municipality_ibge_code=municipality_ibge_code,
                uf=uf,
                headers=headers,
            )
            endpoint_rows["covid_transferencias"] = covid_rows
            endpoint_stats["covid_transferencias"] = {
                "endpoint": "coronavirus/transferencias",
                "rows": len(covid_rows),
                "pages": covid_pages,
            }
            rows_extracted += len(covid_rows)
        except Exception as exc:
            endpoint_rows["covid_transferencias"] = []
            endpoint_stats["covid_transferencias"] = {"endpoint": "coronavirus/transferencias", "rows": 0, "error": str(exc)}
            warnings.append(f"coronavirus/transferencias failed: {exc}")

        metrics = _build_metrics(rows_by_key=endpoint_rows)
        indicator_rows = [
            {
                "territory_id": territory_id,
                "source": SOURCE,
                "dataset": DATASET_NAME,
                "indicator_code": metric.code,
                "indicator_name": metric.name,
                "unit": metric.unit,
                "category": metric.category,
                "value": metric.value,
                "reference_period": str(reference_year),
            }
            for metric in metrics
        ]

        bronze_payload = {
            "reference_year": reference_year,
            "municipality_ibge_code": municipality_ibge_code,
            "municipality_name": municipality_name,
            "endpoint_stats": endpoint_stats,
            "metrics": [
                {
                    "indicator_code": metric.code,
                    "value": str(metric.value),
                    "unit": metric.unit,
                }
                for metric in metrics
            ],
            "warnings": warnings,
        }
        raw_bytes = json.dumps(bronze_payload, ensure_ascii=False, indent=2).encode("utf-8")

        elapsed = time.perf_counter() - started_at
        if dry_run:
            return {
                "job": JOB_NAME,
                "status": "success" if rows_extracted > 0 else "blocked",
                "run_id": run_id,
                "duration_seconds": round(elapsed, 2),
                "rows_extracted": rows_extracted,
                "rows_written": 0,
                "warnings": warnings,
                "errors": [],
                "preview": {
                    "municipality": municipality_name,
                    "metrics": [
                        {
                            "indicator_code": metric.code,
                            "value": str(metric.value),
                            "unit": metric.unit,
                        }
                        for metric in metrics
                    ],
                    "endpoint_stats": endpoint_stats,
                },
            }

        artifact = persist_raw_bytes(
            settings=settings,
            source=SOURCE,
            dataset=DATASET_NAME,
            reference_period=str(reference_year),
            raw_bytes=raw_bytes,
            extension=".json",
            uri=f"{settings.portal_transparencia_api_base_url.rstrip('/') }/*",
            territory_scope="municipality",
            dataset_version="portal-transparencia-v1",
            checks=[
                {
                    "name": "portal_transparencia_api_key_configured",
                    "status": "pass",
                    "details": "API key configured via PORTAL_TRANSPARENCIA_API_KEY.",
                },
                {
                    "name": "portal_transparencia_rows_extracted",
                    "status": "pass" if rows_extracted > 0 else "warn",
                    "details": f"{rows_extracted} rows extracted across Portal Transparencia endpoints.",
                },
            ],
            notes="Municipal indicators extracted from Portal da Transparencia endpoints.",
            run_id=run_id,
            tables_written=["silver.fact_indicator"],
            rows_written=[{"table": "silver.fact_indicator", "rows": len(indicator_rows)}],
        )

        rows_written = _upsert_indicators(settings, indicator_rows)

        run_status = "success" if rows_written > 0 else "blocked"
        with session_scope(settings) as session:
            upsert_pipeline_run(
                session=session,
                run_id=run_id,
                job_name=JOB_NAME,
                source=SOURCE,
                dataset=DATASET_NAME,
                wave=WAVE,
                reference_period=str(reference_year),
                started_at_utc=started_at_utc,
                finished_at_utc=datetime.now(UTC),
                status=run_status,
                rows_extracted=rows_extracted,
                rows_loaded=rows_written,
                warnings_count=len(warnings),
                errors_count=0,
                bronze_path=artifact.local_path.as_posix(),
                manifest_path=artifact.manifest_path.as_posix(),
                checksum_sha256=artifact.checksum_sha256,
                details={
                    "artifact": artifact_to_dict(artifact),
                    "endpoint_stats": endpoint_stats,
                    "metrics_count": len(metrics),
                },
            )
            replace_pipeline_checks_from_dicts(
                session=session,
                run_id=run_id,
                checks=[
                    {
                        "name": "portal_transparencia_api_key_configured",
                        "status": "pass",
                        "details": "API key configured.",
                        "observed_value": 1,
                        "threshold_value": 1,
                    },
                    {
                        "name": "portal_transparencia_rows_extracted",
                        "status": "pass" if rows_extracted > 0 else "warn",
                        "details": f"{rows_extracted} rows extracted from Portal Transparencia.",
                        "observed_value": rows_extracted,
                        "threshold_value": 1,
                    },
                    {
                        "name": "portal_transparencia_indicators_upserted",
                        "status": "pass" if rows_written > 0 else "warn",
                        "details": f"{rows_written} indicators upserted into silver.fact_indicator.",
                        "observed_value": rows_written,
                        "threshold_value": 1,
                    },
                ],
            )

        return {
            "job": JOB_NAME,
            "status": run_status,
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": rows_extracted,
            "rows_written": rows_written,
            "warnings": warnings,
            "errors": [],
            "metrics": [{"indicator_code": metric.code, "value": str(metric.value)} for metric in metrics],
        }
    except Exception as exc:  # pragma: no cover - runtime safety
        elapsed = time.perf_counter() - started_at
        logger.exception("Portal Transparencia pipeline failed")
        error_message = str(exc)
        if not dry_run:
            with session_scope(settings) as session:
                upsert_pipeline_run(
                    session=session,
                    run_id=run_id,
                    job_name=JOB_NAME,
                    source=SOURCE,
                    dataset=DATASET_NAME,
                    wave=WAVE,
                    reference_period=str(reference_year),
                    started_at_utc=started_at_utc,
                    finished_at_utc=datetime.now(UTC),
                    status="failed",
                    rows_extracted=0,
                    rows_loaded=0,
                    warnings_count=len(warnings),
                    errors_count=1,
                    details={"error": error_message},
                )
                replace_pipeline_checks_from_dicts(
                    session=session,
                    run_id=run_id,
                    checks=[
                        {
                            "name": "portal_transparencia_runtime",
                            "status": "fail",
                            "details": error_message,
                            "observed_value": 0,
                            "threshold_value": 1,
                        }
                    ],
                )
        return {
            "job": JOB_NAME,
            "status": "failed",
            "run_id": run_id,
            "duration_seconds": round(elapsed, 2),
            "rows_extracted": 0,
            "rows_written": 0,
            "warnings": warnings,
            "errors": [error_message],
        }
    finally:
        client.close()
