"""설정 모듈 테스트"""

import pytest
from pathlib import Path

from resume_agent.config import (
    get_config_value,
    load_config,
    reload_config,
    _get_defaults,
)


class TestGetConfigValue:
    def test_returns_default_for_missing_key(self):
        result = get_config_value("nonexistent.key", "fallback")
        assert result == "fallback"

    def test_returns_nested_value(self):
        result = get_config_value("codex.max_retries")
        assert result == 3

    def test_returns_nested_default(self):
        result = get_config_value("codex.nonexistent.deep", "nope")
        assert result == "nope"

    def test_returns_none_without_default(self):
        result = get_config_value("nonexistent.key")
        assert result is None


class TestDefaults:
    def test_has_token_section(self):
        defaults = _get_defaults()
        assert "token" in defaults
        assert "warning_threshold" in defaults["token"]

    def test_has_scoring_section(self):
        defaults = _get_defaults()
        assert "scoring" in defaults
        assert "reuse_penalty" in defaults["scoring"]

    def test_has_codex_section(self):
        defaults = _get_defaults()
        assert "codex" in defaults
        assert "max_retries" in defaults["codex"]
        assert defaults["codex"]["max_retries"] == 3

    def test_has_validation_section(self):
        defaults = _get_defaults()
        assert "validation" in defaults
        assert "star_min_lengths" in defaults["validation"]

    def test_has_export_section(self):
        defaults = _get_defaults()
        assert "export" in defaults
        assert "char_limit_ratio_min" in defaults["export"]


class TestLoadConfig:
    def test_returns_dict(self):
        config = load_config()
        assert isinstance(config, dict)

    def test_caches_result(self):
        config1 = load_config()
        config2 = load_config()
        assert config1 is config2

    def test_reload_clears_cache(self):
        config1 = load_config()
        config2 = reload_config()
        assert config2 is not config1


class TestLoadConfigFromPath:
    def test_loads_custom_config(self, tmp_path):
        import resume_agent.config as cfg

        config_file = tmp_path / "custom.yaml"
        config_file.write_text("token:\n  warning_threshold: 5000\n", encoding="utf-8")
        # Manually clear cache because load_config ignores config_path when cached
        cfg._CONFIG = None
        config = load_config(config_file)
        assert config["token"]["warning_threshold"] == 5000
        assert config["token"]["cost_per_1k"] == 0.005

    def test_missing_file_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config["codex"]["max_retries"] == 3

    def test_invalid_yaml_returns_defaults(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("{{invalid yaml: [}", encoding="utf-8")
        config = load_config(config_file)
        assert config["codex"]["max_retries"] == 3
