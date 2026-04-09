# Daily Note 구조 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-session scattered output (Conversations + Experiences + weak Projects) with Daily notes, strong project classification (4 fixed projects), and experience dedup via LLM-aware existing titles.

**Architecture:** config.py defines 4 fixed projects with aliases/descriptions. analyzer.py sends project descriptions + existing experience titles to LLM, returns `daily_entries` per project. pipeline.py maps/validates project names, delegates to generator.py which creates/appends Daily notes and updates Project docs. Conversations folder eliminated.

**Tech Stack:** Python, frontmatter, difflib, pytest, yaml

**Spec:** `docs/superpowers/specs/2026-04-09-daily-note-restructure-design.md`

---

### Task 1: Config — Add project definitions and daily folder

**Files:**
- Modify: `src/obsidian_brain/config.py:5-22`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for new config structure**

```python
# Append to tests/test_config.py

def test_default_config_has_projects():
    """Default config includes fixed project definitions."""
    assert "projects" in DEFAULT_CONFIG
    projects = DEFAULT_CONFIG["projects"]
    assert "wishket" in projects
    assert "wishos" in projects
    assert "prd-manage" in projects
    assert "daeun" in projects
    # Each project has aliases and description
    assert "aliases" in projects["wishket"]
    assert "description" in projects["wishket"]
    assert "backend" in projects["wishket"]["aliases"]


def test_default_config_has_daily_folder():
    """Default config includes daily folder."""
    assert DEFAULT_CONFIG["folders"]["daily"] == "Daily"


def test_config_project_aliases_no_overlap():
    """No alias appears in more than one project."""
    all_aliases = []
    for proj in DEFAULT_CONFIG["projects"].values():
        all_aliases.extend(proj["aliases"])
    assert len(all_aliases) == len(set(all_aliases)), "Duplicate alias found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_config.py::test_default_config_has_projects tests/test_config.py::test_default_config_has_daily_folder tests/test_config.py::test_config_project_aliases_no_overlap -v`
Expected: FAIL — `projects` key not in DEFAULT_CONFIG

- [ ] **Step 3: Implement config changes**

In `src/obsidian_brain/config.py`, replace `DEFAULT_CONFIG`:

```python
DEFAULT_CONFIG = {
    "vault_path": None,
    "min_messages": 3,
    "max_transcript_chars": 50000,
    "max_retries": 3,
    "processed_retention_days": 30,
    "slug_language": "en",
    "batch_limit": 10,
    "rate_limit_seconds": 2,
    "truncate_head": 15,
    "truncate_tail": 85,
    "model": "sonnet",
    "folders": {
        "daily": "Daily",
        "experiences": "Experiences",
        "projects": "Projects",
    },
    "projects": {
        "wishket": {
            "aliases": ["backend", "schema", "yozmit", "manage", "script", "slock", "prdesign", "mapletech"],
            "description": "위시켓 플랫폼 — Django 백엔드, 인프라, 비즈니스 기능",
        },
        "wishos": {
            "aliases": ["wishos-agent"],
            "description": "WishOS AI 에이전트 시스템 — 멀티에이전트 파이프라인",
        },
        "prd-manage": {
            "aliases": [],
            "description": "PRD 관리 도구",
        },
        "daeun": {
            "aliases": ["obsidian-brain", "matjip-scout", "pomodoro-todo", "practice", "daeunBot"],
            "description": "개인 사이드 프로젝트 및 기타",
        },
    },
}
```

Note: remove `"conversations"` from `folders` — no longer used.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_config.py -v`
Expected: ALL PASS (update `test_load_config_defaults` to remove `conversations` assertion, add `daily` assertion)

Update `test_load_config_defaults`:
```python
def test_load_config_defaults(tmp_path):
    """When no config.yaml exists, return defaults."""
    config = load_config(tmp_path)
    assert config["min_messages"] == 3
    assert config["folders"]["daily"] == "Daily"
    assert config["folders"]["experiences"] == "Experiences"
    assert config["folders"]["projects"] == "Projects"
    assert "conversations" not in config["folders"]
    assert "wishket" in config["projects"]
```

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/config.py tests/test_config.py
git commit -m "feat: add fixed project definitions and daily folder to config"
```

---

### Task 2: Project mapping — resolve_project function

