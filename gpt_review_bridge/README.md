# Mustafar GPT Review Bridge

Claude Code가 Blender로 만든 무스타파 착륙장 블록아웃을 **OpenAI GPT가 영화 스틸과 비교해 독립 검수**하고,
**사용자가 승인한 수정만** Claude Code가 새 버전에 적용하는 반자동 흐름이다.

```
prepare_images.py ─▶ review.py estimate ─▶ (사용자: 모델·비용 승인) ─▶ review.py run --confirm
        │                                                                     │
        ▼                                                                     ▼
 reviews/<id>/ 입력 묶음                                           review.json + report_ko.md
                                                                              │
             approval.py plan → note(Claude 계획) → finalize → (사용자: 승인/거절/보류) → decide
                                                                              │
                                              approval.py new-version → 새 버전 폴더에서만 수정
```

기존 Blender 코드(`../v0.2/`)와 게임 코드는 바꾸지 않는다. 이 폴더는 독립 모듈이다.

## 파일

| 파일 | 역할 |
|---|---|
| `review.py` | OpenAI Responses API 검수 요청 (`check` · `list-models` · `estimate` · `run` · `report`) |
| `review_schema.json` | 검수 결과 JSON 형식 (Structured Outputs strict) — object_id, issue, evidence_image, observation, confidence, proposed_change, requires_more_reference |
| `prepare_images.py` | 입력 이미지 검증(형식·크기·용량·장수·역할)·축소, 치수 JSON·확정 구조 정보 묶기, 보호 파일 해시 기록 |
| `approval.py` | 수정 계획 → 사용자 결정 → 새 버전 (`plan` · `note` · `finalize` · `decide` · `status` · `guard` · `new-version` · `applied`) |
| `bridge_common.py` | 설정 읽기, 키 가리기(redact), 해시 |
| `config.json` | 모델, 가격, 이미지 한도, 호출 제한, 보호 파일 목록 |
| `inputs/` | 검수 입력 목록 (`001_connection_test.json` = 이미지 2장, `002_landing_full.json` = 전체) |
| `annotations/` | 사용자가 표시한 격납고·통로 입구 주석 이미지를 넣는 곳 |
| `mock/mock_review_output.json` | 모의 GPT 응답 (흐름 시험용, 모든 문장에 [모의] 표시) |
| `tests/test_flow.py` | API 호출 없는 전체 흐름 시험 (샌드박스에서 실행, 실제 파일 무변경) |
| `reviews/<id>/` | 검수마다 생기는 폴더 (입력, 견적, 응답, 보고서, 계획, 결정) |
| `costs.jsonl` | 호출별 토큰 사용량·비용 기록 (모의·실패 포함) — **저장소에 올리지 않음** |
| `confirmed_structures.json` | 승인·거절된 구조 — 다음 검수 입력에 자동 포함 (저장소에 보관) |

## 설치

저장소 루트에서 (자세한 복원 절차는 `../RESTORE.md`):
```bash
uv venv -p 3.13 .venv-bridge
VIRTUAL_ENV=$PWD/.venv-bridge uv pip install -r gpt_review_bridge/requirements.txt
```

## 비밀정보 — OPENAI_API_KEY

- 키는 **`OPENAI_API_KEY` 환경변수로만** 읽는다. 소스·설정·로그·결과 파일·GitHub에 쓰지 않는다
  (모든 출력은 `redact()`를 거치며, 시험에서 가짜 키가 어떤 파일에도 남지 않는 것을 확인).
- 등록: Claude 앱 세션 제목 표시줄의 클라우드 환경 메뉴 → **Edit** → *Network secrets*(앱이 오래됐으면 *API credentials*)
  또는 환경 변수에 `OPENAI_API_KEY`로 추가. **새 세션부터** 적용된다.
- 키를 채팅에 붙여 넣지 않는다.

## 네트워크

- 이 환경의 기본 네트워크 정책은 `api.openai.com`을 막는다(프록시 403 — `review.py check`로 확인).
- 허용: 같은 환경 설정의 *Network access*에서 Allowed domains에 `api.openai.com` 추가
  (*Allow package managers*는 켠 채로). https://code.claude.com/docs/en/cloud-environments#network-access
- 허용 목록 변경은 사용자 승인 사항이다. 차단되면 `run`은 재시도 없이 멈추고 `error.json`에 원인을 남긴다.

