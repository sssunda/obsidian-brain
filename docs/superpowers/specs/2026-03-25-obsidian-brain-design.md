# Obsidian Brain — Phase 1 Design Spec

## Overview

Claude Code 대화가 끝날 때마다 자동으로 Obsidian 문서를 생성하고, 기존 문서들과 `[[링크]]`를 형성하여 지식 그래프를 성장시키는 시스템.

## Scope (Phase 1)

- **입력**: Claude Code 대화만 (SessionEnd hook으로 자동 트리거)
- **처리**: Python 스크립트 → `claude -p`로 분석 → Obsidian 마크다운 생성
- **출력**: `Conversations/`, `Concepts/`, `Projects/` 문서 + `[[위키링크]]` 자동 연결
- **Phase 2 예정**: Telegram 입력, ChatGPT/Gemini export, Obsidian Plugin 포팅

## Architecture

```
Claude Code 종료 (Ctrl+C, /exit)
→ SessionEnd hook 발동 (session_id, reason 수신)
→ transcript 경로 구성: ~/.claude/projects/{encoded_cwd}/{session_id}.jsonl
→ Python 스크립트 백그라운드 실행 (lockfile 획득)
→ Parser: transcript.jsonl 파싱 → 통합 포맷
→ Filter: user 메시지 3개 이하 스킵
→ Analyzer: claude -p --model sonnet --output-format json 호출
→ Generator: Obsidian 마크다운 생성 + [[링크]] 연결
→ 처리 완료 세션 ID 기록 → lockfile 해제
```

### Components

#### 1. Watcher (Hook 설정)

- `SessionEnd` hook: 대화 종료 시 Python 스크립트를 **백그라운드**로 실행
- `SessionStart` hook: 미처리 과거 대화 확인 → 있으면 처리 (터미널 강제 종료 대비)
- Hook 페이로드: `session_id`, `reason` (transcript_path는 전달되지 않음 — 직접 구성)

**Hook 설정 예시 (`~/.claude/settings.json`):**
```json
{
  "hooks": {
    "SessionEnd": [
      {
        "command": "uv run --project /path/to/obsidian-brain python -m obsidian_brain process --session-id $SESSION_ID --cwd $CWD &",
        "timeout": 5000
      }
    ],
    "SessionStart": [
      {
        "command": "uv run --project /path/to/obsidian-brain python -m obsidian_brain recover &",
        "timeout": 5000
      }
    ]
  }
}
```

**Transcript 경로 구성 규칙:**
- 경로 패턴: `~/.claude/projects/{encoded_cwd}/{session_id}.jsonl`
- CWD 인코딩: 경로 구분자 `/`를 `-`로 치환, 선행 `-` 포함
  - 예: `/Users/daeun/sssunda` → `-Users-daeun-sssunda`
  - 파일: `~/.claude/projects/-Users-daeun-sssunda/abc123.jsonl`

#### 2. Parser

Claude Code의 `{session_id}.jsonl` 파일을 읽어 통합 JSON 포맷으로 변환.

**transcript.jsonl 레코드 타입과 처리:**

| 타입 | 처리 |
|------|------|
| `user` | 추출 — `message.content` (문자열) |
| `assistant` | 추출 — `message.content` 배열에서 `text` 블록만 (thinking, tool_use 제외) |
| `progress` | 무시 (전체의 ~37%) |
| `system` | 무시 |
| `file-history-snapshot` | 무시 |
| `last-prompt` | 무시 |

**통합 포맷:**
```json
{
  "session_id": "abc123",
  "source": "claude-code",
  "date": "2026-03-25",
  "cwd": "/Users/daeun/sssunda/obsidian-brain",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

- Phase 2에서 ChatGPT, Gemini 어댑터 추가 예정

#### 3. Filter

- **user 타입 메시지가 3개 이하**인 세션은 스킵 (assistant나 progress 제외, user 메시지 수가 실질적 대화 깊이를 반영)
- 이미 처리된 세션 ID는 `.processed` 파일로 관리하여 중복 방지

#### 4. Analyzer

- `claude -p --model sonnet --output-format json --json-schema '{...}'` 호출
- `--json-schema` 옵션으로 구조화된 JSON 출력을 강제 → JSON 파싱 실패 가능성 최소화
- `--model sonnet` 사용 — 분석 작업에 Opus는 과잉, 비용 절약
- 프롬프트에 기존 Vault의 개념 이름 목록과 프로젝트 이름 목록을 함께 전달 (이름만, 내용 X)
- Claude가 "Docker"와 "컨테이너"가 같은 개념인지 등 시맨틱 매칭 수행

**Analyzer 프롬프트 구조:**
```
다음 AI 대화를 분석해줘.

[기존 개념 목록]: Docker, Python, React, ...
[기존 프로젝트 목록]: obsidian-brain, pomodoro-todo, ...

