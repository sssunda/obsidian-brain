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
