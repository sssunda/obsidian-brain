"""Migrate existing vault docs to latest format."""
import logging
import re
import shutil
from pathlib import Path

import frontmatter

from .generator import generate_daily_doc
from .project_mapper import resolve_projects
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


def _extract_section_body(content: str, heading: str) -> str:
    """Return the body text of a ## section, or empty string."""
    lines = content.split("\n")
    body: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            body.append(line)
    return "\n".join(body).strip()


def _summary_to_bullet(summary: str, max_len: int = 180) -> str:
    """Condense a multi-sentence summary into a single daily-note bullet."""
    text = summary.strip().replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    # Take first sentence ending in Korean/English sentence terminators
    m = re.search(r"(.+?[.。다]\s)", text)
    if m and 20 <= len(m.group(1)) <= max_len:
        return m.group(1).strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rfind(" ")
    return (text[:cut] if cut > 40 else text[:max_len]) + "…"


def migrate_conversations_to_daily(vault_path: Path, config: dict) -> dict:
    """Convert legacy Conversations/*/*.md files into new Daily/*.md notes.

    Each conversation becomes a single bullet (its condensed summary) under
    the [[project]] section of the corresponding Daily note. Unmatched
    conversations land in `## 기타`. Tags are merged per day.
    Original files are moved to 레거시/Conversations/ for reference.
    """
    conv_dir = vault_path / "Conversations"
    if not conv_dir.exists():
        return {"converted": 0, "skipped": 0, "days": 0}

    daily_folder = config["folders"]["daily"]
    projects_config = config.get("projects", {}) or {}

    by_date: dict[str, dict] = {}
    converted = 0
    skipped = 0

    files = sorted(conv_dir.rglob("*.md"))
    for md_file in files:
        try:
            post = frontmatter.load(md_file)
        except Exception as e:
            logger.warning(f"Skip {md_file.name}: {e}")
            skipped += 1
            continue

        date = post.get("date")
        if not date:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", md_file.stem)
            date = m.group(1) if m else None
        if not date:
            logger.warning(f"Skip {md_file.name}: no date")
            skipped += 1
            continue
        date = str(date)

        summary = _extract_section_body(post.content, "## 요약")
        bullet = _summary_to_bullet(summary or str(post.get("title", "")))
        if not bullet:
            skipped += 1
            continue

        raw_projects = post.get("projects") or []
        resolved = resolve_projects(list(raw_projects), projects_config)
        project = resolved[0] if resolved else None

        tags = post.get("tags") or []

        slot = by_date.setdefault(date, {"by_project": {}, "tags": []})
        slot["by_project"].setdefault(project, []).append(bullet)
        for t in tags:
            if t not in slot["tags"]:
                slot["tags"].append(t)

        converted += 1

    # Write daily notes (generate_daily_doc handles create-or-append)
    for date, slot in sorted(by_date.items()):
        # Place mapped projects first, 기타 last for stable ordering
        ordered_keys = [k for k in slot["by_project"] if k is not None] + (
            [None] if None in slot["by_project"] else []
        )
        daily_entries = [
            {"project": k, "bullets": slot["by_project"][k]} for k in ordered_keys
        ]
        generate_daily_doc(
            vault_path=vault_path,
            daily_folder=daily_folder,
            date=date,
            daily_entries=daily_entries,
            tags=slot["tags"],
        )

    # Archive old Conversations folder to 레거시/
    archive_root = vault_path / "레거시"
    archive_root.mkdir(exist_ok=True)
    archive_target = archive_root / "Conversations"
    if archive_target.exists():
        # Merge: move month dirs one by one
        for child in conv_dir.iterdir():
            dest = archive_target / child.name
            if dest.exists():
                for sub in child.rglob("*"):
                    if sub.is_file():
                        rel = sub.relative_to(child)
                        out = dest / rel
                        out.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(sub), str(out))
                shutil.rmtree(child)
            else:
                shutil.move(str(child), str(dest))
        conv_dir.rmdir()
    else:
        shutil.move(str(conv_dir), str(archive_target))

    logger.info(
        f"Converted {converted} conversations → {len(by_date)} daily notes "
        f"({skipped} skipped). Archived to 레거시/Conversations/"
    )
    return {"converted": converted, "skipped": skipped, "days": len(by_date)}


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


def migrate_vault(vault_path: Path, config: dict | None = None) -> None:
    """Run all migrations."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info(f"Migrating vault: {vault_path}")
    if config is None:
        from .config import load_config
        config = load_config(vault_path)
    c1 = migrate_conversations_to_daily(vault_path, config)
    c2 = migrate_concepts_to_experiences(vault_path)
    c3 = migrate_projects(vault_path)
    c4 = migrate_digest(vault_path)
    logger.info(
        f"Done: {c1['converted']} conversations → {c1['days']} daily notes, "
        f"{c2['removed_concepts']} concepts removed, "
        f"{c3} projects, {c4} digest migrated"
    )
