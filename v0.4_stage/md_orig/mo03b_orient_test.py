"""MO-3b 방향 시험 — 회전 네 가지(0/90/180/270°)를 같은 게임 카메라로 렌더해 비교한다(거울상 없음). 낮은 해상도 검사용.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo03b_orient_test.py <MO_GAMEFIT_rotN.blend> <출력 png>
"""
import json, math, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402
import mo_render as R  # noqa: E402

SRC, OUT = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data; sc = D.scenes["MO_GAMEFIT"]
CFG = {"game": {"OX": 96.0, "OY": 95.5}, "frame_boxes": [[[-40, -26, -6], [40, 26, 12]]], "frame_margin_px": [60, 60]}
if os.environ.get("MO_FRAME"):      # (another map: its own screen range, JSON [[x0,y0,z0],[x1,y1,z1]] m — duel_mustafar)
    CFG["frame_boxes"] = [json.loads(os.environ["MO_FRAME"])]
R.ensure_light(sc, sun_rot=(math.radians(50), 0, math.radians(60)), sun=2.5, amb=0.9)
cd = D.cameras.new("Game_Output_Iso"); cd.clip_start = 1; cd.clip_end = 2000
cam = D.objects.new("Game_Output_Iso", cd); sc.collection.objects.link(cam); sc.camera = cam
W, H, ox, oy = SC.setup(sc, cam, CFG, density=float(os.environ.get("MO_DENSITY", "0.9")))   # (a big map: MO_DENSITY=0.3)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True, scene=sc.name)
print("OK", W, H)
