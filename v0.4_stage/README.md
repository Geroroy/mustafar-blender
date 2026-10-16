# v0.4_stage — 무스타파 착륙장 플레이용 스테이지

**목표**: 착륙장 하나를 실제로 플레이할 수 있는 스테이지로 만든다.

- **기준 배치**: A3b. 임시 작업 기준이며 영화 고증 확정이 아니다.
- **비교용 보존**: A3, H1(`v0.3/work/layouts/`).
- **치수 탐색**: 중단했고 현재 후보값으로 제작한다.
- **실내**: 확장을 중단했다. 블록아웃 파일(`v0.3/interior/`)은 그대로 보존한다.

## 파일
| 파일 | 내용 |
|---|---|
| `build_stage.py` | A3b 열기 → 가설 숨김 → 재질·조명 → 게임 출력·영화 비교 카메라 분리 → `mustafar_landing_stage.blend` |
| `stage_cam.py` | 게임 투영 카메라·좌표 변환(공용) |
| `stage_config.json` | 좌표 원점, 가림 물체, 충돌 규칙, 시작·출구·전투 자리 |
| `export_stage.py` | 배경·가림 조각·충돌 마스크·`stage.json` 내보내기 → `out/mustafar_landing/` |
| `compose_check.py` | 내보낸 데이터를 게임 규칙대로 합성(최종 아이소)하고 충돌을 겹쳐 확인 |
| `review_view.py` | ChatGPT 검수용 밝은 아이소 화면 `renders/review_iso.png`(1536 px). 게임 출력과 같은 배치이되 게임용 색 보정·가장자리 어둡게를 뺀 Blender 원본 밝기. 게임 데이터는 바꾸지 않음 |
| `game_test/play_test.js` | 실제 게임에서 이동·충돌·가림·출구를 자동 확인하고 영상을 녹화(Playwright) |
| `game_patch/` | 게임 저장소(Isometric-RPG)에 적용할 패치(이 세션은 게임 저장소에 푸시 권한이 없음) |
| `GAME_INTEGRATION.md` | 게임 구조 확인, 적용 방식, 맵/전투 변경 범위, 전투 연동 정보, 영화 동선 문제 |

순서: `build_stage.py` → `export_stage.py` → 게임 `public/stages/mustafar_landing/`로 복사 → `#stage-landing`.

## 최종 화면에서 숨긴 것
- 가설: R 구조물, 하강 계단·판 구멍.
- 검증용: 사람 축척 기둥, 우주선 크기 철사틀, 경사로 발치, 판 윤곽 대안, 모서리 표시 기둥.
- 철사틀 임시 자리: 판 밑 지지, 시설 아래, 절벽, 시설 몸체, 트렌치 끝, 통로 끝.

출입구 돌출부 옆면만은 형태가 미확인(U)이지만 단색 볼륨으로 남겼다. 출입구 면(x 14.8)과 시설 벽 사이를 비우면 화면이 성립하지 않기 때문이다.
