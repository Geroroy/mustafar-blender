"""착륙장 스테이지 → 게임 데이터 내보내기(v0.4_stage). Blender(bpy).
입력: mustafar_landing_stage.blend(build_stage.py 결과), stage_config.json
출력(out/mustafar_landing/):
  ground_hd.webp   배경(2배 밀도, 리마스터) — 가림 물체는 카메라에서만 빼고 그림자는 남김
  ground_sd.png    배경(1배, 오리지널: 게임 베이커와 같은 색 보정·포스터라이즈·베이어 디더)
  sprites_hd.png / sprites_sd.png  가림 물체 조각 아틀라스(낮은 상자 1 m 조각, 연석)
  collision.png    충돌 마스크(게임 좌표 0.125 m 칸, 흰색 = 걸을 수 있음) — 시각 형상과 따로 관리
  stage.json       위치·조각·충돌·출구·전투 자리·조명
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/export_stage.py [--samples 32] [--skip-ground]
"""
import json, math, os, sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage_cam as SC  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "stage_config.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "out", "mustafar_landing"); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(HERE, "work_export"); os.makedirs(TMP, exist_ok=True)
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "mustafar_landing_stage.blend"))
scene = bpy.context.scene; D = bpy.data; cam = D.objects["Game_Output_Iso"]; scene.camera = cam
scene.cycles.samples = SAMPLES
from PIL import Image  # noqa: E402

def rendered(o):
    if o.hide_render or o.type != 'MESH':
        return False
    return not any(c.hide_render for c in o.users_collection)


# ---------------------------------------------------------------- 가림 물체 조각 만들기
def evaluated_copy(objs, name):
    """모디파이어를 적용한 메시들을 하나로(재질 슬롯 유지)."""
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); mats = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        off = len(mats)
        for m in o.data.materials:
            mats.append(m)
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
        for f in tmp.faces:
            f.material_index += off
        me2 = D.meshes.new("tmp"); tmp.to_mesh(me2); tmp.free(); bm.from_mesh(me2); D.meshes.remove(me2); ev.to_mesh_clear()
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    return me


def make_obj(name, me):
    o = D.objects.new(name, me); scene.collection.objects.link(o); return o


sprites = []          # {id, obj}
occl_src = []
for key, spec in CFG["occluders"].items():
    if key.startswith("_"):
        continue
    objs = [D.objects[n] for n in spec["objects"]]
    occl_src += objs
    me = evaluated_copy(objs, f"OCC_{key}")
    if spec.get("slice_axis") == "Y":
        bb = [Vector(v.co) for v in me.vertices]; y0 = min(p.y for p in bb); y1 = max(p.y for p in bb)
        n = max(1, math.ceil((y1 - y0) / spec["slice_m"] - 1e-6)); step = (y1 - y0) / n
        for k in range(n):
            a, b = y0 + k * step, y0 + (k + 1) * step
            bm = bmesh.new(); bm.from_mesh(me)
            g = bm.verts[:] + bm.edges[:] + bm.faces[:]
            r = bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, a, 0), plane_no=(0, 1, 0), clear_inner=True)
            g = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, b, 0), plane_no=(0, 1, 0), clear_outer=True)
            m2 = D.meshes.new(f"{key}_{k}"); bm.to_mesh(m2); bm.free()
            for mt in me.materials:
                m2.materials.append(mt)
            if len(m2.polygons):
                sprites.append({"id": f"{key}_{k}", "obj": make_obj(f"SPR_{key}_{k}", m2)})
    elif spec.get("split_islands"):
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        seen = set(); comps = []
        for v in bm.verts:
            if v.index in seen:
                continue
            st, comp = [v], []
            while st:
                q = st.pop()
                if q.index in seen:
                    continue
                seen.add(q.index); comp.append(q.index); st += [e.other_vert(q) for e in q.link_edges]
            comps.append(set(comp))
        for k, comp in enumerate(sorted(comps, key=lambda c: min(bm.verts[i].co.x for i in c))):
            b2 = bm.copy(); b2.verts.ensure_lookup_table()
            bmesh.ops.delete(b2, geom=[b2.verts[i] for i in range(len(b2.verts)) if i not in comp], context='VERTS')
            m2 = D.meshes.new(f"{key}_{k}"); b2.to_mesh(m2); b2.free()
            for mt in me.materials:
                m2.materials.append(mt)
            sprites.append({"id": f"{key}_{k}", "obj": make_obj(f"SPR_{key}_{k}", m2)})
        bm.free()
