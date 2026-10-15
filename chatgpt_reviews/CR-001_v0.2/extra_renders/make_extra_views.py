"""CR-001 추가 렌더 V2~V5 — v0.2 모델 사본에서 카메라·표시·렌더 설정만 바꿔 렌더한다.

실행 (저장소 루트에서):
    .venv-bpy/bin/python chatgpt_reviews/CR-001_v0.2/extra_renders/make_extra_views.py                 # original
    .venv-bpy/bin/python chatgpt_reviews/CR-001_v0.2/extra_renders/make_extra_views.py --preset review  # 빠른 검수용

프리셋
- original: 처음 만든 그대로(1280×720·V4 1536×864, v0.2 .blend의 렌더 설정 = Cycles 24 샘플). 결과 → 이 폴더.
- review:   768×432, Cycles 12 샘플(--samples 8~16), 빛 튕김 축소, persistent data(장면 데이터 재사용).
            결과 → ../extra_renders_review/ (별도 폴더).

공통
- v0.2/mustafar_blockout_v0.2.blend를 임시 폴더로 복사해 **한 번만** 연다. 카메라만 바꿔 V2→V5를 순서대로 렌더한다(병렬 없음).
  원본은 읽기만 하고, 사본도 저장하지 않는다(원본 sha256을 전후로 비교).
- 모델 지오메트리·재질·카메라 배치 기준은 바꾸지 않는다. 바꾸는 것: 카메라 추가, 객체 hide_render, 해상도, Cycles 렌더 설정.
- 해상도를 줄여도 V2·V3·V5는 같은 화면 범위(ortho_scale)를 유지하고, V4는 게임 축척(28.28 px/m)과 중심점을 유지한다.
"""
import argparse
import hashlib
import json
import math
import os
import resource
import shutil
import sys
import tempfile
import time

T_START = time.time()
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "v0.2", "mustafar_blockout_v0.2.blend")
GAME_PPM = 28.28          # 게임 축척(px/m), v0.1/dimensions.json iso_px_per_m_game

ap = argparse.ArgumentParser()
ap.add_argument("--preset", choices=("original", "review"), default="original")
ap.add_argument("--samples", type=int, help="review 프리셋 샘플 수 (기본 12, 권장 8~16)")
ap.add_argument("--res", default="768x432", help="review 프리셋 해상도 W×H (기본 768x432)")
ap.add_argument("--out", help="결과 폴더 (기본: original → 이 폴더, review → ../extra_renders_review)")
ARGS = ap.parse_args()
REVIEW = ARGS.preset == "review"
OUT = os.path.abspath(ARGS.out or (os.path.join(HERE, "..", "extra_renders_review") if REVIEW else HERE))
os.makedirs(OUT, exist_ok=True)
if REVIEW:
    RW, RH = (int(v) for v in ARGS.res.lower().split("x"))
    SAMPLES = ARGS.samples or 12


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)   # Linux: KB


SRC_HASH = sha256(SRC)
TMP = tempfile.mkdtemp(prefix="cr001_")
COPY = os.path.join(TMP, "copy.blend")
shutil.copy2(SRC, COPY)
bpy.ops.wm.open_mainfile(filepath=COPY)
scene = bpy.context.scene
OBJ = bpy.data.objects
for o in OBJ:                                   # 저장된 상태와 같게 시작(모두 보임)
    o.hide_render = False
T_LOADED = time.time()

# ---------------------------------------------------------------- 렌더 설정
RENDER_SETTINGS = {"engine": scene.render.engine, "device": scene.cycles.device}
if REVIEW:
    c, r = scene.cycles, scene.render
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02                  # 기본 0.01 → 평평한 면에서 일찍 멈춤
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 2
    c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 0, 0, 2   # 유리·부피 재질 없음
    c.caustics_reflective = c.caustics_refractive = False
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_prefilter = 'FAST'
    c.denoising_quality = 'BALANCED'
    r.use_persistent_data = True                 # 카메라만 바꾸는 연속 렌더에서 장면 동기화·BVH 재사용
    r.threads_mode = 'FIXED'
    r.threads = len(os.sched_getaffinity(0))     # 이 컨테이너가 쓸 수 있는 CPU 수
