from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import frontmatter

from obsidian_brain.digest import (
    build_digest_prompt,
    collect_recent_conversations,
    mark_digest_done,
    should_run_digest,
    write_digest,
)


def test_should_run_digest_no_marker(tmp_path):
    ob_dir = tmp_path / ".obsidian-brain"
    ob_dir.mkdir()
    assert should_run_digest(tmp_path) is True


def test_should_run_digest_today_already_ran(tmp_path):
    ob_dir = tmp_path / ".obsidian-brain"
    ob_dir.mkdir()
    marker = ob_dir / ".last_digest"
    marker.write_text(date.today().isoformat())
    assert should_run_digest(tmp_path) is False


def test_should_run_digest_ran_yesterday(tmp_path):
    ob_dir = tmp_path / ".obsidian-brain"
    ob_dir.mkdir()
    marker = ob_dir / ".last_digest"
    marker.write_text((date.today() - timedelta(days=1)).isoformat())
    assert should_run_digest(tmp_path) is True


def test_mark_digest_done(tmp_path):
    ob_dir = tmp_path / ".obsidian-brain"
    ob_dir.mkdir()
    mark_digest_done(tmp_path)
    marker = ob_dir / ".last_digest"
    assert marker.read_text().strip() == date.today().isoformat()


def test_collect_recent_conversations(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)

    today = date.today().isoformat()
    post = frontmatter.Post(content="## 요약\n테스트 대화", date=today)
    (conv_dir / "test-conv.md").write_text(frontmatter.dumps(post))

    old_date = (date.today() - timedelta(days=30)).isoformat()
    old_post = frontmatter.Post(content="## 요약\n오래된 대화", date=old_date)
    (conv_dir / "old-conv.md").write_text(frontmatter.dumps(old_post))

    results = collect_recent_conversations(tmp_path, "Conversations", days=7)
    assert len(results) == 1
    assert results[0]["date"] == today


def test_collect_recent_conversations_empty_dir(tmp_path):
    results = collect_recent_conversations(tmp_path, "Conversations")
    assert results == []


def test_build_digest_prompt_without_existing():
    conversations = [
        {"file": "test.md", "date": "2026-03-31", "content": "## 요약\n테스트"}
    ]
    prompt = build_digest_prompt(conversations, "")
    assert "test.md" in prompt
    assert "UNIQUE_EXISTING_CONTENT" not in prompt


def test_build_digest_prompt_with_existing():
    conversations = [
        {"file": "test.md", "date": "2026-03-31", "content": "## 요약\n테스트"}
    ]
    prompt = build_digest_prompt(conversations, "UNIQUE_EXISTING_CONTENT")
    assert "UNIQUE_EXISTING_CONTENT" in prompt


def test_write_digest(tmp_path):
    analysis = {
        "principles": [
            {
                "principle": "자동화 선호",
                "evidence": "여러 대화에서 확인",
                "strength": "strong",
            },
            {
                "principle": "공식 방식 우선",
                "evidence": "1회 관찰",
                "strength": "emerging",
            },
        ],
        "recurring_patterns": [
            {
                "pattern": "위험한 변경 전 백업",
                "examples": ["settings.json 백업", "DB 스냅샷"],
            }
        ],
        "growth": ["비동기 처리 이해 깊어짐"],
    }

    path = write_digest(tmp_path, analysis)
    assert path.exists()
    assert path.name == "My Patterns.md"

    post = frontmatter.load(path)
    assert post["type"] == "digest"
    assert "**[strong]**" in post.content
    assert "*[emerging]*" in post.content
    assert "자동화 선호" in post.content
    assert "위험한 변경 전 백업" in post.content
    assert "비동기 처리 이해 깊어짐" in post.content


def test_write_digest_overwrites_existing(tmp_path):
    old_post = frontmatter.Post(content="# Old", type="digest")
    (tmp_path / "My Patterns.md").write_text(frontmatter.dumps(old_post))

    analysis = {
        "principles": [{"principle": "새 원칙", "evidence": "근거", "strength": "strong"}],
        "recurring_patterns": [],
        "growth": [],
    }
    write_digest(tmp_path, analysis)

    post = frontmatter.load(tmp_path / "My Patterns.md")
    assert "새 원칙" in post.content
    assert "Old" not in post.content
