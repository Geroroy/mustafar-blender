"""MO-6 게임 데이터 내보내기 — MO_STAGE.blend(원본 형상) → 배경·가림 조각·충돌·stage.json. Blender(bpy).
원본 형상은 고치지 않는다. 하는 일:
  1) 렌더용 사본 분할: 판 위로 솟은 삼각형(우주선·상자·통·톱니 등)을 따로 떼어 깊이 띠(X+Y)로 자른 조각으로 굽는다.
     나머지(바닥·시설·옆 통로·용암·암벽·판 아래)는 배경. 사본 삼각형 수의 합 = 원본 삼각형 수를 검사한다.
  2) 배경: 게임 카메라로 2배 밀도 렌더(조각 형상은 카메라에서만 빼고 그림자는 남김).
  3) 조각: 띠마다 배경을 holdout으로 두고 따로 렌더(가려지면 투명).
  4) 충돌: mo04 보행 분석(walk.npz)의 '시작점과 같은 층' 칸 + 칸 안 가는 구조(우주선 다리 등)를 가로 광선으로 막음. 시각 형상과 따로 관리.
  5) stage.json: 시작점(원본 info_player_start)·출구(원본 입구 계단 위)·전투 자리·조명.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo06_export_game.py <walk.npz> [--samples 32] [--skip-ground] [--only-collision]
"""
import json, math, os, sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402
from PIL import Image  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "mo_stage_config.json"), encoding="utf-8"))
WALK = np.load(sys.argv[1], allow_pickle=True)
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
STAGE_BLEND = os.path.normpath(os.path.join(HERE, "..", CFG["stage_blend"]))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", CFG["out_dir"])); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, "_tmp"); os.makedirs(TMP, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=STAGE_BLEND)
D = bpy.data; scene = D.scenes["MO_STAGE"]; cam = D.objects["Game_Output_Iso"]; scene.camera = cam
scene.cycles.samples = SAMPLES
G = CFG["game"]

# ---------------------------------------------------------------- 원본 삼각형(월드 좌표) · BVH
dg = bpy.context.evaluated_depsgraph_get()
src_objs = [o for o in scene.collection.all_objects if o.type == 'MESH' and len(o.data.polygons)]
verts, tris, owner = [], [], []
for oi, o in enumerate(src_objs):
    me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
    base = len(verts); verts += [o.matrix_world @ v.co for v in me.vertices]
    for t in me.loop_triangles:
        tris.append([base + i for i in t.vertices]); owner.append(oi)
    o.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris)
print("원본 삼각형", len(tris), flush=True)

# ---------------------------------------------------------------- 충돌 마스크(게임 좌표 격자)
W = CFG["walk"]; cell = W["cell_m"]
REACH, Z, B = WALK["REACH"], WALK["Z"], [float(v) for v in WALK["bounds"]]
assert abs(float(WALK["cell"]) - cell) < 1e-9
X0w, X1w, Y0w, Y1w = B; nxw, nyw = Z.shape[0], Z.shape[1]
lo, hi = W["level_band_m"]
band = REACH & (Z >= lo) & (Z < hi)                      # 시작점과 같은 층(판 윗면)에 걸어서 닿는 칸
floorz = np.where(band, Z, -np.inf).max(2)               # 칸마다 그 층의 바닥 높이(여러 개면 가장 높은 것)
walk_w = np.isfinite(floorz)
print("같은 층 칸", int(walk_w.sum()), flush=True)
# 칸 안 가는 구조(가로 광선): 바닥 위 0.6·1.0·1.4 m 높이에서 8방향 0.09 m
dirs = [Vector((math.cos(a), math.sin(a), 0)) for a in np.arange(8) * math.pi / 4]
blocked_thin = np.zeros_like(walk_w)
ii, jj = np.nonzero(walk_w)
for i, j in zip(ii, jj):
    x, y, f = X0w + (i + 0.5) * cell, Y0w + (j + 0.5) * cell, float(floorz[i, j])
    hit = False
    for h in (0.6, 1.0, 1.4):
        o_ = Vector((x, y, f + h))
        for d in dirs:
            if bvh.ray_cast(o_, d, 0.09)[0] is not None:
                hit = True; break
        if hit:
            break
    blocked_thin[i, j] = hit
