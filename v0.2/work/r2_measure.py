"""r2_cammatch 결과로 바닥 거리 재기: 시설 쪽 가장자리 선까지의 수직 거리, 경사로 폭, 조명 높이."""
import numpy as np, json, importlib.util, sys
spec = importlib.util.spec_from_file_location("cm", "work/r2_cammatch.py")
src = open("work/r2_cammatch.py").read().split("PTS = {")[0]
ns = {}; exec(src, ns)
ground, solve, axes = ns['ground'], ns['solve'], ns['axes']
P = dict(obiwan=(1415, 1373), anakin=(1830, 1195), padme=(2195, 1290),
         ramp_foot_L=(933, 1083), ramp_foot_R=(1083, 1025),
         edgeA=(1607, 847), edgeB=(2593, 1207), light1=(1580, 832), light2=(1800, 912), light3=(2150, 1060))
rows = {}
for f in [2800, 3500, 4500]:
    err, th, h = solve(f)
    g = {k: ground(*p, f, th, h)[:2] for k, p in P.items()}
    A, Bp = g['edgeA'], g['edgeB']
    t = (Bp - A) / np.linalg.norm(Bp - A); n = np.array([-t[1], t[0]])
    perp = lambda k: float((g[k] - A).dot(n))
    along = lambda k: float((g[k] - A).dot(t))
    # 처마 조명(벽면 위): 가장자리 선에서 벽쪽으로 gap만큼 떨어진 수직면과 만나는 높이
    R, U, F = axes(th); C = np.array([0, 0, h])
    def height_on_plane(u, v, gap):
        d = R * (u - 1477) / f + U * (-(v - 924) / f) + F
        p0 = np.array([*A, 0]) + np.array([*n, 0]) * (-gap if perp('anakin') > 0 else gap)
        nn = np.array([*n, 0]); s = (p0 - C).dot(nn) / d.dot(nn)
        return float((C + s * d)[2])
    rows[f] = dict(
        perp_obiwan=round(perp('obiwan'), 1), perp_anakin=round(perp('anakin'), 1), perp_padme=round(perp('padme'), 1),
        perp_rampL=round(perp('ramp_foot_L'), 1), perp_rampR=round(perp('ramp_foot_R'), 1),
        ramp_foot_width=round(float(np.linalg.norm(g['ramp_foot_L'] - g['ramp_foot_R'])), 2),
        edge_len_visible=round(float(np.linalg.norm(Bp - A)), 1),
        along_obiwan=round(along('obiwan'), 1), along_anakin=round(along('anakin'), 1), along_padme=round(along('padme'), 1),
        light_spacing=[round(float(np.linalg.norm(g['light1'] - g['light2'])), 1), round(float(np.linalg.norm(g['light2'] - g['light3'])), 1)],
        spot_height_gap0=round(height_on_plane(2326, 333, 0), 1), spot_height_gap4=round(height_on_plane(2326, 333, 4), 1))
    print(f, rows[f])
json.dump(rows, open('work/r2_measure.json', 'w'), indent=1)
