import os
import time
from pathlib import Path
from obsidian_brain.recovery import find_unprocessed_sessions


def test_find_unprocessed_sessions(tmp_path):
    projects_dir = tmp_path / "encoded-dir"
    projects_dir.mkdir(parents=True)
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
    projects_dir = tmp_path / "encoded-dir"
    projects_dir.mkdir(parents=True)

    old_file = projects_dir / "old-session.jsonl"
    old_file.write_text('{"type":"user"}\n')
    old_time = time.time() - (60 * 86400)
    os.utime(old_file, (old_time, old_time))

    sessions = find_unprocessed_sessions(
        projects_subdir=projects_dir,
        processed_ids=set(),
        max_age_days=30,
    )
    assert len(sessions) == 0
