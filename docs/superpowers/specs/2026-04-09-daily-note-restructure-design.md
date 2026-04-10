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
| project-a | backend, schema, delta-svc, manage, script, epsilon-svc, zeta-svc, gamma | example platform |
| project-b | project-b-agent | agent pipeline |
| project-c | — | spec management tool |
| personal | obsidian-brain, eta-scout, theta-todo, practice, my-bot | personal/side projects |

매칭 안 되는 세션은 프로젝트 없이 Daily에만 기록 (`## 기타`).

## Analyzer 스키마 변경

기존 `summary` + `projects` → 프로젝트별 분리된 출력 추가.

```json
{
  "summary": "전체 요약 (1-3문장)",
  "daily_entries": [
    {
      "project": "project-a",
      "bullets": [
        "feature-x scoring refactor — reweight to normalize input bias",
        "Celery 태스크 타임아웃 해결 — retry 3회 후 dead letter queue로 전환"
      ]
    }
  ],
  "experiences": [],
  "decisions": [],
  "tags": []
}
```

`daily_entries`는 프로젝트별로 그날 뭘 했는지 bullet 단위로 정리.
한 세션이 여러 프로젝트에 걸치면 각각 별도 entry.
프로젝트 매칭 안 되면 `"project": null`.

## 출력 구조

### 1. Daily Note

**경로:** `Daily/{date}.md` (예: `Daily/2026-04-09.md`)

같은 날 여러 세션 → 하나의 파일에 append. 이미 있는 프로젝트 섹션에 추가.

```markdown
---
date: 2026-04-09
projects: [project-a, personal]
tags: [django, celery, dedup]
---

## [[project-a]]
- feature-x scoring refactor
  - 기존 가중치가 deal size를 과대평가 → 균등 배분으로 변경
- Celery 태스크 타임아웃 해결
  - retry 3회 후 dead letter queue로 전환

## [[personal]]
- obsidian-brain: daily note 구조로 전환 설계
  - Conversations + Experiences 폴더 대체
```

**Append 로직:**
1. `Daily/{date}.md` 존재 확인
2. 없으면 → frontmatter + 새 내용으로 생성
3. 있으면:
   - frontmatter 로드 → `projects`, `tags` 리스트 merge (중복 제거)
   - 각 daily_entry에 대해:
     - 해당 `## [[project]]` 섹션이 이미 있으면 → 섹션 끝에 bullet 추가
     - 없으면 → 파일 끝에 새 섹션 추가
   - project가 null인 entry → `## 기타` 섹션에 추가

### 2. Projects

기존 대화 링크 나열 → 프로젝트 레벨 누적 문서로 강화.

```markdown
---
title: project-a
status: active
updated: 2026-04-09
---

## 개요
example platform — backend, frontend, infra

## 아키텍처
- Django + DRF, Celery, PostgreSQL
- AWS 인프라 (WAF, ECS)

## 핵심 결정
- 2026-03-05: UUID PK 전환 결정 → 전체 스택 연쇄 수정 필요했음
- 2026-04-01: feature-x weighting normalized

## 최근 작업
- [[2026-04-09]] feature-x refactor, background task timeout fix
- [[2026-04-08]] WAF 룰 업데이트
```

**업데이트 방식 (LLM 호출 없이 코드로):**
- "최근 작업"에 `[[{date}]] {summary}` append
- "핵심 결정"에 `{date}: {decision}` append (중복 체크)
- "개요", "아키텍처"는 수동 관리 (자동 수정 안 함)
- `updated` frontmatter 갱신

**초기 생성:** 첫 실행 시 프로젝트 문서가 없으면 기본 템플릿으로 자동 생성.

### 3. Experiences

구조 유지, 중복 방지 강화.

변경:
- analyzer 프롬프트에 **기존 경험 제목 목록 전체** 전달 (~148개 * 30자 ≈ 4400자, 부담 없음)
- "이미 있는 경험과 같은 내용이면 만들지 마" 명시
- 코드 검증: `is_similar_experience` threshold 0.5 → 0.6

## 프로젝트 분류 로직 (접근법 B)

### 프롬프트 강화
- 4개 프로젝트 + 설명 + aliases를 config에서 읽어서 analyzer 프롬프트에 전달
- "이 중에서만 골라, 안 맞으면 null" 지시

### 코드 검증 (분석 결과 후처리)
1. 정확히 일치 → 통과
2. aliases에 있음 → 매핑 (예: "backend" → "project-a")
3. 둘 다 아님 → fuzzy match 시도 (difflib), 0.7 이상이면 매핑
4. 전부 아님 → null (프로젝트 없음, `## 기타`로)

## 변경 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `config.py` | projects를 aliases/description 포함 dict로 변경, daily 폴더 추가 |
| `analyzer.py` | 스키마에 `daily_entries` 추가, 프롬프트에 프로젝트 설명 + 경험 목록 |
| `pipeline.py` | Daily note 생성/append, 프로젝트 후처리 매핑, 경험 목록 전달 |
| `generator.py` | `generate_daily_doc()` 신규, `append_daily_doc()` 신규, `generate_project_doc()` 템플릿 변경, `update_project_doc()` 새 포맷 |
| `filter.py` | experience threshold 0.5 → 0.6 |
| `vault.py` | `scan_experiences()` 추가 |

## 삭제 대상

- `generate_conversation_doc()` — Daily가 대체
- `is_similar_conversation()` — Daily는 날짜별 1개라 중복 체크 불필요

## 기존 데이터 처리

기존 Conversations, Experiences, Projects 폴더는 수동 정리 (이번 스코프 밖).
새 세션부터 새 구조 적용.