[대화 내용]
(파싱된 대화 transcript)
```

**Analyzer 출력 스키마 (`--json-schema`로 전달):**
```json
{
  "summary": "옵시디언에 AI 대화를 자동 문서화하는 시스템을 설계했다",
  "decisions": [
    "Phase 1은 Claude Code만 지원",
    "Python 파이프라인 방식 채택"
  ],
  "concepts": [
    {
      "name": "지식그래프",
      "description": "노드(문서)와 엣지(링크)로 지식을 연결하는 구조",
      "aliases": ["knowledge graph"],
      "existing_match": null,
      "insight": "Obsidian의 그래프 뷰와 결합하면 시각적 지식 탐색이 가능"
    },
    {
      "name": "Docker",
      "description": null,
      "aliases": [],
      "existing_match": "Docker",
      "insight": null
    }
  ],
  "concept_relations": [
    ["지식그래프", "옵시디언"]
  ],
  "tags": ["obsidian", "automation", "knowledge-management"],
  "projects": ["obsidian-brain"],
  "title_slug": "obsidian-knowledge-graph"
}
```

- `existing_match`: 기존 개념 목록에서 매칭되는 이름. 없으면 null (새 개념)
- `description`: 새 개념인 경우에만 생성. 기존 개념이면 null (기존 문서 유지)
- `insight`: 이 대화에서 해당 개념에 대해 새로 알게 된 사실/패턴. 없으면 null
- `concept_relations`: 이 대화에서 함께 등장하며 관련 있는 개념 쌍
- `title_slug`: **영문 slug** — 대화 문서 파일명에 사용 (날짜와 결합: `2026-03-25-obsidian-knowledge-graph.md`)

**긴 대화 처리 (샌드위치 방식):**
- 파싱 후 user+assistant 텍스트 합산 기준 50,000자 초과 시:
  - 앞부분 15개 메시지 (맥락 설정, 핵심 결정사항 포함)
  - `[... 중간 생략 ...]`
  - 마지막 85개 메시지 (최근 진행 상황)
- 이렇게 하면 초반 설계 결정 + 최근 맥락 모두 보존

**에러 처리:**
- `claude -p` 실패 시: 3회 재시도 (5초 간격)
- 3회 모두 실패 시: `.failed` 파일에 세션 ID + 실패 사유 + 타임스탬프 기록
- 다음 SessionStart에서 `.failed` 항목 재시도

#### 5. Generator

- 분석 결과를 Obsidian 마크다운으로 변환
- **새 문서 생성**: Write tool로 파일 생성
- **기존 문서 업데이트**: frontmatter만 수정 (본문은 건드리지 않음 — 사용자 편집 안전)
  - Concept 문서: frontmatter의 `conversations` 리스트에 새 대화 추가, `insight`가 있으면 본문 `## 인사이트` 섹션 끝에 추가
  - Project 문서: frontmatter의 `conversations` 리스트에 추가
- `[[위키링크]]` 자동 생성
- **파일명 충돌 처리**: 동일 slug가 이미 존재하면 `-2`, `-3` suffix 추가

**동시성 제어:**
- 전체 파이프라인은 **단일 프로세스, 순차 처리**를 보장
- lockfile (`~/.obsidian-brain/pipeline.lock`) 사용 — 이미 처리 중이면 대기
- SessionEnd와 SessionStart Recovery가 동시에 실행되는 경우에도 lockfile로 직렬화

## Vault Structure

```
obsidian-vault/
├── Conversations/
│   ├── 2026-03/
│   │   ├── 2026-03-25-obsidian-knowledge-graph.md
│   │   ├── 2026-03-25-docker-networking.md
│   │   └── ...
│   ├── 2026-04/
│   │   └── ...
│   └── ...
├── Concepts/
│   ├── Docker.md
│   ├── 지식그래프.md
│   ├── Python 파이프라인.md
│   └── ...
├── Projects/
│   ├── obsidian-brain.md
│   ├── pomodoro-todo.md
│   └── ...
└── .obsidian-brain/
    ├── config.yaml
    ├── .processed
    ├── .failed
    ├── pipeline.lock
    └── logs/
        └── 2026-03-25.log
```

- **Conversations는 월별 하위폴더** (`2026-03/`) — 연간 수천 개 파일이 한 폴더에 쌓이는 것 방지
- Obsidian의 `[[]]` 링크는 폴더 경로와 무관하게 파일명으로 동작하므로 링크에 영향 없음

## Document Formats

### Conversation Document

```markdown
---
source: claude-code
session_id: abc123
date: 2026-03-25
title: 옵시디언 지식그래프 시스템 설계
tags: [obsidian, knowledge-graph, automation]
concepts: [옵시디언, 지식그래프, Python 파이프라인]
projects: [obsidian-brain]
---

## 요약
옵시디언에 AI 대화 내역을 자동으로 문서화하는 시스템을 설계했다...

## 핵심 결정사항
- Phase 1은 Claude Code만 지원
- Python 파이프라인 + Claude Code CLI 방식 채택
- 모든 대화를 claude -p로 분석 (하이브리드 아님)

## 관련 개념
- [[지식그래프]]
- [[옵시디언]]
- [[Python 파이프라인]]

## 관련 프로젝트
- [[obsidian-brain]]
```

