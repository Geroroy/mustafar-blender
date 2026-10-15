"""CR-001 추가 렌더 V2~V5 — v0.2 모델 사본에서 카메라·표시 설정만 바꿔 렌더한다.

실행 (저장소 루트에서):
    .venv-bpy/bin/python chatgpt_reviews/CR-001_v0.2/extra_renders/make_extra_views.py

- v0.2/mustafar_blockout_v0.2.blend를 임시 폴더로 복사해 연다. 원본은 읽기만 하고, 사본도 저장하지 않는다.
- 모델 메시·치수·재질은 바꾸지 않는다. 바꾸는 것: 카메라 추가, 객체 hide_render, 해상도.
- 결과: 이 폴더의 V2~V5 PNG, render_log.json(카메라·숨긴 객체·원본 해시).
"""
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "v0.2", "mustafar_blockout_v0.2.blend")
GAME_PPM = 28.28          # 게임 축척(px/m), v0.1/dimensions.json iso_px_per_m_game


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


SRC_HASH = sha256(SRC)
TMP = tempfile.mkdtemp(prefix="cr001_")
COPY = os.path.join(TMP, "copy.blend")
shutil.copy2(SRC, COPY)
bpy.ops.wm.open_mainfile(filepath=COPY)
scene = bpy.context.scene
OBJ = bpy.data.objects
for o in OBJ:                                   # 저장된 상태와 같게 시작(모두 보임)
    o.hide_render = False

FD_ = "/usr/share/fonts/truetype/dejavu/"
FONT = ImageFont.truetype(FD_ + "DejaVuSans.ttf", 13)
FONTS = ImageFont.truetype(FD_ + "DejaVuSans.ttf", 11)
FONTB = ImageFont.truetype(FD_ + "DejaVuSans-Bold.ttf", 17)
TAGC = {"C": (215, 215, 215), "P": (240, 200, 110), "U": (240, 125, 215)}
LEGEND = "colour = FORM confidence: grey C  ochre P  magenta U | wire = placeholder | green = ship/scale check | E/F = exist/form"

PLACEHOLDERS = ["Support_Placeholder", "Facility_Base_Placeholder", "Cliff_Placeholder"]
OUTLINES = ["Outline_Alt_84.7deg", "Outline_Alt_98.4deg"]
ROOF = ["Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown"]


def tag(ob):
    return str(ob.get("exist", "U"))[0], str(ob.get("form", "U"))[0]


def new_cam(name, rot_deg, ortho=True, clip_start=0.1):
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO' if ortho else 'PERSP'
    cd.clip_start, cd.clip_end = clip_start, 2000
    co = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(co)
    co.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    bpy.context.view_layer.update()
    return co


def axes(cam):
    m = cam.matrix_world.to_3x3()
    return m.col[0].normalized(), m.col[1].normalized(), -m.col[2].normalized()


def place(cam, center, back):
    """정사영 카메라를 center가 화면 가운데 오도록, 시선 반대쪽으로 back m 떨어뜨려 둔다."""
    _, _, fwd = axes(cam)
    cam.location = Vector(center) - fwd * back
    bpy.context.view_layer.update()


def to_px(cam, p, W, H):
    r, u, _ = axes(cam)
    d = Vector(p) - cam.location
    s = cam.data.ortho_scale
    return W / 2 + d.dot(r) / s * W, H / 2 - d.dot(u) / s * W


def render(cam, res, hide, path):
    for o in OBJ:
        o.hide_render = o.name in hide
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 1)


