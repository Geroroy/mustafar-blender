# 누락 재질 목록 (원본 복원 문제 — 임의 대체 없음)

추출 모델 `duel_mus_both.obj`(SHA256 `a774b9a3e67a173c…`)의 재질 89개 중 **30개**에 질감 연결이 없다(삼각형 25152 / 54240 = 46%).
경로 이름(vjun·imperial·cairn·musend2 등)은 추출 패키지에 이미지가 들어 있지 않은 질감이다(전달 README: 일부 공유 재질은 원본 게임의 다른 패키지에 있을 수 있다). 착륙장 영역 안 삼각형 수는 OBJ에서 직접 센 값이다.
렌더에서는 추출본이 준 기본 재질(회색/흰색 확산)로 나온다. **원래 색이 아니다.** 새로 만든 질감으로 바꾸지 않았다. 원본 기본 자료의 해당 질감을 받으면 같은 이름으로 연결만 하면 된다.

| 재질(엔진 셰이더 경로) | OBJ 재질 | 삼각형 전체 | 착륙장 영역 안 |
|---|---|---:|---:|
| `textures/vjun/basemetal4` | `material_9` | 8269 | 1231 |
| `textures/musend2/terrain_0` | `material_57` | 4495 | 5 |
| `textures/vjun/basemetal1` | `material_1` | 2544 | 104 |
| `textures/cairn/newwall` | `material_18` | 2220 | 0 |
| `textures/vjun/ceilingsupport` | `material_34` | 1777 | 515 |
| `textures/imp_mine/blastshield` | `material_3` | 1349 | 655 |
| `textures/common/glass` | `material_72` | 792 | 0 |
| `textures/impdetention/light_white` | `material_68` | 748 | 236 |
| `textures/imperial/beam_plain` | `material_20` | 508 | 0 |
| `textures/factory/pillerc` | `material_19` | 354 | 0 |
| `textures/musend2/terrain_1` | `material_56` | 354 | 0 |
| `textures/impdetention/light_blue` | `material_67` | 274 | 144 |
| `textures/vjun/basemetal6` | `material_8` | 256 | 256 |
| `textures/vjun/vader_floor2_mask` | `material_40` | 237 | 19 |
| `textures/vjun/basemetal5` | `material_35` | 204 | 152 |
| `textures/imperial/wall_6` | `material_5` | 159 | 91 |
| `textures/musend2/terrain_0to1` | `material_55` | 146 | 0 |
| `textures/imperial/crate_panels` | `material_2` | 128 | 0 |
| `textures/mp/s_ylight_blue` | `material_74` | 64 | 0 |
| `textures/vjun/vader_trim2_mask` | `material_24` | 63 | 10 |
| `textures/hoth/light_ceiling` | `material_70` | 46 | 10 |
| `textures/vjun/floor3_mask` | `material_23` | 34 | 0 |
| `textures/factory/basefloor1` | `material_71` | 33 | 0 |
| `textures/vjun/floor2` | `material_25` | 32 | 2 |
| `textures/vjun/walk_ceiling_mask` | `material_15` | 20 | 0 |
| `textures/impdetention/vslot2a` | `material_48` | 16 | 0 |
| `textures/vjun/vader_floor` | `material_66` | 12 | 0 |
| `textures/vjun/door1` | `material_75` | 12 | 0 |
| `textures/vjun/vader_floor3` | `material_14` | 4 | 0 |
| `textures/impdetention/mp_r_trimlight` | `material_69` | 2 | 0 |

연결된 재질(질감 파일 있음) 59개는 원본 질감 그대로 입혔다. 질감 파일이 디스크에 없는 경우: 없음.

※ 이 목록은 mo01(원본 가져오기) 결과다. 이후 단계(게임 맞춤·내보내기)는 재질을 바꾸지 않는다(용암 질감만 같은 그림을 발광으로 쓴다).
