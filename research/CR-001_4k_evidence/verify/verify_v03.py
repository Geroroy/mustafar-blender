"""v0.3 검증 사본에서 카메라·처마 높이 비교 렌더.  v0.2 원본은 읽기만 한다(해시 전후 비교).
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/verify_v03.py <11615.jpg 경로>
1) 검증 사본 만들기: v0.2 폴더를 research/CR-001_4k_evidence/_private/verify_v03/ 아래로 복사한다.
   - model_v02      : v0.2 .blend 그대로(복사본)
   - model_eave6    : 사본의 dimensions.json에서 facility.beam_height 7.2→6.0, roof_top_z 8.5→7.3 로 바꾼 뒤 사본의 create_mustafar.py로 다시 생성
   그 밖의 치수는 바꾸지 않는다.
2) 카메라 후보: CAM_V02(v0.2 dimensions.json의 R2 카메라)와 CAM_NEW_f(M1 해, f 3640/4550/5850). 새 카메라는 M1 카메라 좌표의
   바닥점(가장자리 등 3개 + 계단 상자 바닥 모서리)을 모델의 같은 점에 2D 강체 맞춤(회전+이동, 축척 없음)해서 모델에 놓는다.
3) 평가:
   (a) 인물 10관측 머리 v 잔차 — 두 카메라를 같은 4K 자료로 평가(모델과 무관)
   (b) 정적 구조 재투영 오차 — 모델의 가장자리 등 3·처마 조명 3·상자 윗모서리를 각 카메라로 투영해 11615 픽셀과 비교
   (c) 11615 겹침 렌더 (영화 화면 포함 → _private)
"""
import hashlib, json, math, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
OUT = os.path.join(EV, "_private", "verify_v03")
PY = os.path.join(ROOT, ".venv-bpy", "bin", "python")
SRC_DIR = os.path.join(ROOT, "v0.2")
SRC_BLEND = os.path.join(SRC_DIR, "mustafar_blockout_v0.2.blend")
VARIANT = {"facility.beam_height": 6.0, "facility.roof_top_z": 7.3}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def build():
    os.makedirs(OUT, exist_ok=True)
    refs = os.path.join(OUT, "refs")
    if not os.path.exists(refs):
        os.symlink(os.path.join(ROOT, "refs"), refs)
    a = os.path.join(OUT, "model_v02"); shutil.rmtree(a, ignore_errors=True); os.makedirs(a)
    shutil.copy2(SRC_BLEND, os.path.join(a, "model.blend"))
    b = os.path.join(OUT, "model_eave6"); shutil.rmtree(b, ignore_errors=True); shutil.copytree(SRC_DIR, b)
    d = json.load(open(os.path.join(b, "dimensions.json"), encoding="utf-8"))
    for k, val in VARIANT.items():
        g, f = k.split("."); d[g][f]["value"] = val
        d[g][f]["basis"] = "[v0.3 검증 사본 변형] " + d[g][f]["basis"]
    d["render"]["samples"] = 8
    json.dump(d, open(os.path.join(b, "dimensions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    r = subprocess.run([PY, os.path.join(b, "create_mustafar.py")], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
    shutil.copy2(os.path.join(b, "mustafar_blockout_v0.2.blend"), os.path.join(b, "model.blend"))


if __name__ == "__main__" and "--inner" not in sys.argv:
    film = sys.argv[1]
    h0 = sha(SRC_BLEND)
    build()
    for m in ("model_v02", "model_eave6"):
        r = subprocess.run([PY, os.path.abspath(__file__), "--inner", os.path.join(OUT, m, "model.blend"), m, film], capture_output=True, text=True)
        print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("CAM", "RES", "ERR"))))
        if r.returncode != 0:
            print(r.stderr[-3000:]); sys.exit(1)
    h1 = sha(SRC_BLEND)
    res = {m: json.load(open(os.path.join(OUT, f"{m}_metrics.json"))) for m in ("model_v02", "model_eave6")}
    res["v02_blend_sha256_before_after_equal"] = h0 == h1
    json.dump(res, open(os.path.join(HERE, "verify_result.json"), "w"), ensure_ascii=False, indent=1)
    print("v0.2 원본 무변경:", h0 == h1)
    sys.exit(0)

# ---------------------------------------------------------------- 내부: bpy 안에서 실행
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

sys.path.insert(0, os.path.join(EV, "measure"))
import m1_r2_camera_4k as m1  # noqa: E402

i = sys.argv.index("--inner"); BLEND, NAME, FILM = sys.argv[i + 1], sys.argv[i + 2], sys.argv[i + 3]
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene; OBJ = bpy.data.objects
DIM = json.load(open(os.path.join(ROOT, "v0.2", "dimensions.json"), encoding="utf-8"))
W4, H4 = 3840, 1600