def label_objects(im, cam, skip=(), only=None):
    """보이는 메시 객체 이름을 bbox 중심(화면 안으로 당김)에 붙인다. only가 있으면 그 객체만(클리핑 뷰용)."""
    dr = ImageDraw.Draw(im)
    W, H = im.size
    dg = bpy.context.evaluated_depsgraph_get()
    items = []
    for o in OBJ:
        if o.type != 'MESH' or o.hide_render or o.name in skip or (only is not None and o.name not in only):
            continue
        ev = o.evaluated_get(dg)
        pts = [to_px(cam, o.matrix_world @ Vector(c), W, H) for c in ev.bound_box]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = max(min(xs), 0), min(max(xs), W), max(min(ys), 30), min(max(ys), H - 22)
        if x0 >= x1 or y0 >= y1:
            continue                                   # 화면 밖
        items.append((o.name, tag(o), (x0 + x1) / 2, (y0 + y1) / 2))
    placed = []
    for nm, (e, fm), x, y in sorted(items, key=lambda t: t[3]):
        txt = f"{nm}  E:{e} F:{fm}"
        col = TAGC.get(fm, TAGC["U"])
        tw = dr.textlength(txt, font=FONT)
        tx = min(max(x + 8, 4), W - tw - 6); ty = min(max(y - 8, 36), H - 40)
        for _ in range(40):
            if not any(abs(ty - py) < 17 and tx < px + pw + 4 and px < tx + tw + 4 for px, py, pw in placed):
                break
            ty += 17
        placed.append((tx, ty, tw))
        dr.line((x, y, tx, ty + 7), fill=col)
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col, outline=(0, 0, 0))
        dr.rectangle((tx - 3, ty - 1, tx + tw + 3, ty + 15), fill=(0, 0, 0))
        dr.text((tx, ty), txt, font=FONT, fill=col)


def grid(im, cam, h_axis, h_range, z_range):
    """정사영 입면·단면용 1 m 격자(5 m마다 진하게, 숫자). h_axis: 화면 가로가 나타내는 월드 축 벡터."""
    dr = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    hv = Vector(h_axis)
    base = cam.location.copy()
    for k in range(int(h_range[0]), int(h_range[1]) + 1):
        p = base.copy(); p -= hv * base.dot(hv); p += hv * k
        x, _ = to_px(cam, p, W, H)
        major = k % 5 == 0
        dr.line((x, 28, x, H - 20), fill=(255, 255, 255, 90 if major else 35), width=1)
        if major:
            dr.text((x + 2, H - 36), f"{k}", font=FONTS, fill=(255, 255, 255, 230))
    for z in range(int(z_range[0]), int(z_range[1]) + 1):
        p = base.copy(); p.z = z
        _, y = to_px(cam, p, W, H)
        major = z % 5 == 0
        dr.line((0, y, W, y), fill=(255, 255, 255, 90 if major else 35), width=1)
        if major or z in (-3, 7):
            dr.text((3, y - 13), f"Z {z}", font=FONTS, fill=(255, 255, 255, 230))


def frame(im, title, legend=LEGEND):
    dr = ImageDraw.Draw(im)
    W, H = im.size
    dr.rectangle((0, 0, W, 28), fill=(0, 0, 0))
    dr.text((8, 5), title, font=FONTB, fill=(255, 255, 255))
    dr.rectangle((0, H - 20, W, H), fill=(0, 0, 0))
    dr.text((8, H - 18), legend, font=FONT, fill=(220, 220, 220))


def scale_bar(im, ppm, metres, y_off=52):
    dr = ImageDraw.Draw(im)
    H = im.size[1]
    L = metres * ppm
    dr.rectangle((10, H - y_off, 30 + L + 60, H - y_off + 28), fill=(0, 0, 0))
    dr.line((20, H - y_off + 14, 20 + L, H - y_off + 14), fill=(255, 255, 255), width=3)
    dr.text((28 + L, H - y_off + 6), f"{metres:g} m", font=FONT, fill=(255, 255, 255))


def cam_record(cam, res, hide, clip_note=""):
    d = cam.data
    r, u, f = axes(cam)
    rec = {"type": d.type, "location_m": [round(v, 3) for v in cam.location],
           "rotation_euler_deg": [round(math.degrees(a), 2) for a in cam.rotation_euler],
           "view_direction": [round(v, 3) for v in f], "screen_right": [round(v, 3) for v in r],
           "screen_up": [round(v, 3) for v in u], "resolution_px": list(res),
           "clip_start_m": round(d.clip_start, 4), "clip_end_m": d.clip_end, "hidden_objects": sorted(hide)}
    if d.type == 'ORTHO':
        rec["ortho_scale_m"] = round(d.ortho_scale, 3)
        rec["px_per_m"] = round(res[0] / d.ortho_scale, 2)
    if clip_note:
        rec["clip_note"] = clip_note
    return rec


