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


def test_process_session_skips_already_processed(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian-brain").mkdir()
    (vault / ".obsidian-brain" / ".processed").write_text("trivial\t2026-03-25T10:00:00\n")
    (vault / "Experiences").mkdir()
    (vault / "Projects").mkdir()

    transcript = tmp_path / "trivial.jsonl"
    lines = [{"type": "user", "uuid": f"u{i}", "message": {"content": f"q{i}"}} for i in range(10)]
    lines += [{"type": "assistant", "uuid": f"a{i}", "message": {"content": [{"type": "text", "text": f"a{i}"}]}} for i in range(10)]
    with open(transcript, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    result = process_session(transcript_path=transcript, vault_path=vault, min_messages=3)
    assert result is None


def test_process_session_creates_experience_notes(tmp_path, monkeypatch):
    import obsidian_brain.pipeline as pipeline_mod
    from obsidian_brain.pipeline import process_session

    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "Experiences").mkdir()
    (vault_path / "Conversations" / "2026-04").mkdir(parents=True)
    (vault_path / ".obsidian-brain").mkdir()

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

    monkeypatch.setattr(pipeline_mod, "analyze", lambda *args, **kwargs: mock_analysis)
    monkeypatch.setattr(pipeline_mod, "is_similar_conversation", lambda **kwargs: False)
    monkeypatch.setattr(pipeline_mod, "should_process", lambda parsed, processed_ids, min_msg: True)
    monkeypatch.setattr(pipeline_mod, "load_processed_ids", lambda vault_path: set())
    monkeypatch.setattr(pipeline_mod, "save_processed_id", lambda vault_path, session_id: None)

    # Create a mock transcript file
    transcript_path = tmp_path / "transcript.jsonl"
    messages = [
        {"type": "message", "role": "user", "content": "Django admin에서 LogEntry 조회가 느려요"},
        {"type": "message", "role": "assistant", "content": "QuerySet lazy evaluation 때문입니다"},
    ] * 3
    transcript_path.write_text("\n".join(json.dumps(m) for m in messages))

    # Mock parse_transcript to return valid parsed data
    monkeypatch.setattr(pipeline_mod, "parse_transcript", lambda path: {
        "session_id": "test-session-123",
        "date": "2026-04-01",
        "messages": [
            {"role": "user", "content": "Django admin에서 LogEntry 조회가 느려요"},
            {"role": "assistant", "content": "QuerySet lazy evaluation 때문입니다"},
        ] * 3,
    })

    # Mock load_config
    monkeypatch.setattr(pipeline_mod, "load_config", lambda path: {
        "min_messages": 3,
        "model": "sonnet",
        "folders": {
            "conversations": "Conversations",
            "experiences": "Experiences",
            "projects": "Projects",
        },
    })

    result = process_session(transcript_path, vault_path)

    assert result is not None
    # Experience note created
    exp_files = list((vault_path / "Experiences").glob("*.md"))
    assert len(exp_files) == 1
    assert "QuerySet" in exp_files[0].stem
