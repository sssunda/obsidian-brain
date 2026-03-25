import json
from pathlib import Path
from obsidian_brain.pipeline import process_session


def test_process_session_skips_trivial(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian-brain").mkdir()
    (vault / ".obsidian-brain" / ".processed").write_text("")
    (vault / "Concepts").mkdir()
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
    (vault / "Concepts").mkdir()
    (vault / "Projects").mkdir()

    transcript = tmp_path / "trivial.jsonl"
    lines = [{"type": "user", "uuid": f"u{i}", "message": {"content": f"q{i}"}} for i in range(10)]
    lines += [{"type": "assistant", "uuid": f"a{i}", "message": {"content": [{"type": "text", "text": f"a{i}"}]}} for i in range(10)]
    with open(transcript, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    result = process_session(transcript_path=transcript, vault_path=vault, min_messages=3)
    assert result is None
