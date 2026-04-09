# Daily Note 구조 전환 + 프로젝트/경험 분류 강화

## 배경

현재 obsidian-brain은 세션당 conversation 1개 + experience N개 + project 업데이트를 생성한다.
결과:
- 프로젝트 21개 (실제 4개), 디렉토리명이 그대로 프로젝트가 됨
- 경험 노트 148개 중 15-20개 중복 (UUID PK 5개, schema 8개 등)
- "뭘 했지?" 검색 불가

## 확정된 프로젝트 목록 (4개)

| 프로젝트 | aliases | 설명 |
|----------|---------|------|
| wishket | backend, schema, yozmit, manage, script, slock, prdesign, mapletech | 위시켓 플랫폼 전체 |
| wishos | wishos-agent | WishOS AI 에이전트 시스템 |
| prd-manage | — | PRD 관리 도구 |
| daeun | obsidian-brain, matjip-scout, pomodoro-todo, practice, daeunBot | 개인/사이드 프로젝트 |

매칭 안 되는 세션은 프로젝트 없이 Daily에만 기록.

## 출력 구조

### 1. Daily Note

**경로:** `Daily/2026-04-09.md`

같은 날 여러 세션 → 하나의 파일에 append. 이미 있는 프로젝트 섹션에 추가.

```markdown
---
date: 2026-04-09
projects: [wishket, daeun]
tags: [django, celery, dedup]
---

## [[wishket]]
- Lead Scoring v3 점수 기준 리팩토링
  - 기존 가중치가 deal size를 과대평가 → 균등 배분으로 변경
- Celery 태스크 타임아웃 해결
  - retry 3회 후 dead letter queue로 전환

## [[daeun]]
- obsidian-brain: daily note 구조로 전환 설계
  - Conversations + Experiences 폴더 대체
```

규칙:
- 프로젝트 매칭 안 된 세션 → `## 기타`
- 한 세션이 여러 프로젝트에 걸치면 각 섹션에 분배
- Conversations 폴더 대체

### 2. Projects

기존 대화 링크 나열 → 프로젝트 레벨 누적 문서로 강화.

```markdown
---
title: wishket
status: active
updated: 2026-04-09
---

## 개요
위시켓 플랫폼 — Django 백엔드, 프론트엔드, 인프라

## 아키텍처
- Django + DRF, Celery, PostgreSQL
- AWS 인프라 (WAF, ECS)

## 핵심 결정
- 2026-03-05: UUID PK 전환 결정 → 전체 스택 연쇄 수정 필요했음
- 2026-04-01: Lead Scoring v3 가중치 균등 배분으로 변경

## 최근 작업
- [[2026-04-09]] Lead Scoring 리팩토링, Celery 타임아웃 해결
- [[2026-04-08]] WAF 룰 업데이트
```

업데이트 방식:
- 세션 처리 시 해당 프로젝트 문서를 읽어서 LLM에 넘김
- "핵심 결정", "최근 작업"에 새 내용 추가
- "아키텍처"는 변경사항 있을 때만 업데이트

### 3. Experiences

구조 유지, 중복 방지 강화.

변경:
- analyzer 프롬프트에 기존 경험 제목 목록 전달
- "이미 있는 경험과 같은 내용이면 만들지 마" 명시
- 코드 검증: `is_similar_experience` threshold 0.5 → 0.6

## 프로젝트 분류 로직 (접근법 B)

### 프롬프트 강화
- 4개 프로젝트 + 설명 + aliases를 analyzer 프롬프트에 전달
- "이 중에서만 골라, 안 맞으면 빈 배열" 지시

### 코드 검증 (분석 결과 후처리)
1. 정확히 일치 → 통과
2. aliases에 있음 → 매핑 (예: "backend" → "wishket")
3. 둘 다 아님 → fuzzy match 시도 (difflib), 안 되면 제외

## 변경 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `config.py` | projects를 aliases/description 포함 dict로 변경, daily 폴더 추가 |
| `analyzer.py` | 프롬프트에 프로젝트 설명 + 기존 경험 목록 추가 |
| `pipeline.py` | Daily note append 로직, 프로젝트 후처리 매핑, 경험 목록 전달 |
| `generator.py` | Daily note 생성/append, Projects 누적 업데이트 |
| `filter.py` | experience threshold 조정 |
| `vault.py` | scan_experiences() 추가, Daily 폴더 스캔 |

## 기존 데이터 처리

기존 Conversations, Experiences, Projects 폴더는 수동 정리 (이번 스코프 밖).
새 세션부터 새 구조 적용.