**Files:**
- Create: `src/obsidian_brain/project_mapper.py`
- Create: `tests/test_project_mapper.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_project_mapper.py
from obsidian_brain.project_mapper import resolve_project


def test_exact_match():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("wishket", projects) == "wishket"


def test_alias_match():
    projects = {
        "wishket": {"aliases": ["backend", "schema"], "description": ""},
    }
    assert resolve_project("backend", projects) == "wishket"
    assert resolve_project("schema", projects) == "wishket"


def test_fuzzy_match():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("wishket-backend", projects) == "wishket"


def test_no_match_returns_none():
    projects = {
        "wishket": {"aliases": ["backend"], "description": ""},
    }
    assert resolve_project("random-thing", projects) is None


def test_case_insensitive():
    projects = {
        "wishket": {"aliases": ["Backend"], "description": ""},
    }
    assert resolve_project("BACKEND", projects) == "wishket"


def test_daeun_catches_personal_projects():
    projects = {
        "daeun": {"aliases": ["obsidian-brain", "matjip-scout", "pomodoro-todo"], "description": ""},
    }
    assert resolve_project("obsidian-brain", projects) == "daeun"
    assert resolve_project("matjip-scout", projects) == "daeun"


def test_resolve_list():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "wishket": {"aliases": ["backend"], "description": ""},
        "daeun": {"aliases": ["obsidian-brain"], "description": ""},
    }
    result = resolve_projects(["backend", "obsidian-brain", "unknown"], projects_config)
    assert result == ["wishket", "daeun"]


def test_resolve_list_deduplicates():
    from obsidian_brain.project_mapper import resolve_projects
    projects_config = {
        "wishket": {"aliases": ["backend", "schema"], "description": ""},
    }
    result = resolve_projects(["backend", "schema", "wishket"], projects_config)
    assert result == ["wishket"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_project_mapper.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement project_mapper.py**

```python
# src/obsidian_brain/project_mapper.py
from difflib import SequenceMatcher


def resolve_project(name: str, projects_config: dict, threshold: float = 0.7) -> str | None:
    """Resolve a project name to a canonical project via exact match, alias, or fuzzy match."""
    name_lower = name.lower()

    # Exact match
    for project_name in projects_config:
        if name_lower == project_name.lower():
            return project_name

    # Alias match
    for project_name, config in projects_config.items():
        for alias in config.get("aliases", []):
            if name_lower == alias.lower():
                return project_name

    # Fuzzy match against project names and aliases
    best_score = 0.0
    best_project = None
    for project_name, config in projects_config.items():
        candidates = [project_name] + config.get("aliases", [])
        for candidate in candidates:
            score = SequenceMatcher(None, name_lower, candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_project = project_name

    if best_score >= threshold:
        return best_project

    return None


def resolve_projects(names: list[str], projects_config: dict) -> list[str]:
    """Resolve a list of project names, deduplicate, drop unmatched."""
    seen = set()
    result = []
    for name in names:
        resolved = resolve_project(name, projects_config)
        if resolved and resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_project_mapper.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/project_mapper.py tests/test_project_mapper.py
git commit -m "feat: add project_mapper with alias and fuzzy matching"
```

---

### Task 3: Vault — Add scan_experiences

**Files:**
- Modify: `src/obsidian_brain/vault.py`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test**

```python
# Append to tests/test_vault.py

def test_scan_experiences(tmp_path):
    from obsidian_brain.vault import scan_experiences
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "Django QuerySet 평가 시점 함정.md").write_text("# test")
    (exp_dir / "UUID PK 전환이 전체 스택을 깨뜨림.md").write_text("# test")

    titles = scan_experiences(tmp_path, "Experiences")
    assert "Django QuerySet 평가 시점 함정" in titles
    assert "UUID PK 전환이 전체 스택을 깨뜨림" in titles
    assert len(titles) == 2


def test_scan_experiences_empty(tmp_path):
    from obsidian_brain.vault import scan_experiences
    titles = scan_experiences(tmp_path, "Experiences")
    assert titles == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_vault.py::test_scan_experiences tests/test_vault.py::test_scan_experiences_empty -v`
Expected: FAIL — `scan_experiences` not found

- [ ] **Step 3: Implement scan_experiences**

Add to `src/obsidian_brain/vault.py`:

```python
def scan_experiences(vault_path: Path, folder: str = "Experiences") -> list[str]:
    """Return titles (filenames without .md) of all experience notes."""
    exp_dir = vault_path / folder
    if not exp_dir.exists():
        return []
    return [f.stem for f in exp_dir.glob("*.md")]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_vault.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/vault.py tests/test_vault.py
git commit -m "feat: add scan_experiences to vault module"
```

---

### Task 4: Analyzer — New schema and prompt with project descriptions + experience titles

**Files:**
- Modify: `src/obsidian_brain/analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing tests**

