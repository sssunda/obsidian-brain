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
→ SessionEnd hook 발동
→ Python 스크립트에 transcript_path 전달
→ Parser: transcript.jsonl 파싱 → 통합 포맷
→ Filter: 메시지 3개 이하 스킵
→ Analyzer: claude -p 호출 (기존 개념/프로젝트 목록 포함)
→ Generator: Obsidian 마크다운 생성 + [[링크]] 연결
→ 처리 완료 세션 ID 기록
```

### Components

#### 1. Watcher (Hook 설정)

- `SessionEnd` hook: 대화 종료 시 Python 스크립트 실행
- `SessionStart` hook: 미처리 과거 대화 확인 → 있으면 처리 (터미널 강제 종료 대비)
- Hook은 `transcript_path`, `session_id`, `cwd` 를 스크립트에 전달

#### 2. Parser

- Claude Code의 `transcript.jsonl` 파일을 읽어 통합 JSON 포맷으로 변환
- 통합 포맷:
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

- 메시지 3개 이하인 세션은 스킵 (의미 없는 대화 제외)
- 이미 처리된 세션 ID는 `.processed` 파일로 관리하여 중복 방지

#### 4. Analyzer

- `claude -p` CLI 호출로 대화 분석
- 프롬프트에 기존 Vault의 개념 이름 목록과 프로젝트 이름 목록을 함께 전달 (이름만, 내용 X)
- Claude가 "Docker"와 "컨테이너"가 같은 개념인지 등 시맨틱 매칭 수행

**Analyzer 프롬프트 구조:**
```
다음 AI 대화를 분석해서 JSON으로 반환해줘.

[기존 개념 목록]: Docker, Python, React, ...
[기존 프로젝트 목록]: obsidian-brain, pomodoro-todo, ...

[대화 내용]
(파싱된 대화 transcript)

반환 형식은 아래 JSON 스키마를 따라줘.
```

**Analyzer 출력 스키마:**
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
      "existing_match": null
    },
    {
      "name": "Docker",
      "description": null,
      "aliases": [],
      "existing_match": "Docker"
    }
  ],
  "tags": ["obsidian", "automation", "knowledge-management"],
  "projects": ["obsidian-brain"],
  "title_slug": "옵시디언-지식그래프"
}
```

- `existing_match`: 기존 개념 목록에서 매칭되는 이름. 없으면 null (새 개념)
- `description`: 새 개념인 경우에만 생성. 기존 개념이면 null (기존 문서 유지)
- `title_slug`: 대화 문서 파일명에 사용 (날짜와 결합: `2026-03-25-옵시디언-지식그래프.md`)

**긴 대화 처리:**
- 대화가 50,000자 초과 시 마지막 100개 메시지만 전달 (최근 맥락 우선)
- 잘린 경우 프롬프트에 "[앞부분 생략됨]" 표시

**에러 처리:**
- `claude -p` 실패 시: 3회 재시도 (5초 간격)
- 3회 모두 실패 시: `.failed` 파일에 세션 ID 기록, 다음 SessionStart에서 재시도
- JSON 파싱 실패 시: 원본 응답을 로그에 기록 후 재시도

#### 5. Generator

- 분석 결과를 Obsidian 마크다운으로 변환
- 기존 Vault 스캔:
  - 새 개념 → `Concepts/` 에 새 문서 생성
  - 기존 개념 → 해당 문서에 새 대화 링크 추가
  - 관련 프로젝트 → `Projects/` 문서에 연결
- `[[위키링크]]` 자동 생성

## Vault Structure

```
obsidian-vault/
├── Conversations/
│   ├── 2026-03-25-옵시디언-지식그래프.md
│   ├── 2026-03-25-docker-네트워킹.md
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
    └── .processed          # 처리 완료된 세션 ID 목록
```

## Document Formats

### Conversation Document

```markdown
---
source: claude-code
session_id: abc123
date: 2026-03-25
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
- [[옵시디언]]
- [[지식그래프]]
- [[Python 파이프라인]]

## 관련 프로젝트
- [[obsidian-brain]]
```

### Concept Document

```markdown
---
type: concept
created: 2026-03-25
updated: 2026-03-25
aliases: []
---

# 지식그래프

노드(문서)와 엣지(링크)로 지식을 연결하는 구조.

## 관련 대화
- [[2026-03-25-옵시디언-지식그래프]]

## 관련 개념
- [[옵시디언]]
```

### Project Document

```markdown
---
type: project
created: 2026-03-25
updated: 2026-03-25
status: active
---

# obsidian-brain

Claude Code 대화를 Obsidian에 자동 문서화하는 시스템.

## 대화 타임라인
- [[2026-03-25-옵시디언-지식그래프]] — 시스템 설계

## 핵심 결정사항
- Phase 1: Claude Code만, Python 파이프라인
- Phase 2: 다른 AI + Obsidian Plugin
```

## Data Flow

1. **SessionEnd hook 발동** → `transcript_path` 수신
2. **Parser** → `transcript.jsonl` 읽기 → 통합 JSON 변환
3. **Filter** → 메시지 3개 이하 스킵, 이미 처리된 세션 스킵
4. **Analyzer** → 기존 Vault 개념/프로젝트 목록 수집 → `claude -p` 호출
5. **Generator** → 대화 문서 생성 → 개념 문서 생성/업데이트 → 프로젝트 문서 연결
6. **기록** → 세션 ID를 `.processed`에 추가

## Recovery (터미널 강제 종료 대비)

- `SessionStart` hook에서 미처리 과거 대화 확인
- `~/.claude/projects/` 아래 `**/transcript.jsonl` 패턴으로 스캔
- 각 transcript의 부모 디렉토리명이 세션 ID
- `.processed`에 없는 세션이 있으면 처리
- 30일 이상 된 미처리 세션은 무시 (너무 오래된 건 의미 없음)
- 미처리 건이 3개 이상이면 백그라운드에서 순차 처리 (세션 시작 지연 방지)
- 최악의 경우에도 다음 대화 시작 시 자동 복구

## Tech Stack

- **Python 3.11+** — 파이프라인 코어
- **Claude Code CLI** (`claude -p`) — 대화 분석
- **watchdog** (Phase 2) — inbox 폴더 감시
- **YAML frontmatter** — Obsidian 메타데이터

## State & Config

모든 설정과 상태 파일은 Vault 내부 `.obsidian-brain/`에 통합 관리:

```
obsidian-vault/.obsidian-brain/
├── config.yaml       # 설정
├── .processed        # 처리 완료된 세션 ID 목록
├── .failed           # 실패한 세션 ID (재시도 대상)
└── logs/             # 실행 로그
    └── 2026-03-25.log
```

```yaml
# .obsidian-brain/config.yaml
vault_path: ~/ObsidianVault          # Obsidian Vault 경로 (자동 감지 가능)
min_messages: 3                       # 최소 메시지 수 (이하 스킵)
max_transcript_chars: 50000           # 이 이상이면 최근 100개 메시지만
max_retries: 3                        # claude -p 실패 시 재시도 횟수
folders:
  conversations: Conversations
  concepts: Concepts
  projects: Projects
```

## Future (Phase 2+)

- Telegram 봇 입력 채널
- ChatGPT/Gemini export 파서
- Obsidian Plugin (TypeScript) 포팅 — 커뮤니티 플러그인 배포
- 기존 개념 문서 내용 강화 (여러 대화에서 정보 병합)
- 그래프 성장 통계 대시보드
