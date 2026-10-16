"""CR-007: A3(+R 가설)가 11615·11246의 기존 관찰과 충돌하는지 확인한다. 후보 .blend는 임시 사본으로 열고 저장하지 않는다.
  - 11615: v0.2 기준안 R2 고정 카메라(Perspective_View_R2_match). A3에서 새로 생기거나 옮겨진 객체가 화면 어디에 투영되는지(꼭짓점 기준 화면 안 비율·범위)를 적고, H1과 같은 카메라로 나란히 렌더한다.
  - 11246: M10 카메라(상자·시설 쪽 가장자리·가장자리 등으로 맞춤 — 후보와 무관, 맞춤 RMS 약 60 px라 약한 대조). 같은 방식으로 투영·렌더한다.
트렌치 끝·출입구 뒤 공간은 UNKNOWN 철사틀 그대로 둔다. 시설 길이 축소(H2)·내부 경로 연결은 적용하지 않는다.
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/check_a3_context.py <4K 원본 폴더> <영화 없는 출력> <영화 비교 출력(비공개)> <out.json>"""
import json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
if "--inner" not in sys.argv:
    import subprocess
    FR, OUT_N, OUT_F, OUT_J = sys.argv[1:5]
    for d in (OUT_N, OUT_F): os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cr007_")
    for n in ("H1", "A3"): shutil.copy2(os.path.join(ROOT, "v0.3", "work", "layouts", f"layout_{n}.blend"), os.path.join(tmp, n + ".blend"))
    r = subprocess.run([os.path.join(ROOT, ".venv-bpy", "bin", "python"), os.path.abspath(__file__), "--inner", tmp, FR, OUT_N, OUT_F, OUT_J], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    shutil.rmtree(tmp, ignore_errors=True); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

i = sys.argv.index("--inner"); TMP, FR, OUT_N, OUT_F, OUT_J = sys.argv[i + 1:i + 6]
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
RW, RH = 1280, 533
NEW = ("Facility_A_Entrance", "Entrance_Bay_Front", "Entrance_Bay_Unknown", "Entrance_Forecourt_Floor", "Trench_End_Unknown", "R_Structure_Hypothesis", "Hangar_Walls")
M10 = json.load(open(os.path.join(EV, "measure", "m10_result.json"), encoding="utf-8"))["fits"][0]   # 11246: 상자·가장자리·등으로 맞춘 카메라(후보와 무관)


def setup(res):
    sc = bpy.context.scene; c = sc.cycles
    c.samples = 12; c.use_denoising = True; c.denoising_prefilter = 'FAST'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 4, 2, 2, 0
    sc.render.use_persistent_data = True; sc.render.resolution_percentage = 100; sc.render.resolution_x, sc.render.resolution_y = res
    for o in bpy.data.objects:
        o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref") or o.name.startswith("Hypothesis_")
    return sc


def look_cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = lens; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return co


def cam_m10():
    c = M10["cam"]; cd = bpy.data.cameras.new("M10"); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = c["f"] * 36.0 / 3840; cd.clip_start = 0.05; cd.clip_end = 2000
    co = bpy.data.objects.new("M10", cd); bpy.context.scene.collection.objects.link(co); co.location = c["xyz"]; y_, p_ = math.radians(c["yaw_deg"]), math.radians(c["pitch_deg"])
    co.rotation_euler = Vector((math.cos(p_) * math.cos(y_), math.cos(p_) * math.sin(y_), math.sin(p_))).to_track_quat('-Z', 'Y').to_euler(); return co


def proj_stats(sc, cam, names):
    out = {}
    for nm in names:
        ob = bpy.data.objects.get(nm)
        if ob is None: continue
        pts = [world_to_camera_view(sc, cam, ob.matrix_world @ v.co) for v in ob.data.vertices]
        front = [p for p in pts if p.z > 0]
        inside = [p for p in front if 0 <= p.x <= 1 and 0 <= p.y <= 1]
        rec = {"verts": len(pts), "in_frame_frac": round(len(inside) / max(1, len(pts)), 2)}
        if inside:
            xs_, ys_ = [p.x * RW for p in inside], [(1 - p.y) * RH for p in inside]
            rec["bbox_px_1280"] = [round(min(xs_)), round(min(ys_)), round(max(xs_)), round(max(ys_))]
        out[nm] = rec
    return out


def label(im, text):
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, im.width, 28), fill=(0, 0, 0)); dr.text((6, 3), text.replace("−", "-"), font=FT, fill=(255, 255, 255)); return im


def film(n):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize((RW, RH))
    a = np.power(np.asarray(im).astype(float) / 255, 0.6); return Image.fromarray((a * 255).astype("uint8"))


res, rend = {}, {}
for n in ("H1", "A3"):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, n + ".blend")); sc = setup((RW, RH))
    cams = {"11615_r2": bpy.data.objects["Perspective_View_R2_match"], "11246_m10": cam_m10()}
    res[n] = {}
    for k, cam in cams.items():
        sc.camera = cam; p = os.path.join(OUT_N, f"_{n}_{k}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); rend[(n, k)] = p
        res[n][k] = proj_stats(sc, cam, NEW)
json.dump({"note": "꼭짓점 투영 기준(가림 무시). in_frame_frac = 화면 안 꼭짓점 비율, bbox는 1280×533 기준", "cameras": {"11615_r2": "v0.2 기준안 R2 고정 카메라",
           "11246_m10": {"cam": M10["cam"], "near_lamp_y": M10["near_lamp_y"], "rms_weighted": M10["rms_weighted"]}}, "projection": res}, open(OUT_J, "w"), ensure_ascii=False, indent=1)
for k, frame, desc in (("11615_r2", 11615, "R2 고정 카메라(v0.2 기준안)"), ("11246_m10", 11246, f"M10 카메라(상자·가장자리·등, RMS {M10['rms_weighted']} px)")):
    a, b = Image.open(rend[("H1", k)]).convert("RGB"), Image.open(rend[("A3", k)]).convert("RGB")
    sh = Image.new("RGB", (RW, RH * 2)); sh.paste(label(a, f"H1 — {desc}"), (0, 0)); sh.paste(label(b, f"A3 + R 가설 — {desc}"), (0, RH)); sh.save(os.path.join(OUT_N, f"X_{k}_H1_vs_A3.png"))
    fm = film(frame); sh = Image.new("RGB", (RW, RH * 3))
    sh.paste(label(fm.copy(), f"4K {frame}"), (0, 0)); sh.paste(label(Image.blend(fm, a, 0.5), f"H1 × {desc} — 영화 50% 겹침"), (0, RH))
    sh.paste(label(Image.blend(fm, b, 0.5), f"A3 + R 가설 × {desc} — 영화 50% 겹침"), (0, RH * 2)); sh.save(os.path.join(OUT_F, f"F_{k}_H1_vs_A3.png"))
for p in rend.values(): os.remove(p)
print("OUT context", json.dumps(res["A3"]["11615_r2"], ensure_ascii=False))
