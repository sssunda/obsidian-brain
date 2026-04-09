from pathlib import Path
import frontmatter
from obsidian_brain.generator import (
    generate_conversation_doc,
    generate_project_doc,
    update_project_doc,
    resolve_slug_conflict,
    sanitize_filename,
)


def test_generate_conversation_doc(tmp_path):
    analysis = {
        "summary": "Docker 네트워킹에 대해 배웠다",
        "decisions": ["bridge 네트워크 사용"],
        "reasoning_patterns": [
            {"situation": "네트워크 선택", "choice": "bridge", "why": "기본값이라 안정적"}
        ],
        "preferences": ["안정성 우선"],
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
    assert post["type"] == "conversation"
    assert post["session_id"] == "abc123"
    assert "docker" in post["tags"]
    assert "## 요약" in post.content
    assert "## 의사결정 패턴" in post.content
    assert "## 드러난 선호/원칙" in post.content


def test_conversation_doc_empty_sections_hidden(tmp_path):
    analysis = {
        "summary": "간단한 질문",
        "decisions": [],
        "reasoning_patterns": [],
        "preferences": [],
        "concepts": [],
        "concept_relations": [],
        "tags": ["misc"],
        "projects": [],
        "title_slug": "simple-question",
    }
    path = generate_conversation_doc(
        vault_path=tmp_path,
        conv_folder="Conversations",
        date="2026-03-25",
        session_id="abc456",
        analysis=analysis,
    )
    post = frontmatter.load(path)
    assert "## 의사결정 패턴" not in post.content
    assert "## 드러난 선호/원칙" not in post.content
    assert "## 핵심 결정사항" not in post.content


def test_conversation_doc_title_truncation(tmp_path):
    long_summary = "이것은 매우 긴 요약 문장입니다 " * 10
    analysis = {
        "summary": long_summary,
        "decisions": [],
        "reasoning_patterns": [],
        "preferences": [],
        "concepts": [],
        "concept_relations": [],
        "tags": [],
        "projects": [],
        "title_slug": "long-title",
    }
    path = generate_conversation_doc(
        vault_path=tmp_path,
        conv_folder="Conversations",
        date="2026-03-25",
        session_id="abc789",
        analysis=analysis,
    )
    post = frontmatter.load(path)
    assert len(post["title"]) <= 80




def test_update_project_doc(tmp_path):
    projects_dir = tmp_path / "Projects"
    projects_dir.mkdir()
    existing = projects_dir / "my-project.md"
    existing.write_text("""---
title: my-project
updated: '2026-03-20'
status: active
---

## 개요

## 핵심 결정
- 2026-03-20: Python 사용

## 최근 작업
- [[2026-03-20]] 초기 셋업
""")
    update_project_doc(
        doc_path=existing,
        date="2026-03-25",
        summary="Docker 설정 추가",
        decisions=["Docker Compose 사용"],
    )
    post = frontmatter.load(existing)
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
        summary="시스템 설계",
        decisions=["Phase 1: Claude Code만"],
    )
    assert path.exists()
    post = frontmatter.load(path)
    assert post["title"] == "obsidian-brain"
    assert "## 최근 작업" in post.content
    assert "## 핵심 결정" in post.content


def test_generate_project_doc_new_format(tmp_path):
    path = generate_project_doc(
        vault_path=tmp_path,
        projects_folder="Projects",
        project_name="wishket",
        date="2026-04-09",
        summary="Lead Scoring 리팩토링",
        decisions=["가중치 균등 배분으로 변경"],
    )
    assert path.exists()
    post = frontmatter.load(path)
    assert post["title"] == "wishket"
    assert post["status"] == "active"
    assert "## 개요" in post.content
    assert "## 핵심 결정" in post.content
    assert "## 최근 작업" in post.content
    assert "[[2026-04-09]]" in post.content
    assert "가중치 균등 배분으로 변경" in post.content


