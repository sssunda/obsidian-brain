import logging

from .claude_api import call_claude

logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "title_slug": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "daily_entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project": {"type": ["string", "null"]},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project", "bullets"],
            },
        },
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "experience_type": {
                        "type": "string",
                        "enum": ["problem-solving", "discovery", "troubleshooting"],
                    },
                    "sections": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "experience_type", "sections"],
            },
        },
    },
    "required": [
        "summary", "title_slug", "tags", "decisions",
        "daily_entries", "experiences",
    ],
}


def build_json_schema() -> dict:
    return ANALYSIS_SCHEMA


def build_prompt(
    parsed: dict,
    projects_config: dict | None = None,
    cwd: str | None = None,
    existing_experiences: list[str] | None = None,
    about: str | None = None,
) -> str:
    messages = truncate_messages(parsed["messages"])
    date = parsed["date"]
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )

    context_lines = []
    if about:
        context_lines.append(f"사용자: {about}")
    if cwd:
        dir_name = cwd.rstrip("/").split("/")[-1] if "/" in cwd else cwd
        context_lines.append(f"작업 디렉토리: {cwd} (힌트: {dir_name})")
    context_section = "\n".join(context_lines)

    # Project descriptions
    project_section = ""
    if projects_config:
        lines = ["## 프로젝트 목록 (이 중에서만 선택)"]
        for name, config in projects_config.items():
            aliases = config.get("aliases", [])
            desc = config.get("description", "")
            alias_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
            lines.append(f"- **{name}**{alias_str}: {desc}")
        lines.append("")
        lines.append("위 목록에 없는 프로젝트명은 사용하지 마. 매칭 안 되면 project: null로.")
        project_section = "\n".join(lines)

    # Existing experiences
    experience_section = ""
    if existing_experiences:
        lines = ["## 기존 경험 노트"]
        for title in existing_experiences:
            lines.append(f"- {title}")
        lines.append("")
        lines.append("위 목록과 같은 내용이면 experiences에 포함하지 마. 새롭게 배운 것만 추출해.")
        experience_section = "\n".join(lines)

    return f"""다음 AI 대화를 분석해줘.

날짜: {date}
{context_section}

{project_section}

## 분석 지침

1. summary: 이 대화에서 뭘 했는지 1-3문장으로 요약
2. title_slug: 영문 kebab-case 파일명 슬러그
3. tags: 소문자 영문 태그
4. decisions: 핵심 결정사항 목록
5. daily_entries: 프로젝트별로 오늘 한 일을 bullet 정리
   - project: 프로젝트명 (위 목록 중 하나, 또는 null)
   - bullets: 각각 한 줄로 뭘 했는지. 하위 설명이 필요하면 " — " 으로 이어서
   - 한 세션이 여러 프로젝트에 걸치면 각각 별도 entry로

{experience_section}

## 경험 추출 (experiences)

이 대화에서 **나중에 다시 찾아볼 만한** 문제 해결, 발견, 삽질이 있으면 추출해.
없으면 experiences: [] 로 반환해. 억지로 만들지 마.

각 경험의 타입:
- problem-solving: 문제를 만나서 해결함. sections에 "상황", "선택", "교훈" 키 사용
- discovery: 새로 알게 된 사실. sections에 "발견", "맥락" 키 사용
- troubleshooting: 삽질해서 원인 찾음. sections에 "삽질", "원인", "해결" 키 사용

title 규칙:
- 사용자가 대화에서 실제로 쓴 표현을 최대한 활용
- 기술 중심이 자연스러우면: "Django QuerySet 평가 시점 함정"
- 상황 중심이 자연스러우면: "배포 직전 마이그레이션 충돌"
- 추상적 조어 금지 ("범용 X 패턴", "Y 오염 패턴" 같은 거 쓰지 마)

sections 내용 규칙:
- 구체적으로 써. "QuerySet이 느렸다"가 아니라 "Admin에서 LogEntry bulk 조회가 5초 이상 걸림"
- 해당 내용이 대화에 실제로 있을 때만 작성. 억지로 채우지 마.

단순 작업 수행 ("파일 만들어줘", "이거 고쳐줘", "리팩토링해줘")은 경험이 아님.

---
대화 내용:
{transcript}"""


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


def analyze(
    parsed: dict,
    projects_config: dict | None = None,
    cwd: str | None = None,
    existing_experiences: list[str] | None = None,
    about: str | None = None,
    model: str = "sonnet",
) -> dict:
    prompt = build_prompt(parsed, projects_config=projects_config, cwd=cwd, existing_experiences=existing_experiences, about=about)
    return call_claude(prompt, ANALYSIS_SCHEMA, model=model)
