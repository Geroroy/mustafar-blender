"""출입구 접근 검사(CR-006): 모델에서 상자를 통과하거나 넘지 않고 바닥만 밟아 출입구 문턱 앞에 닿는지, 그 길의 최소 여유 폭은 얼마인지.
이 값은 **모델 검사값**이다. 영화에서 잰 치수가 아니다.
방법:
  ① 0.1 m 격자마다 z 2.2 m에서 아래로 광선을 쏴 처음 닿는 면을 본다. 그 면이 바닥 높이(|z| ≤ 0.2 m)이고 위를 향하면 걸을 수 있는 칸.
     상자 벽(1.2 m)·연석·핀처럼 바닥 위로 솟은 것은 첫 면이 높아서 막힌 칸, 트렌치·판 밖은 첫 면이 낮거나 없어서 막힌 칸이 된다.
  ② 막힌 칸까지의 거리(여유 반폭)를 구하고, 출발 영역(판 가운데)과 도착 영역(벽면에서 1.3~2.0 m 앞, 문 폭 구간)이 이어지는 가장 큰 여유 반폭 r을 찾는다.
     최소 여유 폭 = 2r (격자 때문에 ±0.1 m).
  ③ 문 자체의 폭(모델 값 1.45 m)은 따로 적는다(병목에서 문을 뺀 값이 ②).
제외 객체: 인물 기준(Ref_*), 우주선 검증(Skiff_*, Ramp_Foot_*), 철사틀 임시 자리(*Placeholder, *Unknown*), 외곽 대안선, 용암 기준면, 숨긴 가설(Hypothesis_*).
실행: <bpy python> -I check_access.py <layout.blend> <후보 이름> <out.json> [plan.png]"""
import json, math, os, sys
from collections import deque

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BLEND, NAME, OUT = sys.argv[-4:-1] if sys.argv[-1].endswith(".png") else sys.argv[-3:]
PLAN = sys.argv[-1] if sys.argv[-1].endswith(".png") else None
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
v = lambda *k: (lambda n: n["value"] if isinstance(n, dict) and "value" in n else n)(__import__("functools").reduce(lambda a, b: a[b], k, D))
LAY = D["v03"]["entrance_layout"]["candidates"][NAME]
X1 = v("platform", "facility_edge_x"); X0 = X1 - v("platform", "width_x"); XW = X1 + v("facility", "trench_gap")
Y0 = LAY["platform_front_y"] if LAY["platform_front_y"] is not None else v("platform", "front_end_y"); Y1 = v("platform", "back_end_y")
EW = v("v03", "entrance", "width"); EYC = LAY["center_y"]; XE = LAY.get("front_x") or XW; EY0, EY1 = EYC - EW / 2, EYC + EW / 2
BOX = (v("stairwell", "corner_back_left")[0], v("stairwell", "corner_back_left")[1] - v("stairwell", "size_y"),
       v("stairwell", "corner_back_left")[0] + v("stairwell", "size_x"), v("stairwell", "corner_back_left")[1])

bpy.ops.wm.open_mainfile(filepath=BLEND)
EXCL = ("Ref_", "Skiff", "Ramp_Foot", "Outline_Alt", "Lava_Level", "Hypothesis_")
dg = bpy.context.evaluated_depsgraph_get()
verts, polys, owners = [], [], []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name.startswith(EXCL) or "Placeholder" in ob.name or "Unknown" in ob.name:
        continue
    if any(c.hide_render for c in ob.users_collection):
        continue
    me = ob.evaluated_get(dg).to_mesh(); mw = ob.matrix_world; base = len(verts)
    verts += [mw @ vt.co for vt in me.vertices]
    for p in me.polygons:
        polys.append([base + i for i in p.vertices]); owners.append(ob.name)
    ob.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, polys)

STEP = 0.1
xs = np.arange(X0 - 1.0, XW + 1.5, STEP) + STEP / 2; ys = np.arange(Y0 - 1.0, Y1 + 1.0, STEP) + STEP / 2
walk = np.zeros((len(ys), len(xs)), bool); hit_owner = {}
down = Vector((0, 0, -1))
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        loc, nrm, idx, dist = bvh.ray_cast(Vector((x, y, 2.2)), down, 6.0)
        if loc is not None and abs(loc.z) <= 0.2 and nrm.z > 0.7:
            walk[j, i] = True
import cv2  # noqa: E402
clear = cv2.distanceTransform(walk.astype(np.uint8), cv2.DIST_L2, 5) * STEP - STEP / 2      # 막힌 칸까지 거리(반폭), m


def cells(x0, x1, y0, y1):
    return [(j, i) for j, y in enumerate(ys) for i, x in enumerate(xs) if x0 <= x <= x1 and y0 <= y <= y1]


START = [c for c in cells(-3, 3, -3, 3) if walk[c]]
GOAL = [c for c in cells(XE - 2.0, XE - 1.3, EY0, EY1) if walk[c]]                        # 출입구 테두리(돌출 0.3 m) 앞 1 m 띠 — 문틀 자체의 폭은 병목에서 뺌
DOOR = [c for c in cells(XE + 0.1, XE + 0.9, EY0 + 0.05, EY1 - 0.05) if walk[c]]           # 문턱 위


def connected(r, goal):
    ok = walk & (clear >= r - 1e-9); seen = np.zeros_like(ok); q = deque()
    for c in START:
        if ok[c]: seen[c] = True; q.append(c)
    gs = set(goal); prev = {}
    while q:
        c = q.popleft()
        if c in gs:
            path = [c]
            while path[-1] in prev: path.append(prev[path[-1]])
            return path[::-1]
        j, i = c
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (j + dj, i + di)
            if 0 <= n[0] < ok.shape[0] and 0 <= n[1] < ok.shape[1] and ok[n] and not seen[n]:
                seen[n] = True; prev[n] = c; q.append(n)
    return None


