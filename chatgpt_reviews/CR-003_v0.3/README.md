# CR-003 제출 — 출입구 주변 배치 검증 (2026-10-16)

v0.3 작업 사본. **영화 고증 최종 승인 아님.** CR-002r2는 작업 체크포인트로 유지.
- 상세: `research/CR-001_4k_evidence/MUSTAFAR_V03_ENTRANCE_VERIFY.md`
- 변경: `v0.3/CHANGES.md` 3차

## 같은 카메라 비교 (`same_camera/`, 영화 없음)
수정 전 = CR-002r2 체크포인트(커밋 69f54b6), 수정 후 = 이번 작업본.

| 파일 | 카메라 |
|---|---|
| BA_r2cam / BA_iso / BA_top | R2 고정 카메라(v0.2 기준안), 게임 투영, 위 |
| BA_m5 | 11726 맞춤 카메라(M5 최적 해, 형상 고정) |
| BA_approx11748 / 11246 / 11712 / 11625 | 근사 카메라(정성) |

이번 형상 변경은 계단 상자 옆면 사다리꼴 구획뿐이다. 나머지 뷰에서 차이가 없는 것이 정상이다.

## 독립 재검증 파일
- 생성: `v0.3/create_mustafar.py`, `v0.3/dimensions.json`
- 바닥: `v0.3/work/floor_plates.json`, `research/CR-001_4k_evidence/verify/check_floor_tiling.py` → `floor_tiling_result.json`
  - 실행: `python3 research/CR-001_4k_evidence/verify/check_floor_tiling.py v0.3/work/floor_plates.json`
  - 기대 결과: hex_over_cell 1.0, area_ratio 1.0, grid_points_uncovered 0
- 카메라: `research/CR-001_4k_evidence/measure/m5_11726_camera.py` → `m5_result.json`
- 이음매: `research/CR-001_4k_evidence/measure/m6_floor_seams.py analyze` → `m6_result.json` (입력 `m6_segments.json`)

## 남은 미확정 사항
1. **출입구–상자 높이 비**: 11726에서 3.0 이상, 모델은 2.0이다. 상자를 낮출지(≤0.8 m), 출입구를 높일지(≥3.6 m), 판독·가정 문제인지 정해지지 않았다.
2. **H1 위치**: 맞춤 해마다 출입구 y가 −13.5~−21.1로 흩어진다. 출입구와 처마 조명 구간을 함께 담고 카메라를 풀 수 있는 넓은 컷이 필요하다.
3. **H1 앞 바닥**: 바닥이 문까지 이어지는 것은 양립하지만, 틈이 끝나는 경계와 앞 바닥 폭은 정해지지 않았다.
4. **H1 핀 삭제**: 출입구 앞에 핀이 안 보이는 것과 양립하지만, 핀 배열·간격은 정해지지 않았다.
5. **외삽한 처마 조명**(y 0·−6.7·−13.4): 11726 최적 해에서 영화에 조명이 없는 곳에 투영된다. 근거가 약하다.
6. **11726 처마 조명 대응**: 모델 조명 (6.7, 0)과 (0, −6.7) 중 어느 쌍인지 정해지지 않았다(두 해의 RMS가 비슷하다).
7. **출입구 형태**: 두 층 구성과 폭 비율, 돌출 깊이, 안쪽 평평한 윗변(모델에 없음).
8. **바닥**: 띠 방향(X/Y), 판 길이/폭 비, 끝 각도(영화 사선 이음매 60~70°·120~130° 대 모델 41°·139°), 엇갈림 거리.
9. **계단 상자**: 사다리꼴 구획 수·모양·홈 깊이, 짧은 끝면의 세로 홈(미반영).
10. **기존 미확정**: 트렌치 폭·깊이, 전체 외곽, 내부 경로 연결. 카메라와 처마는 기준안 유지.
