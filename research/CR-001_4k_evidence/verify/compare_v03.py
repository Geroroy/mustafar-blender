"""CR-002 비교 렌더. .blend는 임시 사본으로 열고 저장하지 않는다(원본 SHA256 전후 비교).
실행 (저장소 루트):
  .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/compare_v03.py <4K 원본 폴더> <수정 전 v0.3 .blend> [수정 후 .blend] [전후 출력 폴더] [영화 출력 폴더]
출력:
  ① 같은 카메라 전후 비교(영화 없음, 순수 렌더) → chatgpt_reviews/CR-002_v0.3/before_after/
  ② 영화 비교(11615 겹침, 11748·11246·11712·11625 나란히) → research/CR-001_4k_evidence/_private/cr002r2_film/  (Git 제외)
카메라: R2 고정 카메라(v0.2 기준안), 게임 투영(Isometric_View), 위(Top_View), 근사 카메라 4개(정성 비교용, 치수 검증 아님)."""
import hashlib, json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
if "--inner" not in sys.argv:
    import subprocess
    PY = os.path.join(ROOT, ".venv-bpy", "bin", "python"); FR = sys.argv[1]
    src = {"before": sys.argv[2], "after": sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else os.path.join(ROOT, "v0.3", "mustafar_blockout_v0.3.blend")}
    OUT_BA = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, "chatgpt_reviews", "CR-002_v0.3", "before_after")
    OUT_F = sys.argv[5] if len(sys.argv) > 5 else os.path.join(EV, "_private", "cr002r2_film")
    for d in (OUT_BA, OUT_F): os.makedirs(d, exist_ok=True)
    h0 = {k: hashlib.sha256(open(p, "rb").read()).hexdigest() for k, p in src.items()}
    tmp = tempfile.mkdtemp(prefix="cr002r2_")
    for k, p in src.items(): shutil.copy2(p, os.path.join(tmp, k + ".blend"))
    r = subprocess.run([PY, os.path.abspath(__file__), "--inner", tmp, FR, OUT_BA, OUT_F], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    h1 = {k: hashlib.sha256(open(p, "rb").read()).hexdigest() for k, p in src.items()}
    shutil.rmtree(tmp, ignore_errors=True); print("입력 .blend 무변경:", h0 == h1); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

i = sys.argv.index("--inner"); TMP, FR, OUT_BA, OUT_F = sys.argv[i + 1:i + 5]
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
RW, RH = 1280, 533
APPROX = [  # (프레임, 내용, 위치, 바라보는 점, 렌즈 mm) — 근사 카메라, 정성 비교
    (11748, "출입구·겹친 테두리·상자·연석", (9.0, -21.5, 1.5), (22.5, -16.0, 1.6), 28),
    (11246, "상자 안 하강 계단·바깥 경사 패널", (5.0, -6.0, 1.7), (12.8, -15.0, 0.0), 30),
    (11712, "바닥 판재(위에서)", (2.0, -9.0, 16.0), (2.0, -7.0, 0.0), 24),
    (11625, "뒤쪽 기둥·난간(반대 방향)", (8.0, -14.0, 1.7), (2.0, 23.0, 1.0), 30),
]


def setup(res):
    sc = bpy.context.scene; c = sc.cycles
    c.samples = 12; c.use_denoising = True; c.denoising_prefilter = 'FAST'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 4, 2, 2, 0
    sc.render.use_persistent_data = True; sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = res
    for nm in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref"):
        if nm in bpy.data.objects: bpy.data.objects[nm].hide_render = True
    return sc


def look_cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = lens; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return co


def label(im, text):
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, im.width, 28), fill=(0, 0, 0)); dr.text((6, 3), text, font=FT, fill=(255, 255, 255)); return im


def film(n, size=(RW, RH)):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize(size)
    a = np.power(np.asarray(im).astype(float) / 255, 0.65); return Image.fromarray((a * 255).astype("uint8"))


VIEWS = [("r2cam", "Perspective_View_R2_match", (RW, RH)), ("iso", "Isometric_View", (1280, 720)), ("top", "Top_View", (1280, 720))]
M5 = None
_m5 = os.path.join(EV, "measure", "m5_result.json")
if os.path.exists(_m5):
    _b = [r for r in json.load(open(_m5))["fits"] if r["geometry"] == "model"][0]
    M5 = (_b["cam"]["xyz"], math.radians(_b["cam"]["yaw_deg"]), math.radians(_b["cam"]["pitch_deg"]), _b["f"], _b["spots_AB"], _b["rms_px"])


