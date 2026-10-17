"""MO-1 원본 가져오기 — Movie Duels duel_mus_both 추출 모델(수정 전)을 그대로 불러온다. Blender(bpy).
이 단계는 형상·재질을 고치지 않는다(회전·이동·축척·삭제·교체 없음). 리메이크 처리와 완전히 분리된 단계다.
  - 입력: 추출 모델 duel_mus_both.obj/.mtl + textures/ (원본 BSP에서 추출한 것, SHA256은 보고에 기록)
  - OBJ 좌표(Quake 단위, Z 위)를 그대로 둔다: forward_axis='Y', up_axis='Z'
  - MTL map_Kd ↔ 이미지 연결을 재질마다 검사하고, 누락(회색)·디스크에 없는 질감을 목록으로 기록한다(임의 대체 없음)
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/md_orig/mo01_import_original.py <models 폴더> <출력 .blend> <보고 json>
"""
import hashlib, json, os, sys

import bpy

MODELS, OUT, REPORT = (os.path.abspath(p) for p in sys.argv[-3:])
M = os.environ.get("MO_MAP", "duel_mus_both")   # (the other Mustafar map, duel_mustafar: MO_MAP=duel_mustafar)
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


obj_path = os.path.join(MODELS, M + ".obj")
sc = bpy.context.scene; sc.name = "SRC_" + M
col = D.collections.new("MD_" + M); sc.collection.children.link(col)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[col.name]
before = set(D.objects)
r = bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Y', up_axis='Z', use_split_objects=True, use_split_groups=True)
new = [o for o in D.objects if o not in before]
if r != {'FINISHED'} or not new:
    raise SystemExit(f"가져오기 실패: {obj_path} {r}")

mtl = {}; cur = None
for line in open(os.path.join(MODELS, M + ".mtl"), encoding="latin1"):
    s = line.split()
    if s and s[0] == "newmtl":
        cur = s[1]; mtl[cur] = None
    elif s and s[0] == "map_Kd" and cur:
        mtl[cur] = s[-1]
tex_dir = os.path.join(MODELS, "textures")
per_mat = {}
tris = 0
for o in new:
    n = sum(len(p.vertices) - 2 for p in o.data.polygons); tris += n
    for ma in o.data.materials:
        key = ma.name.split(".")[0]
        imgs = [nd.image for nd in ma.node_tree.nodes if nd.type == 'TEX_IMAGE' and nd.image] if ma.use_nodes else []
        d = per_mat.setdefault(key, {"map_Kd": mtl.get(key), "linked": False, "tris": 0})
        d["tris"] += n
        if any(i.size[0] > 0 for i in imgs):
            d["linked"] = True
missing_no_map = sorted(k for k, v in per_mat.items() if v["map_Kd"] is None)
missing_file = sorted((k, v["map_Kd"]) for k, v in per_mat.items() if v["map_Kd"] and not v["linked"])
xs = [v for o in new for v in (o.bound_box[0][0], o.bound_box[6][0])]
ys = [v for o in new for v in (o.bound_box[0][1], o.bound_box[6][1])]
zs = [v for o in new for v in (o.bound_box[0][2], o.bound_box[6][2])]
rep = {
    "source_obj": M + ".obj", "units": "원본 게임 좌표(u), Z 위. 변환 없음",
    "sha256": {f: sha(os.path.join(MODELS, f)) for f in (M + ".obj", M + ".mtl")},
    "objects": len(new), "triangles": tris, "materials_in_mtl": len(mtl), "materials_used": len(per_mat),
    "textures_dir_files": len(os.listdir(tex_dir)),
    "missing_no_map_Kd(grey)": [{"material": k, "tris": per_mat[k]["tris"]} for k in missing_no_map],
    "missing_texture_file": [{"material": k, "map_Kd": f, "tris": per_mat[k]["tris"]} for k, f in missing_file],
    "bounds_u": [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]],
    "materials": per_mat,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "materials"}, ensure_ascii=False, indent=1)[:3000])
