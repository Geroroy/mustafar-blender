"""M9 — A3 출입구 형상 재검토(CR-007). 순서: ① 형상 후보를 먼저 정한다(출입구 조명 중심 높이 h × 폭 w의 이산 집합, 위치는 A3 고정)
② 각 형상마다 11748·11726의 카메라를 따로 맞춘다(형상 고정, 카메라 6개 값 x·y·z·yaw·pitch·f만, 롤 0) ③ 모든 대응점의 원시 오차와 가림 관계를 함께 적는다.
카메라와 형상을 동시에 자유 조정하지 않는다(형상은 미리 정한 이산 후보 중 하나로 고정된 채 카메라만 푼다).
11726의 처마 조명 대응은 조명 쌍마다 별도 '카메라 계열'로 기록한다(같은 쌍을 쓰는 해는 독립이 아님).
R 구조물: 각 형상의 11748 카메라로 화면 외형을 바닥에 역투영한 위치(출입구 크기·카메라 가정에 의존하는 후보값)와, 그 R을 11726 카메라에 투영한 조건부 교차 대조.
영화 파일 불필요(픽셀 상수 내장). 실행: python3 m9_a3_shape_fit.py → m9_result.json"""
import itertools, json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
v = lambda *k: (lambda n: n["value"] if isinstance(n, dict) and "value" in n else n)(__import__("functools").reduce(lambda a, b: a[b], k, D))
CX, CY = 1920.0, 800.0
X1 = v("platform", "facility_edge_x"); XW = X1 + v("facility", "trench_gap"); OVER = v("facility", "roof_overhang"); BEAM = v("facility", "beam_height")
SPOT_X, SPOT_Z = XW - OVER + 0.65, BEAM - 0.175; SPOTS_Y = v("spotlights", "y_positions")
HX0, HY1 = v("stairwell", "corner_back_left"); HX1 = HX0 + v("stairwell", "size_x"); HY0 = HY1 - v("stairwell", "size_y")
PH = v("stairwell", "parapet_height"); SK = D["v03"]["stairwell_skin"]; SKO = SK["skirt_out"]["value"]; NEND = SK["end_tiers"]["value"]
YEND = HY0 - 0.3 * NEND
A3 = D["v03"]["entrance_layout"]["candidates"]["A3"]; XE, EYC = A3["front_x"], A3["center_y"]
E = D["v03"]["entrance"]; SFR = E["shoulder_frac"]["value"]; XF0 = E["frame_layers"]["value"][0][2]; OUTR = E["frame_layers"]["value"][-1][1]
SHAPES = [(h, w) for h in (2.4, 2.8, 3.2, 3.6) for w in (1.45, 1.6, 1.8)]

# ---- 관측 (4K px). 11748은 M8과 같은 판독 + R +Y 끝 발치 추가, 11726은 M5와 같은 판독 + 끝 단 발치·B
O48 = {"door_light": (1080, 295), "shoulder_plusY": (735, 820), "shoulder_minusY": (1325, 828), "jamb_minusY_foot": (1352, 1222),
       "threshold_line": [(1050, 1222), (1250, 1222)], "boxL_base_line": [(100, 1385), (800, 1380)], "boxL_rim_minusY_end": (425, 1078),    # 솟은 끝 블록이 시작하는 점(11726 M5 판독 (2560, 1008)과 같은 대응). (790, 1062)는 끝 단 위쪽이라 다른 점
       "boxL_end_tier_foot": (970, 1278)}
R48 = {"base_line": [(2100, 1272), (2700, 1262)], "minusY_end_base": (2795, 1258), "minusY_end_top": (2785, 1060),
       "plusY_end_foot": (1840, 1248), "rim_line": [(2150, 1050), (2700, 1052)], "front_floor_edge": [(2850, 1262), (3300, 1300)]}
O26 = {"eave_light_A": (235, 218), "eave_light_B": (912, 212), "box_rim_line": [(1600, 1007), (2000, 1007), (2500, 1009)],
       "box_rim_minusY_end": (2560, 1008), "box_base_line": [(2300, 1290)], "deck_edge_line": [(300, 1170), (900, 1172)],
       "door_light": (2590, 322), "door_outer_base_minusY": (3000, 1168), "box_end_tier_foot": (2990, 1240)}
B26 = {"plusY_end_x": 3380, "top_v": 1080, "base_v": 1190}
FAMILIES = [(SPOTS_Y[i], SPOTS_Y[i + 1]) for i in range(len(SPOTS_Y) - 1)]


def R_of(yaw, pitch):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    fwd = np.array([cp * cy, cp * sy, sp]); right = np.array([sy, -cy, 0.0]); up = np.cross(right, fwd)
    return fwd, right, up


