"""FULL-1 맵 전체 보행 분석 — md_orig/mo04_walk_analysis.py 사본에 '열린 문' 옵션을 더한 것. Blender(bpy).
  --open-models '[24,2,3,31,32]': 원본 BSP의 인라인 모델(func_door 등) 경계 상자 안에 정점이 모두 든 삼각형을 충돌에서 뺀다(문이 열린 상태).
  형상은 바꾸지 않는다(분석용 BVH에서만 뺌). 그 밖은 mo04와 같다.
원래 설명(mo04):
MO-4 보행 분석 — 원본 형상(MO_GAMEFIT.blend, 형상 불변)에서 직접 걸을 수 있는 면과 연결을 읽는다. Blender(bpy).
형상을 메우거나 지우지 않는다. 엔진(JKA) 이동 규칙을 그대로 쓴다: 걷는 면 법선 z ≥ 0.7, 머리 위 여유 ≥ 1.6 m(서 있는 상자 56 u), 계단 높이 ≤ 0.5 m(STEPSIZE 18 u).
  1) 칸(0.125 m)마다 위에서 아래로 광선을 반복해 모든 면을 모은다 → 서 있을 수 있는 층(바닥 후보)과 머리 위 여유.
  2) 시작점에서 8방향 연결(높이 차 ≤ 0.5 m, 가로로 쏜 광선이 벽·소품에 막히지 않음)로 넓혀 '실제로 걸어서 닿는 층'을 구한다.
출력: <out>/walk.npz(칸별 층 높이·연결), walk_report.json, walk_levels.png(높이별 색)
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo04_walk_analysis.py <MO_GAMEFIT.blend> <출력 폴더> [--cell 0.125] [--spawn X Y]
"""
import json, math, os, sys
from collections import deque

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC, OUT = sys.argv[1], sys.argv[2]
CELL = float(sys.argv[sys.argv.index("--cell") + 1]) if "--cell" in sys.argv else 0.125
SP = tuple(float(v) for v in sys.argv[sys.argv.index("--spawn") + 1:sys.argv.index("--spawn") + 3]) if "--spawn" in sys.argv else (0.0, -14.0)
B = json.loads(sys.argv[sys.argv.index("--bounds") + 1]) if "--bounds" in sys.argv else [-24.0, 24.0, -32.0, 26.0]     # X0 X1 Y0 Y1 (m)
STEP, MIN_NZ, HEAD, ZTOP = 0.506, 0.7, 1.6, 40.0
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
dg = bpy.context.evaluated_depsgraph_get()
verts, tris, owner = [], [], []
names = []
for o in D.scenes["MO_GAMEFIT"].collection.all_objects:
    if o.type != 'MESH':
        continue
    me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
    base = len(verts); verts += [o.matrix_world @ v.co for v in me.vertices]
    for t in me.loop_triangles:
        tris.append([base + i for i in t.vertices]); owner.append(len(names))
    names.append(o.name); o.evaluated_get(dg).to_mesh_clear()
OPEN = json.loads(sys.argv[sys.argv.index("--open-models") + 1]) if "--open-models" in sys.argv else []
if OPEN:
    import struct
    BSP = sys.argv[sys.argv.index("--bsp") + 1]
    bb = open(BSP, "rb").read(); lo, ll = struct.unpack_from("<ii", bb, 8 + 7 * 8)
    mods = list(struct.iter_unpack("<6f4i", bb[lo:lo + ll]))
    FIT = [o for o in D.objects if o.name == "MO_FIT"][0].matrix_world
    boxes = []
    for m in OPEN:
        a = FIT @ Vector(mods[m][:3]); b2 = FIT @ Vector(mods[m][3:6])
        boxes.append((m, Vector((min(a.x, b2.x), min(a.y, b2.y), min(a.z, b2.z))) - Vector((0.02,) * 3), Vector((max(a.x, b2.x), max(a.y, b2.y), max(a.z, b2.z))) + Vector((0.02,) * 3)))
    inside = lambda v, lo_, hi_: all(lo_[k] <= v[k] <= hi_[k] for k in range(3))
    keep, removed = [], {}
    for t, ow in zip(tris, owner):
        hit = next((m for m, lo_, hi_ in boxes if all(inside(verts[q], lo_, hi_) for q in t)), None)
        if hit is None:
            keep.append((t, ow))
        else:
            removed[hit] = removed.get(hit, 0) + 1
    tris = [t for t, _ in keep]; owner = [o_ for _, o_ in keep]
    print("열린 모델(빠진 삼각형):", removed, flush=True)
bvh = BVHTree.FromPolygons(verts, tris)
print("tris", len(tris), flush=True)
X0, X1, Y0, Y1 = B
nx, ny = int((X1 - X0) / CELL), int((Y1 - Y0) / CELL)


def cxy(i, j):
    return X0 + (i + 0.5) * CELL, Y0 + (j + 0.5) * CELL


