import json
from obsidian_brain.analyzer import build_prompt, build_json_schema, truncate_messages


def test_build_prompt_includes_concepts_and_projects():
    parsed = {
        "messages": [
            {"role": "user", "content": "Docker 네트워킹 알려줘"},
            {"role": "assistant", "content": "Bridge 네트워크는..."},
        ]
    }
    prompt = build_prompt(parsed, concepts=["Docker", "React"], projects=["pomodoro-todo"])
    assert "Docker" in prompt
    assert "React" in prompt
    assert "pomodoro-todo" in prompt
    assert "Docker 네트워킹 알려줘" in prompt


def test_build_prompt_empty_concepts():
    parsed = {"messages": [{"role": "user", "content": "hello"}]}
    prompt = build_prompt(parsed, concepts=[], projects=[])
    assert "(없음)" in prompt


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
    assert "concepts" in parsed["properties"]
    assert "tags" in parsed["properties"]
