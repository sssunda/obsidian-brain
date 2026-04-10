# Obsidian Brain Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-generate Obsidian documents from Claude Code conversations with concept extraction and [[wiki link]] formation.

**Architecture:** Python CLI pipeline triggered by Claude Code SessionEnd/SessionStart hooks. Parses transcript.jsonl → filters trivial sessions → analyzes via `claude -p --model sonnet --output-format json` → generates Obsidian markdown with [[links]]. Single-process execution with lockfile for concurrency control.

**Tech Stack:** Python 3.11+, uv, python-frontmatter, Claude Code CLI, PyYAML

**Spec:** `docs/superpowers/specs/2026-03-25-obsidian-brain-design.md`

---

## File Structure

```
obsidian-brain/
├── pyproject.toml                    # Project config, dependencies, entry points
├── src/
│   └── obsidian_brain/
│       ├── __init__.py
│       ├── __main__.py               # CLI entry point (process / recover commands)
│       ├── config.py                 # Config loading from .obsidian-brain/config.yaml
│       ├── lockfile.py               # Lockfile acquisition/release
│       ├── parser.py                 # transcript.jsonl → unified format
│       ├── filter.py                 # Skip trivial/already-processed sessions
│       ├── analyzer.py               # claude -p invocation + prompt construction
│       ├── generator.py              # Obsidian markdown generation + vault updates
│       ├── vault.py                  # Vault scanning (existing concepts/projects)
│       ├── recovery.py               # SessionStart recovery logic
│       └── pipeline.py               # Orchestrates parser→filter→analyzer→generator
├── tests/
│   ├── conftest.py                   # Shared fixtures (tmp vault, sample transcripts)
│   ├── test_parser.py
│   ├── test_filter.py
│   ├── test_analyzer.py
│   ├── test_generator.py
│   ├── test_vault.py
│   ├── test_lockfile.py
│   ├── test_pipeline.py
│   └── fixtures/
│       ├── sample_transcript.jsonl   # Real-format transcript for testing
│       └── sample_vault/             # Minimal vault with existing concepts/projects
│           ├── .obsidian-brain/
│           │   ├── config.yaml
│           │   └── .processed
│           ├── Concepts/
│           │   └── Docker.md
│           └── Projects/
│               └── theta-todo.md
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-03-25-obsidian-brain-design.md
        └── plans/
            └── 2026-03-25-obsidian-brain-phase1.md
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/obsidian_brain/__init__.py`
- Create: `src/obsidian_brain/__main__.py` (stub)
- Create: `tests/conftest.py` (stub)

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "obsidian-brain"
version = "0.1.0"
description = "Auto-generate Obsidian documents from AI conversations"
requires-python = ">=3.11"
dependencies = [
    "python-frontmatter>=1.1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/obsidian_brain"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create __init__.py**

```python
# src/obsidian_brain/__init__.py
```

- [ ] **Step 3: Create __main__.py stub**

```python
# src/obsidian_brain/__main__.py
import sys


def main():
    print("obsidian-brain: not yet implemented")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create tests/conftest.py stub**

```python
# tests/conftest.py
```

- [ ] **Step 5: Install dependencies and verify**

Run: `cd /path/to/obsidian-brain && uv sync --dev`
Expected: Dependencies installed successfully

- [ ] **Step 6: Verify module runs**

Run: `cd /path/to/obsidian-brain && uv run python -m obsidian_brain`
Expected: "obsidian-brain: not yet implemented"

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/conftest.py
git commit -m "feat: scaffold project with pyproject.toml and entry point"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/obsidian_brain/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import yaml
from pathlib import Path
from obsidian_brain.config import load_config, DEFAULT_CONFIG


def test_load_config_defaults(tmp_path):
    """When no config.yaml exists, return defaults."""
    config = load_config(tmp_path)
    assert config["min_messages"] == 3
    assert config["max_transcript_chars"] == 50000
    assert config["max_retries"] == 3
    assert config["processed_retention_days"] == 30
    assert config["slug_language"] == "en"
    assert config["folders"]["conversations"] == "Conversations"
    assert config["folders"]["concepts"] == "Concepts"
    assert config["folders"]["projects"] == "Projects"


def test_load_config_from_file(tmp_path):
    """When config.yaml exists, merge with defaults."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "min_messages": 5,
        "slug_language": "ko",
    }))
    config = load_config(tmp_path)
    assert config["min_messages"] == 5
    assert config["slug_language"] == "ko"
    # defaults preserved for unset keys
    assert config["max_retries"] == 3


def test_load_config_vault_path_resolution(tmp_path):
    """vault_path in config is resolved to absolute path."""
    config_dir = tmp_path / ".obsidian-brain"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({"vault_path": str(tmp_path)}))
    config = load_config(tmp_path)
    assert Path(config["vault_path"]).is_absolute()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_config.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/config.py
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "vault_path": None,
    "min_messages": 3,
    "max_transcript_chars": 50000,
    "max_retries": 3,
    "processed_retention_days": 30,
    "slug_language": "en",
    "folders": {
        "conversations": "Conversations",
        "concepts": "Concepts",
        "projects": "Projects",
    },
}


def load_config(vault_path: Path) -> dict:
    """Load config from .obsidian-brain/config.yaml, merged with defaults."""
    config = _deep_copy(DEFAULT_CONFIG)
    config["vault_path"] = str(vault_path.resolve())

    config_file = vault_path / ".obsidian-brain" / "config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)

    if config.get("vault_path"):
        config["vault_path"] = str(Path(config["vault_path"]).expanduser().resolve())

    return config


def _deep_copy(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        result[k] = _deep_copy(v) if isinstance(v, dict) else v
    return result


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/config.py tests/test_config.py
git commit -m "feat: add config module with YAML loading and defaults"
```

---

## Task 3: Lockfile Module

**Files:**
- Create: `src/obsidian_brain/lockfile.py`
- Create: `tests/test_lockfile.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lockfile.py
from obsidian_brain.lockfile import acquire_lock, release_lock


def test_acquire_and_release(tmp_path):
    """Can acquire lock, then release it."""
    lock_path = tmp_path / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=2)
    assert lock_fd is not None
    assert lock_path.exists()
    release_lock(lock_fd, lock_path)
    assert not lock_path.exists()


def test_acquire_blocks_second_caller(tmp_path):
    """Second acquire with timeout=0 returns None if already locked."""
    lock_path = tmp_path / "pipeline.lock"
    fd1 = acquire_lock(lock_path, timeout=2)
    assert fd1 is not None
    fd2 = acquire_lock(lock_path, timeout=0)
    assert fd2 is None
    release_lock(fd1, lock_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_lockfile.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/lockfile.py
import fcntl
import time
from pathlib import Path


def acquire_lock(lock_path: Path, timeout: int = 30) -> int | None:
    """Acquire file lock. Returns fd on success, None on timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(lock_path, "w")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.write(str(time.time()))
            fd.flush()
            return fd
        except OSError:
            if time.monotonic() >= deadline:
                fd.close()
                return None
            time.sleep(0.5)


def release_lock(fd, lock_path: Path) -> None:
    """Release file lock and remove lock file."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_lockfile.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/lockfile.py tests/test_lockfile.py
git commit -m "feat: add lockfile module for concurrency control"
```

---

## Task 4: Parser Module

**Files:**
- Create: `src/obsidian_brain/parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/sample_transcript.jsonl`

- [ ] **Step 1: Create sample transcript fixture**

Based on real Claude Code transcript format. Create `tests/fixtures/sample_transcript.jsonl`:

```python
# Generate this with a script since it's JSONL:
# tests/fixtures/create_fixture.py — run once, then delete
import json
from pathlib import Path

lines = [
    {"type": "progress", "data": {"type": "hook_progress"}, "parentUuid": None, "isSidechain": False},
    {"type": "system", "message": {"content": "system prompt"}, "parentUuid": None, "isSidechain": False},
    {"type": "file-history-snapshot", "messageId": "snap1", "snapshot": {}},
    {
        "type": "user",
        "uuid": "u1",
        "parentUuid": None,
        "isSidechain": False,
        "message": {"role": "user", "content": "Docker 네트워킹에 대해 알려줘"}
    },
    {
        "type": "assistant",
        "uuid": "a1",
        "parentUuid": "u1",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "Let me explain Docker networking..."},
                {"type": "text", "text": "Docker 네트워킹은 컨테이너 간 통신을 관리합니다."},
                {"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"command": "docker network ls"}}
            ]
        }
    },
    {"type": "progress", "data": {"type": "tool_progress"}, "parentUuid": "a1", "isSidechain": False},
    {
        "type": "user",
        "uuid": "u2",
        "parentUuid": "a1",
        "isSidechain": False,
        "message": {"role": "user", "content": "bridge 네트워크랑 host 네트워크 차이가 뭐야?"}
    },
    {
        "type": "assistant",
        "uuid": "a2",
        "parentUuid": "u2",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Bridge는 격리된 네트워크, Host는 호스트 네트워크를 공유합니다."}
            ]
        }
    },
    {
        "type": "user",
        "uuid": "u3",
        "parentUuid": "a2",
        "isSidechain": False,
        "message": {"role": "user", "content": "고마워"}
    },
    {
        "type": "assistant",
        "uuid": "a3",
        "parentUuid": "u3",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "도움이 되었다니 기쁘네요!"}
            ]
        }
    },
]

fixture_path = Path(__file__).parent / "fixtures" / "sample_transcript.jsonl"
fixture_path.parent.mkdir(parents=True, exist_ok=True)
with open(fixture_path, "w") as f:
    for line in lines:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
print(f"Created {fixture_path}")
```

Run once: `cd /path/to/obsidian-brain && uv run python tests/fixtures/create_fixture.py`
Then delete `create_fixture.py`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_parser.py
from pathlib import Path
from obsidian_brain.parser import parse_transcript, encode_cwd, build_transcript_path

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_transcript_extracts_user_and_assistant():
    """Only user and assistant text blocks are extracted."""
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    messages = result["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]


def test_parse_transcript_excludes_thinking_and_tool_use():
    """Assistant thinking and tool_use blocks are excluded."""
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    first_assistant = result["messages"][1]
    assert "thinking" not in first_assistant["content"].lower() or "Let me explain" not in first_assistant["content"]
    assert "docker network ls" not in first_assistant["content"]
    assert "Docker 네트워킹은" in first_assistant["content"]


def test_parse_transcript_user_content_is_string():
    """User messages have string content."""
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    first_user = result["messages"][0]
    assert first_user["content"] == "Docker 네트워킹에 대해 알려줘"


def test_parse_transcript_metadata():
    """Parsed result includes source and date."""
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    assert result["source"] == "claude-code"
    assert "date" in result


def test_encode_cwd():
    """CWD encoding replaces / with - and adds leading -."""
    assert encode_cwd("/path/to/work") == "-path-to-work"
    assert encode_cwd("/") == "-"


def test_encode_cwd_preserves_hyphens():
    """Literal hyphens in path components are double-encoded."""
    # Note: In practice, Claude Code uses its own encoding.
    # We match the observed pattern from ~/.claude/projects/
    encoded = encode_cwd("/Users/me/my-project")
    assert "my" in encoded and "project" in encoded


def test_build_transcript_path():
    """Build correct transcript path from session_id and cwd."""
    path = build_transcript_path("abc123", "/path/to/work")
    expected = Path.home() / ".claude" / "projects" / "-path-to-work" / "abc123.jsonl"
    assert path == expected
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_parser.py -v`
Expected: FAIL

- [ ] **Step 4: Write implementation**

```python
# src/obsidian_brain/parser.py
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_transcript(transcript_path: Path) -> dict:
    """Parse a Claude Code transcript.jsonl into unified format."""
    messages = []
    session_id = transcript_path.stem

    with open(transcript_path) as f:
        for line in f:
            record = json.loads(line)
            record_type = record.get("type")

            if record_type == "user":
                content = record.get("message", {}).get("content", "")
                if isinstance(content, str) and content.strip():
                    messages.append({"role": "user", "content": content})

            elif record_type == "assistant":
                content = record.get("message", {}).get("content", [])
                text_parts = []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                elif isinstance(content, str):
                    text_parts.append(content)
                combined = "\n".join(text_parts).strip()
                if combined:
                    messages.append({"role": "assistant", "content": combined})

    mtime = transcript_path.stat().st_mtime
    date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "session_id": session_id,
        "source": "claude-code",
        "date": date_str,
        "messages": messages,
    }


def encode_cwd(cwd: str) -> str:
    """Encode CWD path to Claude project directory name.
    Replaces '/' with '-' and '--' for literal hyphens in path components.
    """
    # Replace literal hyphens first, then path separators
    return "-" + cwd.lstrip("/").replace("-", "--").replace("/", "-")


def build_transcript_path(session_id: str, cwd: str) -> Path:
    """Build transcript file path from session_id and cwd."""
    encoded = encode_cwd(cwd)
    return Path.home() / ".claude" / "projects" / encoded / f"{session_id}.jsonl"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_parser.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/parser.py tests/test_parser.py tests/fixtures/
git commit -m "feat: add parser for Claude Code transcript.jsonl"
```

---

## Task 5: Filter Module

**Files:**
- Create: `src/obsidian_brain/filter.py`
- Create: `tests/test_filter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_filter.py
from obsidian_brain.filter import should_process


def test_skip_too_few_user_messages():
    """Skip sessions with 3 or fewer user messages."""
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "thanks"},
            {"role": "assistant", "content": "bye"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_process_enough_messages():
    """Process sessions with more than min_messages user messages."""
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
            {"role": "user", "content": "q4"},
            {"role": "assistant", "content": "a4"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is True


def test_skip_already_processed():
    """Skip sessions that are already in processed set."""
    parsed = {
        "session_id": "abc",
        "messages": [{"role": "user", "content": f"q{i}"} for i in range(10)],
    }
    assert should_process(parsed, processed_ids={"abc"}, min_messages=3) is False


def test_skip_already_processed_even_with_enough_messages():
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": f"q{i}"} for i in range(10)
        ],
    }
    assert should_process(parsed, processed_ids={"abc"}, min_messages=3) is False


