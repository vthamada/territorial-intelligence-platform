from __future__ import annotations

from pipelines.datasus_health import (
    _build_indicator_rows,
    _is_truthy_flag,
    _to_cnes_municipality_code,
)


def test_to_cnes_municipality_code_uses_first_six_digits() -> None:
    assert _to_cnes_municipality_code("3121606") == "312160"


def test_is_truthy_flag_handles_common_variants() -> None:
    assert _is_truthy_flag("sim")
    assert _is_truthy_flag("TRUE")
    assert _is_truthy_flag("1")
    assert not _is_truthy_flag("nao")


def test_build_indicator_rows_deduplicates_by_cnes() -> None:
    establishments = [
        {
            "codigo_cnes": "111",
            "estabelecimento_faz_atendimento_ambulatorial_sus": "SIM",
            "estabelecimento_possui_atendimento_hospitalar": "NAO",
            "estabelecimento_possui_centro_cirurgico": "NAO",
        },
        {
            "codigo_cnes": "111",
            "estabelecimento_faz_atendimento_ambulatorial_sus": "SIM",
            "estabelecimento_possui_atendimento_hospitalar": "NAO",
            "estabelecimento_possui_centro_cirurgico": "NAO",
        },
        {
            "codigo_cnes": "222",
            "estabelecimento_faz_atendimento_ambulatorial_sus": "NAO",
            "estabelecimento_possui_atendimento_hospitalar": "SIM",
            "estabelecimento_possui_centro_cirurgico": "SIM",
        },
    ]
    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        reference_period="2024",
        establishments=establishments,
    )
    by_code = {row["indicator_code"]: row for row in rows}
    assert by_code["DATASUS_CNES_ESTABLISHMENTS_TOTAL"]["value"] == 2
    assert by_code["DATASUS_CNES_AMBULATORY_SUS_TOTAL"]["value"] == 1
    assert by_code["DATASUS_CNES_HOSPITAL_CARE_TOTAL"]["value"] == 1
    assert by_code["DATASUS_CNES_SURGERY_CENTER_TOTAL"]["value"] == 1
