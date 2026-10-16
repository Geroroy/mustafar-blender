"""M13 — 출입구–상자 상대 위치 재검토(CR-009). 출입구 위치만 움직여 다른 형상 오류를 보정하지 않도록, 두 프레임에서 서로 독립인 방법으로 위치 단서를 얻는다.
① 11726 판독 확인: 처마 조명 2점 판독 유지, 상자 근면 윗모서리 v≈1018(M5 1007~1009에서 정정), 밑변 v≈1282, 바닥선(판 시설 쪽 가장자리) v≈1165~1172.
   카메라는 출입구 점을 빼고 맞춘다(처마 조명·바닥선·상자 윗모서리·밑변·P1·P2). 출입구는 모두 평가 전용.
   그 카메라로 출입구 바깥 테두리 −Y 발치(3000, 1168)를 바닥에 역투영 → 출입구 위치 단서(상자 끝 가정과 무관).
   꼭대기 조명(2590, 322)을 출입구 면에 역투영해 높이를 진단값으로 적는다(채택 안 함).
② 11748: 카메라를 출입구 점만으로 맞춘다(M8 방식, 출입구 형상 후보값). 바로잡은 상자 끝 바닥 접점(P5)과 근면 밑변을 바닥에 역투영 → 출입구에 대한 상자 끝 상대 위치.
③ 상자 끝 바닥 접점 y −19.4는 영화 확정값이 아닌 기존 모델 가정이다.
f 범위 1500~8000. 경계에 붙은 해는 위치 근거로 쓰지 않는다. 실행: python3 m13_entrance_position.py → m13_result.json"""
import itertools, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m9_a3_shape_fit as m  # noqa: E402
import m12_end_candidates as m12  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
O26 = {"eave_light_A": (235, 218), "eave_light_B": (905, 215), "deck_edge_line": [(300, 1168), (900, 1170)],
       "box_rim_line": [(1600, 1018), (2000, 1018), (2500, 1018)], "box_base_line": [(1900, 1282), (2400, 1285)],
       "P1": (2555, 1015), "P2": (2595, 978), "door_outer_base_minusY": (3000, 1168), "door_light": (2590, 322)}
O48 = {"door_light": (1080, 295), "shoulder_plusY": (735, 820), "shoulder_minusY": (1325, 828), "jamb_minusY_foot": (1352, 1222),
       "threshold_line": [(1050, 1222), (1250, 1222)], "P5": (975, 1283), "box_base_line": [(100, 1385), (800, 1380)]}
END = json.load(open(os.path.join(m.ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))["v03"]["low_box"]["end_form"]
ENDP = {"Lt": END["tier_len"]["value"], "Lr": END["raised_len"]["value"], "dh": END["raised_dh"]["value"]}
XN = m.HX0 - 0.06


def geom_y5(y5, ph=m.PH):
    G = m12.geom(ph, ENDP); dy = y5 - m12.Y5
    for k in ("y1", "y2", "y3"): G[k] += dy
    for k in ("P1", "P2", "P3", "P4", "P5"): G[k] = (G[k][0], G[k][1] + dy, G[k][2])
    return G


def r26(c, fam, G):
    r = []
    for key, sy in (("eave_light_A", fam[0]), ("eave_light_B", fam[1])):
        q, df = m.proj((m.SPOT_X, sy, m.SPOT_Z), c); r += list(q - O26[key]) if df > 0 else [1e4, 1e4]
    r += m.line_res(O26["deck_edge_line"], (m.X1, 10.0, 0), (m.X1, -5.0, 0), c)
    r += m.line_res(O26["box_rim_line"], (XN, m.HY1, m.PH), (XN, G["y1"], m.PH), c)
    r += [x / 2.0 for x in m.line_res(O26["box_base_line"], (m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, G["y1"], 0), c)]
    for k in ("P1", "P2"):
        q, df = m.proj(G[k], c); r += list(q - O26[k]) if df > 0 else [1e4, 1e4]
    return np.array(r + [max(0.0, 0.2 - c[2]) * 1e4])


def ray(px, c):
    fwd, right, up = m.R_of(c[3], c[4]); return c[:3], fwd + right * (px[0] - m.CX) / c[5] - up * (px[1] - m.CY) / c[5]


def floor_hit(px, c):
    o, d = ray(px, c)
    return None if d[2] >= 0 else o + (-o[2] / d[2]) * d


def plane_x_hit(px, c, x0):
    o, d = ray(px, c); t = (x0 - o[0]) / d[0]; return o + t * d


def fit_26(G, fam):
    m5 = [x for x in json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))["fits"] if x["geometry"] == "model"]
    inits = [np.array([*x["cam"]["xyz"], math.radians(x["cam"]["yaw_deg"]), math.radians(x["cam"]["pitch_deg"]), x["f"]]) for x in m5 if x["spots_AB"] == list(fam)][:3]
    inits += [np.array([cx, cy, cz, math.radians(yw), 0.0, f]) for cx, cy, cz, yw, f in itertools.product((-4.0, 0.0, 4.0), (-20.0, -15.0), (1.6, 2.4), (-5, 10), (2200, 3500))]
    return m12.best(lambda q: r26(q, fam, G), inits)


