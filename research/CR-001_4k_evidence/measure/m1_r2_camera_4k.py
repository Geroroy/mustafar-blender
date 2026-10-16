"""M1 — R2 고정 카메라를 4K 프레임 5장(11609·11612·11615·11618·11621)의 인물 10개 관측으로 다시 푼다.
입력은 아래 PX(사람이 확대 격자에서 읽은 4K 픽셀, 3840×1600)뿐이다. 영화 이미지를 읽지 않으므로 이미지 없이 재현된다.
가정: 주점 = 화면 중심(1920, 800), 롤 0, 바닥 평면 Z=0, 인물 키 오비완 1.78 m · 아나킨 1.85 m(머리 꼭대기까지, 자세·신발 오차 ±3%).
초점거리 f는 인물 키만으로 잘 정해지지 않아 범위로 계산한다(v0.2의 2800/3500/4500 px × 1.30 = 3640/4550/5850 px).
실행: python3 m1_r2_camera_4k.py  (numpy 필요) → m1_result.json"""
import json
import os

import numpy as np

CX, CY = 1920.0, 800.0
H_OBI, H_ANA = 1.78, 1.85
# (frame, who, foot_u, foot_v, head_v)  — 발 = 땅에 닿은 발 아래 끝, 머리 = 머리카락 꼭대기
OBS = [
    (11615, "obi", 1615, 1305, 950), (11615, "ana", 2450, 1228, 868),
    (11609, "obi", 1500, 1220, 888), (11609, "ana", 2520, 1272, 903),
    (11612, "obi", 1556, 1262, 930), (11612, "ana", 2490, 1268, 888),
    (11618, "obi", 1700, 1372, 990), (11618, "ana", 2392, 1200, 868),
    (11621, "obi", 1858, 1395, 1020), (11621, "ana", 2370, 1168, 832),
]
PX_READ_ERR = 4      # 발·머리 판독 오차(px, 4K) — 흐림·그림자·머리카락
# 11615의 바닥/구조 대응점 (4K px)
PTS = {
    "edge_light_d": (2052, 691), "edge_light_e": (2326, 806), "edge_light_f": (2740, 980),   # 시설 쪽 가장자리 낮은 등
    "slab_light_a": (1709, 590), "slab_light_b": (2201, 559), "slab_light_c": (2650, 531),   # 뒤쪽 슬래브 윗면 등 (윗면이 판과 같은 높이라고 가정)
    "obiwan": (1615, 1305), "anakin": (2450, 1228), "padme_center": (2830, 1250),
    "ramp_foot_L": (1250, 1017), "ramp_foot_R": (1335, 985),
    "box_floor_corner": (3248, 1329),
}
BOX_RIM = (3297, 1176)                      # 계단 상자 윗모서리(바닥 모서리 바로 위)
SPOTS = [(2997, 69), (3343, 75), (3803, 80)]  # 처마 조명 3점
FIN_EDGE = [((3506, 423), (3311, 814))]      # 경사 지지부 한 개의 긴 모서리(위 → 아래)


def axes(th):
    F = np.array([0, np.cos(th), -np.sin(th)]); U = np.array([0, np.sin(th), np.cos(th)]); R = np.array([1.0, 0, 0])
    return R, U, F


def ray(u, v, f, th):
    R, U, F = axes(th)
    return R * (u - CX) / f + U * (-(v - CY) / f) + F


def ground(u, v, f, th, h, z=0.0):
    d = ray(u, v, f, th); C = np.array([0, 0, h])
    t = (z - h) / d[2]
    return C + t * d


def project(p, f, th, h):
    R, U, F = axes(th); d = np.asarray(p) - np.array([0, 0, h])
    return CX + f * d.dot(R) / d.dot(F), CY - f * d.dot(U) / d.dot(F)


def pred_head_v(u, v_foot, H, f, th, h):
    g = ground(u, v_foot, f, th, h)
    return project(g + np.array([0, 0, H]), f, th, h)[1]


def residuals(f, th, h, obs, heights):
    """벡터화: th, h 배열에 대한 머리 v 잔차 RMS (px)."""
    sq = 0.0
    for _, w, u, vf, vh in obs:
        H = heights[0] if w == "obi" else heights[1]
        dx = (u - CX) / f; dy = -(vf - CY) / f
        Fy, Fz = np.cos(th), -np.sin(th); Uy, Uz = np.sin(th), np.cos(th)
        d_y = dy * Uy + Fy; d_z = dy * Uz + Fz
        t = -h / d_z
        gy = t * d_y
        pz = H - h
        dF = gy * Fy + pz * Fz; dU = gy * Uy + pz * Uz
        v = CY - f * dU / dF
        sq = sq + (v - vh) ** 2
    return np.sqrt(sq / len(obs))


def solve(f, obs=OBS, heights=(H_OBI, H_ANA)):
    T, Hh = np.meshgrid(np.radians(np.arange(1.0, 25.0, 0.1)), np.arange(2.0, 9.0, 0.02), indexing="ij")
    for _ in range(4):
        r = residuals(f, T, Hh, obs, heights)
        i, j = np.unravel_index(np.argmin(r), r.shape)
        t0, h0 = T[i, j], Hh[i, j]
        dt, dh = abs(T[1, 0] - T[0, 0]) * 3, abs(Hh[0, 1] - Hh[0, 0]) * 3
        T, Hh = np.meshgrid(np.linspace(t0 - dt, t0 + dt, 61), np.linspace(h0 - dh, h0 + dh, 61), indexing="ij")
    r = residuals(f, T, Hh, obs, heights); i, j = np.unravel_index(np.argmin(r), r.shape)
    th, h = float(T[i, j]), float(Hh[i, j])
    res = [float(pred_head_v(u, vf, heights[0] if w == "obi" else heights[1], f, th, h) - vh) for _, w, u, vf, vh in obs]
    return float(r[i, j]), th, h, res