for o in occl_src:
    o.hide_render = True              # 원본은 빼고 조각이 대신함(그림자·빛은 조각이 그대로 만듦)
print("sprites", [s["id"] for s in sprites], flush=True)

# ---------------------------------------------------------------- 배경
ground_objs = [o for o in D.objects if rendered(o) and not o.name.startswith("SPR_")]
for s in sprites:
    s["obj"].visible_camera = False
W2, H2, SX0, SY0 = SC.setup(scene, cam, CFG, density=2)
W1, H1 = W2 // 2, H2 // 2
if "--skip-ground" not in sys.argv:
    scene.render.film_transparent = False
    scene.render.filepath = os.path.join(TMP, "ground_2x.png")
    bpy.ops.render.render(write_still=True)
    print("ground rendered", W2, H2, flush=True)

# ---------------------------------------------------------------- 조각 렌더(자르기, 배경은 holdout = 가리면 투명)
for o in ground_objs:
    o.is_holdout = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
for s in sprites:
    for t in sprites:
        t["obj"].visible_camera = t is s
    box = SC.obj_screen_bbox(CFG, [s["obj"]], pad=4)
    w, h, sx0, sy0 = SC.setup(scene, cam, CFG, density=2, sub=box)
    scene.render.filepath = os.path.join(TMP, f"spr_{s['id']}_2x.png")
    bpy.ops.render.render(write_still=True)
    s["crop"] = (sx0, sy0, w // 2, h // 2)
    ev = s["obj"]; vs = [Vector(v.co) for v in ev.data.vertices]
    X0, X1 = min(p.x for p in vs), max(p.x for p in vs); Y0, Y1 = min(p.y for p in vs), max(p.y for p in vs)
    gx0, gy0 = SC.to_game(CFG, X1, Y1); gx1, gy1 = SC.to_game(CFG, X0, Y0)
    s["fp"] = (gx0, gy0, gx1, gy1)
    print("sprite", s["id"], w, h, flush=True)
for o in ground_objs:
    o.is_holdout = False

# ---------------------------------------------------------------- 충돌 마스크(게임 좌표 격자, 광선)
col = CFG["collision"]; cell = col["cell_m"]
dg = bpy.context.evaluated_depsgraph_get()
tris_all, owner = [], []
verts = []
for o in [o for o in D.objects if (rendered(o) or o.name.startswith("SPR_")) and o.name not in ("Stage_Lava_Sea",)]:
    ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
    base = len(verts); verts += [o.matrix_world @ v.co for v in me.vertices]
    for t in me.loop_triangles:
        tris_all.append([base + i for i in t.vertices]); owner.append(o.name)
    ev.to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris_all)
floor_names = set(col["floor_objects"])
X0, X1, Y0, Y1 = -18.0, 15.5, -26.0, 23.5                       # 판 주변(월드)
gx_a, gy_a = SC.to_game(CFG, X1, Y1); gx_b, gy_b = SC.to_game(CFG, X0, Y0)
gx0, gy0 = math.floor(gx_a), math.floor(gy_a)
cols = int(math.ceil((gx_b - gx0) / cell)); rows = int(math.ceil((gy_b - gy0) / cell))
mask = np.zeros((rows, cols), np.uint8)
for j in range(rows):
    for i in range(cols):
        gx, gy = gx0 + (i + 0.5) * cell, gy0 + (j + 0.5) * cell
        X, Y = SC.to_world(CFG, gx, gy)
        hit = bvh.ray_cast(Vector((X, Y, 2.2)), Vector((0, 0, -1)), 50.0)
        if hit[0] is None:
            continue
        if owner[hit[2]] in floor_names and abs(hit[0].z) <= col["floor_z_tol"]:
            mask[j, i] = 255
# 가림 물체(위가 열린 낮은 상자 포함)는 바닥 투영(볼록 껍질) 전체를 막는다 — 위에서 쏜 광선이 상자 안 바닥에 닿아도 걸을 수 없음
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p_ in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p_) <= 0:
            up.pop()
        up.append(p_)
    return lo[:-1] + up[:-1]


