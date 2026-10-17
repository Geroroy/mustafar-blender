"""ART01-7 재질 누락·흰 임시 면 검사. Blender(bpy) 파이썬(장면은 읽기만).
  1) 장면: 모든 메시 면의 재질이 ART01 분류(art01_class)를 갖고, 노드 출력이 연결돼 있는지. 원본 질감 연결이 없던 30개도 포함.
  2) 화면: 게임 카메라 1배 재질 번호 화면(art01_audit.py의 id_game_cam.npy)과 최종 합성(배경+조각) 화면을 겹쳐,
     '밝고 무채색'(흰 임시 면처럼 보이는) 픽셀이 어느 재질에 있는지 센다. 조명 기구(lamp_*) 재질만 허용.
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art07_check_materials.py <ART01_STAGE.blend> <audit 폴더> <합성 png(2배)> <출력 json>
"""
import json, os, sys

import bpy
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BL, AUD, COMP, OUT = sys.argv[1:5]
bpy.ops.wm.open_mainfile(filepath=BL)
sc = bpy.data.scenes["MO_STAGE"]
faces = {}; bad = []
for o in sc.collection.all_objects:
    if o.type != 'MESH':
        continue
    for p in o.data.polygons:
        ma = o.data.materials[p.material_index] if o.data.materials else None
        k = ma.name if ma else "(none)"
        faces[k] = faces.get(k, 0) + 1
for k in faces:
    ma = bpy.data.materials.get(k)
    out = [n for n in ma.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'] if ma and ma.node_tree else []
    ok = ma is not None and "art01_class" in ma and out and out[0].inputs["Surface"].is_linked
    if not ok:
        bad.append(k)
cls = {k: bpy.data.materials[k]["art01_class"] for k in faces if k not in bad}

rep = json.load(open(os.path.join(AUD, "audit.json"), encoding="utf-8"))
ids = np.load(os.path.join(AUD, "id_game_cam.npy")).astype(int)
inv = {v: k for k, v in rep["id_index"].items()}
im = Image.open(COMP).convert("RGB")
im = im.resize((im.width // 2, im.height // 2), Image.BOX)
a = np.asarray(im).astype(np.int32)
assert a.shape[:2] == ids.shape, (a.shape, ids.shape)
mx, mn = a.max(-1), a.min(-1)
whiteish = (mn >= 200) & (mx - mn <= 30)
per = {}
for i in np.unique(ids[whiteish]):
    k = inv.get(int(i), "(배경)"); per[k] = int((whiteish & (ids == i)).sum())
allowed = {k: v for k, v in per.items() if cls.get(k, "").startswith("lamp")}
other = {k: v for k, v in per.items() if k not in allowed}
vis = {k: v["visible_px_game_cam_1x"] for k, v in rep["materials"].items() if v["visible_px_game_cam_1x"] > 0}
res = {
    "faces_total": sum(faces.values()), "materials_used": len(faces), "materials_without_art01_or_unlinked": bad,
    "visible_materials_1x": len(vis), "visible_materials_without_class": sorted(k for k in vis if k not in cls),
    "whiteish_px_1x(min>=200, 무채색)": int(whiteish.sum()), "whiteish_in_lamp_materials": allowed, "whiteish_in_other_materials": other,
    "classes": cls,
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "classes"}, ensure_ascii=False, indent=1))
