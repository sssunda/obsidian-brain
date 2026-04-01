"""Migrate existing vault docs to latest format."""
import logging
import re
from pathlib import Path

import frontmatter

import shutil

from .similarity import is_similar

logger = logging.getLogger(__name__)


def deduplicate_insights(content: str, threshold: float = 0.5) -> str:
    """Remove near-duplicate insight lines within ## 인사이트 section."""
    lines = content.split("\n")
    result = []
    in_section = False
    kept_insights: list[str] = []

    for line in lines:
        if line.strip() == "## 인사이트":
            in_section = True
            result.append(line)
            continue
        if in_section and line.startswith("## "):
            in_section = False

        if in_section and line.strip().startswith("- ("):
            # Extract insight text after date prefix
            match = re.match(r"^- \(\d{4}-\d{2}-\d{2}\) (.+)$", line.strip())
            insight_text = match.group(1) if match else line.strip()

            is_dup = any(is_similar(insight_text, k, threshold) for k in kept_insights)
            if not is_dup:
                kept_insights.append(insight_text)
                result.append(line)
            else:
                logger.debug(f"  Removed duplicate insight: {insight_text[:50]}")
        else:
            result.append(line)

    return "\n".join(result)


def remove_empty_sections(content: str) -> str:
    """Remove markdown sections that have no content."""
    lines = content.split("\n")
    result = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("## "):
            # Look ahead to see if section has content
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                j += 1
            section_body = "\n".join(lines[i + 1:j]).strip()
            if section_body:
                result.extend(lines[i:j])
            i = j
        else:
            result.append(lines[i])
            i += 1
    # Clean up multiple consecutive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', "\n".join(result))
    return cleaned.strip()


def migrate_conversations(vault_path: Path) -> int:
    """Migrate conversation docs: add type, remove empty sections."""
    conv_dir = vault_path / "Conversations"
    if not conv_dir.exists():
        return 0

    count = 0
    for month_dir in conv_dir.iterdir():
        if not month_dir.is_dir():
            continue
        for md_file in month_dir.glob("*.md"):
            try:
                post = frontmatter.load(md_file)
                changed = False

                # Add type and cssclasses if missing
                if "type" not in post.metadata:
                    post["type"] = "conversation"
                    changed = True
                if "cssclasses" not in post.metadata:
                    post["cssclasses"] = ["ob-conversation"]
                    changed = True

                # Remove empty sections
                cleaned = remove_empty_sections(post.content)
                if cleaned != post.content:
                    post.content = cleaned
                    changed = True

                if changed:
                    md_file.write_text(frontmatter.dumps(post))
                    count += 1
            except Exception as e:
                logger.warning(f"Skip {md_file.name}: {e}")

    logger.info(f"Migrated {count} conversation docs")
    return count


def migrate_concepts_to_experiences(vault_path: Path) -> dict:
    """Migrate vault from concepts to experiences structure."""
    concepts_dir = vault_path / "Concepts"
    experiences_dir = vault_path / "Experiences"

    result = {"removed_concepts": 0, "created_experiences_dir": False}

    # Create Experiences directory
    if not experiences_dir.exists():
        experiences_dir.mkdir(parents=True)
        result["created_experiences_dir"] = True

    # Remove old Concepts directory if it exists
    if concepts_dir.exists():
        result["removed_concepts"] = sum(1 for _ in concepts_dir.glob("*.md"))
        shutil.rmtree(concepts_dir)

    return result


def migrate_digest(vault_path: Path) -> int:
    """Migrate digest doc: add cssclasses if missing."""
    digest_path = vault_path / "My Patterns.md"
    if not digest_path.exists():
        return 0
    try:
        post = frontmatter.load(digest_path)
        if "cssclasses" not in post.metadata:
            post["cssclasses"] = ["ob-digest"]
            digest_path.write_text(frontmatter.dumps(post))
            logger.info("Migrated My Patterns.md")
            return 1
    except Exception as e:
        logger.warning(f"Skip My Patterns.md: {e}")
    return 0


def migrate_projects(vault_path: Path) -> int:
    """Migrate project docs: add cssclasses if missing."""
    projects_dir = vault_path / "Projects"
    if not projects_dir.exists():
        return 0
    count = 0
    for md_file in projects_dir.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            if "cssclasses" not in post.metadata:
                post["cssclasses"] = ["ob-project"]
                md_file.write_text(frontmatter.dumps(post))
                count += 1
        except Exception as e:
            logger.warning(f"Skip {md_file.name}: {e}")
    logger.info(f"Migrated {count} project docs")
    return count


def migrate_vault(vault_path: Path) -> None:
    """Run all migrations."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info(f"Migrating vault: {vault_path}")
    c1 = migrate_conversations(vault_path)
    c2 = migrate_concepts_to_experiences(vault_path)
    c3 = migrate_projects(vault_path)
    c4 = migrate_digest(vault_path)
    logger.info(f"Done: {c1} conversations, {c2['removed_concepts']} concepts removed, {c3} projects, {c4} digest migrated")