def derived(f, th, h):
    g = {k: ground(u, v, f, th, h)[:2] for k, (u, v) in PTS.items()}
    A, B = g["edge_light_d"], g["edge_light_f"]
    t = (B - A) / np.linalg.norm(B - A); n = np.array([-t[1], t[0]])
    side = np.sign((g["anakin"] - A).dot(n)) or 1.0
    n = n * side                                   # +n = 판 안쪽(인물 쪽)
    perp = lambda k: round(float((g[k] - A).dot(n)), 2)
    along = lambda k: round(float((g[k] - A).dot(t)), 2)
    out = {
        "edge_light_spacing_m": [round(float(np.linalg.norm(g["edge_light_d"] - g["edge_light_e"])), 2),
                                 round(float(np.linalg.norm(g["edge_light_e"] - g["edge_light_f"])), 2)],
        "perp_from_edge_light_line_m": {k: perp(k) for k in ("obiwan", "anakin", "padme_center", "ramp_foot_L", "ramp_foot_R", "box_floor_corner")},
        "along_edge_from_light_d_m": {k: along(k) for k in ("obiwan", "anakin", "padme_center", "box_floor_corner")},
        "slab_lights_if_deck_level": {k: {"perp_m": perp(k), "along_m": along(k)} for k in ("slab_light_a", "slab_light_b", "slab_light_c")},
        "slab_light_spacing_m": [round(float(np.linalg.norm(g["slab_light_a"] - g["slab_light_b"])), 2),
                                 round(float(np.linalg.norm(g["slab_light_b"] - g["slab_light_c"])), 2)],
        "camera_to_obiwan_m": round(float(np.linalg.norm(g["obiwan"])), 1),
    }
    # 계단 상자 높이: 바닥 모서리 위 수직선과 윗모서리 v
    gb = ground(*PTS["box_floor_corner"], f, th, h)
    lo, hi = 0.0, 5.0
    for _ in range(60):
        z = (lo + hi) / 2
        if project(gb + np.array([0, 0, z]), f, th, h)[1] > BOX_RIM[1]: lo = z
        else: hi = z
    out["box_rim_height_m"] = round(z, 2)
    # 처마 조명 높이: 가장자리 등 선에서 바깥(-n)으로 gap m 떨어진 수직면과 시선의 교점
    C = np.array([0, 0, h]); nn = np.array([*(-n), 0])
    def h_on_plane(u, v, gap):
        p0 = np.array([*A, 0]) + nn * gap; d = ray(u, v, f, th)
        s = (p0 - C).dot(nn) / d.dot(nn); return float((C + s * d)[2])
    out["eave_spot_height_m_by_wall_gap"] = {str(gap): [round(h_on_plane(u, v, gap), 2) for u, v in SPOTS] for gap in (2, 4, 6, 8, 10)}
    # 지지부 기울기: 같은 수직면(gap)에 투영한 모서리의 수직에서 벗어난 각
    def lean(gap):
        res = []
        for (u1, v1), (u2, v2) in FIN_EDGE:
            p0 = np.array([*A, 0]) + nn * gap
            P = []
            for u, v in ((u1, v1), (u2, v2)):
                d = ray(u, v, f, th); s = (p0 - C).dot(nn) / d.dot(nn); P.append(C + s * d)
            dv = P[0] - P[1]; horiz = abs(float(dv[:2].dot(t)))
            res.append(round(float(np.degrees(np.arctan2(horiz, dv[2]))), 1))
        return res
    out["fin_lean_deg_by_wall_gap"] = {str(gap): lean(gap) for gap in (2, 4, 6, 8, 10)}
    return out


def main():
    res = {"assumptions": {"principal_point": [CX, CY], "roll": 0, "heights_m": {"obiwan": H_OBI, "anakin": H_ANA},
                           "px_read_err": PX_READ_ERR, "observations": OBS}, "by_f": {}}
    for f in (2500, 3000, 3640, 4550, 5850, 7000, 9000):
        s, th, h, r = solve(f)
        # 민감도: 키 ±3%, 판독 ±4px(머리 v를 위/아래로)
        hs = []
        for k in (0.97, 1.03):
            hs.append(solve(f, heights=(H_OBI * k, H_ANA * k))[2])
        obs_up = [(a, b, c, d, e - PX_READ_ERR) for a, b, c, d, e in OBS]
        obs_dn = [(a, b, c, d, e + PX_READ_ERR) for a, b, c, d, e in OBS]
        hp = [solve(f, obs=o)[2] for o in (obs_up, obs_dn)]
        # 한 장씩 빼고 다시 풀기
        loo = []
        for fr in sorted({o[0] for o in OBS}):
            ss = solve(f, obs=[o for o in OBS if o[0] != fr]); loo.append((fr, round(float(np.degrees(ss[1])), 2), round(ss[2], 2)))
        res["by_f"][str(f)] = {
            "hfov_deg": round(float(np.degrees(2 * np.arctan(CX / f))), 1),
            "pitch_deg": round(float(np.degrees(th)), 2), "cam_h_m": round(h, 2), "rms_px": round(s, 2),
            "residual_px": [round(x, 1) for x in r],
            "cam_h_if_heights_pm3pct": [round(x, 2) for x in hs], "cam_h_if_head_read_pm4px": [round(x, 2) for x in hp],
            "leave_one_frame_out": loo, "derived": derived(f, th, h)}
        print(f, res["by_f"][str(f)]["pitch_deg"], res["by_f"][str(f)]["cam_h_m"], "rms", res["by_f"][str(f)]["rms_px"])
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "m1_result.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
