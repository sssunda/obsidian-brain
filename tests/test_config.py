import yaml
from pathlib import Path
from obsidian_brain.config import load_config, DEFAULT_CONFIG


def test_load_config_defaults(tmp_path):
    """When no config.yaml exists, return defaults."""
    config = load_config(tmp_path)
    assert config["min_messages"] == 3
    assert config["max_transcript_chars"] == 50000
    assert config["max_retries"] == 3
    assert config["processed_retention_days"] == 30
    assert config["slug_language"] == "en"
    assert config["folders"]["conversations"] == "Conversations"
    assert config["folders"]["concepts"] == "Concepts"
    assert config["folders"]["projects"] == "Projects"


def test_load_config_from_file(tmp_path):
    """When config.yaml exists, merge with defaults."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "min_messages": 5,
        "slug_language": "ko",
    }))
    config = load_config(tmp_path)
    assert config["min_messages"] == 5
    assert config["slug_language"] == "ko"
    assert config["max_retries"] == 3


def test_load_config_vault_path_resolution(tmp_path):
    """vault_path in config is resolved to absolute path."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({"vault_path": str(tmp_path)}))
    config = load_config(tmp_path)
    assert Path(config["vault_path"]).is_absolute()
