# MO_GENTEX — Movie Duels 원본 적용 맵에 생성 대체 질감 30개 연결 (2026-10-17)

- 출처: 사용자 제공 `MUSTAFAR_TEXTURES_GEN.zip`(GPT 생성 대체 질감 30개 + README_APPLY.md·TEXTURES_GEN_NOTES.md·FILE_MANIFEST.json). **AI로 새로 만든 대체 질감이며 원본 Jedi Academy 질감이 아니다.**
- 기준: MO_STAGE(Movie Duels `duel_mus_both` 원본 형상 그대로, 게임 커밋 `1633ff9` 데이터의 출처). 형상·UV·타일 배율·게임 카메라·조명·보행·시작점·출구·전투 자리는 바꾸지 않았다. 전투·UI·게임 코드도 바꾸지 않았다.
- 질감 이미지·렌더·게임 데이터는 비공개 폴더 `research/CR-001_4k_evidence/_private/md_orig_gentex/`(git 제외)에만 있다.

## 1. 받은 파일 검사
- 30개 모두 있음. 파일 이름·크기·색 형식(JPEG RGB / 유리 PNG RGBA)이 요청서(textures_spec.csv)와 같고, SHA-256이 FILE_MANIFEST.json과 같다. 남는 파일 없음.
- 이음새: 반대편 경계 1 px 평균 차이 0.7~1.5(내부 인접 픽셀 차이 2.5~14.7보다 작음) → 반복해도 경계가 튀지 않는다. 2×2 반복 시트도 확인.
- 유리 알파는 전체 90/255.

## 2. 연결 방식 (README_APPLY.md 따름)
| 항목 | 방식 |
|---|---|
| 연결표 | `mo_gentex_map.json`(obj_material → 파일). **원본 MTL은 고치지 않음** |
| 적용 | `mo11_apply_gentex.py`: MO_STAGE.blend를 열어 질감이 없던 재질 30개에만 붙이고 **새 파일** MO_STAGE_GENTEX.blend로 저장(원본 .blend 그대로). 이미 질감이 있던 59개는 손대지 않음(스크립트가 단언) |
| 색 | 기존 연결 재질과 같게: 이미지 → Base Color, 거칠기 1.0, 반사 0, 금속 0. `_mask` 이름도 색 그림으로만 씀(흑백 마스크·원본 다단 셰이더로 해석하지 않음) |
| 조명 5종 | 이미지 밝기(흑백)를 0.55→0.80 구간에서 0~1로 바꾼 마스크 × 세기 4.0으로 **밝은 광원부만 발광**. 틀은 일반 재질. 값은 미리보기 화면에서 정함 |
| 유리 | PNG 알파를 그대로 Alpha에 연결(추가 곱셈 없음). Cycles 기본 양면 |
| 지형 3종 | 일반 재질(발광·주황색 추가 없음) |
| 내보내기 | `MO_CONFIG=mo_stage_config_gentex.json`으로 기존 mo06·mo07 그대로(설정은 장면 파일·출력 폴더·layout 이름만 다름). 32 샘플, 약 45분 |

## 3. 결과 데이터 비교 (게임 커밋 1633ff9 데이터 대비)
- `collision.png` **바이트까지 같음**. `stage.json`은 `layout`(MO_STAGE → MO_STAGE_GENTEX)만 다르고 가림 조각 58개의 위치·크기·아틀라스 좌표·시작점·출구·전투 자리 모두 같음.
- 바뀐 것: 배경 그림(`ground_sd.png`·`ground_hd.webp`)과 가림 조각 그림(`sprites_sd.png`·`sprites_hd.png`).

## 4. 게임 확인 (오리지널 그래픽만)
실행 패키지(게임 커밋 1633ff9 정적 빌드) 사본에 새 맵 데이터 6개만 바꿔 넣고 로컬 HTTP(`python3 -m http.server`)로 `#stage-landing`을 Chromium(Playwright)으로 실행: **14개 확인 모두 통과**.
- 로딩 35초, 맵 `MO_STAGE_GENTEX`·조각 58개, 시작점 (101.99, 91.37).
- 클릭 이동: 우주선 아래 (0,−23)·판 끝 (0,−35)·옆 통로 끝 (−11,20) 도착. 새 페이지에서 출구 칸 클릭 → `stage:exit`.
- 필수 파일 404·페이지 오류·콘솔 오류 없음(스타 카드 일러스트 선택 파일 404는 기존과 같음). HD 맵 파일은 서버에 있음(리마스터 모드 자체는 실행하지 않음).
- 게임 저장소는 건드리지 않았다(다른 작업 브랜치가 진행 중).

