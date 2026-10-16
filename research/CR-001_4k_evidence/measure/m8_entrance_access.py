"""M8 — 출입구 접근 배치 후보(H1·A1·A2)를 11748·11726의 화면 관계와 대조한다(CR-006). 영화 파일 불필요(픽셀 상수 내장).
① 11748: 카메라를 **출입구 점만으로** 맞춘다(출입구 국소 좌표, 형상 = 출입구 후보값). 후보마다 출입구에 대한 상자의 상대 위치가 다르므로,
   같은 카메라로 상자를 투영해 영화의 왼쪽 상자(L)와 비교한다. f는 범위로 훑는다(평면에 가까운 출입구 점만으로는 f·거리가 잘 갈리지 않음).
② 11726: M5 카메라(처마 조명·상자·바닥선으로 맞춤, 출입구 제외)는 후보와 무관한 형상으로 풀었으므로 그대로 쓰고, 후보마다 출입구 점을 투영해 비교한다.
가정: 핀홀, 주점 = 화면 중심, 롤 0. 출입구 조명 중심 2.4 m·폭 1.45 m·어깨 0.42는 후보값(측정 정의 그대로). 결과는 후보 비교용이며 확정 치수가 아니다."""
import itertools, json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
v = lambda *k: (lambda n: n["value"] if isinstance(n, dict) and "value" in n else n)(__import__("functools").reduce(lambda a, b: a[b], k, D))
CX, CY = 1920.0, 800.0
X1 = v("platform", "facility_edge_x"); XW = X1 + v("facility", "trench_gap")
E = D["v03"]["entrance"]; EW, ELC, ESF = E["width"]["value"], E["light_center_height"]["value"], E["shoulder_frac"]["value"]; EZS = ELC * ESF
XF0 = E["frame_layers"]["value"][0][2]                 # 안쪽 층 돌출(문 가장자리 앞면)
HX0, HY1 = v("stairwell", "corner_back_left"); HX1 = HX0 + v("stairwell", "size_x"); HY0 = HY1 - v("stairwell", "size_y")
PH = v("stairwell", "parapet_height"); SK = D["v03"]["stairwell_skin"]; SKO = SK["skirt_out"]["value"]; NEND = SK["end_tiers"]["value"]
LAYS = D["v03"]["entrance_layout"]["candidates"]

# ---- 관측 (4K px, 확대 격자 판독 ±5~15 px). 왼쪽 = +Y (카메라가 대략 +X를 봄)
OBS_11748 = {
    "door_light": (1080, 295),                 # 꼭대기 조명 중심
    "shoulder_plusY": (735, 820),              # 안쪽 밝은 경사 띠가 세로 문설주로 꺾이는 점(화면 왼쪽)
    "shoulder_minusY": (1325, 828),            # 같은 점(화면 오른쪽)
    "jamb_minusY_foot": (1352, 1222),          # 오른쪽 안쪽 문설주 발치(문턱 끝)
    "threshold_line": [(1050, 1222), (1250, 1222)],   # 밝은 바닥 → 어두운 통로 바닥 경계(문턱 앞)
}
BOX_L_11748 = {                                 # 출입구 왼쪽 낮은 상자 L (11726 앞 상자와 끝 단 모양이 같음 — PROBABLE: 같은 상자)
    "base_line": [(100, 1385), (800, 1380)],   # 근면(−X쪽) 밑변
    "end_tier_foot": (970, 1278),              # −Y 끝 단의 가장 오른쪽 아래(문설주 발치 앞)
    "rim_minusY_end": (790, 1062),             # 근면 윗테두리의 −Y 끝
    "covers_jamb_plusY_foot": True,            # 왼쪽 문설주 발치가 L의 끝 단에 가려 보이지 않음
}
BOX_R_11748 = {"rim_line": [(2150, 1050), (2700, 1052)], "minusY_end_top": (2785, 1060), "minusY_end_base": (2795, 1258),
               "base_line": [(2000, 1272), (2700, 1262)], "note": "오른쪽 사다리꼴 구획 구조물 R. 모델에 없음(위치 근거 없음)"}