def test_skip_exactly_three_user_messages():
    """Exactly 3 user messages should be skipped (boundary case)."""
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_filter.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/filter.py


def should_process(parsed: dict, processed_ids: set[str], min_messages: int = 3) -> bool:
    """Determine if a parsed session should be processed."""
    session_id = parsed["session_id"]
    if session_id in processed_ids:
        return False

    user_count = sum(1 for m in parsed["messages"] if m["role"] == "user")
    return user_count > min_messages
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_filter.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/filter.py tests/test_filter.py
git commit -m "feat: add filter module for session skip logic"
```

---

## Task 6: Vault Scanner Module

**Files:**
- Create: `src/obsidian_brain/vault.py`
- Create: `tests/test_vault.py`
- Create: `tests/fixtures/sample_vault/` (directory with sample docs)

- [ ] **Step 1: Create sample vault fixture**

```bash
mkdir -p tests/fixtures/sample_vault/.obsidian-brain
mkdir -p tests/fixtures/sample_vault/Concepts
mkdir -p tests/fixtures/sample_vault/Projects
```

Create `tests/fixtures/sample_vault/.obsidian-brain/config.yaml`:
```yaml
vault_path: .
min_messages: 3
```

Create `tests/fixtures/sample_vault/.obsidian-brain/.processed`:
```
old-session-id-1
old-session-id-2
```

Create `tests/fixtures/sample_vault/Concepts/Docker.md`:
```markdown
---
type: concept
created: 2026-03-20
updated: 2026-03-20
aliases: [docker, container platform]
conversations: [2026-03-20-docker-basics]
---

