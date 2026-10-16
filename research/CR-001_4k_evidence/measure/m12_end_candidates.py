"""M12 — 낮은 상자 −Y 끝 형태 후보 평가와 높이·출입구 민감도(CR-008).
끝 형태(영화 윤곽): 주 테두리 → 짧게 솟음(모따기) → 솟은 블록 윗면 → 끝 단(한 단 + 경사 앞면) → 바닥 접점.
절대 길이·높이는 영화에서 직접 재지 못하므로 이산 후보로 둔다. 맨 −Y 바닥 접점은 A3 관계를 정한 값(y −19.4)으로 고정하고, 그 안에서 끝 형태를 배분한다.
  y5 = −19.4(고정), y3 = y5 + Lt(끝 단 길이), y2 = y3 + Lr(솟은 블록 윗면 길이), y1 = y2 + CH(모따기 0.2 m) = 주 테두리 끝
상자 본체 높이·위치(+Y 끝 y −12.0, x 범위), 출입구 크기, A3 배치는 이 단계에서 유지한다.
순서: 형상 후보 고정 → 프레임별 카메라 맞춤(6값, 롤 0) → 모든 점의 원시 오차. 맞춤 점과 평가 점을 구분한다.
  맞춤: 끝 형태와 무관한 점 + P1(테두리 끝)·P2(솟은 블록 시작) — 세 프레임 모두 직접 보임
  평가: P3(솟은 블록 끝)·P4(끝 단 윗면)·P5(바닥 접점), 가림 관계
f 탐색 범위 1500~8000 px. 범위 끝에 붙은 해는 표시하고 치수 근거로 쓰지 않는다.
실행: python3 m12_end_candidates.py end   → m12_end_result.json (끝 형태 후보, 상자 1.2 m·출입구 2.4 m)
      python3 m12_end_candidates.py sens  → m12_sens_result.json (선택한 끝 형태로 상자 높이 × 출입구 크기 민감도)"""
import itertools, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m9_a3_shape_fit as m  # noqa: E402
import m11_box_end as e11  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
XN, HX0, HX1, HY1, SKO = m.HX0 - 0.06, m.HX0, m.HX1, m.HY1, m.SKO
Y5, CH = round(m.YEND, 2), 0.2
F_LO, F_HI = 1500.0, 8000.0
EP = {f: {p: (st, px) for p, st, px, _ in v} for f, v in e11.END.items()}


def geom(ph, end):
    lt, lr, dh = end["Lt"], end["Lr"], end["dh"]
    y3 = Y5 + lt; y2 = y3 + lr; y1 = y2 + CH; zt = 0.75 * ph
    return {"y1": y1, "y2": y2, "y3": y3, "zt": zt, "ph": ph, "dh": dh,
            "P1": (XN, y1, ph), "P2": (XN, y2, ph + dh), "P3": (XN, y3, ph + dh), "P4": (XN, y3 - 0.25 * lt, zt), "P5": (HX0 - SKO, Y5, 0.0), "P5seg": ((HX0 - SKO, Y5, 0.0), (HX1, Y5, 0.0)),
            "parts": [np.array([(x, y, z) for x in xr for y in yr for z in zr]) for xr, yr, zr in (
                ((HX0 - SKO, HX1), (y1, HY1 + SKO), (0.0, ph)), ((XN, HX1), (y3, y1), (0.0, ph + dh)), ((XN, HX1), (Y5, y3), (0.0, zt)))]}


def hidden(p, c, G):
    q, dp = m.proj(p, c)
    for part in G["parts"]:
        pr = [m.proj(b, c) for b in part]
        if min(d for _, d in pr) <= 0: continue
        H = m.hull([x for x, _ in pr])
        if all(((H[(i + 1) % len(H)][0] - H[i][0]) * (q[1] - H[i][1]) - (H[(i + 1) % len(H)][1] - H[i][1]) * (q[0] - H[i][0])) >= 0 for i in range(len(H))) and dp > min(d for _, d in pr):
            return True
    return False


def pt_res(frame, part, G, c, w=1.0):
    st, px = EP[frame].get(part, (None, None))
    if px is None: return []
    q, df = m.proj(G[part], c); return list((q - px) * w) if df > 0 else [1e4, 1e4]


def bound_pen(c):
    return [max(0.0, 0.2 - c[2]) * 1e4]


