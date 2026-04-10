from difflib import SequenceMatcher


def resolve_project(name: str, projects_config: dict, threshold: float = 0.7) -> str | None:
    """Resolve a project name to a canonical project via exact match, alias, or fuzzy match."""
    name_lower = name.lower()

    # Exact match
    for project_name in projects_config:
        if name_lower == project_name.lower():
            return project_name

    # Alias match
    for project_name, config in projects_config.items():
        for alias in config.get("aliases", []):
            if name_lower == alias.lower():
                return project_name

    # Substring match — "project-a-backend" contains "project-a"
    for project_name, config in projects_config.items():
        candidates = [project_name] + config.get("aliases", [])
        for candidate in candidates:
            if candidate.lower() in name_lower or name_lower in candidate.lower():
                return project_name

    # Fuzzy match against project names and aliases
    best_score = 0.0
    best_project = None
    for project_name, config in projects_config.items():
        candidates = [project_name] + config.get("aliases", [])
        for candidate in candidates:
            score = SequenceMatcher(None, name_lower, candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_project = project_name

    if best_score >= threshold:
        return best_project

    return None


def resolve_projects(names: list[str], projects_config: dict) -> list[str]:
    """Resolve a list of project names, deduplicate, drop unmatched."""
    seen = set()
    result = []
    for name in names:
        resolved = resolve_project(name, projects_config)
        if resolved and resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result
