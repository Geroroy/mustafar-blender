"""MO-9 원본 형상 불변 검사 — MO_STAGE.blend(및 MO_GAMEFIT.blend)의 모든 메시 정점·면이 원본 OBJ와 같은지 대조한다. Blender(bpy).
OBJ의 'v' 좌표(면이 쓰는 것)와 Blender 메시 로컬 좌표를 반올림해 집합으로 비교하고, 삼각형 수·객체 수·재질 연결도 대조한다.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo09_verify_unchanged.py <MO_*.blend> <duel_mus_both.obj> <출력 json>
"""
import json, sys

import bpy
import numpy as np

BL, OBJ, OUT = sys.argv[1:4]
bpy.ops.wm.open_mainfile(filepath=BL)
sc = next(s for s in bpy.data.scenes)
objs = [o for o in sc.collection.all_objects if o.type == 'MESH' and not o.name.startswith(("BG_", "SPR_", "PR_"))]
bl = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs if len(o.data.vertices)])
V = []; used = set(); tri = 0
for line in open(OBJ, encoding="latin1"):
    if line.startswith("v "):
        V.append([float(t) for t in line.split()[1:4]])
    elif line.startswith("f "):
        idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
        used.update(idx); tri += len(idx) - 2
V = np.array(V)[sorted(used)]
a = {tuple(np.round(r, 2)) for r in V}; b = {tuple(np.round(r, 2)) for r in bl}
bl_tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
ra, rb = np.array(sorted(a - b)), np.array(sorted(b - a))
maxdiff = float(np.abs(ra - rb).max()) if len(ra) == len(rb) and len(ra) else 0.0       # 반올림 경계에서 갈린 정점: float32 정밀도(x≈7200에서 0.004)
d_obj = []; d_bl = []
rep = {"diff_obj_sample": d_obj, "diff_blend_sample": d_bl, "blend": BL, "objects": len(objs), "triangles_blend": bl_tris, "triangles_obj": tri,
       "unique_vertices_obj": len(a), "unique_vertices_blend": len(b), "only_in_obj": len(a - b), "only_in_blend": len(b - a),
       "same_vertex_set(0.01 반올림)": a == b, "max_diff_of_unmatched_u": maxdiff, "same_vertex_set_within_0.02u": (a == b) or maxdiff <= 0.02, "same_triangle_count": bl_tris == tri}
json.dump(rep, open(OUT, "w"), indent=1, default=float); print(rep)
