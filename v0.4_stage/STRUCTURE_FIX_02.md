# 구조 수정 2차 — A3d (2026-10-16)

이번 수정의 출처는 사용자 팩 `MUSTAFAR_STRUCTURE_FIX_02`다(README·CLAUDE_TASK, 영화 78862·78853·78855·78837, 사용자 표시 01~04).
- **배치 이름**: A3d(작업 사본). 기준(수정 전)은 A3c(`current/78845.png`)이고, A3c와 A3b는 그대로 보존했다.
- **값의 성격**: 모든 치수는 형태용 후보이며 영화 고증으로 확정한 것이 아니다.
- **팩 이미지**: 영화 이미지는 비공개 폴더(`research/CR-001_4k_evidence/_private/`)에만 두었고 커밋하지 않았다.

## 무엇을 바꿨나
| 파일 | 내용 |
|---|---|
| `v0.3/dimensions.json` | 후보 `A3d` 추가(A3c 값을 복사한 뒤 새 항목 추가) |
| `v0.3/create_mustafar.py` | A3d 깃발이 있을 때만 도는 코드 추가. A3c를 다시 생성해 객체·정점이 바이트 단위로 같음을 확인 |
| `v0.4_stage/stage_config.json` | A3d용. A3c 설정은 `stage_config_A3c.json`, 출력은 `out/mustafar_landing_A3c/`로 보존 |
| `v0.4_stage/build_stage.py` | 새 객체의 재질·베벨, 베이 채움 빛 3개(약하게) |
| `game_test/play_test.js` | 키로 문을 곧게 드나드는 확인, 이른 종료 확인 추가 |

(작성 중: 게임 적용·출입 검증 결과와 적용·보류 목록은 검증 후 채운다)