LOG = {"source_blend": "v0.2/mustafar_blockout_v0.2.blend", "source_sha256_before": SRC_HASH,
       "bpy_version": bpy.app.version_string, "engine": scene.render.engine,
       "samples": scene.cycles.samples, "denoise": scene.cycles.use_denoising,
       "model_changes": "없음 — 카메라 추가, hide_render, 해상도만 변경. 사본은 저장하지 않음", "views": {}}

# ---------------------------------------------------------------- V2 시설 쪽 단면 (y = -15.5, 계단 상자 가운데)
Y_CUT = -15.5
c2 = new_cam("V2_Section_Y", (90, 0, 0), clip_start=0.001)          # +Y를 봄, 화면 오른쪽 = +X, 위 = +Z
c2.data.ortho_scale = 50.0
place(c2, (6.0, Y_CUT, 1.5), 0.0)
c2.location.y = Y_CUT                                                # 카메라 평면 = 자르는 면
res2 = (1280, 720)
hide2 = PLACEHOLDERS + OUTLINES + ["Lava_Level_Ref", "Skiff_Check_29m_x_49m"]
raw = os.path.join(TMP, "v2.png")
t2 = render(c2, res2, hide2, raw)
im = Image.open(raw).convert("RGB")
grid(im, c2, (1, 0, 0), (-19, 31), (-12, 15))
label_objects(im, c2, only=("Landing_Platform", "Platform_Sidewalls", "Stairwell", "Stairwell_Lit_Slots",
                            "Corridor_Lower_Walkway", "Hangar_Walls", "Structural_Pillars", "Hangar_Roof",
                            "Hangar_Spotlights", "Facility_Body_Unknown"))
frame(im, f"V2 Section at Y = {Y_CUT} m (through stairwell), looking +Y (toward cliff)   +X right = facility   1 m grid")
out2 = os.path.join(HERE, "V2_section_facility_side.png"); im.save(out2)
LOG["views"]["V2"] = dict(file=os.path.basename(out2), seconds=t2, **cam_record(
    c2, res2, hide2, f"카메라 평면 y = {Y_CUT}에서 clip_start 0.001 m — 그보다 앞(−Y)은 잘림. 잘린 면은 채워지지 않아 속이 보일 수 있음. 자른 면 뒤의 구조는 입면으로 보임"))

# ---------------------------------------------------------------- V3 시설 벽 정면 (판 쪽에서 +X를 봄)
X_CLIP = 14.85                                                       # 판 가장자리(14.5)와 트렌치 안쪽 벽(14.5~14.8) 바로 바깥
c3 = new_cam("V3_Facility_Front_X", (90, 0, -90), clip_start=0.001)  # +X를 봄, 화면 오른쪽 = −Y(판 앞), 위 = +Z
c3.data.ortho_scale = 50.0
place(c3, (X_CLIP, 0.5, 2.0), 0.0)
c3.location.x = X_CLIP
res3 = (1280, 720)
hide3 = PLACEHOLDERS + OUTLINES + ["Lava_Level_Ref", "Skiff_Check_29m_x_49m"]
raw = os.path.join(TMP, "v3.png")
t3 = render(c3, res3, hide3, raw)
im = Image.open(raw).convert("RGB")
grid(im, c3, (0, -1, 0), (-25, 25), (-12, 15))
label_objects(im, c3, only=("Corridor_Lower_Walkway", "Hangar_Walls", "Structural_Pillars", "Hangar_Roof",
                            "Hangar_Spotlights", "Facility_Body_Unknown"))
