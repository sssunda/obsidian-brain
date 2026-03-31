import re
from pathlib import Path

import frontmatter

from .similarity import has_similar_insight, trim_insights


def _append_to_section(content: str, section_heading: str, new_line: str) -> str:
    """Append a line at the end of a markdown section."""
    if section_heading not in content:
        return content
    lines = content.split("\n")
    insert_idx = len(lines)
    in_section = False
    for i, line in enumerate(lines):
        if line.strip() == section_heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            insert_idx = i
            break
    lines.insert(insert_idx, new_line)
    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in file paths."""
    return re.sub(r'[<>:"/\\|?*]', '-', name).strip('. ')


def resolve_slug_conflict(directory: Path, slug: str) -> str:
    if not (directory / f"{slug}.md").exists():
        return slug
    counter = 2
    while (directory / f"{slug}-{counter}.md").exists():
        counter += 1
    return f"{slug}-{counter}"


def generate_conversation_doc(
    vault_path: Path,
    conv_folder: str,
    date: str,
    session_id: str,
    analysis: dict,
) -> Path:
    year_month = date[:7]
    conv_dir = vault_path / conv_folder / year_month
    conv_dir.mkdir(parents=True, exist_ok=True)

    slug = resolve_slug_conflict(conv_dir, f"{date}-{analysis['title_slug']}")
    filepath = conv_dir / f"{slug}.md"

    concepts = [c["name"] for c in analysis.get("concepts", [])]
    concept_links = "\n".join(f"- [[{c}]]" for c in concepts)
    project_links = "\n".join(f"- [[{p}]]" for p in analysis.get("projects", []))
    decisions = "\n".join(f"- {d}" for d in analysis.get("decisions", []))

    reasoning_lines = ""
    for rp in analysis.get("reasoning_patterns", []):
        reasoning_lines += f"- **상황:** {rp['situation']}\n  **선택:** {rp['choice']}\n  **이유:** {rp['why']}\n"

    preferences = "\n".join(f"- {p}" for p in analysis.get("preferences", []))

    # Build content with only non-empty sections
    sections = [f"## 요약\n{analysis['summary']}"]

    if reasoning_lines.strip():
        sections.append(f"## 의사결정 패턴\n{reasoning_lines}")
    if preferences.strip():
        sections.append(f"## 드러난 선호/원칙\n{preferences}")
    if decisions.strip():
        sections.append(f"## 핵심 결정사항\n{decisions}")
    if concept_links.strip():
        sections.append(f"## 관련 개념\n{concept_links}")
    if project_links.strip():
        sections.append(f"## 관련 프로젝트\n{project_links}")

    content = "\n\n".join(sections)

    # Title: use full summary, truncate at sentence boundary
    title = analysis["summary"]
    if len(title) > 80:
        cut = title[:80].rfind(" ")
        title = title[:cut] if cut > 30 else title[:80]

    post = frontmatter.Post(
        content=content,
        type="conversation",
        cssclasses=["ob-conversation"],
        source="claude-code",
        session_id=session_id,
        date=date,
        title=title,
        tags=analysis.get("tags", []),
        concepts=concepts,
        projects=analysis.get("projects", []),
    )

    filepath.write_text(frontmatter.dumps(post))
    return filepath


def generate_concept_doc(
    vault_path: Path,
    concepts_folder: str,
    concept: dict,
    date: str,
    conversation_slug: str,
    related_concepts: list[str] | None = None,
) -> Path:
    concepts_dir = vault_path / concepts_folder
    concepts_dir.mkdir(parents=True, exist_ok=True)

    filepath = concepts_dir / f"{sanitize_filename(concept['name'])}.md"

    related = related_concepts or []
    related_links = "\n".join(f"- [[{r}]]" for r in related if r != concept["name"])

    insight_section = ""
    if concept.get("insight"):
        insight_section = f"- ({date}) {concept['insight']}"

    description = concept.get('description') or ''

    post = frontmatter.Post(
        content=f"""# {concept['name']}

{description}

## 인사이트
{insight_section}

## 관련 개념
{related_links}""",
        type="concept",
        cssclasses=["ob-concept"],
        created=date,
        updated=date,
        aliases=concept.get("aliases", []),
        conversations=[conversation_slug],
    )

    filepath.write_text(frontmatter.dumps(post))
    return filepath


def update_concept_doc(
    doc_path: Path,
    conversation_slug: str,
    date: str,
    insight: str | None = None,
) -> None:
    try:
        post = frontmatter.load(doc_path)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Skipping corrupted concept doc {doc_path.name}: {e}")
        return

    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add insight at end of section (chronological order), skip similar duplicates
    if insight and not has_similar_insight(insight, post.content):
        insight_line = f"- ({date}) {insight}"
        if "## 인사이트" in post.content:
            post.content = _append_to_section(post.content, "## 인사이트", insight_line)
        else:
            post.content += f"\n\n## 인사이트\n{insight_line}"

    # Trim to max insights to prevent unbounded growth
    from .similarity import MAX_INSIGHTS
    post.content = trim_insights(post.content, max_count=MAX_INSIGHTS)

    doc_path.write_text(frontmatter.dumps(post))


def generate_project_doc(
    vault_path: Path,
    projects_folder: str,
    project_name: str,
    date: str,
    conversation_slug: str,
    summary: str,
    decisions: list[str] | None = None,
) -> Path:
    projects_dir = vault_path / projects_folder
    projects_dir.mkdir(parents=True, exist_ok=True)

    filepath = projects_dir / f"{sanitize_filename(project_name)}.md"

    decision_lines = "\n".join(f"- {d}" for d in (decisions or []))

    post = frontmatter.Post(
        content=f"""# {project_name}

## 대화 타임라인
- [[{conversation_slug}]] — {summary}

## 핵심 결정사항
{decision_lines}""",
        type="project",
        cssclasses=["ob-project"],
        created=date,
        updated=date,
        status="active",
        conversations=[conversation_slug],
    )

    filepath.write_text(frontmatter.dumps(post))
    return filepath


def update_project_doc(
    doc_path: Path,
    conversation_slug: str,
    date: str,
    summary: str,
    decisions: list[str] | None = None,
) -> None:
    try:
        post = frontmatter.load(doc_path)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Skipping corrupted project doc {doc_path.name}: {e}")
        return

    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add to timeline at end of section
    timeline_entry = f"- [[{conversation_slug}]] — {summary}"
    if "## 대화 타임라인" in post.content:
        post.content = _append_to_section(post.content, "## 대화 타임라인", timeline_entry)

    # Add decisions at end of section
    if decisions:
        for d in decisions:
            if d not in post.content:
                post.content = _append_to_section(post.content, "## 핵심 결정사항", f"- {d}")

    doc_path.write_text(frontmatter.dumps(post))
