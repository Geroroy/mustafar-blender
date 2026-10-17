# ART01 재질 목록

자동 생성: `art09_material_table.py` (art_materials.json + audit.json). 화면 비율 = 게임 카메라 1배 배경 범위에서 그 재질이 실제로 보이는 픽셀 비율(조각 포함, 가림 반영).

## 분류(하나의 그래픽 기준)

| 분류 | 종류 | 기준 반사율(선형) | 금속성 | 거칠기 | 설명 |
|---|---|---|---:|---:|---|
| `floor_pad` | metal | [0.08, 0.075, 0.069] | 0.25 | 0.62 | 착륙장 판 윗면. 원본 floor_1_o의 판 배치를 가는 이음선으로만(판 톤 차이 ±5%). 어두운 다각형 무늬의 높은 대비는 버림. |
| `floor_bay` | metal | [0.068, 0.064, 0.06] | 0.25 | 0.62 |  |
| `floor_plain` | metal | [0.068, 0.064, 0.06] | 0.25 | 0.62 |  |
| `fac_wall` | metal | [0.05, 0.05, 0.052] | 0.45 | 0.55 | 시설 외벽·판 측면·받침·경사 지지부. 어두운 중성 회색 금속, 틈 그을음, 세로 그을음 자국은 약하게, 볼록 모서리 마모. |
| `fac_roof` | metal | [0.066, 0.065, 0.064] | 0.35 | 0.65 |  |
| `curb` | metal | [0.064, 0.063, 0.062] | 0.45 | 0.5 |  |
| `bay_detail` | metal | [0.058, 0.057, 0.056] | 0.45 | 0.55 |  |
| `bay_detail_plain` | metal | [0.058, 0.057, 0.056] | 0.45 | 0.55 |  |
| `prop_metal` | metal | [0.074, 0.067, 0.056] | 0.5 | 0.5 | 상자·통·바닥 위 작은 판. 시설보다 약간 따뜻한 어두운 금속(영화 낮은 상자의 황동빛 기운은 아주 약하게). |
| `ship_silver` | metal | [0.29, 0.295, 0.31] | 0.3 | 0.58 | 우주선 은색 선체. 원본 hull·wing·underside 그림의 패널선만 씀. [판단] 영화의 거울 같은 크롬 대신 무광에 가까운 은색: 평평한 면에 해가 비쳐 하얗게 타는 것을 막고 작은 화면에서 형태가 읽히게. |
| `ship_dark` | metal | [0.06, 0.06, 0.065] | 0.6 | 0.45 |  |
| `rock` | rock | [0.028, 0.024, 0.022] | 0.0 | 0.92 | 현무암 암벽. 질감 없는 원본 재질(musend2/terrain_*): 위치·형상(판 둘레 용암 위로 솟은 큰 삼각 면)으로 용도 확인. 발광 균열은 넣지 않음. |
| `cloth` | cloth | [0.04, 0.032, 0.028] | 0.0 | 0.9 |  |
| `glass` | metal | [0.02, 0.022, 0.025] | 0.2 | 0.15 |  |
| `lamp_white` | lamp | [1.0, 0.92, 0.82] | — | — |  |
| `lamp_blue` | lamp | [0.75, 0.86, 1.0] | — | — |  |
| `lamp_tex` | lamp | None | — | — |  |
| `lava` | lava | [0.025, 0.012, 0.008] | — | — | 원본 lava 그림의 흐름(밝기 분포, 원본 UV)과 큰 잡음으로 발광 분포를 정하고, 굳은 껍질 판 사이 가는 균열(보로노이 경계 약 4.5 m 칸)을 원본 밝기에 비례해 더한다. 노란 고휘도·검은 반점의 큰 대비를 줄이고 연무를 겹친다. |

## 재질 89개

