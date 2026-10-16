"""CR-008: 낮은 상자 −Y 끝 형태 국소 수정의 같은 카메라 전후 비교. 전 = 수정 전 A3 사본(_private/v03_pre_endform), 후 = 현재 A3.
카메라(전후 동일):
  - lowbox_close: 근접 카메라(CR-005와 같은 값), top: 위에서
  - pre_*: 수정 전 형상(이전 대응)으로 맞춘 카메라(CR-007 M9·M10) — 전 쪽에 유리
  - post_*: 수정 후 형상(부위별 대응)으로 맞춘 카메라(M12, 선택한 끝 형태) — 후 쪽에 유리
  (끝 형태 점을 뺀 M11 카메라는 상자 길이 방향 제약이 없어 끝 부위 오차가 수백~수천 px로 나와 쓰지 않음)
끝 부위 대응점(P1~P5)의 원시 오차를 전(이전 대응: 모두 끝 벽 모서리·끝 단 끝)과 후(부위별 대응)로 계산해 JSON에 적는다.
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/compare_endform.py <4K 원본 폴더> <영화 없는 출력> <영화 출력(비공개)> <out.json>"""
import json, math, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
if "--inner" not in sys.argv:
    import subprocess
    FR, OUT_N, OUT_F, OUT_J = sys.argv[1:5]
    for d in (OUT_N, OUT_F): os.makedirs(d, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cr008_")
    shutil.copy2(os.path.join(EV, "_private", "v03_pre_endform", "layout_A3.blend"), os.path.join(tmp, "before.blend"))
    shutil.copy2(os.path.join(ROOT, "v0.3", "work", "layouts", "layout_A3.blend"), os.path.join(tmp, "after.blend"))
    r = subprocess.run([os.path.join(ROOT, ".venv-bpy", "bin", "python"), os.path.abspath(__file__), "--inner", tmp, FR, OUT_N, OUT_F, OUT_J], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith("OUT")))
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    shutil.rmtree(tmp, ignore_errors=True); sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
sys.path.insert(0, os.path.join(EV, "measure"))
import m9_a3_shape_fit as m  # noqa: E402
import m11_box_end as e11  # noqa: E402
import m12_end_candidates as m12  # noqa: E402

i = sys.argv.index("--inner"); TMP, FR, OUT_N, OUT_F, OUT_J = sys.argv[i + 1:i + 6]
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
RW, RH, K = 1280, 533, 1280 / 3840
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
EFD = D["v03"]["low_box"]["end_form"]; END = {"Lt": EFD["tier_len"]["value"], "Lr": EFD["raised_len"]["value"], "dh": EFD["raised_dh"]["value"]}
G_AFTER = m12.geom(m.PH, END)
XN = m.HX0 - 0.06
G_BEFORE = {"P1": (XN, m.HY0, m.PH), "P2": (XN, m.HY0, m.PH), "P3": (XN, m.HY0, m.PH), "P4": (XN, m.HY0 - 0.3, m.PH * 0.75), "P5": (m.HX0 - m.SKO, m.YEND, 0.0),
            "P5seg": ((m.HX0 - 0.06, m.YEND, 0.0), (m.HX1, m.YEND, 0.0))}
M9 = json.load(open(os.path.join(EV, "measure", "m9_result.json"), encoding="utf-8"))
_r9 = [r for r in M9["rows"] if r["shape"] == {"light_center_h": 2.4, "width": 1.45}][0]
M10 = json.load(open(os.path.join(EV, "measure", "m10_result.json"), encoding="utf-8"))["fits"][0]
M12 = [r for r in json.load(open(os.path.join(EV, "measure", "m12_end_result.json"), encoding="utf-8"))["rows"] if r["end"] == END][0]["frames"]
CAMS = {   # 수정 전 형상으로 맞춘 카메라(전 쪽에 유리) / 수정 후 형상으로 맞춘 카메라(후 쪽에 유리) — 둘 다 같은 카메라로 전후를 렌더
    "pre_11748": ("11748", _r9["11748"]["cam"]), "pre_11726": ("11726", [x for x in _r9["11726"] if x["family_spots_AB"] == [0.0, -6.7] and x["door_in_fit"]][0]["cam"]),
    "pre_11246": ("11246", M10["cam"]),
    "post_11748": ("11748", M12["11748"]["cam"]), "post_11726": ("11726", M12["11726"][0]["cam"]), "post_11246": ("11246", min(M12["11246"], key=lambda q: q["rms_weighted_fit"])["cam"])}


def cvec(cd):
    return np.array([*cd["xyz"], math.radians(cd["yaw_deg"]), math.radians(cd["pitch_deg"]), cd["f"]])


def mk_cam(name, c):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = c[5] * 36.0 / 3840; cd.clip_start = 0.05; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co); co.location = tuple(c[:3])
    co.rotation_euler = Vector((math.cos(c[4]) * math.cos(c[3]), math.cos(c[4]) * math.sin(c[3]), math.sin(c[4]))).to_track_quat('-Z', 'Y').to_euler(); return co


def look(name, loc, tgt, lens, ortho=None):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = lens; cd.clip_end = 2000
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co); co.location = loc
    co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return co


def setup():
    sc = bpy.context.scene; cy = sc.cycles; cy.samples = 12; cy.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
    for o in bpy.data.objects: o.hide_render = o.name in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref") or o.name.startswith("Hypothesis_")
    return sc