def test_generate_experience_doc_problem_solving(tmp_path):
    from obsidian_brain.generator import generate_experience_doc

    experience = {
        "title": "Django QuerySet 평가 시점 함정",
        "experience_type": "problem-solving",
        "sections": {
            "상황": "Admin에서 LogEntry를 bulk로 조회하는데 페이지 로딩이 5초 이상 걸림",
            "선택": ".all() 캐싱에 의존하지 않고, .values_list()로 즉시 평가하도록 변경",
            "교훈": "Django QuerySet은 lazy evaluation이라 변수 할당 ≠ 실행",
        },
        "tags": ["django", "queryset", "performance"],
    }
    conversation_slug = "2026-03-30-django-admin-logentry"
    date = "2026-03-30"
    projects = ["wishos"]

    doc_path = generate_experience_doc(
        experience=experience,
        conversation_slug=conversation_slug,
        date=date,
        projects=projects,
        vault_path=tmp_path,
        exp_folder="Experiences",
    )

    assert doc_path.exists()
    content = doc_path.read_text()

    # Frontmatter checks
    assert "type: experience" in content
    assert "ob-experience" in content
    assert "experience_type: problem-solving" in content

    # Section checks
    assert "## 상황" in content
    assert "5초 이상" in content
    assert "## 선택" in content
    assert "## 교훈" in content

    # Links
    assert "[[2026-03-30-django-admin-logentry]]" in content


def test_generate_experience_doc_discovery(tmp_path):
    from obsidian_brain.generator import generate_experience_doc

    experience = {
        "title": "LogEntry change_message 포맷 차이",
        "experience_type": "discovery",
        "sections": {
            "발견": "Django의 LogEntry.change_message은 admin 자동 생성과 수동 생성의 포맷이 다름",
            "맥락": "감사 로그 파싱할 때 두 포맷 모두 처리해야 함",
        },
        "tags": ["django", "admin"],
    }

    doc_path = generate_experience_doc(
        experience=experience,
        conversation_slug="2026-04-01-logentry-discovery",
        date="2026-04-01",
        projects=[],
        vault_path=tmp_path,
        exp_folder="Experiences",
    )

    content = doc_path.read_text()
    assert "## 발견" in content
    assert "## 맥락" in content
    assert "## 상황" not in content  # no problem-solving sections


def test_generate_daily_doc_new_file(tmp_path):
    from obsidian_brain.generator import generate_daily_doc

    daily_entries = [
        {"project": "wishket", "bullets": ["Lead Scoring 리팩토링", "Celery 타임아웃 해결"]},
        {"project": "daeun", "bullets": ["obsidian-brain 구조 전환"]},
    ]
    path = generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=daily_entries,
        tags=["django", "celery"],
    )
    assert path.exists()
    assert path.name == "2026-04-09.md"

    post = frontmatter.load(path)
    assert post["date"] == "2026-04-09"
    assert "wishket" in post["projects"]
    assert "daeun" in post["projects"]
    assert "## [[wishket]]" in post.content
    assert "Lead Scoring 리팩토링" in post.content
    assert "## [[daeun]]" in post.content


def test_generate_daily_doc_append_existing(tmp_path):
    from obsidian_brain.generator import generate_daily_doc

    # First session
    generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": "wishket", "bullets": ["Lead Scoring 리팩토링"]}],
        tags=["django"],
    )
    # Second session — same project
    path = generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": "wishket", "bullets": ["Celery 타임아웃 해결"]}],
        tags=["celery"],
    )

    post = frontmatter.load(path)
    assert "django" in post["tags"]
    assert "celery" in post["tags"]
    assert post.content.count("## [[wishket]]") == 1
    assert "Lead Scoring 리팩토링" in post.content
    assert "Celery 타임아웃 해결" in post.content


def test_generate_daily_doc_append_new_project(tmp_path):
    from obsidian_brain.generator import generate_daily_doc

    generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": "wishket", "bullets": ["작업1"]}],
        tags=[],
    )
    path = generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": "daeun", "bullets": ["작업2"]}],
        tags=[],
    )

    post = frontmatter.load(path)
    assert "wishket" in post["projects"]
    assert "daeun" in post["projects"]
    assert "## [[wishket]]" in post.content
    assert "## [[daeun]]" in post.content


def test_generate_daily_doc_null_project(tmp_path):
    from obsidian_brain.generator import generate_daily_doc

    path = generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": None, "bullets": ["잡다한 작업"]}],
        tags=[],
    )
    post = frontmatter.load(path)
    assert "## 기타" in post.content
    assert "잡다한 작업" in post.content