for s in sprites:
    hp = hull([(round(v.co.x, 3), round(v.co.y, 3)) for v in s["obj"].data.vertices if v.co.z > 0.02])
    gpoly = [SC.to_game(CFG, x, y) for x, y in hp]
    xs_ = [q[0] for q in gpoly]; ys_ = [q[1] for q in gpoly]
    for j in range(max(0, int((min(ys_) - gy0) / cell)), min(rows, int((max(ys_) - gy0) / cell) + 1)):
        for i in range(max(0, int((min(xs_) - gx0) / cell)), min(cols, int((max(xs_) - gx0) / cell) + 1)):
            px_, py_ = gx0 + (i + 0.5) * cell, gy0 + (j + 0.5) * cell
            n_ = len(gpoly); sg = [((gpoly[(k + 1) % n_][0] - gpoly[k][0]) * (py_ - gpoly[k][1]) - (gpoly[(k + 1) % n_][1] - gpoly[k][1]) * (px_ - gpoly[k][0])) for k in range(n_)]
            if all(v >= 0 for v in sg) or all(v <= 0 for v in sg):
                mask[j, i] = 0
Image.fromarray(mask).save(os.path.join(OUT, "collision.png"))
print("collision", cols, rows, int((mask > 0).sum()), flush=True)

# ---------------------------------------------------------------- 이미지 후처리(게임 베이커와 같은 보정)
BAYER = (np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4) / 16.0 - 0.5)