res = {"layout": NAME, "blend": os.path.basename(BLEND), "grid_m": STEP, "entrance_center_y": EYC, "entrance_wall_x": XE, "platform_front_y": Y0,
       "note": "모델 검사값(영화 치수 아님). 폭은 막힌 칸 사이 거리로 잰 값이라 격자 때문에 ±0.1 m", "goal_cells": len(GOAL), "door_cells": len(DOOR)}
path0 = connected(0.0, GOAL) if GOAL else None
res["reachable_without_crossing_box"] = path0 is not None
best, path_b = 0.0, path0
if path0:
    lo, hi = 0.0, 3.0
    while hi - lo > 0.025:
        mid = (lo + hi) / 2; p = connected(mid, GOAL)
        if p: lo, path_b = mid, p
        else: hi = mid
    best = lo
    k = min(range(len(path_b)), key=lambda t: clear[path_b[t]])
    jb, ib = path_b[k]
    res["min_clear_width_m"] = round(2 * best, 2)
    res["bottleneck_xy"] = [round(float(xs[ib]), 2), round(float(ys[jb]), 2)]
    res["path_len_m"] = round(len(path_b) * STEP, 1)
    pts = [(float(xs[i]), float(ys[j])) for j, i in path_b]
    res["path_passes_box_minus_y_end"] = any(BOX[0] - 0.5 <= x <= BOX[2] + 0.5 and y < BOX[1] for x, y in pts)
    res["path_passes_box_plus_y_end"] = any(BOX[0] - 0.5 <= x <= BOX[2] + 0.5 and y > BOX[3] for x, y in pts)
# 상자 −Y 끝(끝 단 포함) 옆으로 드러나는 바닥 폭: 상자 x 범위의 각 열에서 끝 단 −Y 끝부터 −Y로 걸을 수 있는 칸이 이어지는 길이(최소값)
SKO = D["v03"]["stairwell_skin"]["skirt_out"]["value"]; YEND = BOX[1] - 0.3 * D["v03"]["stairwell_skin"]["end_tiers"]["value"]
gaps = []
for i, x in enumerate(xs):
    if not (BOX[0] - SKO <= x <= BOX[2]): continue
    js = [j for j, y in enumerate(ys) if y < YEND]
    n = 0
    for j in sorted(js, reverse=True):
        if walk[j, i]: n += 1
        elif n: break
        else: continue
    gaps.append(n * STEP)
res["floor_beside_box_minusY_end_min_m"] = round(min(gaps), 2) if gaps else None
res["door_opening_width_model_m"] = EW
res["door_threshold_walkable"] = len(DOOR) > 0
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))

if PLAN:
    from PIL import Image, ImageDraw, ImageFont
    k_ = 14; H, W = walk.shape
    im = Image.new("RGB", (W * k_ // 1 // 1, H * k_ // 1), (25, 25, 28))
    a = np.zeros((H, W, 3), np.uint8); a[walk] = (150, 150, 150); a[~walk] = (40, 40, 44)
    im = Image.fromarray(a[::-1]).resize((W * 4, H * 4), Image.NEAREST); S = 4
    dr = ImageDraw.Draw(im); ft = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
    tr = lambda x, y: ((x - xs[0] + STEP / 2) / STEP * S, (ys[-1] + STEP / 2 - y) / STEP * S)
    dr.rectangle([tr(BOX[0], BOX[3]), tr(BOX[2], BOX[1])], outline=(255, 170, 0), width=3)
    dr.text(tr(BOX[0] - 6, BOX[3] + 1.5), "낮은 상자(R2 위치, 모든 후보 동일)", font=ft, fill=(255, 170, 0))
    dr.line([tr(XE, EY0), tr(XE, EY1)], fill=(80, 200, 255), width=6)
    dr.text(tr(XE + 0.5, EY1 + 1.0), "출입구 문턱", font=ft, fill=(80, 200, 255))
    if path_b:
        dr.line([tr(float(xs[i]), float(ys[j])) for j, i in path_b], fill=(230, 40, 40), width=3)
        bx, by = res["bottleneck_xy"]; X_, Y_ = tr(bx, by); R_ = best / STEP * S
        dr.ellipse((X_ - R_, Y_ - R_, X_ + R_, Y_ + R_), outline=(255, 255, 0), width=3)
    txt = (f"후보 {NAME} — 문턱 도달: {'가능' if path0 else '불가(상자를 지나야 함)'}"
           + (f", 최소 여유 폭 {res['min_clear_width_m']} m (노란 원, 모델 검사값)" if path0 else ""))
    cx0_, cy0_ = tr(X1 - 14, -3.0); cx1_, cy1_ = tr(XW + 1.5, Y0 - 1.0)
    body = im.crop((int(cx0_), int(cy0_), int(cx1_), int(cy1_)))
    out = Image.new("RGB", (body.width, body.height + 60), (0, 0, 0)); out.paste(body, (0, 30)); d2 = ImageDraw.Draw(out)
    d2.text((6, 4), txt, font=ft, fill=(255, 255, 255))
    d2.text((6, out.height - 26), "회색 = 걸을 수 있는 바닥, 검정 = 막힘(상자·연석·핀·트렌치·판 밖), 빨강 = 판 가운데→문턱 앞 최대 여유 경로. +X 오른쪽, +Y 위", font=ft, fill=(220, 220, 220))
    out.save(PLAN)
