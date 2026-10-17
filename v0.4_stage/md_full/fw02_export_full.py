"""FULL-2 맵 전체 게임 데이터 내보내기 — MO_STAGE.blend(원본 형상·원본 질감·MO 조명 그대로)에서 걸어서 닿는 곳 전체를 한 스테이지로. Blender(bpy).
md_orig/mo06_export_game.py와 md_art01/art04_export_game.py(이음선 보정용 한 번 렌더)를 바탕으로, 맵 전체에 필요한 것만 더했다:
  1) 걷는 칸: fw01_walk_open.py 결과(문 *2·*3·*24, 방어막 *31·*32·*33을 연 상태) 중 층 범위(−6 ~ +0.55 m). 칸마다 바닥 높이.
     칸 안 가는 구조는 mo06과 같이 가로 광선으로 막는다(열린 문 면은 빼고).
  2) 높이 지도(heights.png): 게임 격자 칸마다 바닥 높이(R·G 16비트, (h + 10 m) × 1000), B = 실내 칸이면 255. 걷는 칸 밖은 4 m까지 가장 가까운 바닥 높이로 채움.
  3) 렌더용 사본 분할(원본 객체는 그대로, 렌더에서만): 면마다
       HIDE(열린 문·방어막 면: 렌더에서 뺌) / ROOF(면 안 표본 중 하나라도 실내 칸 0.5 m 안, 그 바닥 + 1.2 m 위: 지붕 조각 — 실내에 있으면 게임이 숨김) /
       OCC(걷는 칸 2 m 안, 그 바닥 위로 솟은 면: 깊이 띠 가림 조각 — MO와 같은 규칙) / BG(배경).
     실내 바닥 높이 + 1.2 m에서 실내 근처 형상을 수평으로 잘라, 벽이 그 높이에서 끊기게 한다(형상 원본은 그대로, 렌더용 사본만 자름).
  4) 배경(지붕·가림 조각 형상은 카메라에서 빼고, 지붕은 그림자도 빼서 실내가 어둡지 않게)과 조각 층 두 장(가림만 / 가림+지붕) + 조각 번호 화면.
     조각은 fw03이 번호 화면으로 나눠 만든다(띠마다 따로 렌더하지 않음 → 이음선 없음, 렌더 시간 짧음).
실행: .venv-bpy/bin/python v0.4_stage/md_full/fw02_export_full.py <walk.npz> <MO walk_world_mask.npy> <duel_mus_both.bsp> [--samples 16] [--plan-only] [--skip-ground] [--skip-sprites(있는 층 렌더 재사용)]
"""
import json, math, os, struct, sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402
from PIL import Image  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "full_stage_config.json"), encoding="utf-8"))
WALK = np.load(sys.argv[1], allow_pickle=True)
MO_MASK = np.load(sys.argv[2])
BSP = sys.argv[3]
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 16
STAGE_BLEND = os.path.normpath(os.path.join(HERE, "..", CFG["stage_blend"]))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", CFG["out_dir"])); os.makedirs(OUT, exist_ok=True)
PREVIEW = "--preview" in sys.argv                       # 분류 확인용 저밀도 미리보기(_tmp/preview, 밀도 0.35, 4샘플)
TMP = os.path.join(OUT, "_tmp", "preview" if PREVIEW else ""); os.makedirs(TMP, exist_ok=True)
DEN = 0.35 if PREVIEW else 2
bpy.ops.wm.open_mainfile(filepath=STAGE_BLEND)
D = bpy.data; scene = D.scenes["MO_STAGE"]; cam = D.objects["Game_Output_Iso"]; scene.camera = cam
scene.cycles.samples = 4 if PREVIEW else SAMPLES
G = CFG["game"]
FIT = D.objects["MO_FIT"].matrix_world