## 실행 단계

1. **환경 확인** — `python review.py check` (키 등록 여부, SDK, 모델·가격 설정, api.openai.com 연결. 과금 없음)
2. **모의 흐름 시험** — `python tests/test_flow.py` (API 호출 없음)
3. **연결 테스트** (사용자 승인 후, 이미지 2장, 1회)
   ```bash
   python review.py list-models                        # 무료: 계정에서 쓸 수 있는 모델 확인
   # config.json에 model, pricing(공식 가격·확인 날짜) 기입
   python prepare_images.py inputs/001_connection_test.json
   python review.py estimate 001_connection_test        # 모델·예상 토큰·예상 비용·승인 지문 출력
   # → 사용자에게 모델과 예상 비용을 보여 주고 승인받음
   python review.py run 001_connection_test --confirm <지문>
   ```
4. **전체 검수** — `annotations/hangar_entrance.png`(사용자 주석)를 넣고 `inputs/002_landing_full.json`으로 같은 순서.

## 승인 흐름

```bash
python approval.py plan <검수>                                   # GPT 지적 → 계획 초안 (모델 파일 무변경)
python approval.py note <검수> F01 --summary "..." [--recommend 보류]   # Claude가 항목별 수정 계획 작성
python approval.py finalize <검수>                               # plan_ko.md: 항목마다 ☐ 승인 ☐ 거절 ☐ 보류
python approval.py decide <검수> F01=승인 F02=거절 F03=보류 --source "사용자, 채팅 답변"
python approval.py guard <검수>                                  # 검수 이후 .blend·스크립트·dimensions.json 무변경 확인
python approval.py new-version <검수> --to v0.3                  # 승인 항목이 있을 때만, v0.2 복사 → v0.3
#   (Claude가 v0.3 안에서 승인 항목만 수정·재렌더)
python approval.py applied <검수> F01 --version v0.3
```

- 결정은 계획 지문에 묶인다: 확정 뒤 계획이 바뀌면 `decide`를 거부한다.
- 거절·보류·미결정 항목은 새 버전에 넣지 않는다. 이미 있는 버전 폴더는 덮어쓰지 않는다.
- 승인·거절 결과는 `confirmed_structures.json`에 쌓여 다음 검수 입력에 들어간다(거절된 제안을 같은 근거로 반복하지 않게).

## 비용·실행 제한

- 실제 호출은 `estimate`가 낸 **승인 지문**(`--confirm`)이 맞아야만 한다. 입력·설정이 바뀌면 지문이 달라져 다시 견적.
- 모델이나 가격이 비어 있으면 호출하지 않는다. 검수(`reviews/<id>`)당 **1회** — 실패해도 같은 검수로 다시 부르지 않는다.
- SDK `max_retries=0` (자동 재시도 없음). 자동 반복 수정 없음.
- 연결 테스트(`mode: connection_test`)는 이미지 2장까지만 허용.
- 호출마다 `costs.jsonl`에 사용량(입력·출력·캐시·추론 토큰)과 `config.json` 가격 기준 비용을 기록한다.
  실제 청구액은 OpenAI 플랫폼의 Usage 페이지가 기준이다.
- **월별 비용 한도는 OpenAI 플랫폼의 결제·사용 한도 설정에서 따로 정한다** (이 도구는 한도를 관리하지 않음).
- 이미지 토큰 추정(`config.json image_tokens`)은 모델마다 계산법이 달라 근사치다.

## 개인정보·저작물

- 영화 스틸과 렌더 이미지가 OpenAI로 전송된다. `store_responses_on_openai: false`로 응답 저장을 요청하지 않는다
  (데이터 보존 정책은 OpenAI 계정 설정을 따름).
- 업로드 전 이미지는 다시 저장되어 EXIF 등 메타데이터가 제거된다.

## 검수 원칙 (GPT 지시문 `review.py INSTRUCTIONS`)

근거 우선순위 영화 원본 > 사용자 주석 > 다른 게임. Blender 렌더는 검수 대상. 사용자 주석은 공간의 기능·의도 설명이며
치수의 근거가 아니다. 영화에서 보이지 않는 구조·검증되지 않은 수치를 확정하지 않는다. 미적 디테일은 다루지 않는다.