def m5_cam():
    (x, y, z), yaw, pitch, f, _, _ = M5
    fwd = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
    return look_cam("M5_11726", (x, y, z), (x + fwd[0], y + fwd[1], z + fwd[2]), f * 36.0 / 3840)
renders = {}
for k in ("before", "after"):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, k + ".blend"))
    for nm in ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder"):
        pass
    for vn, cam_name, res in VIEWS:
        sc = setup(res); cam = bpy.data.objects[cam_name]
        hide = ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder") if vn == "top" else ()
        for o in bpy.data.objects: o.hide_render = o.name in hide or o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref")
        sc.camera = cam; p = os.path.join(OUT_BA, f"_{k}_{vn}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        renders[(k, vn)] = p
    for o in bpy.data.objects: o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref")
    sc = setup((RW, RH))
    for n, what, loc, tgt, lens in APPROX:
        cam = look_cam(f"APPROX_{n}", loc, tgt, lens); sc.camera = cam
        p = os.path.join(OUT_BA, f"_{k}_approx{n}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        renders[(k, f"approx{n}")] = p
    if M5:
        sc.camera = m5_cam(); p = os.path.join(OUT_BA, f"_{k}_m5.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        renders[(k, "m5")] = p

# ① 전후 비교 (영화 없음)
names = [v[0] for v in VIEWS] + [f"approx{a[0]}" for a in APPROX] + (["m5"] if M5 else [])
desc = {"r2cam": "R2 고정 카메라(v0.2 기준안)", "iso": "게임 투영 30°/45°", "top": "위(지붕·절벽 숨김)"}
desc.update({f"approx{a[0]}": f"근사 카메라 — {a[0]} 방향({a[1]})" for a in APPROX})
if M5: desc["m5"] = f"M5 맞춤 카메라(11726, 형상 고정, RMS {M5[5]} px, 출입구 점 제외)"
for vn in names:
    a, b = Image.open(renders[("before", vn)]).convert("RGB"), Image.open(renders[("after", vn)]).convert("RGB")
    sheet = Image.new("RGB", (a.width, a.height * 2))
    sheet.paste(label(a, f"수정 전 v0.3 (CR-002 제출본) — {desc[vn]}"), (0, 0)); sheet.paste(label(b, f"수정 후 v0.3 — {desc[vn]}"), (0, a.height))
    sheet.save(os.path.join(OUT_BA, f"BA_{vn}.png"))
for p in set(renders.values()): os.remove(p)
print("OUT before_after", len(names))

# ② 영화 비교 (Git 제외)
bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, "after.blend")); sc = setup((RW, RH))
for o in bpy.data.objects: o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref")
sc.camera = bpy.data.objects["Perspective_View_R2_match"]; p = os.path.join(OUT_F, "_r2.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
r2 = Image.open(p).convert("RGB"); os.remove(p)
sheet = Image.new("RGB", (RW, RH * 2))
sheet.paste(label(film(11615), "4K 11615 (R2와 같은 고정 카메라)"), (0, 0))
sheet.paste(label(Image.blend(film(11615), r2, 0.5), "수정 후 v0.3 × v0.2 R2 카메라 — 영화 50% 겹침 (판 크기·엇갈림 비교)"), (0, RH))
sheet.save(os.path.join(OUT_F, "F_11615_r2cam_after.png"))
for n, what, loc, tgt, lens in APPROX:
    cam = look_cam(f"APPROX_{n}", loc, tgt, lens); sc.camera = cam
    p = os.path.join(OUT_F, "_a.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    ren = Image.open(p).convert("RGB"); os.remove(p)
    sheet = Image.new("RGB", (RW, RH * 2))
    sheet.paste(label(film(n), f"4K {n} — {what}"), (0, 0))
    sheet.paste(label(ren, f"수정 후 v0.3 근사 카메라 {loc}→{tgt}, {lens} mm — 정성 비교, 절대 크기 판정 안 함"), (0, RH))
    sheet.save(os.path.join(OUT_F, f"F_{n}_film_vs_after.png"))
if M5:
    sc.camera = m5_cam(); p = os.path.join(OUT_F, "_m5.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    ren = Image.open(p).convert("RGB"); os.remove(p)
    sheet = Image.new("RGB", (RW, RH * 2))
    sheet.paste(label(film(11726), "4K 11726 (주 검증 프레임)"), (0, 0))
    sheet.paste(label(Image.blend(film(11726), ren, 0.5), f"수정 후 v0.3 × M5 맞춤 카메라(형상 고정, 출입구 점 제외) — 50% 겹침"), (0, RH))
    sheet.save(os.path.join(OUT_F, "F_11726_m5_overlay.png"))
print("OUT film", 1 + len(APPROX) + (1 if M5 else 0))
