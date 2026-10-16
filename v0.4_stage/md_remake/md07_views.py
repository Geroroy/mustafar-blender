"""POC01 ↔ POC02 비교 렌더(같은 장면 .blend에서 같은 카메라 표로 찍는다). Blender(bpy).
  - 게임 카메라 화면(ortho): 같은 투영·같은 28.284 px/m·같은 화면 범위(게임 화면 좌표 사각형을 월드 상자 투영으로 고정 → 두 .blend에 같은 값)
  - 근사 원근 화면: 영화 프레임과 비슷한 시점(맞춤이 아니라 근사). 1.8 m 인체 대용 형상(렌더 전용 REF_Human_1p8m, 게임·스테이지 데이터에는 없음)을 같은 자리에 둔다
실행: .venv-bpy/bin/python v0.4_stage/md_remake/md07_views.py <stage .blend> <출력 접두어> --cfg <POC02 stage_config> [--views a,b] [--samples 40]
"""
import json, math, os, sys

import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
BLEND, PRE = args[0], args[1]
CFG = json.load(open(args[args.index("--cfg") + 1], encoding="utf-8"))
ONLY = set(args[args.index("--views") + 1].split(",")) if "--views" in args else set()
SAMPLES = int(args[args.index("--samples") + 1]) if "--samples" in args else 40


def rect_of(boxes, margin):
    xs, ys = [], []
    for (x0, y0, z0), (x1, y1, z1) in boxes:
        for X in (x0, x1):
            for Y in (y0, y1):
                for Z in (z0, z1):
                    sx, sy = SC.screen(CFG, X, Y, Z); xs.append(sx); ys.append(sy)
    return (math.floor(min(xs) - margin[0]), math.floor(min(ys) - margin[1]), math.ceil(max(xs) + margin[0]), math.ceil(max(ys) + margin[1]))


# 이름: dict(kind='game'|'persp', ...). human = 인체 대용 형상 자리 목록(x, y, 바라보는 각도)
FULL = rect_of(CFG["frame_boxes"], (60, 40))                     # 판 윗면·출입구·지붕(마스트 포함) 중심. 받침 다리 끝(−17 m)은 담지 않음(하부 크롭: 플레이 출력과 같은 범위)
VIEWS = {
    "full_game": dict(kind="game", rect=FULL, human=[(2.0, -6.0, 0)]),
    "entrance_game": dict(kind="game", rect=rect_of([((12.0, -12.0, 0.0), (21.0, -5.0, 6.6))], (50, 40)), human=[(15.2, -10.0, 90)]),
    "crates_game": dict(kind="game", rect=rect_of([((10.0, -15.5, 0.0), (15.5, -0.5, 1.2))], (50, 40)), human=[(9.0, -8.2, 90)]),
    "floor_game": dict(kind="game", rect=rect_of([((-8.0, -9.0, 0.0), (12.0, 9.0, 0.2))], (30, 30)), human=[(2.5, -2.0, 45)]),
    "roof_game": dict(kind="game", rect=rect_of([((16.0, -21.0, 6.5), (39.0, 9.0, 15.0))], (30, 30)), human=[]),
    "entrance_film78862": dict(kind="persp", loc=(5.5, -10.4, 1.55), tgt=(19.0, -8.0, 2.35), lens=22, res=(1434, 600), human=[(15.4, -11.0, 90)]),
    "entrance_film11748": dict(kind="persp", loc=(9.5, -6.4, 1.5), tgt=(19.5, -8.4, 2.7), lens=24, res=(1600, 670), human=[(16.0, -6.0, 90)]),
    "crate_film78855": dict(kind="persp", loc=(5.0, 0.8, 1.45), tgt=(12.6, -3.6, 0.5), lens=24, res=(900, 1000), human=[(10.2, -6.4, 90)]),
    "crate_close": dict(kind="persp", loc=(6.5, -17.6, 1.7), tgt=(12.4, -12.4, 0.5), lens=26, res=(1200, 900), human=[(9.0, -9.6, 0)]),
    "floor_human": dict(kind="persp", loc=(-9.0, -4.5, 1.65), tgt=(8.0, -7.2, 0.0), lens=24, res=(1434, 720), human=[(1.5, -6.5, 90)]),
    "roof_persp": dict(kind="persp", loc=(4.0, -17.0, 2.0), tgt=(26.0, -6.0, 8.0), lens=24, res=(1434, 800), human=[]),
    "roof_far": dict(kind="persp", loc=(-7.0, -28.0, 3.0), tgt=(28.0, -4.0, 8.0), lens=28, res=(1434, 700), human=[]),
}


def human(name, x, y, rot_deg):
    """1.8 m 인체 대용(바닥 z 0): 다리·몸통·팔·머리. 렌더 전용."""
    bm = bmesh.new()
    def box(lo, hi):
        vs = [bm.verts.new((x_, y_, z_)) for z_ in (lo[2], hi[2]) for y_ in (lo[1], hi[1]) for x_ in (lo[0], hi[0])]
        for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)):
            bm.faces.new([vs[i] for i in f])
    box((-0.17, -0.2, 0.0), (-0.01, -0.02, 0.86)); box((0.01, -0.2, 0.0), (0.17, -0.02, 0.86))     # 다리(발 길이 쪽 y)
    box((-0.2, -0.17, 0.86), (0.2, 0.13, 1.45))                                                          # 몸통
    box((-0.31, -0.1, 1.12), (-0.2, 0.08, 1.45)); box((0.2, -0.1, 1.12), (0.31, 0.08, 1.45))             # 어깨·팔 위
    box((-0.31, -0.1, 0.78), (-0.22, 0.08, 1.12)); box((0.22, -0.1, 0.78), (0.31, 0.08, 1.12))           # 팔 아래
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.115, matrix=__import__("mathutils").Matrix.Translation((0, -0.02, 1.685)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    mt = bpy.data.materials.get("REF_Human") or bpy.data.materials.new("REF_Human"); mt.use_nodes = True
    mt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.4, 0.55, 1); mt.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
    me.materials.append(mt)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, 0.0); ob.rotation_euler = (0, 0, math.radians(rot_deg)); return ob


bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene; sc.cycles.samples = SAMPLES; sc.render.image_settings.file_format = 'PNG'
game_cam = bpy.data.objects["Game_Output_Iso"]
cd = bpy.data.cameras.new("VIEW07"); pcam = bpy.data.objects.new("VIEW07", cd); sc.collection.objects.link(pcam)
cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 600
for name, v in VIEWS.items():
    if ONLY and name not in ONLY:
        continue
    hs = [human(f"REF_Human_1p8m_{k}", *h) for k, h in enumerate(v["human"])]
    if v["kind"] == "game":
        sc.camera = game_cam
        W, H, sx0, sy0 = SC.setup(sc, game_cam, CFG, density=1, sub=v["rect"])
    else:
        sc.camera = pcam; pcam.location = Vector(v["loc"])
        pcam.rotation_euler = (Vector(v["tgt"]) - Vector(v["loc"])).to_track_quat('-Z', 'Y').to_euler()
        cd.lens = v["lens"]; sc.render.resolution_x, sc.render.resolution_y = v["res"]; sc.render.resolution_percentage = 100
    sc.render.filepath = f"{PRE}_{name}.png"; os.makedirs(os.path.dirname(os.path.abspath(sc.render.filepath)), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("VIEW", name, sc.render.filepath, flush=True)
    for h in hs:
        bpy.data.objects.remove(h)
