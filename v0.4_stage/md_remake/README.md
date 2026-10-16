# md_remake — Movie Duels 모델 기반 리메이크 작업

- **현재 시험본: MD_REMAKE_POC01** — 출발 형상은 Movie Duels `duel_mus_both` 착륙장 영역이다. 보고서는 [MD_REMAKE_POC01.md](MD_REMAKE_POC01.md)에 있다.
- `_superseded_A3e_base/`: 이전 시도(A3e 시설 + 모드 판 외곽)다. 기반이 잘못돼 중단했고, 보존만 한다.
- 모드 형상·질감이 들어간 .blend·이미지·게임 데이터는 비공개 폴더 `research/CR-001_4k_evidence/_private/md_remake_v2/`(git 제외)에만 둔다.

| 파일 | 역할 |
|---|---|
| `md01_import_source.py` | 1단계: OBJ 2개를 별도 장면·컬렉션으로 불러오기(MTL·textures 연결 검사) |
| `md02_render_source.py`, `md_regions.json` | 2·3단계: 원본 렌더(A), 착륙장·정면·입구 표시 |
| `md03_build_poc.py`, `md_modify.py`, `md_poc01.json` | 4·5단계: 선택 영역 복사 → 축척·축 보정 → 영화·게임 수정 |
| `stage_config_MD_REMAKE_POC01.json` | 기존 `build_stage.py`·`export_stage.py`용 설정(게임 카메라·충돌·가림·전투 자리) |
| `md04_game_cam_render.py` | C: A3e와 같은 게임 카메라·같은 화면 범위 렌더 |
| `md05_render_remake.py` | B: 원본과 같은 시점의 리메이크 렌더 |
| `md06_sheets.py` | 전후·비교 묶음 이미지 |
| `md_play_test.js` | 실제 게임 확인(Playwright) |
| `md_render.py` | 렌더·라벨 공용 |