def clusters(name, key):
    o = OBJ[name]; me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    pts = sorted((o.matrix_world @ v.co for v in me.vertices), key=lambda p: -getattr(p, key))
    groups = [[pts[0]]]
    for p in pts[1:]:                       # 축 방향 간격이 2 m 넘게 벌어지면 다른 등
        if getattr(groups[-1][-1], key) - getattr(p, key) > 2.0: groups.append([p])
        else: groups[-1].append(p)
    return [sum(g, Vector()) / len(g) for g in groups]


lights = clusters("Edge_Lights_Facility_Side", "y")          # y 큰 순 = d, e, f
spots_all = clusters("Hangar_Spotlights", "y")               # y 큰 순: 13.4, 6.7, 0, ...
spots = spots_all[:3]
sx, sy = DIM["stairwell"]["corner_back_left"]["value"]
box_floor = Vector((sx, sy, 0.0)); box_rim = Vector((sx, sy, DIM["stairwell"]["parapet_height"]["value"]))
STATIC = {"edge_light_d": (lights[0], m1.PTS["edge_light_d"]), "edge_light_e": (lights[1], m1.PTS["edge_light_e"]),
          "edge_light_f": (lights[2], m1.PTS["edge_light_f"]),
          "spot1": (spots[0], m1.SPOTS[0]), "spot2": (spots[1], m1.SPOTS[1]), "spot3": (spots[2], m1.SPOTS[2]),
          "box_rim": (box_rim, m1.BOX_RIM)}


def make_cam(name, loc, pitch_deg, yaw_deg, f_px):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
    cd.lens = f_px * 36.0 / W4; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    co.location = loc; co.rotation_euler = (math.radians(90 - pitch_deg), 0, math.radians(yaw_deg))
    return co


def project(cam, p):
    sc.render.resolution_x, sc.render.resolution_y = W4, H4
    c = world_to_camera_view(sc, cam, p)
    return c.x * W4, (1 - c.y) * H4, c.z


cams = {}
rc = DIM["r2_camera"]; AX, AY = rc["anchor_A"]["value"]; cx, cy, cz = rc["location_from_back_corner"]["value"]
f_v02 = rc["lens_mm_36"] * W4 / 36.0
cams["CAM_V02"] = dict(obj=make_cam("CAM_V02", (AX + cx, AY + cy, cz), rc["pitch_deg"], rc["yaw_deg"], f_v02),
                       f=f_v02, h=cz, pitch=rc["pitch_deg"], note="v0.2 dimensions.json r2_camera")
for f in (3640, 4550, 5850):
    s, th, h, _ = m1.solve(f)
    src = np.array([m1.ground(*m1.PTS[k], f, th, h)[:2] for k in ("edge_light_d", "edge_light_e", "edge_light_f", "box_floor_corner")])
    dst = np.array([[lights[0].x, lights[0].y], [lights[1].x, lights[1].y], [lights[2].x, lights[2].y], [box_floor.x, box_floor.y]])
    cs, cd_ = src.mean(0), dst.mean(0); Hm = (src - cs).T @ (dst - cd_)
    U, _, Vt = np.linalg.svd(Hm); R = (U @ Vt).T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1; R = (U @ Vt).T
    t = cd_ - R @ cs; fit_res = np.linalg.norm((src @ R.T + t) - dst, axis=1)
    yaw = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    cams[f"CAM_NEW_f{f}"] = dict(obj=make_cam(f"CAM_NEW_f{f}", (t[0], t[1], h), math.degrees(th), yaw, f), f=f, h=round(h, 2),
                                 pitch=round(math.degrees(th), 2), yaw=round(yaw, 2), loc=[round(float(t[0]), 2), round(float(t[1]), 2)],
                                 rigid_fit_residual_m=[round(float(x), 2) for x in fit_res])
bpy.context.view_layer.update()

