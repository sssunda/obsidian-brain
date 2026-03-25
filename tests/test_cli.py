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