c, r = scene.cycles, scene.render
RENDER_SETTINGS.update(samples=c.samples, adaptive=c.use_adaptive_sampling, adaptive_threshold=round(c.adaptive_threshold, 4),
                       bounces=dict(max=c.max_bounces, diffuse=c.diffuse_bounces, glossy=c.glossy_bounces,
                                    transmission=c.transmission_bounces, transparent=c.transparent_max_bounces),
                       caustics=c.caustics_reflective or c.caustics_refractive,
                       denoise=c.use_denoising, denoiser=c.denoiser, denoise_prefilter=c.denoising_prefilter,
                       denoise_quality=c.denoising_quality, persistent_data=r.use_persistent_data,
                       threads_mode=r.threads_mode, threads=r.threads)

# ---------------------------------------------------------------- 글꼴 (해상도에 맞춰 줄임, original은 처음과 같음)
FD_ = "/usr/share/fonts/truetype/dejavu/"
TAGC = {"C": (215, 215, 215), "P": (240, 200, 110), "U": (240, 125, 215)}
LEGEND = "colour = FORM confidence: grey C  ochre P  magenta U | wire = placeholder | green = ship/scale check | E/F = exist/form"
F = {}


def set_fonts(W):
    k = min(1.0, W / 1280)
    F["k"] = k
    F["n"] = ImageFont.truetype(FD_ + "DejaVuSans.ttf", max(9, round(13 * k)))
    F["s"] = ImageFont.truetype(FD_ + "DejaVuSans.ttf", max(8, round(11 * k)))
    F["b"] = max(10, round(17 * k))
    F["bar"] = max(18, round(28 * k))             # 위 제목 띠 높이
    F["foot"] = max(14, round(20 * k))            # 아래 범례 띠 높이
    F["lh"] = F["n"].size + 4                      # 라벨 줄 간격


def fit(dr, text, start, width, bold=True):
    """띠 폭에 들어갈 때까지 글자 크기를 줄인다(이미 들어가면 그대로)."""
    size = start
    while True:
        ft = ImageFont.truetype(FD_ + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)
        if dr.textlength(text, font=ft) <= width or size <= 8:
            return ft
        size -= 1


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


TIMES = []


def render(cam, res, hide, path):
    for o in OBJ:
        o.hide_render = o.name in hide
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    dt = round(time.time() - t, 1)
    TIMES.append(dt)
    if len(TIMES) == 1:
        # V2가 가장 가볍다(화면 대부분이 배경). 측정한 전체/첫 렌더 비율: review 6.6, original 7.5
        print(f"FIRST RENDER {dt:.1f}s (V2, 장면 동기화·BVH 포함) → 전체 4장 예상 ≈ {6.6 * dt:.0f}~{7.5 * dt:.0f}s "
              f"(측정 비율 6.6~7.5×, 로드 {T_LOADED - T_START:.1f}s 별도)", flush=True)
    set_fonts(res[0])
    return dt