## 5. 화면 확인
- 같은 게임 카메라 전체(실행 패키지 배경 범위)에서 질감 재질별 화면 픽셀을 정확한 색 위치 지도(조명 없는 발광색 렌더)로 골라 전후를 비교했다.
  - 전체 화면에 실제로 보이는 재질은 **16개**이고 모두 바뀜(그 재질 픽셀의 95~100%).
  - 벽·암벽 밝기가 약 190(흰색)에서 40~65(어두운 금속·현무암)로, 조명 띠는 약 106~128(발광부)이다.
- 3개(hoth/light_ceiling, vjun/floor3_mask, vjun/basemetal6)는 배경 범위 안에 있지만 다른 형상에 가려 전체 화면에서는 안 보인다. hoth/light_ceiling은 처마 밑 근접(S5)에서 확인했다.
- 11개(C 등급)는 게임 배경 범위 밖이라 연결만 확인했다.
- 근접 비교판(같은 카메라 전후): 암벽(S2), 시설 벽·지붕(S3), 받침 기둥(S4), 조명(S5), 유리(S6), 실제 게임 화면 4곳(S7).

## 6. 30개 연결 결과
| # | 우선 | 셰이더(재질) | 파일 | 처리 | 연결 | 전체 게임 화면 결과 | 근접 비교판 |
|---|---|---|---|---|---|---|---|
| 1 | A | `musend2/terrain_0` (material_57) | `textures__musend2__terrain_0.jpg` | 색 | 예 | 바뀜 100% (밝기 193.3→53.9) | S2 |
| 2 | A | `vjun/vader_floor2_mask` (material_40) | `textures__vjun__vader_floor2_mask.jpg` | 색 | 예 | 바뀜 100% (밝기 168.0→37.1) | S4 |
| 3 | A | `musend2/terrain_1` (material_56) | `textures__musend2__terrain_1.jpg` | 색 | 예 | 바뀜 100% (밝기 156.8→39.8) | S2 |
| 4 | A | `vjun/ceilingsupport` (material_34) | `textures__vjun__ceilingsupport.jpg` | 색 | 예 | 바뀜 100% (밝기 202.4→59.0) |  |
| 5 | A | `vjun/basemetal4` (material_9) | `textures__vjun__basemetal4.jpg` | 색 | 예 | 바뀜 100% (밝기 189.1→47.1) | S3 |
| 6 | A | `imperial/wall_6` (material_5) | `textures__imperial__wall_6.jpg` | 색 | 예 | 바뀜 100% (밝기 235.0→63.0) | S3 |
| 7 | A | `musend2/terrain_0to1` (material_55) | `textures__musend2__terrain_0to1.jpg` | 색 | 예 | 바뀜 100% (밝기 221.5→64.6) | S2 |
| 8 | A | `imp_mine/blastshield` (material_3) | `textures__imp_mine__blastshield.jpg` | 색 | 예 | 바뀜 100% (밝기 195.1→51.1) | S3 |
| 9 | B | `vjun/basemetal1` (material_1) | `textures__vjun__basemetal1.jpg` | 색 | 예 | 바뀜 100% (밝기 200.7→44.3) | S3 |
| 10 | B | `vjun/vader_trim2_mask` (material_24) | `textures__vjun__vader_trim2_mask.jpg` | 색 | 예 | 바뀜 100% (밝기 193.5→48.0) | S3 |
| 11 | B | `vjun/basemetal5` (material_35) | `textures__vjun__basemetal5.jpg` | 색 | 예 | 바뀜 100% (밝기 103.8→26.4) |  |
| 12 | B | `impdetention/light_white` (material_68) | `textures__impdetention__light_white.jpg` | 색+발광(밝은 부분만) | 예 | 바뀜 99% (밝기 184.0→128.2) | S5 |
| 13 | B | `cairn/newwall` (material_18) | `textures__cairn__newwall.jpg` | 색 | 예 | 바뀜 100% (밝기 186.9→53.8) |  |
| 14 | B | `hoth/light_ceiling` (material_70) | `textures__hoth__light_ceiling.jpg` | 색+발광(밝은 부분만) | 예 | 전체 게임 화면에서는 다른 형상에 가려 안 보임 | S5(아래 근접) |
| 15 | B | `vjun/floor3_mask` (material_23) | `textures__vjun__floor3_mask.jpg` | 색 | 예 | 전체 게임 화면에서는 다른 형상에 가려 안 보임 |  |
| 16 | B | `vjun/floor2` (material_25) | `textures__vjun__floor2.jpg` | 색 | 예 | 바뀜 100% (밝기 113.2→41.3) |  |
| 17 | B | `impdetention/light_blue` (material_67) | `textures__impdetention__light_blue.jpg` | 색+발광(밝은 부분만) | 예 | 바뀜 100% (밝기 207.7→106.2) | S5 |
| 18 | B | `vjun/basemetal6` (material_8) | `textures__vjun__basemetal6.jpg` | 색 | 예 | 전체 게임 화면에서는 다른 형상에 가려 안 보임 |  |
| 19 | B | `common/glass` (material_72) | `textures__common__glass.png` | 색+투명(알파) | 예 | 바뀜 95% (밝기 49.1→29.5) | S6 |
| 20 | C | `imperial/crate_panels` (material_2) | `textures__imperial__crate_panels.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 21 | C | `vjun/vader_floor3` (material_14) | `textures__vjun__vader_floor3.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 22 | C | `vjun/walk_ceiling_mask` (material_15) | `textures__vjun__walk_ceiling_mask.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 23 | C | `factory/pillerc` (material_19) | `textures__factory__pillerc.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 24 | C | `imperial/beam_plain` (material_20) | `textures__imperial__beam_plain.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 25 | C | `impdetention/vslot2a` (material_48) | `textures__impdetention__vslot2a.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 26 | C | `vjun/vader_floor` (material_66) | `textures__vjun__vader_floor.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 27 | C | `impdetention/mp_r_trimlight` (material_69) | `textures__impdetention__mp_r_trimlight.jpg` | 색+발광(밝은 부분만) | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 28 | C | `factory/basefloor1` (material_71) | `textures__factory__basefloor1.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 29 | C | `mp/s_ylight_blue` (material_74) | `textures__mp__s_ylight_blue.jpg` | 색+발광(밝은 부분만) | 예 | 게임 배경 범위 밖(연결만 확인) |  |
| 30 | C | `vjun/door1` (material_75) | `textures__vjun__door1.jpg` | 색 | 예 | 게임 배경 범위 밖(연결만 확인) |  |

