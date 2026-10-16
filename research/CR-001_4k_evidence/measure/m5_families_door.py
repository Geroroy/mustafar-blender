"""M5 해를 처마 조명 대응(조명 쌍)별 '카메라 계열'로 묶고, 각 해에서 후보(H1·A2·A3, 출입구 높이 2.4 m)의 출입구 점 원시 오차를 적는다(CR-007).
같은 조명 쌍을 쓰는 해들은 같은 대응 가정을 공유하므로 서로 독립이 아니다. 다른 계열의 큰 오차도 함께 기록한다.
이 대조는 '다른 프레임(11726)에서의 조건부 교차 대조'다(조건: 조명 대응, 상자·바닥선 대응, 출입구 형상 후보값).
실행: python3 m5_families_door.py → m5_families_door.json"""
import json, math, os
import numpy as np
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I 실행에서도 같은 폴더 모듈을 찾도록
import m8_entrance_access as m8

HERE = os.path.dirname(os.path.abspath(__file__))
fits = [f for f in json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))["fits"] if f["geometry"] == "model"]
out = {"note": __doc__.split("\n")[1], "door_obs_11726": {"door_light": [2590, 322], "door_outer_base_minusY": [3000, 1168]}, "families": []}
for fam in sorted({tuple(f["spots_AB"]) for f in fits}):
    rows = []
    for f in sorted([f for f in fits if tuple(f["spots_AB"]) == fam], key=lambda f: f["rms_px"]):
        c = f["cam"]; cam = (*c["xyz"], math.radians(c["yaw_deg"]), math.radians(c["pitch_deg"]), f["f"])
        r = {"f": f["f"], "rms_px_weighted_without_door": f["rms_px"], "cam": c, "door_err_px": {}}
        for n in ("H1", "A2", "A3"):
            L = m8.LAYS[n]; y = L["center_y"]; xe = L.get("front_x") or m8.XW; outer = m8.E["frame_layers"]["value"][-1][1] * m8.EW
            li = m8.proj((xe - 0.25, y, m8.ELC), cam)[0]; ba = m8.proj((xe - 0.15, y - m8.EW / 2 - outer, 0.0), cam)[0]
            r["door_err_px"][n] = {"door_light": round(float(np.linalg.norm(li - (2590, 322))), 1), "door_outer_base_minusY": round(float(np.linalg.norm(ba - (3000, 1168))), 1)}
        rows.append(r)
    out["families"].append({"spots_AB": list(fam), "solutions": rows})
json.dump(out, open(os.path.join(HERE, "m5_families_door.json"), "w"), ensure_ascii=False, indent=1)
for fm in out["families"]:
    b = fm["solutions"][0]; print(fm["spots_AB"], "best wrms", b["rms_px_weighted_without_door"], {n: tuple(v.values()) for n, v in b["door_err_px"].items()})
