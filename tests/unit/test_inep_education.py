from __future__ import annotations

from decimal import Decimal

from pipelines.inep_education import (
    _build_indicator_rows,
    _choose_sinopse_zip,
    _extract_sinopse_zip_links,
    _find_municipality_row,
)


def test_extract_sinopse_zip_links_filters_expected_download_urls() -> None:
    html = """
    <a href="https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2024.zip">2024</a>
    <a href="https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2023.zip">2023</a>
    <a href="https://download.inep.gov.br/arquivo.pdf">pdf</a>
    """
    links = _extract_sinopse_zip_links(html)
    assert len(links) == 2
    assert links[0].endswith("2024.zip")


def test_choose_sinopse_zip_prefers_exact_year() -> None:
    links = [
        "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2024.zip",
        "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2023.zip",
    ]
    selected, year, warning = _choose_sinopse_zip(links, 2024)
    assert selected.endswith("2024.zip")
    assert year == 2024
    assert warning is None


def test_choose_sinopse_zip_falls_back_to_latest_lower_year() -> None:
    links = [
        "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2024.zip",
        "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopses_estatisticas_censo_escolar_2023.zip",
    ]
    selected, year, warning = _choose_sinopse_zip(links, 2025)
    assert selected.endswith("2024.zip")
    assert year == 2024
    assert warning is not None


def test_find_municipality_row_matches_by_code() -> None:
    rows = [
        {"C": "Outra Cidade", "D": "9999999", "E": "100"},
        {"C": "Diamantina", "D": "3121605", "E": "200"},
    ]
    row = _find_municipality_row(
        rows,
        municipality_name="Diamantina",
        municipality_ibge_code="3121605",
    )
    assert row is not None
    assert row["E"] == "200"


def test_build_indicator_rows_uses_column_e_as_total_enrolments() -> None:
    rows = _build_indicator_rows(
        territory_id="00000000-0000-0000-0000-000000000000",
        row={"E": "11231"},
        reference_period="2024",
    )
    assert len(rows) == 1
    assert rows[0]["indicator_code"] == "INEP_CENSO_ESCOLAR_MATRICULAS_TOTAL"
    assert rows[0]["value"] == Decimal("11231")
