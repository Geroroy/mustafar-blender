"""CR-009 출입구 위치 후보 평가 — 실제 후보 메시에 광선을 쏴서 가림과 '보이는 표면'을 확인한다(깊이·물체 ID 렌더와 같은 정보).
  ① 점 가림 검사: 영화에서 보이거나 가려진 점(문턱 가운데, 문설주 발치, 바깥 테두리 발치)을 카메라에서 광선으로 확인
  ② 화소 표본 검사: 영화 화소마다 '무엇이 보이는가'(바닥·상자·출입구·R·시설·없음)를 판독해 두고, 같은 화소 광선이 후보 메시에서 처음 닿는 물체 범주와 비교
     — 맞춤에 쓰지 않은 관측(바닥 연결, 용암이 보이는 빈자리, R 위치 등)도 여기서 평가한다
  ③ 11615·11246: 기준(H1)과 후보의 물체 ID 격자(64×27)를 비교해, 후보에서 새로 보이게 된 물체가 있는지(새 모순 후보) 적는다
카메라: measure/m13_cams.json(11726 출입구 뺀 맞춤, 11748 출입구 점만, 11246 상자·등), 11615는 v0.2 R2 고정 카메라.
실행 (저장소 루트): .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/eval_entrance_candidates.py <out.json>"""
import json, math, os, sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(EV, "..", ".."))
OUT = sys.argv[-1]
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
LAYS = D["v03"]["entrance_layout"]["candidates"]
CAMS = json.load(open(os.path.join(EV, "measure", "m13_cams.json"), encoding="utf-8"))
XW = D["platform"]["facility_edge_x"]["value"] + D["facility"]["trench_gap"]["value"]
EW = D["v03"]["entrance"]["width"]["value"]; XF0 = D["v03"]["entrance"]["frame_layers"]["value"][0][2]; OUTR = D["v03"]["entrance"]["frame_layers"]["value"][-1][1]
CX, CY = 1920.0, 800.0
NAMES = ["H1", "A3", "A3a", "A3b"]

CAT = [("box", ("Low_Box",)), ("floor", ("Floor_Plates", "Landing_Platform", "Entrance_Forecourt_Floor", "Entrance_Apron", "Platform_Sidewalls")),
       ("door", ("Facility_A_Entrance", "Entrance_Bay_Front", "Entrance_Passage")), ("R", ("R_Structure_Hypothesis",)), ("curb", ("Edge_Curbs",)),
       ("facility", ("Hangar_", "Structural_Pillars", "Corridor_Lower_Walkway", "Facility_", "Back_Edge", "Edge_Lights"))]
SAMPLES = {   # 영화 화소(4K) → 영화에서 보이는 범주(판독). 맞춤에 쓰지 않은 관측
    "11748": [((1100, 1265), "floor", "문턱 앞 바닥(상자 끝 옆)"), ((1250, 1260), "floor", "문턱 앞 바닥"), ((1350, 1300), "floor", "−Y 문설주 앞 바닥"),
              ((1150, 1350), "floor", "문턱 앞 바닥(가까운 쪽)"), ((1450, 1290), "floor", "−Y 문설주 오른쪽 바닥"), ((300, 1250), "box", "상자 L 근면"),
              ((600, 1250), "box", "상자 L 근면"), ((800, 1200), "box", "상자 L 끝 쪽"), ((930, 1220), "box", "상자 L 끝 단"), ((1400, 1000), "door", "−Y 문설주 면"),
              ((2300, 1150), "R", "R 긴 면"), ((2600, 1150), "R", "R 긴 면"), ((3000, 1220), "none", "R 너머 용암(바닥 끝 위)"), ((3000, 1360), "floor", "R 너머 바닥"),
              ((3500, 1300), "curb", "가장자리 연석")],
    "11726": [((1800, 1150), "box", "상자 A 근면"), ((2300, 1150), "box", "상자 A 근면"), ((2700, 1100), "box", "상자 A 끝 블록"), ((2900, 1150), "box", "상자 A 끝 단"),
              ((3100, 1230), "floor", "상자 끝 너머 바닥"), ((3400, 1240), "floor", "상자 끝 너머 바닥"), ((3700, 1270), "floor", "상자 끝 너머 바닥"),
              ((3445, 1150), "none", "바닥 끝 위로 용암"), ((3600, 1130), "R", "오른쪽 끝 구조물 B"), ((2700, 700), "door", "출입구 테두리(상자 위)"),
              ((500, 1250), "floor", "왼쪽 바닥"), ((500, 900), "facility", "처마 구간 벽·지지부")],
}


