from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "vault_path": None,
    "min_messages": 3,
    "max_transcript_chars": 50000,
    "max_retries": 3,
    "processed_retention_days": 30,
    "slug_language": "en",
    "batch_limit": 10,
    "rate_limit_seconds": 2,
    "max_insights": 10,
    "similarity_threshold": 0.5,
    "truncate_head": 15,
    "truncate_tail": 85,
    "model": "sonnet",
    "folders": {
        "conversations": "Conversations",
        "concepts": "Concepts",
        "projects": "Projects",
    },
}


def load_config(vault_path: Path) -> dict:
    """Load config from .obsidian-brain/config.yaml, merged with defaults."""
    config = _deep_copy(DEFAULT_CONFIG)
    config["vault_path"] = str(vault_path.resolve())

    config_file = vault_path / ".obsidian-brain" / "config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)

    if config.get("vault_path"):
        config["vault_path"] = str(Path(config["vault_path"]).expanduser().resolve())

    _validate(config)
    return config


def _validate(config: dict) -> None:
    """Validate config values."""
    int_fields = ["min_messages", "max_retries", "processed_retention_days", "batch_limit", "max_insights", "truncate_head", "truncate_tail"]
    for field in int_fields:
        val = config.get(field)
        if val is not None and (not isinstance(val, int) or val < 0):
            raise ValueError(f"Config '{field}' must be a non-negative integer, got: {val}")

    threshold = config.get("similarity_threshold")
    if threshold is not None and (not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1):
        raise ValueError(f"Config 'similarity_threshold' must be 0~1, got: {threshold}")


def _deep_copy(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        result[k] = _deep_copy(v) if isinstance(v, dict) else v
    return result


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
