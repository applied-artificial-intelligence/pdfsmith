"""Tests for the pdfsmith configuration system."""

import os
from pathlib import Path

import pytest

from pdfsmith.config import (
    BACKEND_DEFAULTS,
    BackendConfig,
    _find_config_file,
    _load_env_config,
    _load_yaml_config,
    get_backend_defaults,
    load_backend_config,
)


class TestBackendConfig:
    """Tests for the BackendConfig dataclass."""

    def test_get_existing_key(self):
        """get() should return value for existing key."""
        config = BackendConfig(
            backend_name="test",
            options={"key": "value"},
        )
        assert config.get("key") == "value"

    def test_get_missing_key_default(self):
        """get() should return default for missing key."""
        config = BackendConfig(backend_name="test", options={})
        assert config.get("missing") is None
        assert config.get("missing", "default") == "default"

    def test_get_bool_from_bool_true(self):
        """get_bool() should handle bool True."""
        config = BackendConfig(backend_name="test", options={"flag": True})
        assert config.get_bool("flag") is True

    def test_get_bool_from_bool_false(self):
        """get_bool() should handle bool False."""
        config = BackendConfig(backend_name="test", options={"flag": False})
        assert config.get_bool("flag") is False

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on"])
    def test_get_bool_true_strings(self, value):
        """get_bool() should parse truthy strings."""
        config = BackendConfig(backend_name="test", options={"flag": value})
        assert config.get_bool("flag") is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "off", "anything"])
    def test_get_bool_false_strings(self, value):
        """get_bool() should parse falsy strings."""
        config = BackendConfig(backend_name="test", options={"flag": value})
        assert config.get_bool("flag") is False

    def test_get_bool_missing_key_default(self):
        """get_bool() should return default for missing key."""
        config = BackendConfig(backend_name="test", options={})
        assert config.get_bool("missing") is False
        assert config.get_bool("missing", True) is True

    def test_get_bool_from_int(self):
        """get_bool() should handle int values."""
        config = BackendConfig(backend_name="test", options={"flag": 1})
        assert config.get_bool("flag") is True

        config = BackendConfig(backend_name="test", options={"flag": 0})
        assert config.get_bool("flag") is False

    def test_get_int_valid(self):
        """get_int() should parse integer values."""
        config = BackendConfig(backend_name="test", options={"count": 42})
        assert config.get_int("count") == 42

    def test_get_int_from_string(self):
        """get_int() should parse string integers."""
        config = BackendConfig(backend_name="test", options={"count": "42"})
        assert config.get_int("count") == 42

    def test_get_int_missing_default(self):
        """get_int() should return default for missing key."""
        config = BackendConfig(backend_name="test", options={})
        assert config.get_int("missing") == 0
        assert config.get_int("missing", 10) == 10

    def test_config_source_tracking(self):
        """Config should track where it came from."""
        config = BackendConfig(backend_name="test", source="explicit")
        assert config.source == "explicit"


class TestConfigFileFinding:
    """Tests for _find_config_file function."""

    def test_find_local_config(self, tmp_path, monkeypatch):
        """Should find project-local config first."""
        # Create local config
        monkeypatch.chdir(tmp_path)
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        local_config = local_dir / "test.yaml"
        local_config.write_text("key: value")

        result = _find_config_file("test")
        assert result is not None
        assert result.name == "test.yaml"

    def test_find_user_config(self, tmp_path, monkeypatch):
        """Should find user config if no local config."""
        # Set up temp home directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create user config only
        user_dir = tmp_path / ".config" / "pdfsmith"
        user_dir.mkdir(parents=True)
        user_config = user_dir / "test.yaml"
        user_config.write_text("key: value")

        result = _find_config_file("test")
        assert result is not None
        assert str(result).endswith("test.yaml")

    def test_no_config_returns_none(self, tmp_path, monkeypatch):
        """Should return None if no config found."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _find_config_file("nonexistent")
        assert result is None

    def test_local_takes_precedence(self, tmp_path, monkeypatch):
        """Local config should be found before user config."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create both local and user configs
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        (local_dir / "test.yaml").write_text("source: local")

        user_dir = tmp_path / ".config" / "pdfsmith"
        user_dir.mkdir(parents=True)
        (user_dir / "test.yaml").write_text("source: user")

        result = _find_config_file("test")
        assert result is not None
        assert ".pdfsmith" in str(result)


