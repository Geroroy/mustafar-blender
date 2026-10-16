"""MO-2 원본 렌더 — 수정 전 duel_mus_both 전체와 착륙장 영역. Blender(bpy).
입력: mo01이 만든 MO_ORIGINAL_IMPORT.blend. 아무것도 숨기거나 자르지 않는다(우주선·소품·용암·암벽 모두 표시). 원본 좌표 그대로.
출력: <출력 폴더>/O_*.png — 이미지마다 원본 파일명·객체 수·카메라·영역을 적는다.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo02_render_original.py <MO_ORIGINAL_IMPORT.blend> <출력 폴더> [--samples 24]
"""
import json, math, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mo_render as R  # noqa: E402

SRC, OUT = sys.argv[1], sys.argv[2]
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 24
REG = json.load(open(os.path.join(HERE, "mo_regions.json"), encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.data.scenes["SRC_duel_mus_both"]; objs = list(sc.collection.all_objects)
R.ensure_light(sc, sun_rot=tuple(math.radians(a) for a in REG["sun_rot_deg"]), sun=2.5, amb=0.9)
head = f"원본 파일: duel_mus_both.obj (수정 전 추출 모델)  |  객체 {len(objs)}개 전부 표시, 숨김·삭제·회전·이동 없음  |  원본 좌표 u(Z 위)"
rb = REG["region"]; made = []
VIEWS = [("00_full_top", "전체 맵 상면", REG["full_center"], REG["full_extent"], 'top', tuple(REG["full_res"])),
         ("01_region_top", "착륙장 영역 상면", REG["region_center"], 2800, 'top', (1440, 1080)),
         ("02_region_oblique_A", "착륙장 영역 사선 A(카메라 방위 −35°, 고도 30°)", REG["region_center"], 2600, ('az', -35, 30), (1440, 1080)),
         ("03_region_oblique_B", "착륙장 영역 사선 B(방위 35°)", REG["region_center"], 2600, ('az', 35, 30), (1440, 1080)),
         ("04_front_ground", "시설 정면·입구(판 쪽 낮은 고도 14°)", [3700, -850, 300], 1700, ('az', 0, 14), (1440, 1080))]
for name, title, ctr, ext, view, res in VIEWS:
    cam = R.camera(sc, ctr, ext, view)
    png = os.path.join(OUT, f"O_{name}.png"); R.render(sc, png, res, samples=SAMPLES)
    boxes = None
    if view == 'top':
        a, b = R.world_to_px(sc, cam, rb[0]), R.world_to_px(sc, cam, rb[1])
        boxes = [(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), "착륙장 영역", (255, 220, 0))]
    R.label(png, [head, f"{title}. 영역 x {rb[0][0]}~{rb[1][0]}, y {rb[0][1]}~{rb[1][1]} u. 회색 = 추출본에 질감 연결 없음(원본 색 아님)"], boxes=boxes)
    made.append(png); bpy.data.objects.remove(cam)
json.dump(made, open(os.path.join(OUT, "O_list.json"), "w"), ensure_ascii=False, indent=0)
print("DONE", len(made))
