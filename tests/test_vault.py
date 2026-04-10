from pathlib import Path
from obsidian_brain.vault import scan_projects, load_processed_ids, save_processed_id, rotate_processed

SAMPLE_VAULT = Path(__file__).parent / "fixtures" / "sample_vault"


def test_scan_projects():
    projects = scan_projects(SAMPLE_VAULT, "Projects")
    assert "theta-todo" in projects


def test_load_processed_ids():
    ids = load_processed_ids(SAMPLE_VAULT)
    assert "old-session-id-1" in ids
    assert "old-session-id-2" in ids


def test_load_processed_ids_missing_file(tmp_path):
    brain_dir = tmp_path / ".obsidian-brain"
    brain_dir.mkdir()
    ids = load_processed_ids(tmp_path)
    assert ids == set()


def test_save_processed_id(tmp_path):
    brain_dir = tmp_path / ".obsidian-brain"
    brain_dir.mkdir()
    save_processed_id(tmp_path, "new-session-123")
    ids = load_processed_ids(tmp_path)
    assert "new-session-123" in ids


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