def proj(p, c):
    fwd, right, up = R_of(c[3], c[4]); d = np.asarray(p, float) - c[:3]; df = d @ fwd
    return np.array([CX + c[5] * (d @ right) / df, CY - c[5] * (d @ up) / df]), df


def line_res(pts, a, b, c):
    (pa, _), (pb, _) = proj(a, c), proj(b, c); t = (pb - pa) / (np.linalg.norm(pb - pa) + 1e-9); n = np.array([-t[1], t[0]])
    return [float((np.asarray(q) - pa) @ n) for q in pts]


def ent(h, w):
    return {"door_light": (XE - 0.25, EYC, h), "shoulder_plusY": (XE - XF0, EYC + w / 2, SFR * h), "shoulder_minusY": (XE - XF0, EYC - w / 2, SFR * h),
            "jamb_minusY_foot": (XE - XF0, EYC - w / 2, 0.0), "jamb_plusY_foot": (XE - XF0, EYC + w / 2, 0.0), "threshold_mid": (XE - XF0, EYC, 0.0),
            "door_outer_base_minusY": (XE - 0.15, EYC - w / 2 - OUTR * w, 0.0)}


BOX_PARTS = [np.array([(x, y, z) for x in xr for y in yr for z in zr]) for xr, yr, zr in (     # 가림 판정용 볼록 부품: 본체(끝 벽까지)와 양옆 끝 단
    ((HX0 - SKO, HX1), (HY0, HY1 + SKO), (0.0, PH)), ((HX0 - 0.06, HX0 + 0.35), (YEND, HY0), (0.0, PH * NEND / (NEND + 1))),
    ((HX1 - 0.35, HX1), (YEND, HY0), (0.0, PH * NEND / (NEND + 1))))]


def hull(pts):
    pts = sorted(map(tuple, pts)); lo, up_ = [], []
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up_) >= 2 and cr(up_[-2], up_[-1], p) <= 0: up_.pop()
        up_.append(p)
    return lo[:-1] + up_[:-1]


def hidden_by_box(p, c):
    """점 p가 낮은 상자(본체 + 양옆 끝 단, 각각 볼록 외곽 근사)에 가려지는가."""
    q, dp = proj(p, c)
    for part in BOX_PARTS:
        pr = [proj(b, c) for b in part]
        if min(d for _, d in pr) <= 0: continue
        H = hull([x for x, _ in pr])
        inside = all(((H[(i + 1) % len(H)][0] - H[i][0]) * (q[1] - H[i][1]) - (H[(i + 1) % len(H)][1] - H[i][1]) * (q[0] - H[i][0])) >= 0 for i in range(len(H)))
        if inside and dp > min(d for _, d in pr): return True
    return False