def label_objects(im, cam, skip=(), only=None):
    """보이는 메시 객체 이름을 bbox 중심(화면 안으로 당김)에 붙인다. only가 있으면 그 객체만(클리핑 뷰용)."""
    dr = ImageDraw.Draw(im)
    W, H = im.size
    ft, lh, top, foot = F["n"], F["lh"], F["bar"], F["foot"]
    dg = bpy.context.evaluated_depsgraph_get()
    items = []
    for o in OBJ:
        if o.type != 'MESH' or o.hide_render or o.name in skip or (only is not None and o.name not in only):
            continue
        ev = o.evaluated_get(dg)
        pts = [to_px(cam, o.matrix_world @ Vector(c), W, H) for c in ev.bound_box]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = max(min(xs), 0), min(max(xs), W), max(min(ys), top + 2), min(max(ys), H - foot - 2)
        if x0 >= x1 or y0 >= y1:
            continue                                   # 화면 밖
        items.append((o.name, tag(o), (x0 + x1) / 2, (y0 + y1) / 2))
    placed = []
    for nm, (e, fm), x, y in sorted(items, key=lambda t: t[3]):
        txt = f"{nm}  E:{e} F:{fm}"
        col = TAGC.get(fm, TAGC["U"])
        tw = dr.textlength(txt, font=ft)
        tx = min(max(x + 8, 4), W - tw - 6); ty = min(max(y - lh // 2, top + 8), H - foot - lh - 3)
        for _ in range(40):
            if not any(abs(ty - py) < lh and tx < px + pw + 4 and px < tx + tw + 4 for px, py, pw in placed):
                break
            ty += lh
        placed.append((tx, ty, tw))
        dr.line((x, y, tx, ty + lh // 2 - 1), fill=col)
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col, outline=(0, 0, 0))
        dr.rectangle((tx - 3, ty - 1, tx + tw + 3, ty + lh - 2), fill=(0, 0, 0))
        dr.text((tx, ty), txt, font=ft, fill=col)


def grid(im, cam, h_axis, h_range, z_range):
    """정사영 입면·단면용 1 m 격자(5 m마다 진하게, 숫자). h_axis: 화면 가로가 나타내는 월드 축 벡터."""
    dr = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    fs, top, foot = F["s"], F["bar"], F["foot"]
    hv = Vector(h_axis)
    base = cam.location.copy()
    for k in range(int(h_range[0]), int(h_range[1]) + 1):
        p = base.copy(); p -= hv * base.dot(hv); p += hv * k
        x, _ = to_px(cam, p, W, H)
        major = k % 5 == 0
        dr.line((x, top, x, H - foot), fill=(255, 255, 255, 90 if major else 35), width=1)
        if major:
            dr.text((x + 2, H - foot - fs.size - 5), f"{k}", font=fs, fill=(255, 255, 255, 230))
    for z in range(int(z_range[0]), int(z_range[1]) + 1):
        p = base.copy(); p.z = z
        _, y = to_px(cam, p, W, H)
        major = z % 5 == 0
        dr.line((0, y, W, y), fill=(255, 255, 255, 90 if major else 35), width=1)
        if major or z in (-3, 7):
            dr.text((3, y - fs.size - 2), f"Z {z}", font=fs, fill=(255, 255, 255, 230))


def frame(im, title, legend=LEGEND):
    dr = ImageDraw.Draw(im)
    W, H = im.size
    top, foot = F["bar"], F["foot"]
    dr.rectangle((0, 0, W, top), fill=(0, 0, 0))
    ft = fit(dr, title, F["b"], W - 16)
    dr.text((8, (top - ft.size) // 2), title, font=ft, fill=(255, 255, 255))
    dr.rectangle((0, H - foot, W, H), fill=(0, 0, 0))
    fl = fit(dr, legend, F["n"].size, W - 16, bold=False)
    dr.text((8, H - foot + (foot - fl.size) // 2 - 1), legend, font=fl, fill=(220, 220, 220))


def scale_bar(im, ppm, metres):
    dr = ImageDraw.Draw(im)
    H = im.size[1]
    k = F["k"]
    L = metres * ppm
    bh = max(18, round(28 * k)); y0 = H - F["foot"] - bh - 4
    dr.rectangle((10, y0, 30 + L + 60 * k, y0 + bh), fill=(0, 0, 0))
    dr.line((20, y0 + bh // 2, 20 + L, y0 + bh // 2), fill=(255, 255, 255), width=3)
    dr.text((28 + L, y0 + (bh - F["n"].size) // 2 - 1), f"{metres:g} m", font=F["n"], fill=(255, 255, 255))


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


def res_of(original):
    return (RW, RH) if REVIEW else original


LOG = {"preset": ARGS.preset, "source_blend": "v0.2/mustafar_blockout_v0.2.blend", "source_sha256_before": SRC_HASH,
       "bpy_version": bpy.app.version_string, "cpu_threads_available": len(os.sched_getaffinity(0)),
       "render_settings": RENDER_SETTINGS,
       "model_changes": "없음 — 카메라 추가, hide_render, 해상도" + (", Cycles 렌더 설정" if REVIEW else "") + "만 변경. 사본은 저장하지 않음",
       "views": {}}

# ---------------------------------------------------------------- V2 시설 쪽 단면 (y = -15.5, 계단 상자 가운데)
Y_CUT = -15.5
c2 = new_cam("V2_Section_Y", (90, 0, 0), clip_start=0.001)          # +Y를 봄, 화면 오른쪽 = +X, 위 = +Z
c2.data.ortho_scale = 50.0                                           # 화면 범위 고정(해상도와 무관)
place(c2, (6.0, Y_CUT, 1.5), 0.0)
c2.location.y = Y_CUT                                                # 카메라 평면 = 자르는 면
res2 = res_of((1280, 720))
hide2 = PLACEHOLDERS + OUTLINES + ["Lava_Level_Ref", "Skiff_Check_29m_x_49m"]
raw = os.path.join(TMP, "v2.png")
t2 = render(c2, res2, hide2, raw)
im = Image.open(raw).convert("RGB")
grid(im, c2, (1, 0, 0), (-19, 31), (-12, 15))
label_objects(im, c2, only=("Landing_Platform", "Platform_Sidewalls", "Stairwell", "Stairwell_Lit_Slots",
                            "Corridor_Lower_Walkway", "Hangar_Walls", "Structural_Pillars", "Hangar_Roof",
                            "Hangar_Spotlights", "Facility_Body_Unknown"))
frame(im, f"V2 Section at Y = {Y_CUT} m (through stairwell), looking +Y (toward cliff)   +X right = facility   1 m grid")
out2 = os.path.join(OUT, "V2_section_facility_side.png"); im.save(out2)
LOG["views"]["V2"] = dict(file=os.path.basename(out2), seconds=t2, **cam_record(
    c2, res2, hide2, f"카메라 평면 y = {Y_CUT}에서 clip_start 0.001 m — 그보다 앞(−Y)은 잘림. 잘린 면은 채워지지 않아 속이 보일 수 있음. 자른 면 뒤의 구조는 입면으로 보임"))

# ---------------------------------------------------------------- V3 시설 벽 정면 (판 쪽에서 +X를 봄)
X_CLIP = 14.85                                                       # 판 가장자리(14.5)와 트렌치 안쪽 벽(14.5~14.8) 바로 바깥
c3 = new_cam("V3_Facility_Front_X", (90, 0, -90), clip_start=0.001)  # +X를 봄, 화면 오른쪽 = −Y(판 앞), 위 = +Z
c3.data.ortho_scale = 50.0
place(c3, (X_CLIP, 0.5, 2.0), 0.0)
c3.location.x = X_CLIP
res3 = res_of((1280, 720))
hide3 = PLACEHOLDERS + OUTLINES + ["Lava_Level_Ref", "Skiff_Check_29m_x_49m"]
raw = os.path.join(TMP, "v3.png")
t3 = render(c3, res3, hide3, raw)
im = Image.open(raw).convert("RGB")
grid(im, c3, (0, -1, 0), (-25, 25), (-12, 15))
label_objects(im, c3, only=("Corridor_Lower_Walkway", "Hangar_Walls", "Structural_Pillars", "Hangar_Roof",
                            "Hangar_Spotlights", "Facility_Body_Unknown"))
frame(im, f"V3 Facility front elevation, looking +X from X = {X_CLIP} m   left = +Y (cliff/back), right = -Y (front)   1 m grid, numbers = -Y")
out3 = os.path.join(OUT, "V3_facility_wall_front.png"); im.save(out3)
LOG["views"]["V3"] = dict(file=os.path.basename(out3), seconds=t3, **cam_record(
    c3, res3, hide3, f"카메라 평면 x = {X_CLIP}에서 clip_start 0.001 m — 판(x ≤ 14.5), 계단 상자, 가장자리 등, 트렌치 안쪽 벽(x 14.5~14.8)은 잘려 보이지 않음. 트렌치 바닥(Z −3)과 벽 밑동이 보이게 하려는 것. 격자 숫자는 −Y 값(오른쪽이 +)"))

# ---------------------------------------------------------------- V4 게임 축척 부분 확대 (경사로-계단 상자-시설 모퉁이)
iso = OBJ["Isometric_View"]
c4 = new_cam("V4_Game_Scale_Crop", tuple(math.degrees(a) for a in iso.rotation_euler))
res4 = res_of((1536, 864))
c4.data.ortho_scale = res4[0] / GAME_PPM                             # 게임 축척 고정 → 해상도를 줄이면 보이는 범위가 좁아짐
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
out4 = os.path.join(OUT, "V4_game_scale_crop.png"); im.save(out4)
LOG["views"]["V4"] = dict(file=os.path.basename(out4), seconds=t4, center_m=[round(v, 2) for v in ctr],
                          center_basis="Stairwell·Ramp_Foot_Measured·Ref_ObiWan·Ref_Anakin·Ref_Padme bbox 꼭짓점 평균(z=0)",
                          **cam_record(c4, res4, hide4))

# ---------------------------------------------------------------- V5 지붕 숨긴 게임 투영 (isometric_view와 같은 카메라)
c5 = new_cam("V5_Game_No_Roof", tuple(math.degrees(a) for a in iso.rotation_euler))
c5.data.ortho_scale = iso.data.ortho_scale
c5.location = iso.location.copy()
res5 = res_of((1280, 720))
hide5 = ROOF
raw = os.path.join(TMP, "v5.png")
t5 = render(c5, res5, hide5, raw)
im = Image.open(raw).convert("RGB")
frame(im, f"V5 Game projection, roof / eave lights / facility body hidden  (same camera as isometric_view.png, {res5[0] / c5.data.ortho_scale:.1f} px/m)  - no labels")
scale_bar(im, res5[0] / c5.data.ortho_scale, 10)
out5 = os.path.join(OUT, "V5_game_iso_no_roof.png"); im.save(out5)
LOG["views"]["V5"] = dict(file=os.path.basename(out5), seconds=t5, camera_basis="v0.2 Isometric_View 카메라의 위치·회전·ortho_scale 복사",
                          **cam_record(c5, res5, hide5))

# ---------------------------------------------------------------- 마무리: 원본 무변경 확인, 사본 삭제(저장 안 함)
LOG["timing_s"] = {"import_and_load": round(T_LOADED - T_START, 1), "renders": TIMES, "renders_total": round(sum(TIMES), 1),
                   "wall_total": round(time.time() - T_START, 1)}
LOG["peak_rss_mb"] = rss_mb()
LOG["source_sha256_after"] = sha256(SRC)
LOG["source_unchanged"] = LOG["source_sha256_after"] == SRC_HASH
with open(os.path.join(OUT, "render_log.json"), "w", encoding="utf-8") as f:
    json.dump(LOG, f, ensure_ascii=False, indent=2)
shutil.rmtree(TMP, ignore_errors=True)
print("EXTRA RENDERS OK", ARGS.preset, {k: v["seconds"] for k, v in LOG["views"].items()},
      LOG["timing_s"], "peak_rss_mb =", LOG["peak_rss_mb"], "source_unchanged =", LOG["source_unchanged"])
if not LOG["source_unchanged"]:
    sys.exit(2)