# Docker

컨테이너 기반 가상화 플랫폼.

## 인사이트
- (2026-03-20) 멀티스테이지 빌드로 이미지 크기를 줄일 수 있다

## 관련 개념
- [[컨테이너]]
```

Create `tests/fixtures/sample_vault/Projects/theta-todo.md`:
```markdown
---
type: project
created: 2026-03-19
updated: 2026-03-19
status: active
conversations: [2026-03-19-theta-setup]
---

# theta-todo

Example project description.
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_vault.py
from pathlib import Path
from obsidian_brain.vault import scan_concepts, scan_projects, load_processed_ids, save_processed_id

SAMPLE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def test_scan_concepts():
    """Scan concept names from Concepts/ folder."""
    concepts = scan_concepts(SAMPLE_VAULT, "Concepts")
    assert "Docker" in concepts


def test_scan_projects():
    """Scan project names from Projects/ folder."""
    projects = scan_projects(SAMPLE_VAULT, "Projects")
    assert "theta-todo" in projects


def test_load_processed_ids():
    """Load processed session IDs from .processed file."""
    ids = load_processed_ids(SAMPLE_VAULT)
    assert "old-session-id-1" in ids
    assert "old-session-id-2" in ids


def test_load_processed_ids_missing_file(tmp_path):
    """Return empty set when .processed doesn't exist."""
    brain_dir = tmp_path / ".obsidian-brain"
    brain_dir.mkdir()
    ids = load_processed_ids(tmp_path)
    assert ids == set()