## 7. 남은 문제·주의
1. 생성 대체 질감이다. 원본 질감·영화 고증으로 부르지 않는다. 판재 개수·띠 간격 등은 생성 측 제작 판단이다.
2. 조명 발광 문턱(0.55~0.80)·세기(4.0)는 미리보기 화면에서 정했다. 판 가장자리·옆 통로의 흰 조명은 게임 화면에서 짧은 점선처럼 보인다. 형상 자체가 짧은 조각인지 질감 띠의 마디(한 장 1.53 × 7.65 m) 때문인지는 확인하지 않았다.
3. 판 아래 받침 기둥은 용암 반사광 때문에 붉게 보인다(질감 색은 회흑색).
4. 우주선이 흰색인 것은 원본에 연결돼 있던 질감(asjc_starship) 그대로이고 이번 30개와 무관하다.
5. 리마스터(HD) 화면은 확인하지 않았다. HD 파일은 만들어 두었다.
6. C 등급 11개는 지금 게임 화면 밖이라 화면 검수를 하지 못했다.

## 8. 다시 만들기
```
.venv-bpy/bin/python v0.4_stage/md_orig/mo11_apply_gentex.py research/CR-001_4k_evidence/_private/md_orig/MO_STAGE.blend research/CR-001_4k_evidence/_private/md_orig_gentex/textures research/CR-001_4k_evidence/_private/md_orig_gentex/MO_STAGE_GENTEX.blend
MO_CONFIG=mo_stage_config_gentex.json .venv-bpy/bin/python v0.4_stage/md_orig/mo06_export_game.py research/CR-001_4k_evidence/_private/md_orig/walk/walk.npz --samples 32
MO_CONFIG=mo_stage_config_gentex.json .venv-bpy/bin/python v0.4_stage/md_orig/mo07_pack.py
.venv-bpy/bin/python v0.4_stage/md_orig/mo12_views.py <MO_STAGE.blend 또는 MO_STAGE_GENTEX.blend> <출력 접두어 BEFORE/AFTER>
python3 -I v0.4_stage/md_orig/mo13_sheets_gentex.py <views> <게임 전 화면> <게임 후 화면> <출력(_private 안)>
```