def cat_of(name):
    if name is None: return "none"
    for c, pre in CAT:
        if any(name.startswith(p) for p in pre): return c
    return "other"


def build_bvh():
    dg = bpy.context.evaluated_depsgraph_get(); verts, polys, owner = [], [], []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name.startswith(("Ref_", "Skiff", "Ramp_Foot", "Outline_Alt", "Lava_Level", "Hypothesis_")) or "Placeholder" in ob.name or "Unknown" in ob.name:
            continue
        if any(c.hide_render for c in ob.users_collection): continue
        me = ob.evaluated_get(dg).to_mesh(); mw = ob.matrix_world; b = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        for p in me.polygons: polys.append([b + i for i in p.vertices]); owner.append(ob.name)
        ob.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), owner


def R_of(yaw, pitch):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    fwd = np.array([cp * cy, cp * sy, sp]); right = np.array([sy, -cy, 0.0]); up = np.cross(right, fwd); return fwd, right, up


def cam_rays(cd):
    o = np.array(cd["xyz"], float); fwd, right, up = R_of(math.radians(cd["yaw_deg"]), math.radians(cd["pitch_deg"])); f = cd["f"]
    return o, (lambda u, v: fwd + right * (u - CX) / f - up * (v - CY) / f)


def first_hit(bvh, owner, o, d, dist=500.0):
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    loc, nrm, idx, t = bvh.ray_cast(Vector(o), Vector(d), dist)
    return (owner[idx], t, loc) if loc is not None else (None, None, None)


def visible(bvh, owner, o, p, eps=0.06):
    d = np.asarray(p, float) - o; L = float(np.linalg.norm(d)); n, t, _ = first_hit(bvh, owner, o, d, L + 1.0)
    return (n is None) or (t >= L - eps), n


def world_local(cl, xe, ey):
    return {"xyz": [xe + cl["xyz"][0], ey + cl["xyz"][1], cl["xyz"][2]], "yaw_deg": cl["yaw_deg"], "pitch_deg": cl["pitch_deg"], "f": cl["f"]}


res = {"note": "광선 교차(후보 메시) 기반. 범주 표본은 영화 판독(맞춤에 쓰지 않은 관측 포함). 11748 카메라는 출입구 점만으로 맞춘 국소 카메라(f 2000~2800, 출입구 크기 2.4 m 가정)를 각 후보 출입구에 붙임",
       "samples": {f: [{"px": p, "expect": e, "desc": s} for p, e, s in v] for f, v in SAMPLES.items()}, "candidates": {}}
