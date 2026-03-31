# Obsidian Brain

Claude Code 대화를 자동으로 분석해서 Obsidian Vault에 구조화된 문서로 저장하는 도구.

단순 기록이 아니라 **의사결정 패턴, 판단 기준, 선호/원칙**을 추출해서 "나를 대체할 수 있는 지식 베이스"를 만드는 것이 목표.

## 작동 방식

```
Claude Code 세션 종료
  → SessionEnd 훅 (async, 비동기)
    → transcript 파싱
      → 필터링 (처리할 가치가 있는 대화인지)
        → 유사 대화 중복 체크
          → claude -p로 AI 분석
            → Obsidian Vault에 MD 파일 생성

매일 첫 세션 시작 시
  → SessionStart 훅
    → 미처리 세션 복구 (배치 제한)
    → Daily Digest: My Patterns.md 업데이트
```

## 생성되는 문서 4종류

### 1. Conversations (대화 기록)

`Conversations/YYYY-MM/YYYY-MM-DD-{slug}.md`

세션 하나당 하나의 문서. 내용이 있는 섹션만 렌더링:

| 섹션 | 설명 |
|------|------|
| 요약 | 1~3문장 대화 요약 |
| 의사결정 패턴 | 상황 → 선택 → 이유 (왜 그렇게 했는지) |
| 드러난 선호/원칙 | 행동에서 추론한 성향 (예: "자동화 선호", "안전장치 중시") |
| 핵심 결정사항 | 내린 결정 목록 |
| 관련 개념 | `[[개념]]` 링크 |
| 관련 프로젝트 | `[[프로젝트]]` 링크 |

### 2. Concepts (개념)

`Concepts/{개념명}.md`

**추출 기준:** "다른 프로젝트에서도 재사용할 수 있는 지식인가?"
- 시스템/아키텍처/설계 수준의 핵심 개념만 (대화당 0~3개)
- 일회성 버그, 특정 함수명, 사소한 패턴은 제외
- 유사 인사이트 자동 중복 제거 (SequenceMatcher + Jaccard 이중 체크)
- 개념당 인사이트 최대 10개 유지 (초과 시 오래된 것 삭제)

### 3. Projects (프로젝트)

`Projects/{프로젝트명}.md`

프로젝트별 대화 타임라인 + 누적 결정사항.

### 4. My Patterns (일일 종합)

`My Patterns.md` (vault 루트)

매일 첫 세션 시작 시 자동 생성/업데이트. 최근 대화들을 종합 분석:

| 섹션 | 설명 |
|------|------|
| 핵심 원칙/성향 | strong (반복 확인) / emerging (1~2회 관찰) |
| 반복되는 의사결정 패턴 | "이 사람은 X 상황에서 항상 Y를 선택한다" |
| 변화/성장 | 이전 대비 새로 나타난 성향이나 변화 |

수동 실행: `obsidian-brain digest --vault-path "<vault>" [--force]`

## 처리 기준 (필터링)

| 조건 | 기본값 | 설명 |
|------|--------|------|
| 사용자 메시지 수 | > 3개 | 간단한 질문 세션은 건너뜀 |
| 평균 메시지 길이 | >= 10자 | 너무 짧은 메시지만 있는 세션은 건너뜀 |
| 유사 대화 | threshold 0.6 | 같은 날짜에 비슷한 대화가 있으면 건너뜀 |
| 미처리 세션 | - | 이미 처리되거나 실패(3회)한 세션은 건너뜀 |
| 배치 제한 | 10개/회 | Recovery 시 한 번에 최대 10개만 처리 |

긴 대화는 앞 15개 + 뒤 85개 메시지만 사용 (최대 50,000자). 설정 변경 가능.

## 설치

