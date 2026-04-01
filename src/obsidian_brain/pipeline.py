import logging
from pathlib import Path

from .analyzer import analyze
from .config import load_config
from .filter import is_similar_conversation, should_process
from .generator import (
    generate_experience_doc,
    generate_conversation_doc,
    generate_project_doc,
    update_project_doc,
)
from .parser import parse_transcript
from .vault import load_processed_ids, save_processed_id, scan_projects

logger = logging.getLogger(__name__)


def _extract_cwd_from_path(transcript_path: Path) -> str | None:
    """Extract the original cwd from the encoded transcript directory name."""
    # Transcript lives at ~/.claude/projects/{encoded-cwd}/{session}.jsonl
    # encoded-cwd replaces / with -
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

    parsed = parse_transcript(transcript_path)
    logger.info(f"Parsed session {parsed['session_id']}: {len(parsed['messages'])} messages")

    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids, min_msg):
        logger.info(f"Skipping session {parsed['session_id']}")
        return None

    projects = scan_projects(vault_path, config["folders"]["projects"])
    cwd = _extract_cwd_from_path(transcript_path)

    analysis = analyze(
        parsed,
        projects=projects,
        cwd=cwd,
        model=config.get("model", "sonnet"),
    )

    if not analysis:
        logger.warning("Analysis returned empty for session %s", parsed["session_id"])
        return None

    if is_similar_conversation(
        summary=analysis["summary"],
        vault_path=vault_path,
        conv_folder=config["folders"]["conversations"],
        date=parsed["date"],
    ):
        logger.info("Similar conversation exists, skipping %s", parsed["session_id"])
        save_processed_id(vault_path, parsed["session_id"])
        return None

    conv_path = generate_conversation_doc(
        vault_path=vault_path,
        conv_folder=config["folders"]["conversations"],
        date=parsed["date"],
        session_id=parsed["session_id"],
        analysis=analysis,
    )
    conversation_slug = conv_path.stem
    logger.info(f"Created conversation: {conv_path}")

    # Generate experience notes
    for exp in analysis.get("experiences", []):
        try:
            generate_experience_doc(
                experience=exp,
                conversation_slug=conversation_slug,
                date=parsed["date"],
                projects=analysis.get("projects", []),
                vault_path=vault_path,
                exp_folder=config["folders"].get("experiences", "Experiences"),
            )
            logger.info("Created experience: %s", exp.get("title", "unknown"))
        except Exception:
            logger.warning("Failed to generate experience note: %s", exp.get("title", "unknown"))

    # Generate/update project docs (unchanged from current code)
    for project_name in analysis.get("projects", []):
        project_path = vault_path / config["folders"]["projects"] / f"{project_name}.md"
        if project_path.exists():
            update_project_doc(
                doc_path=project_path,
                conversation_slug=conversation_slug,
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
                conversation_slug=conversation_slug,
                summary=analysis["summary"],
                decisions=analysis.get("decisions"),
            )
            logger.info(f"Created project: {project_name}")

    save_processed_id(vault_path, parsed["session_id"])
    logger.info(f"Session {parsed['session_id']} processed successfully")

    return conv_path
