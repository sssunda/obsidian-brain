import json
from obsidian_brain.analyzer import build_prompt, build_json_schema, truncate_messages, ANALYSIS_SCHEMA


def test_schema_has_daily_entries():
    props = ANALYSIS_SCHEMA["properties"]
    assert "daily_entries" in props
    entry_props = props["daily_entries"]["items"]["properties"]
    assert "project" in entry_props
    assert "bullets" in entry_props


def test_schema_still_has_experiences():
    props = ANALYSIS_SCHEMA["properties"]
    assert "experiences" in props
    exp_items = props["experiences"]["items"]["properties"]
    assert "title" in exp_items
    assert "experience_type" in exp_items
    assert "sections" in exp_items


def test_schema_required_fields():
    required = ANALYSIS_SCHEMA["required"]
    assert "summary" in required
    assert "daily_entries" in required
    assert "experiences" in required
    assert "decisions" in required
    assert "tags" in required


def test_prompt_includes_project_descriptions():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    projects_config = {
        "wishket": {"aliases": ["backend"], "description": "위시켓 플랫폼"},
        "daeun": {"aliases": ["obsidian-brain"], "description": "개인 프로젝트"},
    }
    prompt = build_prompt(parsed, projects_config=projects_config)
    assert "wishket" in prompt
    assert "위시켓 플랫폼" in prompt
    assert "backend" in prompt
    assert "daeun" in prompt


def test_prompt_includes_existing_experiences():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    existing_experiences = [
        "Django QuerySet 평가 시점 함정",
        "UUID PK 전환이 전체 스택을 깨뜨림",
    ]
    prompt = build_prompt(parsed, existing_experiences=existing_experiences)
    assert "Django QuerySet 평가 시점 함정" in prompt
    assert "UUID PK 전환이 전체 스택을 깨뜨림" in prompt


def test_prompt_no_experiences_section_when_empty():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    prompt = build_prompt(parsed, existing_experiences=[])
    assert "기존 경험 노트:" not in prompt


def test_prompt_daily_entries_instructions():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    projects_config = {
        "wishket": {"aliases": [], "description": "위시켓"},
    }
    prompt = build_prompt(parsed, projects_config=projects_config)
    assert "daily_entries" in prompt


def test_prompt_includes_about():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    prompt = build_prompt(parsed, about="백엔드 개발자, Django 주력")
    assert "백엔드 개발자" in prompt


def test_prompt_no_about_when_empty():
    parsed = {
        "messages": [{"role": "user", "content": "test"}],
        "date": "2026-04-09",
    }
    prompt = build_prompt(parsed, about="")
    assert "사용자:" not in prompt


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