def test_save_processed_id(tmp_path):
    """Append session ID to .processed file."""
    brain_dir = tmp_path / ".obsidian-brain"
    brain_dir.mkdir()
    save_processed_id(tmp_path, "new-session-123")
    ids = load_processed_ids(tmp_path)
    assert "new-session-123" in ids
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_vault.py -v`
Expected: FAIL

- [ ] **Step 4: Write implementation**

```python
# src/obsidian_brain/vault.py
from pathlib import Path

import frontmatter


def scan_concepts(vault_path: Path, folder: str = "Concepts") -> list[str]:
    """Return list of existing concept names (from filenames, stem only)."""
    concepts_dir = vault_path / folder
    if not concepts_dir.exists():
        return []
    return [f.stem for f in concepts_dir.glob("*.md")]


def scan_projects(vault_path: Path, folder: str = "Projects") -> list[str]:
    """Return list of existing project names (from filenames, stem only)."""
    projects_dir = vault_path / folder
    if not projects_dir.exists():
        return []
    return [f.stem for f in projects_dir.glob("*.md")]


def load_processed_ids(vault_path: Path) -> set[str]:
    """Load set of already-processed session IDs."""
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    if not processed_file.exists():
        return set()
    text = processed_file.read_text().strip()
    if not text:
        return set()
    return {line.split("\t")[0] for line in text.splitlines() if line.strip()}


def save_processed_id(vault_path: Path, session_id: str) -> None:
    """Append a session ID with timestamp to the .processed file."""
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    with open(processed_file, "a") as f:
        f.write(f"{session_id}\t{datetime.now().isoformat()}\n")


def rotate_processed(vault_path: Path, retention_days: int = 30) -> None:
    """Remove entries older than retention_days from .processed file."""
    processed_file = vault_path / ".obsidian-brain" / ".processed"
    if not processed_file.exists():
        return
    from datetime import datetime, timedelta
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
        kept.append(line)  # keep lines without timestamp (legacy)
    processed_file.write_text("\n".join(kept) + "\n" if kept else "")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_vault.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_brain/vault.py tests/test_vault.py tests/fixtures/sample_vault/
git commit -m "feat: add vault scanner for concepts, projects, and processed IDs"
```

---

## Task 7: Analyzer Module

**Files:**
- Create: `src/obsidian_brain/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analyzer.py
import json
from obsidian_brain.analyzer import build_prompt, build_json_schema, truncate_messages, ANALYSIS_SCHEMA


def test_build_prompt_includes_concepts_and_projects():
    """Prompt includes existing concept and project names."""
    parsed = {
        "messages": [
            {"role": "user", "content": "Docker 네트워킹 알려줘"},
            {"role": "assistant", "content": "Bridge 네트워크는..."},
        ]
    }
    prompt = build_prompt(parsed, concepts=["Docker", "React"], projects=["theta-todo"])
    assert "Docker" in prompt
    assert "React" in prompt
    assert "theta-todo" in prompt
    assert "Docker 네트워킹 알려줘" in prompt


def test_build_prompt_empty_concepts():
    """Prompt works with no existing concepts."""
    parsed = {"messages": [{"role": "user", "content": "hello"}]}
    prompt = build_prompt(parsed, concepts=[], projects=[])
    assert "(없음)" in prompt


def test_truncate_messages_short_conversation():
    """Short conversations are not truncated."""
    messages = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    result = truncate_messages(messages, max_chars=50000)
    assert len(result) == 10


def test_truncate_messages_long_conversation():
    """Long conversations use sandwich strategy: first 15 + last 85."""
    messages = [{"role": "user", "content": "x" * 600} for i in range(200)]
    result = truncate_messages(messages, max_chars=50000)
    # Should have first 15 + separator + last 85 = 101 items
    assert len(result) == 101
    assert result[15]["role"] == "system"  # separator marker
    assert "[... 중간 생략" in result[15]["content"]


def test_json_schema_is_valid():
    """Schema is valid JSON and has required fields."""
    schema = build_json_schema()
    parsed = json.loads(schema) if isinstance(schema, str) else schema
    assert "properties" in parsed
    assert "summary" in parsed["properties"]
    assert "concepts" in parsed["properties"]
    assert "tags" in parsed["properties"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/analyzer.py
import json
import logging
import subprocess
import time

logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "1~3문장 대화 요약"},
        "decisions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "핵심 결정사항 목록",
        },
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "existing_match": {"type": ["string", "null"]},
                    "insight": {"type": ["string", "null"]},
                },
                "required": ["name", "existing_match"],
            },
        },
        "concept_relations": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
        "title_slug": {"type": "string", "description": "영문 slug for filename"},
    },
    "required": ["summary", "concepts", "tags", "projects", "title_slug"],
}


def build_json_schema() -> dict:
    """Return the JSON schema for analyzer output."""
    return ANALYSIS_SCHEMA


def build_prompt(parsed: dict, concepts: list[str], projects: list[str]) -> str:
    """Build the analysis prompt with conversation and existing vault context."""
    concept_list = ", ".join(concepts) if concepts else "(없음)"
    project_list = ", ".join(projects) if projects else "(없음)"

    conversation = ""
    for msg in parsed["messages"]:
        role = "사용자" if msg["role"] == "user" else "AI"
        conversation += f"[{role}]: {msg['content']}\n\n"

    return f"""다음 AI 대화를 분석해줘.

[기존 개념 목록]: {concept_list}
[기존 프로젝트 목록]: {project_list}

규칙:
- existing_match: 기존 개념 목록에 같은 개념이 있으면 해당 이름. 없으면 null.
- description: 새 개념(existing_match가 null)이면 한 줄 설명. 기존 개념이면 null.
- insight: 이 대화에서 해당 개념에 대해 새로 알게 된 사실이 있으면 한 줄. 없으면 null.
- concept_relations: 이 대화에서 관련 있는 개념 쌍 목록.
- title_slug: 대화 주제를 영문 kebab-case로 (예: docker-networking, react-hooks-guide).
- tags: 소문자 영문 태그.
- projects: 기존 프로젝트 목록에서 관련된 것만. 새 프로젝트면 이름 추가.

[대화 내용]
{conversation}"""


