# Experience Notes Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the low-value Concept documents with Experience Notes that capture real problem-solving moments, discoveries, and troubleshooting in a format users actually want to read.

**Architecture:** Modify the analyzer prompt and schema to extract "experiences" instead of "concepts". Replace concept generation/update functions with experience note generation. Add a feedback loop via the existing session-start hook. Remove concept-related scanning, similarity, and trimming logic.

**Tech Stack:** Python, python-frontmatter, Claude API (existing), YAML config

---

### Task 1: Update Analyzer Schema and Prompt

**Files:**
- Modify: `src/obsidian_brain/analyzer.py:8-104`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing test for new schema**

```python
# tests/test_analyzer.py — add new test

def test_analysis_schema_has_experiences():
    from obsidian_brain.analyzer import ANALYSIS_SCHEMA
    props = ANALYSIS_SCHEMA["properties"]
    assert "experiences" in props
    assert "concepts" not in props

    exp_items = props["experiences"]["items"]["properties"]
    assert "title" in exp_items
    assert "experience_type" in exp_items
    assert "sections" in exp_items

    # experience_type must be enum
    assert set(exp_items["experience_type"]["enum"]) == {
        "problem-solving", "discovery", "troubleshooting"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/daeun/sssunda/obsidian-brain && python -m pytest tests/test_analyzer.py::test_analysis_schema_has_experiences -v`
Expected: FAIL — `KeyError: 'experiences'`

- [ ] **Step 3: Replace ANALYSIS_SCHEMA concepts with experiences**

Replace `ANALYSIS_SCHEMA` in `analyzer.py` lines 8-58. Remove `concepts` and `concept_relations` properties. Add `experiences` property:

```python
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "title_slug": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "reasoning_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "situation": {"type": "string"},
                    "choice": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["situation", "choice", "why"],
            },
        },
        "preferences": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
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
        "reasoning_patterns", "preferences", "projects", "experiences",
    ],
}
```

The `sections` field is a flexible dict — keys depend on `experience_type`:
- problem-solving: `{"상황": "...", "선택": "...", "교훈": "..."}`
- discovery: `{"발견": "...", "맥락": "..."}`
- troubleshooting: `{"삽질": "...", "원인": "...", "해결": "..."}`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analyzer.py::test_analysis_schema_has_experiences -v`
Expected: PASS

- [ ] **Step 5: Write failing test for new prompt**

```python
# tests/test_analyzer.py — add new test

