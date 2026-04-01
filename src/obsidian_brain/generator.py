import re
from pathlib import Path

import frontmatter


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

    experiences = analysis.get("experiences", [])
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
    if experiences:
        exp_links = "\n".join(f"- [[{e['title']}]]" for e in experiences)
        sections.append(f"## 관련 경험\n{exp_links}")
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
        experiences=[e["title"] for e in experiences],
        projects=analysis.get("projects", []),
    )

    filepath.write_text(frontmatter.dumps(post))
    return filepath


def generate_experience_doc(
    experience: dict,
    conversation_slug: str,
    date: str,
    projects: list[str],
    vault_path: Path,
    exp_folder: str = "Experiences",
) -> Path:
    """Generate a single experience note."""
    title = experience["title"]
    exp_type = experience["experience_type"]
    sections = experience["sections"]
    tags = experience.get("tags", [])

    # Build sections content
    body_parts = []
    for heading, text in sections.items():
        body_parts.append(f"## {heading}\n\n{text}")

    # Related links
    links = [f"- [[{conversation_slug}]]"]
    body_parts.append("## 관련 대화\n\n" + "\n".join(links))

    body = "\n\n".join(body_parts)

    metadata = {
        "type": "experience",
        "cssclasses": ["ob-experience"],
        "created": date,
        "experience_type": exp_type,
        "tags": tags,
        "conversations": [conversation_slug],
        "projects": projects,
    }

    post = frontmatter.Post(content=f"# {title}\n\n{body}", **metadata)
    output = frontmatter.dumps(post) + "\n"

    exp_dir = vault_path / exp_folder
    exp_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(title) + ".md"
    doc_path = exp_dir / filename

    # Handle filename conflicts
    if doc_path.exists():
        slug = sanitize_filename(title)
        new_slug = resolve_slug_conflict(exp_dir, slug)
        doc_path = exp_dir / f"{new_slug}.md"

    doc_path.write_text(output, encoding="utf-8")
    return doc_path


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
