import json
import logging
import subprocess
import time

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
    "required": ["summary", "concepts", "tags", "projects", "title_slug"],
}


def build_json_schema() -> dict:
    return ANALYSIS_SCHEMA


def build_prompt(parsed: dict, concepts: list[str], projects: list[str]) -> str:
    concept_list = ", ".join(concepts) if concepts else "(없음)"
    project_list = ", ".join(projects) if projects else "(없음)"

    conversation = ""
    for msg in parsed["messages"]:
        role = "사용자" if msg["role"] == "user" else "AI"
        conversation += f"[{role}]: {msg['content']}\n\n"

    return f"""다음 AI 대화를 분석해줘.

[기존 개념 목록]: {concept_list}
[기존 프로젝트 목록]: {project_list}

규칙:
- existing_match: 기존 개념 목록에 같은 개념이 있으면 해당 이름. 없으면 null.
- description: 새 개념(existing_match가 null)이면 한 줄 설명. 기존 개념이면 null.
- insight: 이 대화에서 해당 개념에 대해 새로 알게 된 사실이 있으면 한 줄. 없으면 null.
- concept_relations: 이 대화에서 관련 있는 개념 쌍 목록.
- title_slug: 대화 주제를 영문 kebab-case로 (예: docker-networking, react-hooks-guide).
- tags: 소문자 영문 태그.
- projects: 기존 프로젝트 목록에서 관련된 것만. 새 프로젝트면 이름 추가.

[대화 내용]
{conversation}"""


def truncate_messages(messages: list[dict], max_chars: int = 50000) -> list[dict]:
    total = sum(len(m["content"]) for m in messages)
    if total <= max_chars:
        return messages

    head_count = 15
    tail_count = 85
    if len(messages) <= head_count + tail_count:
        return messages

    head = messages[:head_count]
    tail = messages[-tail_count:]
    skipped = len(messages) - head_count - tail_count
    separator = {"role": "system", "content": f"[... 중간 {skipped}개 메시지 생략 ...]"}
    return head + [separator] + tail


def analyze(parsed: dict, concepts: list[str], projects: list[str], max_retries: int = 3) -> dict:
    truncated = truncate_messages(parsed["messages"], max_chars=50000)
    truncated_parsed = {**parsed, "messages": truncated}
    prompt = build_prompt(truncated_parsed, concepts, projects)
    schema_json = json.dumps(ANALYSIS_SCHEMA)

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--model", "sonnet",
                    "--output-format", "json",
                    "--json-schema", schema_json,
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(f"claude -p failed (attempt {attempt + 1}): {result.stderr[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue

            output = json.loads(result.stdout)
            if "result" in output and isinstance(output["result"], str):
                return json.loads(output["result"])
            elif "result" in output and isinstance(output["result"], dict):
                return output["result"]
            return output

        except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Analyzer error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    raise RuntimeError(f"Analyzer failed after {max_retries} attempts")
