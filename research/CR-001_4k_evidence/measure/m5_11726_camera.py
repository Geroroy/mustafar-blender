"""M5 — 11726(주 검증 프레임) 근사 카메라 맞춤. 형상은 v0.3 모델 값으로 고정하고 카메라만 푼다.
H1(출입구 위치·앞 바닥·핀 삭제)에 속하는 점은 맞춤에 쓰지 않고, 맞춘 카메라로 투영해 평가만 한다.
입력: 아래 상수(4K 픽셀, 확대 격자 판독)와 v0.3/dimensions.json. 출력: m5_result.json
가정: 핀홀, 주점 = 화면 중심, 롤 0, f는 범위로 훑음. 모델 좌표: +X 시설, +Y 절벽(뒤), Z 위."""
import itertools, json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
v = lambda *k: (lambda d: d["value"] if isinstance(d, dict) and "value" in d else d)(__import__("functools").reduce(lambda a, b: a[b], k, D))
CX, CY = 1920.0, 800.0
X1 = v("platform", "facility_edge_x"); XW = X1 + v("facility", "trench_gap"); OVER = v("facility", "roof_overhang"); BEAM = v("facility", "beam_height")
SPOT_X, SPOT_Z = XW - OVER + 0.65, BEAM - 0.175
SPOTS_Y = v("spotlights", "y_positions")
HX0 = v("stairwell", "corner_back_left")[0]; HY1 = v("stairwell", "corner_back_left")[1]; HY0 = HY1 - v("stairwell", "size_y")
PH = v("stairwell", "parapet_height"); SKO = D["v03"]["stairwell_skin"]["skirt_out"]["value"]
E = D["v03"]["entrance"]; EYC, ELC, EW = E["center_y"]["value"], E["light_center_height"]["value"], E["width"]["value"]
OUTER = E["frame_layers"]["value"][-1]

# ---- 11726 관측 (4K px). 판독 오차: 조명 ±3, 모서리 ±10~40
OBS = {
    "eave_light_A": (235, 218), "eave_light_B": (912, 212),                     # 처마 조명 2점(왼쪽이 +Y 쪽)
    "box_top_near_edge": [(1600, 1007), (2000, 1007), (2500, 1009)],          # 상자 근면 윗모서리(직선 위의 점)
    "box_top_right_end": (2560, 1008),                                        # 근면 윗모서리 오른쪽 끝(−Y 끝), ±40
    "box_base_near_edge": [(2300, 1290)],                                     # 근면 밑변(경사 패널 바닥)
    "deck_edge_far": [(300, 1170), (900, 1172)],                              # 왼쪽: 바닥과 벽 밑동이 만나는 선
}
DOOR_OBS = {"door_light": (2590, 322), "door_outer_base_right": (3000, 1168)}  # H1 평가용(맞춤에 안 씀)
UNMATCHED = {
    "inner_flat_top": "11726 문 안쪽 어두운 사다리꼴의 평평한 윗변(v≈490, x 2450~2740): 모델에 대응 요소 없음(통로 안쪽 깊이·천장 형태 미확정)",
    "door_threshold": "문턱: 계단 상자에 가려 보이지 않음",
    "door_shoulders": "어깨점: 11726에서는 비스듬한 시점·연기로 꺾임이 보이지 않음(11748에서만 판독)",
    "box_left_end": "상자 왼쪽(+Y) 끝: 인물(x 1380~1520)에 가림",
    "fin": "처마 조명 사이 지지부(x≈450~650): 모델 핀은 기울어 위아래 y가 6 m 달라 단일 점 대응이 모호 — 맞춤에서 제외, 투영만 비교",
}


def R_of(yaw, pitch):
    """카메라 → 월드 회전. yaw: +Y 쪽으로 돈 각(0 = +X를 봄), pitch: 위로 든 각."""
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


def residuals(cam, sA, sB):
    r = []
    for key, sy in (("eave_light_A", sA), ("eave_light_B", sB)):
        p, df = proj((SPOT_X, sy, SPOT_Z), cam); r += list(p - OBS[key]) if df > 0 else [1e4, 1e4]
    r += line_res(OBS["box_top_near_edge"], (HX0 - 0.06, HY1, PH), (HX0 - 0.06, HY0, PH), cam)
    p, _ = proj((HX0 - 0.06, HY0, PH), cam); r += list((p - OBS["box_top_right_end"]) / 4.0)       # ±40 px → 가중 1/4
    r += [x / 2.0 for x in line_res(OBS["box_base_near_edge"], (HX0 - SKO, HY1, 0), (HX0 - SKO, HY0, 0), cam)]
    r += line_res(OBS["deck_edge_far"], (X1, 10.0, 0), (X1, -5.0, 0), cam)
    return np.array(r)


def lm(cam0, sA, sB, iters=200):
    cam = np.array(cam0, float); lam = 1e-2; fix_f = cam[5]
    for _ in range(iters):
        r = residuals(cam, sA, sB); J = np.zeros((len(r), 5))
        for k in range(5):
            dc = np.zeros(6); dc[k] = 1e-4 if k < 3 else 1e-5; J[:, k] = (residuals(cam + dc, sA, sB) - r) / dc[k]
        A = J.T @ J; g = J.T @ r
        step = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
        new = cam.copy(); new[:5] += step; new[5] = fix_f
        if np.sum(residuals(new, sA, sB) ** 2) < np.sum(r ** 2): cam, lam = new, lam * 0.5
        else: lam *= 4
        if np.linalg.norm(step) < 1e-7: break
    return cam, residuals(cam, sA, sB)


