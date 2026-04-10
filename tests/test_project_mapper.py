from obsidian_brain.project_mapper import resolve_project


def test_exact_match():
    projects = {
        "project-a": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("project-a", projects) == "project-a"


def test_alias_match():
    projects = {
        "project-a": {"aliases": ["backend", "schema"], "description": ""},
    }
    assert resolve_project("backend", projects) == "project-a"
    assert resolve_project("schema", projects) == "project-a"


def test_fuzzy_match():
    projects = {
        "project-a": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("project-a-backend", projects) == "project-a"


def test_no_match_returns_none():
    projects = {
        "project-a": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("random-thing", projects) is None


def test_case_insensitive():
    projects = {
        "project-a": {"aliases": ["Backend"], "description": ""},
    }
    assert resolve_project("BACKEND", projects) == "project-a"


def test_personal_catches_aliases():
    projects = {
        "personal": {"aliases": ["obsidian-brain", "eta-scout", "theta-todo"], "description": ""},
    }
    assert resolve_project("obsidian-brain", projects) == "personal"
    assert resolve_project("eta-scout", projects) == "personal"


def test_resolve_list():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "project-a": {"aliases": ["backend"], "description": ""},
        "personal": {"aliases": ["obsidian-brain"], "description": ""},
    }
    result = resolve_projects(["backend", "obsidian-brain", "unknown"], projects_config)
    assert result == ["project-a", "personal"]


def test_resolve_list_deduplicates():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "project-a": {"aliases": ["backend", "schema"], "description": ""},
    }
    result = resolve_projects(["backend", "schema", "project-a"], projects_config)
    assert result == ["project-a"]
