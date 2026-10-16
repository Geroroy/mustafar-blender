"""2단계 — Movie Duels 원본 렌더(기존 제작 맵 형상 없는 별도 장면). Blender(bpy).
입력: md01_import_source.py가 만든 MD_SOURCE_IMPORT.blend(장면 SRC_duel_mustafar / SRC_duel_mus_both, 각 장면에 그 맵 컬렉션 하나만 있음)
출력: <출력 폴더>/A_source_*.png — 이미지마다 원본 파일명·장면·컬렉션·표시 객체 수·영역·숨김 규칙을 적는다.
  - 전체 상면: 맵 전체(아무것도 숨기지 않음) + 착륙장 검사 영역 상자
  - 영역 렌더: 검사 영역 밖 삼각형을 뺀 임시 사본(원본 객체는 그대로). 영역 안 암벽(rock_*)·용암(lava)은 판·정면을 가려서 뺌(이미지에 적음)
  - 식별 표시: 착륙장(PAD)·시설 정면(FRONT)·입구(ENTRY) — md_regions.json의 원본 좌표(u)를 화면에 투영해 상자로 그림
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/md_remake/md02_render_source.py <MD_SOURCE_IMPORT.blend> <출력 폴더> [--samples 24]
"""
import json, math, os, sys

import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import md_render as R  # noqa: E402

SRC, OUT = sys.argv[1], sys.argv[2]
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 24
REG = json.load(open(os.path.join(HERE, "md_regions.json"), encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
COL = {"PAD": (80, 220, 255), "FRONT": (255, 200, 60), "ENTRY": (255, 80, 200), "SIDE": (120, 255, 120), "BAY": (255, 140, 60)}


def tex_of(o):
    ma = o.data.materials[0] if o.data.materials else None
    im = [n.image.name for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image] if ma and ma.node_tree else []
    return im[0] if im else ""


def region_copy(sc, src_objs, box, hide_tex):
    """영역 상자 안(면 중심 기준) 삼각형만 남긴 임시 사본. 원본 객체는 렌더에서 끔."""
    (x0, y0, z0), (x1, y1, z1) = box; tmp = []
    for o in src_objs:
        o.hide_render = True
        if any(h in tex_of(o) for h in hide_tex):
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        dead = [f for f in bm.faces if not (x0 <= f.calc_center_median().x <= x1 and y0 <= f.calc_center_median().y <= y1 and z0 <= f.calc_center_median().z <= z1)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        if not bm.faces:
            bm.free(); continue
        me = D.meshes.new("RGN_" + o.name); bm.to_mesh(me); bm.free()
        for m in o.data.materials:
            me.materials.append(m)
        c = D.objects.new("RGN_" + o.name, me); sc.collection.objects.link(c); tmp.append(c)
    return tmp


def boxes_px(sc, cam, marks):
    out = []
    for k, (lo, hi) in marks:
        pts = [R.world_to_px(sc, cam, (x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append((min(xs), min(ys), max(xs), max(ys), k, COL[k.split(":")[0]]))
    return out


made = []
for m, spec in REG["maps"].items():
    sc = D.scenes["SRC_" + m]; col = sc.collection.children[0]; objs = list(col.objects)
    R.ensure_light(sc, sun_rot=tuple(math.radians(a) for a in spec.get("sun_rot_deg", (45, 0, 35))))
    head = f"원본 파일: {m}.obj  (02_models.zip / models/)  |  장면 SRC_{m}  |  컬렉션 {col.name}"
    marks = [(k, v) for k, v in spec["marks"].items()]
    # 전체 상면
    cam = R.camera(sc, spec["full_center"], spec["full_extent"], 'top')
    res = tuple(spec.get("full_res", (1280, 1280)))
    png = os.path.join(OUT, f"A_source_{m}_00_full_top.png"); R.render(sc, png, res, samples=max(8, SAMPLES // 3))
    rb = spec["region"]
    R.label(png, [head, f"전체 맵 상면(직교, 위 = +Y). 객체 {len(objs)}개 모두 표시, 숨김 없음. 노란 상자 = 착륙장 검사 영역 x {rb[0][0]}~{rb[1][0]}, y {rb[0][1]}~{rb[1][1]} (원본 u)"],
            boxes=[(*[min(a, b) for a, b in zip(R.world_to_px(sc, cam, rb[0]), R.world_to_px(sc, cam, rb[1]))],
                    *[max(a, b) for a, b in zip(R.world_to_px(sc, cam, rb[0]), R.world_to_px(sc, cam, rb[1]))], "검사 영역", (255, 220, 0))])
    made.append(png); cam.name = "CHK_Cam_done"; D.objects.remove(cam)
    # 영역 렌더
    tmp = region_copy(sc, objs, rb, spec.get("hide_tex", []))
    for k, v in enumerate(spec["views"]):
        view = 'top' if v["view"] == "top" else ("az", v["view"][0], v["view"][1])
        extra = v.get("hide_tex_extra", [])
        for c in tmp:
            c.hide_render = any(h in tex_of(c) for h in extra)
        cam = R.camera(sc, v.get("center", spec["region_center"]), v["extent"], view)
        png = os.path.join(OUT, f"A_source_{m}_{k + 1:02d}_{v['name']}.png"); R.render(sc, png, tuple(v.get("res", (1440, 1080))), samples=SAMPLES)
        vd = "상면" if view == 'top' else f"직교 사선(카메라 방위 {view[1]}°, 고도 {view[2]}°)"
        R.label(png, [head, f"{v['title']} — {vd}. 영역 x {rb[0][0]}~{rb[1][0]}, y {rb[0][1]}~{rb[1][1]}, z {rb[0][2]}~{rb[1][2]} u 밖 삼각형 제외(검사용 자름)",
                      f"표시 객체 {sum(not c.hide_render for c in tmp)}/{len(objs)}개(재질 그룹). 숨김: 영역 밖, " + (", ".join(spec.get("hide_tex", []) + extra) or "없음") + ". 회색 = 원본 재질에 질감 연결 없음(색 아님). 기존 A3e·v0.3 형상 없음"],
                boxes=boxes_px(sc, cam, marks) if v.get("marks", True) else None)
        made.append(png); D.objects.remove(cam)
    for c in tmp:
        D.objects.remove(c)
    for o in objs:
        o.hide_render = False
json.dump(made, open(os.path.join(OUT, "A_source_list.json"), "w"), ensure_ascii=False, indent=0)
print("DONE", len(made))
