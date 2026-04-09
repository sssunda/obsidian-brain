from obsidian_brain.project_mapper import resolve_project


def test_exact_match():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("wishket", projects) == "wishket"


def test_alias_match():
    projects = {
        "wishket": {"aliases": ["backend", "schema"], "description": ""},
    }
    assert resolve_project("backend", projects) == "wishket"
    assert resolve_project("schema", projects) == "wishket"


def test_fuzzy_match():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("wishket-backend", projects) == "wishket"


def test_no_match_returns_none():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("random-thing", projects) is None


def test_case_insensitive():
    projects = {
        "wishket": {"aliases": ["Backend"], "description": ""},
    }
    assert resolve_project("BACKEND", projects) == "wishket"


def test_daeun_catches_personal_projects():
    projects = {
        "daeun": {"aliases": ["obsidian-brain", "matjip-scout", "pomodoro-todo"], "description": ""},
    }
    assert resolve_project("obsidian-brain", projects) == "daeun"
    assert resolve_project("matjip-scout", projects) == "daeun"


def test_resolve_list():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "wishket": {"aliases": ["backend"], "description": ""},
        "daeun": {"aliases": ["obsidian-brain"], "description": ""},
    }
    result = resolve_projects(["backend", "obsidian-brain", "unknown"], projects_config)
    assert result == ["wishket", "daeun"]


def test_resolve_list_deduplicates():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "wishket": {"aliases": ["backend", "schema"], "description": ""},
    }
    result = resolve_projects(["backend", "schema", "wishket"], projects_config)
    assert result == ["wishket"]