# ---------------------------------------------------------------- 열린 모델(문·방어막) 상자(월드)
bb = open(BSP, "rb").read(); lo_, ll_ = struct.unpack_from("<ii", bb, 8 + 7 * 8)
MODS = list(struct.iter_unpack("<6f4i", bb[lo_:lo_ + ll_]))
OPEN_BOXES = []
for m in CFG["open_models"]:
    a = FIT @ Vector(MODS[m][:3]); b = FIT @ Vector(MODS[m][3:6])
    OPEN_BOXES.append((Vector((min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))) - Vector((0.02,) * 3), Vector((max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))) + Vector((0.02,) * 3)))
in_open = lambda pts: any(all(all(lo[k] <= p[k] <= hi[k] for k in range(3)) for p in pts) for lo, hi in OPEN_BOXES)

# ---------------------------------------------------------------- 원본 삼각형(월드) · BVH(열린 문 면 제외)
dg = bpy.context.evaluated_depsgraph_get()
src_objs = [o for o in scene.collection.all_objects if o.type == 'MESH' and len(o.data.polygons)]
verts, tris = [], []
n_open = 0
for o in src_objs:
    me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
    base = len(verts); vv = [o.matrix_world @ v.co for v in me.vertices]; verts += vv
    for t in me.loop_triangles:
        if in_open([vv[i] for i in t.vertices]):
            n_open += 1; continue
        tris.append([base + i for i in t.vertices])
    o.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris)
print("원본 삼각형(열린 문 면 뺀 충돌용)", len(tris), "열린 면", n_open, flush=True)

# ---------------------------------------------------------------- 걷는 칸 · 바닥 높이 · 실내
W = CFG["walk"]; cell = W["cell_m"]
REACH, Z, B = WALK["REACH"], WALK["Z"], [float(v) for v in WALK["bounds"]]
assert abs(float(WALK["cell"]) - cell) < 1e-9
X0w, X1w, Y0w, Y1w = B; nxw, nyw = Z.shape[0], Z.shape[1]
lo, hi = W["level_band_m"]
band = REACH & (Z >= lo) & (Z < hi)
floorz = np.where(band, Z, -np.inf).max(2)
walk_w = np.isfinite(floorz)
print("층 범위 칸", int(walk_w.sum()), flush=True)
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
floorz = np.where(walk_w, floorz, np.nan)
print("가는 구조로 막힌 칸", int(blocked_thin.sum()), "→ 걷는 칸", int(walk_w.sum()), flush=True)
# 실내 = MO 걷는 칸(판 층, bounds [-24,24,-52,26])에 없던 걷는 칸
mo = np.zeros_like(walk_w)
oi_, oj_ = int(round((-24.0 - X0w) / cell)), int(round((-52.0 - Y0w) / cell))
mo[oi_:oi_ + MO_MASK.shape[0], oj_:oj_ + MO_MASK.shape[1]] = MO_MASK
interior = walk_w & ~mo
print("실내 칸", int(interior.sum()), "판 층 칸", int((walk_w & mo).sum()), flush=True)


def spread(val, ok, steps):
    """ok 칸의 val을 8방향으로 steps번 퍼뜨림(가장 먼저 닿은 값). 반환: 값, 닿은 여부."""
    v = np.where(ok, val, np.nan).astype(np.float32); have = ok.copy()
    for _ in range(steps):
        nv, nh = v.copy(), have.copy()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sv = np.roll(np.roll(v, di, 0), dj, 1); sh = np.roll(np.roll(have, di, 0), dj, 1)
            take = sh & ~nh
            nv[take] = sv[take]; nh |= take
        v, have = nv, nh
    return v, have


near_f, near_ok = spread(floorz, walk_w, int(round(CFG["props"]["dilate_m"] / cell)))
int_f, int_ok = spread(floorz, interior, int(round(CFG["interior"]["near_m"] / cell)))
int_ok_wide = spread(floorz, interior, int(round(1.0 / cell)))[1]
fill_f, fill_ok = spread(floorz, walk_w, int(round(4.0 / cell)))

