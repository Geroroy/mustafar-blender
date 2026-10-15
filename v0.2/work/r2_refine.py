"""R2 카메라(f=3500 기준, 범위 2800/4500)로 v0.1-식 오류 고치기:
 - 계단 상자 모서리를 난간 높이(1.2 m) 점으로 다시 투영
 - 시설 쪽 가장자리 조명 3개의 위치(뒤 끝 기준 거리)
 - 시설 벽의 뒤 끝(벽 왼쪽 경계)과 날개 끝 위치를 영화 픽셀에 맞춰 역산
좌표: 블록아웃 월드(X1=14.5, Y1=20 = 시설 쪽 뒤 모서리)."""
import numpy as np, json, math
src = open("work/r2_cammatch.py").read().split("PTS = {")[0]; ns = {}; exec(src, ns)
ground, solve, axes = ns['ground'], ns['solve'], ns['axes']
X1, Y1 = 14.5, 20.0
res = {}
for f in [2800, 3500, 4500]:
    err, th, h = solve(f)
    R, U, F = axes(th); C = np.array([0, 0, h])
    A = ground(1607, 847, f, th, h)[:2]; Bp = ground(2593, 1207, f, th, h)[:2]
    t = (Bp - A) / np.linalg.norm(Bp - A); n = np.array([-t[1], t[0]])
    # 캠 좌표 → 월드: along(t)는 월드 -Y, n 은 월드 +X
    def to_world(p):
        d = p[:2] - A
        return np.array([X1 + d.dot(n), Y1 - d.dot(t), p[2] if len(p) > 2 else 0])
    def to_cam(w):
        a = Y1 - w[1]; b = w[0] - X1
        xy = A + t * a + n * b
        return np.array([xy[0], xy[1], w[2]])
    def proj(w):
        d = to_cam(w) - C
        return 1477 + f * d.dot(R) / d.dot(F), 924 - f * d.dot(U) / d.dot(F)
    def ray_z(u, v, z):
        d = R * (u - 1477) / f + U * (-(v - 924) / f) + F
        s = (z - h) / d[2]; return C + s * d
    out = {}
    out['stair_corner_at_1.2m'] = to_world(ray_z(2500, 1190, 1.2)).round(2).tolist()
    out['lights'] = [to_world(ray_z(u, v, 0.1)).round(1).tolist() for u, v in [(1580, 832), (1800, 912), (2150, 1060)]]
    # 시설 벽 왼쪽 경계: 영화에서 벽면이 끝나는 가장 왼쪽 경계 (보 높이 근처) — 원본 픽셀 (2146, 397)과 (2146,767) 사이
    best = None
    for gap in (2, 4, 6, 8):
        for yb in np.arange(-10, 30, 0.25):
            u, _ = proj(np.array([X1 + gap, yb, 6.7]))
            e = abs(u - 2146)
            if best is None or e < best[0]:
                best = (e, gap, yb)
        out[f'wall_back_end_y_gap{gap}'] = float(min(np.arange(-10, 30, 0.25), key=lambda yb: abs(proj(np.array([X1 + gap, yb, 6.7]))[0] - 2146)))
    # 날개 끝: 영화에서 얇은 날개가 끝나는 곳 (원본 ≈ 2008, 552) — 높이 4.75 m, 몸체 중심 y=6 기준 앞쪽 1 m
    tip = min(np.arange(-5, 30, 0.1), key=lambda x: (proj(np.array([x, 5.0, 4.75]))[0] - 2008) ** 2)
    out['wing_tip_x'] = round(float(tip), 1)
    out['wing_tip_v_at_that_x'] = round(proj(np.array([tip, 5.0, 4.75]))[1], 0)
    out['skiff_center_x_if_span_49.3'] = round(float(tip - 49.3 / 2), 1)
    res[f] = out
    print(f, out)
json.dump(res, open('work/r2_refine.json', 'w'), indent=1)
