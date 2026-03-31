from datetime import datetime, timedelta
from pathlib import Path

from obsidian_brain.generator import sanitize_filename
from obsidian_brain.vault import rotate_processed


class TestSanitizeFilename:
    def test_normal_name(self):
        assert sanitize_filename("Docker Networking") == "Docker Networking"

    def test_slashes(self):
        assert sanitize_filename("API/REST") == "API-REST"

    def test_colons(self):
        assert sanitize_filename("Step 1: Setup") == "Step 1- Setup"

    def test_backslash(self):
        assert sanitize_filename("path\\to\\file") == "path-to-file"

    def test_quotes(self):
        assert sanitize_filename('He said "hello"') == "He said -hello-"

    def test_question_mark(self):
        assert sanitize_filename("Why?") == "Why-"

    def test_pipe(self):
        assert sanitize_filename("A | B") == "A - B"

    def test_asterisk(self):
        assert sanitize_filename("glob*pattern") == "glob-pattern"

    def test_angle_brackets(self):
        assert sanitize_filename("<input>") == "-input-"

    def test_dots_stripped(self):
        assert sanitize_filename("..hidden") == "hidden"

    def test_spaces_stripped(self):
        assert sanitize_filename("  padded  ") == "padded"

    def test_multiple_special(self):
        assert sanitize_filename('a/b:c"d?e') == "a-b-c-d-e"

    def test_korean(self):
        assert sanitize_filename("리드 스코어링") == "리드 스코어링"


class TestRotateProcessed:
    def test_removes_old_entries(self, tmp_path):
        ob_dir = tmp_path / ".obsidian-brain"
        ob_dir.mkdir()
        processed = ob_dir / ".processed"

        old_ts = (datetime.now() - timedelta(days=60)).isoformat()
        recent_ts = (datetime.now() - timedelta(days=5)).isoformat()
        processed.write_text(f"old-session\t{old_ts}\nrecent-session\t{recent_ts}\n")

        rotate_processed(tmp_path, retention_days=30)

        content = processed.read_text()
        assert "old-session" not in content
        assert "recent-session" in content

    def test_keeps_all_recent(self, tmp_path):
        ob_dir = tmp_path / ".obsidian-brain"
        ob_dir.mkdir()
        processed = ob_dir / ".processed"

        ts = datetime.now().isoformat()
        processed.write_text(f"s1\t{ts}\ns2\t{ts}\n")

        rotate_processed(tmp_path, retention_days=30)

        content = processed.read_text()
        assert "s1" in content
        assert "s2" in content

    def test_handles_malformed_lines(self, tmp_path):
        ob_dir = tmp_path / ".obsidian-brain"
        ob_dir.mkdir()
        processed = ob_dir / ".processed"

        ts = datetime.now().isoformat()
        processed.write_text(f"no-tab-line\ngood-session\t{ts}\n")

        rotate_processed(tmp_path, retention_days=30)

        content = processed.read_text()
        assert "no-tab-line" in content  # Kept because can't parse date
        assert "good-session" in content

    def test_empty_file(self, tmp_path):
        ob_dir = tmp_path / ".obsidian-brain"
        ob_dir.mkdir()
        processed = ob_dir / ".processed"
        processed.write_text("")

        rotate_processed(tmp_path, retention_days=30)
        assert processed.read_text() == ""

    def test_no_file(self, tmp_path):
        ob_dir = tmp_path / ".obsidian-brain"
        ob_dir.mkdir()
        rotate_processed(tmp_path, retention_days=30)  # Should not raise
