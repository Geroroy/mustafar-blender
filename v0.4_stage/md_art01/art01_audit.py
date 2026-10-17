"""ART01-1 재질 점검 — MO_STAGE.blend(원본 형상 그대로)의 재질 89개를 표면 용도로 분류하기 위한 자료를 만든다. Blender(bpy).
형상·재질은 바꾸지 않는다(파일을 저장하지 않음). 결과:
  - audit.json: 재질마다 엔진 셰이더 경로·질감 파일·삼각형 수·UV(넓이 0인 면 비율, 범위)·높이·법선 분포·게임 카메라 화면에 실제로 보이는 픽셀 수
  - id_game_cam.exr → id_game_cam.png: 게임 카메라(1배)에서 재질마다 다른 색으로 칠한 화면(재질 번호 이미지)
엔진 셰이더 경로는 추출 목록(duel_mus_both_inventory.json)의 재질 순서 = OBJ 재질 번호(material_N)로 대응한다(누락 목록과 대조해 확인).
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art01_audit.py <MO_STAGE.blend> <inventory.json> <출력 폴더>
"""
import colorsys, json, math, os, sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

BLEND, INV, OUTD = (os.path.abspath(p) for p in sys.argv[-3:])
os.makedirs(OUTD, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
D = bpy.data; sc = D.scenes["MO_STAGE"]; CFG = json.loads(sc["stage_config"]); cam = D.objects["Game_Output_Iso"]
inv = list(json.load(open(INV, encoding="utf-8"))["materials"].items())
shader_of = {f"material_{i}": k for i, (k, _) in enumerate(inv)}

objs = [o for o in sc.collection.all_objects if o.type == 'MESH' and len(o.data.polygons)]
rows = {}
for o in objs:
    me = o.data; mw = o.matrix_world
    uv = me.uv_layers.active
    nm = np.array(mw.to_3x3().inverted().transposed())
    for p in me.polygons:
        ma = me.materials[p.material_index] if me.materials else None
        key = ma.name.split(".")[0] if ma else "(none)"
        r = rows.setdefault(key, {"tris": 0, "uv_zero": 0, "uv_min": [1e9, 1e9], "uv_max": [-1e9, -1e9], "z": [], "nz": [], "xy": [], "objects": set()})
        r["tris"] += len(p.vertices) - 2; r["objects"].add(o.name)
        c = mw @ p.center; n = nm @ np.array(p.normal); n /= (np.linalg.norm(n) or 1)
        r["z"].append(c.z); r["nz"].append(float(n[2])); r["xy"].append((c.x, c.y))
        if uv:
            us = [uv.data[li].uv for li in p.loop_indices]
            for u in us:
                r["uv_min"] = [min(r["uv_min"][0], u[0]), min(r["uv_min"][1], u[1])]; r["uv_max"] = [max(r["uv_max"][0], u[0]), max(r["uv_max"][1], u[1])]
            a = 0.0
            for k in range(1, len(us) - 1):
                a += abs((us[k][0] - us[0][0]) * (us[k + 1][1] - us[0][1]) - (us[k + 1][0] - us[0][0]) * (us[k][1] - us[0][1])) / 2
            if a < 1e-9:
                r["uv_zero"] += 1
        else:
            r["uv_zero"] += 1

# ---- 재질 번호 화면: 재질마다 발광 하나(값 = 번호/256), 1샘플·필터 최소 → 섞이지 않음
keys = sorted(rows, key=lambda k: int(k.split("_")[1]) if k.startswith("material_") else 999)
idx = {k: i + 1 for i, k in enumerate(keys)}
orig = {}
for o in objs:
    orig[o.name] = list(o.data.materials)
    for si, ma in enumerate(o.data.materials):
        key = ma.name.split(".")[0]
        idm = D.materials.get("ID_" + key)
        if idm is None:
            idm = D.materials.new("ID_" + key); idm.use_nodes = True; nt = idm.node_tree; nt.nodes.clear()
            em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (idx[key] / 256.0, 0, 0, 1); em.inputs[1].default_value = 1.0
            out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
        o.data.materials[si] = idm
for o in [o for o in sc.objects if o.type == 'LIGHT']:
    o.hide_render = True
sc.world = None
W, H, sx0, sy0 = SC.setup(sc, cam, CFG, density=1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.cycles.filter_width = 0.01
sc.cycles.max_bounces = 0; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
exr = os.path.join(OUTD, "id_game_cam.exr"); sc.render.filepath = exr
bpy.ops.render.render(write_still=True)
img = D.images.load(exr); px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]
ids = np.round(px[..., 0] * 256).astype(int) * (px[..., 3] > 0.5)
vis = {k: int((ids == i).sum()) for k, i in idx.items()}
# 보이는 색 그림(사람이 보기 쉬운 색상환 배정)
from PIL import Image  # noqa: E402
pal = np.zeros((len(keys) + 2, 3), np.uint8)
for k, i in idx.items():
    h = (i * 0.618034) % 1.0; r_, g_, b_ = colorsys.hsv_to_rgb(h, 0.75, 0.95); pal[i] = (int(r_ * 255), int(g_ * 255), int(b_ * 255))
Image.fromarray(pal[np.clip(ids, 0, len(keys) + 1)]).save(os.path.join(OUTD, "id_game_cam.png"))
np.save(os.path.join(OUTD, "id_game_cam.npy"), ids.astype(np.uint8))

rep = {"blend": BLEND, "frame_px": [W, H, sx0, sy0], "id_index": idx, "materials": {}}
for k in keys:
    r = rows[k]; z = np.array(r["z"]); nz = np.array(r["nz"]); xy = np.array(r["xy"])
    m = D.materials.get(k)
    im = None
    for o in objs:
        for ma in orig[o.name]:
            if ma.name.split(".")[0] == k and ma.use_nodes:
                ii = [n.image.name for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
                im = ii[0] if ii else None
    rep["materials"][k] = {
        "shader": shader_of.get(k), "image": im, "tris": r["tris"], "objects": sorted(r["objects"]),
        "uv_zero_area_faces": r["uv_zero"], "uv_range": [r["uv_min"], r["uv_max"]],
        "z_m": [round(float(z.min()), 2), round(float(np.median(z)), 2), round(float(z.max()), 2)],
        "normal_up_frac": round(float((nz > 0.7).mean()), 3), "normal_side_frac": round(float((abs(nz) <= 0.7).mean()), 3),
        "xy_median_m": [round(float(v), 2) for v in np.median(xy, 0)],
        "xy_bbox_m": [round(float(v), 1) for v in (*xy.min(0), *xy.max(0))],
        "visible_px_game_cam_1x": vis[k],
    }
json.dump(rep, open(os.path.join(OUTD, "audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot = sum(vis.values())
for k in sorted(keys, key=lambda k: -vis[k]):
    v = rep["materials"][k]
    print(f"{k:12s} {str(v['shader'])[:42]:42s} img={'Y' if v['image'] else '-'} tris={v['tris']:6d} vis={vis[k]:8d} ({100*vis[k]/max(tot,1):5.2f}%) z={v['z_m']} up={v['normal_up_frac']} uv0={v['uv_zero_area_faces']} xy={v['xy_median_m']}")
