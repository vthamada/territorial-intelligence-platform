"""Tests for strategic engine configuration loader and helpers."""
from __future__ import annotations

import textwrap
from pathlib import Path
from uuid import uuid4

import pytest

from app.api.strategic_engine_config import (
    ScoringConfig,
    StrategicEngineConfig,
    load_strategic_engine_config,
    score_to_status,
    status_impact,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Ensure lru_cache is cleared between every test."""
    load_strategic_engine_config.cache_clear()
    yield
    load_strategic_engine_config.cache_clear()


@pytest.fixture()
def config_file() -> Path:
    """Write a custom strategic_engine.yml and return its path."""
    base_dir = Path("tmp/test_strategic_engine_config")
    base_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir = base_dir / f"case_{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent("""\
        version: "2.5.0"
        scoring:
          critical_threshold: 90
          attention_threshold: 60
          rank_formula: "percentile"
          default_domain_weight: 1.25
          default_indicator_weight: 0.75
          domain_weights:
            saude: 1.5
          indicator_weights:
            IND_TESTE: 2.0
          severity_weights:
            stable: 0
            attention: 2
            critical: 5
          max_score: 100
          min_score: 0
    """)
    p = cfg_dir / "strategic_engine.yml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def default_config() -> StrategicEngineConfig:
    return StrategicEngineConfig()


# ---------------------------------------------------------------------------
# ScoringConfig defaults
# ---------------------------------------------------------------------------

class TestScoringConfigDefaults:
    def test_default_critical(self):
        assert ScoringConfig().critical_threshold == 80.0

    def test_default_attention(self):
        assert ScoringConfig().attention_threshold == 50.0

    def test_default_weights(self):
        w = ScoringConfig().severity_weights
        assert w == {"stable": 0, "attention": 1, "critical": 2}

    def test_default_domain_indicator_weights(self):
        cfg = ScoringConfig()
        assert cfg.default_domain_weight == 1.0
        assert cfg.default_indicator_weight == 1.0
        assert cfg.domain_weights == {}
        assert cfg.indicator_weights == {}

    def test_frozen(self):
        cfg = ScoringConfig()
        with pytest.raises(AttributeError):
            cfg.critical_threshold = 42  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Loading from YAML
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_load_custom_file(self, config_file: Path):
        cfg = load_strategic_engine_config(config_file)
        assert cfg.version == "2.5.0"
        assert cfg.scoring.critical_threshold == 90.0
        assert cfg.scoring.attention_threshold == 60.0
        assert cfg.scoring.severity_weights["critical"] == 5
        assert cfg.scoring.default_domain_weight == 1.25
        assert cfg.scoring.default_indicator_weight == 0.75
        assert cfg.scoring.domain_weights["saude"] == 1.5
        assert cfg.scoring.indicator_weights["IND_TESTE"] == 2.0

    def test_load_missing_file_returns_defaults(self):
        base_dir = Path("tmp/test_strategic_engine_config")
        base_dir.mkdir(parents=True, exist_ok=True)
        missing = base_dir / f"missing_{uuid4().hex}.yml"
        cfg = load_strategic_engine_config(missing)
        assert cfg.version == "1.0.0"
        assert cfg.scoring.critical_threshold == 80.0

    def test_load_empty_file_returns_defaults(self):
        base_dir = Path("tmp/test_strategic_engine_config")
        base_dir.mkdir(parents=True, exist_ok=True)
        empty = base_dir / f"empty_{uuid4().hex}.yml"
        empty.write_text("", encoding="utf-8")
        cfg = load_strategic_engine_config(empty)
        assert cfg.version == "1.0.0"
        assert cfg.scoring.critical_threshold == 80.0

    def test_load_partial_yaml_uses_defaults_for_missing_keys(self):
        base_dir = Path("tmp/test_strategic_engine_config")
        base_dir.mkdir(parents=True, exist_ok=True)
        partial = base_dir / f"partial_{uuid4().hex}.yml"
        partial.write_text("version: '3.0.0'\n", encoding="utf-8")
        cfg = load_strategic_engine_config(partial)
        assert cfg.version == "3.0.0"
        assert cfg.scoring.critical_threshold == 80.0
        assert cfg.scoring.attention_threshold == 50.0

    def test_caching(self, config_file: Path):
        cfg1 = load_strategic_engine_config(config_file)
        cfg2 = load_strategic_engine_config(config_file)
        assert cfg1 is cfg2  # same object due to lru_cache

    def test_real_config_file_loads(self):
        """Smoke-test that the actual configs/strategic_engine.yml loads."""
        real_path = Path("configs/strategic_engine.yml")
        if real_path.exists():
            cfg = load_strategic_engine_config(real_path)
            assert cfg.version
            assert cfg.scoring.critical_threshold > 0


# ---------------------------------------------------------------------------
# score_to_status
# ---------------------------------------------------------------------------

class TestScoreToStatus:
    def test_critical(self, default_config):
        assert score_to_status(100.0, default_config) == "critical"
        assert score_to_status(80.0, default_config) == "critical"

    def test_attention(self, default_config):
        assert score_to_status(79.99, default_config) == "attention"
        assert score_to_status(50.0, default_config) == "attention"

    def test_stable(self, default_config):
        assert score_to_status(49.99, default_config) == "stable"
        assert score_to_status(0.0, default_config) == "stable"

    def test_custom_thresholds(self, config_file: Path):
        cfg = load_strategic_engine_config(config_file)
        # critical at 90, attention at 60
        assert score_to_status(95, cfg) == "critical"
        assert score_to_status(89, cfg) == "attention"
        assert score_to_status(59, cfg) == "stable"

    def test_boundary_exactly_at_threshold(self, default_config):
        assert score_to_status(80.0, default_config) == "critical"
        assert score_to_status(50.0, default_config) == "attention"

    def test_negative_score(self, default_config):
        assert score_to_status(-10.0, default_config) == "stable"

    def test_uses_default_config_when_none(self):
        """score_to_status() works without explicit config arg."""
        result = score_to_status(85.0)
        assert result == "critical"


# ---------------------------------------------------------------------------
# status_impact
# ---------------------------------------------------------------------------

class TestStatusImpact:
    def test_worsened(self, default_config):
        assert status_impact("stable", "critical", default_config) == "worsened"
        assert status_impact("stable", "attention", default_config) == "worsened"
        assert status_impact("attention", "critical", default_config) == "worsened"

    def test_improved(self, default_config):
        assert status_impact("critical", "stable", default_config) == "improved"
        assert status_impact("critical", "attention", default_config) == "improved"
        assert status_impact("attention", "stable", default_config) == "improved"

    def test_unchanged(self, default_config):
        assert status_impact("stable", "stable", default_config) == "unchanged"
        assert status_impact("critical", "critical", default_config) == "unchanged"

    def test_custom_weights(self, config_file: Path):
        cfg = load_strategic_engine_config(config_file)
        # weights: stable=0, attention=2, critical=5
        assert status_impact("stable", "attention", cfg) == "worsened"
        assert status_impact("critical", "attention", cfg) == "improved"

    def test_unknown_status_treated_as_zero(self, default_config):
        assert status_impact("unknown", "critical", default_config) == "worsened"
        assert status_impact("critical", "unknown", default_config) == "improved"

    def test_uses_default_config_when_none(self):
        result = status_impact("stable", "critical")
        assert result == "worsened"


# ---------------------------------------------------------------------------
# Integration: config_version appears in QgMetadata
# ---------------------------------------------------------------------------

class TestConfigVersionInMetadata:
    def test_qg_metadata_has_config_version_field(self):
        from app.schemas.qg import QgMetadata
        m = QgMetadata(
            source_name="test",
            coverage_note="test",
            config_version="2.0.0",
        )
        assert m.config_version == "2.0.0"

    def test_qg_metadata_config_version_defaults_to_none(self):
        from app.schemas.qg import QgMetadata
        m = QgMetadata(source_name="test", coverage_note="test")
        assert m.config_version is None

    def test_qg_metadata_serializes_config_version(self):
        from app.schemas.qg import QgMetadata
        m = QgMetadata(
            source_name="test",
            coverage_note="test",
            config_version="1.0.0",
        )
        d = m.model_dump()
        assert d["config_version"] == "1.0.0"
