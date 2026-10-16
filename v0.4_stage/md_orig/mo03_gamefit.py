"""MO-3 게임 맞춤 — 원본(MO_ORIGINAL_IMPORT.blend)에 '전체 일괄 변환' 하나만 건다. Blender(bpy).
허용된 변경은 이것뿐이다: 빈 객체 MO_FIT 하나에 회전·이동·축척을 걸고, 원본 객체 89개를 그 아래에 붙인다.
  - 메시 정점·면·재질·UV는 한 점도 고치지 않는다(MO_FIT 변환만 다름) → 형상·소품의 상대 위치 불변.
  - 삭제·추가·교체·거울상 없음. 원본 객체 수와 삼각형 수를 가져오기 보고와 대조해 검사한다.
  - 변환: p' = S · Rz(rot) · (p − c),  c = 시설 쪽 판 가장자리 가운데(원본 u), S = 0.028125 m/u (JKA 플레이어 64 u = 1.8 m).
  - rot_z_deg 는 하나로 고정해 쓴다(방향 시험은 mo03b_orient_test.py).
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo03_gamefit.py <MO_ORIGINAL_IMPORT.blend> <출력 .blend> <보고 json> [--rot 180]
"""
import json, math, os, sys

import bpy
from mathutils import Matrix, Vector

SRC, OUT, REPORT = (os.path.abspath(p) for p in sys.argv[1:4])
ROT = float(sys.argv[sys.argv.index("--rot") + 1]) if "--rot" in sys.argv else 180.0
S = 0.028125
C = (3888.0, -952.0, 168.0)      # 판 윗면(z 168) 위, 시설 쪽 판 가장자리(x 3888) 가운데(y −952). 원본 마크 PAD 에서 읽음

bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
sc = D.scenes["SRC_duel_mus_both"]
objs = [o for o in sc.collection.all_objects if o.type == 'MESH']
before = {o.name: (len(o.data.vertices), len(o.data.polygons), tuple(round(c, 4) for c in o.data.vertices[0].co)) for o in objs}
M = Matrix.Rotation(math.radians(ROT), 4, 'Z') @ Matrix.Scale(S, 4) @ Matrix.Translation(-Vector(C))
# Matrix.Scale(S,4)는 균일 축척 → 회전과 교환 가능. 회전 → 축척 → 이동 순서와 같은 결과
fit = D.objects.new("MO_FIT", None); sc.collection.objects.link(fit)
fit.matrix_world = M
fit["note"] = f"전체 일괄 변환 p' = S·Rz({ROT})·(p − c), S={S} m/u, c={C} u. 원본 메시는 고치지 않음"
for o in objs:
    o.parent = fit; o.matrix_parent_inverse = Matrix.Identity(4)
bpy.context.view_layer.update()
after = {o.name: (len(o.data.vertices), len(o.data.polygons), tuple(round(c, 4) for c in o.data.vertices[0].co)) for o in objs}
assert before == after, "메시가 바뀌었음"
det = M.to_3x3().determinant()
assert det > 0, "거울상 변환"
sc["mo_fit"] = fit["note"]
sc.name = "MO_GAMEFIT"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
rep = {"rot_z_deg": ROT, "scale_m_per_u": S, "pivot_u": C, "objects": len(objs), "triangles": sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons),
       "mesh_data_unchanged": True, "determinant_positive(no_mirror)": det > 0}
json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(rep)