### 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [jq](https://jqlang.github.io/jq/) (설치 스크립트용)
- Obsidian Vault (로컬)
- [Dataview 플러그인](https://github.com/blacksmithgu/obsidian-dataview) (대시보드용, 권장)

### 설치 방법

```bash
git clone <repo-url>
cd obsidian-brain
uv sync
bash scripts/install-hooks.sh
```

스크립트가 자동으로:
1. Vault 경로 입력 받기
2. `.obsidian-brain/` 디렉토리 + 기본 config 생성
3. `Conversations/`, `Concepts/`, `Projects/` 폴더 생성
4. `~/.claude/settings.json`에 hooks 자동 병합 (기존 hooks 있으면 백업)
5. CSS snippet 설치 (문서 타입별 컬러 코딩)
6. Brain Dashboard 생성 (Dataview 기반)

설치 후 Obsidian에서 **설정 → 외모 → CSS snippets → obsidian-brain 활성화** 필요.

### 설정 (`config.yaml`)

`<vault>/.obsidian-brain/config.yaml`

```yaml
vault_path: /path/to/vault
min_messages: 3              # 사용자 메시지 이 이하면 건너뜀
max_transcript_chars: 50000  # 대화 최대 길이
max_retries: 3               # 분석 실패 시 재시도 횟수
processed_retention_days: 30 # 복구/다이제스트 대상 기간
model: sonnet                # 분석에 사용할 Claude 모델
batch_limit: 10              # Recovery 배치 크기
rate_limit_seconds: 2        # 세션 간 대기 시간
max_insights: 10             # 개념당 인사이트 최대 개수
similarity_threshold: 0.5    # 인사이트 유사도 판단 임계값 (0~1)
truncate_head: 15            # 긴 대화 앞부분 메시지 수
truncate_tail: 85            # 긴 대화 뒷부분 메시지 수
folders:
  conversations: Conversations
  concepts: Concepts
  projects: Projects
```

## CLI 명령어

```bash
# 단일 세션 처리
obsidian-brain process --session-id <id> --cwd <dir> --vault-path <vault>

# 미처리 세션 복구 + 일일 다이제스트
obsidian-brain recover --vault-path <vault>

# 일일 다이제스트 수동 실행
obsidian-brain digest --vault-path <vault> [--force]

# 처리 현황 확인
obsidian-brain status --vault-path <vault>
```

## Obsidian 연동

### CSS 스타일

설치 시 자동으로 CSS snippet이 추가됩니다. 문서 타입별 색상:

| 타입 | 색상 | cssclass |
|------|------|----------|
| Conversation | 파랑 | `ob-conversation` |
| Concept | 초록 | `ob-concept` |
| Project | 주황 | `ob-project` |
| Digest | 보라 | `ob-digest` |

다크/라이트 모드 모두 호환 (Obsidian CSS variable 사용).

### Dashboard

`Brain Dashboard.md`에 Dataview 쿼리 5종 포함:
- 최근 대화 10개
- 프로젝트별 대화 수
- 최근 업데이트된 개념
- 이번 주 대화
- 태그별 대화 수

## 상태 확인

```bash
obsidian-brain status --vault-path "<vault>"
```

## 에러 확인

```bash
# 오늘 로그
cat "<vault>/.obsidian-brain/logs/$(date +%Y-%m-%d).log"

# 실패한 세션 목록
cat "<vault>/.obsidian-brain/.failed"
```

## 마이그레이션

기존 문서를 최신 포맷으로 업데이트:

```bash
bash scripts/migrate-docs.sh [vault-path]
```

수행 내용:
- `type` frontmatter 추가
- `cssclasses` 추가 (Conversation, Concept, Project, Digest 모두)
- `None` 텍스트 제거
- 빈 섹션 제거
- 인사이트 중복 정리 + 최대 개수 제한
- 연속 빈 줄 정리

## 훅 동작

| 이벤트 | 실행 | 설명 |
|--------|------|------|
| SessionEnd | `process` | 방금 끝난 세션을 분석하고 문서 생성 |
| SessionStart | `recover` | 미처리 세션 복구 (배치 제한) + Daily Digest |

모든 훅은 `async: true`로 백그라운드 실행 — Claude 세션을 블로킹하지 않음.
세션 간 rate limiting 적용 (기본 2초).
