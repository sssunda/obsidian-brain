from pathlib import Path
from obsidian_brain.parser import parse_transcript, encode_cwd, build_transcript_path

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_transcript_extracts_user_and_assistant():
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    messages = result["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]


def test_parse_transcript_excludes_thinking_and_tool_use():
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    first_assistant = result["messages"][1]
    assert "docker network ls" not in first_assistant["content"]
    assert "Docker 네트워킹은" in first_assistant["content"]


def test_parse_transcript_user_content_is_string():
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    first_user = result["messages"][0]
    assert first_user["content"] == "Docker 네트워킹에 대해 알려줘"


def test_parse_transcript_metadata():
    result = parse_transcript(FIXTURES / "sample_transcript.jsonl")
    assert result["source"] == "claude-code"
    assert "date" in result


def test_encode_cwd():
    assert encode_cwd("/path/to/work") == "-path-to-work"
    assert encode_cwd("/") == "-"


def test_build_transcript_path():
    path = build_transcript_path("abc123", "/path/to/work")
    expected = Path.home() / ".claude" / "projects" / "-path-to-work" / "abc123.jsonl"
    assert path == expected
