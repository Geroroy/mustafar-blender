"""M9b — 민감도(채택 안 함): 낮은 상자 높이(기준안 1.2 m / 기존 후보 범위 안 0.8 m)를 바꾼 고정 형상에서 M9와 같은 방법으로 두 프레임 카메라를 다시 푼다.
형상(상자 높이 포함)은 미리 정한 이산 값으로 고정하고 카메라만 푼다. 모델은 바꾸지 않는다(상자 높이 1.2 m 기준안 유지).
실행: python3 m9b_box_height_sensitivity.py → m9b_result.json"""
import itertools, json, math, os
import numpy as np
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I 실행에서도 같은 폴더 모듈을 찾도록
import m9_a3_shape_fit as m

HERE = os.path.dirname(os.path.abspath(__file__))
SH = [(2.4, 1.45), (2.8, 1.6), (3.2, 1.8), (3.6, 1.8)]
FAMS = [(0.0, -6.7), (6.7, 0.0)]


def set_ph(ph):
    m.PH = ph
    parts = (((m.HX0 - m.SKO, m.HX1), (m.HY0, m.HY1 + m.SKO), (0.0, ph)), ((m.HX0 - 0.06, m.HX0 + 0.35), (m.YEND, m.HY0), (0.0, ph * 0.75)),
             ((m.HX1 - 0.35, m.HX1), (m.YEND, m.HY0), (0.0, ph * 0.75)))
    m.BOX_PARTS = [np.array([(x, y, z) for x in xr for y in yr for z in zr]) for xr, yr, zr in parts]


def main():
    out = {"note": __doc__.split("\n")[1], "rows": []}
    i48 = [(m.XE + dx, m.EYC + dy, z, math.radians(yw), 0.08, f) for dx, dy, z, yw, f in itertools.product((-6.0, -10.0), (-1.0, 1.5), (0.5, 1.5), (-15,), (2400, 4000))]
    m5 = [x for x in json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))["fits"] if x["geometry"] == "model"]
    for ph in (1.2, 0.8):
        set_ph(ph)
        for h, w in SH:
            s, c, _ = m.best_fit(lambda q: m.res48(q, h, w), i48); e, rel = m.raw48(c, h, w)
            row = {"box_height": ph, "shape": {"light_center_h": h, "width": w}, "11748": {"rms_weighted": round(s, 1), "cam": m.cam_dict(c), "raw_err_px": e, "relations": rel,
                                                                                         "R_estimate": m.r_from_11748(c)}, "11726": []}
            for fam in FAMS:
                i26 = [np.array([*x["cam"]["xyz"], math.radians(x["cam"]["yaw_deg"]), math.radians(x["cam"]["pitch_deg"]), x["f"]]) for x in m5 if x["spots_AB"] == list(fam)][:3]
                i26 += [np.array([cx, cy, 2.0, math.radians(yw), 0.03, 3000]) for cx, cy, yw in itertools.product((-6.0, 2.0), (-26.0, -18.0), (8, 25))]
                s2, c2, _ = m.best_fit(lambda q: m.res26(q, h, w, fam, True), i26); e2, rel2 = m.raw26(c2, h, w, fam)
                row["11726"].append({"family_spots_AB": list(fam), "rms_weighted": round(s2, 1), "cam": m.cam_dict(c2), "raw_err_px": e2, "relations": rel2})
            out["rows"].append(row)
            b = row["11726"][0]
            print("PH", ph, "h", h, "w", w, "| 11748", row["11748"]["rms_weighted"], row["11748"]["cam"]["f"], e["boxL_rim_minusY_end"], e["door_light"],
                  "| 11726(0,-6.7)", b["rms_weighted"], b["cam"]["f"], b["raw_err_px"]["box_base_line"], b["raw_err_px"]["box_rim_minusY_end"], b["raw_err_px"]["door_light"],
                  b["raw_err_px"]["door_outer_base_minusY"], list(b["relations"].values()), flush=True)
    json.dump(out, open(os.path.join(HERE, "m9b_result.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
