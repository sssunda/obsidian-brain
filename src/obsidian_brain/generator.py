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


def generate_daily_doc(
    vault_path: Path,
    daily_folder: str,
    date: str,
    daily_entries: list[dict],
    tags: list[str],
) -> Path:
    """Create or append to a daily note."""
    daily_dir = vault_path / daily_folder
    daily_dir.mkdir(parents=True, exist_ok=True)
    filepath = daily_dir / f"{date}.md"

    if filepath.exists():
        post = frontmatter.load(filepath)
        # Merge tags
        existing_tags = post.get("tags", [])
        merged_tags = list(dict.fromkeys(existing_tags + tags))
        post["tags"] = merged_tags

        # Merge projects
        existing_projects = post.get("projects", [])
        new_projects = [e["project"] for e in daily_entries if e["project"]]
        merged_projects = list(dict.fromkeys(existing_projects + new_projects))
        post["projects"] = merged_projects

        # Append entries to sections
        for entry in daily_entries:
            project = entry["project"]
            bullets_text = "\n".join(f"- {b}" for b in entry["bullets"])
            heading = f"## [[{project}]]" if project else "## 기타"

            if heading in post.content:
                post.content = _append_to_section(post.content, heading, bullets_text)
            else:
                post.content = post.content.rstrip() + f"\n\n{heading}\n{bullets_text}"

        filepath.write_text(frontmatter.dumps(post))
    else:
        projects = [e["project"] for e in daily_entries if e["project"]]
        projects = list(dict.fromkeys(projects))

        sections = []
        for entry in daily_entries:
            project = entry["project"]
            heading = f"## [[{project}]]" if project else "## 기타"
            bullets_text = "\n".join(f"- {b}" for b in entry["bullets"])
            sections.append(f"{heading}\n{bullets_text}")

        content = "\n\n".join(sections)
        post = frontmatter.Post(
            content=content,
            date=date,
            projects=projects,
            tags=tags,
        )
        filepath.write_text(frontmatter.dumps(post))

    return filepath


def generate_project_doc(
    vault_path: Path,
    projects_folder: str,
    project_name: str,
    date: str,
    summary: str,
    decisions: list[str] | None = None,
) -> Path:
    projects_dir = vault_path / projects_folder
    projects_dir.mkdir(parents=True, exist_ok=True)

    filepath = projects_dir / f"{sanitize_filename(project_name)}.md"

    decision_lines = ""
    if decisions:
        decision_lines = "\n".join(f"- {date}: {d}" for d in decisions)

    post = frontmatter.Post(
        content=f"""## 개요

## 핵심 결정
{decision_lines}

## 최근 작업
- [[{date}]] {summary}""",
        title=project_name,
        status="active",
        updated=date,
    )

    filepath.write_text(frontmatter.dumps(post))
    return filepath


def update_project_doc(
    doc_path: Path,
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

    post["updated"] = date

    # Add to 최근 작업
    work_entry = f"- [[{date}]] {summary}"
    if "## 최근 작업" in post.content:
        post.content = _append_to_section(post.content, "## 최근 작업", work_entry)
    else:
        post.content = post.content.rstrip() + f"\n\n## 최근 작업\n{work_entry}"

    # Add decisions
    if decisions:
        for d in decisions:
            decision_entry = f"- {date}: {d}"
            if d not in post.content:
                if "## 핵심 결정" in post.content:
                    post.content = _append_to_section(post.content, "## 핵심 결정", decision_entry)
                else:
                    post.content = post.content.rstrip() + f"\n\n## 핵심 결정\n{decision_entry}"

    doc_path.write_text(frontmatter.dumps(post))
