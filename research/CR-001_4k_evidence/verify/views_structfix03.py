"""구조 수정 3차(A3e) 확인 화면(A3d와 같은 카메라로 전/후): 최종 재질 스테이지 .blend에서 같은 카메라로 원근 화면을 렌더한다(영화 이미지 없음 — 커밋 가능).
카메라 위치는 영화 프레임에 맞춘 값이 아니라 비슷한 시점의 근사다(카메라 재계산·치수 탐색 아님).
실행(저장소 루트): .venv-bpy/bin/python research/CR-001_4k_evidence/verify/views_structfix03.py <stage.blend> <출력 접두어> [카메라 이름 ...]"""
import math, os, sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
blend, pre = args[0], args[1]
only = set(args[2:])
CAMS = {
    # 이름: (위치, 바라보는 점, 렌즈 mm, 가로, 세로) — 2차와 같은 카메라 재사용 + 3차 항목별 근접
    "film78862": ((5.5, -18.2, 1.5), (16.3, -19.3, 2.6), 24, 1434, 600),        # 78862 비슷한 시점(2차와 동일)
    "entrance_front": ((9.0, -19.06, 1.6), (16.3, -19.06, 1.9), 30, 1200, 900),  # 출입구 정면(사람 눈높이)
    "entrance_oblique": ((8.6, -13.2, 3.4), (15.6, -19.8, 1.0), 22, 1400, 900),  # 2차와 동일
    "R_oblique": ((6.0, -31.5, 3.6), (12.8, -24.0, 0.3), 24, 1400, 900),         # R·측면 확장부
    "film78855": ((7.2, -29.8, 1.9), (13.0, -22.5, 0.6), 30, 900, 1100),         # 78855 비슷한 낮은 시점(구조물 경사 외벽·띠)
    "side_walkway": ((5.0, 28.5, 5.5), (19.0, 21.0, 0.3), 22, 1400, 900),        # 시설 왼쪽 끝 외부 통로
    "pad_overview": ((-34.0, -46.0, 30.0), (-1.0, -4.0, 0.0), 26, 1600, 1000),   # 판 외곽 전체(앞 바깥 모서리 쪽 높은 시점)
    "film11206": ((-95.0, 8.0, 9.0), (0.0, 0.0, 2.0), 55, 1600, 667),           # 11206 비슷한 먼 옆 시점(외곽 실루엣 대조용, 맞춤 아님)
}
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("VIEW_SAMPLES", 40)); sc.cycles.use_denoising = True
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
