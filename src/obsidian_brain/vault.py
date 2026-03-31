import re
from pathlib import Path
from datetime import datetime, timedelta

import frontmatter


def scan_concepts(vault_path: Path, folder: str = "Concepts") -> list[str]:
    concepts_dir = vault_path / folder
    if not concepts_dir.exists():
        return []
    return [f.stem for f in concepts_dir.glob("*.md")]


def scan_projects(vault_path: Path, folder: str = "Projects") -> list[str]:
    projects_dir = vault_path / folder
    if not projects_dir.exists():
        return []
    return [f.stem for f in projects_dir.glob("*.md")]


def load_processed_ids(vault_path: Path) -> set[str]:
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    if not processed_file.exists():
        return set()
    text = processed_file.read_text().strip()
    if not text:
        return set()
    return {line.split("\t")[0] for line in text.splitlines() if line.strip()}


def save_processed_id(vault_path: Path, session_id: str) -> None:
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    with open(processed_file, "a") as f:
        f.write(f"{session_id}\t{datetime.now().isoformat()}\n")


def scan_existing_insights(vault_path: Path, folder: str = "Concepts") -> dict[str, list[str]]:
    """Read existing insights from concept docs, keyed by concept name."""
    concepts_dir = vault_path / folder
    if not concepts_dir.exists():
        return {}

    insights: dict[str, list[str]] = {}
    for f in concepts_dir.glob("*.md"):
        try:
            post = frontmatter.load(f)
            concept_name = f.stem
            concept_insights = []
            in_section = False
            for line in post.content.split("\n"):
                if line.strip() == "## 인사이트":
                    in_section = True
                    continue
                if in_section and line.startswith("## "):
                    break
                if in_section and line.strip().startswith("- ("):
                    match = re.match(r"^- \(\d{4}-\d{2}-\d{2}\) (.+)$", line.strip())
                    if match:
                        concept_insights.append(match.group(1))
            if concept_insights:
                insights[concept_name] = concept_insights
        except Exception:
            continue
    return insights


def rotate_processed(vault_path: Path, retention_days: int = 30) -> None:
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    if not processed_file.exists():
        return
    cutoff = datetime.now() - timedelta(days=retention_days)
    kept = []
    for line in processed_file.read_text().strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            try:
                ts = datetime.fromisoformat(parts[1])
                if ts >= cutoff:
                    kept.append(line)
                continue
            except ValueError:
                pass
        kept.append(line)
    processed_file.write_text("\n".join(kept) + "\n" if kept else "")
