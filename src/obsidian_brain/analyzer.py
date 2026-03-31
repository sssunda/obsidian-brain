import json
import logging

from .claude_api import call_claude

logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "1~3문장 대화 요약"},
        "decisions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "핵심 결정사항 목록",
        },
        "reasoning_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "situation": {"type": "string", "description": "어떤 상황이었는지"},
                    "choice": {"type": "string", "description": "무엇을 선택했는지"},
                    "why": {"type": "string", "description": "왜 그렇게 선택했는지"},
                },
                "required": ["situation", "choice", "why"],
            },
            "description": "사용자의 의사결정 패턴 — 상황→선택→이유",
        },
        "preferences": {
            "type": "array",
            "items": {"type": "string"},
            "description": "드러난 선호/원칙 (예: '자동화 선호', '안전장치 중시')",
        },
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "existing_match": {"type": ["string", "null"]},
                    "insight": {"type": ["string", "null"]},
                },
                "required": ["name", "existing_match"],
            },
        },
        "concept_relations": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
        "title_slug": {"type": "string", "description": "영문 slug for filename"},
    },
    "required": ["summary", "concepts", "tags", "projects", "title_slug", "reasoning_patterns", "preferences"],
}


def build_json_schema() -> dict:
    return ANALYSIS_SCHEMA


def build_prompt(parsed: dict, concepts: list[str], projects: list[str], existing_insights: dict[str, list[str]] | None = None) -> str:
    concept_list = ", ".join(concepts) if concepts else "(없음)"
    project_list = ", ".join(projects) if projects else "(없음)"

    conversation = ""
    for msg in parsed["messages"]:
        role = "사용자" if msg["role"] == "user" else "AI"
        conversation += f"[{role}]: {msg['content']}\n\n"

    return f"""다음 AI 대화를 분석해줘. 단순히 뭘 했는지가 아니라, **사용자가 왜 그런 선택을 했는지**에 집중해서 분석해줘.

[기존 개념 목록]: {concept_list}
[기존 프로젝트 목록]: {project_list}

규칙:
- reasoning_patterns: 사용자가 선택/판단을 한 순간을 찾아서, 상황(situation) → 선택(choice) → 이유(why)로 정리. 예: "훅이 세션을 블로킹" → "async: true 사용" → "공식 지원 옵션이라 셸 해킹보다 안정적". 판단이 드러나지 않는 단순 질문 대화면 빈 배열.
- preferences: 대화에서 드러나는 사용자의 성향/원칙. 예: "자동화 선호", "안전장치 먼저 확인", "수동 복붙보다 스크립트 자동화". 명시적으로 말한 것뿐 아니라 행동에서 추론한 것도 포함.
- concepts: 시스템/아키텍처/설계 수준의 핵심 개념만 추출. 일회성 버그, 특정 함수명, 사소한 패턴은 제외. "다른 프로젝트에서도 재사용할 수 있는 지식인가?"를 기준으로 판단. 대화당 0~3개 정도.
- existing_match: 기존 개념 목록에 같은 개념이 있으면 해당 이름. 없으면 null.
- description: 새 개념(existing_match가 null)이면 한 줄 설명. 기존 개념이면 null.
- insight: 이 대화에서 해당 개념에 대해 **이전에 기록된 적 없는** 완전히 새로운 사실이 있을 때만 한 줄. 그 외에는 반드시 null. 판단 기준: 아래 [기존 인사이트]를 읽고, 핵심 의미가 같으면 표현이 달라도 중복이다. 조사/어미/어순만 다른 경우도 중복이다. 의심스러우면 null로 처리하라.
- concept_relations: 이 대화에서 관련 있는 개념 쌍 목록.
- title_slug: 대화 주제를 영문 kebab-case로 (예: docker-networking, react-hooks-guide).
- tags: 소문자 영문 태그.
- projects: 기존 프로젝트 목록에서 관련된 것만. 새 프로젝트면 이름 추가.

{_format_existing_insights(existing_insights)}[대화 내용]
{conversation}"""


def _format_existing_insights(insights: dict[str, list[str]] | None) -> str:
    if not insights:
        return ""
    lines = ["[기존 인사이트 — 아래 내용과 같거나 유사한 의미의 insight는 반드시 null로 처리. 표현이 달라도 의미가 같으면 중복이다.]\n"]
    for concept, insight_list in insights.items():
        if insight_list:
            lines.append(f"  {concept}:")
            for ins in insight_list:  # All insights, not just last 5
                lines.append(f"    - {ins}")
    return "\n".join(lines) + "\n\n"


def truncate_messages(messages: list[dict], max_chars: int = 50000, head_count: int = 15, tail_count: int = 85) -> list[dict]:
    total = sum(len(m["content"]) for m in messages)
    if total <= max_chars:
        return messages
    if len(messages) <= head_count + tail_count:
        return messages

    head = messages[:head_count]
    tail = messages[-tail_count:]
    skipped = len(messages) - head_count - tail_count
    separator = {"role": "system", "content": f"[... 중간 {skipped}개 메시지 생략 ...]"}
    return head + [separator] + tail


def analyze(parsed: dict, concepts: list[str], projects: list[str], max_retries: int = 3, existing_insights: dict[str, list[str]] | None = None, model: str = "sonnet") -> dict:
    truncated = truncate_messages(parsed["messages"], max_chars=50000)
    truncated_parsed = {**parsed, "messages": truncated}
    prompt = build_prompt(truncated_parsed, concepts, projects, existing_insights)
    return call_claude(prompt, ANALYSIS_SCHEMA, max_retries=max_retries, model=model)
