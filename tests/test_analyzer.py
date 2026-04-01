import json
from obsidian_brain.analyzer import build_prompt, build_json_schema, truncate_messages


def test_analysis_schema_has_experiences():
    from obsidian_brain.analyzer import ANALYSIS_SCHEMA
    props = ANALYSIS_SCHEMA["properties"]
    assert "experiences" in props
    assert "concepts" not in props

    exp_items = props["experiences"]["items"]["properties"]
    assert "title" in exp_items
    assert "experience_type" in exp_items
    assert "sections" in exp_items

    # experience_type must be enum
    assert set(exp_items["experience_type"]["enum"]) == {
        "problem-solving", "discovery", "troubleshooting"
    }


def test_build_prompt_contains_experience_instructions():
    from obsidian_brain.analyzer import build_prompt

    parsed = {
        "messages": [
            {"role": "user", "content": "test message"}
        ],
        "date": "2026-04-01",
    }
    prompt = build_prompt(parsed, projects=["wishos"])
    assert "경험" in prompt or "experience" in prompt.lower()
    assert "개념" not in prompt  # no concept instructions
    assert "problem-solving" in prompt
    assert "discovery" in prompt
    assert "troubleshooting" in prompt


def test_build_prompt_includes_projects():
    parsed = {
        "messages": [
            {"role": "user", "content": "Docker 네트워킹 알려줘"},
            {"role": "assistant", "content": "Bridge 네트워크는..."},
        ],
        "date": "2026-04-01",
    }
    prompt = build_prompt(parsed, projects=["pomodoro-todo"])
    assert "pomodoro-todo" in prompt
    assert "Docker 네트워킹 알려줘" in prompt


def test_truncate_messages_short_conversation():
    messages = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    result = truncate_messages(messages, max_chars=50000)
    assert len(result) == 10


def test_truncate_messages_long_conversation():
    messages = [{"role": "user", "content": "x" * 600} for i in range(200)]
    result = truncate_messages(messages, max_chars=50000)
    assert len(result) == 101  # 15 head + 1 separator + 85 tail
    assert result[15]["role"] == "system"
    assert "[... 중간" in result[15]["content"]


def test_json_schema_is_valid():
    schema = build_json_schema()
    parsed = json.loads(schema) if isinstance(schema, str) else schema
    assert "properties" in parsed
    assert "summary" in parsed["properties"]
    assert "experiences" in parsed["properties"]
    assert "tags" in parsed["properties"]