```python
# Replace tests/test_analyzer.py entirely

import json
from obsidian_brain.analyzer import build_prompt, build_json_schema, truncate_messages, ANALYSIS_SCHEMA


def test_schema_has_daily_entries():
    props = ANALYSIS_SCHEMA["properties"]
    assert "daily_entries" in props
    entry_props = props["daily_entries"]["items"]["properties"]
    assert "project" in entry_props
    assert "bullets" in entry_props


def test_schema_still_has_experiences():
    props = ANALYSIS_SCHEMA["properties"]
    assert "experiences" in props
    exp_items = props["experiences"]["items"]["properties"]
    assert "title" in exp_items
    assert "experience_type" in exp_items
    assert "sections" in exp_items


def test_schema_required_fields():
    required = ANALYSIS_SCHEMA["required"]
    assert "summary" in required
    assert "daily_entries" in required
    assert "experiences" in required
    assert "decisions" in required
    assert "tags" in required


def test_prompt_includes_project_descriptions():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    projects_config = {
        "wishket": {"aliases": ["backend"], "description": "위시켓 플랫폼"},
        "daeun": {"aliases": ["obsidian-brain"], "description": "개인 프로젝트"},
    }
    prompt = build_prompt(parsed, projects_config=projects_config)
    assert "wishket" in prompt
    assert "위시켓 플랫폼" in prompt
    assert "backend" in prompt
    assert "daeun" in prompt


def test_prompt_includes_existing_experiences():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    existing_experiences = [
        "Django QuerySet 평가 시점 함정",
        "UUID PK 전환이 전체 스택을 깨뜨림",
    ]
    prompt = build_prompt(parsed, existing_experiences=existing_experiences)
    assert "Django QuerySet 평가 시점 함정" in prompt
    assert "UUID PK 전환이 전체 스택을 깨뜨림" in prompt


def test_prompt_no_experiences_section_when_empty():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    prompt = build_prompt(parsed, existing_experiences=[])
    assert "기존 경험 노트:" not in prompt


def test_prompt_daily_entries_instructions():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    projects_config = {
        "wishket": {"aliases": [], "description": "위시켓"},
    }
    prompt = build_prompt(parsed, projects_config=projects_config)
    assert "daily_entries" in prompt


def test_truncate_messages_short_conversation():
    messages = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    result = truncate_messages(messages, max_chars=50000)
    assert len(result) == 10


def test_truncate_messages_long_conversation():
    messages = [{"role": "user", "content": "x" * 600} for i in range(200)]
    result = truncate_messages(messages, max_chars=50000)
    assert len(result) == 101  # 15 head + 1 separator + 85 tail
    assert result[15]["role"] == "system"
    assert "[... 중간" in result[15]["content"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_analyzer.py -v`
Expected: FAIL — `daily_entries` not in schema, `projects_config` not accepted by `build_prompt`

- [ ] **Step 3: Implement schema and prompt changes**

Replace `src/obsidian_brain/analyzer.py`:

