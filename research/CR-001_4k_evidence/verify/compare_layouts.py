"""CR-006 출입구 접근 배치 후보 비교 렌더. 후보 .blend는 임시 사본으로 열고 저장하지 않는다.
실행 (저장소 루트):
  .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/compare_layouts.py <4K 원본 폴더> <영화 없는 출력 폴더> <영화 비교 출력 폴더(비공개)>
입력: v0.3/work/layouts/layout_<후보>.blend (MUSTAFAR_LAYOUT=<후보>로 생성), measure/m5_result.json, measure/m8_result.json, verify/access_<후보>.json
카메라:
  - plan: 위에서 본 정사영(출입구 주변, 지붕·처마 조명·몸체·절벽 숨김)
  - c11726: M5 카메라(처마 조명·상자·바닥선으로 맞춤, 출입구 제외 — 후보와 무관). 1순위 해와 (0, −6.7) 쌍 f 2800 해
  - c11748: M8 카메라(11748 출입구 점만으로 맞춤, f 2600, 출입구 국소 좌표) → 후보마다 그 출입구에 붙여 놓음. 출입구는 화면의 같은 자리에 오고 상자 위치 차이만 보인다
모든 카메라는 후보 사이에서 바꾸지 않는다(형상만 바뀜). 근사·맞춤 카메라라 크기 판정에 쓰지 않는다."""
import json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
NAMES = ["H1", "A1", "A2", "A3"]
if "--inner" not in sys.argv:
    import subprocess
    FR, OUT_N, OUT_F = sys.argv[1:4]
    for d in (OUT_N, OUT_F): os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cr006_")
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
RW, RH = 1280, 533
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
LAYS = D["v03"]["entrance_layout"]["candidates"]
XW = D["platform"]["facility_edge_x"]["value"] + D["facility"]["trench_gap"]["value"]
M5 = [x for x in json.load(open(os.path.join(EV, "measure", "m5_result.json")))["fits"] if x["geometry"] == "model"]
M5_USE = [M5[0]] + [x for x in M5 if x["spots_AB"] == [0.0, -6.7] and x["f"] == 2800][:1]
M8 = [r for r in json.load(open(os.path.join(EV, "measure", "m8_result.json")))["test3_relative_placement"] if r["f"] == 2600][0]
HIDE = ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref")


def setup(res):
    sc = bpy.context.scene; c = sc.cycles
    c.samples = 12; c.use_denoising = True; c.denoising_prefilter = 'FAST'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 4, 2, 2, 0
    sc.render.use_persistent_data = True; sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = res
    return sc


def cam_yaw_pitch(name, xyz, yaw, pitch, f):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = f * 36.0 / 3840; cd.clip_start = 0.05; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co); co.location = xyz
    fwd = Vector((math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)))
    co.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler(); return co


def plan_cam():
    cd = bpy.data.cameras.new("PLAN"); cd.type = 'ORTHO'; cd.ortho_scale = 30.0; cd.clip_end = 500
    co = bpy.data.objects.new("PLAN", cd); bpy.context.scene.collection.objects.link(co); co.location = (11.0, -15.5, 60.0); co.rotation_euler = (0, 0, 0)
    return co


def label(im, text):
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, im.width, 28), fill=(0, 0, 0)); dr.text((6, 3), text.replace("−", "-"), font=FT, fill=(255, 255, 255)); return im   # 글꼴에 − 없음


def film(n, size=(RW, RH)):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize(size)
    a = np.power(np.asarray(im).astype(float) / 255, 0.6); return Image.fromarray((a * 255).astype("uint8"))


views = {}
for n in NAMES:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, n + ".blend"))
    L = LAYS[n]; xe = L.get("front_x") or XW; ey = L["center_y"]
    for o in bpy.data.objects:
        o.hide_render = o.name in HIDE or o.name.startswith("Hypothesis_")
    sc = setup((1000, 1000))
    for nm in ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder"):
        if nm in bpy.data.objects: bpy.data.objects[nm].hide_render = True
    sc.camera = plan_cam(); p = os.path.join(OUT_N, f"_{n}_plan.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); views[(n, "plan")] = p
    for nm in ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder"):
        if nm in bpy.data.objects: bpy.data.objects[nm].hide_render = False
    sc = setup((RW, RH))
    for k, fit in enumerate(M5_USE):
        c = fit["cam"]; sc.camera = cam_yaw_pitch(f"M5_{k}", c["xyz"], math.radians(c["yaw_deg"]), math.radians(c["pitch_deg"]), fit["f"])
        p = os.path.join(OUT_N, f"_{n}_c11726_{k}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); views[(n, f"c11726_{k}")] = p
    cl = M8["cam_local"]; xyz = (xe + cl["xyz"][0], ey + cl["xyz"][1], cl["xyz"][2])
    sc.camera = cam_yaw_pitch("M8_11748", xyz, math.radians(cl["yaw_deg"]), math.radians(cl["pitch_deg"]), M8["f"])
    p = os.path.join(OUT_N, f"_{n}_c11748.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); views[(n, "c11748")] = p

ACC = {n: json.load(open(os.path.join(HERE, f"access_{n}.json"))) for n in NAMES}


def acc_txt(n):
    a = ACC[n]
    if not a["reachable_without_crossing_box"]: return "문 앞 접근: 불가(상자를 지나야 함)"
    return f"문 앞 접근 최소 여유 {a['approach']['min_clear_width_m']} m, 문틀 안쪽까지 {a['inside']['min_clear_width_m']} m (바닥 연결 검사값)"


DESC = {"plan": "위에서(출입구 주변)", "c11726_0": f"11726 구도 — M5 1순위 해(조명 {M5_USE[0]['spots_AB']}, f {M5_USE[0]['f']})",
        "c11748": f"11748 구도 — M8 카메라(출입구 점만으로 맞춤, f {M8['f']})"}
if len(M5_USE) > 1: DESC["c11726_1"] = f"11726 구도 — M5 해(조명 {M5_USE[1]['spots_AB']}, f {M5_USE[1]['f']})"
for vn in DESC:
    ims = [Image.open(views[(n, vn)]).convert("RGB") for n in NAMES]
    w, h = ims[0].size
    if vn == "plan":
        sheet = Image.new("RGB", (w * 2, h * 2))
        for k, (n, im) in enumerate(zip(NAMES, ims)):
            sheet.paste(label(im, f"후보 {n} — {acc_txt(n)}"), ((k % 2) * w, (k // 2) * h))
    else:
        sheet = Image.new("RGB", (w, h * 4))
        for k, (n, im) in enumerate(zip(NAMES, ims)):
            sheet.paste(label(im, f"후보 {n} — {DESC[vn]}"), (0, k * h))
    sheet.save(os.path.join(OUT_N, f"L_{vn}.png"))
print("OUT no_film", len(DESC))

# 영화 비교(비공개): 후보마다 영화 50% 겹침
for vn, frame in (("c11726_0", 11726), ("c11726_1", 11726), ("c11748", 11748)):
    if vn not in DESC: continue
    fm = film(frame); rows = [label(fm.copy(), f"4K {frame}")]
    for n in NAMES:
        ren = Image.open(views[(n, vn)]).convert("RGB")
        rows.append(label(Image.blend(fm, ren, 0.5), f"후보 {n} × {DESC[vn]} — 영화 50% 겹침"))
    sheet = Image.new("RGB", (RW, RH * len(rows)))
    for k, im in enumerate(rows): sheet.paste(im, (0, k * RH))
    sheet.save(os.path.join(OUT_F, f"F_{vn}_candidates.png"))
for p in set(views.values()): os.remove(p)
print("OUT film 3")
