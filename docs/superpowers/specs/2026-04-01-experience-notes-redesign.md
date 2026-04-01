# Experience Notes Redesign

## 문제 정의

현재 obsidian-brain의 Concept 문서는 사용자에게 가치가 없다:
- 이름이 LLM이 만든 추상적 조어 ("범용 modified_at 오염 패턴")
- 내용이 뻔하거나 추상적
- 인사이트 중복 반복
- 어떤 맥락에서 나온 건지 연결 안 됨
- 코드 품질 리뷰에서 8.94/10을 받았지만, 실제 사용 가치는 낮음

Conversation 문서의 "정리된 대화 기록" 가치는 있으나, 거기서 인사이트를 찾기는 어려움.

## 변경 사항

### 1. Concept 문서 → Experience Note (경험 노트)로 교체

**Concept 문서 폐기.** 대신 Experience Note 도입.

**위치:** `Experiences/{제목}.md`

**제목 규칙:**
- 대화에서 사용자가 실제로 쓴 표현을 최대한 활용
- 기술 중심이 자연스러우면 기술 중심 ("Django QuerySet 평가 시점 함정")
- 상황 중심이 자연스러우면 상황 중심 ("배포 직전 마이그레이션 충돌")
- LLM이 만든 조어 금지

**Frontmatter:**
```yaml
type: experience
cssclasses: [ob-experience]
created: {YYYY-MM-DD}
experience_type: {problem-solving | discovery | troubleshooting}
tags: [extracted tags]
conversations: [conversation slug]
projects: [project name]
```

**유연한 본문 구조 — 대화 성격에 맞는 타입 선택:**

문제 해결형 (problem-solving):
```markdown
## 상황
{구체적으로 어떤 문제를 만났는지}

## 선택
{어떤 접근을 택했고, 대안이 있었다면 왜 이걸 골랐는지}

## 교훈
{다음에 비슷한 상황에서 기억할 것}
```

발견형 (discovery):
```markdown
## 발견
{새로 알게 된 사실}

## 맥락
{어떤 상황에서 이걸 알게 됐고, 언제 유용한지}
```

삽질형 (troubleshooting):
```markdown
## 삽질
{뭘 했는데 안 됐는지}

## 원인
{왜 안 됐는지}

## 해결
{어떻게 고쳤는지}
```

LLM이 대화 내용을 보고 가장 자연스러운 타입을 선택. 섹션이 억지로 채워지면 안 됨 — 해당 내용이 대화에 실제로 있을 때만 작성.

### 2. 추출 로직 변경

**기존:** "재사용 가능한 크로스 프로젝트 지식 0-3개 추출"
**변경:** "이 대화에서 나중에 다시 찾아볼 만한 경험이 있는지 판단"

추출 기준:
- 실제 문제를 만나서 해결한 순간이 있는가?
- 시행착오가 있었는가?
- 새로 알게 된 것이 있는가?
- 단순 작업 수행 ("파일 만들어줘", "이거 고쳐줘")은 제외
- **없으면 experiences: [] 반환** — 강제 추출 안 함

Analyzer 프롬프트 변경:
```
기존: "재사용 가능한 크로스 프로젝트 지식만 추출해"
변경: "이 대화에서 사용자가 실제로 부딪힌 문제, 발견, 삽질이 있으면 알려줘. 없으면 없다고 해."
```

### 3. 누적 전략: 1대화 = 1노트

- 같은 주제로 여러 번 경험해도 각각 별도 경험 노트
- 합치지 않음 — 각각의 상황/맥락이 다름
- 관련 경험끼리는 태그 + 백링크로 연결
- 기존 concept의 insight 누적/삭제 로직 폐기

### 4. 필터링

숫자 기반 필터(메시지 수, 길이)는 기존 최소 기준 유지 (명백한 스팸 제거용).
실질적 필터링은 LLM 판단에 위임:
- analyzer가 대화 전문을 읽고 경험 노트 추출 가치를 판단
- 가치 없으면 experiences: [] → conversation doc만 생성

### 5. 피드백 루프

세션 시작 시 직전 세션의 경험 노트를 보여주고 피드백 수집:

```
[이전 세션 경험 노트]
📝 "Django QuerySet 평가 시점 함정"

유용했나요? (y/n/무시하면 스킵)
```

- y → 긍정 기록
- n → 사유 한 줄 입력 → 개선 참고
- 무응답 → 스킵

피드백 저장: `.obsidian-brain/feedback.jsonl`
```json
{"date": "2026-04-01", "note": "Django QuerySet 평가 시점 함정", "rating": "n", "reason": "너무 뻔한 내용"}
```

주기적으로 피드백 데이터를 analyzer 프롬프트 튜닝에 반영.

### 6. 기존 문서 유지 항목

| 문서 | 변경 |
|------|------|
| Conversation doc | 유지 — 정리된 대화 기록 가치 |
| Project doc | 유지 — 타임라인 + 결정사항 누적 |
| My Patterns.md | 유지, 경험 노트 기반으로 재작성 |
| Concept doc | **폐기** → Experience Note로 대체 |

### 7. CSS 변경

- `.ob-concept` → `.ob-experience` 로 교체
- experience_type별 시각적 구분 (색상 또는 아이콘)은 선택적

## 스코프 외

- Claude.ai / Cowork 대화 연동 — 데이터 포맷 확인 후 별도 작업
- 비개발자 대상 확장 — 입력 소스 확장 시 함께 고려
- Dataview 쿼리 템플릿 — 경험 노트 안정화 후 추가