FRONT_EDGE_11748 = {"floor_edge_beyond_R": [(2850, 1262), (3300, 1300)], "curb": [(3340, 1240), (3670, 1375)],
                    "note": "R 너머 바닥 끝(용암 경계)과 연석 — 앞 변(−Y)으로 보임(PROBABLE)"}
OBS_11726 = {
    "door_light": (2590, 322), "door_outer_base_minusY": (3000, 1168),
    "box_A_plusY_end": (1580, 1010), "box_A_rim": [(1700, 1010), (2500, 1010)], "box_A_raised_start": (2555, 975),
    "box_A_minusY_end_foot": (2990, 1240), "box_A_base": [(2300, 1290)],
    "floor_beyond_A": [(3000, 1185), (3840, 1300)], "box_B": [(3380, 1080), (3840, 1200)],
    "lava_above_floor_x": [3330, 3560],
    "threshold": "상자 A에 가림",
}


def R_of(yaw, pitch):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    fwd = np.array([cp * cy, cp * sy, sp]); right = np.array([sy, -cy, 0.0]); up = np.cross(right, fwd)
    return fwd, right, up


def proj(p, cam):
    x, y, z, yaw, pitch, f = cam
    fwd, right, up = R_of(yaw, pitch); d = np.asarray(p, float) - np.array([x, y, z]); df = d @ fwd
    return np.array([CX + f * (d @ right) / df, CY - f * (d @ up) / df]), df


def line_res(pts, a, b, cam):
    (pa, _), (pb, _) = proj(a, cam), proj(b, cam); t = (pb - pa) / np.linalg.norm(pb - pa); n = np.array([-t[1], t[0]])
    return [float((np.asarray(q) - pa) @ n) for q in pts]


# 출입구 국소 좌표: 원점 = 벽면(XW)·출입구 중심·바닥
ENT = {"door_light": (-0.25, 0.0, ELC), "shoulder_plusY": (-XF0, EW / 2, EZS), "shoulder_minusY": (-XF0, -EW / 2, EZS),
       "jamb_minusY_foot": (-XF0, -EW / 2, 0.0)}


def res_11748(cam):
    r = []
    for k, p in ENT.items():
        q, df = proj(p, cam); r += list(q - OBS_11748[k]) if df > 0 else [1e4, 1e4]
    r += [x * 0.5 for x in line_res(OBS_11748["threshold_line"], (-XF0, 1.0, 0.0), (-XF0, -1.0, 0.0), cam)]   # 문턱선 위치 모호 → 가중 ½
    return np.array(r)


def lm(fun, cam0, iters=300):
    cam = np.array(cam0, float); lam = 1e-2
    for _ in range(iters):
        r = fun(cam); J = np.zeros((len(r), 5))
        for k in range(5):
            dc = np.zeros(6); dc[k] = 1e-4 if k < 3 else 1e-5; J[:, k] = (fun(cam + dc) - r) / dc[k]
        A = J.T @ J; g = J.T @ r
        step = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
        new = cam.copy(); new[:5] += step
        if np.sum(fun(new) ** 2) < np.sum(r ** 2): cam, lam = new, lam * 0.5
        else: lam *= 4
        if np.linalg.norm(step) < 1e-8: break
    return cam, fun(cam)


def box_local(eyc, xe):
    """상자 특징점을 출입구 국소 좌표로(후보마다 출입구 위치가 다름)."""
    o = np.array([xe, eyc, 0.0]); y_end = HY0 - 0.3 * NEND
    P = {"base_a": (HX0 - SKO, HY1, 0.0), "base_b": (HX0 - SKO, HY0, 0.0), "rim_minusY_end": (HX0 - 0.06, HY0, PH)}
    feet = [(HX0 - 0.06, y_end, 0.0), (HX0 + 0.35, y_end, 0.0), (HX1 - 0.35, y_end, 0.0), (HX1, y_end, 0.0), (HX1, HY0, 0.0)]
    return {k: np.array(p) - o for k, p in P.items()}, [np.array(p) - o for p in feet]


