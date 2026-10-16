"""M1 보조 — 뒤쪽 슬래브 높이 가정(±0.5 m)과 한 장 빼기(LOO) 카메라에 따른 결과 폭. m1_r2_camera_4k.py의 함수를 그대로 쓴다.
실행: python3 m1b_sensitivity.py → m1b_result.json"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m1_r2_camera_4k as m

out = {}
for f in (3640, 4550, 5850):
    s, th, h, _ = m.solve(f)
    g = {k: m.ground(u, v, f, th, h)[:2] for k, (u, v) in m.PTS.items()}
    A, B = g["edge_light_d"], g["edge_light_f"]; t = (B - A) / np.linalg.norm(B - A); n = np.array([-t[1], t[0]])
    n = n * (np.sign((g["anakin"] - A).dot(n)) or 1)
    slab = {}
    for z in (-0.5, 0.0, 0.5):
        slab[str(z)] = {k: round(float((m.ground(*m.PTS[k], f, th, h, z=z)[:2] - A).dot(n)), 2) for k in ("slab_light_a", "slab_light_b", "slab_light_c")}
    loo = {}
    for fr in sorted({o[0] for o in m.OBS}):
        ss, th2, h2, _ = m.solve(f, obs=[o for o in m.OBS if o[0] != fr])
        d = m.derived(f, th2, h2)
        loo[str(fr)] = {"cam_h": round(h2, 2), "spot_h_gap6": d["eave_spot_height_m_by_wall_gap"]["6"],
                        "perp_obi": d["perp_from_edge_light_line_m"]["obiwan"], "perp_ana": d["perp_from_edge_light_line_m"]["anakin"],
                        "slab_c_perp": d["slab_lights_if_deck_level"]["slab_light_c"]["perp_m"], "box_rim_h": d["box_rim_height_m"]}
    out[str(f)] = {"slab_perp_by_slab_top_z": slab, "leave_one_frame_out": loo}
    print(f, json.dumps(out[str(f)], ensure_ascii=False))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "m1b_result.json"), "w"), indent=1)
