"""CR-009 제출 렌더: 가장 설명력 좋은 후보(A3b)와 대안(A3)을 같은 카메라로 나란히. 영화 없는 판 + 영화 50% 겹침(비공개).
카메라: iso(게임 투영 Isometric_View), top(위, 출입구 주변), c11748(출입구 점만 맞춘 국소 카메라 f 2400을 각 후보 출입구에 붙임),
        c11726((0, −6.7) 계열, 출입구 뺀 맞춤 — 후보별), c11246(상자·등 맞춤 — 후보별), c11615(v0.2 R2 고정)
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/compare_cr009.py <4K 원본 폴더> <영화 없는 출력> <영화 출력(비공개)>"""
import json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
NAMES = ["A3b", "A3"]
if "--inner" not in sys.argv:
    import subprocess
    FR, OUT_N, OUT_F = sys.argv[1:4]
    for d in (OUT_N, OUT_F): os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cr009_")
    for n in NAMES: shutil.copy2(os.path.join(ROOT, "v0.3", "work", "layouts", f"layout_{n}.blend"), os.path.join(tmp, n + ".blend"))
    r = subprocess.run([os.path.join(ROOT, ".venv-bpy", "bin", "python"), os.path.abspath(__file__), "--inner", tmp, FR, OUT_N, OUT_F], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    shutil.rmtree(tmp, ignore_errors=True); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

i = sys.argv.index("--inner"); TMP, FR, OUT_N, OUT_F = sys.argv[i + 1:i + 5]
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8")); LAYS = D["v03"]["entrance_layout"]["candidates"]
CAMS = json.load(open(os.path.join(EV, "measure", "m13_cams.json"), encoding="utf-8"))
L48 = [c for c in CAMS["11748_local"] if c["f"] == 2400][0]["cam_local"]
DESC = {"iso": "아이소메트릭 전체(게임 투영 30°/45°)", "top": "위에서(출입구 주변)", "c11748": "11748 구도 — 출입구 점만 맞춘 카메라(f 2400)",
        "c11726": "11726 구도 — 출입구 뺀 맞춤((0, −6.7) 계열)", "c11246": "11246 구도 — 상자·등 맞춤", "c11615": "11615 구도 — v0.2 R2 고정 카메라"}
FRAMES = {"c11748": 11748, "c11726": 11726, "c11246": 11246, "c11615": 11615}


def setup(res):
    sc = bpy.context.scene; c = sc.cycles; c.samples = 12; c.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = res[0], res[1], 100
    for o in bpy.data.objects: o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref") or o.name.startswith("Hypothesis_")
    return sc


def ypcam(name, cd):
    c = bpy.data.cameras.new(name); c.sensor_fit = 'HORIZONTAL'; c.sensor_width = 36.0; c.lens = cd["f"] * 36.0 / 3840; c.clip_start = 0.05; c.clip_end = 2000
    o = bpy.data.objects.new(name, c); bpy.context.scene.collection.objects.link(o); o.location = cd["xyz"]
    y, p = math.radians(cd["yaw_deg"]), math.radians(cd["pitch_deg"])
    o.rotation_euler = Vector((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))).to_track_quat('-Z', 'Y').to_euler(); return o


def topcam():
    c = bpy.data.cameras.new("TOP"); c.type = 'ORTHO'; c.ortho_scale = 22.0; o = bpy.data.objects.new("TOP", c); bpy.context.scene.collection.objects.link(o)
    o.location = (13.0, -18.5, 60.0); return o


def label(im, t):
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, im.width, 28), fill=(0, 0, 0)); dr.text((6, 3), t.replace("−", "-"), font=FT, fill=(255, 255, 255)); return im


def film(n, size):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize(size)
    a = np.power(np.asarray(im).astype(float) / 255, 0.6); return Image.fromarray((a * 255).astype("uint8"))


rend = {}
for n in NAMES:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, n + ".blend")); L = LAYS[n]; xe, ey = L["front_x"], L["center_y"]; cc = CAMS["candidates"][n]
    cams = {"iso": (bpy.data.objects["Isometric_View"], (1280, 720)), "top": (topcam(), (1000, 1000)),
            "c11748": (ypcam("C48", {"xyz": [xe + L48["xyz"][0], ey + L48["xyz"][1], L48["xyz"][2]], "yaw_deg": L48["yaw_deg"], "pitch_deg": L48["pitch_deg"], "f": L48["f"]}), (1280, 533)),
            "c11726": (ypcam("C26", [c for c in cc["11726"] if c["family_spots_AB"] == [0.0, -6.7]][0]["cam"]), (1280, 533)),
            "c11246": (ypcam("C46", min(cc["11246"], key=lambda q: q["rms_weighted"])["cam"]), (1280, 533)),
            "c11615": (bpy.data.objects["Perspective_View_R2_match"], (1280, 533))}
    for k, (cam, res) in cams.items():
        sc = setup(res)
        if k == "top":
            for nm in ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder"):
                if nm in bpy.data.objects: bpy.data.objects[nm].hide_render = True
        sc.camera = cam; p = os.path.join(TMP, f"{n}_{k}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); rend[(n, k)] = Image.open(p).convert("RGB")
for k in DESC:
    a, b = rend[("A3b", k)], rend[("A3", k)]
    if k == "top":
        sh = Image.new("RGB", (a.width * 2, a.height)); sh.paste(label(a, f"A3b(설명력 최선) — {DESC[k]}"), (0, 0)); sh.paste(label(b, f"A3(대안) — {DESC[k]}"), (a.width, 0))
    else:
        sh = Image.new("RGB", (a.width, a.height * 2)); sh.paste(label(a, f"A3b(설명력 최선) — {DESC[k]}"), (0, 0)); sh.paste(label(b, f"A3(대안) — {DESC[k]}"), (0, a.height))
    sh.save(os.path.join(OUT_N, f"V_{k}.png"))
    if k in FRAMES:
        fm = film(FRAMES[k], a.size); sh = Image.new("RGB", (a.width, a.height * 3))
        sh.paste(label(fm.copy(), f"4K {FRAMES[k]}"), (0, 0)); sh.paste(label(Image.blend(fm, a, 0.5), f"A3b × {DESC[k]} — 영화 50%"), (0, a.height))
        sh.paste(label(Image.blend(fm, b, 0.5), f"A3 × {DESC[k]} — 영화 50%"), (0, a.height * 2)); sh.save(os.path.join(OUT_F, f"F_{k}.png"))
print("OUT views", len(DESC))