| 재질 | 원본 셰이더 경로 | 원본 질감 | 삼각형 | 게임 화면 비율(1배) | 새 분류 | 원본 UV로 쓰는 배치 마스크 | 근거·메모 |
|---|---|---|---:|---:|---|---|---|
| material_64 | textures/plasma_mustafar/lava2 | 있음 | 2 | 36.13% | lava | — | [모드] plasma_mustafar/lava2, 용암 면(z −39.8) |
| material_57 | textures/musend2/terrain_0 | **없음(누락)** | 4495 | 20.76% | rock | — | [모드] musend2/terrain_0 질감 없음. 판 둘레 큰 암벽 |
| material_40 | textures/vjun/vader_floor2_mask | **없음(누락)** | 237 | 9.55% | fac_wall | — | [모드] vjun/vader_floor2_mask 질감 없음. 판 아래 받침 탑 벽 → 시설 금속(연무로 뒤로) |
| material_46 | textures/plasma_mustafar/floor_1_o | 있음 | 161 | 7.58% | floor_pad | floor_1_o | [모드] plasma_mustafar/floor_1_o, 착륙장 판 윗면·옆 통로 바닥 |
| material_5 | textures/imperial/wall_6 | **없음(누락)** | 159 | 5.93% | fac_roof | — | [모드] imperial/wall_6 질감 없음. 시설 지붕 경사면 → 지붕 금속 |
| material_9 | textures/vjun/basemetal4 | **없음(누락)** | 8269 | 4.70% | fac_wall | — | [모드] vjun/basemetal4 질감 없음. 시설 정면 벽·판 가장자리 톱니·받침 → 시설 금속 |
| material_6 | textures/asjc_starship/silver_wing | 있음 | 284 | 2.85% | ship_silver | silver_wing | [모드] asjc_starship/silver_wing, 날개·꼬리 |
| material_0 | textures/asjc_starship/hull | 있음 | 96 | 2.71% | ship_silver | hull | [모드] asjc_starship/hull, 우주선 윗면 |
| material_34 | textures/vjun/ceilingsupport | **없음(누락)** | 1777 | 1.53% | fac_wall | — | [모드] vjun/ceilingsupport 질감 없음. 판 앞·옆 측면 띠, 베이 앞 턱 → 시설 금속 |
| material_41 | textures/plasma_mustafar/floor_3_o | 있음 | 19 | 1.12% | floor_bay | floor_3_o | [모드] plasma_mustafar/floor_3_o, 베이 바닥·옆 통로 아래층 바닥 |
| material_3 | textures/imp_mine/blastshield | **없음(누락)** | 1349 | 0.89% | curb | — | [모드] imp_mine/blastshield 질감 없음. 옆 통로 쪽 낮은 연석 띠와 측면 → 연석 |
| material_24 | textures/vjun/vader_trim2_mask | **없음(누락)** | 63 | 0.83% | fac_wall | — | [모드] vjun/vader_trim2_mask 질감 없음. 시설 옆 박공벽 → 시설 금속 |
| material_56 | textures/musend2/terrain_1 | **없음(누락)** | 354 | 0.75% | rock | — | [모드] musend2/terrain_1 질감 없음. 아래쪽 암벽 |
| material_43 | textures/plasma_mustafar/basic | 있음 | 287 | 0.56% | prop_metal | — | [모드] plasma_mustafar/basic, 통 뚜껑·바닥 위 낮은 삼각 판 |
| material_39 | textures/plasma_mustafar/trim_2 | 있음 | 328 | 0.56% | prop_metal | — | [모드] plasma_mustafar/trim_2, 통·상자 테두리. 원본 그림 안 씀 |
| material_73 | textures/asjc_mustafar/heat_shield | 있음 | 608 | 0.52% | fac_wall | — | [모드] heat_shield, 먼 배경 탑(연무로 뒤로) |
| material_45 | textures/asjc_mustafar/basic_metal | 있음 | 10917 | 0.48% | bay_detail_plain | — | [모드] asjc_mustafar/basic_metal, 베이 안 세로 판·구조. 원본 그림은 거의 무늬 없음 → 패널 격자만 |
| material_77 | textures/md_mus/base2 | 있음 | 6299 | 0.42% | fac_wall | — | [모드] md_mus/base2, 먼 배경 탑 |
| material_1 | textures/vjun/basemetal1 | **없음(누락)** | 2544 | 0.37% | fac_wall | — | [모드] vjun/basemetal1 질감 없음. 베이 경사 지지부 2개·주변 → 시설 금속 |
| material_47 | textures/asjc_mustafar/control_floor_2 | 있음 | 956 | 0.35% | bay_detail | control_floor_2 | [모드] asjc_mustafar/control_floor_2, 베이 안 바닥·장비 면 |
| material_60 | textures/plasma_mustafar/light_6 | 있음 | 4 | 0.20% | lamp_tex | — | [모드] plasma_mustafar/light_6(밝은 판 등 그림), 옆 통로 아래층 벽 조명 |
| material_55 | textures/musend2/terrain_0to1 | **없음(누락)** | 146 | 0.19% | rock | — | [모드] musend2/terrain_0to1 질감 없음. 암벽 전이부 |
| material_33 | textures/asjc_mustafar/mustafar_door | 있음 | 48 | 0.16% | bay_detail | mustafar_door | [모드] asjc_mustafar/mustafar_door, 시설 옆문 |
| material_38 | textures/plasma_mustafar/pipe_1 | 있음 | 240 | 0.12% | prop_metal | — | [모드] plasma_mustafar/pipe_1, 상자 몸체. 원본 그림(솔질·나뭇결 모양)은 쓰지 않음 |
| material_80 | textures/md_mus/base2_kanter | 있음 | 1186 | 0.12% | fac_wall | — | [모드] base2_kanter, 먼 배경 탑 |
| material_68 | textures/impdetention/light_white | **없음(누락)** | 748 | 0.11% | lamp_white | — | [모드] impdetention/light_white 질감 없음. 연석 띠 사이 작은 면 → 원본 조명. [영화] 판 가장자리 낮은 등(11615). 세기는 [판단] |
| material_82 | textures/md_mus/base4 | 있음 | 1336 | 0.10% | fac_wall | — | [모드] base4, 먼 배경 탑 |
| material_7 | textures/asjc_starship/silver_hull_underside | 있음 | 477 | 0.07% | ship_silver | silver_hull_underside | [모드] silver_hull_underside, 선체 아래 |
| material_67 | textures/impdetention/light_blue | **없음(누락)** | 274 | 0.06% | lamp_blue | — | [모드] impdetention/light_blue 질감 없음. 지붕 처마의 작은 기구 면 → 원본 조명 기구(셰이더 이름이 조명). [영화] 처마 조명 있음(11235·11615·11726). 색은 [판단] |
| material_18 | textures/cairn/newwall | **없음(누락)** | 2220 | 0.05% | fac_wall | — | [모드] cairn/newwall 질감 없음, 시설 뒤·아래(거의 안 보임) |
| material_11 | textures/plasma_mustafar/frame_4 | 있음 | 4 | 0.05% | prop_metal | — | [모드] frame_4, 육각 상자 옆 작은 장치 |
| material_36 | textures/asjc_starship/ramp2 | 있음 | 28 | 0.03% | ship_silver | ramp2 | [모드] starship/ramp2, 승강 경사 |
| material_37 | textures/plasma_mustafar/trim_4 | 있음 | 76 | 0.03% | ship_dark | — | [모드] plasma_mustafar/trim_4, 승강 경사 테두리 |
| material_86 | textures/mussp/robe1 | 있음 | 32 | 0.02% | cloth | — | [모드] mussp/robe1, 위와 같음 |
| material_85 | textures/mussp/robe2 | 있음 | 32 | 0.02% | cloth | — | [모드] mussp/robe2, 바닥에 붙은 납작한 면(z 0.05) — 옷감 그림. 용도(쓰러진 인물 자리 등)는 UNKNOWN, 원본 그림 반 섞음 |
| material_25 | textures/vjun/floor2 | **없음(누락)** | 32 | 0.02% | floor_plain | — | [모드] vjun/floor2 질감 없음, 통로 안쪽 일부 |
| material_76 | textures/md_mus/arm_back1_grunge | 있음 | 960 | 0.02% | fac_wall | — | [모드] md_mus/arm_back1_grunge, 먼 배경 팔 구조 |
| material_62 | textures/plasma_mustafar/light_2 | 있음 | 20 | 0.01% | lamp_tex | — | [모드] light_2(청색 타원 등 그림), 판 가장자리 작은 장치 |
| material_65 | textures/plasma_Mustafar/floorgrate | 있음 | 6 | 0.01% | prop_metal | — | [모드] plasma_Mustafar/floorgrate, 열린 상자 안 격자(덮개 밑) |
| material_72 | textures/common/glass | **없음(누락)** | 792 | 0.00% | glass | — | [모드] common/glass 질감 없음, 화면 밖 창 |
| material_35 | textures/vjun/basemetal5 | **없음(누락)** | 204 | 0.00% | ship_dark | — | [모드] vjun/basemetal5 질감 없음. 우주선 아래 기계부(착륙 다리 근처) → 어두운 우주선 금속 |
| material_10 | textures/plasma_mustafar/chair | 있음 | 858 | 0 (화면 밖) | prop_metal | — | [모드] plasma_mustafar/chair, 화면 밖 실내 |
| material_12 | textures/plasma_mustafar/frame_2 | 있음 | 6 | 0 (화면 밖) | prop_metal | — | [모드] frame_2, 상자 안쪽(안 보임) |
| material_13 | textures/asjc_mustafar/basic_silver | 있음 | 166 | 0 (화면 밖) | fac_wall | — | [모드] basic_silver, 화면 밖 아래층 |
| material_14 | textures/vjun/vader_floor3 | **없음(누락)** | 4 | 0 (화면 밖) | floor_plain | — | [모드] vjun/vader_floor3 질감 없음, 실내(안 보임) |
| material_15 | textures/vjun/walk_ceiling_mask | **없음(누락)** | 20 | 0 (화면 밖) | fac_wall | — | [모드] vjun/walk_ceiling_mask 질감 없음, 실내(안 보임) |
| material_16 | textures/asjc_mustafar/door_frame | 있음 | 568 | 0 (화면 밖) | fac_wall | — | [모드] door_frame, 화면 밖 |
| material_17 | textures/asjc_mustafar/base_interior | 있음 | 355 | 0 (화면 밖) | fac_wall | — | [모드] base_interior, 실내(안 보임) |
| material_19 | textures/factory/pillerc | **없음(누락)** | 354 | 0 (화면 밖) | fac_wall | — | [모드] factory/pillerc 질감 없음, 화면 밖 기둥 |
| material_2 | textures/imperial/crate_panels | **없음(누락)** | 128 | 0 (화면 밖) | prop_metal | — | [모드] imperial/crate_panels 질감 없음. 게임 화면 밖(먼 아래층) → 상자 금속(화면 영향 없음) |
| material_20 | textures/imperial/beam_plain | **없음(누락)** | 508 | 0 (화면 밖) | fac_wall | — | [모드] imperial/beam_plain 질감 없음, 화면 밖 보 |
| material_21 | textures/asjc_mustafar/walkway | 있음 | 468 | 0 (화면 밖) | floor_plain | — | [모드] asjc_mustafar/walkway, 화면 밖 보행로 |
| material_22 | textures/mus/s_light_vjuny | 있음 | 18 | 0 (화면 밖) | lamp_tex | — | [모드] mus/s_light_vjuny, 실내 조명(안 보임) |
| material_23 | textures/vjun/floor3_mask | **없음(누락)** | 34 | 0 (화면 밖) | floor_plain | — | [모드] vjun/floor3_mask 질감 없음, 실내 |
| material_26 | textures/asjc_starship/hold_door1 | 있음 | 8 | 0 (화면 밖) | ship_dark | — | [모드] starship/hold_door1, 우주선 안 |
| material_27 | textures/asjc_starship/wire_blue | 있음 | 6 | 0 (화면 밖) | ship_dark | — | [모드] starship/wire_blue, 우주선 안 |
| material_28 | textures/asjc_starship/light_panel | 있음 | 8 | 0 (화면 밖) | lamp_tex | — | [모드] starship/light_panel, 우주선 안 |
| material_29 | textures/asjc_starship/wall2 | 있음 | 42 | 0 (화면 밖) | ship_dark | — | [모드] starship/wall2, 우주선 안 |
| material_30 | textures/asjc_starship/wire_red | 있음 | 6 | 0 (화면 밖) | ship_dark | — | [모드] starship/wire_red, 우주선 안 |
| material_31 | textures/asjc_starship/wall_panel | 있음 | 84 | 0 (화면 밖) | ship_dark | — | [모드] starship/wall_panel, 우주선 안 |
| material_32 | textures/asjc_starship/wall_light | 있음 | 8 | 0 (화면 밖) | lamp_tex | — | [모드] starship/wall_light, 우주선 안 |
| material_4 | textures/asjc_mustafar/screen_readout3 | 있음 | 42 | 0 (화면 밖) | lamp_tex | — | [모드] screen_readout3, 화면 밖 실내 |
| material_42 | textures/asjc_mustafar/control_floor_1 | 있음 | 364 | 0 (화면 밖) | floor_plain | — | [모드] control_floor_1, 화면 밖 |
| material_44 | textures/plasma_mustafar/trim_5 | 있음 | 18 | 0 (화면 밖) | prop_metal | — | [모드] trim_5, 실내 |
| material_48 | textures/impdetention/vslot2a | **없음(누락)** | 16 | 0 (화면 밖) | fac_wall | — | [모드] impdetention/vslot2a 질감 없음, 실내 |
| material_49 | textures/plasma_mustafar/floor_4 | 있음 | 44 | 0 (화면 밖) | floor_plain | — | [모드] floor_4, 실내 |
| material_50 | textures/plasma_mustafar/basic_black | 있음 | 110 | 0 (화면 밖) | prop_metal | — | [모드] basic_black, 실내 |
| material_51 | textures/plasma_mustafar/trim_2_black | 있음 | 152 | 0 (화면 밖) | prop_metal | — | [모드] trim_2_black, 실내 |
| material_52 | textures/asjc_mustafar/holo_table | 있음 | 32 | 0 (화면 밖) | lamp_tex | — | [모드] holo_table, 실내 |
| material_53 | textures/asjc_mustafar/screen_readout4 | 있음 | 85 | 0 (화면 밖) | lamp_tex | — | [모드] screen_readout4, 실내 |
| material_54 | textures/asjc_mustafar/screen_readout2 | 있음 | 41 | 0 (화면 밖) | lamp_tex | — | [모드] screen_readout2, 실내 |
| material_58 | textures/plasma_mustafar/table_black | 있음 | 38 | 0 (화면 밖) | prop_metal | — | [모드] table_black, 실내 |
| material_59 | textures/plasma_mustafar/basic_2 | 있음 | 45 | 0 (화면 밖) | prop_metal | — | [모드] basic_2, 실내 |
| material_61 | textures/plasma_mustafar/light_4 | 있음 | 72 | 0 (화면 밖) | lamp_tex | — | [모드] light_4, 화면 밖 |
| material_63 | textures/plasma_mustafar/light_1 | 있음 | 24 | 0 (화면 밖) | lamp_tex | — | [모드] light_1, 실내 |
| material_66 | textures/vjun/vader_floor | **없음(누락)** | 12 | 0 (화면 밖) | floor_plain | — | [모드] vjun/vader_floor 질감 없음, 실내 |
| material_69 | textures/impdetention/mp_r_trimlight | **없음(누락)** | 2 | 0 (화면 밖) | lamp_white | — | [모드] mp_r_trimlight 질감 없음, 실내 |
| material_70 | textures/hoth/light_ceiling | **없음(누락)** | 46 | 0 (화면 밖) | lamp_white | — | [모드] hoth/light_ceiling 질감 없음, 실내 천장(안 보임) |
| material_71 | textures/factory/basefloor1 | **없음(누락)** | 33 | 0 (화면 밖) | floor_plain | — | [모드] factory/basefloor1 질감 없음, 실내 |
| material_74 | textures/mp/s_ylight_blue | **없음(누락)** | 64 | 0 (화면 밖) | lamp_blue | — | [모드] mp/s_ylight_blue 질감 없음, 화면 밖 |
| material_75 | textures/vjun/door1 | **없음(누락)** | 12 | 0 (화면 밖) | fac_wall | — | [모드] vjun/door1 질감 없음, 실내 문 |
| material_78 | textures/md_mus/base2_subilte | 있음 | 24 | 0 (화면 밖) | fac_wall | — | [모드] base2_subilte, 먼 배경 |
| material_79 | textures/md_mus/base2_l_kanter | 있음 | 58 | 0 (화면 밖) | fac_wall | — | [모드] base2_l_kanter, 먼 배경 |
| material_8 | textures/vjun/basemetal6 | **없음(누락)** | 256 | 0 (화면 밖) | ship_dark | — | [모드] vjun/basemetal6 질감 없음. 우주선 안쪽(카메라에 안 보임) → 어두운 우주선 금속 |
| material_81 | textures/md_mus/base5 | 있음 | 792 | 0 (화면 밖) | fac_wall | — | [모드] base5, 먼 배경 |
| material_83 | textures/md_mus/arm_lamp1 | 있음 | 132 | 0 (화면 밖) | lamp_tex | — | [모드] arm_lamp1, 먼 배경(안 보임) |
| material_84 | textures/md_mus/door_small2 | 있음 | 4 | 0 (화면 밖) | fac_wall | — | [모드] door_small2, 실내 |
| material_87 | textures/plasma_mustafar/screen_6 | 있음 | 2 | 0 (화면 밖) | lamp_tex | — | [모드] screen_6, 실내 |
| material_88 | textures/plasma_mustafar/screen_6_b | 있음 | 2 | 0 (화면 밖) | lamp_tex | — | [모드] screen_6_b, 실내 |
