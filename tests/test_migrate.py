import frontmatter

from obsidian_brain.migrate import (
    deduplicate_insights,
    migrate_concepts_to_experiences,
    migrate_conversations_to_daily,
    remove_empty_sections,
)
from obsidian_brain.similarity import is_similar


def test_similar_identical():
    assert is_similar("hello world", "hello world")


def test_similar_different():
    assert not is_similar("apples", "oranges")


def test_similar_near_duplicate():
    assert is_similar("10단계 파이프라인 확정", "파이프라인 10단계 확정")


def test_deduplicate_insights():
    content = """## 인사이트
- (2026-03-01) 10단계 파이프라인 확정
- (2026-03-02) 파이프라인 10단계가 확정됨
- (2026-03-03) 완전히 다른 인사이트"""

    result = deduplicate_insights(content)
    assert "10단계 파이프라인 확정" in result
    assert "완전히 다른 인사이트" in result
    # Second duplicate should be removed
    lines = [l for l in result.split("\n") if l.strip().startswith("- (")]
    assert len(lines) == 2


def test_remove_empty_sections():
    content = """## 요약
대화 요약 내용

## 핵심 결정사항

## 관련 개념
- [[Docker]]"""

    result = remove_empty_sections(content)
    assert "## 요약" in result
    assert "## 핵심 결정사항" not in result
    assert "## 관련 개념" in result


def test_remove_empty_sections_all_filled():
    content = """## 요약
내용1

## 결정
내용2"""
    result = remove_empty_sections(content)
    assert result == content


def test_migrate_conversations_to_daily_basic(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)

    post = frontmatter.Post(
        content="## 요약\nproject-a feature-x v3 설계를 논의하고 가중치 구조를 결정했다.",
        source="claude-code",
        date="2026-03-01",
        projects=["backend"],
        tags=["project-a", "feature-x"],
    )
    (conv_dir / "2026-03-01-project-a-feature-x.md").write_text(frontmatter.dumps(post))

    config = {
        "folders": {"daily": "Daily"},
        "projects": {
            "project-a": {"description": "", "aliases": ["backend"]},
        },
    }
    result = migrate_conversations_to_daily(tmp_path, config)

    assert result["converted"] == 1
    assert result["days"] == 1

    daily_file = tmp_path / "Daily" / "2026-03-01.md"
    assert daily_file.exists()
    daily = frontmatter.load(daily_file)
    assert "## [[project-a]]" in daily.content
    assert "feature-x" in daily.content
    assert "project-a" in daily["projects"]
    assert "feature-x" in daily["tags"]

    # Original archived
    assert not (tmp_path / "Conversations").exists()
    assert (tmp_path / "레거시" / "Conversations" / "2026-03" / "2026-03-01-project-a-feature-x.md").exists()


def test_migrate_conversations_to_daily_unmapped_goes_to_기타(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)

    post = frontmatter.Post(
        content="## 요약\n미분류 실험 세션.",
        date="2026-03-02",
        projects=["random-thing"],
    )
    (conv_dir / "test.md").write_text(frontmatter.dumps(post))

    result = migrate_conversations_to_daily(tmp_path, {"folders": {"daily": "Daily"}, "projects": {}})
    assert result["converted"] == 1

    daily = frontmatter.load(tmp_path / "Daily" / "2026-03-02.md")
    assert "## 기타" in daily.content
    assert "미분류" in daily.content


def test_migrate_conversations_to_daily_groups_same_day(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)

    for i, title in enumerate(["first session", "second session"]):
        post = frontmatter.Post(
            content=f"## 요약\n{title} 작업.",
            date="2026-03-03",
            projects=["project-a"],
        )
        (conv_dir / f"conv-{i}.md").write_text(frontmatter.dumps(post))

    config = {
        "folders": {"daily": "Daily"},
        "projects": {"project-a": {"description": "", "aliases": []}},
    }
    result = migrate_conversations_to_daily(tmp_path, config)
    assert result["converted"] == 2
    assert result["days"] == 1

    daily = frontmatter.load(tmp_path / "Daily" / "2026-03-03.md")
    assert daily.content.count("- ") >= 2


def test_migrate_concepts_to_experiences(tmp_path):
    concepts_dir = tmp_path / "Concepts"
    concepts_dir.mkdir()
    (concepts_dir / "Old Concept.md").write_text("old content")
    (concepts_dir / "Another Concept.md").write_text("old content")

    result = migrate_concepts_to_experiences(tmp_path)

    assert result["removed_concepts"] == 2
    assert result["created_experiences_dir"] is True
    assert not concepts_dir.exists()
    assert (tmp_path / "Experiences").exists()


def test_migrate_concepts_to_experiences_no_concepts(tmp_path):
    result = migrate_concepts_to_experiences(tmp_path)

    assert result["removed_concepts"] == 0
    assert result["created_experiences_dir"] is True
    assert (tmp_path / "Experiences").exists()