```python
import logging

from .claude_api import call_claude

logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "title_slug": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "daily_entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project": {"type": ["string", "null"]},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project", "bullets"],
            },
        },
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "experience_type": {
                        "type": "string",
                        "enum": ["problem-solving", "discovery", "troubleshooting"],
                    },
                    "sections": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "experience_type", "sections"],
            },
        },
    },
    "required": [
        "summary", "title_slug", "tags", "decisions",
        "daily_entries", "experiences",
    ],
}


def build_json_schema() -> dict:
    return ANALYSIS_SCHEMA


def build_prompt(
    parsed: dict,
    projects_config: dict | None = None,
    cwd: str | None = None,
    existing_experiences: list[str] | None = None,
) -> str:
    messages = truncate_messages(parsed["messages"])
    date = parsed["date"]
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )

    context_lines = []
    if cwd:
        dir_name = cwd.rstrip("/").split("/")[-1] if "/" in cwd else cwd
        context_lines.append(f"작업 디렉토리: {cwd} (힌트: {dir_name})")
    context_section = "\n".join(context_lines)

    # Project descriptions
    project_section = ""
    if projects_config:
        lines = ["## 프로젝트 목록 (이 중에서만 선택)"]
        for name, config in projects_config.items():
            aliases = config.get("aliases", [])
            desc = config.get("description", "")
            alias_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
            lines.append(f"- **{name}**{alias_str}: {desc}")
        lines.append("")
        lines.append("위 목록에 없는 프로젝트명은 사용하지 마. 매칭 안 되면 project: null로.")
        project_section = "\n".join(lines)

    # Existing experiences
    experience_section = ""
    if existing_experiences:
        lines = ["## 기존 경험 노트"]
        for title in existing_experiences:
            lines.append(f"- {title}")
        lines.append("")
        lines.append("위 목록과 같은 내용이면 experiences에 포함하지 마. 새롭게 배운 것만 추출해.")
        experience_section = "\n".join(lines)

    return f"""다음 AI 대화를 분석해줘.

날짜: {date}
{context_section}

{project_section}

## 분석 지침

1. summary: 이 대화에서 뭘 했는지 1-3문장으로 요약
2. title_slug: 영문 kebab-case 파일명 슬러그
3. tags: 소문자 영문 태그
4. decisions: 핵심 결정사항 목록
5. daily_entries: 프로젝트별로 오늘 한 일을 bullet 정리
   - project: 프로젝트명 (위 목록 중 하나, 또는 null)
   - bullets: 각각 한 줄로 뭘 했는지. 하위 설명이 필요하면 " — " 으로 이어서
   - 한 세션이 여러 프로젝트에 걸치면 각각 별도 entry로

{experience_section}

## 경험 추출 (experiences)

이 대화에서 **나중에 다시 찾아볼 만한** 문제 해결, 발견, 삽질이 있으면 추출해.
없으면 experiences: [] 로 반환해. 억지로 만들지 마.

각 경험의 타입:
- problem-solving: 문제를 만나서 해결함. sections에 "상황", "선택", "교훈" 키 사용
- discovery: 새로 알게 된 사실. sections에 "발견", "맥락" 키 사용
- troubleshooting: 삽질해서 원인 찾음. sections에 "삽질", "원인", "해결" 키 사용

title 규칙:
- 사용자가 대화에서 실제로 쓴 표현을 최대한 활용
- 기술 중심이 자연스러우면: "Django QuerySet 평가 시점 함정"
- 상황 중심이 자연스러우면: "배포 직전 마이그레이션 충돌"
- 추상적 조어 금지 ("범용 X 패턴", "Y 오염 패턴" 같은 거 쓰지 마)

sections 내용 규칙:
- 구체적으로 써. "QuerySet이 느렸다"가 아니라 "Admin에서 LogEntry bulk 조회가 5초 이상 걸림"
- 해당 내용이 대화에 실제로 있을 때만 작성. 억지로 채우지 마.

단순 작업 수행 ("파일 만들어줘", "이거 고쳐줘", "리팩토링해줘")은 경험이 아님.

---
대화 내용:
{transcript}"""


def truncate_messages(messages: list[dict], max_chars: int = 50000, head_count: int = 15, tail_count: int = 85) -> list[dict]:
    total = sum(len(m["content"]) for m in messages)
    if total <= max_chars:
        return messages
    if len(messages) <= head_count + tail_count:
        return messages

    head = messages[:head_count]
    tail = messages[-tail_count:]
    skipped = len(messages) - head_count - tail_count
    separator = {"role": "system", "content": f"[... 중간 {skipped}개 메시지 생략 ...]"}
    return head + [separator] + tail


def analyze(
    parsed: dict,
    projects_config: dict | None = None,
    cwd: str | None = None,
    existing_experiences: list[str] | None = None,
    model: str = "sonnet",
) -> dict:
    prompt = build_prompt(parsed, projects_config=projects_config, cwd=cwd, existing_experiences=existing_experiences)
    return call_claude(prompt, ANALYSIS_SCHEMA, model=model)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_analyzer.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/analyzer.py tests/test_analyzer.py
git commit -m "feat: add daily_entries schema, project descriptions, and experience titles to analyzer"
```

---

### Task 5: Generator — Daily note create/append

**Files:**
- Modify: `src/obsidian_brain/generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests for daily note creation**

```python
# Append to tests/test_generator.py

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
    # Both bullets under same wishket section
    assert post.content.count("## [[wishket]]") == 1
    assert "Lead Scoring 리팩토링" in post.content
    assert "Celery 타임아웃 해결" in post.content


def test_generate_daily_doc_append_new_project(tmp_path):
    from obsidian_brain.generator import generate_daily_doc

    # First session
    generate_daily_doc(
        vault_path=tmp_path,
        daily_folder="Daily",
        date="2026-04-09",
        daily_entries=[{"project": "wishket", "bullets": ["작업1"]}],
        tags=[],
    )
    # Second session — different project
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_generator.py::test_generate_daily_doc_new_file tests/test_generator.py::test_generate_daily_doc_append_existing tests/test_generator.py::test_generate_daily_doc_append_new_project tests/test_generator.py::test_generate_daily_doc_null_project -v`
Expected: FAIL — `generate_daily_doc` not found

- [ ] **Step 3: Implement generate_daily_doc**

Add to `src/obsidian_brain/generator.py`:

```python
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
                # Append to existing section
                post.content = _append_to_section(post.content, heading, bullets_text)
            else:
                # Add new section at end
                post.content = post.content.rstrip() + f"\n\n{heading}\n{bullets_text}"

        filepath.write_text(frontmatter.dumps(post))
    else:
        # Build new file
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_generator.py::test_generate_daily_doc_new_file tests/test_generator.py::test_generate_daily_doc_append_existing tests/test_generator.py::test_generate_daily_doc_append_new_project tests/test_generator.py::test_generate_daily_doc_null_project -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/generator.py tests/test_generator.py
git commit -m "feat: add generate_daily_doc with create/append support"
```

---

### Task 6: Generator — Update project doc to new format

**Files:**
- Modify: `src/obsidian_brain/generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# Append to tests/test_generator.py

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