def e48_res(c, h=2.4, w=1.45):
    """11748 출입구 국소 좌표(원점 = 출입구 면·중심·바닥)에서 출입구 점만."""
    xf = m.XF0; r = []
    P = {"door_light": (-0.25, 0.0, h), "shoulder_plusY": (-xf, w / 2, m.SFR * h), "shoulder_minusY": (-xf, -w / 2, m.SFR * h), "jamb_minusY_foot": (-xf, -w / 2, 0.0)}
    for k, p in P.items():
        q, df = m.proj(p, c); r += list(q - O48[k]) if df > 0 else [1e4, 1e4]
    r += [x * 0.5 for x in m.line_res(O48["threshold_line"], (-xf, 1.0, 0.0), (-xf, -1.0, 0.0), c)]
    return np.array(r)


def main():
    out = {"doc": __doc__.split("\n")[0], "obs_11726": O26, "obs_11748": O48, "end_form": ENDP, "box_end_y_assumption": m12.Y5, "11726": [], "11748": []}
    G = geom_y5(m12.Y5)
    for fam in ((0.0, -6.7), (6.7, 0.0)):
        s, c = fit_26(G, fam)
        fb = floor_hit(O26["door_outer_base_minusY"], c)
        row = {"family_spots_AB": list(fam), "rms_weighted": round(s, 1), "cam": m.cam_dict(c), "f_at_bound": bool(c[5] <= 1501 or c[5] >= 7999)}
        if fb is not None:
            xe = fb[0] + 0.15; ey = fb[1] + 1.45 / 2 + m.OUTR * 1.45              # 바깥 테두리 −Y 발치 → 출입구 면 x·중심 y(폭 1.45 후보값)
            lp = plane_x_hit(O26["door_light"], c, xe - 0.25)
            row["door_outer_base_floor"] = [round(float(fb[0]), 2), round(float(fb[1]), 2)]
            row["implied_door_face_x"] = round(float(xe), 2); row["implied_door_center_y"] = round(float(ey), 2)
            row["diagnostic_door_light_height_m"] = round(float(lp[2]), 2)
        out["11726"].append(row)
        print("11726", row, flush=True)
    for f in range(2000, 3401, 200):
        best = None
        for cx, cy, cz, yw in itertools.product((-6.0, -10.0), (-3.0, 0.0, 3.0), (0.6, 1.5), (-0.4, 0.0, 0.4)):
            c, r = m12.lm(lambda q: np.r_[e48_res(np.r_[q[:5], f]), max(0.0, 0.2 - q[2]) * 1e4], (cx, cy, cz, yw, 0.05, f))
            c[5] = f; s = float(np.sqrt(np.mean(e48_res(c) ** 2)))
            if c[0] < -0.5 and (best is None or s < best[0]): best = (s, c)
        s, c = best
        row = {"f": f, "rms_entrance_fit": round(s, 1), "cam_local": m.cam_dict(c), "valid_camera_height": bool(c[2] >= 0.3)}
        if c[2] >= 0.3:
            p5 = floor_hit(O48["P5"], c); bl = [floor_hit(q, c) for q in O48["box_base_line"]]
            row["P5_local"] = [round(float(p5[0]), 2), round(float(p5[1]), 2)]
            row["box_base_x_local"] = round(float(np.mean([q[0] for q in bl])), 2)
            row["implied_door_center_y_if_box_end_fixed"] = round(float(m12.Y5 - p5[1]), 2)            # 상자 끝 바닥 접점 = −19.4(가정)
            row["implied_door_face_x_if_box_base_fixed"] = round(float((m.HX0 - m.SKO) - row["box_base_x_local"]), 2)
        out["11748"].append(row)
        print("11748", row, flush=True)
    json.dump(out, open(os.path.join(HERE, "m13_result.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__" and not sys.argv[1:]:
    main()


def cams_for_candidates():
    """후보별 평가 카메라(m13_cams.json). 11726: 출입구를 뺀 맞춤(후보의 상자 끝 반영), 11748: 출입구 점만(국소 좌표, 후보 공통), 11246: 상자·등·P1·P2."""
    D = json.load(open(os.path.join(m.ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
    L = D["v03"]["entrance_layout"]["candidates"]; out = {"candidates": {}, "11748_local": []}
    src = json.load(open(os.path.join(HERE, "m13_result.json"), encoding="utf-8"))
    out["11748_local"] = [{"f": r["f"], "cam_local": r["cam_local"]} for r in src["11748"] if r["valid_camera_height"]]
    for name in ("A3", "A3a", "A3b"):
        y5 = L[name].get("box_end_y") or m12.Y5; G = geom_y5(y5); rec = {"center_y": L[name]["center_y"], "front_x": L[name]["front_x"], "box_end_y": y5, "11726": [], "11246": []}
        for fam in ((0.0, -6.7), (6.7, 0.0)):
            s, c = fit_26(G, fam); rec["11726"].append({"family_spots_AB": list(fam), "rms_weighted": round(s, 1), "cam": m.cam_dict(c), "f_at_bound": bool(c[5] <= 1501 or c[5] >= 7999)})
        base = [(x, y, 1.5, math.radians(yw), -0.02, f) for x, y, yw, f in itertools.product((2.0, 6.0), (-16.0, -8.0), (30, 50), (1800, 3500))]
        for ly in (21.3, 10.7):
            s, c = m12.best(lambda q: m12.r46(q, G, ly), base)
            rec["11246"].append({"near_lamp_y": ly, "rms_weighted": round(s, 1), "cam": m.cam_dict(c), "f_at_bound": bool(c[5] <= 1501 or c[5] >= 7999)})
        out["candidates"][name] = rec; print(name, rec, flush=True)
    json.dump(out, open(os.path.join(HERE, "m13_cams.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__" and sys.argv[1:] == ["cams"]:
    cams_for_candidates()
