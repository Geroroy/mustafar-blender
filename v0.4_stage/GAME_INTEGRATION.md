# 착륙장 스테이지 — 게임 적용 (v0.4_stage)

작성: 2026-10-16.
- 기준 배치는 **A3b**다. 임시 작업 기준이며 영화 고증 확정이 아니다.
- A3·H1은 `v0.3/work/layouts/`에 그대로 보존했다.
- 이번 작업에 실내와 다른 결투 구간은 넣지 않았다. 실내 블록아웃(`v0.3/interior/`)은 손대지 않고 보존했다.

## 1. 게임 프로젝트 확인 결과 (Isometric-RPG)

| 항목 | 확인한 내용 |
|---|---|
| 엔진 | 브라우저 게임이다. Vite 8 + Three.js 0.186. 3D 모델을 **로딩 시점에 스프라이트로 구움**(`src/gfx/baker.js`), 2D 캔버스에 그림(`src/gfx/renderer.js`) |
| 투영·축척 | 직교, 고도 30°, 방위 45°, 2:1. 1 타일 = 1 m, 28.284 px/m. 화면 x = (x − y)·20, y = (x + y)·10 − z·24.49 (`src/core/iso.js`) |
| 맵 | `World`(192×192 타일): `biome` 격자 → 절차적 지형(`terrain.js`), `blocked` 격자(0 통행, 1 소품, 2 허공), 소품 목록(`props`), 조명 목록, 시작 위치. 장소마다 `World` 하위 클래스(`worldgen.js`) |
| 충돌 | 유닛은 반지름(아나킨 0.35 m)의 4점을 `world.isBlocked`로 검사하고 벽을 따라 미끄러짐. 클릭 이동은 타일 A*(`pathfind.js`) |
| 가림 | 소품·유닛을 x + y 깊이로 정렬. 플레이어를 가리는 큰 소품은 반투명(디아블로 방식)으로 그리고, 플레이어 실루엣을 덧그림 |
| 조명 | 라이트맵(앰비언트 × 점광원)을 곱하기로 합성 |
| 그래픽 모드 | 오리지널(1배, 색 보정·포스터라이즈·베이어 디더) / 리마스터(2배 밀도, 전체 색). F5로 전환 |
| Blender → 게임 기존 방식 | **없었다.** 모든 그림은 Three.js 코드로 만든 모델을 굽는 방식이다. 이번에 Blender 렌더를 미리 그린 배경으로 넣는 경로를 새로 만들었다(아래) |
| 기존 무스타파 | `#duel-mustafar`(무비 듀얼 #2, `duelMustafar.js`, `MustafarArena`). 절차적 직사각 갑판 맵이다. **이번 작업은 이 파일들을 건드리지 않음** |

## 2. Blender → 게임 경로

1. `v0.4_stage/build_stage.py`
   - A3b 배치를 열어 근거 없는 가설·검증용 객체를 최종 화면에서 숨긴다(목록은 `.blend`의 `scene["hidden_in_final"]`).
   - 재질·조명을 입힌다.
   - 카메라를 나눈다: `Game_Output_Iso`는 게임 투영과 정확히 같고, `Film_Compare_*`는 영화 맞춤 비교용이다.
2. `v0.4_stage/export_stage.py`가 `out/mustafar_landing/`에 다음을 만든다.
   - **배경** `ground_hd.webp`(2배)·`ground_sd.png`(1배): 플레이어가 그 뒤로 갈 수 없는 모든 것(바닥, 시설 정면·지붕·지지부, 출입구, 뒤 가장자리 기둥·난간, 바닥 조명, 용암)을 굽는다.
   - **가림 조각** `sprites_*.png`: 낮은 상자 8조각(1 m), 연석 4개. 다른 물체는 카메라에서만 빼서 그림자와 반사광은 남겼다. 게임 소품과 같은 깊이 정렬·반투명 규칙을 그대로 쓴다.
   - **충돌** `collision.png`: 0.125 m 칸, **시각 형상과 따로** 관리한다.
     - 위에서 광선을 쏴 바닥 객체(0 ± 0.15 m)에 맞는 칸만 통행 가능으로 둔다.
     - 위가 열린 상자는 바닥 투영 전체를 막는다.
   - `stage.json`: 배경 위치, 조각, 충돌 격자, 시작 위치, 출구, 전투 자리, 조명, 앰비언트.
3. 게임 쪽(`stage/mustafar-landing` 브랜치, 아래 패치)
   - `src/stage/stageWorld.js`: 데이터를 읽어 `StageWorld extends World`를 만든다.
     - 타일 격자는 길찾기와 지도용이고, 유닛 충돌은 0.125 m 마스크를 쓴다.
     - 배경 그리기와 조각 프레임 등록도 여기서 한다.
   - `src/stage/stageController.js`: 시작 카드, 출구, 전투 연동 이벤트를 맡는다.
   - 공유 파일 수정은 최소로 했다(총 26줄):
     - `main.js`: `#stage-landing` 진입, 스테이지 로딩, 시작 버튼
     - `game.js`: `stage` 모드 월드 선택, `stage.update` 한 줄
     - `renderer.js`: 배경이 있으면 지형 대신 배경을 그림(한 줄)
   - `public/stages/mustafar_landing/`: 내보낸 데이터.

실행: `npm run dev` → `http://localhost:5173/#stage-landing` → 「스테이지 시작」.

## 3. 맵 작업 / 전투 작업 변경 범위 (겹치지 않게)

| 구분 | 파일 |
|---|---|
| **맵 작업만 바꿈** | `src/stage/*`(새 파일), `public/stages/*`(새 파일) |
| **맵 작업이 최소 수정한 공유 파일** | `src/main.js`(스테이지 모드 분기 3곳), `src/game/game.js`(생성자 분기 1곳, update 한 줄), `src/gfx/renderer.js`(배경 한 줄) |
| **맵 작업이 건드리지 않음 — 전투 세션 영역** | `src/game/duel.js`, `duelMustafar.js`, `units.js`, `skills.js`, `cinema.js`, `src/gfx/models/*`, `src/ui/duelHud.js`, `src/core/input.js`, `src/core/audio.js` |

- 전투 코드는 새로 만들지 않았다. 스테이지 컨트롤러는 위치와 이벤트만 알려 준다.
- 전투 세션이 `game.js`나 `main.js`를 고치면 위 몇 줄만 합치면 된다(충돌이 나도 같은 자리에 다시 넣으면 됨).

## 4. 전투 제작 세션에 전달할 연동 정보

좌표는 게임 타일(m)이다. Blender(X, Y) → 게임: gx = 96 − Y, gy = 95.5 − X.

| 항목 | 값(게임 좌표) | 비고 |
|---|---|---|
| 스테이지 진입 | `#stage-landing`, `game.mode === 'stage'`, `game.stage`(StageController) | 시작 버튼 → `game.stage.start()` |
| 플레이어 시작 | `stage.data.spawn` = (82.0, 101.5) | 판 뒤쪽 가운데 |
| 전투 영역 | `game.stage.combat.area` = (90, 82.5)–(119.5, 107.5) 사각형 | 상자·출입구 앞 바닥을 포함한다. 게임 판단값 |
| 아나킨 시작 | `combat.anakinStart` = (105.0, 93.5) | |
| 상대 시작 | `combat.opponentStart` = (111.0, 88.5) | 상자 앞 |
| 전투 시작 지점 | `combat.trigger` = 중심 (102.0, 93.5), 반지름 4 | 처음 들어오면 `'stage:combatTrigger'` |
| 출구(스테이지 종료) | `stage.data.exit` = x 115.04–115.76, y 80.90–81.60 | A3b 출입구 문턱 앞. 도착하면 페이드 → `'stage:exit'` |

- **이벤트**: `'stage:start'`, `'stage:combatTrigger'`(combat), `'stage:combatArea'`(inside), `'stage:exitLocked'`, `'stage:exit'`(info), `'stage:combatEnd'`(result).
- **호출**:
  - `game.stage.lockExit(true)`: 전투 끝까지 출구를 닫는다.
  - `game.stage.completeCombat(result)`: 출구를 열고 `'stage:combatEnd'`를 낸다.
- **충돌 질의**:
  - `game.world.isBlocked(x, y)`: 0.125 m 마스크.
  - `game.pathfinder`: 타일 A*.
  - 판 밖은 모두 막힘이다. 떨어지는 처리는 없다.
- **가림**:
  - 상자 조각과 연석은 일반 소품과 같은 정렬·반투명 규칙을 따르므로 새 유닛도 자동으로 적용된다.
  - 높이(z)가 있는 유닛은 기존 렌더러 규칙을 따른다.

## 5. 영화 동선을 막는 문제 (기록만 함, 구조물은 줄이거나 옮기지 않음)
1. **출입구 문턱 안으로 몸이 들어가지 않는다(A3b).**
   - 끝 단이 문 +Y 절반 앞을 막고, −Y 절반 앞 통로는 약 0.72 m다. 몸 폭은 0.6 m다.
   - 문틀 겹층이 판 위로 돌출해 있다.
   - 문틀 면(X 14.8) 너머 통로 바닥까지(X 15.8) 바닥 객체가 없다(모델 공백).
   - 그래서 출구를 문틀 앞(몸이 닿는 범위)에 두었다.
2. **클릭 이동이 좁은 문턱 앞까지 경로를 못 찾을 수 있다.** 타일 A*가 0.72 m 틈을 막힌 타일로 본다. 근처에 클릭하면 직선 이동과 미끄러짐으로 닿고, 키 이동으로는 닿는다.
3. **판 가장자리**: 뒤쪽만 난간이 있고, 앞·옆은 막힘 처리만 했다(떨어짐 없음). 영화에서 앞·옆 가장자리 처리(턱·연석 구간)는 후보값이다.
