import logging
from pathlib import Path

from .analyzer import analyze
from .config import load_config
from .filter import should_process
from .generator import (
    generate_concept_doc,
    generate_conversation_doc,
    generate_project_doc,
    update_concept_doc,
    update_project_doc,
)
from .parser import parse_transcript
from .vault import load_processed_ids, save_processed_id, scan_concepts, scan_projects

logger = logging.getLogger(__name__)


def process_session(
    transcript_path: Path,
    vault_path: Path,
    min_messages: int = 3,
    max_retries: int = 3,
) -> Path | None:
    config = load_config(vault_path)
    min_msg = min_messages or config["min_messages"]

    # Parse
    parsed = parse_transcript(transcript_path)
    logger.info(f"Parsed session {parsed['session_id']}: {len(parsed['messages'])} messages")

    # Filter
    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids, min_msg):
        logger.info(f"Skipping session {parsed['session_id']}")
        return None

    # Analyze
    concepts = scan_concepts(vault_path, config["folders"]["concepts"])
    projects = scan_projects(vault_path, config["folders"]["projects"])
    logger.info(f"Vault context: {len(concepts)} concepts, {len(projects)} projects")

    analysis = analyze(
        parsed,
        concepts=concepts,
        projects=projects,
        max_retries=config.get("max_retries", max_retries),
    )
    logger.info(f"Analysis complete: {analysis['title_slug']}")

    # Generate conversation doc
    conv_path = generate_conversation_doc(
        vault_path=vault_path,
        conv_folder=config["folders"]["conversations"],
        date=parsed["date"],
        session_id=parsed["session_id"],
        analysis=analysis,
    )
    conversation_slug = conv_path.stem
    logger.info(f"Created conversation: {conv_path}")

    # Build concept relations map
    concept_relations = {c["name"]: [] for c in analysis.get("concepts", [])}
    for pair in analysis.get("concept_relations", []):
        if len(pair) == 2:
            for name in pair:
                if name in concept_relations:
                    other = pair[1] if pair[0] == name else pair[0]
                    concept_relations[name].append(other)

    # Generate/update concept docs
    for concept in analysis.get("concepts", []):
        concept_name = concept.get("existing_match") or concept["name"]
        concept_path = vault_path / config["folders"]["concepts"] / f"{concept_name}.md"
        related = concept_relations.get(concept["name"], [])

        if concept_path.exists():
            update_concept_doc(
                doc_path=concept_path,
                conversation_slug=conversation_slug,
                date=parsed["date"],
                insight=concept.get("insight"),
            )
            logger.info(f"Updated concept: {concept_name}")
        else:
            generate_concept_doc(
                vault_path=vault_path,
                concepts_folder=config["folders"]["concepts"],
                concept=concept,
                date=parsed["date"],
                conversation_slug=conversation_slug,
                related_concepts=related,
            )
            logger.info(f"Created concept: {concept_name}")

    # Generate/update project docs
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

    # Record as processed
    save_processed_id(vault_path, parsed["session_id"])
    logger.info(f"Session {parsed['session_id']} processed successfully")

    return conv_path