def test_update_project_doc_new_format(tmp_path):
    projects_dir = tmp_path / "Projects"
    projects_dir.mkdir()
    existing = projects_dir / "wishket.md"
    existing.write_text("""---
title: wishket
status: active
updated: '2026-04-08'
---

## 개요

위시켓 플랫폼

## 핵심 결정
- 2026-04-08: UUID PK 전환

## 최근 작업
- [[2026-04-08]] UUID PK 전환 작업
""")
    update_project_doc(
        doc_path=existing,
        date="2026-04-09",
        summary="Lead Scoring 리팩토링",
        decisions=["가중치 균등 배분"],
    )
    post = frontmatter.load(existing)
    assert post["updated"] == "2026-04-09"
    assert "[[2026-04-09]]" in post.content
    assert "Lead Scoring 리팩토링" in post.content
    assert "가중치 균등 배분" in post.content
    # Old content preserved
    assert "UUID PK 전환" in post.content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_generator.py::test_generate_project_doc_new_format tests/test_generator.py::test_update_project_doc_new_format -v`
Expected: FAIL — new format assertions fail (old format uses `## 대화 타임라인`, not `## 최근 작업`)

- [ ] **Step 3: Update generate_project_doc and update_project_doc**

Replace `generate_project_doc` in `src/obsidian_brain/generator.py`:

```python
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
```

Replace `update_project_doc`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_generator.py -v`
Expected: ALL PASS (also fix old tests that relied on old format — see step 5)

Note: `test_generate_project_doc` (old test) and `test_update_project_doc` (old test) need updating to match new format. Update them:

Old `test_generate_project_doc` — change assertion from `"obsidian-brain" in post.content` to check new format:
```python
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
```

Old `test_update_project_doc` — update the fixture and assertions to use new section names (`## 핵심 결정`, `## 최근 작업`):
```python
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
```

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/generator.py tests/test_generator.py
git commit -m "feat: update project doc format with 개요/핵심 결정/최근 작업 sections"
```

---

### Task 7: Filter — Adjust experience threshold, remove conversation dedup

**Files:**
- Modify: `src/obsidian_brain/filter.py`
- Modify: `tests/test_filter.py`

- [ ] **Step 1: Update filter.py**

In `src/obsidian_brain/filter.py`:
- Change `is_similar_experience` default threshold from `0.5` to `0.6`
- Remove `is_similar_conversation` function entirely

```python
import logging
from difflib import SequenceMatcher
from pathlib import Path

import frontmatter

logger = logging.getLogger(__name__)


def should_process(parsed: dict, processed_ids: set[str], min_messages: int = 3) -> bool:
    session_id = parsed["session_id"]
    if session_id in processed_ids:
        return False
    user_count = sum(1 for m in parsed["messages"] if m["role"] == "user")
    if user_count <= min_messages:
        return False
    user_msgs = [m["content"] for m in parsed["messages"] if m["role"] == "user"]
    avg_len = sum(len(m) for m in user_msgs) / max(len(user_msgs), 1)
    if avg_len < 10:
        return False
    return True


def is_similar_experience(title: str, vault_path, exp_folder: str = "Experiences", threshold: float = 0.6) -> bool:
    """Check if a similar experience note already exists."""
    exp_dir = Path(vault_path) / exp_folder
    if not exp_dir.exists():
        return False

    title_lower = title.lower()
    title_words = set(title_lower.split())

    for md_file in exp_dir.glob("*.md"):
        existing_title = md_file.stem
        existing_lower = existing_title.lower()

        if SequenceMatcher(None, title_lower, existing_lower).ratio() >= threshold:
            logger.info(f"Experience dedup: '{title}' similar to existing '{existing_title}'")
            return True

        existing_words = set(existing_lower.split())
        if title_words and existing_words:
            jaccard = len(title_words & existing_words) / len(title_words | existing_words)
            if jaccard >= threshold:
                logger.info(f"Experience dedup (jaccard): '{title}' similar to existing '{existing_title}'")
                return True

    return False
```

- [ ] **Step 2: Update tests**

Replace `tests/test_filter.py`:

```python
from obsidian_brain.filter import should_process, is_similar_experience


