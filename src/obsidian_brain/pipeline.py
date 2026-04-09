import logging
from pathlib import Path

from .analyzer import analyze
from .config import load_config
from .filter import is_similar_experience, should_process
from .generator import (
    generate_daily_doc,
    generate_experience_doc,
    generate_project_doc,
    update_project_doc,
)
from .parser import parse_transcript
from .project_mapper import resolve_project, resolve_projects
from .vault import load_processed_ids, save_processed_id, scan_experiences

logger = logging.getLogger(__name__)


def _extract_cwd_from_path(transcript_path: Path) -> str | None:
    """Extract the original cwd from the encoded transcript directory name."""
    encoded = transcript_path.parent.name
    if encoded.startswith("-"):
        return encoded.replace("-", "/")
    return None


def process_session(
    transcript_path: Path,
    vault_path: Path,
    min_messages: int = 3,
) -> Path | None:
    config = load_config(vault_path)
    min_msg = min_messages or config["min_messages"]
    projects_config = config.get("projects", {})

    parsed = parse_transcript(transcript_path)
    logger.info(f"Parsed session {parsed['session_id']}: {len(parsed['messages'])} messages")

    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids, min_msg):
        logger.info(f"Skipping session {parsed['session_id']}")
        return None

    cwd = _extract_cwd_from_path(transcript_path)

    # Gather existing experience titles for dedup
    exp_folder = config["folders"].get("experiences", "Experiences")
    existing_experiences = scan_experiences(vault_path, exp_folder)

    analysis = analyze(
        parsed,
        projects_config=projects_config,
        cwd=cwd,
        existing_experiences=existing_experiences,
        about=config.get("about"),
        model=config.get("model", "sonnet"),
    )

    if not analysis:
        logger.warning("Analysis returned empty for session %s", parsed["session_id"])
        return None

    # Post-process: resolve project names in daily_entries
    for entry in analysis.get("daily_entries", []):
        if entry.get("project"):
            entry["project"] = resolve_project(entry["project"], projects_config)

    # Collect resolved project names
    resolved_projects = []
    for entry in analysis.get("daily_entries", []):
        if entry["project"] and entry["project"] not in resolved_projects:
            resolved_projects.append(entry["project"])

    # Generate daily note
    daily_path = generate_daily_doc(
        vault_path=vault_path,
        daily_folder=config["folders"].get("daily", "Daily"),
        date=parsed["date"],
        daily_entries=analysis.get("daily_entries", []),
        tags=analysis.get("tags", []),
    )
    logger.info(f"Created/updated daily note: {daily_path}")

    # Generate experience notes (skip duplicates)
    for exp in analysis.get("experiences", []):
        title = exp.get("title", "unknown")
        try:
            if is_similar_experience(title, vault_path, exp_folder):
                logger.info("Skipping duplicate experience: %s", title)
                continue
            generate_experience_doc(
                experience=exp,
                conversation_slug=daily_path.stem,
                date=parsed["date"],
                projects=resolved_projects,
                vault_path=vault_path,
                exp_folder=exp_folder,
            )
            logger.info("Created experience: %s", title)
        except Exception:
            logger.warning("Failed to generate experience note: %s", title)

    # Update project docs
    for project_name in resolved_projects:
        project_path = vault_path / config["folders"]["projects"] / f"{project_name}.md"
        if project_path.exists():
            update_project_doc(
                doc_path=project_path,
                date=parsed["date"],
                summary=analysis["summary"],
                decisions=analysis.get("decisions"),
            )
            logger.info(f"Updated project: {project_name}")
        else:
            generate_project_doc(
                vault_path=vault_path,
                projects_folder=config["folders"]["projects"],
                project_name=project_name,
                date=parsed["date"],
                summary=analysis["summary"],
                decisions=analysis.get("decisions"),
            )
            logger.info(f"Created project: {project_name}")

    save_processed_id(vault_path, parsed["session_id"])
    logger.info(f"Session {parsed['session_id']} processed successfully")

    return daily_path
