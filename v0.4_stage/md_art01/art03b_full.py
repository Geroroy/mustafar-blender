"""ART01-3b 전체 화면 미리보기 — 게임 카메라 배경 범위 전체를 낮은 밀도로 렌더(형상 불변, 저장 안 함).
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art03b_full.py <장면 .blend> <출력 png> [--density 0.5] [--samples 12]
"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

args = sys.argv[1:]
BLEND, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
opt = lambda k, d: type(d)(args[args.index(k) + 1]) if k in args else d
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.data.scenes["MO_STAGE"]; CFG = json.loads(sc["stage_config"]); cam = bpy.data.objects["Game_Output_Iso"]; sc.camera = cam
sc.cycles.samples = opt("--samples", 12); sc.cycles.use_denoising = True; sc.render.film_transparent = False
SC.setup(sc, cam, CFG, density=opt("--density", 0.5))
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("FULL", OUT)