# ---------------------------------------------------------------- 게임 격자(충돌·높이)
gxa, gya = SC.to_game(CFG, X0w, Y1w), SC.to_game(CFG, X1w, Y0w)
gx0, gy0 = math.floor(min(gxa[0], gya[0])), math.floor(min(gxa[1], gya[1]))
gx1, gy1 = math.ceil(max(gxa[0], gya[0])), math.ceil(max(gxa[1], gya[1]))
cols, rows = int(round((gx1 - gx0) / cell)), int(round((gy1 - gy0) / cell))
mask = np.zeros((rows, cols), np.uint8); hts = np.zeros((rows, cols, 3), np.uint8)
for j in range(rows):
    gy = gy0 + (j + 0.5) * cell; X = G["OY"] - gy
    iw = int(math.floor((X - X0w) / cell))
    if not (0 <= iw < nxw):
        continue
    for i in range(cols):
        gx = gx0 + (i + 0.5) * cell; Y = G["OX"] - gx
        jw = int(math.floor((Y - Y0w) / cell))
        if not (0 <= jw < nyw):
            continue
        if walk_w[iw, jw]:
            mask[j, i] = 255
        h = float(fill_f[iw, jw]) if fill_ok[iw, jw] else 0.0
        code = int(round((h + 10.0) * 1000)); hts[j, i] = (code >> 8, code & 255, 255 if interior[iw, jw] else 0)
Image.fromarray(mask).save(os.path.join(OUT, "collision.png"))
Image.fromarray(hts, "RGB").save(os.path.join(OUT, "heights.png"))
print("collision", cols, rows, int((mask > 0).sum()), "gx0 gy0", gx0, gy0, flush=True)
np.savez_compressed(os.path.join(TMP, "walk_full.npz"), walk=walk_w, floorz=floorz, interior=interior)

# ---------------------------------------------------------------- 렌더용 사본: 실내 높이에서 수평 자르기 + 분류
P = CFG["props"]; IC = CFG["interior"]; cut = IC["cut_m"]
cells = lambda c: (int(math.floor((c.x - X0w) / cell)), int(math.floor((c.y - Y0w) / cell)))
def over_interior(f):
    """면 안을 0.5 m 이하 간격으로 표본 → 어느 표본이 실내 칸(0.5 m 안) 위, 그 바닥 + cut 위에 있으면 지붕.
    면 중심 하나만 보면 큰 지붕 삼각형(중심이 벽·바깥 위)을 놓친다."""
    vs = [np.array(v.co[:]) for v in f.verts]
    for t in range(1, len(vs) - 1):
        a, b, c_ = vs[0], vs[t], vs[t + 1]
        n = int(min(60, max(1, math.ceil(max(np.linalg.norm(b - a), np.linalg.norm(c_ - a), np.linalg.norm(c_ - b)) / 0.5))))
        u, v = np.meshgrid(np.arange(n + 1), np.arange(n + 1)); m = (u + v) <= n
        u, v = u[m] / n, v[m] / n
        pts = a[None] + u[:, None] * (b - a)[None] + v[:, None] * (c_ - a)[None]
        ii_ = np.floor((pts[:, 0] - X0w) / cell).astype(int); jj_ = np.floor((pts[:, 1] - Y0w) / cell).astype(int)
        ok = (ii_ >= 0) & (ii_ < nxw) & (jj_ >= 0) & (jj_ < nyw)
        ii_, jj_, zz = ii_[ok], jj_[ok], pts[ok, 2]
        sel = int_ok[ii_, jj_]
        if sel.any() and (zz[sel] > int_f[ii_[sel], jj_[sel]] + cut - 0.02).any():
            return True
    return False