walk_w &= ~blocked_thin
print("가는 구조로 막힌 칸", int(blocked_thin.sum()), "→ 걷는 칸", int(walk_w.sum()), flush=True)
# 게임 격자로(칸 정렬이 같다: gx = OX − Y, gy = OY − X)
gxa, gya = SC.to_game(CFG, X0w, Y1w), SC.to_game(CFG, X1w, Y0w)
gx0, gy0 = math.floor(min(gxa[0], gya[0])), math.floor(min(gxa[1], gya[1]))
gx1, gy1 = math.ceil(max(gxa[0], gya[0])), math.ceil(max(gxa[1], gya[1]))
cols, rows = int(round((gx1 - gx0) / cell)), int(round((gy1 - gy0) / cell))
mask = np.zeros((rows, cols), np.uint8)
for j in range(rows):
    gy = gy0 + (j + 0.5) * cell; X = G["OY"] - gy
    iw = int(math.floor((X - X0w) / cell))
    if not (0 <= iw < nxw):
        continue
    for i in range(cols):
        gx = gx0 + (i + 0.5) * cell; Y = G["OX"] - gx
        jw = int(math.floor((Y - Y0w) / cell))
        if 0 <= jw < nyw and walk_w[iw, jw]:
            mask[j, i] = 255
Image.fromarray(mask).save(os.path.join(OUT, "collision.png"))
print("collision", cols, rows, int((mask > 0).sum()), "gx0 gy0", gx0, gy0, flush=True)
np.save(os.path.join(TMP, "walk_world_mask.npy"), walk_w)
if "--only-collision" in sys.argv:
    sys.exit(0)

# ---------------------------------------------------------------- 렌더용 사본 분할(원본 객체는 그대로, 렌더에서만 뺌)
P = CFG["props"]
dil = int(round(P["dilate_m"] / cell))
fp = walk_w.copy()
for _ in range(dil):                                     # 십자 팽창
    n = fp.copy(); n[1:] |= fp[:-1]; n[:-1] |= fp[1:]; n[:, 1:] |= fp[:, :-1]; n[:, :-1] |= fp[:, 1:]; fp = n
# 판 아래로 이어진 층(시설 통로 −1.8 m 등)이 아니라 같은 층 위쪽만 보게 높이 조건 사용
G0 = None
bm_pr = {}; n_bg = n_pr = 0
bg_objs, pr_objs = [], []
for o in src_objs:
    me = o.evaluated_get(dg).to_mesh()
    bmw = bmesh.new(); bmw.from_mesh(me); o.evaluated_get(dg).to_mesh_clear()
    bmw.transform(o.matrix_world)
    pr_faces = []
    for f in bmw.faces:
        c = f.calc_center_median()
        i = int(math.floor((c.x - X0w) / cell)); j = int(math.floor((c.y - Y0w) / cell))
        if 0 <= i < nxw and 0 <= j < nyw and fp[i, j] and P["min_z"] < c.z < P["max_z"] \
                and not any(b[0][0] <= c.x <= b[1][0] and b[0][1] <= c.y <= b[1][1] and b[0][2] <= c.z <= b[1][2] for b in P.get("exclude_boxes", [])):
            pr_faces.append(f)
    keep = set(f.index for f in pr_faces)
    bmp = bmw.copy()
    bmesh.ops.delete(bmw, geom=pr_faces, context='FACES')
    bmp.faces.ensure_lookup_table()
    bmesh.ops.delete(bmp, geom=[f for f in bmp.faces if f.index not in keep], context='FACES')
    for kind, bm_ in (("BG", bmw), ("PR", bmp)):
        if not len(bm_.faces):
            bm_.free(); continue
        m2 = D.meshes.new(f"{kind}_{o.name}"); bm_.to_mesh(m2); bm_.free()
        for mt in o.data.materials:
            m2.materials.append(mt)
        ob = D.objects.new(f"{kind}_{o.name}", m2); scene.collection.objects.link(ob)
        (bg_objs if kind == "BG" else pr_objs).append(ob)
    o.hide_render = True
