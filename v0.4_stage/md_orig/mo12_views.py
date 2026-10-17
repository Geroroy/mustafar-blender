"""MO-12 전후 비교 렌더 — 같은 .blend 구조(MO_STAGE / MO_STAGE_GENTEX)에서 같은 카메라 표로 찍는다. Blender(bpy). 형상·재질은 바꾸지 않는다(읽기만).
  game_full : 게임 카메라(직교 30°/45°), 실행 패키지(게임 커밋 1633ff9) 배경과 같은 화면 범위
  game_*    : 게임 카메라, 같은 배율로 일부 범위만(암벽·시설·받침 기둥 등)
  persp_*   : 근사 원근 근접(재질 확인용)
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo12_views.py <.blend> <출력 접두어> [--views a,b] [--density 1] [--samples 32]
"""
import json, math, os, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

BLEND, PRE = sys.argv[1], sys.argv[2]
ONLY = set(sys.argv[sys.argv.index("--views") + 1].split(",")) if "--views" in sys.argv else set()
DEN = float(sys.argv[sys.argv.index("--density") + 1]) if "--density" in sys.argv else 1.0
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
CFG = json.load(open(os.path.join(HERE, "mo_stage_config.json"), encoding="utf-8"))
FULL = (-910, 1239, -910 + 2260, 1239 + 1440)          # 게임 커밋 1633ff9 stage.json backdrop (x, y, w, h) — 실행 패키지와 같은 범위


def rect(boxes, margin=(30, 30)):
    xs, ys = [], []
    for (x0, y0, z0), (x1, y1, z1) in boxes:
        for X in (x0, x1):
            for Y in (y0, y1):
                for Z in (z0, z1):
                    sx, sy = SC.screen(CFG, X, Y, Z); xs.append(sx); ys.append(sy)
    return (math.floor(min(xs) - margin[0]), math.floor(min(ys) - margin[1]), math.ceil(max(xs) + margin[0]), math.ceil(max(ys) + margin[1]))


VIEWS = {
    "game_full": dict(kind="game", rect=FULL),
    "game_facility_roof": dict(kind="game", rect=rect([((-15.0, 3.0, -2.0), (20.0, 27.0, 12.0))])),
    "game_pad_edge_lights": dict(kind="game", rect=rect([((-15.0, -20.0, -2.0), (12.0, 6.0, 3.0))])),
    "game_pillars": dict(kind="game", rect=rect([((-10.0, 4.0, -21.0), (12.0, 23.0, -1.0))])),
    "game_rocks": dict(kind="game", rect=rect([((-37.0, -45.0, -29.0), (-14.0, 10.0, -2.0))])),
    "persp_facade_roof": dict(kind="persp", loc=(6.0, -14.0, 1.7), tgt=(4.0, 10.0, 6.0), lens=24, res=(1600, 900)),
    "persp_eave_lights": dict(kind="persp", loc=(3.0, 2.0, 1.7), tgt=(5.0, 14.0, 4.5), lens=24, res=(1600, 900)),
    "persp_pillars": dict(kind="persp", loc=(24.0, -6.0, -10.0), tgt=(2.0, 12.0, -15.0), lens=24, res=(1600, 900)),
    "persp_rocks": dict(kind="persp", loc=(8.0, -30.0, 3.0), tgt=(-28.0, -10.0, -14.0), lens=24, res=(1600, 900)),
    "persp_glass": dict(kind="persp", loc=(2.0, 49.0, 0.5), tgt=(2.0, 60.0, 0.0), lens=24, res=(1600, 900)),
}
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.data.scenes["MO_STAGE"]; bpy.context.window.scene = sc if bpy.context.window else None
sc.cycles.samples = SAMPLES; sc.render.image_settings.file_format = 'PNG'
game = bpy.data.objects["Game_Output_Iso"]
cd = bpy.data.cameras.new("VIEW12"); pc = bpy.data.objects.new("VIEW12", cd); sc.collection.objects.link(pc)
cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 2000
for name, v in VIEWS.items():
    if ONLY and name not in ONLY:
        continue
    if v["kind"] == "game":
        sc.camera = game; SC.setup(sc, game, CFG, density=DEN, sub=v["rect"])
    else:
        sc.camera = pc; pc.location = Vector(v["loc"]); pc.rotation_euler = (Vector(v["tgt"]) - Vector(v["loc"])).to_track_quat('-Z', 'Y').to_euler()
        cd.lens = v["lens"]; sc.render.resolution_x, sc.render.resolution_y = (int(v["res"][0] * min(DEN, 1)), int(v["res"][1] * min(DEN, 1))); sc.render.resolution_percentage = 100
    sc.render.filepath = f"{PRE}_{name}.png"; os.makedirs(os.path.dirname(os.path.abspath(sc.render.filepath)), exist_ok=True)
    bpy.ops.render.render(write_still=True); print("VIEW", name, sc.render.filepath, flush=True)