groups = {"BG": [], "OCC": [], "ROOF": []}; n_cls = {"BG": 0, "OCC": 0, "ROOF": 0, "HIDE": 0}; n_src = 0
for o in src_objs:
    me = o.evaluated_get(dg).to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); o.evaluated_get(dg).to_mesh_clear()
    bm.transform(o.matrix_world)
    n_src += len(bm.faces)
    # 원본 면마다 분류 번호를 먼저 붙인다(HIDE는 원본 면 기준). 자르기는 실내 1 m 안의 면만
    lay = bm.faces.layers.int.new("src")
    for f in bm.faces:
        f[lay] = 1 if in_open([v.co for v in f.verts]) else 0
    near_int = []
    for f in bm.faces:
        i, j = cells(f.calc_center_median())
        if 0 <= i < nxw and 0 <= j < nyw and int_ok_wide[i, j]:
            near_int.append(f)
    for L in IC["cut_levels"]:
        if not near_int:
            break
        geom = list({e for f in near_int if f.is_valid for e in f.edges}) + [f for f in near_int if f.is_valid] + list({v for f in near_int if f.is_valid for v in f.verts})
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, L + cut), plane_no=(0, 0, 1))
        near_int = list({f for f in near_int if f.is_valid} | {g for g in res["geom"] if isinstance(g, bmesh.types.BMFace) and g.is_valid})
    bm.faces.ensure_lookup_table()
    sel = {"BG": [], "OCC": [], "ROOF": [], "HIDE": []}
    for f in bm.faces:
        if f[lay] == 1:
            sel["HIDE"].append(f.index); continue
        c = f.calc_center_median(); i, j = cells(c)
        k = "ROOF" if over_interior(f) else "BG"
        if k == "BG" and 0 <= i < nxw and 0 <= j < nyw:
            if near_ok[i, j] and float(near_f[i, j]) + P["min_z"] < c.z < float(near_f[i, j]) + P["max_z"]:
                ext = not int_ok_wide[i, j]
                if not (ext and any(b[0][0] <= c.x <= b[1][0] and b[0][1] <= c.y <= b[1][1] and b[0][2] <= c.z <= b[1][2] for b in P.get("exclude_boxes", []))):
                    k = "OCC"
        sel[k].append(f.index)
    for k in sel:
        n_cls[k] += len(sel[k])
    for k in ("BG", "OCC", "ROOF"):
        if not sel[k]:
            continue
        keep = set(sel[k]); b2 = bm.copy(); b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context='FACES')
        m2 = D.meshes.new(f"{k}_{o.name}"); b2.to_mesh(m2); b2.free()
        for mt in o.data.materials:
            m2.materials.append(mt)
        ob = D.objects.new(f"{k}_{o.name}", m2); scene.collection.objects.link(ob)
        groups[k].append(ob)
    bm.free()
    o.hide_render = True
print("면 분류(자른 뒤):", n_cls, "원본 면", n_src, flush=True)

# ---------------------------------------------------------------- 깊이 띠(G = OX+OY − X − Y)
Gk = G["OX"] + G["OY"]; bandw = P["band_m"]


def make_bands(objs, prefix):
    gmin, gmax = 1e9, -1e9
    for ob in objs:
        for v in ob.data.vertices:
            g = Gk - v.co.x - v.co.y; gmin = min(gmin, g); gmax = max(gmax, g)
    G0b = math.floor(gmin); nb = int(math.ceil((gmax - G0b) / bandw)); bands = {}
    for ob in objs:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        for k in range(1, nb):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(Gk - (G0b + k * bandw), 0, 0), plane_no=(1, 1, 0))
        bm.faces.ensure_lookup_table(); per = {}
        for f in bm.faces:
            c = f.calc_center_median(); b = int(math.floor((Gk - c.x - c.y - G0b) / bandw))
            per.setdefault(max(0, min(nb - 1, b)), []).append(f.index)
        for b, idxs in per.items():
            keep = set(idxs); b2 = bm.copy(); b2.faces.ensure_lookup_table()
            bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context='FACES')
            bands.setdefault(b, []).append((ob, b2))
        bm.free()
    out = []
    for b in sorted(bands):
        bm = bmesh.new(); mats = []
        for ob, b2 in bands[b]:
            off = len(mats); mats += list(ob.data.materials)
            for f in b2.faces:
                f.material_index += off
            m2 = D.meshes.new("t"); b2.to_mesh(m2); b2.free(); bm.from_mesh(m2); D.meshes.remove(m2)
        me = D.meshes.new(f"SPR_{prefix}{b}"); bm.to_mesh(me); bm.free()
        for mt in mats:
            me.materials.append(mt)
        if len(me.polygons):
            o = D.objects.new(f"SPR_{prefix}{b}", me); scene.collection.objects.link(o)
            out.append({"id": f"{prefix}_{b:03d}", "obj": o, "G": G0b + (b + 0.5) * bandw, "roof": prefix == "roof", "band": b})
    for ob in objs:
        D.objects.remove(ob)
    return out