MAXL = 10
Z = np.full((nx, ny, MAXL), np.nan, np.float32)       # 층 높이(서 있는 면)
HR = np.full((nx, ny, MAXL), np.nan, np.float32)      # 머리 위 여유
OWN = np.full((nx, ny, MAXL), -1, np.int16)
down = Vector((0, 0, -1)); up = Vector((0, 0, 1))
for i in range(nx):
    for j in range(ny):
        x, y = cxy(i, j); z0 = ZTOP; k = 0
        for _ in range(30):
            h = bvh.ray_cast(Vector((x, y, z0)), down, 200.0)
            if h[0] is None:
                break
            loc, nrm, fi, _d = h
            z0 = loc.z - 0.004
            if abs(nrm.z) >= MIN_NZ and k < MAXL:
                hu = bvh.ray_cast(Vector((x, y, loc.z + 0.01)), up, 100.0)
                head = (hu[3] if hu[0] is not None else 99.0)
                if head >= HEAD:
                    Z[i, j, k] = loc.z; HR[i, j, k] = head; OWN[i, j, k] = owner[fi]; k += 1
    if i % 40 == 0:
        print("scan", i, nx, flush=True)
# 연결 넓히기
sx, sy = int((SP[0] - X0) / CELL), int((SP[1] - Y0) / CELL)
start = None
for k in range(MAXL):
    z = Z[sx, sy, k]
    if not np.isnan(z) and abs(z) < 0.2:
        start = (sx, sy, k); break
assert start, "시작점에 바닥 없음"
seen = {start: 0}; dq = deque([start]); ZR = {}
NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
blocked_by = {}
while dq:
    a = dq.popleft(); ai, aj, ak = a; za = float(Z[ai, aj, ak]); ax, ay = cxy(ai, aj)
    for di, dj in NB:
        bi, bj = ai + di, aj + dj
        if not (0 <= bi < nx and 0 <= bj < ny):
            continue
        bx, by = cxy(bi, bj)
        for bk in range(MAXL):
            zb = Z[bi, bj, bk]
            if np.isnan(zb) or (bi, bj, bk) in seen or abs(zb - za) > STEP:
                continue
            hh = bvh.ray_cast(Vector((ax, ay, max(za, zb) + STEP + 0.02)), Vector((bx - ax, by - ay, 0)).normalized(), math.hypot(bx - ax, by - ay) + 0.001)
            if hh[0] is not None:                  # 가로 막힘(벽·소품)
                n = names[owner[hh[2]]]; blocked_by[n] = blocked_by.get(n, 0) + 1
                continue
            seen[(bi, bj, bk)] = 1; dq.append((bi, bj, bk))
print("reachable nodes", len(seen), flush=True)
REACH = np.zeros((nx, ny, MAXL), bool)
for (i, j, k) in seen:
    REACH[i, j, k] = True
R = np.zeros((nx, ny), np.uint8); RZ = np.full((nx, ny), np.nan, np.float32); MULTI = np.zeros((nx, ny), np.uint8)
for (i, j, k) in seen:
    if np.isnan(RZ[i, j]) or Z[i, j, k] > RZ[i, j]:
        pass
    MULTI[i, j] += 1
    R[i, j] = 255
    RZ[i, j] = Z[i, j, k] if np.isnan(RZ[i, j]) else max(RZ[i, j], Z[i, j, k])
np.savez_compressed(os.path.join(OUT, "walk.npz"), REACH=REACH, Z=Z, HR=HR, OWN=OWN, R=R, RZ=RZ, MULTI=MULTI, bounds=np.array(B), cell=CELL, names=np.array(names))
zs = [float(Z[i, j, k]) for (i, j, k) in seen]
hist = {}
for z in zs:
    hist[round(z / 0.1) * 0.1] = hist.get(round(z / 0.1) * 0.1, 0) + 1
rep = {"cell_m": CELL, "bounds_xy_m": B, "start": [SP[0], SP[1]], "reachable_cells": len(seen), "cells_with_2plus_levels": int((MULTI > 1).sum()),
       "z_range_m": [min(zs), max(zs)], "z_hist_0.1m": {f"{k:.1f}": v for k, v in sorted(hist.items())}, "horizontal_blockers_top": sorted(blocked_by.items(), key=lambda t: -t[1])[:15]}
json.dump(rep, open(os.path.join(OUT, "walk_report.json"), "w"), ensure_ascii=False, indent=1)
from PIL import Image
img = np.zeros((ny, nx, 3), np.uint8)
anyfloor = ~np.isnan(Z[:, :, 0])
img[...] = 30
for i in range(nx):
    for j in range(ny):
        if anyfloor[i, j]:
            img[ny - 1 - j, i] = (70, 70, 80)
        if R[i, j]:
            z = RZ[i, j]; t = np.clip((z + 2.5) / 5.0, 0, 1)
            img[ny - 1 - j, i] = (int(255 * t), int(220 * (1 - abs(t - 0.5) * 2)), int(255 * (1 - t)))
Image.fromarray(img).resize((nx * 3 // 2, ny * 3 // 2), Image.NEAREST).save(os.path.join(OUT, "walk_levels.png"))
print(json.dumps(rep, ensure_ascii=False, indent=1))
