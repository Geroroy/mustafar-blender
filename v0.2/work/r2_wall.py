"""벽면(가장자리 선에서 gap만큼 안쪽 수직면) 위 점: 처마 조명 위치·간격, 핀 기울기."""
import numpy as np, json
src = open("work/r2_cammatch.py").read().split("PTS = {")[0]
ns = {}; exec(src, ns); ground, solve, axes = ns['ground'], ns['solve'], ns['axes']
out = {}
for f in [2800, 3500, 4500]:
    err, th, h = solve(f)
    A = ground(1607, 847, f, th, h)[:2]; Bp = ground(2593, 1207, f, th, h)[:2]
    t = (Bp - A) / np.linalg.norm(Bp - A); n = np.array([-t[1], t[0]])
    ana = ground(1830, 1195, f, th, h)[:2]
    side = -1 if (ana - A).dot(n) > 0 else 1   # 벽 쪽(인물 반대쪽)
    R, U, F = axes(th); C = np.array([0, 0, h])
    def on_plane(u, v, gap):
        d = R * (u - 1477) / f + U * (-(v - 924) / f) + F
        nn = np.array([*n, 0]); p0 = np.array([*A, 0]) + nn * side * gap
        s = (p0 - C).dot(nn) / d.dot(nn); P = C + s * d
        return float((P[:2] - A).dot(t)), float(P[2])
    r = {}
    for gap in (2, 4, 6):
        s1, s2 = on_plane(2326, 333, gap), on_plane(2600, 337, gap)
        fa, fb = on_plane(2633, 1153, gap), on_plane(2513, 700, gap)
        lean = np.degrees(np.arctan2(fb[0] - fa[0], fb[1] - fa[1]))
        r[gap] = dict(spot1=[round(x, 1) for x in s1], spot2=[round(x, 1) for x in s2],
                      spot_spacing=round(abs(s2[0] - s1[0]), 1), fin_lean_deg=round(float(lean), 1),
                      fin_bottom=[round(x, 1) for x in fa], fin_top=[round(x, 1) for x in fb])
    out[f] = r
    print(f, r)
json.dump(out, open('work/r2_wall.json', 'w'), indent=1)
