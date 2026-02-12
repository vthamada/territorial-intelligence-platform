from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_bootstrap_module():
    module_path = Path("scripts/bootstrap_manual_sources.py")
    spec = importlib.util.spec_from_file_location("bootstrap_manual_sources", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_snis_rs_metrics_reads_in015_by_ibge_code() -> None:
    module = _load_bootstrap_module()

    rows = [
        [],
        [],
        [],
        [],
        [],
        [],
        ["Código do município", "Código do IBGE", "Município"] + ([""] * 20) + ["Tx cobertura"],
        [],
        [],
        ["-", "-", "-"] + ([""] * 20) + ["IN015"],
        ["312160", "3121605", "Diamantina"] + ([""] * 20) + ["81,45"],
    ]

    extracted = module._extract_snis_rs_metrics(
        rows,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )

    assert extracted is not None
    assert extracted["codigo_municipio"] == "3121605"
    assert extracted["municipio"] == "Diamantina"
    assert extracted["coleta_residuos_percentual"] == 81.45
    assert extracted["source_indicator_code"] == "IN015"


def test_extract_snis_rs_metrics_returns_none_without_in015() -> None:
    module = _load_bootstrap_module()

    rows = [
        [],
        [],
        [],
        [],
        [],
        [],
        ["Código do município", "Código do IBGE", "Município", "Valor X"],
        [],
        [],
        ["-", "-", "-", "IN999"],
        ["312160", "3121605", "Diamantina", "10"],
    ]

    extracted = module._extract_snis_rs_metrics(
        rows,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
    )

    assert extracted is None


def test_extract_snis_indicator_metrics_reads_ae_indicators() -> None:
    module = _load_bootstrap_module()

    rows = [
        [],
        ["Codigo do IBGE", "Municipio", "valor_a", "valor_b", "valor_c"],
        [],
        ["-", "-", "IN055", "IN056", "IN049"],
        ["3121605", "Diamantina", "91,2", "84,6", "37,4"],
    ]

    extracted = module._extract_snis_indicator_metrics(
        rows,
        municipality_ibge_code="3121605",
        municipality_name="Diamantina",
        indicator_fields=module.SNIS_AE_INDICATOR_FIELDS,
    )

    assert extracted is not None
    assert extracted["atendimento_agua_percentual"] == 91.2
    assert extracted["atendimento_esgoto_percentual"] == 84.6
    assert extracted["perdas_agua_percentual"] == 37.4
