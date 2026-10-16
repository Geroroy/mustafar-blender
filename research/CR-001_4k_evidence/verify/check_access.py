"""출입구 바닥 연결 검사(CR-006, CR-007 확장): 상자를 통과하거나 넘지 않고 바닥만 밟아
판 가운데 → 상자 옆 → 문턱 → 문틀 바로 안쪽(통로 시작)까지 이어지는지, 그 경로의 최소 여유 폭은 얼마인지.
이 값은 **모델의 바닥 연결 검사값**이다. 영화에서 잰 치수가 아니며, 키·어깨 폭·머리 높이를 포함한 캐릭터 충돌 검증도 아니다.
방법:
  ① 0.1 m 격자마다 탐침 높이(0.9 m)에서 아래로 광선을 쏴 처음 닿는 면을 본다. 그 면이 바닥 높이(|z| ≤ 0.2 m)이고 위를 향하면 걸을 수 있는 칸.
     단 0.25 m에서 위로 쏜 광선이 윗면을 아래에서 먼저 만나면(탐침보다 높은 물체 안) 막힘.
     바닥 위 0.2~0.9 m에 걸친 것(상자 벽·끝 단·연석·문설주·통로 리브·R 가설 외곽 등)은 막힘. 트렌치·판 밖은 첫 면이 낮거나 없어서 막힘.
     0.9 m보다 높은 곳의 돌출(A자 경사 테두리, 문 위 벽 등)은 이 검사에서 보지 않는다 — A자 문은 어깨점(조명 중심 × 0.42)보다 위에서 좁아진다.
  ② 막힌 칸까지 거리(여유 반폭)로, 출발(판 가운데)과 도착 영역이 이어지는 가장 큰 여유 반폭 r을 이분 탐색한다. 최소 여유 폭 = 2r(격자 ±0.1 m).
     도착 영역 세 가지를 따로 잰다:
       - approach: 문틀 앞면에서 1.0~1.7 m 앞(문 폭 구간) — 문 앞 접근 폭(문틀 제외)
       - threshold: 문틀 앞면~벽 두께 끝(문턱 위)
       - inside: 통로 시작 0.05~0.6 m 안쪽 — 문틀·통로 리브를 포함한 전체 경로
제외 객체: 인물 기준(Ref_*), 우주선 검증(Skiff_*, Ramp_Foot_*), 철사틀 임시 자리(*Placeholder, *Unknown*), 외곽 대안선, 용암 기준면, 숨긴 가설(Hypothesis_*).
R 가설 외곽(R_Structure_Hypothesis)은 장애물로 포함한다.
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
EW = LAY.get("entrance_width") or v("v03", "entrance", "width"); EYC = LAY["center_y"]; XE = LAY.get("front_x") or XW; EY0, EY1 = EYC - EW / 2, EYC + EW / 2
XF0 = D["v03"]["entrance"]["frame_layers"]["value"][0][2]; XFR = XE - XF0          # 문틀 앞면
BOX = (v("stairwell", "corner_back_left")[0], v("stairwell", "corner_back_left")[1] - v("stairwell", "size_y"),
       v("stairwell", "corner_back_left")[0] + v("stairwell", "size_x"), v("stairwell", "corner_back_left")[1])
PROBE = 0.9

bpy.ops.wm.open_mainfile(filepath=BLEND)
EXCL = ("Ref_", "Skiff", "Ramp_Foot", "Outline_Alt", "Lava_Level", "Hypothesis_")
dg = bpy.context.evaluated_depsgraph_get()
verts, polys, used = [], [], []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name.startswith(EXCL) or "Placeholder" in ob.name or "Unknown" in ob.name:
        continue
    if any(c.hide_render for c in ob.users_collection):
        continue
    me = ob.evaluated_get(dg).to_mesh(); mw = ob.matrix_world; base = len(verts)
    verts += [mw @ vt.co for vt in me.vertices]
    for p in me.polygons:
        polys.append([base + i for i in p.vertices])
    used.append(ob.name); ob.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, polys)

STEP = 0.1
xs = np.arange(X0 - 1.0, XW + 6.0, STEP) + STEP / 2; ys = np.arange(Y0 - 1.0, Y1 + 1.0, STEP) + STEP / 2
walk = np.zeros((len(ys), len(xs)), bool)
down, upv = Vector((0, 0, -1)), Vector((0, 0, 1))
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        loc, nrm, idx, dist = bvh.ray_cast(Vector((x, y, PROBE)), down, 6.0)
        if loc is not None and abs(loc.z) <= 0.2 and nrm.z > 0.7:
            # 탐침 높이보다 높은 막힌 물체(벽·상자 등) 안에서 시작한 광선은 그 밑 바닥을 보므로, 위로 쏴서 윗면을 아래에서 만나면(=물체 안) 막힘
            l2, n2, _, _ = bvh.ray_cast(Vector((x, y, 0.25)), upv, 20.0)
            if l2 is None or n2.z <= 0.3:
                walk[j, i] = True
import cv2  # noqa: E402
clear = cv2.distanceTransform(walk.astype(np.uint8), cv2.DIST_L2, 5) * STEP - STEP / 2      # 막힌 칸까지 거리(반폭), m


def cells(x0, x1, y0, y1):
    return [(j, i) for j, y in enumerate(ys) for i, x in enumerate(xs) if x0 <= x <= x1 and y0 <= y <= y1]


START = [c for c in cells(-3, 3, -3, 3) if walk[c]]
GOALS = {"approach": [c for c in cells(XFR - 1.7, XFR - 1.0, EY0, EY1) if walk[c]],
         "threshold": [c for c in cells(XFR + 0.05, XE + 0.95, EY0, EY1) if walk[c]],
         "inside": [c for c in cells(XE + 1.05, XE + 1.6, EY0, EY1) if walk[c]]}


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


def bottleneck(goal):
    if not goal: return None
    p0 = connected(0.0, goal)
    if not p0: return {"connected": False}
    lo, hi, pb = 0.0, 3.0, p0
    while hi - lo > 0.0125:
        mid = (lo + hi) / 2; p = connected(mid, goal)
        if p: lo, pb = mid, p
        else: hi = mid
    k = min(range(len(pb)), key=lambda t: clear[pb[t]]); jb, ib = pb[k]
    pts = [(float(xs[i]), float(ys[j])) for j, i in pb]
    return {"connected": True, "min_clear_width_m": round(2 * lo, 2), "bottleneck_xy": [round(float(xs[ib]), 2), round(float(ys[jb]), 2)],
            "path_len_m": round(len(pb) * STEP, 1), "passes_box_minusY_side": any(BOX[0] - 0.5 <= x <= BOX[2] + 0.5 and y < BOX[1] for x, y in pts),
            "passes_box_plusY_side": any(BOX[0] - 0.5 <= x <= BOX[2] + 0.5 and y > BOX[3] for x, y in pts), "_path": pb, "_r": lo}


res = {"layout": NAME, "blend": os.path.basename(BLEND), "grid_m": STEP, "probe_height_m": PROBE, "entrance_center_y": EYC, "entrance_wall_x": XE,
       "entrance_width_model_m": EW, "platform_front_y": Y0, "objects_used": sorted(used),
       "note": "바닥 연결 검사값(모델). 영화 치수도, 캐릭터 충돌 검증도 아님. 폭은 막힌 칸 사이 거리라 격자 때문에 ±0.1 m. 0.9 m 위 돌출(A자 경사 테두리)은 보지 않음"}
BN = {}
for k, g in GOALS.items():
    BN[k] = bottleneck(g); res[k] = {kk: vv for kk, vv in (BN[k] or {"connected": False, "goal_cells": 0}).items() if not kk.startswith("_")}
    res[k]["goal_cells"] = len(g)
res["reachable_without_crossing_box"] = bool(BN["approach"] and BN["approach"]["connected"])
res["reaches_inside_door"] = bool(BN["inside"] and BN["inside"]["connected"])
# 문턱 위 걸을 수 있는 폭(문턱 중간 x에서 문 y 구간의 연속 칸)
ic = int(np.argmin(np.abs(xs - (XE + 0.5)))); col = [walk[j, ic] for j, y in enumerate(ys) if EY0 - 1.0 <= y <= EY1 + 1.0]
runs, n = [], 0
for b in col + [False]:
    if b: n += 1
    elif n: runs.append(n); n = 0
res["threshold_walkable_width_m"] = round(max(runs) * STEP, 2) if runs else 0.0
SKO = D["v03"]["stairwell_skin"]["skirt_out"]["value"]; YEND = BOX[1] - 0.3 * D["v03"]["stairwell_skin"]["end_tiers"]["value"]
gaps = []
for i, x in enumerate(xs):
    if not (BOX[0] - SKO <= x <= BOX[2]): continue
    n = 0
    for j in sorted([j for j, y in enumerate(ys) if y < YEND], reverse=True):
        if walk[j, i]: n += 1
        elif n: break
    gaps.append(n * STEP)
res["floor_beside_box_minusY_end_min_m"] = round(min(gaps), 2) if gaps else None
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: vv for k, vv in res.items() if k != "objects_used"}, ensure_ascii=False))

if PLAN:
    from PIL import Image, ImageDraw, ImageFont
    H, W = walk.shape; S = 4
    a = np.zeros((H, W, 3), np.uint8); a[walk] = (150, 150, 150); a[~walk] = (40, 40, 44)
    im = Image.fromarray(a[::-1]).resize((W * S, H * S), Image.NEAREST)
    dr = ImageDraw.Draw(im); ft = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
    tr = lambda x, y: ((x - xs[0] + STEP / 2) / STEP * S, (ys[-1] + STEP / 2 - y) / STEP * S)
    dr.rectangle([tr(BOX[0], BOX[3]), tr(BOX[2], BOX[1])], outline=(255, 170, 0), width=3)
    dr.text(tr(BOX[0] - 7, BOX[3] + 1.5), "낮은 상자 L(R2 위치)", font=ft, fill=(255, 170, 0))
    RH = D["v03"].get("r_hypothesis")
    if RH and NAME in RH["layouts"]:
        lx, ly = RH["local_x"]["value"], RH["local_y"]["value"]
        dr.rectangle([tr(XE + lx[0], EYC + ly[1]), tr(XE + lx[1], EYC + ly[0])], outline=(255, 240, 60), width=3)
        dr.text(tr(XE + lx[0] - 6.5, EYC + ly[0] - 0.4), "R 가설 외곽", font=ft, fill=(255, 240, 60))
    dr.line([tr(XE, EY0), tr(XE, EY1)], fill=(80, 200, 255), width=6)
    dr.text(tr(XE + 1.6, EY1 + 0.6), "출입구(문턱)", font=ft, fill=(80, 200, 255))
    for k, col_ in (("approach", (60, 220, 90)), ("inside", (230, 40, 40))):
        b = BN.get(k)
        if b and b.get("connected"):
            dr.line([tr(float(xs[i]), float(ys[j])) for j, i in b["_path"]], fill=col_, width=3 if k == "inside" else 5)
            bx, by = b["bottleneck_xy"]; X_, Y_ = tr(bx, by); R_ = max(b["_r"] / STEP * S, 4)
            dr.ellipse((X_ - R_, Y_ - R_, X_ + R_, Y_ + R_), outline=col_, width=3)
    t1 = f"후보 {NAME} — 문 앞 접근: " + (f"가능, 최소 여유 {res['approach']['min_clear_width_m']} m" if res["approach"].get("connected") else "불가(상자를 지나야 함)")
    t2 = "문틀 안쪽까지 전체 경로: " + (f"가능, 최소 여유 {res['inside']['min_clear_width_m']} m (문턱 위 걸을 수 있는 폭 {res['threshold_walkable_width_m']} m)" if res["inside"].get("connected") else "불가")
    cx0_, cy0_ = tr(X1 - 14, -3.0); cx1_, cy1_ = tr(XE + 6.0 if XE < XW else XW + 6.0, Y0 - 1.0)
    body = im.crop((int(cx0_), int(cy0_), int(min(cx1_, im.width)), int(cy1_)))
    out = Image.new("RGB", (body.width, body.height + 110), (0, 0, 0)); out.paste(body, (0, 56)); d2 = ImageDraw.Draw(out)
    d2.text((6, 4), t1, font=ft, fill=(255, 255, 255)); d2.text((6, 28), t2, font=ft, fill=(255, 255, 255))
    d2.text((6, out.height - 50), "회색 = 0.9 m 탐침 아래 걸을 수 있는 바닥, 검정 = 막힘. 초록 = 문 앞 접근 경로, 빨강 = 문틀 안쪽까지 경로(원 = 병목)", font=ft, fill=(220, 220, 220))
    d2.text((6, out.height - 26), "바닥 연결 검사값(모델) — 영화 치수·캐릭터 충돌 검증 아님. +X 오른쪽, +Y 위", font=ft, fill=(220, 220, 220))
    out.save(PLAN)
