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
    assert config["folders"]["daily"] == "Daily"
    assert config["folders"]["experiences"] == "Experiences"
    assert config["folders"]["projects"] == "Projects"
    assert "conversations" not in config["folders"]
    assert config["projects"] == {}
    assert config["about"] == ""


def test_load_config_from_file(tmp_path):
    """When config.yaml exists, merge with defaults."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "min_messages": 5,
        "slug_language": "ko",
        "about": "백엔드 개발자",
        "projects": {
            "my-project": {
                "aliases": ["mp"],
                "description": "내 프로젝트",
            },
        },
    }))
    config = load_config(tmp_path)
    assert config["min_messages"] == 5
    assert config["slug_language"] == "ko"
    assert config["max_retries"] == 3
    assert config["about"] == "백엔드 개발자"
    assert "my-project" in config["projects"]


def test_load_config_vault_path_resolution(tmp_path):
    """vault_path in config is resolved to absolute path."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({"vault_path": str(tmp_path)}))
    config = load_config(tmp_path)
    assert Path(config["vault_path"]).is_absolute()


def test_default_config_has_projects_and_about():
    """Default config includes empty projects dict and about string."""
    assert "projects" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["projects"] == {}
    assert "about" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["about"] == ""


def test_default_config_has_daily_folder():
    """Default config includes daily folder."""
    assert DEFAULT_CONFIG["folders"]["daily"] == "Daily"


def test_config_projects_from_yaml(tmp_path):
    """Projects defined in config.yaml are loaded correctly."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "projects": {
            "alpha": {"aliases": ["a1"], "description": "Alpha project"},
            "beta": {"aliases": ["b1"], "description": "Beta project"},
        },
    }))
    config = load_config(tmp_path)
    assert "alpha" in config["projects"]
    assert "beta" in config["projects"]
    assert config["projects"]["alpha"]["aliases"] == ["a1"]
