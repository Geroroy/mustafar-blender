"""CR-004 비교 카메라: v0.3 형상을 고정하고 11206에 가까운 원거리 카메라 가설 3개로 렌더한다(.blend는 임시 사본, 저장 안 함).
카메라는 맞춤이 아니라 방향 가설이다(어느 쪽에서 보았는지 미확정). 각 가설은 판 전체가 화면 폭의 약 절반을 차지하고 난간 높이가 화면 가운데쯤 오도록 잡았다.
실행: .venv-bpy/bin/python -I research/CR-001_4k_evidence/silhouette/compare_far_view.py <프레임 폴더> <영화 없는 출력 폴더> <영화 비교 출력 폴더>"""
import hashlib, json, math, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CAMS = {  # 이름: (설명, 위치, 바라보는 점, 렌즈 mm)
    "A_from_minusX": ("−X(용암 쪽)에서 +X를 봄 — 시설 긴 면이 정면", (-160.0, 0.0, 8.0), (12.0, 0.0, 3.0), 70),
    "B_from_minusY": ("−Y(앞 끝)에서 +Y를 봄 — 시설 짧은 면이 정면", (8.0, -175.0, 8.0), (8.0, 0.0, 3.0), 70),
    "C_oblique": ("−X−Y 사선(앞 왼쪽)에서 봄", (-115.0, -120.0, 9.0), (8.0, 0.0, 3.0), 70),
}
if "--inner" not in sys.argv:
    FR, OUT0, OUTF = sys.argv[1:4]
    for d in (OUT0, OUTF): os.makedirs(d, exist_ok=True)
    src = os.path.join(ROOT, "v0.3", "mustafar_blockout_v0.3.blend"); h0 = hashlib.sha256(open(src, "rb").read()).hexdigest()
    tmp = tempfile.mkdtemp(prefix="cr004_"); shutil.copy2(src, os.path.join(tmp, "v03.blend"))
    r = subprocess.run([os.path.join(ROOT, ".venv-bpy", "bin", "python"), os.path.abspath(__file__), "--inner", tmp, FR, OUT0, OUTF], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    print("v0.3 .blend 무변경:", h0 == hashlib.sha256(open(src, "rb").read()).hexdigest()); shutil.rmtree(tmp, ignore_errors=True); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
i = sys.argv.index("--inner"); TMP, FR, OUT0, OUTF = sys.argv[i + 1:i + 5]
bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, "v03.blend")); sc = bpy.context.scene; c = sc.cycles
c.samples = 12; c.use_denoising = True; c.denoising_prefilter = 'FAST'; c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 4, 2, 2, 0
sc.render.use_persistent_data = True; sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 533, 100
for o in bpy.data.objects:
    o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref", "Skiff_Check_29m_x_49m", "Ramp_Foot_Measured", "Ref_ObiWan", "Ref_Anakin", "Ref_Padme")
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
film = Image.open(os.path.join(FR, "11206.jpg")).convert("RGB").resize((1280, 533))
a = np.power(np.asarray(film).astype(float) / 255, 0.6); film = Image.fromarray((a * 255).astype("uint8"))


def label(im, t):
    d = ImageDraw.Draw(im); d.rectangle((0, 0, im.width, 28), fill=(0, 0, 0)); d.text((6, 3), t, font=FT, fill=(255, 255, 255)); return im


rows = [label(film.copy(), "4K 11206 (우주선 창밖 원거리)")]
meta = {}
for name, (desc, loc, tgt, lens) in CAMS.items():
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = lens; cd.clip_end = 5000
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = loc
    co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); sc.camera = co
    p = os.path.join(OUT0, f"FAR_{name}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    im = label(Image.open(p).convert("RGB"), f"v0.3 고정 형상 — 가설 {name}: {desc} ({lens} mm)"); im.save(p); rows.append(im)
    meta[name] = {"desc": desc, "loc": loc, "target": tgt, "lens_mm": lens}
    print("OUT", name)
sheet = Image.new("RGB", (1280, 533 * len(rows)))
for j, r in enumerate(rows): sheet.paste(r, (0, j * 533))
sheet.save(os.path.join(OUTF, "C_11206_vs_v03_cameras.png"))
json.dump(meta, open(os.path.join(HERE, "far_view_cameras.json"), "w"), ensure_ascii=False, indent=1)
print("OUT sheet")
