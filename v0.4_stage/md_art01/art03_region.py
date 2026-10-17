"""ART01-3 대표 구역 렌더 — 게임 카메라(같은 투영·배율)로 지정 구역만 잘라 렌더한다(형상 불변, 저장 안 함). 재질·조명 기준 잡기와 전후 비교용.
구역: art_regions.json (월드 중심 X,Y와 화면 크기 px, 1배 기준). 조각 분리 없이 전체 형상을 한 번에 그린다(게임 합성과 같은 그림).
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art03_region.py <장면 .blend> <출력 폴더> [--density 2] [--samples 32] [--only start,ship_front]
"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
BLEND, OUTD = os.path.abspath(args[0]), os.path.abspath(args[1])
opt = lambda k, d: type(d)(args[args.index(k) + 1]) if k in args else d
DEN, SAMP, ONLY = opt("--density", 2), opt("--samples", 32), opt("--only", "")
REG = json.load(open(os.path.join(HERE, "art_regions.json"), encoding="utf-8"))["regions"]
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.data.scenes["MO_STAGE"]; CFG = json.loads(sc["stage_config"]); cam = bpy.data.objects["Game_Output_Iso"]; sc.camera = cam
sc.cycles.samples = SAMP; sc.cycles.use_denoising = True; sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
os.makedirs(OUTD, exist_ok=True)
for name, r in REG.items():
    if ONLY and name not in ONLY.split(","):
        continue
    sx, sy = SC.screen(CFG, r["world"][0], r["world"][1], r.get("z", 0.0)); w, h = r["size_px"]
    box = (round(sx - w / 2), round(sy - h / 2), round(sx + w / 2), round(sy + h / 2))
    SC.setup(sc, cam, CFG, density=DEN, sub=box)
    sc.render.filepath = os.path.join(OUTD, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REGION", name, box, flush=True)