def door_pts(yc):
    return {"door_light": (XW - 0.25, yc, ELC), "door_outer_base_right": (XW - 0.15, yc - EW / 2 - OUTER[1] * EW, 0.0)}


def ratio_check():
    """카메라와 무관한 검사: 같은 바닥에서 잰 화면 높이 비. 상자 근면은 문보다 카메라에 가까우므로
    (문 조명 높이 / 상자 윗모서리 높이) ≥ (문 px / 상자 px)."""
    door_px = DOOR_OBS["door_outer_base_right"][1] - DOOR_OBS["door_light"][1]
    box_px = OBS["box_base_near_edge"][0][1] - OBS["box_top_near_edge"][2][1]
    r = door_px / box_px
    return {"door_px_floor_to_light": door_px, "box_px_floor_to_top": box_px, "min_ratio_door_light_over_box_top": round(r, 2),
            "model_ratio": round(ELC / PH, 2), "if_box_kept_door_light_at_least_m": round(r * PH, 2), "if_door_kept_box_at_most_m": round(ELC / r, 2),
            "note": "판독 오차(문 조명 ±3, 바닥 ±15, 상자 윗모서리 ±5 px)로 비 ±0.2. 바닥이 평평하다는 가정"}


def main():
    out = {"ratio_check_11726": ratio_check(), "what_if_note": "what_if_box_*는 상자 높이만 다른 고정 형상으로 카메라를 다시 푼 민감도 분석이다. 모델은 바꾸지 않았고 채택하지 않는다.", "assumptions": {"principal_point": [CX, CY], "roll": 0, "geometry": "v0.3 dimensions.json 고정", "obs": OBS, "door_obs": DOOR_OBS},
           "unmatched": UNMATCHED, "fits": []}
    pairs = [(SPOTS_Y[i], SPOTS_Y[i + 1]) for i in range(len(SPOTS_Y) - 1)]          # (A=+Y 쪽, B)
    global PH
    runs = [("model", PH)] + [("what_if_box_" + str(h), h) for h in (0.75,)]
    for (tag, ph), (sA, sB), f in itertools.product(runs, pairs, (2200, 2800, 3500, 4500, 5500)):
        PH = ph
        best = None
        for cx, cy, cz, yaw in itertools.product((4.0, 8.0), (-28.0, -22.0, -16.0), (1.2, 2.0), (0.0, 0.3, 0.6)):
            cam, r = lm((cx, cy, cz, yaw, 0.02, f), sA, sB)
            s = float(np.sqrt(np.mean(r ** 2)))
            if best is None or s < best[0]: best = (s, cam, r)
        s, cam, r = best
        dp = {k: [round(float(c), 1) for c in proj(p, cam)[0]] for k, p in door_pts(EYC).items()}
        derr = {k: round(float(np.linalg.norm(np.array(dp[k]) - DOOR_OBS[k])), 1) for k in dp}
        ys = np.arange(-24.0, -6.0, 0.05)                                             # 문 조명이 관측과 맞는 문 중심 y
        e = [abs(proj(door_pts(y)["door_light"], cam)[0][0] - DOOR_OBS["door_light"][0]) for y in ys]
        y_best = float(ys[int(np.argmin(e))])
        spots_px = {str(y): [round(float(c)) for c in proj((SPOT_X, y, SPOT_Z), cam)[0]] for y in SPOTS_Y if proj((SPOT_X, y, SPOT_Z), cam)[1] > 0}
        fins = []
        for fy in (-17.7, -12.2, -6.7, -1.2):                                            # 핀 중심(바닥·위) 투영
            lean = math.radians(v("fins", "lean_deg")); h = BEAM - v("facility", "trench_floor_z"); dy = h / 2 * math.tan(lean)
            zc = (BEAM + v("facility", "trench_floor_z")) / 2
            fins.append({"y": fy, "bottom": [round(float(c)) for c in proj((XW - 0.6, fy - dy, zc - h / 2), cam)[0]],
                         "top": [round(float(c)) for c in proj((XW - 0.6, fy + dy, zc + h / 2), cam)[0]]})
        out["fits"].append({"geometry": tag, "spots_AB": [sA, sB], "f": f, "rms_px": round(s, 1), "resid": [round(float(x), 1) for x in r],
                            "cam": {"xyz": [round(float(c), 2) for c in cam[:3]], "yaw_deg": round(math.degrees(cam[3]), 1), "pitch_deg": round(math.degrees(cam[4]), 1)},
                            "door_proj_px_H1": dp, "door_err_px_H1": derr, "door_center_y_matching_light_x": round(y_best, 2),
                            "spots_proj_px": spots_px, "fins_proj_px": fins})
    out["fits"].sort(key=lambda r: (r["geometry"] != "model", r["rms_px"]))
    print("ratio", out["ratio_check_11726"])
    json.dump(out, open(os.path.join(HERE, "m5_result.json"), "w"), ensure_ascii=False, indent=1)
    for r in [x for x in out["fits"] if x["geometry"] == "model"][:4] + [x for x in out["fits"] if x["geometry"] != "model"][:4]:
        print(r["geometry"], r["spots_AB"], r["f"], r["rms_px"], r["cam"], "door_err", r["door_err_px_H1"], "door_y*", r["door_center_y_matching_light_x"])


if __name__ == "__main__":
    main()
