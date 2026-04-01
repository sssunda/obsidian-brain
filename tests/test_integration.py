"""Integration test using a real transcript file (mocked claude -p)."""
import json
from pathlib import Path
from unittest.mock import patch

import frontmatter

from obsidian_brain.pipeline import process_session

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_analyze(parsed, projects, model="sonnet"):
    """Return a realistic analysis result without calling claude -p."""
    return {
        "summary": "Docker 네트워킹의 bridge와 host 차이를 배웠다",
        "decisions": [],
        "experiences": [
            {
                "title": "Docker bridge vs host 네트워크 차이",
                "experience_type": "discovery",
                "sections": {
                    "상황": "Docker 네트워킹 옵션을 알아보던 중",
                    "선택": "bridge 모드 사용",
                    "교훈": "bridge는 격리, host는 공유",
                },
                "tags": ["docker", "networking"],
            }
        ],
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

    (vault / "Experiences").mkdir()
    (vault / "Projects").mkdir()
    (vault / "Conversations").mkdir()

    result = process_session(
        transcript_path=FIXTURES / "sample_transcript.jsonl",
        vault_path=vault,
        min_messages=2,
    )

    # Conversation doc created
    assert result is not None
    assert result.exists()
    assert "docker-networking" in result.name

    # Experience note created
    exp_files = list((vault / "Experiences").glob("*.md"))
    assert len(exp_files) == 1
    exp_post = frontmatter.load(exp_files[0])
    assert exp_post.get("experience_type") == "discovery"
    assert "bridge는 격리" in exp_post.content

    # Session marked as processed
    processed = (brain_dir / ".processed").read_text()
    assert "sample_transcript" in processed