class TestYAMLParsing:
    """Tests for _load_yaml_config function."""

    def test_valid_yaml(self, tmp_path):
        """Should parse valid YAML."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
key: value
nested:
  inner: data
list:
  - item1
  - item2
"""
        )

        result = _load_yaml_config(yaml_file)
        assert result["key"] == "value"
        assert result["nested"]["inner"] == "data"
        assert result["list"] == ["item1", "item2"]

    def test_empty_yaml(self, tmp_path):
        """Should return empty dict for empty YAML."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = _load_yaml_config(yaml_file)
        assert result == {}

    def test_yaml_with_only_comments(self, tmp_path):
        """Should return empty dict for YAML with only comments."""
        yaml_file = tmp_path / "comments.yaml"
        yaml_file.write_text("# Just a comment\n# Another comment")

        result = _load_yaml_config(yaml_file)
        assert result == {}


class TestEnvConfig:
    """Tests for _load_env_config function."""

    def test_pdfsmith_prefixed_env_var(self, monkeypatch):
        """Should read PDFSMITH_<BACKEND>_<OPTION> format."""
        monkeypatch.setenv("PDFSMITH_DOCLING_OCR", "true")

        result = _load_env_config("docling", ["ocr"])
        assert result["ocr"] == "true"

    def test_backend_prefixed_env_var(self, monkeypatch):
        """Should read <BACKEND>_<OPTION> format."""
        monkeypatch.setenv("DOCLING_OCR", "true")

        result = _load_env_config("docling", ["ocr"])
        assert result["ocr"] == "true"

    def test_pdfsmith_prefix_takes_precedence(self, monkeypatch):
        """PDFSMITH_ prefix should take precedence."""
        monkeypatch.setenv("PDFSMITH_DOCLING_OCR", "pdfsmith_value")
        monkeypatch.setenv("DOCLING_OCR", "backend_value")

        result = _load_env_config("docling", ["ocr"])
        assert result["ocr"] == "pdfsmith_value"

    def test_unknown_option_not_loaded(self, monkeypatch):
        """Should only load known options."""
        monkeypatch.setenv("DOCLING_UNKNOWN", "value")

        result = _load_env_config("docling", ["ocr", "threads"])
        assert "unknown" not in result

    def test_backend_with_hyphen(self, monkeypatch):
        """Should handle backend names with hyphens."""
        monkeypatch.setenv("SOME_BACKEND_OPTION", "value")

        result = _load_env_config("some-backend", ["option"])
        assert result["option"] == "value"

    def test_no_env_vars_returns_empty(self, isolated_env):
        """Should return empty dict when no env vars set."""
        result = _load_env_config("docling", ["ocr", "threads"])
        assert result == {}


class TestConfigLoading:
    """Tests for load_backend_config function."""

    def test_load_defaults_only(self, tmp_path, monkeypatch, isolated_env):
        """Should use defaults when no other sources."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = load_backend_config("test")
        assert config.backend_name == "test"
        assert config.source == "defaults"

    def test_load_from_file(self, tmp_path, monkeypatch, isolated_env):
        """Should load config from YAML file."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create config file
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        (local_dir / "test.yaml").write_text("ocr: true\nthreads: 8")

        config = load_backend_config("test")
        assert config.get_bool("ocr") is True
        assert config.get_int("threads") == 8
        assert ".pdfsmith/test.yaml" in config.source

    def test_env_var_override(self, tmp_path, monkeypatch):
        """Environment variables should override file config."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create config file
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        (local_dir / "docling.yaml").write_text("ocr: false")

        # Set env var
        monkeypatch.setenv("DOCLING_OCR", "true")

        config = load_backend_config("docling", known_options=["ocr"])
        assert config.get_bool("ocr") is True
        assert config.source == "environment"

    def test_explicit_override(self, tmp_path, monkeypatch):
        """Explicit options should override all."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create config file
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        (local_dir / "docling.yaml").write_text("ocr: false")

        # Set env var
        monkeypatch.setenv("DOCLING_OCR", "false")

        config = load_backend_config(
            "docling",
            explicit_options={"ocr": True},
            known_options=["ocr"],
        )
        assert config.get_bool("ocr") is True
        assert config.source == "explicit"

    def test_precedence_order(self, tmp_path, monkeypatch):
        """Test full precedence: explicit > env > file > defaults."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create config file with all options
        local_dir = tmp_path / ".pdfsmith"
        local_dir.mkdir()
        (local_dir / "test.yaml").write_text(
            "file_only: from_file\nenv_override: from_file\nexplicit_override: from_file"
        )

        # Set env var for one option
        monkeypatch.setenv("TEST_ENV_OVERRIDE", "from_env")
        monkeypatch.setenv("TEST_EXPLICIT_OVERRIDE", "from_env")

        config = load_backend_config(
            "test",
            explicit_options={"explicit_override": "from_explicit"},
            known_options=["env_override", "explicit_override"],
        )

        assert config.get("file_only") == "from_file"
        assert config.get("env_override") == "from_env"
        assert config.get("explicit_override") == "from_explicit"


class TestBackendDefaults:
    """Tests for get_backend_defaults function."""

    def test_get_docling_defaults(self):
        """Should return docling defaults."""
        defaults = get_backend_defaults("docling")
        assert "do_ocr" in defaults
        assert defaults["do_ocr"] is False
        assert "do_table_structure" in defaults

    def test_get_marker_defaults(self):
        """Should return marker defaults."""
        defaults = get_backend_defaults("marker")
        assert "use_llm" in defaults
        assert defaults["use_llm"] is False

    def test_get_unstructured_defaults(self):
        """Should return unstructured defaults."""
        defaults = get_backend_defaults("unstructured")
        assert defaults["strategy"] == "fast"

    def test_get_unknown_backend_returns_empty(self):
        """Should return empty dict for unknown backend."""
        defaults = get_backend_defaults("unknown_backend")
        assert defaults == {}

    def test_defaults_are_copies(self):
        """Should return copies, not references."""
        defaults1 = get_backend_defaults("docling")
        defaults2 = get_backend_defaults("docling")

        defaults1["do_ocr"] = "modified"
        assert defaults2["do_ocr"] is False

    def test_backend_defaults_constant(self):
        """BACKEND_DEFAULTS should have expected backends."""
        assert "docling" in BACKEND_DEFAULTS
        assert "marker" in BACKEND_DEFAULTS
        assert "unstructured" in BACKEND_DEFAULTS