def r48(c, G, h, w):
    P = m.ent(h, w); r = []
    for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"):
        q, df = m.proj(P[k], c); r += list(q - m.O48[k]) if df > 0 else [1e4, 1e4]
    r += [x * 0.5 for x in m.line_res(m.O48["threshold_line"], (m.XE - m.XF0, m.EYC + 1, 0), (m.XE - m.XF0, m.EYC - 1, 0), c)]
    r += m.line_res(m.O48["boxL_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)
    r += m.line_res(e11.RIM48, (XN, HY1, G["ph"]), (XN, G["y1"], G["ph"]), c)
    r += pt_res("11748", "P1", G, c) + pt_res("11748", "P2", G, c)
    return np.array(r + bound_pen(c))


def r26(c, G, h, w, fam):
    P = m.ent(h, w); r = []
    for key, sy in (("eave_light_A", fam[0]), ("eave_light_B", fam[1])):
        q, df = m.proj((m.SPOT_X, sy, m.SPOT_Z), c); r += list(q - m.O26[key]) if df > 0 else [1e4, 1e4]
    r += m.line_res(m.O26["box_rim_line"], (XN, HY1, G["ph"]), (XN, G["y1"], G["ph"]), c)
    r += [x / 2.0 for x in m.line_res(m.O26["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)]
    r += m.line_res(m.O26["deck_edge_line"], (m.X1, 10.0, 0), (m.X1, -5.0, 0), c)
    for k in ("door_light", "door_outer_base_minusY"):
        q, df = m.proj(P[k], c); r += list(q - m.O26[k]) if df > 0 else [1e4, 1e4]
    r += pt_res("11726", "P1", G, c) + pt_res("11726", "P2", G, c)
    return np.array(r + bound_pen(c))


def r46(c, G, lamp_y):
    O = e11.O46; r = []
    q, df = m.proj((m.X1 - e11.INS, lamp_y, 0.06), c); r += list(q - O["edge_light_near"]) if df > 0 else [1e4, 1e4]
    r += m.line_res(O["deck_edge_line"], (m.X1, lamp_y + 6, 0), (m.X1, lamp_y - 6, 0), c)
    for k, p in (("box_plusY_top_near", (XN, HY1 + 0.06, G["ph"])), ("box_plusY_top_far", (HX1, HY1 + 0.06, G["ph"]))):
        q, df = m.proj(p, c); r += list(q - O[k]) if df > 0 else [1e4, 1e4]
    r += m.line_res(O["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)
    r += [x * 0.5 for x in m.line_res(O["box_far_rim_line"], (HX1, HY1, G["ph"]), (HX1, G["y1"], G["ph"]), c)]
    r += pt_res("11246", "P1", G, c) + pt_res("11246", "P2", G, c)
    return np.array(r + [max(0.0, 0.3 - c[2]) * 1e4])


def lm(fun, c0, iters=120):
    c = np.array(c0, float); lam = 1e-2; sc = np.array([1e-4, 1e-4, 1e-4, 1e-5, 1e-5, 1e-1])
    for _ in range(iters):
        r = fun(c); J = np.zeros((len(r), 6))
        for k in range(6):
            dc = np.zeros(6); dc[k] = sc[k]; J[:, k] = (fun(c + dc) - r) / sc[k]
        A = J.T @ J; st = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), J.T @ r)
        n = c + st; n[5] = min(max(n[5], F_LO), F_HI)
        if np.sum(fun(n) ** 2) < np.sum(r ** 2): c, lam = n, lam * 0.5
        else: lam *= 4
        if np.linalg.norm(st) < 1e-8: break
    return c, fun(c)


def best(fun, inits):
    b = None
    for c0 in inits:
        c, r = lm(fun, c0); s = float(np.sqrt(np.mean(r ** 2)))
        if b is None or s < b[0]: b = (s, c)
    return b


def seg_err(px, a, b, c):
    """화면 점과 투영 선분 사이 거리(P5: 끝 바닥 접점은 시점에 따라 근면~원면 중 어느 점이 맨 끝으로 보이는지 달라 선분으로 대응)."""
    pa, pb = m.proj(a, c)[0], m.proj(b, c)[0]; d = pb - pa; t = float(np.clip(np.dot(np.array(px) - pa, d) / (np.dot(d, d) + 1e-9), 0, 1))
    return round(float(np.linalg.norm(np.array(px) - (pa + t * d))), 1)


def err(px, p, c):
    return round(float(np.linalg.norm(m.proj(p, c)[0] - np.array(px))), 1)


def lerr(pts, a, b, c):
    return [round(abs(x), 1) for x in m.line_res(pts, a, b, c)]


def raw(frame, c, G, h, w, extra=None):
    P = m.ent(h, w); fit, ev = {}, {}
    if frame == "11748":
        for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"): fit[k] = err(m.O48[k], P[k], c)
        fit["threshold_line"] = lerr(m.O48["threshold_line"], (m.XE - m.XF0, m.EYC + 1, 0), (m.XE - m.XF0, m.EYC - 1, 0), c)
        fit["box_base_line"] = lerr(m.O48["boxL_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)
        fit["main_rim_line"] = lerr(e11.RIM48, (XN, HY1, G["ph"]), (XN, G["y1"], G["ph"]), c)
        rel = {"jamb_plusY_foot_hidden(film: yes)": hidden(P["jamb_plusY_foot"], c, G), "threshold_mid_visible(film: yes)": not hidden(P["threshold_mid"], c, G),
               "jamb_minusY_foot_visible(film: yes)": not hidden(P["jamb_minusY_foot"], c, G)}
    elif frame == "11726":
        fam = extra
        fit["eave_light_A"] = err(m.O26["eave_light_A"], (m.SPOT_X, fam[0], m.SPOT_Z), c); fit["eave_light_B"] = err(m.O26["eave_light_B"], (m.SPOT_X, fam[1], m.SPOT_Z), c)
        fit["main_rim_line"] = lerr(m.O26["box_rim_line"], (XN, HY1, G["ph"]), (XN, G["y1"], G["ph"]), c)
        fit["box_base_line"] = lerr(m.O26["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)
        fit["deck_edge_line"] = lerr(m.O26["deck_edge_line"], (m.X1, 10.0, 0), (m.X1, -5.0, 0), c)
        for k in ("door_light", "door_outer_base_minusY"): fit[k] = err(m.O26[k], P[k], c)
        rel = {"threshold_mid_hidden(film: yes)": hidden(P["threshold_mid"], c, G), "jamb_plusY_foot_hidden(film: yes)": hidden(P["jamb_plusY_foot"], c, G),
               "door_outer_base_minusY_visible(film: yes)": not hidden(P["door_outer_base_minusY"], c, G)}
    else:
        O = e11.O46; ly = extra
        fit["edge_light_near"] = err(O["edge_light_near"], (m.X1 - e11.INS, ly, 0.06), c)
        fit["deck_edge_line"] = lerr(O["deck_edge_line"], (m.X1, ly + 6, 0), (m.X1, ly - 6, 0), c)
        fit["box_plusY_top_near"] = err(O["box_plusY_top_near"], (XN, HY1 + 0.06, G["ph"]), c); fit["box_plusY_top_far"] = err(O["box_plusY_top_far"], (HX1, HY1 + 0.06, G["ph"]), c)
        fit["box_base_line"] = lerr(O["box_base_line"], (HX0 - SKO, HY1, 0), (HX0 - SKO, G["y1"], 0), c)
        fit["far_rim_line"] = lerr(O["box_far_rim_line"], (HX1, HY1, G["ph"]), (HX1, G["y1"], G["ph"]), c)
        rel = {}
    for part in ("P1", "P2", "P3", "P4", "P5"):
        st, px = EP[frame].get(part, (None, None))
        if px is None: continue
        (fit if part in ("P1", "P2") else ev)[f"{part}({st})"] = seg_err(px, *G["P5seg"], c) if part == "P5" else err(px, G[part], c)
    allv = [x for v in fit.values() for x in (v if isinstance(v, list) else [v])]
    return {"fit_points_px": fit, "eval_points_px": ev, "relations": rel, "raw_rms_fit_points": round(float(np.sqrt(np.mean(np.square(allv)))), 1),
            "raw_rms_eval_points": round(float(np.sqrt(np.mean(np.square(list(ev.values()))))), 1) if ev else None}


def inits_from(prev, frame, base):
    out = [prev] if prev is not None else []
    return out + base[frame]


def run_frames(G, h, w, prev):
    base = {"11748": [(m.XE + dx, m.EYC + dy, z, math.radians(-12), 0.05, f) for dx, dy, z, f in itertools.product((-6.0, -10.0), (-1.0, 1.0), (0.6, 1.8), (2600, 4500))],
            "11726": [np.array([cx, cy, 1.8, math.radians(yw), 0.02, f]) for cx, cy, yw, f in itertools.product((-4.0, 4.0), (-24.0, -19.0), (10, 30), (2200, 4500))],
            "11246": [(x, y, 1.5, math.radians(yw), -0.02, f) for x, y, yw, f in itertools.product((2.0, 6.0), (-16.0, -8.0), (30, 50), (1800, 3500))]}
    res, cams = {}, {}
    s, c = best(lambda q: r48(q, G, h, w), inits_from(prev.get("11748"), "11748", base)); cams["11748"] = c
    res["11748"] = {"cam": m.cam_dict(c), "rms_weighted_fit": round(s, 1), "f_at_bound": bool(c[5] <= F_LO + 1 or c[5] >= F_HI - 1), **raw("11748", c, G, h, w)}
    res["11726"] = []
    for fam in ((0.0, -6.7), (6.7, 0.0)):
        s, c = best(lambda q: r26(q, G, h, w, fam), inits_from(prev.get(("11726", fam)), "11726", base)); cams[("11726", fam)] = c
        res["11726"].append({"family_spots_AB": list(fam), "cam": m.cam_dict(c), "rms_weighted_fit": round(s, 1), "f_at_bound": bool(c[5] <= F_LO + 1 or c[5] >= F_HI - 1), **raw("11726", c, G, h, w, fam)})
    res["11246"] = []
    for ly in (21.3, 10.7):
        s, c = best(lambda q: r46(q, G, ly), inits_from(prev.get(("11246", ly)), "11246", base)); cams[("11246", ly)] = c
        res["11246"].append({"near_lamp_y": ly, "cam": m.cam_dict(c), "rms_weighted_fit": round(s, 1), "f_at_bound": bool(c[5] <= F_LO + 1 or c[5] >= F_HI - 1), **raw("11246", c, G, h, w, ly)})
    return res, cams


def score(res):
    """끝 부위(평가 점 P3~P5 + 맞춤 점 P1·P2)의 프레임별 원시 오차 RMS — 11726은 (0, −6.7) 계열, 11246은 더 나은 등 대응."""
    v = []
    for fr in (res["11748"], res["11726"][0], min(res["11246"], key=lambda q: q["rms_weighted_fit"])):
        v += [x for k, x in {**fr["fit_points_px"], **fr["eval_points_px"]}.items() if k.startswith("P")]
    return round(float(np.sqrt(np.mean(np.square(v)))), 1)


def main_end():
    out = {"doc": __doc__.split("\n")[0], "fixed": {"extremity_y": Y5, "chamfer": CH, "box_height": m.PH, "door": [2.4, 1.45], "tier_top": "0.75 × 상자 높이"}, "rows": []}
    cands = [{"Lt": lt, "Lr": lr, "dh": dh} for lt in (0.6, 0.9, 1.2) for lr in (0.8, 1.2, 1.6, 2.0, 2.5) for dh in (0.15, 0.3)]
    prev = {}
    for end in cands:
        G = geom(m.PH, end); res, cams = run_frames(G, 2.4, 1.45, prev); prev = cams
        row = {"end": end, "y1_main_rim_end": round(G["y1"], 2), "y3_raised_end": round(G["y3"], 2), "score_end_parts_rms": score(res), "frames": res}
        out["rows"].append(row)
        print(end, "y1", round(G["y1"], 2), "score", row["score_end_parts_rms"], "| 48", res["11748"]["rms_weighted_fit"], res["11748"]["cam"]["f"], res["11748"]["eval_points_px"],
              "| 26", res["11726"][0]["rms_weighted_fit"], res["11726"][0]["eval_points_px"], "| 46", [(q["rms_weighted_fit"], q["cam"]["f"], q["eval_points_px"]) for q in res["11246"]], flush=True)
    out["rows"].sort(key=lambda r: r["score_end_parts_rms"])
    json.dump(out, open(os.path.join(HERE, "m12_end_result.json"), "w"), ensure_ascii=False, indent=1)


def main_sens():
    D = json.load(open(os.path.join(m.ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
    ef = D["v03"]["low_box"]["end_form"]; end = {"Lt": ef["tier_len"]["value"], "Lr": ef["raised_len"]["value"], "dh": ef["raised_dh"]["value"]}
    alt = {"Lt": 0.9, "Lr": 1.6, "dh": 0.15}                       # 11246 쪽이 선호한 끝 형태(견고성 확인용)
    out = {"doc": "상자 높이 × 출입구 크기 민감도(끝 형태 고정 — 선택값과 대안 하나, 자동 채택 안 함)", "end": end, "end_alt": alt, "rows": []}
    prev = {}
    for e_ in (end, alt):
        for ph in (1.2, 1.0, 0.8):
            for h, w in ((2.4, 1.45), (2.8, 1.6), (3.2, 1.8), (3.6, 1.8)):
                G = geom(ph, e_); res, cams = run_frames(G, h, w, prev); prev = cams
                out["rows"].append({"end": e_, "box_height": ph, "door": {"light_center_h": h, "width": w}, "score_end_parts_rms": score(res), "frames": res})
                b26 = res["11726"][0]
                print(e_, "PH", ph, "h", h, "w", w, "| 48", res["11748"]["rms_weighted_fit"], res["11748"]["cam"]["f"], res["11748"]["f_at_bound"], res["11748"]["raw_rms_fit_points"], res["11748"]["eval_points_px"],
                      "| 26", b26["rms_weighted_fit"], b26["cam"]["f"], b26["raw_rms_fit_points"], b26["fit_points_px"]["door_light"], b26["eval_points_px"],
                      "| 46", [(q["rms_weighted_fit"], q["cam"]["f"], q["f_at_bound"]) for q in res["11246"]], flush=True)
    json.dump(out, open(os.path.join(HERE, "m12_sens_result.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main_end() if sys.argv[1:] == ["end"] else main_sens()
