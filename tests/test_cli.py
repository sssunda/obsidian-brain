import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "obsidian_brain", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "process" in result.stdout or "recover" in result.stdout


def test_cli_process_missing_args():
    result = subprocess.run(
        [sys.executable, "-m", "obsidian_brain", "process"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_read_last_result(tmp_path):
    import json
    from obsidian_brain.__main__ import _read_last_result

    state_dir = tmp_path / ".obsidian-brain"
    state_dir.mkdir()

    result_data = {
        "conversation": "2026-04-01-django-admin-logentry",
        "experiences": ["Django QuerySet 평가 시점 함정"],
    }
    (state_dir / ".last_result").write_text(json.dumps(result_data, ensure_ascii=False))

    loaded = _read_last_result(tmp_path)
    assert loaded["experiences"] == ["Django QuerySet 평가 시점 함정"]


def test_save_feedback(tmp_path):
    import json
    from obsidian_brain.__main__ import _save_feedback

    state_dir = tmp_path / ".obsidian-brain"
    state_dir.mkdir()

    _save_feedback(
        vault_path=tmp_path,
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