grids = {}
for name in NAMES:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "v0.3", "work", "layouts", f"layout_{name}.blend"))
    bvh, owner = build_bvh(); L = LAYS[name]; xe = L.get("front_x") or XW; ey = L["center_y"]
    pts = {"threshold_mid": (xe - XF0, ey, 0.02), "jamb_plusY_foot": (xe - XF0, ey + EW / 2, 0.02), "jamb_minusY_foot": (xe - XF0, ey - EW / 2, 0.02),
           "door_outer_base_minusY": (xe - 0.15, ey - EW / 2 - OUTR * EW, 0.02)}
    rec = {"door": {"front_x": xe, "center_y": ey, "box_end_y": L.get("box_end_y")}, "11748": [], "11726": []}
    for cl in CAMS["11748_local"]:
        cd = world_local(cl["cam_local"], xe, ey); o, rayf = cam_rays(cd)
        vis = {k: visible(bvh, owner, o, p) for k, p in pts.items()}
        rel = {"jamb_plusY_foot_hidden(film: yes)": not vis["jamb_plusY_foot"][0], "threshold_mid_visible(film: yes)": vis["threshold_mid"][0],
               "jamb_minusY_foot_visible(film: yes)": vis["jamb_minusY_foot"][0]}
        samp = []
        for (u, v), exp, desc in SAMPLES["11748"]:
            n, t, _ = first_hit(bvh, owner, o, rayf(u, v)); samp.append({"px": [u, v], "expect": exp, "got": cat_of(n), "object": n, "ok": cat_of(n) == exp})
        rec["11748"].append({"f": cl["f"], "relations": rel, "relations_ok": sum(rel.values()), "samples_ok": sum(s["ok"] for s in samp), "samples_n": len(samp), "samples": samp})
    if name != "H1":
        for c26 in CAMS["candidates"][name]["11726"]:
            o, rayf = cam_rays(c26["cam"]); vis = {k: visible(bvh, owner, o, p) for k, p in pts.items()}
            rel = {"threshold_mid_hidden(film: yes)": not vis["threshold_mid"][0], "jamb_plusY_foot_hidden(film: yes)": not vis["jamb_plusY_foot"][0],
                   "door_outer_base_minusY_visible(film: yes)": vis["door_outer_base_minusY"][0]}
            fwd, right, up = R_of(math.radians(c26["cam"]["yaw_deg"]), math.radians(c26["cam"]["pitch_deg"])); f = c26["cam"]["f"]
            def pj(p):
                d = np.asarray(p) - o; return [CX + f * (d @ right) / (d @ fwd), CY - f * (d @ up) / (d @ fwd)]
            ob_px = pj(pts["door_outer_base_minusY"]); err_ob = float(np.hypot(ob_px[0] - 3000, ob_px[1] - 1168))
            samp = []
            for (u, v), exp, desc in SAMPLES["11726"]:
                n, t, _ = first_hit(bvh, owner, o, rayf(u, v)); samp.append({"px": [u, v], "expect": exp, "got": cat_of(n), "object": n, "ok": cat_of(n) == exp})
            rec["11726"].append({"family_spots_AB": c26["family_spots_AB"], "cam_rms_weighted": c26["rms_weighted"], "f": c26["cam"]["f"], "f_at_bound": c26["f_at_bound"],
                                 "relations": rel, "relations_ok": sum(rel.values()), "door_outer_base_err_px(eval)": round(err_ob, 1),
                                 "samples_ok": sum(s["ok"] for s in samp), "samples_n": len(samp), "samples": samp})
    # ③ 11615(R2 고정)·11246 물체 ID 격자
    g = {}
    cam = bpy.data.objects["Perspective_View_R2_match"]; sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 3840, 1600
    fr = [cam.matrix_world @ v for v in cam.data.view_frame(scene=sc)]; o2 = np.array(cam.matrix_world.translation)
    tr, br, bl, tl = [np.array(v) for v in fr]
    ids = []
    for j in range(27):
        for i in range(64):
            a, b = (i + 0.5) / 64, (j + 0.5) / 27
            p = tl + (tr - tl) * a + (bl - tl) * b; n, _, _ = first_hit(bvh, owner, o2, p - o2); ids.append(n)
    g["11615_r2"] = ids
    c46 = min(CAMS["candidates"].get(name, CAMS["candidates"]["A3"])["11246"], key=lambda q: q["rms_weighted"])["cam"]; o3, rf3 = cam_rays(c46)
    g["11246"] = [first_hit(bvh, owner, o3, rf3((i + 0.5) * 3840 / 64, (j + 0.5) * 1600 / 27))[0] for j in range(27) for i in range(64)]
    grids[name] = g
    res["candidates"][name] = rec
    print(name, {f: [(r["relations_ok"], r["samples_ok"]) for r in rec[f]] for f in ("11748", "11726")}, flush=True)
for name in NAMES[1:]:
    res["candidates"][name]["new_visible_vs_H1"] = {}
    for k in ("11615_r2", "11246"):
        ch = {}
        for a, b in zip(grids["H1"][k], grids[name][k]):
            if a != b and b is not None and cat_of(b) in ("door", "R", "floor", "box") and cat_of(a) != cat_of(b):
                ch[b] = ch.get(b, 0) + 1
        res["candidates"][name]["new_visible_vs_H1"][k] = {"cells_changed_to(object: count of 64x27)": ch}
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
for name in NAMES[1:]: print(name, res["candidates"][name]["new_visible_vs_H1"])
