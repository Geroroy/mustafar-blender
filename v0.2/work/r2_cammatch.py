"""R2 카메라 맞춤: 두 인물(키 알려짐)로 피치·카메라 높이를 풀고 바닥 점을 m로 옮긴다.
초점거리 f는 한 장면으로는 결정되지 않아 범위로 돌려 결과의 폭을 본다."""
import numpy as np, json, sys
CX, CY = 1477.0, 924.0           # 필름 영역(305~1543행)의 중심
OBI = dict(foot=(1415, 1373), head=(1420, 1072), H=1.78)
ANA = dict(foot=(1830, 1195), head=(1830, 945), H=1.85)

def axes(th):
    F = np.array([0, np.cos(th), -np.sin(th)]); U = np.array([0, np.sin(th), np.cos(th)]); R = np.array([1., 0, 0])
    return R, U, F

def ground(u, v, f, th, h):
    R, U, F = axes(th)
    d = R * (u - CX) / f + U * (-(v - CY) / f) + F
    t = -h / d[2]
    return np.array([0, 0, h]) + t * d

def height_of(p, f, th, h):
    """발 픽셀 → 바닥점, 머리 픽셀의 v에 맞는 높이."""
    g = ground(*p['foot'], f, th, h)
    R, U, F = axes(th)
    C = np.array([0, 0, h])
    # 바닥점 위 높이 z인 점의 v를 머리 v에 맞춤 (z에 대해 단조)
    lo, hi = 0.0, 10.0
    for _ in range(60):
        z = (lo + hi) / 2
        d = g + np.array([0, 0, z]) - C
        v = CY - f * d.dot(U) / d.dot(F)
        if v > p['head'][1]: lo = z
        else: hi = z
    return z

def solve(f):
    best = None
    for th in np.radians(np.linspace(2, 60, 2321)):
        r1 = height_of(OBI, f, th, 1.0) ; r2 = height_of(ANA, f, th, 1.0)
        h1, h2 = OBI['H'] / r1, ANA['H'] / r2
        err = abs(h1 - h2) / ((h1 + h2) / 2)
        if best is None or err < best[0]:
            best = (err, th, (h1 + h2) / 2)
    return best

PTS = {   # 바닥(Z=0)에 있다고 볼 수 있는 점
    "obiwan": OBI['foot'], "anakin": ANA['foot'], "padme": (2195, 1290),
    "edge_light_1": (1580, 832), "edge_light_2": (1800, 912), "edge_light_3": (2150, 1060),
    "edge_line_A": (1607, 847), "edge_line_B": (2593, 1207),
    "stair_box_near_corner": (2500, 1190),
}
out = {}
for f in [2200, 2800, 3500, 4500, 6000]:
    err, th, h = solve(f)
    g = {k: ground(*p, f, th, h)[:2] for k, p in PTS.items()}
    dist = lambda a, b: float(np.linalg.norm(g[a] - g[b]))
    hfov = np.degrees(2 * np.arctan(CX / f))
    vtilt = np.degrees(np.arctan(1123 * np.tan(th) / f))  # 계단 상자(x≈2600) 수직선 기울기 예측
    r = dict(f=f, hfov=round(hfov, 1), pitch=round(np.degrees(th), 1), cam_h=round(h, 2), fit_err=round(err, 4),
             pred_vertical_tilt_at_x2600=round(vtilt, 1),
             obi_anakin=round(dist('obiwan', 'anakin'), 1), anakin_edge_light3=round(dist('anakin', 'edge_light_3'), 1),
             edge_lights_1_2=round(dist('edge_light_1', 'edge_light_2'), 1), edge_lights_2_3=round(dist('edge_light_2', 'edge_light_3'), 1),
             edge_A_B=round(dist('edge_line_A', 'edge_line_B'), 1), obi_padme=round(dist('obiwan', 'padme'), 1),
             cam_to_obi=round(float(np.linalg.norm(g['obiwan'])), 1),
             pts={k: [round(float(x), 1) for x in v] for k, v in g.items()})
    out[f] = r
    print({k: v for k, v in r.items() if k != 'pts'})
json.dump(out, open('work/r2_cammatch.json', 'w'), indent=1)