sprites = make_bands(groups["OCC"], "band") + make_bands(groups["ROOF"], "roof")
print("조각: 가림", sum(not s["roof"] for s in sprites), "지붕", sum(s["roof"] for s in sprites), flush=True)
for s in sprites:
    if s["roof"]:
        s["obj"].visible_shadow = False                # 지붕은 그림자를 드리우지 않는다 → 실내가 밝게 보임(잘라 보기)
ground_objs = groups["BG"]
fr = SC.frame(CFG); bx = SC.obj_screen_bbox(CFG, [s["obj"] for s in sprites], pad=4)
print("배경(2배)", (fr[2] - fr[0]) * 2, (fr[3] - fr[1]) * 2, "조각 층(2배)", (bx[2] - bx[0]) * 2, (bx[3] - bx[1]) * 2, flush=True)
if "--plan-only" in sys.argv:
    sys.exit(0)

TILE = int(sys.argv[sys.argv.index("--tile") + 1]) if "--tile" in sys.argv else 2400


def render_tiled(path, box, density, maxpx=None, ov=8):
    """큰 화면을 겹친 타일로 나눠 렌더하고 이어 붙인다(한 장 72 MP는 메모리 부족). 직교 카메라라 타일이 픽셀까지 맞는다.
    box = 게임 1배 px (x0, y0, x1, y1), 겹침 ov(1배 px)만큼 더 렌더하고 잘라 낸다(디노이즈 가장자리 차이를 버림)."""
    x0, y0, x1, y1 = [int(v) for v in box]
    W, H = int(round((x1 - x0) * density)), int(round((y1 - y0) * density))
    step = max(64, int((maxpx or TILE) / density))
    big = None; mode = scene.render.image_settings.color_mode
    for ty in range(y0, y1, step):
        for tx in range(x0, x1, step):
            sub = (tx - ov, ty - ov, min(tx + step, x1) + ov, min(ty + step, y1) + ov)
            SC.setup(scene, cam, CFG, density=density, sub=sub)
            tp = path + ".tile.png"; scene.render.filepath = tp; bpy.ops.render.render(write_still=True)
            im = Image.open(tp); im.load()
            if big is None:
                big = Image.new(im.mode, (W, H))
            cx0 = int(round(ov * density)); cw = int(round((min(tx + step, x1) - tx) * density)); ch = int(round((min(ty + step, y1) - ty) * density))
            big.paste(im.crop((cx0, cx0, cx0 + cw, cx0 + ch)), (int(round((tx - x0) * density)), int(round((ty - y0) * density))))
            print("tile", os.path.basename(path), tx, ty, flush=True)
    big.save(path); os.remove(path + ".tile.png")
    return W, H


# ---------------------------------------------------------------- 배경
for s in sprites:
    s["obj"].visible_camera = False
if "--skip-ground" not in sys.argv:
    scene.render.film_transparent = False; scene.render.image_settings.color_mode = 'RGB'
    W2, H2 = render_tiled(os.path.join(TMP, "ground_2x.png"), SC.frame(CFG), DEN)
    print("ground rendered", W2, H2, flush=True)

