"""M14 — 11725: 인물·처마 조명·출입구 꼭대기 조명·판 가장자리가 한 화면에 있는 컷(11726 직전 와이드, 다른 카메라 위치).
목적: 11726(4.6~5.5 m, 처마 조명 높이 가정)과 11748(2.0~2.8 m, 인물 축척) 중 한쪽을 확정하지 않고, 같은 화면 안에서 두 축척이 함께 성립하는지 본다.
방법(한 장 측량, 카메라 수평 근사 — 세로선이 화면에서 세로):
  - 바닥에 선 높이 H 물체: H / 카메라 높이 = (v_발 − v_머리) / (v_발 − v_지평선)
  - 출입구 꼭대기 조명 높이 = 카메라 높이 × (v_가장자리 − v_조명) / (v_가장자리 − v_지평선)
    (출입구 밑동은 상자에 가려 보이지 않음 → 판 시설 쪽 가장자리선 v로 대신함. 문틀 앞면은 가장자리 뒤 0.3 m이므로 약간 과소)
  - 지평선 v는 700 / 800 / 900 범위(피치 약 ±2~3°)로 둔다. 위 두 식은 f와 무관하다.
  - 처마 조명: 모델 깊이(SPOT_X, 가장자리 뒤 6.65 m)에 둘 때의 높이와, 모델 높이(7.03 m)일 때 필요한 깊이를 f별로 적는다(f 의존).
판독은 4K 원본에서 직접(±5 px, 인물 발 ±10 px). 실행: python3 m14_11725_person_scale.py → m14_result.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m9_a3_shape_fit as m  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OBS = {"anakin_head": (1185, 480), "anakin_feet_ground": 1345, "obiwan_head": (1880, 525), "obiwan_feet_ground": 1345,
       "eave_light": (515, 255), "door_light": (2850, 350), "deck_edge_line_v": 1196, "deck_edge_lamp": (420, 1170)}
PERSONS = {"anakin": {"head": 480, "H": [1.70, 1.85], "note": "달리는 보폭 — 머리가 조금 낮아짐"},
           "obiwan": {"head": 525, "H": [1.60, 1.78], "note": "다리를 벌린 자세 — 머리가 낮아짐"}}
VB, VE, VL, VEAVE = 1345, OBS["deck_edge_line_v"], OBS["door_light"][1], OBS["eave_light"][1]
DX_EAVE = m.SPOT_X - m.X1


def main():
    rows = []
    for vh in (700, 800, 900):
        for nm, p in PERSONS.items():
            for H in p["H"]:
                hc = H * (VB - vh) / (VB - p["head"])
                rows.append({"horizon_v": vh, "person": nm, "H_assumed": H, "camera_height": round(hc, 2),
                             "door_light_height": round(hc * (VE - VL) / (VE - vh), 2)})
    dl = [r["door_light_height"] for r in rows]
    eave = []
    for vh in (700, 800, 900):
        hcs = [r["camera_height"] for r in rows if r["horizon_v"] == vh]
        hc = sum(hcs) / len(hcs)
        for f in (2039, 2800, 3500, 5000):
            d_edge = f * hc / (VE - vh)
            h_at_model = hc + (vh - VEAVE) * (d_edge + DX_EAVE) / f
            d_need = f * (m.SPOT_Z - hc) / (vh - VEAVE)
            eave.append({"horizon_v": vh, "f": f, "camera_height_mean": round(hc, 2), "deck_edge_distance": round(d_edge, 1),
                         "eave_height_if_at_model_depth": round(h_at_model, 2),
                         "eave_depth_behind_edge_if_height_7.03": round(d_need - d_edge, 1)})
    out = {"doc": __doc__.split("\n")[0], "obs_11725_4k": OBS, "persons": PERSONS, "door_light": rows,
           "door_light_range_m": [min(dl), max(dl)], "eave_check": eave, "model_eave": {"x": m.SPOT_X, "z": m.SPOT_Z, "behind_edge": round(DX_EAVE, 2)}}
    json.dump(out, open(os.path.join(HERE, "m14_result.json"), "w"), ensure_ascii=False, indent=1)
    print("door light", out["door_light_range_m"])
    for e in eave: print(e)


if __name__ == "__main__":
    main()
