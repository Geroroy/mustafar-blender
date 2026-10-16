"""B — 리메이크 결과 렌더. Blender(bpy). 원본 렌더(md02, A_source_duel_mus_both_*)와 같은 시점을 같은 좌표 변환으로 옮겨 찍는다(전/후 짝).
  --mode layout : 형상 확인용 중립 조명(원본 렌더와 같은 조명·색 처리) — layout_MD_REMAKE_POC01.blend
  --mode stage  : 게임용 재질·조명(build_stage 결과) — mustafar_landing_stage_MD_REMAKE_POC01.blend
실행: .venv-bpy/bin/python v0.4_stage/md_remake/md05_render_remake.py <.blend> <출력 폴더> --mode layout|stage [--samples 24]
"""
import json, math, os, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import md_render as R  # noqa: E402

BLEND, OUT = sys.argv[1], sys.argv[2]
MODE = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "layout"
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 24
C = json.load(open(os.path.join(HERE, os.environ.get("MD_CONFIG", "md_poc01.json")), encoding="utf-8")); T = C["transform"]; S = T["scale_m_per_u"]
REG = json.load(open(os.path.join(HERE, "md_regions.json"), encoding="utf-8"))["maps"][C["source_map"]]


def u2m(p):
    x, y, z = p; pu = T["pre_translate_u"]; return ((-pu[0] - x) * S + T["offset_m"][0], -(y + pu[1]) * S, (z + pu[2]) * S)


bpy.ops.wm.open_mainfile(filepath=BLEND)
SCN = C.get("scene_name", "MD_REMAKE_POC01")
sc = bpy.data.scenes.get(SCN) or bpy.context.scene
if MODE == "layout":
    R.ensure_light(sc, sun_rot=tuple(math.radians(a) for a in (REG.get("sun_rot_deg", (45, 0, 35))[0], 0, REG.get("sun_rot_deg", (45, 0, 35))[2] + 180)))
lab = f"{SCN} — 출발 형상: duel_mus_both.obj 착륙장 영역(md03_build_poc.py 복사·축척·수정). 기존 A3e 형상 없음"
made = []
for k, v in enumerate(REG["views"]):
    c = u2m(v.get("center", REG["region_center"])); ext = v["extent"] * S
    view = ('top', 180) if v["view"] == "top" else ("az", v["view"][0] + 180, v["view"][1])
    cam = R.camera(sc, c, ext, view)
    png = os.path.join(OUT, f"B_remake_{MODE}_{k + 1:02d}_{v['name']}.png")
    if MODE == "layout":
        R.render(sc, png, tuple(v.get("res", (1440, 1080))), samples=SAMPLES)
    else:
        sc.render.resolution_x, sc.render.resolution_y = tuple(v.get("res", (1440, 1080))); sc.render.resolution_percentage = 100
        sc.cycles.samples = SAMPLES; sc.render.filepath = png; sc.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
    vd = "상면(원본과 같은 방향으로 180° 돌려 봄)" if view[0] == 'top' else f"직교 사선(우리 좌표 방위 {view[1]}° = 원본 방위 {v['view'][0]}°, 고도 {view[2]}°)"
    R.label(png, [lab, f"{v['title']} — {vd}, 원본 렌더와 같은 시점·같은 범위(×{S} m/u)",
                  ("중립 검사 조명(원본 렌더와 같음)" if MODE == "layout" else "게임용 재질·조명(build_stage)") + ". 판 윗면 z 0, +X 시설"])
    made.append(png); bpy.data.objects.remove(cam)
print("DONE", made)