frame(im, f"V3 Facility front elevation, looking +X from X = {X_CLIP} m   left = +Y (cliff/back), right = -Y (front)   1 m grid, numbers = -Y")
out3 = os.path.join(HERE, "V3_facility_wall_front.png"); im.save(out3)
LOG["views"]["V3"] = dict(file=os.path.basename(out3), seconds=t3, **cam_record(
    c3, res3, hide3, f"카메라 평면 x = {X_CLIP}에서 clip_start 0.001 m — 판(x ≤ 14.5), 계단 상자, 가장자리 등, 트렌치 안쪽 벽(x 14.5~14.8)은 잘려 보이지 않음. 트렌치 바닥(Z −3)과 벽 밑동이 보이게 하려는 것. 격자 숫자는 −Y 값(오른쪽이 +)"))

# ---------------------------------------------------------------- V4 게임 축척 부분 확대 (경사로-계단 상자-시설 모퉁이)
iso = OBJ["Isometric_View"]
c4 = new_cam("V4_Game_Scale_Crop", tuple(math.degrees(a) for a in iso.rotation_euler))
res4 = (1536, 864)
c4.data.ortho_scale = res4[0] / GAME_PPM
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for nm in ("Stairwell", "Ramp_Foot_Measured", "Ref_ObiWan", "Ref_Anakin", "Ref_Padme"):
    ev = OBJ[nm].evaluated_get(dg)
    pts += [OBJ[nm].matrix_world @ Vector(c) for c in ev.bound_box]
ctr = sum(pts, Vector()) / len(pts)
ctr.z = 0.0
place(c4, ctr, 400)
hide4 = []
raw = os.path.join(TMP, "v4.png")
t4 = render(c4, res4, hide4, raw)
im = Image.open(raw).convert("RGB")
frame(im, f"V4 Game projection at game scale {GAME_PPM} px/m (ortho elev 30 / az 45, 2:1)  - no labels; green cylinders = 1.78 / 1.85 m people")
scale_bar(im, GAME_PPM, 5)
out4 = os.path.join(HERE, "V4_game_scale_crop.png"); im.save(out4)
LOG["views"]["V4"] = dict(file=os.path.basename(out4), seconds=t4, center_m=[round(v, 2) for v in ctr],
                          center_basis="Stairwell·Ramp_Foot_Measured·Ref_ObiWan·Ref_Anakin·Ref_Padme bbox 꼭짓점 평균(z=0)",
                          **cam_record(c4, res4, hide4))

# ---------------------------------------------------------------- V5 지붕 숨긴 게임 투영 (isometric_view와 같은 카메라)
c5 = new_cam("V5_Game_No_Roof", tuple(math.degrees(a) for a in iso.rotation_euler))
c5.data.ortho_scale = iso.data.ortho_scale
c5.location = iso.location.copy()
res5 = (1280, 720)
hide5 = ROOF
raw = os.path.join(TMP, "v5.png")
t5 = render(c5, res5, hide5, raw)
im = Image.open(raw).convert("RGB")
frame(im, f"V5 Game projection, roof / eave lights / facility body hidden  (same camera as isometric_view.png, {res5[0] / c5.data.ortho_scale:.1f} px/m)  - no labels")
scale_bar(im, res5[0] / c5.data.ortho_scale, 10)
out5 = os.path.join(HERE, "V5_game_iso_no_roof.png"); im.save(out5)
LOG["views"]["V5"] = dict(file=os.path.basename(out5), seconds=t5, camera_basis="v0.2 Isometric_View 카메라의 위치·회전·ortho_scale 복사",
                          **cam_record(c5, res5, hide5))

# ---------------------------------------------------------------- 마무리: 원본 무변경 확인, 사본 삭제(저장 안 함)
LOG["source_sha256_after"] = sha256(SRC)
LOG["source_unchanged"] = LOG["source_sha256_after"] == SRC_HASH
with open(os.path.join(HERE, "render_log.json"), "w", encoding="utf-8") as f:
    json.dump(LOG, f, ensure_ascii=False, indent=2)
shutil.rmtree(TMP, ignore_errors=True)
print("EXTRA RENDERS OK", {k: v["seconds"] for k, v in LOG["views"].items()}, "source_unchanged =", LOG["source_unchanged"])
if not LOG["source_unchanged"]:
    sys.exit(2)