def grade(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    l = r * 0.3 + g * 0.59 + b * 0.11; k = 0.8
    c = lambda v: np.clip(128 + (v - 128) * 1.14, 0, 255)
    return np.stack([c((l + (r - l) * k) * 1.03), c(l + (g - l) * k), c((l + (b - l) * k) * 0.95)], -1)


def glow_mask(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    return (mn >= 185) & (mx >= 250) & (mx - mn <= 80)


def to_sd(img2x):
    """2배 렌더 → 1배 오리지널: 줄이기, 색 보정, 20단계 포스터라이즈 + 4×4 베이어, 1비트 알파."""
    im = img2x.resize((img2x.width // 2, img2x.height // 2), Image.LANCZOS)
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    g = np.where(glow_mask(rgb)[..., None], rgb, grade(rgb))
    H_, W_ = al.shape; t = np.tile(BAYER, (H_ // 4 + 1, W_ // 4 + 1))[:H_, :W_] * (255 / 20)
    q = np.clip(np.round((g + t[..., None]) / (255 / 20)) * (255 / 20), 0, 255)
    al2 = np.where(al > 127, 255, 0)
    return Image.fromarray(np.dstack([q, al2]).astype(np.uint8), "RGBA")


def to_hd(img2x):
    a = np.asarray(img2x.convert("RGBA")).astype(np.float32); rgb = a[..., :3]
    g = np.where(glow_mask(rgb)[..., None], rgb, grade(rgb))
    return Image.fromarray(np.dstack([g, a[..., 3]]).astype(np.uint8), "RGBA")


g2 = Image.open(os.path.join(TMP, "ground_2x.png")).convert("RGBA")
# 가장자리를 어두운 연기색으로 서서히(이미지 밖은 게임이 같은 색으로 채움)
FILL = (12, 6, 5)
hd = to_hd(g2); arr = np.asarray(hd).astype(np.float32)
yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
edge = np.minimum.reduce([xx, yy, arr.shape[1] - 1 - xx, arr.shape[0] - 1 - yy]) / 140.0
f = np.clip(edge, 0, 1)[..., None]
arr[..., :3] = arr[..., :3] * f + np.array(FILL) * (1 - f)
hd = Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB")
hd.save(os.path.join(OUT, "ground_hd.webp"), quality=86, method=5)
sd = to_sd(Image.fromarray(arr.astype(np.uint8), "RGBA")).convert("RGB")
sd.save(os.path.join(OUT, "ground_sd.png"), optimize=True)

# 아틀라스(선반 패킹)
def pack(images, maxw):
    x = y = rowh = 0; pos = []
    for im in images:
        if x + im.width > maxw:
            x, y, rowh = 0, y + rowh + 2, 0
        pos.append((x, y)); x += im.width + 2; rowh = max(rowh, im.height)
    atl = Image.new("RGBA", (maxw, y + rowh), (0, 0, 0, 0))
    for im, p in zip(images, pos):
        atl.paste(im, p)
    return atl, pos


hd_imgs, sd_imgs = [], []
for s in sprites:
    im2 = Image.open(os.path.join(TMP, f"spr_{s['id']}_2x.png")).convert("RGBA")
    hd_imgs.append(to_hd(im2)); sd_imgs.append(to_sd(im2))
atl_hd, pos_hd = pack(hd_imgs, 2048); atl_sd, pos_sd = pack(sd_imgs, 1024)
atl_hd.save(os.path.join(OUT, "sprites_hd.png"), optimize=True); atl_sd.save(os.path.join(OUT, "sprites_sd.png"), optimize=True)

# ---------------------------------------------------------------- stage.json
st = CFG["stage"]
def gpt(xy):
    gx, gy = SC.to_game(CFG, xy[0], xy[1]); return [round(gx, 3), round(gy, 3)]


props = []
for s, ih, is_, ph, ps in zip(sprites, hd_imgs, sd_imgs, pos_hd, pos_sd):
    gx0_, gy0_, gx1_, gy1_ = s["fp"]; cx, cy = (gx0_ + gx1_) / 2, (gy0_ + gy1_) / 2
    sx, sy = (cx - cy) * SC.HALF_W, (cx + cy) * SC.HALF_H
    c0x, c0y, cw, chh = s["crop"]
    props.append({"id": s["id"], "x": round(cx, 3), "y": round(cy, 3), "rect": [round(gx1_ - gx0_, 3), round(gy1_ - gy0_, 3)],
                  "sd": {"sx": ps[0], "sy": ps[1], "w": is_.width, "h": is_.height, "ox": round(sx - c0x, 2), "oy": round(sy - c0y, 2)},
                  "hd": {"sx": ph[0], "sy": ph[1], "w": ih.width, "h": ih.height, "ox": round((sx - c0x) * 2, 2), "oy": round((sy - c0y) * 2, 2)}})
ex = st["exit"]; ec = ex["center_world"]; eh = ex["half"]
e0 = SC.to_game(CFG, ec[0] + eh[0], ec[1] + eh[1]); e1 = SC.to_game(CFG, ec[0] - eh[0], ec[1] - eh[1])
cb = st["combat"]
lights = []
for k, (x, y) in enumerate(CFG["edge_light_xy"]):
    gx, gy = SC.to_game(CFG, x, y); lights.append({"x": gx, "y": gy, "z": 0.3, "r": 110, "g": 170, "b": 255, "rad": 70, "flicker": 0.02})
for y in CFG["eave_spot_y"]:
    gx, gy = SC.to_game(CFG, CFG["eave_spot_x"] - 3.0, y); lights.append({"x": gx, "y": gy, "z": 0.5, "r": 255, "g": 220, "b": 170, "rad": 120, "flicker": 0.0})
egx, egy = SC.to_game(CFG, 14.0, ec[1]); lights.append({"x": egx, "y": egy, "z": 1.0, "r": 200, "g": 220, "b": 255, "rad": 90, "flicker": 0.02})
for X, Y in ((-17.5, -25.5), (-17.5, 0), (-17.5, 23), (0, -25.5), (14.5, -25.5), (0, 23)):
    gx, gy = SC.to_game(CFG, X, Y); lights.append({"x": gx, "y": gy, "z": 0.0, "r": 255, "g": 110, "b": 40, "rad": 200, "flicker": 0.12})
data = {
    "version": 1, "name": st["name"], "layout": CFG["layout"], "note": "A3b 임시 작업 기준(영화 고증 확정 아님). 좌표는 게임 타일(1 m). gx = OX − Y, gy = OY − X (Blender m)",
    "offset": CFG["game"],
    "backdrop": {"sd": "ground_sd.png", "hd": "ground_hd.webp", "x": SX0, "y": SY0, "w": W1, "h": H1, "fill": list(FILL)},
    "sprites": {"sd": "sprites_sd.png", "hd": "sprites_hd.png"},
    "props": props,
    "collision": {"file": "collision.png", "cell": cell, "gx0": gx0, "gy0": gy0, "cols": cols, "rows": rows},
    "spawn": gpt(st["spawn_world"]),
    "exit": {"x0": round(min(e0[0], e1[0]), 3), "y0": round(min(e0[1], e1[1]), 3), "x1": round(max(e0[0], e1[0]), 3), "y1": round(max(e0[1], e1[1]), 3)},
    "combat": {"area": [gpt(p) for p in cb["area_world"]], "anakinStart": gpt(cb["anakin_start_world"]), "opponentStart": gpt(cb["opponent_start_world"]),
               "trigger": {"center": gpt(cb["trigger_world"]["center"]), "radius": cb["trigger_world"]["radius"]}},
    "ambient": [236, 206, 188],
    "lights": lights,
    "region": st["name"],
}
json.dump(data, open(os.path.join(OUT, "stage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OUT", OUT, "props", len(props), flush=True)
