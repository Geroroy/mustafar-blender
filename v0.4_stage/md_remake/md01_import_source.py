"""1단계 — Movie Duels 원본 모델 불러오기(기존 제작 맵 형상 없음). Blender(bpy).
02_models.zip의 duel_mustafar.obj·duel_mus_both.obj를 각각 별도 장면·컬렉션으로 불러온다.
  - 원본 게임 좌표(Quake 단위, Z 위)를 그대로 둔다: forward_axis='Y', up_axis='Z' → OBJ x,y,z = Blender X,Y,Z.
  - MTL·textures 연결을 그대로 쓴다(OBJ 옆 models/textures/). 연결 여부를 재질마다 검사해 기록한다.
  - 기존 A3e·v0.3 형상은 열지도 붙이지도 않는다(빈 파일에서 시작).
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/md_remake/md01_import_source.py <models 폴더> <출력 .blend> <보고 json>
"""
import json, os, sys

import bpy

MODELS, OUT, REPORT = (os.path.abspath(p) for p in sys.argv[-3:])      # 절대 경로: 이미지 경로가 .blend 위치 기준으로 바르게 바뀌게
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data
rep = {"models_dir": MODELS, "units": "원본 게임 좌표(1 u), Z 위. 미터 변환 안 함", "maps": {}}
first = True
for m in ("duel_mustafar", "duel_mus_both"):
    obj_path = os.path.join(MODELS, m + ".obj")
    if not os.path.isfile(obj_path):
        raise SystemExit(f"없음: {obj_path}")
    sc = bpy.context.scene          # 가져온 뒤 두 번째 맵은 자기 장면으로 옮김(아래)
    col = D.collections.new(f"MD_{m}"); sc.collection.children.link(col)
    lc = bpy.context.view_layer.layer_collection.children[col.name]; bpy.context.view_layer.active_layer_collection = lc
    before = set(D.objects)
    r = bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Y', up_axis='Z', use_split_objects=True, use_split_groups=True)
    new = [o for o in D.objects if o not in before]
    if r != {'FINISHED'} or not new:
        raise SystemExit(f"가져오기 실패: {obj_path} {r}")
    # MTL map_Kd 원문 ↔ Blender 이미지 연결 검사
    mtl = {}; cur = None
    for line in open(os.path.join(MODELS, m + ".mtl"), encoding="latin1"):
        s = line.split()
        if not s:
            continue
        if s[0] == "newmtl":
            cur = s[1]; mtl[cur] = None
        elif s[0] == "map_Kd" and cur:
            mtl[cur] = s[-1]
    linked, unlinked_img, nomap = [], [], []
    tris = 0
    for o in new:
        o["md_source_file"] = m + ".obj"
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        for ma in o.data.materials:
            key = ma.name.split(".")[0]
            imgs = [n.image for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image] if ma.use_nodes else []
            ok = [i for i in imgs if i.size[0] > 0]
            if mtl.get(key) is None:
                nomap.append(key)
            elif ok:
                linked.append(key)
            else:
                unlinked_img.append((key, mtl[key]))
    xs = [v for o in new for v in (o.bound_box[0][0], o.bound_box[6][0])]
    ys = [v for o in new for v in (o.bound_box[0][1], o.bound_box[6][1])]
    zs = [v for o in new for v in (o.bound_box[0][2], o.bound_box[6][2])]
    if first:
        sc.name = f"SRC_{m}"; first = False
    else:                            # 별도 장면으로 옮김(두 맵을 한 장면에 두지 않음)
        sc2 = D.scenes.new(f"SRC_{m}"); sc2.collection.children.link(col); sc.collection.children.unlink(col); sc = sc2
    rep["maps"][m] = {"obj": obj_path, "scene": sc.name, "collection": col.name, "objects": len(new), "triangles": tris,
                      "materials_in_mtl": len(mtl), "texture_linked": len(sorted(set(linked))), "mtl_without_map_Kd(grey)": sorted(set(nomap)),
                      "texture_missing_on_disk": sorted(set(unlinked_img)), "bounds_u": [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]]}
    print(m, json.dumps(rep["maps"][m], ensure_ascii=False)[:400], flush=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SAVED", OUT)