def res48(c, h, w):
    P = ent(h, w); r = []
    for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"):
        q, df = proj(P[k], c); r += list(q - O48[k]) if df > 0 else [1e4, 1e4]
    r += [x * 0.5 for x in line_res(O48["threshold_line"], (XE - XF0, EYC + 1, 0), (XE - XF0, EYC - 1, 0), c)]
    r += line_res(O48["boxL_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)
    q, df = proj((HX0 - 0.06, HY0, PH), c); r += list((q - O48["boxL_rim_minusY_end"]) * 0.5) if df > 0 else [1e4, 1e4]
    r += [max(0.0, 0.2 - c[2]) * 1e4]
    return np.array(r)


def res26(c, h, w, fam, with_door=True):
    P = ent(h, w); r = []
    for key, sy in (("eave_light_A", fam[0]), ("eave_light_B", fam[1])):
        q, df = proj((SPOT_X, sy, SPOT_Z), c); r += list(q - O26[key]) if df > 0 else [1e4, 1e4]
    r += line_res(O26["box_rim_line"], (HX0 - 0.06, HY1, PH), (HX0 - 0.06, HY0, PH), c)
    q, _ = proj((HX0 - 0.06, HY0, PH), c); r += list((q - O26["box_rim_minusY_end"]) / 4.0)
    r += [x / 2.0 for x in line_res(O26["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)]
    r += line_res(O26["deck_edge_line"], (X1, 10.0, 0), (X1, -5.0, 0), c)
    if with_door:
        for k in ("door_light", "door_outer_base_minusY"):
            q, df = proj(P[k], c); r += list(q - O26[k]) if df > 0 else [1e4, 1e4]
    r += [max(0.0, 0.2 - c[2]) * 1e4]
    return np.array(r)


def lm(fun, c0, iters=120):
    c = np.array(c0, float); lam = 1e-2; sc = np.array([1e-4, 1e-4, 1e-4, 1e-5, 1e-5, 1e-1])
    for _ in range(iters):
        r = fun(c); J = np.zeros((len(r), 6))
        for k in range(6):
            dc = np.zeros(6); dc[k] = sc[k]; J[:, k] = (fun(c + dc) - r) / sc[k]
        A = J.T @ J; st = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), J.T @ r)
        n = c + st; n[5] = min(max(n[5], 1500.0), 8000.0)
        if np.sum(fun(n) ** 2) < np.sum(r ** 2): c, lam = n, lam * 0.5
        else: lam *= 4
        if np.linalg.norm(st) < 1e-8: break
    return c, fun(c)


def best_fit(fun, inits):
    best = None
    for c0 in inits:
        c, r = lm(fun, c0); s = float(np.sqrt(np.mean(r ** 2)))
        if best is None or s < best[0]: best = (s, c, r)
    return best


def cam_dict(c):
    return {"xyz": [round(float(x), 2) for x in c[:3]], "yaw_deg": round(math.degrees(c[3]), 1), "pitch_deg": round(math.degrees(c[4]), 1), "f": round(float(c[5]))}


def floor_pt(px, c):
    fwd, right, up = R_of(c[3], c[4]); d = fwd + right * (px[0] - CX) / c[5] - up * (px[1] - CY) / c[5]
    if d[2] >= 0: return None
    t = -c[2] / d[2]; return c[:3] + t * d


def height_above(base_px, top_px, c):
    """바닥 점(base_px) 위 수직선에서 top_px의 v에 맞는 높이."""
    b = floor_pt(base_px, c)
    if b is None: return None
    zs = np.linspace(0, 4, 401); vs = [proj((b[0], b[1], z), c)[0][1] for z in zs]
    return float(zs[int(np.argmin([abs(x - top_px[1]) for x in vs]))])


def raw48(c, h, w):
    P = ent(h, w); e = {}
    for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"):
        e[k] = round(float(np.linalg.norm(proj(P[k], c)[0] - O48[k])), 1)
    e["threshold_line"] = [round(abs(x), 1) for x in line_res(O48["threshold_line"], (XE - XF0, EYC + 1, 0), (XE - XF0, EYC - 1, 0), c)]
    e["boxL_base_line"] = [round(abs(x), 1) for x in line_res(O48["boxL_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)]
    e["boxL_rim_minusY_end"] = round(float(np.linalg.norm(proj((HX0 - 0.06, HY0, PH), c)[0] - O48["boxL_rim_minusY_end"])), 1)
    feet = [proj(q, c)[0] for q in ((HX0 - 0.06, YEND, 0), (HX0 + 0.35, YEND, 0), (HX1 - 0.35, YEND, 0), (HX1, YEND, 0))]
    e["boxL_end_tier_foot(eval)"] = round(float(min(np.linalg.norm(q - O48["boxL_end_tier_foot"]) for q in feet)), 1)
    rel = {"jamb_plusY_foot_hidden_by_box(film: yes)": hidden_by_box(P["jamb_plusY_foot"], c),
           "jamb_minusY_foot_visible(film: yes)": not hidden_by_box(P["jamb_minusY_foot"], c),
           "threshold_mid_visible(film: yes)": not hidden_by_box(P["threshold_mid"], c)}
    return e, rel


def raw26(c, h, w, fam):
    P = ent(h, w); e = {}
    for key, sy in (("eave_light_A", fam[0]), ("eave_light_B", fam[1])):
        e[key] = round(float(np.linalg.norm(proj((SPOT_X, sy, SPOT_Z), c)[0] - O26[key])), 1)
    e["box_rim_line"] = [round(abs(x), 1) for x in line_res(O26["box_rim_line"], (HX0 - 0.06, HY1, PH), (HX0 - 0.06, HY0, PH), c)]
    e["box_rim_minusY_end"] = round(float(np.linalg.norm(proj((HX0 - 0.06, HY0, PH), c)[0] - O26["box_rim_minusY_end"])), 1)
    e["box_base_line"] = [round(abs(x), 1) for x in line_res(O26["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), c)]
    e["deck_edge_line"] = [round(abs(x), 1) for x in line_res(O26["deck_edge_line"], (X1, 10.0, 0), (X1, -5.0, 0), c)]
    for k in ("door_light", "door_outer_base_minusY"):
        e[k] = round(float(np.linalg.norm(proj(P[k], c)[0] - O26[k])), 1)
    feet = [proj(q, c)[0] for q in ((HX0 - 0.06, YEND, 0), (HX1, YEND, 0))]
    e["box_end_tier_foot(eval)"] = round(float(min(np.linalg.norm(q - O26["box_end_tier_foot"]) for q in feet)), 1)
    rel = {"threshold_mid_hidden_by_box(film: yes)": hidden_by_box(P["threshold_mid"], c),
           "jamb_plusY_foot_hidden_by_box(film: yes)": hidden_by_box(P["jamb_plusY_foot"], c),
           "door_outer_base_minusY_visible(film: yes)": not hidden_by_box(P["door_outer_base_minusY"], c)}
    return e, rel


def r_from_11748(c):
    """R 화면 외형 → 바닥 역투영(세계 좌표). 출입구 크기·카메라 가정에 의존하는 후보값."""
    bl = [floor_pt(q, c) for q in R48["base_line"]]; me = floor_pt(R48["minusY_end_base"], c); pe = floor_pt(R48["plusY_end_foot"], c)
    fe = [floor_pt(q, c) for q in R48["front_floor_edge"]]
    if any(p is None for p in bl + [me, pe] + fe): return None
    hgt = height_above((2700, 1262), (2700, 1052), c)
    x_face = float(np.mean([p[0] for p in bl] + [me[0]]))
    return {"minusX_face_x": round(x_face, 2), "y_minus_end": round(float(me[1]), 2), "y_plus_end_foot": round(float(pe[1]), 2),
            "plus_end_foot_x": round(float(pe[0]), 2), "height": round(hgt, 2) if hgt is not None else None,
            "front_floor_edge_y": [round(float(p[1]), 2) for p in fe]}


def main():
    out = {"order": "형상 후보 고정 → 프레임별 카메라 맞춤(카메라 6값만). 형상과 카메라를 동시에 자유 조정하지 않음",
           "a3_position": {"front_x": XE, "center_y": EYC}, "shapes": SHAPES, "obs_11748": O48, "r_obs_11748": R48, "obs_11726": O26, "b_obs_11726": B26,
           "families_11726": FAMILIES, "rows": []}
    i48 = [(XE + dx, EYC + dy, z, math.radians(yw), 0.08, f) for dx, dy, z, yw, f in itertools.product((-6.0, -10.0), (-1.0, 1.5), (0.5, 1.5), (-15,), (2400, 4000))]
    m5 = [x for x in json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))["fits"] if x["geometry"] == "model"]
    for h, w in SHAPES:
        row = {"shape": {"light_center_h": h, "width": w}}
        s, c, _ = best_fit(lambda q: res48(q, h, w), i48)
        e, rel = raw48(c, h, w)
        row["11748"] = {"rms_weighted": round(s, 1), "cam": cam_dict(c), "raw_err_px": e, "relations": rel, "R_estimate": r_from_11748(c)}
        c48 = c
        fams = []
        for fam in FAMILIES:
            i26 = [np.array([*x["cam"]["xyz"], math.radians(x["cam"]["yaw_deg"]), math.radians(x["cam"]["pitch_deg"]), x["f"]]) for x in m5 if x["spots_AB"] == list(fam)][:3]
            i26 += [np.array([cx, cy, cz, math.radians(yw), 0.03, f]) for cx, cy, cz, yw, f in itertools.product((-6.0, 2.0), (-26.0, -18.0), (2.0,), (8, 25), (3000,))]
            for with_door in (True, False):
                s2, c2, _ = best_fit(lambda q: res26(q, h, w, fam, with_door), i26)
                e2, rel2 = raw26(c2, h, w, fam)
                fr = {"family_spots_AB": list(fam), "door_in_fit": with_door, "rms_weighted": round(s2, 1), "cam": cam_dict(c2), "raw_err_px": e2, "relations": rel2}
                R = row["11748"]["R_estimate"]
                if R:                                                        # R(11748 역투영)을 11726 카메라에 투영 → B와 조건부 교차 대조
                    p_plus = proj((R["minusX_face_x"], R["y_plus_end_foot"], R["height"] or 1.0), c2)[0]
                    p_base = proj((R["minusX_face_x"], (R["y_plus_end_foot"] + R["y_minus_end"]) / 2, 0.0), c2)[0]
                    fr["R_in_11726"] = {"plusY_end_top_px": [round(float(x)) for x in p_plus], "dx_vs_B_plusY_end": round(float(p_plus[0] - B26["plusY_end_x"]), 1),
                                        "dv_top_vs_B": round(float(p_plus[1] - B26["top_v"]), 1), "dv_base_vs_B": round(float(p_base[1] - B26["base_v"]), 1)}
                fams.append(fr)
        row["11726"] = fams
        out["rows"].append(row)
        b = min([f for f in fams if f["door_in_fit"]], key=lambda f: f["rms_weighted"])
        print(f"h {h} w {w} | 11748 rms {row['11748']['rms_weighted']} raw {e} rel {list(rel.values())} R {row['11748']['R_estimate']}")
        print(f"         11726 best family {b['family_spots_AB']} rms {b['rms_weighted']} raw {b['raw_err_px']} rel {list(b['relations'].values())} R {b.get('R_in_11726')}", flush=True)
    json.dump(out, open(os.path.join(HERE, "m9_result.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