def truncate_messages(messages: list[dict], max_chars: int = 50000) -> list[dict]:
    """Apply sandwich truncation if total text exceeds max_chars."""
    total = sum(len(m["content"]) for m in messages)
    if total <= max_chars:
        return messages

    head_count = 15
    tail_count = 85
    if len(messages) <= head_count + tail_count:
        return messages

    head = messages[:head_count]
    tail = messages[-tail_count:]
    skipped = len(messages) - head_count - tail_count
    separator = {"role": "system", "content": f"[... 중간 {skipped}개 메시지 생략 ...]"}
    return head + [separator] + tail


def analyze(parsed: dict, concepts: list[str], projects: list[str], max_retries: int = 3) -> dict:
    """Run claude -p to analyze a conversation. Returns parsed JSON result."""
    truncated = truncate_messages(parsed["messages"], max_chars=50000)
    truncated_parsed = {**parsed, "messages": truncated}
    prompt = build_prompt(truncated_parsed, concepts, projects)
    schema_json = json.dumps(ANALYSIS_SCHEMA)

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--model", "sonnet",
                    "--output-format", "json",
                    "--json-schema", schema_json,
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(f"claude -p failed (attempt {attempt + 1}): {result.stderr[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue

            output = json.loads(result.stdout)
            # claude --output-format json wraps in {"result": ..., "cost_usd": ...}
            if "result" in output and isinstance(output["result"], str):
                return json.loads(output["result"])
            elif "result" in output and isinstance(output["result"], dict):
                return output["result"]
            return output

        except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Analyzer error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    raise RuntimeError(f"Analyzer failed after {max_retries} attempts")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_analyzer.py -v`
Expected: 5 passed (only unit tests — `analyze()` is not tested here as it calls `claude -p`)

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/analyzer.py tests/test_analyzer.py
git commit -m "feat: add analyzer module with prompt construction and claude -p invocation"
```

---

## Task 8: Generator Module

**Files:**
- Create: `src/obsidian_brain/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generator.py
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
    """Generate a conversation markdown file."""
    conv_dir = tmp_path / "Conversations" / "2026-03"
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
    """Generate a new concept document."""
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
    """Update existing concept doc: add conversation to frontmatter."""
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


def test_resolve_slug_conflict(tmp_path):
    """Add -2 suffix when slug already exists."""
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)
    (conv_dir / "2026-03-25-docker-networking.md").write_text("existing")
    result = resolve_slug_conflict(conv_dir, "2026-03-25-docker-networking")
    assert result == "2026-03-25-docker-networking-2"


def test_update_project_doc(tmp_path):
    """Update existing project doc: add conversation and decisions."""
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


def test_generate_project_doc(tmp_path):
    """Generate a new project document."""
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/generator.py
from pathlib import Path

import frontmatter


def resolve_slug_conflict(directory: Path, slug: str) -> str:
    """If slug.md exists, return slug-2, slug-3, etc."""
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
    """Generate a conversation document in the vault."""
    year_month = date[:7]  # "2026-03"
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
    """Generate a new concept document."""
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
    """Update an existing concept doc: add conversation ref and optional insight."""
    post = frontmatter.load(doc_path)

    # Update frontmatter
    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add insight to body if provided (append at end of section for chronological order)
    if insight:
        insight_line = f"- ({date}) {insight}"
        if "## 인사이트" in post.content:
            # Find the next ## heading after 인사이트 section
            lines = post.content.split("\n")
            insert_idx = len(lines)  # default: end of file
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
    """Generate a new project document."""
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
    """Update an existing project doc: add conversation ref."""
    post = frontmatter.load(doc_path)

    convs = post.get("conversations", [])
    if conversation_slug not in convs:
        convs.append(conversation_slug)
    post["conversations"] = convs
    post["updated"] = date

    # Add to timeline
    timeline_entry = f"- [[{conversation_slug}]] — {summary}"
    if "## 대화 타임라인" in post.content:
        post.content = post.content.replace(
            "## 대화 타임라인",
            f"## 대화 타임라인\n{timeline_entry}",
        )

    # Add decisions
    if decisions:
        for d in decisions:
            if d not in post.content:
                if "## 핵심 결정사항" in post.content:
                    post.content = post.content.replace(
                        "## 핵심 결정사항",
                        f"## 핵심 결정사항\n- {d}",
                    )

    doc_path.write_text(frontmatter.dumps(post))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_generator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/generator.py tests/test_generator.py
git commit -m "feat: add generator module for Obsidian markdown creation and updates"
```

---

## Task 9: Pipeline Orchestrator

**Files:**
- Create: `src/obsidian_brain/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py
from pathlib import Path
from unittest.mock import patch
from obsidian_brain.pipeline import process_session


def test_process_session_skips_trivial(tmp_path):
    """Pipeline skips sessions with too few messages."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian-brain").mkdir()
    (vault / ".obsidian-brain" / ".processed").write_text("")
    (vault / "Concepts").mkdir()
    (vault / "Projects").mkdir()

    # Create a trivial transcript
    transcript = tmp_path / "trivial.jsonl"
    import json
    lines = [
        {"type": "user", "uuid": "u1", "message": {"content": "hi"}},
        {"type": "assistant", "uuid": "a1", "message": {"content": [{"type": "text", "text": "hello"}]}},
    ]
    with open(transcript, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    result = process_session(
        transcript_path=transcript,
        vault_path=vault,
        min_messages=3,
    )
    assert result is None  # skipped


def test_process_session_skips_already_processed(tmp_path):
    """Pipeline skips already-processed sessions."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian-brain").mkdir()
    (vault / ".obsidian-brain" / ".processed").write_text("trivial\n")
    (vault / "Concepts").mkdir()
    (vault / "Projects").mkdir()

    transcript = tmp_path / "trivial.jsonl"
    import json
    lines = [{"type": "user", "uuid": f"u{i}", "message": {"content": f"q{i}"}} for i in range(10)]
    lines += [{"type": "assistant", "uuid": f"a{i}", "message": {"content": [{"type": "text", "text": f"a{i}"}]}} for i in range(10)]
    with open(transcript, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    result = process_session(
        transcript_path=transcript,
        vault_path=vault,
        min_messages=3,
    )
    assert result is None  # skipped — already processed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/pipeline.py
import logging
from pathlib import Path

from .analyzer import analyze
from .config import load_config
from .filter import should_process
from .generator import (
    generate_concept_doc,
    generate_conversation_doc,
    generate_project_doc,
    update_concept_doc,
    update_project_doc,
)
from .parser import parse_transcript
from .vault import load_processed_ids, save_processed_id, scan_concepts, scan_projects

logger = logging.getLogger(__name__)


def process_session(
    transcript_path: Path,
    vault_path: Path,
    min_messages: int = 3,
    max_retries: int = 3,
) -> Path | None:
    """Process a single session transcript into Obsidian documents.

    Returns the conversation document path, or None if skipped.
    """
    config = load_config(vault_path)
    min_msg = min_messages or config["min_messages"]

    # Parse
    parsed = parse_transcript(transcript_path)
    logger.info(f"Parsed session {parsed['session_id']}: {len(parsed['messages'])} messages")

    # Filter
    processed_ids = load_processed_ids(vault_path)
    if not should_process(parsed, processed_ids, min_msg):
        logger.info(f"Skipping session {parsed['session_id']}")
        return None

    # Analyze
    concepts = scan_concepts(vault_path, config["folders"]["concepts"])
    projects = scan_projects(vault_path, config["folders"]["projects"])
    logger.info(f"Vault context: {len(concepts)} concepts, {len(projects)} projects")

    analysis = analyze(
        parsed,
        concepts=concepts,
        projects=projects,
        max_retries=config.get("max_retries", max_retries),
    )
    logger.info(f"Analysis complete: {analysis['title_slug']}")

    # Generate conversation doc
    conv_path = generate_conversation_doc(
        vault_path=vault_path,
        conv_folder=config["folders"]["conversations"],
        date=parsed["date"],
        session_id=parsed["session_id"],
        analysis=analysis,
    )
    conversation_slug = conv_path.stem
    logger.info(f"Created conversation: {conv_path}")

    # Generate/update concept docs
    concept_relations = {
        c["name"]: []
        for c in analysis.get("concepts", [])
    }
    for pair in analysis.get("concept_relations", []):
        if len(pair) == 2:
            for name in pair:
                if name in concept_relations:
                    other = pair[1] if pair[0] == name else pair[0]
                    concept_relations[name].append(other)

    for concept in analysis.get("concepts", []):
        concept_name = concept.get("existing_match") or concept["name"]
        concept_path = vault_path / config["folders"]["concepts"] / f"{concept_name}.md"

        related = concept_relations.get(concept["name"], [])

        if concept_path.exists():
            update_concept_doc(
                doc_path=concept_path,
                conversation_slug=conversation_slug,
                date=parsed["date"],
                insight=concept.get("insight"),
            )
            logger.info(f"Updated concept: {concept_name}")
        else:
            generate_concept_doc(
                vault_path=vault_path,
                concepts_folder=config["folders"]["concepts"],
                concept=concept,
                date=parsed["date"],
                conversation_slug=conversation_slug,
                related_concepts=related,
            )
            logger.info(f"Created concept: {concept_name}")

    # Generate/update project docs
    for project_name in analysis.get("projects", []):
        project_path = vault_path / config["folders"]["projects"] / f"{project_name}.md"
        if project_path.exists():
            update_project_doc(
                doc_path=project_path,
                conversation_slug=conversation_slug,
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
                conversation_slug=conversation_slug,
                summary=analysis["summary"],
                decisions=analysis.get("decisions"),
            )
            logger.info(f"Created project: {project_name}")

    # Record as processed
    save_processed_id(vault_path, parsed["session_id"])
    logger.info(f"Session {parsed['session_id']} processed successfully")

    return conv_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_pipeline.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator connecting all components"
```

---

## Task 10: Recovery Module

**Files:**
- Create: `src/obsidian_brain/recovery.py`
- Create: `tests/test_recovery.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_recovery.py
import json
import time
from pathlib import Path
from obsidian_brain.recovery import find_unprocessed_sessions
from obsidian_brain.parser import encode_cwd


def test_find_unprocessed_sessions(tmp_path):
    """Find transcript files not in .processed."""
    projects_dir = tmp_path / "encoded-dir"
    projects_dir.mkdir(parents=True)

    # Create transcript files
    (projects_dir / "session-1.jsonl").write_text('{"type":"user"}\n')
    (projects_dir / "session-2.jsonl").write_text('{"type":"user"}\n')

    processed = {"session-1"}
    sessions = find_unprocessed_sessions(
        projects_subdir=projects_dir,
        processed_ids=processed,
        max_age_days=30,
    )
    assert len(sessions) == 1
    assert sessions[0].stem == "session-2"


def test_find_unprocessed_ignores_old_sessions(tmp_path):
    """Sessions older than max_age_days are ignored."""
    projects_dir = tmp_path / "encoded-dir"
    projects_dir.mkdir(parents=True)

    old_file = projects_dir / "old-session.jsonl"
    old_file.write_text('{"type":"user"}\n')
    # Set mtime to 60 days ago
    old_time = time.time() - (60 * 86400)
    import os
    os.utime(old_file, (old_time, old_time))

    sessions = find_unprocessed_sessions(
        projects_subdir=projects_dir,
        processed_ids=set(),
        max_age_days=30,
    )
    assert len(sessions) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_recovery.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/recovery.py
import logging
import time
from pathlib import Path

from .parser import encode_cwd

logger = logging.getLogger(__name__)


def find_unprocessed_sessions(
    projects_subdir: Path,
    processed_ids: set[str],
    max_age_days: int = 30,
) -> list[Path]:
    """Find transcript files that haven't been processed yet.

    Args:
        projects_subdir: Direct path to ~/.claude/projects/{encoded_cwd}/
    """
    if not projects_subdir.exists():
        return []

    cutoff = time.time() - (max_age_days * 86400)
    unprocessed = []

    for f in projects_subdir.glob("*.jsonl"):
        if not f.is_file():
            continue
        session_id = f.stem
        if session_id in processed_ids:
            continue
        if f.stat().st_mtime < cutoff:
            continue
        unprocessed.append(f)

    # Sort oldest first
    unprocessed.sort(key=lambda f: f.stat().st_mtime)
    return unprocessed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_recovery.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/recovery.py tests/test_recovery.py
git commit -m "feat: add recovery module for finding unprocessed sessions"
```

---

## Task 11: CLI Entry Point

**Files:**
- Modify: `src/obsidian_brain/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import subprocess
import sys


def test_cli_help():
    """CLI shows help text."""
    result = subprocess.run(
        [sys.executable, "-m", "obsidian_brain", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "process" in result.stdout or "recover" in result.stdout


def test_cli_process_missing_args():
    """Process command requires --session-id and --vault-path."""
    result = subprocess.run(
        [sys.executable, "-m", "obsidian_brain", "process"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/obsidian_brain/__main__.py
import argparse
import logging
import sys
from pathlib import Path

from .lockfile import acquire_lock, release_lock
from .pipeline import process_session
from .parser import build_transcript_path
from .recovery import find_unprocessed_sessions
from .vault import load_processed_ids
from .config import load_config


def setup_logging(vault_path: Path) -> None:
    """Configure logging to file and stderr."""
    from datetime import date
    log_dir = vault_path / ".obsidian-brain" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date.today().isoformat()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr),
        ],
    )


def cmd_process(args) -> None:
    """Process a single session."""
    vault_path = Path(args.vault_path).expanduser().resolve()
    setup_logging(vault_path)
    logger = logging.getLogger(__name__)

    lock_path = vault_path / ".obsidian-brain" / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=60)
    if lock_fd is None:
        logger.warning("Could not acquire lock, another process is running")
        sys.exit(1)

    try:
        transcript = build_transcript_path(args.session_id, args.cwd)
        if not transcript.exists():
            logger.error(f"Transcript not found: {transcript}")
            sys.exit(1)

        result = process_session(
            transcript_path=transcript,
            vault_path=vault_path,
        )
        if result:
            logger.info(f"Created: {result}")
    except Exception as e:
        logger.exception(f"Failed to process session {args.session_id}: {e}")
        # Record failure
        failed_file = vault_path / ".obsidian-brain" / ".failed"
        with open(failed_file, "a") as f:
            from datetime import datetime
            f.write(f"{args.session_id}\t{e}\t{datetime.now().isoformat()}\n")
        sys.exit(1)
    finally:
        release_lock(lock_fd, lock_path)


def cmd_recover(args) -> None:
    """Find and process unprocessed sessions."""
    vault_path = Path(args.vault_path).expanduser().resolve()
    setup_logging(vault_path)
    logger = logging.getLogger(__name__)
    config = load_config(vault_path)

    lock_path = vault_path / ".obsidian-brain" / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=0)
    if lock_fd is None:
        logger.info("Another process is running, skipping recovery")
        return

    try:
        processed = load_processed_ids(vault_path)
        claude_dir = Path.home() / ".claude"

        # Scan all project directories
        projects_dir = claude_dir / "projects"
        if not projects_dir.exists():
            return

        total_processed = 0
        for encoded_dir in projects_dir.iterdir():
            if not encoded_dir.is_dir():
                continue

            sessions = find_unprocessed_sessions(
                projects_subdir=encoded_dir,
                processed_ids=processed,
                max_age_days=config.get("processed_retention_days", 30),
            )

            for transcript in sessions:
                try:
                    result = process_session(
                        transcript_path=transcript,
                        vault_path=vault_path,
                    )
                    if result:
                        total_processed += 1
                        logger.info(f"Recovered: {result}")
                except Exception as e:
                    logger.warning(f"Recovery failed for {transcript.stem}: {e}")

        logger.info(f"Recovery complete: {total_processed} sessions processed")
    finally:
        release_lock(lock_fd, lock_path)


def main():
    parser = argparse.ArgumentParser(
        prog="obsidian-brain",
        description="Auto-generate Obsidian docs from AI conversations",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # process command
    p_process = subparsers.add_parser("process", help="Process a single session")
    p_process.add_argument("--session-id", required=True)
    p_process.add_argument("--cwd", required=True)
    p_process.add_argument("--vault-path", required=True)
    p_process.set_defaults(func=cmd_process)

    # recover command
    p_recover = subparsers.add_parser("recover", help="Find and process unprocessed sessions")
    p_recover.add_argument("--vault-path", required=True)
    p_recover.set_defaults(func=cmd_recover)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_brain/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point with process and recover commands"
```

---

## Task 12: Integration Test with Real Transcript

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""Integration test using a real transcript file (mocked claude -p)."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from obsidian_brain.pipeline import process_session

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_analyze(parsed, concepts, projects, max_retries=3):
    """Return a realistic analysis result without calling claude -p."""
    return {
        "summary": "Docker 네트워킹의 bridge와 host 차이를 배웠다",
        "decisions": [],
        "concepts": [
            {
                "name": "Docker",
                "description": None,
                "aliases": [],
                "existing_match": "Docker",
                "insight": "bridge는 격리, host는 공유",
            },
            {
                "name": "컨테이너 네트워킹",
                "description": "컨테이너 간 통신을 관리하는 기술",
                "aliases": ["container networking"],
                "existing_match": None,
                "insight": None,
            },
        ],
        "concept_relations": [["Docker", "컨테이너 네트워킹"]],
        "tags": ["docker", "networking"],
        "projects": [],
        "title_slug": "docker-networking",
    }


@patch("obsidian_brain.pipeline.analyze", side_effect=_mock_analyze)
def test_full_pipeline_creates_documents(mock_analyze, tmp_path):
    """Full pipeline: parse → filter → analyze → generate."""
    # Set up vault
    vault = tmp_path / "vault"
    vault.mkdir()
    brain_dir = vault / ".obsidian-brain"
    brain_dir.mkdir()
    (brain_dir / ".processed").write_text("")

    # Create existing concept
    concepts_dir = vault / "Concepts"
    concepts_dir.mkdir()
    docker_doc = concepts_dir / "Docker.md"
    docker_doc.write_text("""---
type: concept
created: 2026-03-20
updated: 2026-03-20
aliases: []
conversations: []
---

# Docker

컨테이너 플랫폼.

## 인사이트

## 관련 개념
""")

    (vault / "Projects").mkdir()

    result = process_session(
        transcript_path=FIXTURES / "sample_transcript.jsonl",
        vault_path=vault,
    )

    # Conversation doc created
    assert result is not None
    assert result.exists()
    assert "docker-networking" in result.name

    # Existing concept updated
    docker_content = docker_doc.read_text()
    assert "bridge는 격리" in docker_content

    # New concept created
    new_concept = concepts_dir / "컨테이너 네트워킹.md"
    assert new_concept.exists()

    # Session marked as processed
    processed = (brain_dir / ".processed").read_text()
    assert "sample_transcript" in processed
```

- [ ] **Step 2: Run test**

Run: `cd /path/to/obsidian-brain && uv run pytest tests/test_integration.py -v`
Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test with mocked analyzer"
```

---

## Task 13: Hook Configuration & README

**Files:**
- Create: `README.md` (minimal install instructions only)
- Create: `scripts/install-hooks.sh`

- [ ] **Step 1: Create hook installation script**

```bash
#!/usr/bin/env bash
# scripts/install-hooks.sh
# Installs Claude Code hooks for obsidian-brain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Obsidian Brain Hook Installer"
echo "=============================="
echo ""

# Ask for vault path
read -p "Obsidian Vault 경로를 입력하세요 (예: ~/ObsidianVault): " VAULT_PATH
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

if [ ! -d "$VAULT_PATH" ]; then
    echo "Error: $VAULT_PATH 디렉토리가 존재하지 않습니다."
    exit 1
fi

# Create .obsidian-brain directory
mkdir -p "$VAULT_PATH/.obsidian-brain/logs"

# Create default config if not exists
if [ ! -f "$VAULT_PATH/.obsidian-brain/config.yaml" ]; then
    cat > "$VAULT_PATH/.obsidian-brain/config.yaml" << EOF
vault_path: $VAULT_PATH
min_messages: 3
max_transcript_chars: 50000
max_retries: 3
processed_retention_days: 30
slug_language: en
folders:
  conversations: Conversations
  concepts: Concepts
  projects: Projects
EOF
    echo "Created config: $VAULT_PATH/.obsidian-brain/config.yaml"
fi

# Create vault directories
mkdir -p "$VAULT_PATH/Conversations"
mkdir -p "$VAULT_PATH/Concepts"
mkdir -p "$VAULT_PATH/Projects"

echo ""
echo "설치 완료!"
echo ""
echo "Claude Code hooks를 설정하려면 ~/.claude/settings.json에 아래를 추가하세요:"
echo ""
cat << EOF
{
  "hooks": {
    "SessionEnd": [
      {
        "command": "uv run --project $PROJECT_DIR python -m obsidian_brain process --session-id \$SESSION_ID --cwd \$CWD --vault-path $VAULT_PATH &",
        "timeout": 5000
      }
    ],
    "SessionStart": [
      {
        "command": "uv run --project $PROJECT_DIR python -m obsidian_brain recover --vault-path $VAULT_PATH &",
        "timeout": 5000
      }
    ]
  }
}
EOF
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x scripts/install-hooks.sh`

- [ ] **Step 3: Run all tests to verify nothing broke**

Run: `cd /path/to/obsidian-brain && uv run pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add scripts/install-hooks.sh
git commit -m "feat: add hook installation script"
```

---

## Task 14: End-to-End Manual Test

This task verifies the full system works with a real Claude Code session.

- [ ] **Step 1: Run install script**

Run: `cd /path/to/obsidian-brain && bash scripts/install-hooks.sh`
Enter vault path when prompted.

- [ ] **Step 2: Add hooks to Claude Code settings**

Copy the output from the install script into `~/.claude/settings.json` (merge with existing hooks if any).

- [ ] **Step 3: Start a test Claude Code session**

Start a Claude Code session, have a short conversation (4+ exchanges), then exit.

- [ ] **Step 4: Verify documents were created**

Check the vault:
- `Conversations/` should have a new `.md` file
- `Concepts/` should have concept documents
- `.obsidian-brain/logs/` should have today's log
- `.obsidian-brain/.processed` should have the session ID

- [ ] **Step 5: Open Obsidian and verify**

- Documents appear in file explorer
- `[[links]]` work and connect documents
- Graph view shows connections

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: obsidian-brain Phase 1 complete"
```
