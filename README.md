# Mustafar Landing Platform — Blender 복원 프로젝트

영화 《Star Wars: Episode III – Revenge of the Sith》(2005)의 무스타파 착륙장을 Blender Python(bpy)으로 블록아웃하고,
ChatGPT 독립 검수 + 사용자 승인으로 고쳐 나가는 작업 저장소. 게임 저장소(Isometric-RPG)와 분리되어 있다.

> **2026-10-15부터 OpenAI API 유료 호출은 보류.** 검수는 아래 [ChatGPT 협업 절차](#chatgpt-협업-절차-github-반자동)대로
> GitHub 저장소의 Markdown 파일을 주고받는 방식으로 한다.

> **이 저장소는 비공개(private)로만 유지한다.** `refs/`의 영화 스틸은 저작권 자료로, 개인 참고용이다.

| 폴더 | 내용 |
|---|---|
| `refs/` | 참고 이미지: R1·R2·R3·R6 영화 스틸, R4·R5 다른 게임 재현 |
| `v0.1/` | 블록아웃 v0.1 (첫 시도, 직사각형 판) — 보존용 |
| `v0.2/` | 블록아웃 v0.2 (영화 스틸 카메라 맞춤 측정 반영) — 현재 기준 |
| `v0.2/work/` | R2 카메라 맞춤 측정 스크립트·결과(`r2_*.py`, `r2_*.json`) |
| `gpt_review_bridge/` | GPT API 검수 연동 모듈 — **보존·휴면** (삭제하지 않음, 실제 호출 안 함) |
| `chatgpt_reviews/` | ChatGPT 검수 라운드 (요청서·답변·수정 계획, Markdown) |

각 버전 폴더: `create_mustafar.py`(생성 스크립트), `dimensions.json`(치수·신뢰도), `.blend`, 렌더 PNG, `reference_analysis.md`.

복원·재실행 절차: **[RESTORE.md](RESTORE.md)**

---

## ChatGPT 협업 절차 (GitHub 반자동)

> 상태: **승인됨(2026-10-15)**. 첫 라운드는 기존 **v0.2**를 그대로 검수한다 → [`chatgpt_reviews/CR-001_v0.2/request.md`](chatgpt_reviews/CR-001_v0.2/request.md).
> v0.2 렌더는 이미 있는 파일 이름을 그대로 쓰고(보존 버전이라 이름을 바꾸지 않음), 아래 `renders/` 규칙은 v0.3부터 적용한다.

### 원칙

1. **유료 API 호출 없음.** `gpt_review_bridge/`는 지우지 않고 그대로 둔다. 그 안의 모의 시험
   (`tests/test_flow.py`)은 네트워크를 쓰지 않으므로 돌려도 된다. `review.py check`는 api.openai.com에 접속하므로
   실행하지 않는다(RESTORE.md 기본 절차에서 제외함).
   `run`, `list-models`도 실행하지 않는다.
2. **보존 대상은 수정하지 않는다:** `v0.1/`, `v0.2/`, 그리고 별도 저장소인 Isometric-RPG 게임.
3. **Blender 구조 변경은 사용자 승인 후에만 한다.** Claude Code는 계획만 쓰고, 승인된 항목만 **새 버전 폴더**에 적용한다.
4. **영화 원본 스틸(`refs/R1·R2·R3·R6`)은 이 비공개 저장소에만 둔다.** 공개 저장소, 공개 링크, gist, 이슈 첨부로 옮기지 않는다.
   검수 자료에도 경로로만 적는다(복사본을 만들지 않음).
   저장소를 공개로 바꾸려면 먼저 `refs/`를 히스토리에서 빼야 한다.

### 역할

| 누가 | 하는 일 |
|---|---|
| Claude Code | 새 버전 렌더, 검수 요청서(`request.md`) 작성, ChatGPT 답을 읽고 수정 계획(`plan.md`) 작성, 승인 항목 적용 |
| 사용자 | ChatGPT에 요청서 전달, 답을 `chatgpt_review.md`로 저장, `plan.md`에서 항목마다 승인·거절·보류 |
| ChatGPT | 요청서와 렌더·참고 이미지를 보고 정해진 형식의 Markdown으로 검수 결과 작성 |

### 폴더 구조 (예정)

```
v0.3/                              ← 승인 항목을 적용한 새 버전 (v0.2 사본에서 시작)
  create_mustafar.py, dimensions.json, *.blend, reference_analysis.md
  renders/                         ← 검수용 렌더. 파일 이름 고정, 번호 순으로 보면 됨
    01_compare_R2.png              ← 영화 스틸과 같은 카메라 각도로 나란히 비교 (가장 중요)
    02_compare_R6.png
    03_perspective.png
    04_top.png                     ← 치수 격자 표시
    05_isometric.png
  RENDERS.md                       ← 렌더마다 카메라·조명·해상도, 무엇을 보면 되는지 한 줄씩
  CHANGES.md                       ← 이전 버전 대비 바뀐 점 (적용한 plan 항목 ID 목록)

chatgpt_reviews/
  CR-001_v0.2/                     ← 검수 라운드 1회 = 폴더 1개 (첫 라운드는 v0.2)
    request.md                     ← Claude 작성: 검수 대상 커밋, 볼 이미지 경로, 질문(영화 고증 A / 게임 구현 B), 답변 형식
    images.md                      ← Claude 작성: 이미지 목록, 카메라 방향, 영화↔렌더 대응([확인]/[추정]/[미확인])
    extra_views_proposal.md        ← Claude 작성: 추가 카메라 시점 제안(렌더는 승인 후)
    chatgpt_review.md              ← 사용자가 저장: ChatGPT 답 원문 (수정하지 않음)
    plan.md                        ← Claude 작성: 수정 계획 + 사용자 결정 칸
  TEMPLATE_review.md               ← ChatGPT 답변 형식 (request.md에도 붙여 넣음)
```

- 렌더는 버전 폴더에 한 번만 둔다. 검수 폴더는 Markdown만 담고 이미지를 상대경로로 가리킨다(중복 없음).
- 렌더 PNG는 긴 변 1536 px 이하로 저장한다. 웹 화면에서 바로 보이고 저장소 용량도 아낀다.

### 한 라운드 순서

1. **렌더·요청** (Claude Code): 새 버전 폴더에서 렌더한다. `RENDERS.md`, `CHANGES.md`, `request.md`를 쓰고
   작업 브랜치에 커밋·푸시한다. 요청서 맨 위에 **커밋 SHA**를 적어, ChatGPT가 같은 시점의 파일을 보게 한다.
2. **전달** (사용자 → ChatGPT): ChatGPT에서 GitHub 연결로 이 비공개 저장소를 읽게 하고
   `chatgpt_reviews/CR-NNN_*/request.md`를 검수하라고 요청한다. 이미지를 읽지 못하면 `request.md`에 적힌 PNG를
   내려받아 직접 첨부한다(영화 스틸은 이 저장소에서 바로 첨부하고, 다른 곳에 올리지 않는다).
3. **답 저장** (사용자): ChatGPT의 답을 그대로 `chatgpt_review.md`로 저장한다.
   GitHub 웹에서 직접 커밋해도 되고, Claude Code 채팅에 붙여 넣고 "저장해 줘"라고 해도 된다.
4. **계획** (Claude Code): `chatgpt_review.md`를 읽고 `plan.md`를 쓴다. 블록아웃 파일은 이 단계에서 건드리지 않는다.
   항목마다 다음을 적는다.
   - ChatGPT 지적 ID
   - 바꿀 파일·치수
   - 예상 영향
   - Claude 의견(동의/이견, 근거)
   - 권고(승인/거절/보류)

   근거가 약하거나 신뢰도가 UNKNOWN인 항목은 '보류'로 권고한다.
5. **결정** (사용자): `plan.md`의 결정 칸에 `승인` / `거절` / `보류`를 적는다(채팅으로 알려 줘도 된다).
6. **적용** (Claude Code): 승인 항목만 다음 버전 폴더(예: `v0.4/`)에 적용하고 다시 1로 돌아간다.
   거절된 항목은 `CHANGES.md`에 "거절"로 남겨, 다음 라운드에 같은 지적이 되풀이되지 않게 한다.

### ChatGPT 답변 형식

[`chatgpt_reviews/TEMPLATE_review.md`](chatgpt_reviews/TEMPLATE_review.md)를 따른다.
- 영화 고증은 **A01…**, 게임 구현은 **B01…**로 나눠 적는다.
- 지적마다 대상, 근거, 제안, 신뢰도(또는 고증과의 관계)를 고정 항목 이름으로 적는다.
- 그래서 Claude Code가 답을 항목별로 빠짐없이 계획에 옮길 수 있다.
- 형식이 어긋나면 Claude Code가 `plan.md` 맨 위에 무엇이 빠졌는지 적고, 추측으로 채우지 않는다.
