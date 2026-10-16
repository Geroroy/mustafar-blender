"""구조 수정 2차(A3d) 확인 화면: 최종 재질 스테이지 .blend에서 같은 카메라로 원근 화면을 렌더한다(영화 이미지 없음 — 커밋 가능).
카메라 위치는 영화 프레임에 맞춘 값이 아니라 비슷한 시점의 근사다(카메라 재계산·치수 탐색 아님).
실행(저장소 루트): .venv-bpy/bin/python research/CR-001_4k_evidence/verify/views_structfix02.py <stage.blend> <출력 접두어> [카메라 이름 ...]"""
import math, sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
blend, pre = args[0], args[1]
only = set(args[2:])
CAMS = {
    # 이름: (위치, 바라보는 점, 렌즈 mm, 가로, 세로)
    "film78862": ((5.5, -18.2, 1.5), (16.3, -19.3, 2.6), 24, 1434, 600),       # 판 위 사람 눈높이에서 출입구 정면(78862 비슷한 시점)
    "film78853": ((11.5, -17.0, 2.2), (22.0, 2.0, 3.5), 20, 1000, 1000),       # 상자 옆에서 시설 정면을 비스듬히(78853 비슷한 시점)
    "bays_front": ((1.0, 1.5, 3.2), (22.5, 1.5, 2.2), 20, 1600, 900),         # 판 가운데에서 베이 3개 정면
    "bay_interior": ((14.2, -1.6, 1.8), (27.0, 2.6, -1.2), 22, 1400, 900),     # 틈 가장자리에서 가운데 베이 안쪽(깊이)
    "entrance_oblique": ((8.6, -13.2, 3.4), (15.6, -19.8, 1.0), 22, 1400, 900),  # 출입구·양옆 낮은 구조물 비스듬히
}
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
sc.render.film_transparent = False
cd = bpy.data.cameras.new("VIEW02"); cam = bpy.data.objects.new("VIEW02", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.type = 'PERSP'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 500
for name, (loc, tgt, lens, w, h) in CAMS.items():
    if only and name not in only:
        continue
    cam.location = Vector(loc); cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens; sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.filepath = f"{pre}_{name}.png"; bpy.ops.render.render(write_still=True)
    print("VIEW", name, sc.render.filepath, flush=True)
