import logging
from datetime import date, timedelta
from pathlib import Path

import frontmatter

from .claude_api import call_claude

logger = logging.getLogger(__name__)

DIGEST_FILENAME = "My Patterns.md"

DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "principles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "principle": {"type": "string", "description": "원칙/성향 한 줄"},
                    "evidence": {"type": "string", "description": "근거가 된 대화/상황 요약"},
                    "strength": {
                        "type": "string",
                        "enum": ["strong", "emerging"],
                        "description": "strong: 여러 대화에서 반복 확인, emerging: 1~2회 관찰",
                    },
                },
                "required": ["principle", "evidence", "strength"],
            },
            "description": "종합된 사용자의 원칙/성향 목록",
        },
        "recurring_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "반복되는 의사결정 패턴"},
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "패턴이 나타난 구체적 사례들",
                    },
                },
                "required": ["pattern", "examples"],
            },
            "description": "여러 대화에서 반복되는 의사결정 패턴",
        },
        "growth": {
            "type": "array",
            "items": {"type": "string"},
            "description": "이전 대비 변화/성장이 보이는 부분",
        },
    },
    "required": ["principles", "recurring_patterns", "growth"],
}


def should_run_digest(vault_path: Path) -> bool:
    """Check if digest should run today (once per day)."""
    marker = vault_path / ".obsidian-brain" / ".last_digest"
    if not marker.exists():
        return True
    last_run = marker.read_text().strip()
    return last_run != date.today().isoformat()


def mark_digest_done(vault_path: Path) -> None:
    marker = vault_path / ".obsidian-brain" / ".last_digest"
    marker.write_text(date.today().isoformat())


def collect_recent_conversations(vault_path: Path, conv_folder: str, days: int = 7) -> list[dict]:
    """Read recent conversation docs and extract reasoning patterns + preferences."""
    conv_dir = vault_path / conv_folder
    if not conv_dir.exists():
        return []

    cutoff = date.today() - timedelta(days=days)
    conversations = []

    for month_dir in sorted(conv_dir.iterdir()):
        if not month_dir.is_dir():
            continue
        for md_file in sorted(month_dir.glob("*.md")):
            try:
                post = frontmatter.load(md_file)
                doc_date = post.get("date", "")
                if doc_date and doc_date >= cutoff.isoformat():
                    conversations.append({
                        "file": md_file.name,
                        "date": doc_date,
                        "content": post.content,
                    })
            except Exception:
                continue

    return conversations


def load_existing_digest(vault_path: Path) -> str:
    """Load existing digest content if it exists."""
    digest_path = vault_path / DIGEST_FILENAME
    if digest_path.exists():
        post = frontmatter.load(digest_path)
        return post.content
    return ""


def build_digest_prompt(conversations: list[dict], existing_digest: str) -> str:
    conv_text = ""
    for conv in conversations:
        conv_text += f"### {conv['file']} ({conv['date']})\n{conv['content']}\n\n"

    existing_section = ""
    if existing_digest:
        existing_section = f"""[기존 종합 문서]
{existing_digest}

"""

    return f"""다음은 사용자의 최근 AI 대화 기록들이다. 각 대화에서 추출된 의사결정 패턴과 선호/원칙이 포함되어 있다.

{existing_section}[최근 대화 기록]
{conv_text}

이 대화들을 종합 분석해서 사용자의 핵심 원칙/성향, 반복되는 의사결정 패턴, 성장/변화를 정리해줘.

규칙:
- principles: 여러 대화에서 일관되게 나타나는 원칙이면 strong, 1~2회면 emerging. 기존 종합 문서가 있으면 기존 원칙을 유지/업데이트/제거 판단.
- recurring_patterns: "이 사람은 X 상황에서 항상 Y를 선택한다" 형태로 정리. 최소 2회 이상 관찰된 것만.
- growth: 이전 종합 대비 새로 나타난 성향이나 변화. 기존 문서가 없으면 빈 배열."""


def run_digest_analysis(prompt: str, max_retries: int = 3) -> dict:
    return call_claude(prompt, DIGEST_SCHEMA, max_retries=max_retries)


def write_digest(vault_path: Path, analysis: dict) -> Path:
    digest_path = vault_path / DIGEST_FILENAME

    principles_lines = ""
    for p in analysis.get("principles", []):
        badge = "**[strong]**" if p["strength"] == "strong" else "*[emerging]*"
        principles_lines += f"- {badge} {p['principle']}\n  - 근거: {p['evidence']}\n"

    patterns_lines = ""
    for rp in analysis.get("recurring_patterns", []):
        examples = ", ".join(rp["examples"])
        patterns_lines += f"- **{rp['pattern']}**\n  - 사례: {examples}\n"

    growth_lines = "\n".join(f"- {g}" for g in analysis.get("growth", []))

    post = frontmatter.Post(
        content=f"""# My Patterns

마지막 업데이트: {date.today().isoformat()}

## 핵심 원칙/성향
{principles_lines}
## 반복되는 의사결정 패턴
{patterns_lines}
## 변화/성장
{growth_lines}""",
        type="digest",
        cssclasses=["ob-digest"],
        updated=date.today().isoformat(),
    )

    digest_path.write_text(frontmatter.dumps(post))
    return digest_path


def run_daily_digest(vault_path: Path, conv_folder: str = "Conversations", max_retries: int = 3, digest_days: int = 30) -> Path | None:
    if not should_run_digest(vault_path):
        logger.info("Digest already ran today, skipping")
        return None

    conversations = collect_recent_conversations(vault_path, conv_folder, days=digest_days)
    if not conversations:
        logger.info("No recent conversations for digest")
        mark_digest_done(vault_path)
        return None

    existing = load_existing_digest(vault_path)
    prompt = build_digest_prompt(conversations, existing)

    logger.info(f"Running digest with {len(conversations)} recent conversations")
    analysis = run_digest_analysis(prompt, max_retries=max_retries)

    digest_path = write_digest(vault_path, analysis)
    mark_digest_done(vault_path)
    logger.info(f"Digest written to {digest_path}")

    return digest_path
