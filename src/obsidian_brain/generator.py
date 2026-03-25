from pathlib import Path
import frontmatter


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

    post = frontmatter.Post(
        content=f"""## 요약
{analysis['summary']}

## 핵심 결정사항
{decisions}

## 관련 개념
{concept_links}

## 관련 프로젝트
{project_links}""",
        source="claude-code",
        session_id=session_id,
        date=date,
        title=analysis["summary"][:50],
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

    filepath = concepts_dir / f"{concept['name']}.md"

    related = related_concepts or []
    related_links = "\n".join(f"- [[{r}]]" for r in related if r != concept["name"])

    insight_section = ""
    if concept.get("insight"):
        insight_section = f"- ({date}) {concept['insight']}"

    post = frontmatter.Post(
        content=f"""# {concept['name']}

{concept.get('description', '')}

## 인사이트
{insight_section}

## 관련 개념
{related_links}""",
        type="concept",
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
    post = frontmatter.load(doc_path)

    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add insight at end of section (chronological order)
    if insight:
        insight_line = f"- ({date}) {insight}"
        if "## 인사이트" in post.content:
            lines = post.content.split("\n")
            insert_idx = len(lines)
            in_section = False
            for i, line in enumerate(lines):
                if line.strip() == "## 인사이트":
                    in_section = True
                    continue
                if in_section and line.startswith("## "):
                    insert_idx = i
                    break
            lines.insert(insert_idx, insight_line)
            post.content = "\n".join(lines)
        else:
            post.content += f"\n\n## 인사이트\n{insight_line}"

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

    filepath = projects_dir / f"{project_name}.md"

    decision_lines = "\n".join(f"- {d}" for d in (decisions or []))

    post = frontmatter.Post(
        content=f"""# {project_name}

## 대화 타임라인
- [[{conversation_slug}]] — {summary}

## 핵심 결정사항
{decision_lines}""",
        type="project",
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
    post = frontmatter.load(doc_path)

    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add to timeline at end of section
    timeline_entry = f"- [[{conversation_slug}]] — {summary}"
    if "## 대화 타임라인" in post.content:
        lines = post.content.split("\n")
        insert_idx = len(lines)
        in_section = False
        for i, line in enumerate(lines):
            if line.strip() == "## 대화 타임라인":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                insert_idx = i
                break
        lines.insert(insert_idx, timeline_entry)
        post.content = "\n".join(lines)

    # Add decisions at end of section
    if decisions:
        for d in decisions:
            if d not in post.content:
                decision_line = f"- {d}"
                if "## 핵심 결정사항" in post.content:
                    lines = post.content.split("\n")
                    insert_idx = len(lines)
                    in_section = False
                    for i, line in enumerate(lines):
                        if line.strip() == "## 핵심 결정사항":
                            in_section = True
                            continue
                        if in_section and line.startswith("## "):
                            insert_idx = i
                            break
                    lines.insert(insert_idx, decision_line)
                    post.content = "\n".join(lines)

    doc_path.write_text(frontmatter.dumps(post))