def _make_parsed(session_id, user_msgs):
    messages = []
    for msg in user_msgs:
        messages.append({"role": "user", "content": msg})
        messages.append({"role": "assistant", "content": "response to: " + msg})
    return {"session_id": session_id, "messages": messages}


def test_skip_too_few_user_messages():
    parsed = _make_parsed("abc", ["hi", "thanks"])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_process_enough_messages():
    parsed = _make_parsed("abc", [
        "Docker 네트워킹 설정 방법을 알려줘",
        "bridge와 host 네트워크의 차이가 뭐야?",
        "컨테이너 간 통신은 어떻게 하지?",
        "docker-compose에서 네트워크 설정하는 법",
    ])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is True


def test_skip_already_processed():
    parsed = _make_parsed("abc", ["질문 " * 10 for _ in range(10)])
    assert should_process(parsed, processed_ids={"abc"}, min_messages=3) is False


def test_skip_exactly_three_user_messages():
    parsed = _make_parsed("abc", [
        "첫 번째 질문입니다 설명해주세요",
        "두 번째 질문도 궁금합니다",
        "세 번째 질문까지만 할게요",
    ])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_skip_short_messages():
    parsed = _make_parsed("abc", ["ㅇ", "ㅎ", "ㅇㅇ", "ㄴㄴ", "ㅋ"])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


# --- is_similar_experience tests ---