n_bg = sum(len(o.data.polygons) for o in bg_objs); n_pr = sum(len(o.data.polygons) for o in pr_objs)
n_src = sum(len(o.data.polygons) for o in src_objs)
assert n_bg + n_pr == n_src, (n_bg, n_pr, n_src)
print(f"사본 분할: 배경 {n_bg} + 조각 대상 {n_pr} = 원본 {n_src} 면", flush=True)

# ---------------------------------------------------------------- 깊이 띠(게임 깊이 G = gx+gy = OX+OY − X − Y)로 자르기
Gk = G["OX"] + G["OY"]
sprites = []
bandw = P["band_m"]
allbm = {}
gmin, gmax = 1e9, -1e9
for ob in pr_objs:
    for v in ob.data.vertices:
        g = Gk - v.co.x - v.co.y; gmin = min(gmin, g); gmax = max(gmax, g)
G0b = math.floor(gmin)
nb = int(math.ceil((gmax - G0b) / bandw))
bands = {}
for ob in pr_objs:
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for k in range(1, nb):
        gk = G0b + k * bandw                           # X + Y = Gk − gk
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(Gk - gk, 0, 0), plane_no=(1, 1, 0))
    bm.faces.ensure_lookup_table()
    per = {}
    for f in bm.faces:
        c = f.calc_center_median(); b = int(math.floor((Gk - c.x - c.y - G0b) / bandw))
        per.setdefault(max(0, min(nb - 1, b)), []).append(f.index)
    for b, idxs in per.items():
        keep = set(idxs); b2 = bm.copy(); b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context='FACES')
        bands.setdefault(b, []).append((ob, b2))
    bm.free()
for b in sorted(bands):
    bm = bmesh.new(); mats = []
    for ob, b2 in bands[b]:
        off = len(mats); mats += list(ob.data.materials)
        for f in b2.faces:
            f.material_index += off
        m2 = D.meshes.new("t"); b2.to_mesh(m2); b2.free(); bm.from_mesh(m2); D.meshes.remove(m2)
    me = D.meshes.new(f"SPR_band{b}"); bm.to_mesh(me); bm.free()
    for mt in mats:
        me.materials.append(mt)
    if len(me.polygons):
        o = D.objects.new(f"SPR_band{b}", me); scene.collection.objects.link(o)
        sprites.append({"id": f"band_{b:03d}", "obj": o, "G": G0b + (b + 0.5) * bandw})
for ob in pr_objs:                                        # 띠 조각이 형상을 대신한다(같은 면이 겹쳐 그림자 얼룩이 생기지 않게)
    D.objects.remove(ob)
n_spr = sum(len(s["obj"].data.polygons) for s in sprites)
print("조각", len(sprites), "면", n_spr, "(분할로 면이 더 생김)", flush=True)

# ---------------------------------------------------------------- 배경 렌더
for s in sprites:
    s["obj"].visible_camera = False
ground_objs = bg_objs
W2, H2, SX0, SY0 = SC.setup(scene, cam, CFG, density=2)
W1, H1 = W2 // 2, H2 // 2
if "--skip-ground" not in sys.argv:
    scene.render.film_transparent = False
    scene.render.filepath = os.path.join(TMP, "ground_2x.png")
    bpy.ops.render.render(write_still=True)
    print("ground rendered", W2, H2, flush=True)

# ---------------------------------------------------------------- 조각 렌더(배경 holdout, 자신만 카메라에 보임)
for o in ground_objs:
    o.is_holdout = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
for s in sprites:
    for t in sprites:
        t["obj"].visible_camera = t is s                   # 다른 조각은 그림자만 남김
    box = SC.obj_screen_bbox(CFG, [s["obj"]], pad=4)
    w, h, sx0, sy0 = SC.setup(scene, cam, CFG, density=2, sub=box)
    p = os.path.join(TMP, f"spr_{s['id']}_2x.png")
    if "--skip-sprites" not in sys.argv or not os.path.exists(p):
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
    s["crop"] = (sx0, sy0, w // 2, h // 2)
    print("sprite", s["id"], w, h, flush=True)
for o in ground_objs:
    o.is_holdout = False
json.dump({s["id"]: {"crop": s["crop"], "G": s["G"]} for s in sprites}, open(os.path.join(TMP, "sprites_meta.json"), "w"))
print("렌더 끝", flush=True)
