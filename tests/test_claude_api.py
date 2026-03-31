import json
from unittest.mock import MagicMock, patch

import pytest

from obsidian_brain.claude_api import _extract_result, call_claude, ensure_claude_available


SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}


def test_ensure_claude_available_found():
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        ensure_claude_available()  # Should not raise


def test_ensure_claude_available_missing():
    with patch("shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError, match="claude CLI not found"):
            ensure_claude_available()


class TestExtractResult:
    def test_structured_output_dict(self):
        output = {"structured_output": {"summary": "test"}}
        result = _extract_result(output, SAMPLE_SCHEMA)
        assert result == {"summary": "test"}

    def test_structured_output_str(self):
        output = {"structured_output": json.dumps({"summary": "test"})}
        result = _extract_result(output, SAMPLE_SCHEMA)
        assert result == {"summary": "test"}

    def test_result_dict(self):
        output = {"result": {"summary": "test"}}
        result = _extract_result(output, SAMPLE_SCHEMA)
        assert result == {"summary": "test"}

    def test_result_str(self):
        output = {"result": json.dumps({"summary": "test"})}
        result = _extract_result(output, SAMPLE_SCHEMA)
        assert result == {"summary": "test"}

    def test_direct_output(self):
        output = {"summary": "test"}
        result = _extract_result(output, SAMPLE_SCHEMA)
        assert result == {"summary": "test"}

    def test_missing_required_keys(self):
        output = {"structured_output": {"tags": []}}
        with pytest.raises(ValueError, match="missing required keys"):
            _extract_result(output, SAMPLE_SCHEMA)


class TestCallClaude:
    def _mock_run(self, stdout_dict, returncode=0):
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = json.dumps(stdout_dict)
        mock_result.stderr = ""
        return mock_result

    @patch("obsidian_brain.claude_api.ensure_claude_available")
    @patch("subprocess.run")
    def test_success(self, mock_run, mock_ensure):
        mock_run.return_value = self._mock_run({"structured_output": {"summary": "ok"}})
        result = call_claude("prompt", SAMPLE_SCHEMA)
        assert result == {"summary": "ok"}

    @patch("obsidian_brain.claude_api.ensure_claude_available")
    @patch("subprocess.run")
    def test_retry_on_failure(self, mock_run, mock_ensure):
        fail = self._mock_run({}, returncode=1)
        success = self._mock_run({"structured_output": {"summary": "ok"}})
        mock_run.side_effect = [fail, success]
        result = call_claude("prompt", SAMPLE_SCHEMA, max_retries=2)
        assert result == {"summary": "ok"}
        assert mock_run.call_count == 2

    @patch("obsidian_brain.claude_api.ensure_claude_available")
    @patch("subprocess.run")
    def test_all_retries_fail(self, mock_run, mock_ensure):
        mock_run.return_value = self._mock_run({}, returncode=1)
        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            call_claude("prompt", SAMPLE_SCHEMA, max_retries=2)

    @patch("obsidian_brain.claude_api.ensure_claude_available")
    @patch("subprocess.run")
    def test_timeout_retry(self, mock_run, mock_ensure):
        import subprocess as sp
        mock_run.side_effect = [
            sp.TimeoutExpired("claude", 120),
            self._mock_run({"structured_output": {"summary": "ok"}}),
        ]
        result = call_claude("prompt", SAMPLE_SCHEMA, max_retries=2)
        assert result == {"summary": "ok"}

    @patch("obsidian_brain.claude_api.ensure_claude_available")
    @patch("subprocess.run")
    def test_invalid_json_retry(self, mock_run, mock_ensure):
        bad = MagicMock()
        bad.returncode = 0
        bad.stdout = "not json"
        good = self._mock_run({"structured_output": {"summary": "ok"}})
        mock_run.side_effect = [bad, good]
        result = call_claude("prompt", SAMPLE_SCHEMA, max_retries=2)
        assert result == {"summary": "ok"}
