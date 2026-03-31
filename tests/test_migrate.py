import frontmatter

from obsidian_brain.migrate import (
    deduplicate_insights,
    migrate_concepts,
    migrate_conversations,
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


def test_migrate_conversations_adds_type(tmp_path):
    conv_dir = tmp_path / "Conversations" / "2026-03"
    conv_dir.mkdir(parents=True)

    post = frontmatter.Post(content="## 요약\n테스트", source="claude-code", date="2026-03-01")
    (conv_dir / "test.md").write_text(frontmatter.dumps(post))

    count = migrate_conversations(tmp_path)
    assert count == 1

    migrated = frontmatter.load(conv_dir / "test.md")
    assert migrated["type"] == "conversation"


def test_migrate_concepts_removes_none(tmp_path):
    concepts_dir = tmp_path / "Concepts"
    concepts_dir.mkdir()

    post = frontmatter.Post(
        content="# Test\n\nNone\n\n## 인사이트\n- (2026-03-01) test",
        type="concept",
    )
    (concepts_dir / "Test.md").write_text(frontmatter.dumps(post))

    count = migrate_concepts(tmp_path)
    assert count == 1

    migrated = frontmatter.load(concepts_dir / "Test.md")
    assert "None" not in migrated.content