def test_build_prompt_contains_experience_instructions():
    from obsidian_brain.analyzer import build_prompt

    parsed = {
        "messages": [
            {"role": "user", "content": "test message"}
        ],
        "date": "2026-04-01",
    }
    prompt = build_prompt(parsed, projects=["wishos"])
    assert "경험" in prompt or "experience" in prompt.lower()
    assert "개념" not in prompt  # no concept instructions
    assert "problem-solving" in prompt
    assert "discovery" in prompt
    assert "troubleshooting" in prompt
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_analyzer.py::test_build_prompt_contains_experience_instructions -v`
Expected: FAIL — prompt still contains "개념"

- [ ] **Step 7: Rewrite build_prompt()**

Replace `build_prompt()` in `analyzer.py`. Remove `concepts` and `existing_insights` parameters. Add experience extraction instructions:

```python
def build_prompt(parsed: dict, projects: list[str] | None = None) -> str:
    messages = parsed["messages"]
    date = parsed["date"]
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )
    transcript = truncate_messages(transcript)

    project_list = ""
    if projects:
        project_list = f"\n기존 프로젝트: {', '.join(projects)}"

    return f"""다음 AI 대화를 분석해줘.

날짜: {date}
{project_list}

## 분석 지침

1. summary: 이 대화에서 뭘 했는지 1-3문장으로 요약
2. title_slug: 영문 kebab-case 파일명 슬러그
3. tags: 소문자 영문 태그
4. decisions: 핵심 결정사항 목록
5. reasoning_patterns: situation/choice/why 구조의 의사결정 패턴 (실제로 판단/선택이 있었을 때만)
6. preferences: 드러난 행동 선호/원칙 (명시적 + 암시적)
7. projects: 관련 프로젝트 이름 (기존 프로젝트 목록에서 매칭)

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
```

- [ ] **Step 8: Remove _format_existing_insights()**

Delete `_format_existing_insights()` function (lines 95-104) — no longer needed.

- [ ] **Step 9: Update analyze() signature**

Remove `existing_insights` parameter from `analyze()`:

```python
def analyze(parsed: dict, projects: list[str] | None = None, model: str = "sonnet") -> dict:
    prompt = build_prompt(parsed, projects=projects)
    return call_claude(prompt, ANALYSIS_SCHEMA, model=model)
```

- [ ] **Step 10: Run all analyzer tests**

Run: `python -m pytest tests/test_analyzer.py -v`
Expected: All PASS. Fix any remaining tests that reference old `concepts` parameter.

- [ ] **Step 11: Commit**

```bash
git add src/obsidian_brain/analyzer.py tests/test_analyzer.py
git commit -m "feat: replace concept extraction with experience extraction in analyzer"
```

---

### Task 2: Create Experience Note Generator

**Files:**
- Modify: `src/obsidian_brain/generator.py:105-180`
- Test: `tests/test_generator.py`

- [ ] **Step 1: Write failing test for generate_experience_doc()**

```python
# tests/test_generator.py — add new test

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generator.py::test_generate_experience_doc_problem_solving -v`
Expected: FAIL — `ImportError: cannot import name 'generate_experience_doc'`

- [ ] **Step 3: Write failing test for discovery type**

```python
# tests/test_generator.py — add new test

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
```

- [ ] **Step 4: Implement generate_experience_doc()**

In `generator.py`, replace `generate_concept_doc()` (lines 105-146) and `update_concept_doc()` (lines 149-180) with:

```python
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
        doc_path = resolve_slug_conflict(doc_path)

    doc_path.write_text(output, encoding="utf-8")
    return doc_path
```

- [ ] **Step 5: Remove generate_concept_doc() and update_concept_doc()**

Delete `generate_concept_doc()` (lines 105-146) and `update_concept_doc()` (lines 149-180) entirely.

Also remove the import of `has_similar_insight, trim_insights` from similarity module at the top of generator.py.

- [ ] **Step 6: Update generate_conversation_doc() concept references**

In `generate_conversation_doc()`, replace the "관련 개념" section builder with "관련 경험" that links to experience notes. Find the section that references `analysis["concepts"]` and change it to `analysis.get("experiences", [])`:

```python
# In generate_conversation_doc(), replace concept linking with experience linking
experiences = analysis.get("experiences", [])
if experiences:
    exp_links = "\n".join(f"- [[{e['title']}]]" for e in experiences)
    _append_to_section(sections, "관련 경험", exp_links)
```

- [ ] **Step 7: Run all generator tests**

Run: `python -m pytest tests/test_generator.py -v`
Expected: All new tests PASS. Fix any old tests that reference concept functions.

- [ ] **Step 8: Commit**

```bash
git add src/obsidian_brain/generator.py tests/test_generator.py
git commit -m "feat: replace concept doc generation with experience note generation"
```

---

### Task 3: Update Pipeline to Use Experiences

**Files:**
- Modify: `src/obsidian_brain/pipeline.py:20-139`
- Modify: `src/obsidian_brain/vault.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test for pipeline with experiences**

```python
# tests/test_pipeline.py — add/replace test

def test_process_session_creates_experience_notes(tmp_path, mocker):
    from obsidian_brain.pipeline import process_session

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "Experiences").mkdir()
    (vault_path / "Conversations" / "2026-04").mkdir(parents=True)

    mock_analysis = {
        "summary": "Django admin LogEntry 관련 작업",
        "title_slug": "django-admin-logentry",
        "tags": ["django"],
        "decisions": ["values_list 사용"],
        "reasoning_patterns": [],
        "preferences": [],
        "projects": [],
        "experiences": [
            {
                "title": "Django QuerySet 평가 시점 함정",
                "experience_type": "problem-solving",
                "sections": {
                    "상황": "LogEntry bulk 조회가 느림",
                    "선택": "values_list로 즉시 평가",
                    "교훈": "변수 할당 ≠ 실행",
                },
                "tags": ["django", "queryset"],
            }
        ],
    }

    mocker.patch("obsidian_brain.pipeline.analyze", return_value=mock_analysis)
    mocker.patch("obsidian_brain.pipeline.is_similar_conversation", return_value=False)

    parsed = {
        "session_id": "test-session-123",
        "date": "2026-04-01",
        "messages": [
            {"role": "user", "content": "Django admin에서 LogEntry 조회가 느려요"},
            {"role": "assistant", "content": "QuerySet lazy evaluation 때문입니다"},
        ] * 3,
    }
    config = {
        "vault_path": str(vault_path),
        "folders": {
            "conversations": "Conversations",
            "experiences": "Experiences",
            "projects": "Projects",
        },
    }

    result = process_session(parsed, config)

    assert result is not None
    # Experience note created
    exp_files = list((vault_path / "Experiences").glob("*.md"))
    assert len(exp_files) == 1
    assert "QuerySet" in exp_files[0].stem
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::test_process_session_creates_experience_notes -v`
Expected: FAIL

- [ ] **Step 3: Update pipeline.py**

Replace concept-related logic in `process_session()`:

```python
import logging
from pathlib import Path

from .analyzer import analyze
from .filter import should_process, is_similar_conversation
from .generator import (
    generate_experience_doc,
    generate_conversation_doc,
    generate_project_doc,
    update_project_doc,
)
from .vault import scan_projects, load_processed_ids, save_processed_id

logger = logging.getLogger(__name__)


def process_session(parsed: dict, config: dict) -> str | None:
    session_id = parsed["session_id"]
    vault_path = Path(config["vault_path"])
    conv_folder = config["folders"]["conversations"]
    exp_folder = config["folders"].get("experiences", "Experiences")
    proj_folder = config["folders"].get("projects", "Projects")

    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids):
        return None

    projects = scan_projects(vault_path, proj_folder)

    analysis = analyze(parsed, projects=projects)

    if not analysis:
        logger.warning("Analysis returned empty for session %s", session_id)
        return None

    # Dedup check
    if is_similar_conversation(
        summary=analysis["summary"],
        vault_path=vault_path,
        conv_folder=conv_folder,
        date=parsed["date"],
    ):
        logger.info("Similar conversation already exists, skipping %s", session_id)
        return None

    # Generate conversation doc
    conv_path = generate_conversation_doc(
        analysis=analysis,
        parsed=parsed,
        vault_path=vault_path,
        conv_folder=conv_folder,
    )

    # Generate experience notes
    experiences = analysis.get("experiences", [])
    for exp in experiences:
        try:
            generate_experience_doc(
                experience=exp,
                conversation_slug=conv_path.stem,
                date=parsed["date"],
                projects=analysis.get("projects", []),
                vault_path=vault_path,
                exp_folder=exp_folder,
            )
        except Exception:
            logger.warning("Failed to generate experience note: %s", exp.get("title", "unknown"))

    # Generate/update project docs (unchanged)
    for project_name in analysis.get("projects", []):
        proj_path = vault_path / proj_folder / f"{project_name}.md"
        try:
            if proj_path.exists():
                update_project_doc(
                    project_path=proj_path,
                    conversation_slug=conv_path.stem,
                    summary=analysis["summary"],
                    decisions=analysis.get("decisions", []),
                    date=parsed["date"],
                )
            else:
                generate_project_doc(
                    project_name=project_name,
                    conversation_slug=conv_path.stem,
                    summary=analysis["summary"],
                    decisions=analysis.get("decisions", []),
                    date=parsed["date"],
                    vault_path=vault_path,
                    proj_folder=proj_folder,
                )
        except Exception:
            logger.warning("Failed to update project doc: %s", project_name)

    save_processed_id(vault_path, session_id)
    return str(conv_path)
```

- [ ] **Step 4: Remove concept-related vault functions**

In `vault.py`, remove `scan_concepts()` (lines 8-12) and `scan_existing_insights()` (lines 39-66). Keep `scan_projects()`, `load_processed_ids()`, `save_processed_id()`, and `rotate_processed()`.

- [ ] **Step 5: Run pipeline test**

Run: `python -m pytest tests/test_pipeline.py::test_process_session_creates_experience_notes -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/pipeline.py src/obsidian_brain/vault.py tests/test_pipeline.py
git commit -m "feat: pipeline generates experience notes instead of concept docs"
```

---

### Task 4: Update Config and Folder Structure

**Files:**
- Modify: `src/obsidian_brain/config.py`
- Modify: `scripts/install-hooks.sh`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test for new config**

```python
# tests/test_config.py — add new test

def test_default_config_has_experiences_folder():
    from obsidian_brain.config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["folders"]["experiences"] == "Experiences"
    assert "concepts" not in DEFAULT_CONFIG["folders"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::test_default_config_has_experiences_folder -v`
Expected: FAIL

- [ ] **Step 3: Update DEFAULT_CONFIG**

In `config.py`, replace `concepts` folder with `experiences`:

```python
# In DEFAULT_CONFIG["folders"]
"experiences": "Experiences",  # was "concepts": "Concepts"
```

Remove `max_insights` and `similarity_threshold` from DEFAULT_CONFIG — no longer needed.

- [ ] **Step 4: Update install-hooks.sh**

In `scripts/install-hooks.sh`, replace `Concepts` directory creation with `Experiences`:

Find the `mkdir` line that creates `Concepts` and change to `Experiences`.

- [ ] **Step 5: Run config tests**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/config.py scripts/install-hooks.sh tests/test_config.py
git commit -m "feat: update config and install script for experiences folder"
```

---

### Task 5: Update CSS

**Files:**
- Modify: `templates/obsidian-brain.css`

- [ ] **Step 1: Replace .ob-concept with .ob-experience**

In `templates/obsidian-brain.css`, replace:

```css
.ob-concept {
  --color-accent: var(--color-green);
  border-left: 3px solid var(--color-accent);
}
```

with:

```css
.ob-experience {
  --color-accent: var(--color-green);
  border-left: 3px solid var(--color-accent);
}
```

- [ ] **Step 2: Commit**

```bash
git add templates/obsidian-brain.css
git commit -m "feat: replace ob-concept CSS class with ob-experience"
```

---

### Task 6: Add Feedback Loop

**Files:**
- Modify: `src/obsidian_brain/__main__.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for feedback collection**

```python
# tests/test_cli.py — add new test

def test_show_last_result_with_experiences(tmp_path):
    import json
    from obsidian_brain.__main__ import _write_last_result, _read_last_result

    result_data = {
        "conversation": "2026-04-01-django-admin-logentry",
        "experiences": ["Django QuerySet 평가 시점 함정"],
    }

    state_dir = tmp_path / ".obsidian-brain"
    state_dir.mkdir()

    _write_last_result(result_data, state_dir)
    loaded = _read_last_result(state_dir)
    assert loaded["experiences"] == ["Django QuerySet 평가 시점 함정"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_show_last_result_with_experiences -v`
Expected: FAIL

- [ ] **Step 3: Write failing test for feedback saving**

```python
# tests/test_cli.py — add new test

def test_save_feedback(tmp_path):
    import json
    from obsidian_brain.__main__ import _save_feedback

    state_dir = tmp_path / ".obsidian-brain"
    state_dir.mkdir()

    _save_feedback(
        state_dir=state_dir,
        note_title="Django QuerySet 평가 시점 함정",
        rating="n",
        reason="너무 뻔한 내용",
    )

    feedback_path = state_dir / "feedback.jsonl"
    assert feedback_path.exists()
    line = json.loads(feedback_path.read_text().strip())
    assert line["note"] == "Django QuerySet 평가 시점 함정"
    assert line["rating"] == "n"
    assert line["reason"] == "너무 뻔한 내용"
```

- [ ] **Step 4: Implement feedback functions in __main__.py**

Add to `__main__.py`:

```python
import json
from datetime import date


def _read_last_result(state_dir: Path) -> dict | None:
    result_path = state_dir / "last_result.json"
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _save_feedback(
    state_dir: Path,
    note_title: str,
    rating: str,
    reason: str = "",
) -> None:
    feedback_path = state_dir / "feedback.jsonl"
    entry = {
        "date": str(date.today()),
        "note": note_title,
        "rating": rating,
        "reason": reason,
    }
    with open(feedback_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

Update `_write_last_result()` to include experience titles in the result data. In `cmd_process()`, after `process_session()` returns, write:

```python
result_data = {
    "conversation": conv_path_stem,
    "experiences": [e["title"] for e in analysis.get("experiences", [])],
}
_write_last_result(result_data, state_dir)
```

Update `_show_last_result()` to display experience notes and prompt for feedback:

```python
def _show_last_result(state_dir: Path) -> None:
    result = _read_last_result(state_dir)
    if not result:
        return

    experiences = result.get("experiences", [])
    if not experiences:
        # Clean up and return
        (state_dir / "last_result.json").unlink(missing_ok=True)
        return

    print(f"\n[이전 세션 경험 노트]")
    for title in experiences:
        print(f"  📝 {title}")
    print()

    try:
        answer = input("유용했나요? (y/n/엔터=스킵): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""

    if answer in ("y", "n"):
        reason = ""
        if answer == "n":
            try:
                reason = input("이유 한 줄: ").strip()
            except (EOFError, KeyboardInterrupt):
                reason = ""

        for title in experiences:
            _save_feedback(state_dir, title, answer, reason)

    (state_dir / "last_result.json").unlink(missing_ok=True)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/__main__.py tests/test_cli.py
git commit -m "feat: add experience note feedback loop"
```

---

### Task 7: Clean Up Dead Code and Update Remaining Tests

**Files:**
- Modify: `src/obsidian_brain/similarity.py`
- Modify: `tests/test_integration.py`
- Modify: `tests/test_vault.py`
- Modify: `tests/test_similarity.py`
- Modify: `src/obsidian_brain/__main__.py` (status command)

- [ ] **Step 1: Simplify similarity.py**

Remove concept-related functions: `has_similar_insight()`, `count_insights()`, `trim_insights()`, and `MAX_INSIGHTS` constant.

Keep only `is_similar()` and `DEFAULT_THRESHOLD` — still used for conversation deduplication in `filter.py`.

- [ ] **Step 2: Update status command**

In `__main__.py`, `cmd_status()` currently counts concept docs. Replace with experience note count:

Find: `concept_count = sum(1 for _ in concept_dir.glob("*.md"))`
Replace with: `exp_count = sum(1 for _ in exp_dir.glob("*.md"))` where `exp_dir` uses the `experiences` folder from config.

Update the status display line accordingly.

- [ ] **Step 3: Update integration test**

Replace `tests/test_integration.py` mock analysis to return `experiences` instead of `concepts`:

```python
def _mock_analyze(parsed, projects=None, model="sonnet"):
    return {
        "summary": "테스트 대화 요약",
        "title_slug": "test-conversation",
        "tags": ["test"],
        "decisions": ["테스트 결정"],
        "reasoning_patterns": [],
        "preferences": [],
        "projects": [],
        "experiences": [
            {
                "title": "테스트 삽질 경험",
                "experience_type": "troubleshooting",
                "sections": {
                    "삽질": "뭔가 안 됨",
                    "원인": "설정 문제",
                    "해결": "설정 변경",
                },
                "tags": ["test"],
            }
        ],
    }
```

Update the assertions to check for experience note creation instead of concept doc creation.

- [ ] **Step 4: Fix test_vault.py**

Remove tests for `scan_concepts()` and `scan_existing_insights()`. Add any needed tests for remaining vault functions.

- [ ] **Step 5: Fix test_similarity.py**

Remove tests for `has_similar_insight()`, `count_insights()`, `trim_insights()`. Keep tests for `is_similar()`.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/obsidian_brain/similarity.py src/obsidian_brain/__main__.py tests/
git commit -m "chore: remove concept dead code, update all tests for experiences"
```

---

### Task 8: Update Digest to Use Experience Notes

**Files:**
- Modify: `src/obsidian_brain/digest.py`
- Test: `tests/test_digest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_digest.py — add/update test

def test_digest_reads_experience_notes(tmp_path):
    from obsidian_brain.digest import collect_recent_experiences

    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()

    # Create a sample experience note
    note = """---
