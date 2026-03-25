"""Integration test using a real transcript file (mocked claude -p)."""
import json
from pathlib import Path
from unittest.mock import patch

import frontmatter

from obsidian_brain.pipeline import process_session

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_analyze(parsed, concepts, projects, max_retries=3):
    """Return a realistic analysis result without calling claude -p."""
    return {
        "summary": "Docker 네트워킹의 bridge와 host 차이를 배웠다",
        "decisions": [],
        "concepts": [
            {
                "name": "Docker",
                "description": None,
                "aliases": [],
                "existing_match": "Docker",
                "insight": "bridge는 격리, host는 공유",
            },
            {
                "name": "컨테이너 네트워킹",
                "description": "컨테이너 간 통신을 관리하는 기술",
                "aliases": ["container networking"],
                "existing_match": None,
                "insight": None,
            },
        ],
        "concept_relations": [["Docker", "컨테이너 네트워킹"]],
        "tags": ["docker", "networking"],
        "projects": [],
        "title_slug": "docker-networking",
    }


@patch("obsidian_brain.pipeline.analyze", side_effect=_mock_analyze)
def test_full_pipeline_creates_documents(mock_analyze, tmp_path):
    """Full pipeline: parse -> filter -> analyze -> generate."""
    # Set up vault
    vault = tmp_path / "vault"
    vault.mkdir()
    brain_dir = vault / ".obsidian-brain"
    brain_dir.mkdir()
    (brain_dir / ".processed").write_text("")

    # Create existing concept
    concepts_dir = vault / "Concepts"
    concepts_dir.mkdir()
    docker_doc = concepts_dir / "Docker.md"
    docker_doc.write_text("""---
type: concept
created: 2026-03-20
updated: 2026-03-20
aliases: []
conversations: []
---

# Docker

컨테이너 플랫폼.

## 인사이트

## 관련 개념
""")

    (vault / "Projects").mkdir()

    result = process_session(
        transcript_path=FIXTURES / "sample_transcript.jsonl",
        vault_path=vault,
        min_messages=2,
    )

    # Conversation doc created
    assert result is not None
    assert result.exists()
    assert "docker-networking" in result.name

    # Existing concept updated
    docker_content = docker_doc.read_text()
    assert "bridge는 격리" in docker_content

    # New concept created
    new_concept = concepts_dir / "컨테이너 네트워킹.md"
    assert new_concept.exists()
    post = frontmatter.load(new_concept)
    assert "container networking" in post.get("aliases", [])

    # Session marked as processed
    processed = (brain_dir / ".processed").read_text()
    assert "sample_transcript" in processed