def label(im, t):
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, im.width, 26), fill=(0, 0, 0)); dr.text((6, 3), t.replace("−", "-"), font=FT, fill=(255, 255, 255)); return im


def marks(im, frame, c, G):
    im = im.copy(); dr = ImageDraw.Draw(im)
    for part, st, px, _ in e11.END[frame]:
        if px is None: continue
        x, y = px[0] * K, px[1] * K; col = {"direct": (60, 255, 90), "estimated": (255, 230, 60)}.get(st, (200, 200, 200))
        q = m.proj(G[part], c)[0] * K
        dr.ellipse((x - 7, y - 7, x + 7, y + 7), outline=col, width=3)
        dr.line((q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6), fill=(255, 60, 60), width=3); dr.line((q[0] - 6, q[1] + 6, q[0] + 6, q[1] - 6), fill=(255, 60, 60), width=3)
        dr.line((x, y, q[0], q[1]), fill=(255, 255, 255), width=1); dr.text((x + 8, y - 22), part, font=FT, fill=col)
    return im


errs = {}
for tag, (frame, cd) in CAMS.items():
    c = cvec(cd); errs[tag] = {}
    for when, G in (("before", G_BEFORE), ("after", G_AFTER)):
        errs[tag][when] = {f"{p}({st})": (m12.seg_err(px, *G["P5seg"], c) if p == "P5" else round(float(np.linalg.norm(m.proj(G[p], c)[0] - np.array(px))), 1))
                           for p, st, px, _ in e11.END[frame] if px is not None}
rend = {}
for when in ("before", "after"):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(TMP, when + ".blend")); sc = setup()
    cams = {"lowbox_close": look("CL", (7.0, -23.0, 5.5), (12.8, -17.2, 0.3), 35), "side": look("SD", (4.0, -17.0, 1.0), (12.8, -17.5, 0.6), 30),
            "top": look("TP", (12.8, -16.5, 40.0), (12.8, -16.5, 0.0), 50, ortho=12.0)}
    for tag, (frame, cd) in CAMS.items(): cams[tag] = mk_cam(tag, cvec(cd))
    for k, cam in cams.items():
        sc.camera = cam; p = os.path.join(TMP, f"{when}_{k}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True); rend[(when, k)] = Image.open(p).convert("RGB")


def film(n):
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize((RW, RH))
    a = np.power(np.asarray(im).astype(float) / 255, 0.6); return Image.fromarray((a * 255).astype("uint8"))


DESC = {"lowbox_close": "근접 카메라", "side": "옆에서(−X 쪽, 낮은 시점)", "top": "위에서(정사영)",
        "pre_11748": "11748 — 수정 전 형상으로 맞춘 카메라(M9, f 상한)", "pre_11726": "11726 — 수정 전 형상으로 맞춘 카메라(M9, (0, −6.7) 계열)", "pre_11246": "11246 — 수정 전 형상으로 맞춘 카메라(M10)",
        "post_11748": "11748 — 수정 후 형상으로 맞춘 카메라(M12, f 상한)", "post_11726": "11726 — 수정 후 형상으로 맞춘 카메라(M12, (0, −6.7) 계열, f 하한)", "post_11246": "11246 — 수정 후 형상으로 맞춘 카메라(M12)"}
for k in DESC:
    a, b = rend[("before", k)], rend[("after", k)]
    if k in CAMS:
        frame, cd = CAMS[k]; c = cvec(cd); a, b = marks(a, frame, c, G_BEFORE), marks(b, frame, c, G_AFTER)
    sh = Image.new("RGB", (RW, RH * 2)); sh.paste(label(a, f"수정 전 A3 — {DESC[k]}"), (0, 0)); sh.paste(label(b, f"수정 후 A3(끝 형태) — {DESC[k]}"), (0, RH))
    sh.save(os.path.join(OUT_N, f"BA_end_{k}.png"))
    if k in CAMS:
        frame, cd = CAMS[k]; c = cvec(cd); fm = film(int(frame))
        sh = Image.new("RGB", (RW, RH * 3)); sh.paste(label(marks(fm, frame, c, G_AFTER), f"4K {frame} — 끝 부위 관측(초록 직접, 노랑 추정) × 수정 후 모델 투영(빨강)"), (0, 0))
        sh.paste(label(Image.blend(fm, a, 0.5), f"수정 전 × {DESC[k]} — 영화 50%"), (0, RH)); sh.paste(label(Image.blend(fm, b, 0.5), f"수정 후 × {DESC[k]} — 영화 50%"), (0, RH * 2))
        sh.save(os.path.join(OUT_F, f"F_end_{k}.png"))
json.dump({"end_form": END, "camera_note": "pre = 수정 전 형상으로 맞춘 카메라(M9·M10), post = 수정 후 형상으로 맞춘 카메라(M12). 각 카메라로 전후를 같은 조건에서 비교. 11748은 두 세트 모두 f 상한, 11726 post는 f 하한",
           "before_mapping": "P1·P2·P3 → 끝 벽 모서리(x 10.99, y −18.5, 1.2 m), P4 → 끝 단 첫 단, P5 → 끝 단 끝 바닥", "after_mapping": "부위별(P1 테두리 끝, P2 솟은 블록 시작, P3 솟은 블록 끝, P4 끝 단 윗면, P5 바닥 접점)",
           "errors_px": errs}, open(OUT_J, "w"), ensure_ascii=False, indent=1)
print("OUT endform", json.dumps(errs, ensure_ascii=False))