metrics = {"model": NAME, "beam_height_m": None, "cams": {}}
metrics["model_spot_z_m"] = [round(p.z, 2) for p in spots]
for cn, c in cams.items():
    cam = c["obj"]
    th = math.radians(c["pitch"]); hr = m1.residuals(c["f"], np.array([th]), np.array([c["h"]]), m1.OBS, (m1.H_OBI, m1.H_ANA))
    st = {}
    for k, (wp, (u, v)) in STATIC.items():
        pu, pv, _ = project(cam, wp); st[k] = {"px": [round(pu), round(pv)], "film": [u, v], "err_px": round(math.hypot(pu - u, pv - v), 1), "dv_px": round(pv - v, 1)}
    errs = [x["err_px"] for x in st.values()]
    metrics["cams"][cn] = {k: v for k, v in c.items() if k != "obj"}
    metrics["cams"][cn].update(actor_head_rms_px=round(float(hr[0]), 1), static=st,
                               static_rms_px=round(float(np.sqrt(np.mean(np.square(errs)))), 1),
                               spot_dv_px=[st[f"spot{j}"]["dv_px"] for j in (1, 2, 3)])
    print("CAM", NAME, cn, "actorRMS", metrics["cams"][cn]["actor_head_rms_px"], "staticRMS", metrics["cams"][cn]["static_rms_px"], "spot_dv", metrics["cams"][cn]["spot_dv_px"])
# 계단 상자: 바닥 모서리 위치 확인 + 윗모서리 높이를 바꿔 가며 v 오차 (CAM_V02 기준, 모델 무변경)
cam = cams["CAM_V02"]["obj"]
fu, fv, _ = project(cam, box_floor)
metrics["box_check_cam_v02"] = {"floor_corner_px": [round(fu), round(fv)], "floor_corner_film": list(m1.PTS["box_floor_corner"]),
                               "rim_dv_px_by_z": {str(z): round(project(cam, Vector((sx, sy, z)))[1] - m1.BOX_RIM[1], 1) for z in (0.5, 0.75, 1.0, 1.2, 1.4)}}
# 처마 조명: CAM_V02에서 v 오차가 0이 되는 높이(모델 x·y 위치 고정, 높이만 변화)
metrics["spot_zero_dv_z_cam_v02"] = {}
for j, sp in enumerate(spots):
    lo, hi = 3.0, 10.0
    for _ in range(50):
        z = (lo + hi) / 2
        if project(cam, Vector((sp.x, sp.y, z)))[1] > m1.SPOTS[j][1]: lo = z
        else: hi = z
    metrics["spot_zero_dv_z_cam_v02"][f"spot{j+1}"] = round(z, 2)
print("CAM", NAME, "box", metrics["box_check_cam_v02"], "spotz", metrics["spot_zero_dv_z_cam_v02"])
json.dump(metrics, open(os.path.join(OUT, f"{NAME}_metrics.json"), "w"), ensure_ascii=False, indent=1)

# 렌더 (빠른 설정, 장면 1회 로드·순차)
c_ = sc.cycles; c_.samples = 8; c_.use_denoising = True; c_.denoising_prefilter = 'FAST'
c_.max_bounces, c_.diffuse_bounces, c_.glossy_bounces, c_.transmission_bounces = 4, 2, 2, 0
sc.render.use_persistent_data = True
for nm in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg", "Lava_Level_Ref"):
    if nm in OBJ: OBJ[nm].hide_render = True
RW, RH = 1280, 533
film = Image.open(FILM).convert("RGB").resize((RW, RH))
a = np.power(np.asarray(film).astype(float) / 255, 0.7); film = Image.fromarray((a * 255).astype("uint8"))
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
rows = []
for cn in ("CAM_V02", "CAM_NEW_f4550"):
    cam = cams[cn]["obj"]; sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
    path = os.path.join(OUT, f"{NAME}_{cn}.png"); sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    ren = Image.open(path).convert("RGB"); over = Image.blend(film, ren, 0.45); dr = ImageDraw.Draw(over)
    k = RW / W4
    for key, (wp, (u, v)) in STATIC.items():
        pu, pv, _ = project(cam, wp)
        dr.ellipse((u * k - 5, v * k - 5, u * k + 5, v * k + 5), outline=(0, 255, 0), width=2)     # 영화 픽셀
        dr.line((u * k, v * k, pu * k, pv * k), fill=(255, 255, 0), width=2)                       # → 모델 투영
        dr.rectangle((pu * k - 4, pv * k - 4, pu * k + 4, pv * k + 4), outline=(255, 60, 60), width=2)
    m = metrics["cams"][cn]
    dr.rectangle((0, 0, RW, 26), fill=(0, 0, 0))
    dr.text((6, 3), f"{NAME} × {cn}  (h {m['h']:.2f} m, pitch {m['pitch']}°)  인물 잔차 {m['actor_head_rms_px']} px · 구조 재투영 {m['static_rms_px']} px (4K)  초록=영화 빨강=모델", font=FT, fill=(255, 255, 255))
    rows.append(over)
sheet = Image.new("RGB", (RW, RH * len(rows)))
for j, r in enumerate(rows): sheet.paste(r, (0, j * RH))
sheet.save(os.path.join(OUT, f"{NAME}_compare_11615.png"))
print("RES", NAME, "ok")
