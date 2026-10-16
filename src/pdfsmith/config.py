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

import math
import os
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BackendConfig:
    """Configuration container for a backend."""

    backend_name: str
    options: dict[str, Any] = field(default_factory=dict)
    source: str = "defaults"  # Where the config came from

    def __post_init__(self) -> None:
        self.options = deepcopy(self.options)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return deepcopy(self.options.get(key, default))

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean config value."""
        val = self.options.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            normalized = val.strip().lower()
            if normalized in ("true", "1", "yes", "on"):
                return True
            if normalized in ("false", "0", "no", "off"):
                return False
        elif type(val) is int and val in (0, 1):
            return bool(val)
        raise ValueError(f"Invalid boolean for {key}: {val!r}")

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer config value."""
        val = self.options.get(key)
        if val is None:
            return default
        if isinstance(val, bool) or not isinstance(val, int | str):
            raise ValueError(f"Invalid integer for {key}")
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
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("YAML configuration requires pdfsmith[config]") from exc

    with open(path) as f:
        value = yaml.safe_load(f)
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(
            f"YAML configuration must be a mapping with string keys: {path}"
        )
    return value


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
    aliases = (
        {
            "do_ocr": ("ocr",),
            "do_table_structure": ("table_structure",),
            "num_threads": ("threads",),
        }
        if backend_name == "docling"
        else {}
    )
    recognized = {
        key.upper()
        for option in known_options
        for key in (option, *aliases.get(option, ()))
    }
    prefix = f"PDFSMITH_{backend_upper}_"
    for key in os.environ:
        if key.startswith(prefix) and key[len(prefix) :] not in recognized:
            raise ValueError(f"Unknown configuration option: {key}")
    for option in known_options:
        names = (option, *aliases.get(option, ()))
        for prefix in (f"PDFSMITH_{backend_upper}_", f"{backend_upper}_"):
            values = [
                os.environ[prefix + name.upper()]
                for name in names
                if prefix + name.upper() in os.environ
            ]
            if len(set(values)) > 1:
                raise ValueError(f"Conflicting aliases for {backend_name}.{option}")
            if values:
                config[option] = values[0]
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
    paths = [
        Path.home() / ".config" / "pdfsmith" / f"{backend_name}.yaml",
        Path(".pdfsmith") / f"{backend_name}.yaml",
    ]
    for config_path in paths:
        if config_path.is_file():
            merged_options.update(_load_yaml_config(config_path))
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
    return deepcopy(BACKEND_DEFAULTS.get(backend_name, {}))


@dataclass(frozen=True)
class Option:
    default: Any
    kind: type
    choices: tuple[Any, ...] = ()
    minimum: float | None = None
    allow_none: bool = False


def normalize_options(
    backend: str, options: dict[str, Any], schema: dict[str, Option]
) -> dict[str, Any]:
    unknown = set(options) - set(schema)
    if unknown:
        raise ValueError(f"Unknown {backend} options: {sorted(unknown)}")
    result: dict[str, Any] = {}
    for key, spec in schema.items():
        value = deepcopy(options.get(key, spec.default))
        if value is None and spec.allow_none:
            result[key] = None
            continue
        if value is None:
            raise ValueError(f"{backend}.{key} does not accept null")
        if spec.kind is bool:
            value = BackendConfig(backend, {key: value}).get_bool(key)
        elif spec.kind in (float, int):
            if isinstance(value, bool):
                raise ValueError(f"{backend}.{key} must be {spec.kind.__name__}")
            if isinstance(value, str):
                try:
                    value = spec.kind(value)
                except ValueError as exc:
                    raise ValueError(f"Invalid {backend}.{key}") from exc
            if not isinstance(value, int | float) or (
                spec.kind is int and type(value) is not int
            ):
                raise ValueError(f"{backend}.{key} must be {spec.kind.__name__}")
            value = spec.kind(value)
            if not math.isfinite(value):
                raise ValueError(f"{backend}.{key} must be finite")
        elif not isinstance(value, spec.kind):
            raise ValueError(f"{backend}.{key} must be {spec.kind.__name__}")
        if spec.choices and value not in spec.choices:
            raise ValueError(f"Invalid {backend}.{key}; choose {spec.choices}")
        if spec.minimum is not None and value < spec.minimum:
            raise ValueError(f"{backend}.{key} must be >= {spec.minimum}")
        result[key] = value
    return result
