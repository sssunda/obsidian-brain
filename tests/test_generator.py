from pathlib import Path
import frontmatter
from obsidian_brain.generator import (
    generate_conversation_doc,
    generate_concept_doc,
    update_concept_doc,
    generate_project_doc,
    update_project_doc,
    resolve_slug_conflict,
)


def test_generate_conversation_doc(tmp_path):
    analysis = {
        "summary": "Docker 네트워킹에 대해 배웠다",
        "decisions": ["bridge 네트워크 사용"],
        "concepts": [{"name": "Docker", "existing_match": "Docker", "insight": None}],
        "concept_relations": [],
        "tags": ["docker", "networking"],
        "projects": ["my-project"],
        "title_slug": "docker-networking",
    }
    path = generate_conversation_doc(
        vault_path=tmp_path,
        conv_folder="Conversations",
        date="2026-03-25",
        session_id="abc123",
        analysis=analysis,
    )
    assert path.exists()
    post = frontmatter.load(path)
    assert post["source"] == "claude-code"
    assert post["session_id"] == "abc123"
    assert "docker" in post["tags"]
    assert "## 요약" in post.content


def test_generate_concept_doc(tmp_path):
    concept = {
        "name": "지식그래프",
        "description": "노드와 엣지로 지식을 연결",
        "aliases": ["knowledge graph"],
        "existing_match": None,
        "insight": "Obsidian 그래프 뷰와 결합 가능",
    }
    path = generate_concept_doc(
        vault_path=tmp_path,
        concepts_folder="Concepts",
        concept=concept,
        date="2026-03-25",
        conversation_slug="2026-03-25-docker-networking",
        related_concepts=["옵시디언"],
    )
    assert path.exists()
    post = frontmatter.load(path)
    assert post["type"] == "concept"
    assert "knowledge graph" in post["aliases"]
    assert "## 인사이트" in post.content


def test_update_concept_doc_adds_conversation(tmp_path):
    concepts_dir = tmp_path / "Concepts"
    concepts_dir.mkdir()
    existing = concepts_dir / "Docker.md"
    existing.write_text("""---
type: concept
created: 2026-03-20
updated: 2026-03-20
aliases: []
conversations: [2026-03-20-docker-basics]
---

# Docker

컨테이너 플랫폼.

## 인사이트
- (2026-03-20) 멀티스테이지 빌드

## 관련 개념
""")
    update_concept_doc(
        doc_path=existing,
        conversation_slug="2026-03-25-docker-networking",
        date="2026-03-25",
        insight="Bridge vs Host 네트워크 차이",
    )
    post = frontmatter.load(existing)
    assert "2026-03-25-docker-networking" in post["conversations"]
    assert "Bridge vs Host" in post.content
    assert post["updated"] == "2026-03-25"
    # Verify chronological order: old insight first, new insight after
    content = post.content
    old_pos = content.find("멀티스테이지 빌드")
    new_pos = content.find("Bridge vs Host")
    assert old_pos < new_pos, "New insight should come after old insight (chronological)"


def test_update_project_doc(tmp_path):
    projects_dir = tmp_path / "Projects"
    projects_dir.mkdir()
    existing = projects_dir / "my-project.md"
    existing.write_text("""---
type: project
created: 2026-03-20
updated: 2026-03-20
status: active
conversations: [2026-03-20-initial-setup]
---

# my-project

## 대화 타임라인
- [[2026-03-20-initial-setup]] — 초기 셋업

## 핵심 결정사항
- Python 사용
""")
    update_project_doc(
        doc_path=existing,
        conversation_slug="2026-03-25-docker-networking",
        date="2026-03-25",
        summary="Docker 설정 추가",
        decisions=["Docker Compose 사용"],
    )
    post = frontmatter.load(existing)
    assert "2026-03-25-docker-networking" in post["conversations"]
    assert "Docker 설정 추가" in post.content
    assert "Docker Compose 사용" in post.content
    assert post["updated"] == "2026-03-25"


def test_resolve_slug_conflict(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)
    (conv_dir / "2026-03-25-docker-networking.md").write_text("existing")
    result = resolve_slug_conflict(conv_dir, "2026-03-25-docker-networking")
    assert result == "2026-03-25-docker-networking-2"


def test_generate_project_doc(tmp_path):
    path = generate_project_doc(
        vault_path=tmp_path,
        projects_folder="Projects",
        project_name="obsidian-brain",
        date="2026-03-25",
        conversation_slug="2026-03-25-obsidian-design",
        summary="시스템 설계",
        decisions=["Phase 1: Claude Code만"],
    )
    assert path.exists()
    post = frontmatter.load(path)
    assert post["type"] == "project"
    assert "obsidian-brain" in post.content