def test_experience_dedup_exact_match(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")

    assert is_similar_experience(
        "schema 서브모듈 커밋 누락으로 Django 부팅 불가",
        tmp_path, "Experiences",
    ) is True


def test_experience_dedup_similar_title(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")

    assert is_similar_experience(
        "schema 서브모듈 커밋 누락으로 Django ModuleNotFoundError",
        tmp_path, "Experiences",
    ) is True


def test_experience_dedup_different_topic(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")

    assert is_similar_experience(
        "Celery 태스크 내 in-memory 캐시 vs Redis",
        tmp_path, "Experiences",
    ) is False


def test_experience_dedup_empty_dir(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    assert is_similar_experience("아무 제목", tmp_path, "Experiences") is False


def test_experience_dedup_no_dir(tmp_path):
    assert is_similar_experience("아무 제목", tmp_path, "Experiences") is False


def test_experience_dedup_threshold_06(tmp_path):
    """With threshold 0.6, moderately similar titles should NOT match."""
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "Django QuerySet 평가 시점 함정.md").write_text("# test")

    # Very different wording, same vague topic — should NOT match at 0.6
    assert is_similar_experience(
        "Django ORM 성능 최적화 팁",
        tmp_path, "Experiences",
    ) is False
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_filter.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/obsidian_brain/filter.py tests/test_filter.py
git commit -m "feat: raise experience dedup threshold to 0.6, remove conversation dedup"
```

---

### Task 8: Pipeline — Wire everything together

**Files:**
- Modify: `src/obsidian_brain/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
# Replace tests/test_pipeline.py entirely

import json
from pathlib import Path
from obsidian_brain.pipeline import process_session


def test_process_session_skips_trivial(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian-brain").mkdir()
    (vault / ".obsidian-brain" / ".processed").write_text("")
    (vault / "Experiences").mkdir()
    (vault / "Projects").mkdir()

    transcript = tmp_path / "trivial.jsonl"
    lines = [
        {"type": "user", "uuid": "u1", "message": {"content": "hi"}},
        {"type": "assistant", "uuid": "a1", "message": {"content": [{"type": "text", "text": "hello"}]}},
    ]
    with open(transcript, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    result = process_session(transcript_path=transcript, vault_path=vault, min_messages=3)
    assert result is None


def test_process_session_creates_daily_note(tmp_path, monkeypatch):
    import obsidian_brain.pipeline as pipeline_mod

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "Experiences").mkdir()
    (vault_path / "Projects").mkdir()
    (vault_path / ".obsidian-brain").mkdir()

    mock_analysis = {
        "summary": "Lead Scoring 리팩토링 및 Celery 타임아웃 해결",
        "title_slug": "lead-scoring-celery",
        "tags": ["django", "celery"],
        "decisions": ["가중치 균등 배분"],
        "daily_entries": [
            {"project": "wishket", "bullets": ["Lead Scoring v3 리팩토링", "Celery 타임아웃 해결"]},
        ],
        "experiences": [],
    }

    monkeypatch.setattr(pipeline_mod, "analyze", lambda *args, **kwargs: mock_analysis)
    monkeypatch.setattr(pipeline_mod, "should_process", lambda parsed, processed_ids, min_msg: True)
    monkeypatch.setattr(pipeline_mod, "load_processed_ids", lambda vault_path: set())
    monkeypatch.setattr(pipeline_mod, "save_processed_id", lambda vault_path, session_id: None)
    monkeypatch.setattr(pipeline_mod, "parse_transcript", lambda path: {
        "session_id": "test-session-123",
        "date": "2026-04-09",
        "messages": [
            {"role": "user", "content": "Lead Scoring 점수 기준을 바꾸자"},
            {"role": "assistant", "content": "가중치를 균등 배분으로 변경하겠습니다"},
        ] * 3,
    })
    monkeypatch.setattr(pipeline_mod, "load_config", lambda path: {
        "min_messages": 3,
        "model": "sonnet",
        "folders": {"daily": "Daily", "experiences": "Experiences", "projects": "Projects"},
        "projects": {
            "wishket": {"aliases": ["backend"], "description": "위시켓"},
        },
    })

    result = process_session(transcript_path=tmp_path / "t.jsonl", vault_path=vault_path)

    assert result is not None
    # Daily note created
    daily_files = list((vault_path / "Daily").glob("*.md"))
    assert len(daily_files) == 1
    assert daily_files[0].name == "2026-04-09.md"


def test_process_session_maps_alias_to_project(tmp_path, monkeypatch):
    import obsidian_brain.pipeline as pipeline_mod

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "Experiences").mkdir()
    (vault_path / "Projects").mkdir()
    (vault_path / ".obsidian-brain").mkdir()

    mock_analysis = {
        "summary": "백엔드 작업",
        "title_slug": "backend-work",
        "tags": [],
        "decisions": [],
        "daily_entries": [
            {"project": "backend", "bullets": ["API 수정"]},
        ],
        "experiences": [],
    }

    monkeypatch.setattr(pipeline_mod, "analyze", lambda *args, **kwargs: mock_analysis)
    monkeypatch.setattr(pipeline_mod, "should_process", lambda parsed, processed_ids, min_msg: True)
    monkeypatch.setattr(pipeline_mod, "load_processed_ids", lambda vault_path: set())
    monkeypatch.setattr(pipeline_mod, "save_processed_id", lambda vault_path, session_id: None)
    monkeypatch.setattr(pipeline_mod, "parse_transcript", lambda path: {
        "session_id": "test-456",
        "date": "2026-04-09",
        "messages": [{"role": "user", "content": "q"}] * 4 + [{"role": "assistant", "content": "a"}] * 4,
    })
    monkeypatch.setattr(pipeline_mod, "load_config", lambda path: {
        "min_messages": 3,
        "model": "sonnet",
        "folders": {"daily": "Daily", "experiences": "Experiences", "projects": "Projects"},
        "projects": {
            "wishket": {"aliases": ["backend"], "description": "위시켓"},
        },
    })

    result = process_session(transcript_path=tmp_path / "t.jsonl", vault_path=vault_path)

    import frontmatter
    daily = frontmatter.load(vault_path / "Daily" / "2026-04-09.md")
    # "backend" was mapped to "wishket"
    assert "wishket" in daily["projects"]
    assert "## [[wishket]]" in daily.content


def test_process_session_creates_experience_notes(tmp_path, monkeypatch):
    import obsidian_brain.pipeline as pipeline_mod

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "Experiences").mkdir()
    (vault_path / "Projects").mkdir()
    (vault_path / ".obsidian-brain").mkdir()

    mock_analysis = {
        "summary": "Django QuerySet 관련 작업",
        "title_slug": "django-queryset",
        "tags": ["django"],
        "decisions": [],
        "daily_entries": [{"project": "wishket", "bullets": ["QuerySet 최적화"]}],
        "experiences": [
            {
                "title": "Django QuerySet 평가 시점 함정",
                "experience_type": "problem-solving",
                "sections": {"상황": "느림", "선택": "values_list", "교훈": "lazy eval"},
                "tags": ["django"],
            }
        ],
    }

    monkeypatch.setattr(pipeline_mod, "analyze", lambda *args, **kwargs: mock_analysis)
    monkeypatch.setattr(pipeline_mod, "should_process", lambda parsed, processed_ids, min_msg: True)
    monkeypatch.setattr(pipeline_mod, "load_processed_ids", lambda vault_path: set())
    monkeypatch.setattr(pipeline_mod, "save_processed_id", lambda vault_path, session_id: None)
    monkeypatch.setattr(pipeline_mod, "parse_transcript", lambda path: {
        "session_id": "test-789",
        "date": "2026-04-09",
        "messages": [{"role": "user", "content": "Django admin 느려요"}] * 4
                   + [{"role": "assistant", "content": "QuerySet lazy eval"}] * 4,
    })
    monkeypatch.setattr(pipeline_mod, "load_config", lambda path: {
        "min_messages": 3,
        "model": "sonnet",
        "folders": {"daily": "Daily", "experiences": "Experiences", "projects": "Projects"},
        "projects": {"wishket": {"aliases": [], "description": "위시켓"}},
    })

    process_session(transcript_path=tmp_path / "t.jsonl", vault_path=vault_path)

    exp_files = list((vault_path / "Experiences").glob("*.md"))
    assert len(exp_files) == 1
    assert "QuerySet" in exp_files[0].stem
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — pipeline still uses old code

- [ ] **Step 3: Rewrite pipeline.py**

Replace `src/obsidian_brain/pipeline.py`:

```python
import logging
from pathlib import Path

from .analyzer import analyze
from .config import load_config
from .filter import is_similar_experience, should_process
from .generator import (
    generate_daily_doc,
    generate_experience_doc,
    generate_project_doc,
    update_project_doc,
)
from .parser import parse_transcript
from .project_mapper import resolve_project, resolve_projects
from .vault import load_processed_ids, save_processed_id, scan_experiences

logger = logging.getLogger(__name__)


def _extract_cwd_from_path(transcript_path: Path) -> str | None:
    """Extract the original cwd from the encoded transcript directory name."""
    encoded = transcript_path.parent.name
    if encoded.startswith("-"):
        return encoded.replace("-", "/")
    return None


def process_session(
    transcript_path: Path,
    vault_path: Path,
    min_messages: int = 3,
) -> Path | None:
    config = load_config(vault_path)
    min_msg = min_messages or config["min_messages"]
    projects_config = config.get("projects", {})

    parsed = parse_transcript(transcript_path)
    logger.info(f"Parsed session {parsed['session_id']}: {len(parsed['messages'])} messages")

    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids, min_msg):
        logger.info(f"Skipping session {parsed['session_id']}")
        return None

    cwd = _extract_cwd_from_path(transcript_path)

    # Gather existing experience titles for dedup
    exp_folder = config["folders"].get("experiences", "Experiences")
    existing_experiences = scan_experiences(vault_path, exp_folder)

    analysis = analyze(
        parsed,
        projects_config=projects_config,
        cwd=cwd,
        existing_experiences=existing_experiences,
        model=config.get("model", "sonnet"),
    )

    if not analysis:
        logger.warning("Analysis returned empty for session %s", parsed["session_id"])
        return None

    # Post-process: resolve project names in daily_entries
    for entry in analysis.get("daily_entries", []):
        if entry.get("project"):
            entry["project"] = resolve_project(entry["project"], projects_config)

    # Resolve project names in top-level for project doc updates
    resolved_projects = []
    for entry in analysis.get("daily_entries", []):
        if entry["project"] and entry["project"] not in resolved_projects:
            resolved_projects.append(entry["project"])

    # Generate daily note
    daily_path = generate_daily_doc(
        vault_path=vault_path,
        daily_folder=config["folders"].get("daily", "Daily"),
        date=parsed["date"],
        daily_entries=analysis.get("daily_entries", []),
        tags=analysis.get("tags", []),
    )
    logger.info(f"Created/updated daily note: {daily_path}")

    # Generate experience notes (skip duplicates)
    for exp in analysis.get("experiences", []):
        title = exp.get("title", "unknown")
        try:
            if is_similar_experience(title, vault_path, exp_folder):
                logger.info("Skipping duplicate experience: %s", title)
                continue
            generate_experience_doc(
                experience=exp,
                conversation_slug=daily_path.stem,
                date=parsed["date"],
                projects=resolved_projects,
                vault_path=vault_path,
                exp_folder=exp_folder,
            )
            logger.info("Created experience: %s", title)
        except Exception:
            logger.warning("Failed to generate experience note: %s", title)

    # Update project docs
    for project_name in resolved_projects:
        project_path = vault_path / config["folders"]["projects"] / f"{project_name}.md"
        if project_path.exists():
            update_project_doc(
                doc_path=project_path,
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
                summary=analysis["summary"],
                decisions=analysis.get("decisions"),
            )
            logger.info(f"Created project: {project_name}")

    save_processed_id(vault_path, parsed["session_id"])
    logger.info(f"Session {parsed['session_id']} processed successfully")

    return daily_path
```

- [ ] **Step 4: Run all tests**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/pipeline.py tests/test_pipeline.py
git commit -m "feat: rewrite pipeline to use daily notes, project mapping, and experience dedup"
```

---

### Task 9: Full test suite — verify nothing is broken

**Files:**
- All test files

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Fix any remaining failures**

Common issues to watch for:
- `test_integration.py` may reference old `generate_conversation_doc` or `is_similar_conversation` imports
- Other test files may import removed functions
- Fix imports and update test assertions as needed

- [ ] **Step 3: Run full suite again**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix: update remaining tests for daily note restructure"
```
