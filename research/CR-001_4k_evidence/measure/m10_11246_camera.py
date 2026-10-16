"""M10 — 11246 카메라 맞춤(CR-007). A3와 H1에서 똑같은 형상(낮은 상자·시설 쪽 가장자리·가장자리 등)만으로 카메라를 푼다.
이렇게 하면 카메라가 배치 후보에 의존하지 않으므로, 그 카메라에 A3의 새 객체(출입구·출입구 면·R 가설)를 투영해 11246의 관찰과 충돌하는지 볼 수 있다.
가정: 핀홀, 주점 = 화면 중심, 롤 0. 판독 ±5~20 px. 영화 파일 불필요. 실행: python3 m10_11246_camera.py → m10_result.json"""
import itertools, json, math, os
import numpy as np
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I 실행에서도 같은 폴더 모듈을 찾도록
from m9_a3_shape_fit import (proj, line_res, lm, best_fit, cam_dict, HX0, HX1, HY0, HY1, PH, SKO, X1, D)

HERE = os.path.dirname(os.path.abspath(__file__))
INS = D["edge_lights"]["inset"]["value"]
OBS = {"edge_light_near": (1003, 870), "deck_edge_line": [(300, 905), (700, 893)],
       "box_plusY_top_near": (2445, 895), "box_plusY_top_far": (2780, 835), "box_raised_start": (3220, 1000),
       "box_base_line": [(2700, 1320), (3300, 1420)], "box_far_rim_line": [(2900, 845), (3400, 870)]}
LAMP_Y = D["edge_lights"]["facility_edge_y"]["value"]


def res(c, lamp_y):
    r = []
    q, df = proj((X1 - INS, lamp_y, 0.06), c); r += list(q - OBS["edge_light_near"]) if df > 0 else [1e4, 1e4]
    r += line_res(OBS["deck_edge_line"], (X1, lamp_y + 6, 0), (X1, lamp_y - 6, 0), c)
    for k, p in (("box_plusY_top_near", (HX0 - 0.06, HY1 + 0.06, PH)), ("box_plusY_top_far", (HX1, HY1 + 0.06, PH))):
        q, df = proj(p, c); r += list(q - OBS[k]) if df > 0 else [1e4, 1e4]
    q, df = proj((HX0 - 0.06, HY0, PH), c); r += list((q - OBS["box_raised_start"]) * 0.5) if df > 0 else [1e4, 1e4]
    r += line_res(OBS["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)
    r += [x * 0.5 for x in line_res(OBS["box_far_rim_line"], (HX1, HY1, PH), (HX1, HY0, PH), c)]
    r += [max(0.0, 0.3 - c[2]) * 1e4]
    return np.array(r)


def main():
    out = {"obs_11246": OBS, "assumption": "가장자리 등 대응: 화면 앞쪽 등 = 시설 쪽 등 중 하나(후보별로 시험). 먼 쪽 등(310, 482)은 뒤쪽 슬래브 위로 보여 쓰지 않음", "fits": []}
    inits = [(x, y, z, math.radians(yw), -0.05, f) for x, y, z, yw, f in itertools.product((2.0, 6.0), (-8.0, -3.0, 2.0), (1.6,), (-60, -30, 0), (3000, 4500))]
    for ly in LAMP_Y:
        s, c, r = best_fit(lambda q: res(q, ly), inits)
        raw = {"edge_light_near": round(float(np.linalg.norm(proj((X1 - INS, ly, 0.06), c)[0] - OBS["edge_light_near"])), 1),
               "deck_edge_line": [round(abs(x), 1) for x in line_res(OBS["deck_edge_line"], (X1, ly + 6, 0), (X1, ly - 6, 0), c)],
               "box_plusY_top_near": round(float(np.linalg.norm(proj((HX0 - 0.06, HY1 + 0.06, PH), c)[0] - OBS["box_plusY_top_near"])), 1),
               "box_plusY_top_far": round(float(np.linalg.norm(proj((HX1, HY1 + 0.06, PH), c)[0] - OBS["box_plusY_top_far"])), 1),
               "box_raised_start": round(float(np.linalg.norm(proj((HX0 - 0.06, HY0, PH), c)[0] - OBS["box_raised_start"])), 1),
               "box_base_line": [round(abs(x), 1) for x in line_res(OBS["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)],
               "box_far_rim_line": [round(abs(x), 1) for x in line_res(OBS["box_far_rim_line"], (HX1, HY1, PH), (HX1, HY0, PH), c)]}
        out["fits"].append({"near_lamp_y": ly, "rms_weighted": round(s, 1), "cam": cam_dict(c), "raw_err_px": raw})
        print(ly, round(s, 1), cam_dict(c), raw)
    out["fits"].sort(key=lambda f: f["rms_weighted"])
    json.dump(out, open(os.path.join(HERE, "m10_result.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
