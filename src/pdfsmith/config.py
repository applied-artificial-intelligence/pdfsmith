"""
Backend configuration loader with multi-source support.

Configuration sources (in order of precedence):
1. Explicit options passed to backend constructor
2. Environment variables (PDFSMITH_<BACKEND>_<OPTION> or <BACKEND>_<OPTION>)
3. Project-local config: ./.pdfsmith/<backend>.yaml
4. User config: ~/.config/pdfsmith/<backend>.yaml
5. Built-in defaults

Example usage:
    config = load_backend_config("docling")
    # Returns merged config from all sources
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BackendConfig:
    """Configuration container for a backend."""

    backend_name: str
    options: dict[str, Any] = field(default_factory=dict)
    source: str = "defaults"  # Where the config came from

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.options.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean config value."""
        val = self.options.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer config value."""
        val = self.options.get(key)
        if val is None:
            return default
        return int(val)


def _find_config_file(backend_name: str) -> Path | None:
    """Find config file for backend, checking multiple locations."""
    # Project-local config
    local_config = Path(f".pdfsmith/{backend_name}.yaml")
    if local_config.exists():
        return local_config

    # User config
    user_config = Path.home() / ".config" / "pdfsmith" / f"{backend_name}.yaml"
    if user_config.exists():
        return user_config

    return None


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_env_config(backend_name: str, known_options: list[str]) -> dict[str, Any]:
    """Load config from environment variables.

    Format: PDFSMITH_<BACKEND>_<OPTION> or <BACKEND>_<OPTION>
    Examples:
        DOCLING_OCR=true
        DOCLING_TABLE_STRUCTURE=false
        PDFSMITH_DOCLING_THREADS=4
    """
    config = {}
    backend_upper = backend_name.upper().replace("-", "_")

    for option in known_options:
        option_upper = option.upper()

        # Try both formats
        for prefix in [f"PDFSMITH_{backend_upper}_", f"{backend_upper}_"]:
            env_key = f"{prefix}{option_upper}"
            val = os.environ.get(env_key)
            if val is not None:
                config[option] = val
                break

    return config


def load_backend_config(
    backend_name: str,
    explicit_options: dict[str, Any] | None = None,
    known_options: list[str] | None = None,
) -> BackendConfig:
    """
    Load backend configuration from multiple sources.

    Args:
        backend_name: Backend identifier (e.g., "docling", "marker")
        explicit_options: Options passed directly (highest priority)
        known_options: List of known option names (for env var lookup)

    Returns:
        BackendConfig with merged options from all sources
    """
    known_options = known_options or []
    merged_options: dict[str, Any] = {}
    source = "defaults"

    # 1. Load from config file (lowest priority file source)
    config_path = _find_config_file(backend_name)
    if config_path:
        file_options = _load_yaml_config(config_path)
        merged_options.update(file_options)
        source = str(config_path)

    # 2. Override with environment variables
    env_options = _load_env_config(backend_name, known_options)
    if env_options:
        merged_options.update(env_options)
        source = "environment"

    # 3. Override with explicit options (highest priority)
    if explicit_options:
        merged_options.update(explicit_options)
        source = "explicit"

    return BackendConfig(
        backend_name=backend_name,
        options=merged_options,
        source=source,
    )


# Default configurations for backends that need them
BACKEND_DEFAULTS: dict[str, dict[str, Any]] = {
    "docling": {
        "do_ocr": False,  # Disabled by default for performance
        "do_table_structure": True,
        "num_threads": 4,
        "device": "auto",
        "ocr_languages": ["en"],
    },
    "marker": {
        "use_llm": False,
        "batch_size": 4,
    },
    "unstructured": {
        "strategy": "fast",
        "include_page_breaks": True,
    },
}


def get_backend_defaults(backend_name: str) -> dict[str, Any]:
    """Get default configuration for a backend."""
    return BACKEND_DEFAULTS.get(backend_name, {}).copy()