- 파일명은 **영문 slug** (`2026-03-25-obsidian-knowledge-graph.md`)
- frontmatter `title`에 **한국어 제목** — Obsidian이 표시 이름으로 사용

### Concept Document

```markdown
---
type: concept
created: 2026-03-25
updated: 2026-03-25
aliases: [knowledge graph]
conversations: [2026-03-25-obsidian-knowledge-graph]
---

# 지식그래프

노드(문서)와 엣지(링크)로 지식을 연결하는 구조.

## 인사이트
- (2026-03-25) Obsidian의 그래프 뷰와 결합하면 시각적 지식 탐색이 가능

## 관련 개념
- [[옵시디언]]
```

- **단순 백링크 나열 대신 `인사이트` 누적** — 대화에서 새로 알게 된 사실/패턴을 날짜와 함께 추가
- `conversations` 리스트는 frontmatter에서 관리 (Dataview 플러그인으로 동적 목록 가능)
- `aliases`는 Obsidian의 aliases 기능과 연동 — `[[knowledge graph]]`로 링크해도 이 문서로 연결

### Project Document

```markdown
---
type: project
created: 2026-03-25
updated: 2026-03-25
status: active
conversations: [2026-03-25-obsidian-knowledge-graph]
---

# obsidian-brain

Claude Code 대화를 Obsidian에 자동 문서화하는 시스템.

## 대화 타임라인
- [[2026-03-25-obsidian-knowledge-graph]] — 시스템 설계

## 핵심 결정사항
- Phase 1: Claude Code만, Python 파이프라인
- Phase 2: 다른 AI + Obsidian Plugin
```

## Data Flow

1. **SessionEnd hook 발동** → `session_id` 수신
2. **경로 구성** → `~/.claude/projects/{encoded_cwd}/{session_id}.jsonl`
3. **Lockfile 획득** → 동시 실행 방지
4. **Parser** → jsonl 읽기 → user/assistant text 블록만 추출 → 통합 JSON
5. **Filter** → user 메시지 3개 이하 스킵, 이미 처리된 세션 스킵
6. **Analyzer** → 기존 Vault 개념/프로젝트 이름 수집 → `claude -p --model sonnet --output-format json` 호출
7. **Generator** → 대화 문서 생성 → 개념 문서 생성/업데이트 (frontmatter + 인사이트) → 프로젝트 문서 연결
8. **기록** → 세션 ID를 `.processed`에 추가 → lockfile 해제

## Recovery (터미널 강제 종료 대비)

- `SessionStart` hook에서 미처리 과거 대화 확인
- `~/.claude/projects/{encoded_cwd}/` 아래 `*.jsonl` 파일 스캔
- 파일명(확장자 제외)이 세션 ID
- `.processed`에 없는 세션이 있으면 처리
- 30일 이상 된 미처리 세션은 무시 (너무 오래된 건 의미 없음)
- 미처리 건이 3개 이상이면 백그라운드에서 순차 처리 (세션 시작 지연 방지)
- `.processed` 파일에서 30일 이상 지난 항목은 자동 정리 (rotation)

## Tech Stack

- **Python 3.11+** — 파이프라인 코어
- **uv** — 패키지 관리 및 실행 (`uv run`으로 가상환경 문제 해결)
- **Claude Code CLI** (`claude -p --model sonnet --output-format json`) — 대화 분석
- **python-frontmatter** — YAML frontmatter 파싱/수정
- **watchdog** (Phase 2) — inbox 폴더 감시

## State & Config

모든 설정과 상태 파일은 Vault 내부 `.obsidian-brain/`에 통합 관리:

```
obsidian-vault/.obsidian-brain/
├── config.yaml       # 설정
├── .processed        # 처리 완료된 세션 ID 목록
├── .failed           # 실패한 세션 (ID + 사유 + 타임스탬프)
├── pipeline.lock     # 동시 실행 방지 lockfile
└── logs/             # 실행 로그
    └── 2026-03-25.log
```

```yaml
# .obsidian-brain/config.yaml
vault_path: ~/ObsidianVault          # Obsidian Vault 경로
min_messages: 3                       # 최소 user 메시지 수 (이하 스킵)
max_transcript_chars: 50000           # 이 이상이면 샌드위치 방식 적용
max_retries: 3                        # claude -p 실패 시 재시도 횟수
processed_retention_days: 30          # .processed 항목 보존 기간
slug_language: en                     # 파일명 slug 언어 (en/ko)
folders:
  conversations: Conversations
  concepts: Concepts
  projects: Projects
```

## Future (Phase 2+)

- Telegram 봇 입력 채널
- ChatGPT/Gemini export 파서
- Obsidian Plugin (TypeScript) 포팅 — 커뮤니티 플러그인 배포
- Daily Note 연동 — 그날 생성된 대화 링크를 일간 노트에 자동 추가
- 기존 개념 문서 내용 강화 (여러 대화에서 정보 병합)
- 그래프 성장 통계 대시보드
- 개념 목록 스케일링 — 대화 키워드 기반 관련 개념만 필터링해서 전달