# ---------------------------------------------------------------- 조각 층: 띠마다 따로가 아니라 '층' 두 장을 한 번씩 렌더하고, 조각 번호 화면으로 나눈다(fw03)
#   layer_occ : 가림 조각만 카메라에 보임(지붕은 카메라·그림자 모두 없음), 배경 holdout — 실내에 있을 때·지붕 없는 곳의 가림 조각 색
#   layer_all : 가림 + 지붕 조각, 배경 holdout — 바깥에서 볼 때의 지붕 색, 그리고 어느 가림 픽셀이 지붕에 덮이는지
#   *_id      : 맨 앞 조각 번호(R + 256·G), 1샘플·필터 최소·Raw
# 한 장에서 나누므로 띠 사이 이음선이 생기지 않는다.
for o in ground_objs:
    o.is_holdout = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
for k, s in enumerate(sprites):
    s["obj"].pass_index = k + 1; s["pid"] = k + 1
box = SC.obj_screen_bbox(CFG, [s["obj"] for s in sprites], pad=4)
sx0, sy0 = box[0], box[1]
idm = D.materials.new("FULL_ID_IDX"); nt = idm.node_tree; nt.nodes.clear()
oi = nt.nodes.new("ShaderNodeObjectInfo")
md = nt.nodes.new("ShaderNodeMath"); md.operation = 'MODULO'; md.inputs[1].default_value = 256.0
dv = nt.nodes.new("ShaderNodeMath"); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 256.0
fl = nt.nodes.new("ShaderNodeMath"); fl.operation = 'FLOOR'
r = nt.nodes.new("ShaderNodeMath"); r.operation = 'DIVIDE'; r.inputs[1].default_value = 255.0
g_ = nt.nodes.new("ShaderNodeMath"); g_.operation = 'DIVIDE'; g_.inputs[1].default_value = 255.0
cc = nt.nodes.new("ShaderNodeCombineColor"); em = nt.nodes.new("ShaderNodeEmission"); mo_ = nt.nodes.new("ShaderNodeOutputMaterial")
L = nt.links.new
L(oi.outputs["Object Index"], md.inputs[0]); L(oi.outputs["Object Index"], dv.inputs[0]); L(dv.outputs[0], fl.inputs[0])
L(md.outputs[0], r.inputs[0]); L(fl.outputs[0], g_.inputs[0]); L(r.outputs[0], cc.inputs[0]); L(g_.outputs[0], cc.inputs[1])
L(cc.outputs[0], em.inputs[0]); L(em.outputs[0], mo_.inputs[0])
vl = scene.view_layers[0]


def render_layer(name, roofs_visible):
    for s in sprites:
        s["obj"].visible_camera = (not s["roof"]) or roofs_visible
    p = os.path.join(TMP, f"{name}_2x.png")
    if "--skip-sprites" not in sys.argv or not os.path.exists(p):
        render_tiled(p, box, DEN)
    vl.material_override = idm
    keep = scene.cycles.samples, scene.cycles.use_denoising, scene.cycles.filter_width, scene.view_settings.view_transform, scene.render.dither_intensity
    scene.cycles.samples = 1; scene.cycles.use_denoising = False; scene.cycles.filter_width = 0.01; scene.view_settings.view_transform = 'Raw'; scene.render.dither_intensity = 0.0
    render_tiled(os.path.join(TMP, f"{name}_id_2x.png"), box, DEN)
    vl.material_override = None
    scene.cycles.samples, scene.cycles.use_denoising, scene.cycles.filter_width, scene.view_settings.view_transform, scene.render.dither_intensity = keep
    print("layer", name, flush=True)


render_layer("layer_occ", False)
render_layer("layer_all", True)
json.dump({"layer_crop": (sx0, sy0, box[2] - box[0], box[3] - box[1]), "density": DEN, "frame": list(SC.frame(CFG)),
           "sprites": [{"id": s["id"], "G": s["G"], "roof": s["roof"], "band": s["band"], "pid": s["pid"]} for s in sprites]},
          open(os.path.join(TMP, "layers_meta.json"), "w"))
print("렌더 끝", flush=True)
