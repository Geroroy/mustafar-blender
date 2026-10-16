"""CR-007: A3(출입구 h 2.4·w 1.45, 상자 1.2 m 기준 형상)의 두 영화 구도 전체 대응점 표시. M9에서 형상을 고정하고 맞춘 카메라로 렌더하고,
관측점(초록 원)과 모델 투영점(빨강 ×)을 잇는 선으로 원시 오차를 보인다. 평가 전용 점(끝 단 발치 등)은 노랑.
  - 영화 없는 판: 모델 렌더 위에 표시(관측점은 좌표만) → chatgpt_reviews/
  - 영화 판: 4K 영화 위에 표시 → _private/
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/plot_a3_points.py <4K 원본 폴더> <영화 없는 출력> <영화 출력(비공개)>"""
import json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
if "--inner" not in sys.argv:
    import subprocess
    FR, OUT_N, OUT_F = sys.argv[1:4]
    for d in (OUT_N, OUT_F): os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cr007p_"); shutil.copy2(os.path.join(ROOT, "v0.3", "work", "layouts", "layout_A3.blend"), os.path.join(tmp, "A3.blend"))
    r = subprocess.run([os.path.join(ROOT, ".venv-bpy", "bin", "python"), os.path.abspath(__file__), "--inner", tmp, FR, OUT_N, OUT_F], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    shutil.rmtree(tmp, ignore_errors=True); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
sys.path.insert(0, os.path.join(EV, "measure"))
import m9_a3_shape_fit as m  # noqa: E402

i = sys.argv.index("--inner"); TMP, FR, OUT_N, OUT_F = sys.argv[i + 1:i + 5]
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
RW, RH, K = 1280, 533, 1280 / 3840
M9 = json.load(open(os.path.join(EV, "measure", "m9_result.json"), encoding="utf-8"))
ROW = [r for r in M9["rows"] if r["shape"] == {"light_center_h": 2.4, "width": 1.45}][0]
H, Wd = 2.4, 1.45


def cvec(cd):
    return np.array([*cd["xyz"], math.radians(cd["yaw_deg"]), math.radians(cd["pitch_deg"]), cd["f"]])


def render(c, name):
    sc = bpy.context.scene; cy = sc.cycles; cy.samples = 12; cy.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
    for o in bpy.data.objects: o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref") or o.name.startswith("Hypothesis_")
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = c[5] * 36.0 / 3840; cd.clip_start = 0.05; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = tuple(c[:3])
    fwd = Vector((math.cos(c[4]) * math.cos(c[3]), math.cos(c[4]) * math.sin(c[3]), math.sin(c[4]))); co.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co; p = os.path.join(TMP, name + ".png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    return Image.open(p).convert("RGB")


def pairs48(c):
    P = m.ent(H, Wd); out = []
    for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"): out.append((k, m.O48[k], P[k], "fit"))
    out.append(("boxL_rim_minusY_end", m.O48["boxL_rim_minusY_end"], (m.HX0 - 0.06, m.HY0, m.PH), "fit"))
    out.append(("boxL_end_tier_foot", m.O48["boxL_end_tier_foot"], (m.HX1, m.YEND, 0.0), "eval"))
    return out, [("threshold_line", m.O48["threshold_line"], ((m.XE - m.XF0, m.EYC + 1, 0), (m.XE - m.XF0, m.EYC - 1, 0))),
                 ("boxL_base_line", m.O48["boxL_base_line"], ((m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, m.HY0, 0)))]


def pairs26(fam):
    P = m.ent(H, Wd); out = [("eave_light_A", m.O26["eave_light_A"], (m.SPOT_X, fam[0], m.SPOT_Z), "fit"), ("eave_light_B", m.O26["eave_light_B"], (m.SPOT_X, fam[1], m.SPOT_Z), "fit"),
                             ("box_rim_minusY_end", m.O26["box_rim_minusY_end"], (m.HX0 - 0.06, m.HY0, m.PH), "fit"),
                             ("door_light", m.O26["door_light"], P["door_light"], "fit"), ("door_outer_base_minusY", m.O26["door_outer_base_minusY"], P["door_outer_base_minusY"], "fit"),
                             ("box_end_tier_foot", m.O26["box_end_tier_foot"], (m.HX0 - 0.06, m.YEND, 0.0), "eval")]
    return out, [("box_rim_line", m.O26["box_rim_line"], ((m.HX0 - 0.06, m.HY1, m.PH), (m.HX0 - 0.06, m.HY0, m.PH))),
                 ("box_base_line", m.O26["box_base_line"], ((m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, m.HY0, 0))),
                 ("deck_edge_line", m.O26["deck_edge_line"], ((m.X1, 10.0, 0), (m.X1, -5.0, 0)))]


def draw(im, c, pts, lines, title):
    im = im.copy(); dr = ImageDraw.Draw(im)
    for name, (o, a, b) in [(n, (o, a, b)) for n, o, (a, b) in lines]:
        pa, pb = m.proj(a, c)[0] * K, m.proj(b, c)[0] * K
        d_ = pb - pa; pa2, pb2 = pa - d_ * 3, pb + d_ * 3
        dr.line([tuple(pa2), tuple(pb2)], fill=(255, 80, 80), width=2)
        for q in o:
            x, y = q[0] * K, q[1] * K; dr.ellipse((x - 6, y - 6, x + 6, y + 6), outline=(60, 255, 90), width=3)
    for name, o, p, kind in pts:
        q = m.proj(p, c)[0] * K; x, y = o[0] * K, o[1] * K; col = (60, 255, 90) if kind == "fit" else (255, 230, 60)
        dr.ellipse((x - 7, y - 7, x + 7, y + 7), outline=col, width=3)
        dr.line((q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7), fill=(255, 60, 60), width=3); dr.line((q[0] - 7, q[1] + 7, q[0] + 7, q[1] - 7), fill=(255, 60, 60), width=3)
        dr.line((x, y, q[0], q[1]), fill=(255, 255, 255), width=1)
        e = float(np.linalg.norm(m.proj(p, c)[0] - np.array(o)))
        dr.text((x + 9, y - 9), f"{name} {e:.0f}px", font=FT, fill=col)
    dr.rectangle((0, 0, im.width, 26), fill=(0, 0, 0)); dr.text((6, 3), title.replace("−", "-"), font=FT, fill=(255, 255, 255))
    dr.rectangle((0, im.height - 24, im.width, im.height), fill=(0, 0, 0))
    dr.text((6, im.height - 22), "초록 원 = 영화 관측(맞춤에 씀), 노랑 원 = 평가 전용, 빨강 × = 모델 투영, 빨강 선 = 모델 직선(상자 밑변·문턱 등). 4K px 오차", font=FT, fill=(230, 230, 230))
    return im


def film(n):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize((RW, RH))
    a = np.power(np.asarray(im).astype(float) / 255, 0.6); return Image.fromarray((a * 255).astype("uint8"))


bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, "A3.blend"))
c48 = cvec(ROW["11748"]["cam"]); pts, lines = pairs48(c48)
r48 = render(c48, "M9_11748")
t48 = f"11748 — A3(h 2.4, w 1.45, 상자 1.2 m) 형상 고정·카메라만 맞춤(M9, f {ROW['11748']['cam']['f']} = 상한)"
draw(r48, c48, pts, lines, t48).save(os.path.join(OUT_N, "E_11748_A3_points.png")); draw(film(11748), c48, pts, lines, t48).save(os.path.join(OUT_F, "E_11748_A3_points_film.png"))
for fam in ((0.0, -6.7), (6.7, 0.0)):
    fr = [x for x in ROW["11726"] if x["family_spots_AB"] == list(fam) and x["door_in_fit"]][0]
    c26 = cvec(fr["cam"]); pts, lines = pairs26(fam); r26 = render(c26, f"M9_11726_{fam[0]}")
    t26 = f"11726 — A3 형상 고정·카메라만 맞춤(M9, 처마 조명 계열 {list(fam)}, 출입구 포함, f {fr['cam']['f']})"
    tag = "fam_0_m6.7" if fam[0] == 0.0 else "fam_6.7_0"
    draw(r26, c26, pts, lines, t26).save(os.path.join(OUT_N, f"E_11726_A3_points_{tag}.png")); draw(film(11726), c26, pts, lines, t26).save(os.path.join(OUT_F, f"E_11726_A3_points_{tag}_film.png"))
print("OUT points 3")