def main():
    out = {"assumptions": {"principal_point": [CX, CY], "roll": 0, "entrance_geometry": "후보값(조명 중심 2.4 m, 폭 1.45 m, 어깨 0.42×2.4 m, 안쪽 층 돌출 0.30 m)",
                           "f_scan_px": [2200, 2800, 3500, 4500, 5500]},
           "obs_11748": OBS_11748, "box_L_11748": BOX_L_11748, "box_R_11748": BOX_R_11748, "front_edge_11748": FRONT_EDGE_11748, "obs_11726": OBS_11726,
           "test1_11748": [], "test2_11726": []}
    # ① 11748: 출입구만으로 카메라(국소 좌표). 후보와 무관(출입구 형상은 모든 후보에서 같음)
    cams = []
    for f in out["assumptions"]["f_scan_px"]:
        best = None
        for cx, cy, cz, yaw in itertools.product((-6.0, -10.0, -14.0), (-6.0, -3.0, 0.0, 3.0), (1.0, 1.8), (-0.4, 0.0, 0.4)):
            cam, r = lm(lambda c: res_11748(np.r_[c[:5], f]), (cx, cy, cz, yaw, 0.05, f))
            cam[5] = f; s = float(np.sqrt(np.mean(r ** 2)))
            if cam[0] < -0.5 and (best is None or s < best[0]): best = (s, cam, r)
        cams.append((f, best))
    for f, (s, cam, r) in cams:
        row = {"f": f, "rms_px_entrance_fit": round(s, 1), "cam_local": {"xyz": [round(float(c), 2) for c in cam[:3]], "yaw_deg": round(math.degrees(cam[3]), 1),
               "pitch_deg": round(math.degrees(cam[4]), 1)}, "candidates": {}}
        for name, L in LAYS.items():
            P, feet = box_local(L["center_y"], L.get("front_x") or XW)
            base_err = [abs(x) for x in line_res(BOX_L_11748["base_line"], P["base_a"], P["base_b"], cam)]
            fp = [proj(p, cam)[0] for p in feet]; k = int(np.argmax([q[0] for q in fp])); foot = fp[k]
            rim = proj(P["rim_minusY_end"], cam)[0]
            jamb_plus = proj((-XF0, EW / 2, 0.0), cam)[0]                       # 왼쪽 문설주 발치(영화에서는 L에 가림)
            row["candidates"][name] = {
                "box_end_foot_px": [round(float(c)) for c in foot], "err_end_foot_px": round(float(np.linalg.norm(foot - BOX_L_11748["end_tier_foot"])), 1),
                "box_rim_minusY_end_px": [round(float(c)) for c in rim], "err_rim_end_px": round(float(np.linalg.norm(rim - BOX_L_11748["rim_minusY_end"])), 1),
                "err_base_line_px": [round(x, 1) for x in base_err],
                "jamb_plusY_foot_px": [round(float(c)) for c in jamb_plus],
                "box_end_right_of_jamb_plusY": bool(foot[0] > jamb_plus[0]),          # 상자 끝이 왼쪽 문설주 발치를 가릴 수 있는가(영화: 그렇다)
            }
        out["test1_11748"].append(row)
    # ③ 11748: 출입구만으로 푼 카메라(카메라 높이 ≥0.3 m인 f만)로 영화의 바닥 점(상자 L 밑변·끝 단 발치, 문턱, 상자 R, 앞 바닥 끝)을 바닥에 역투영해
    #    출입구 국소 좌표로 적는다. 출입구 높이 2.4 m·폭 1.45 m 가정을 그대로 물려받는다(문이 크면 거리도 비례해 커짐).
    out["test3_relative_placement"] = []
    for f in range(2000, 3401, 200):
        best = None
        for cx, cy, cz, yaw in itertools.product((-6.0, -10.0), (-3.0, 0.0, 3.0), (0.6, 1.5), (-0.4, 0.0, 0.4)):
            cam, r = lm(lambda c: res_11748(np.r_[c[:5], f]), (cx, cy, cz, yaw, 0.05, f))
            cam[5] = f; s_ = float(np.sqrt(np.mean(r ** 2)))
            if cam[0] < -0.5 and (best is None or s_ < best[0]): best = (s_, cam, r)
        s_, cam, r = best
        row = {"f": f, "rms_px_entrance_fit": round(s_, 1), "cam_local": {"xyz": [round(float(c), 2) for c in cam[:3]], "yaw_deg": round(math.degrees(cam[3]), 1),
               "pitch_deg": round(math.degrees(cam[4]), 1)}, "valid_camera_height": bool(cam[2] >= 0.3)}
        if cam[2] >= 0.3:
            fwd, right, up = R_of(cam[3], cam[4])
            def floor_pt(px):                                     # 화면 점 → 바닥(z=0) 위 출입구 국소 좌표
                d = fwd + right * (px[0] - CX) / f - up * (px[1] - CY) / f
                if d[2] >= 0: return None
                t_ = -cam[2] / d[2]; q = cam[:3] + t_ * d; return [round(float(q[0]), 2), round(float(q[1]), 2)]
            row["floor_points_local"] = {
                "box_L_base_line": [floor_pt(q) for q in BOX_L_11748["base_line"]],
                "box_L_end_tier_foot": floor_pt(BOX_L_11748["end_tier_foot"]),
                "threshold_line": [floor_pt(q) for q in OBS_11748["threshold_line"]],
                "box_R_base_line": [floor_pt(q) for q in BOX_R_11748["base_line"]], "box_R_minusY_end_base": floor_pt(BOX_R_11748["minusY_end_base"]),
                "front_floor_edge": [floor_pt(q) for q in FRONT_EDGE_11748["floor_edge_beyond_R"]]}
            # 모델 상자(R2 위치)의 근면 밑변 x와 끝 단 −Y 끝 y를 맞추면 출입구 벽면 x·중심 y가 어디여야 하는가
            bl = row["floor_points_local"]["box_L_base_line"]; ef = row["floor_points_local"]["box_L_end_tier_foot"]
            if all(bl) and ef:
                row["implied_entrance_wall_x_if_box_L_is_R2_box"] = round((HX0 - SKO) - float(np.mean([q[0] for q in bl])), 2)
                row["implied_entrance_center_y_if_box_L_is_R2_box"] = round((HY0 - 0.3 * NEND) - ef[1], 2)
        out["test3_relative_placement"].append(row)
    # ② 11726: M5 카메라(후보와 무관한 점으로 맞춤) → 후보별 출입구 투영
    m5 = json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))
    for fit in [x for x in m5["fits"] if x["geometry"] == "model"][:4]:
        c = fit["cam"]; cam = (*c["xyz"], math.radians(c["yaw_deg"]), math.radians(c["pitch_deg"]), fit["f"])
        row = {"m5_fit": {"spots_AB": fit["spots_AB"], "f": fit["f"], "rms_px_weighted": fit["rms_px_weighted"]}, "candidates": {}}
        for name, L in LAYS.items():
            y = L["center_y"]; xe = L.get("front_x") or XW; outer = E["frame_layers"]["value"][-1][1] * EW
            light = proj((xe - 0.25, y, ELC), cam)[0]; base = proj((xe - 0.15, y - EW / 2 - outer, 0.0), cam)[0]
            row["candidates"][name] = {"door_light_px": [round(float(q)) for q in light], "err_door_light_px": round(float(np.linalg.norm(light - OBS_11726["door_light"])), 1),
                                       "err_door_light_x_px": round(float(light[0] - OBS_11726["door_light"][0]), 1),
                                       "door_outer_base_px": [round(float(q)) for q in base], "err_door_outer_base_px": round(float(np.linalg.norm(base - OBS_11726["door_outer_base_minusY"])), 1)}
        out["test2_11726"].append(row)
    json.dump(out, open(os.path.join(HERE, "m8_result.json"), "w"), ensure_ascii=False, indent=1)
    for row in out["test1_11748"]:
        print("11748 f", row["f"], "entrance rms", row["rms_px_entrance_fit"], row["cam_local"],
              {n: (c["err_end_foot_px"], c["err_rim_end_px"], c["err_base_line_px"], c["box_end_right_of_jamb_plusY"]) for n, c in row["candidates"].items()})
    for row in out["test3_relative_placement"]:
        print("REL", row)
    for row in out["test2_11726"]:
        print("11726", row["m5_fit"], {n: (c["err_door_light_px"], c["err_door_light_x_px"], c["err_door_outer_base_px"]) for n, c in row["candidates"].items()})


if __name__ == "__main__":
    main()