type: experience
experience_type: problem-solving
created: '2026-04-01'
tags: [django]
---

# Django QuerySet 평가 시점 함정

## 상황
Admin에서 LogEntry bulk 조회가 느림

## 선택
values_list로 즉시 평가

## 교훈
변수 할당 ≠ 실행
"""
    (exp_dir / "Django QuerySet 평가 시점 함정.md").write_text(note)

    experiences = collect_recent_experiences(tmp_path, "Experiences", days=30)
    assert len(experiences) == 1
    assert experiences[0]["title"] == "Django QuerySet 평가 시점 함정"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_digest.py::test_digest_reads_experience_notes -v`
Expected: FAIL

- [ ] **Step 3: Add collect_recent_experiences() to digest.py**

```python
def collect_recent_experiences(
    vault_path: Path, exp_folder: str, days: int = 30
) -> list[dict]:
    """Collect experience notes from the last N days."""
    exp_dir = vault_path / exp_folder
    if not exp_dir.exists():
        return []

    cutoff = date.today() - timedelta(days=days)
    experiences = []

    for f in exp_dir.glob("*.md"):
        try:
            post = frontmatter.load(f)
            created = post.metadata.get("created", "")
            if isinstance(created, str):
                created_date = date.fromisoformat(created)
            else:
                created_date = created
            if created_date >= cutoff:
                experiences.append({
                    "title": f.stem,
                    "experience_type": post.metadata.get("experience_type", ""),
                    "content": post.content,
                    "tags": post.metadata.get("tags", []),
                    "created": str(created_date),
                })
        except (ValueError, KeyError, OSError):
            continue

    return experiences
```

- [ ] **Step 4: Update digest prompt to use experiences instead of concepts**

In the digest generation function, replace concept/insight references with experience note content. The digest should summarize patterns across recent experience notes rather than concept insights.

- [ ] **Step 5: Run digest tests**

Run: `python -m pytest tests/test_digest.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/digest.py tests/test_digest.py
git commit -m "feat: digest uses experience notes instead of concept insights"
```

---

### Task 9: Update Migration Script

**Files:**
- Modify: `src/obsidian_brain/migrate.py`
- Test: `tests/test_migrate.py`

- [ ] **Step 1: Update migrate.py**

Add a migration function that renames/moves existing `Concepts/` folder if it exists, and creates `Experiences/` folder. The migration should:

```python
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
        import shutil
        result["removed_concepts"] = sum(1 for _ in concepts_dir.glob("*.md"))
        shutil.rmtree(concepts_dir)

    return result
```

Note: We don't try to convert old concept docs to experience notes — they were low quality (the whole reason for this redesign). Just remove them.

- [ ] **Step 2: Write test**

```python
# tests/test_migrate.py — add test

def test_migrate_concepts_to_experiences(tmp_path):
    from obsidian_brain.migrate import migrate_concepts_to_experiences

    # Setup old structure
    concepts_dir = tmp_path / "Concepts"
    concepts_dir.mkdir()
    (concepts_dir / "Old Concept.md").write_text("old content")
    (concepts_dir / "Another Concept.md").write_text("old content")

    result = migrate_concepts_to_experiences(tmp_path)

    assert result["removed_concepts"] == 2
    assert result["created_experiences_dir"] is True
    assert not concepts_dir.exists()
    assert (tmp_path / "Experiences").exists()
```

- [ ] **Step 3: Run test**

Run: `python -m pytest tests/test_migrate.py::test_migrate_concepts_to_experiences -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/obsidian_brain/migrate.py tests/test_migrate.py
git commit -m "feat: add migration from concepts to experiences folder structure"
```

---

### Task 10: Final Integration Test and Full Suite

**Files:**
- Test: `tests/test_integration.py`

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Fix any remaining failures**

Address any test failures from import changes, removed functions, or updated signatures.

- [ ] **Step 3: Run full suite again to confirm**

Run: `python -m pytest tests/ -v`
Expected: All PASS, zero failures

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: ensure full test suite passes after experience notes redesign"
```
