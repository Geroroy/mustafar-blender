"""ART01-10 MO_STAGE ↔ ART01_STAGE 대조 — 재질 노드·조명 말고는 같은지 확인한다. Blender(bpy).
객체마다 월드 변환(MO_FIT 포함)·정점/면 수·재질 슬롯 이름·UV 합(검사합)·면 재질 번호, 게임 카메라 위치·회전·투영을 비교한다.
(원본 OBJ와의 정점 대조는 md_orig/mo09_verify_unchanged.py를 ART01_STAGE.blend에 그대로 돌린다.)
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art10_same_as_mo.py <MO_STAGE.blend> <ART01_STAGE.blend> <출력 json>
"""
import json, sys

import bpy

A, B, OUT = sys.argv[-3:]


def snap(p):
    bpy.ops.wm.open_mainfile(filepath=p); sc = bpy.data.scenes["MO_STAGE"]; r = {}
    for o in sc.collection.all_objects:
        if o.type == 'MESH':
            me = o.data; uv = me.uv_layers.active
            r[o.name] = (tuple(round(v, 6) for row in o.matrix_world for v in row), len(me.vertices), len(me.polygons),
                         tuple(m.name for m in me.materials), round(sum(d.uv[0] + 3 * d.uv[1] for d in uv.data), 3) if uv else None,
                         tuple(p.material_index for p in me.polygons))
    c = bpy.data.objects["Game_Output_Iso"]
    r["_cam"] = (tuple(round(v, 6) for v in c.matrix_world.to_translation()), tuple(round(v, 6) for v in c.rotation_euler), c.data.type)
    return r


a = snap(A); b = snap(B)
diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
rep = {"mo_stage": A, "art01_stage": B, "objects": len(a) - 1, "identical(transform·mesh counts·slots·UV·face material·camera)": not diff, "diff": diff}
json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(rep)
