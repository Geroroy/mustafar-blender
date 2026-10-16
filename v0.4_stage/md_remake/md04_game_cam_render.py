"""C — 같은 게임 카메라 비교 렌더. Blender(bpy).
스테이지 .blend(build_stage.py 결과)를 열고 Game_Output_Iso 카메라를 stage_cam.setup으로 맞춘다.
화면 범위(sub)를 기준 설정(A3e stage_config.json)의 게임 화면 좌표로 고정하므로, 두 배치가 같은 게임 좌표(OX/OY)·같은 투영·같은 28.284 px/m에서 나란히 비교된다.
실행: .venv-bpy/bin/python v0.4_stage/md_remake/md04_game_cam_render.py <stage .blend> <출력 png> <sx0,sy0,sx1,sy1 | frame> [--samples 32] [--density 1]
"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

BLEND, OUT, RECT = sys.argv[1], sys.argv[2], sys.argv[3]
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
DEN = float(sys.argv[sys.argv.index("--density") + 1]) if "--density" in sys.argv else 1.0
REF = json.load(open(os.path.join(os.path.dirname(HERE), "stage_config.json"), encoding="utf-8"))     # A3e 기준(게임 좌표 변환 OX/OY 같음)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene; cam = bpy.data.objects["Game_Output_Iso"]; scene.camera = cam
own = json.loads(scene["stage_config"]) if "stage_config" in scene else REF
assert own["game"] == REF["game"], ("게임 좌표 변환이 다름", own["game"], REF["game"])
sub = SC.frame(REF) if RECT == "frame" else tuple(float(v) for v in RECT.split(","))
W, H, sx0, sy0 = SC.setup(scene, cam, REF, density=DEN, sub=sub)
scene.cycles.samples = SAMPLES
scene.render.image_settings.file_format = 'PNG'; scene.render.filepath = OUT
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("RENDERED", OUT, W, H, sx0, sy0, "ortho", round(cam.data.ortho_scale, 3), "rot", [round(a, 4) for a in cam.rotation_euler])
