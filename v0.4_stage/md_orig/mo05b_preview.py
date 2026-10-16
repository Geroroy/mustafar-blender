"""MO-5b 게임 카메라 미리보기(낮은 해상도). 실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo05b_preview.py <MO_STAGE.blend> <출력 png> [density 0.5]"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
sc = bpy.data.scenes["MO_STAGE"]; CFG = json.loads(sc["stage_config"]); cam = bpy.data.objects["Game_Output_Iso"]
den = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
W, H, ox, oy = SC.setup(sc, cam, CFG, density=den)
sc.cycles.samples = 12; sc.render.filepath = os.path.abspath(sys.argv[2])
bpy.ops.render.render(write_still=True, scene=sc.name)
print("OK", W, H, ox, oy)
