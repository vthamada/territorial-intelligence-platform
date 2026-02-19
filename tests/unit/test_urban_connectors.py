from __future__ import annotations

from app.settings import Settings
from pipelines import urban_pois, urban_roads


def _build_settings() -> Settings:
    return Settings(
        municipality_ibge_code="3121605",
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/test_db",
    )


class _FakeHttpClient:
    def close(self) -> None:
        return None


def test_parse_overpass_road_rows_extracts_linestring_metadata() -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 123,
                "tags": {"name": "Rua da Quitanda", "highway": "residential", "oneway": "yes"},
                "geometry": [
                    {"lat": -18.244, "lon": -43.601},
                    {"lat": -18.243, "lon": -43.600},
                ],
            }
        ]
    }

    rows = urban_roads._parse_overpass_rows(payload, reference_period="2026")

    assert len(rows) == 1
    first = rows[0]
    assert first["external_id"] == "way/123"
    assert first["road_class"] == "residential"
    assert first["is_oneway"] is True
    assert "LineString" in first["geometry_json"]


def test_parse_overpass_poi_rows_classifies_health_category() -> None:
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 987,
                "lat": -18.2438,
                "lon": -43.6005,
                "tags": {"name": "UBS Centro", "amenity": "clinic"},
            }
        ]
    }

    rows = urban_pois._parse_overpass_rows(payload, reference_period="2026")

    assert len(rows) == 1
    first = rows[0]
    assert first["external_id"] == "node/987"
    assert first["category"] == "health"
    assert first["subcategory"] == "clinic"
    assert "Point" in first["geometry_json"]


def test_urban_roads_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        urban_roads,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", (-43.7, -18.3, -43.5, -18.1)),
    )
    monkeypatch.setattr(
        urban_roads,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            [
                {
                    "source": "MANUAL_URBAN",
                    "external_id": "r-1",
                    "name": "Rua A",
                    "road_class": "residential",
                    "is_oneway": False,
                    "metadata_json": {},
                    "geometry_json": '{"type":"LineString","coordinates":[[-43.60,-18.24],[-43.59,-18.23]]}',
                    "geometry_wkt": None,
                }
            ],
            b"raw",
            ".json",
            "manual",
            "file:///tmp/roads.geojson",
            "roads.geojson",
            [],
        ),
    )
    monkeypatch.setattr(
        urban_roads.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = urban_roads.run(reference_period="2026", dry_run=True, settings=_build_settings())

    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["first_row"]["name"] == "Rua A"


def test_urban_pois_dry_run_uses_resolved_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        urban_pois,
        "_resolve_municipality_context",
        lambda _settings: ("00000000-0000-0000-0000-000000000000", "Diamantina", (-43.7, -18.3, -43.5, -18.1)),
    )
    monkeypatch.setattr(
        urban_pois,
        "_resolve_dataset",
        lambda **kwargs: (  # noqa: ARG005
            [
                {
                    "source": "MANUAL_URBAN",
                    "external_id": "p-1",
                    "name": "UBS Centro",
                    "category": "health",
                    "subcategory": "clinic",
                    "metadata_json": {},
                    "geometry_json": '{"type":"Point","coordinates":[-43.6005,-18.2438]}',
                    "geometry_wkt": None,
                }
            ],
            b"raw",
            ".json",
            "manual",
            "file:///tmp/pois.geojson",
            "pois.geojson",
            [],
        ),
    )
    monkeypatch.setattr(
        urban_pois.HttpClient,
        "from_settings",
        lambda *args, **kwargs: _FakeHttpClient(),
    )

    result = urban_pois.run(reference_period="2026", dry_run=True, settings=_build_settings())

    assert result["status"] == "success"
    assert result["rows_extracted"] == 1
    assert result["preview"]["source_type"] == "manual"
    assert result["preview"]["first_row"]["name"] == "UBS Centro"
