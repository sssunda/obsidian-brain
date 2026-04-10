# obsidian-brain 작업 가이드

## 이건 오픈소스 툴이다 — 개인/회사 이름을 코드에 박지 마라

`obsidian-brain`은 다른 사람들도 쓸 수 있는 범용 도구다. 특정 사용자의 회사명, 제품명, 내부 프로젝트명, 업무 내용, 동료·고객 이름은 **소스코드, 테스트, 기본값, 문서, 커밋 메시지, 픽스처 파일명 어디에도** 하드코딩하지 않는다.

**유일하게 허용되는 위치:**

사용자 vault의 `.obsidian-brain/config.yaml` — 이건 사용자 개인 파일이라 레포 밖이다. 특정 프로젝트명·alias·설명은 오직 여기에만 있어야 한다.

**올바른 예시 작성법:**

- 프로젝트 이름 예시는 중립 placeholder로: `project-a`, `project-b`, `alpha`, `beta`, `gamma`, `acme`, `my-project`, `Example Corp`
- 사용자 이름 예시: `me`, `user`
- 경로 예시: `/path/to/vault`, `/path/to/obsidian-brain`, `~/.claude/projects/-path-to-work`
- 업무 내용 예시: `feature-x refactor`, `background task timeout fix`, `query optimization` (특정 도메인 용어 금지)
- fixture 파일 이름도 중립으로: `Projects/alpha.md`, `Projects/theta-todo.md`

**왜:**

- 실제 회사·프로젝트명이 레포에 박히면 사용자의 업무 비밀·프라이버시가 git 히스토리에 영구 기록된다.
- 다른 사용자·기여자가 레포를 보면 "이거 특정 회사 전용인가?" 오해한다.
- fork 했을 때 해당 이름들을 전부 찾아 바꿔야 하는 번거로움이 생긴다.
- 한 번 섞이기 시작하면 테스트·문서·기본값에 기하급수적으로 퍼진다. 초기에 막는 게 핵심.

**코드 변경 시 체크리스트:**

1. 새 테스트/fixture에 실제 사람·회사·프로젝트 이름이 들어갔는가? → 중립 placeholder로 교체.
2. `src/obsidian_brain/config.py`의 `DEFAULT_CONFIG`나 다른 소스의 하드코딩된 예시에 특정 이름이 섞였는가?
3. 문서(README, spec, plan, CLAUDE.md 자기 자신 포함)에 실제 경로·이름·업무 내용이 있는가?
4. 커밋 메시지가 특정 업무 컨텍스트를 드러내지 않는가? → 일반화된 기능 설명으로.
5. 픽스처 파일명 자체(`Projects/realname.md`) 도 중립으로.

**커밋 직전 셀프체크 (zsh):**

```zsh
# 리포 전체에서 본인이 아는 회사/프로젝트/동료/업무 용어를 찾아본다.
# 패턴은 각자 환경에 맞춰 조정 — 여기엔 예시로 아무 이름도 박지 않는다.
grep -rniE "your-internal-name-here" src tests docs
```

이 규칙은 사용자가 명시적으로 지적한 뒤 2026-04-10에 도입됐고, 전체 레포에서 기존 오염을 일괄 sanitize 했다. 앞으로는 애초에 섞이지 않도록 한다.
