"""MO-11 생성 대체 질감 연결 — MO_STAGE.blend(원본 형상·원본 연결 질감)를 열어, 질감이 없던 재질 30개에만 생성 대체 질감을 붙여 새 파일로 저장한다. Blender(bpy).
- 연결표: mo_gentex_map.json (obj_material → 파일). 원본 MTL·원본 .blend는 고치지 않는다(새 파일로 저장).
- 기존 연결 재질과 같은 방식: 이미지 → Base Color, 거칠기 1.0, 반사 0, 금속 0. UV·형상·타일 배율은 그대로.
- 조명 5종(kind emissive): 이미지 밝기(흑백)를 MapRange(bw_lo→bw_hi)로 0~1 마스크로 만들어 밝은 광원부만 발광. 틀은 일반 재질.
- 유리(kind glass): PNG 알파를 그대로 Alpha에 연결(추가 곱셈 없음). Cycles는 양면.
- 생성 질감은 AI로 만든 대체물이며 원본 Jedi Academy 질감이 아니다. 재질마다 사용자 속성 gentex_source로 기록한다.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo11_apply_gentex.py <MO_STAGE.blend> <질감 폴더> <출력 .blend> [--report <json>]
"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, TEXDIR, OUT = (os.path.abspath(a) for a in sys.argv[1:4])
REPORT = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else os.path.splitext(OUT)[0] + "_report.json"
MAP = json.load(open(os.path.join(HERE, "mo_gentex_map.json"), encoding="utf-8"))
E = MAP["emission"]

bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
rep = []
for row in MAP["materials"]:
    ma = D.materials.get(row["obj_material"])
    path = os.path.join(TEXDIR, row["file"])
    if ma is None or not os.path.exists(path):
        rep.append({**row, "applied": False, "why": "재질 없음" if ma is None else "파일 없음"}); continue
    before = [n.type for n in ma.node_tree.nodes]
    assert not any(n.type == 'TEX_IMAGE' for n in ma.node_tree.nodes), ("이미 질감이 연결된 재질", ma.name)   # 원본 연결 재질은 건드리지 않는다
    nt = ma.node_tree; L = nt.links.new
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    img = D.images.load(path, check_existing=True)
    if row["kind"] == "glass":
        img.alpha_mode = 'STRAIGHT'
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img; tx.interpolation = 'Linear'; tx.extension = 'REPEAT'; tx.location = (-420, 200)
    L(tx.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 1.0; b.inputs["Specular IOR Level"].default_value = 0.0; b.inputs["Metallic"].default_value = 0.0
    if row["kind"] == "emissive":
        bw = nt.nodes.new("ShaderNodeRGBToBW"); L(tx.outputs["Color"], bw.inputs["Color"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.clamp = True
        mr.inputs[1].default_value, mr.inputs[2].default_value, mr.inputs[3].default_value, mr.inputs[4].default_value = E["bw_lo"], E["bw_hi"], 0.0, E["strength"]
        L(bw.outputs[0], mr.inputs[0]); L(tx.outputs["Color"], b.inputs["Emission Color"]); L(mr.outputs[0], b.inputs["Emission Strength"])
    if row["kind"] == "glass":
        L(tx.outputs["Alpha"], b.inputs["Alpha"])
    ma["gentex_source"] = f"AI 생성 대체 질감 {row['file']} (MUSTAFAR_TEXTURES_GEN.zip, 원본 아님)"
    rep.append({**row, "applied": True, "image_size": list(img.size), "nodes_before": before})
# 원본 연결 재질 수(바뀌지 않아야 함)
linked = sum(1 for m in D.materials if m.use_nodes and any(n.type == 'TEX_IMAGE' and n.image and "md_orig_gentex" not in n.image.filepath and "textures__" in n.image.name for n in m.node_tree.nodes) and "gentex_source" not in m)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump({"source_blend": SRC, "texture_dir": TEXDIR, "out_blend": OUT, "applied": sum(r["applied"] for r in rep), "total": len(rep),
           "original_linked_materials_untouched": linked, "materials": rep}, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("APPLIED", sum(r["applied"] for r in rep), "/", len(rep), "original linked untouched", linked, "->", OUT)
