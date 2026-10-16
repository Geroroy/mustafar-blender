"""무스타파 착륙장 — 플레이용 스테이지 시각 완성본(v0.4_stage). Blender(bpy).
기준 배치: v0.3 A3b(임시 작업 기준, 영화 고증 확정 아님). A3·H1은 v0.3/work/layouts/에 그대로 보존.
하는 일:
  1) v0.3/work/layouts/layout_A3b.blend 를 열어(원본은 바꾸지 않음) 근거 없는 가설·검증용·철사틀 객체를 최종 화면에서 숨긴다.
  2) 영화에 맞춘 재질(어두운 금속, 먼지 낀 바닥판, 오염·마모, 용암, 현무암)과 조명(용암 반사광, 처마 조명, 청색 가장자리 등)을 입힌다.
  3) 카메라를 둘로 나눈다: Game_Output_Iso(게임 투영과 정확히 같은 직교 30°/45°, 28.284 px/m) / Film_Compare_*(영화 맞춤 카메라, 비교 전용).
  4) mustafar_landing_stage.blend 저장. 형상(위치·치수)은 바꾸지 않는다 — 모서리 베벨(시각용)만 더한다.
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/build_stage.py [--preview]   (--preview: 1배 크기 최종 아이소 확인 렌더)
"""
import json, math, os, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(HERE, os.environ.get("STAGE_CONFIG", "stage_config.json")), encoding="utf-8"))
SRC = os.path.join(ROOT, "v0.3", "work", "layouts", f"layout_{CFG['layout']}.blend")   # A3b(보존) / A3c(구조 수정 작업 사본)
OUT_BLEND = os.path.join(HERE, CFG.get("stage_blend", "mustafar_landing_stage.blend"))

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
D = bpy.data

# ---------------------------------------------------------------- 1. 숨김(최종 화면) — 객체는 지우지 않고 렌더에서만 뺀다
HIDE_COLLS = ["Hypothesis_R", "Hypothesis_Stairwell_Descent", "Scale_Check", "Platform_Corner_Markers", "Platform_Outline_Range", "Placeholders"]
HIDE_OBJS = ["Lava_Level_Ref", "Trench_End_Unknown", "Entrance_Passage_Unknown_End", "Facility_Body_Unknown"]
hidden_log = []
for cn in HIDE_COLLS:
    c = D.collections.get(cn)
    if c:
        c.hide_render = True
        hidden_log += [o.name for o in c.objects]
for n in HIDE_OBJS:
    o = D.objects.get(n)
    if o:
        o.hide_render = True; hidden_log.append(n)
# 출입구 돌출부 옆면: 형태 미확인(U)이지만 출입구 면(x 14.8)과 시설 벽 사이를 비워 두면 화면이 성립하지 않아 단색 볼륨으로 둠(시각용)
bay = D.objects.get("Entrance_Bay_Unknown")          # A3b만 있음(A3c는 A자 외피로 대체)
if bay:
    for m in list(bay.modifiers):
        if m.type == 'WIREFRAME':
            bay.modifiers.remove(m)
    bay.visible_shadow = True

# ---------------------------------------------------------------- 2. 재질
def node_mat(name):
    m = D.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    return m, nt, out


def coord(nt, scale=(1, 1, 1)):
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); mp.inputs["Scale"].default_value = scale
    return mp.outputs["Vector"]


def noise(nt, vec, scale, detail=6.0, rough=0.6):
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; nt.links.new(vec, n.inputs["Vector"]); return n.outputs["Fac"]


def ramp(nt, fac, stops):
    r = nt.nodes.new("ShaderNodeValToRGB"); cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = cr.elements.new(p); e.color = (*c, 1)
    nt.links.new(fac, r.inputs["Fac"]); return r.outputs["Color"]


def mix(nt, a, b, fac, mode='MULTIPLY'):
    x = nt.nodes.new("ShaderNodeMix"); x.data_type = 'RGBA'; x.blend_type = mode
    nt.links.new(fac, x.inputs[0]) if not isinstance(fac, float) else None
    if isinstance(fac, float):
        x.inputs[0].default_value = fac
    nt.links.new(a, x.inputs[6]); nt.links.new(b, x.inputs[7]); return x.outputs[2]


def metal(name, base, dark, streak=True, metallic=0.55, rough=(0.45, 0.85), scale=1.0):
    """먼지·그을음이 낀 산업 금속. streak: 세로로 흘러내린 얼룩(높이 방향으로 늘린 잡음)."""
    m, nt, out = node_mat(name)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    v = coord(nt, (scale, scale, scale))
    vs = coord(nt, (scale * 3.0, scale * 3.0, scale * 0.25)) if streak else v
    grime = noise(nt, vs, 2.2, 8.0, 0.65)
    panel = noise(nt, v, 0.35, 2.0, 0.5)
    fine = noise(nt, v, 38.0, 4.0, 0.7)
    c_base = ramp(nt, panel, [(0.3, dark), (0.7, base)])
    c_grime = ramp(nt, grime, [(0.35, (0.35, 0.3, 0.27)), (0.62, (1, 1, 1))])
    col = mix(nt, c_base, c_grime, 1.0)
    c_fine = ramp(nt, fine, [(0.4, (0.86, 0.84, 0.82)), (0.6, (1.05, 1.03, 1.0))])
    col = mix(nt, col, c_fine, 1.0)
    nt.links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = metallic
    rr = nt.nodes.new("ShaderNodeMapRange"); nt.links.new(grime, rr.inputs["Value"]); rr.inputs[3].default_value, rr.inputs[4].default_value = rough[1], rough[0]
    nt.links.new(rr.outputs[0], bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12; nt.links.new(fine, bump.inputs["Height"]); nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], out.inputs[0]); return m


def floor(name, base, alt):
    """영화 11246·11712의 바닥판: 따뜻한 회갈색 금속판, 먼지 얼룩, 긁힘, 판마다 조금 다른 톤."""
    m, nt, out = node_mat(name)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    v = coord(nt)
    dust = noise(nt, v, 0.18, 6.0, 0.6)
    mid = noise(nt, v, 1.4, 6.0, 0.65)
    scr = noise(nt, coord(nt, (1.0, 12.0, 1.0)), 9.0, 3.0, 0.4)
    c = ramp(nt, mid, [(0.3, alt), (0.7, base)])
    c = mix(nt, c, ramp(nt, dust, [(0.38, (0.55, 0.5, 0.46)), (0.6, (1, 1, 1)), (0.8, (1.08, 1.04, 0.98))]), 1.0)
    c = mix(nt, c, ramp(nt, scr, [(0.55, (1, 1, 1)), (0.7, (1.25, 1.2, 1.12))]), 1.0)
    nt.links.new(c, bsdf.inputs["Base Color"]); bsdf.inputs["Metallic"].default_value = 0.35
    rr = nt.nodes.new("ShaderNodeMapRange"); nt.links.new(dust, rr.inputs["Value"]); rr.inputs[3].default_value, rr.inputs[4].default_value = 0.9, 0.55
    nt.links.new(rr.outputs[0], bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08; nt.links.new(scr, bump.inputs["Height"]); nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], out.inputs[0]); return m


def emit(name, color, strength):
    m, nt, out = node_mat(name)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*color, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0]); return m


def lava():
    m, nt, out = node_mat("STAGE_Lava")
    v = coord(nt, (0.08, 0.08, 0.08))
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs["Scale"].default_value = 7.0; vo.inputs["Randomness"].default_value = 1.0
    wob = noise(nt, v, 2.0, 4.0, 0.6)
    vv = nt.nodes.new("ShaderNodeMix"); vv.data_type = 'VECTOR'; vv.inputs[0].default_value = 0.35
    nt.links.new(v, vv.inputs[4]); nt.links.new(wob, vv.inputs[5]); nt.links.new(vv.outputs[1], vo.inputs["Vector"])
    n = noise(nt, v, 3.0, 8.0, 0.7)
    crack = ramp(nt, vo.outputs["Distance"], [(0.0, (1.0, 0.62, 0.18)), (0.035, (0.85, 0.2, 0.03)), (0.09, (0.035, 0.012, 0.008))])
    big = noise(nt, coord(nt, (0.01, 0.01, 0.01)), 1.2, 3.0, 0.5)
    glow = mix(nt, crack, ramp(nt, n, [(0.35, (0.25, 0.2, 0.2)), (0.75, (1.4, 1.1, 1.0))]), 1.0)
    glow = mix(nt, glow, ramp(nt, big, [(0.42, (0.12, 0.1, 0.1)), (0.62, (1.0, 1.0, 1.0))]), 1.0)
    e = nt.nodes.new("ShaderNodeEmission"); nt.links.new(glow, e.inputs[0]); e.inputs[1].default_value = 2.2
    nt.links.new(e.outputs[0], out.inputs[0]); return m


def rock():
    m, nt, out = node_mat("STAGE_Basalt")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    v = coord(nt, (0.5, 0.5, 0.5))
    n = noise(nt, v, 1.6, 10.0, 0.7)
    nt.links.new(ramp(nt, n, [(0.35, (0.03, 0.025, 0.025)), (0.7, (0.11, 0.085, 0.075))]), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; nt.links.new(n, bump.inputs["Height"]); nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], out.inputs[0]); return m


MAT = {
    "facility": metal("STAGE_FacilityMetal", (0.13, 0.12, 0.115), (0.06, 0.055, 0.055)),
    "facade": metal("STAGE_FacadeMetal", (0.19, 0.17, 0.16), (0.09, 0.08, 0.08)),
    "roof": metal("STAGE_RoofMetal", (0.11, 0.10, 0.10), (0.05, 0.045, 0.045), streak=False),
    "deckbase": metal("STAGE_DeckBase", (0.06, 0.055, 0.05), (0.03, 0.028, 0.026), streak=False, metallic=0.3),
    "sidewall": metal("STAGE_PlatformSide", (0.15, 0.13, 0.12), (0.07, 0.06, 0.055), streak=False),
    "box": metal("STAGE_BoxMetal", (0.30, 0.24, 0.19), (0.15, 0.12, 0.10)),
    "boxinner": metal("STAGE_BoxInner", (0.62, 0.52, 0.40), (0.38, 0.31, 0.24), streak=False, metallic=0.3, scale=2.0),
    "trim": metal("STAGE_EdgeTrim", (0.24, 0.20, 0.17), (0.10, 0.09, 0.08), streak=False),
    "plateA": floor("STAGE_FloorPlateA", (0.60, 0.54, 0.47), (0.49, 0.44, 0.39)),
    "plateB": floor("STAGE_FloorPlateB", (0.53, 0.48, 0.42), (0.42, 0.38, 0.34)),
    "blue": emit("STAGE_LightBlue", (0.45, 0.75, 1.0), 18.0),
    "warm": emit("STAGE_LightWarm", (1.0, 0.86, 0.66), 14.0),
    "cool": emit("STAGE_LightCool", (0.85, 0.92, 1.0), 22.0),
    "slot": emit("STAGE_LightSlot", (1.0, 0.82, 0.6), 5.0),
    "lava": lava(),
    "rock": rock(),
    "baydark": metal("STAGE_BayDark", (0.035, 0.03, 0.03), (0.015, 0.012, 0.012), streak=False, metallic=0.2),
}
ASSIGN = {
    "Landing_Platform": "deckbase", "Platform_Sidewalls": "sidewall",
    "Hangar_Walls": "facility", "Structural_Pillars": "facade", "Hangar_Roof": "roof", "Corridor_Lower_Walkway": "facility",
    "Entrance_Bay_Front": "facade", "Entrance_Bay_Unknown": "facility", "Facility_A_Entrance": "facade", "Entrance_Passage_Visible": "facility",
    "Entrance_Forecourt_Floor": "plateB",
    "Entrance_Housing": "facade", "Hangar_Open_Bay": "baydark", "Entrance_Bridge_Floor": "plateB", "Entrance_Side_Structure_R": "box",
    "Low_Box": "box", "Low_Box_End_Block": "box", "Low_Box_Outer_Skin": "box", "Low_Box_Inner_Members": "boxinner",
    "Edge_Curbs_Near_Stairwell": "trim", "Back_Edge_Posts": "trim", "Back_Edge_Rail": "trim",
    "Hangar_Spotlights": "warm", "Facility_A_Entrance_Light": "cool", "Edge_Lights_Facility_Side": "blue", "Back_Edge_Post_Lights": "blue",
    "Low_Box_Lit_Slots": "slot",
}
for n, k in ASSIGN.items():
    o = D.objects.get(n)
    if o is None:
        continue
    o.data.materials.clear(); o.data.materials.append(MAT[k])
fp = D.objects["Floor_Plates"]
fp.data.materials[0] = MAT["plateA"]; fp.data.materials[1] = MAT["plateB"]

# 시각용 모서리 베벨(형상 치수는 그대로)
for n, w in (("Hangar_Walls", 0.06), ("Structural_Pillars", 0.05), ("Hangar_Roof", 0.08), ("Entrance_Bay_Front", 0.05), ("Entrance_Bay_Unknown", 0.05),
             ("Facility_A_Entrance", 0.03), ("Low_Box", 0.025), ("Low_Box_End_Block", 0.025), ("Low_Box_Outer_Skin", 0.02), ("Low_Box_Inner_Members", 0.015),
             ("Edge_Curbs_Near_Stairwell", 0.03), ("Back_Edge_Posts", 0.03), ("Platform_Sidewalls", 0.05), ("Floor_Plates", 0.012),
             ("Entrance_Housing", 0.04), ("Entrance_Side_Structure_R", 0.025), ("Entrance_Bridge_Floor", 0.02)):
    o = D.objects.get(n)
    if o is None:
        continue
    b = o.modifiers.new("vis_bevel", 'BEVEL'); b.width = w; b.segments = 2; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(40)

# ---------------------------------------------------------------- 3. 주변: 용암 바다, 뒤 절벽(존재 R6 확인·형태 미확인 → 어두운 덩어리)
import bmesh
def plane(name, z, size, mat):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    o = D.objects.new(name, me); scene.collection.objects.link(o); o.location = (0, 0, z); o.data.materials.append(mat); return o


lava_o = plane("Stage_Lava_Sea", CFG["lava_z"], 600, MAT["lava"]); lava_o["stage_role"] = "ground"
# 뒤 절벽(R6 존재 확인, 형태 미확인)은 게임 배경에서 화면을 크게 가려 넣지 않음 — 남은 작업 목록에 기록

# ---------------------------------------------------------------- 4. 조명
for o in [o for o in D.objects if o.type == 'LIGHT']:
    D.objects.remove(o)
world = D.worlds.new("STAGE_World"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.32, 0.14, 0.08, 1); bg.inputs[1].default_value = 0.9


def light(name, kind, loc, energy, color, rot=None, size=None, spot=None):
    ld = D.lights.new(name, kind); ld.energy = energy; ld.color = color
    if size is not None:
        if kind == 'AREA':
            ld.size = size
        else:
            ld.shadow_soft_size = size
    if spot:
        ld.spot_size = math.radians(spot); ld.spot_blend = 0.6
    lo_ = D.objects.new(name, ld); scene.collection.objects.link(lo_); lo_.location = loc
    if rot:
        lo_.rotation_euler = rot
    return lo_


light("Stage_Sun_Smoke", 'SUN', (0, 0, 50), 3.4, (1.0, 0.74, 0.55), rot=(math.radians(42), 0, math.radians(-120)), size=None)
D.lights["Stage_Sun_Smoke"].angle = math.radians(12)
light("Stage_Lava_Bounce", 'AREA', (0, 0, -12), 14000, (1.0, 0.38, 0.12), rot=(0, 0, 0), size=160)          # 아래에서 비추는 용암 반사광
sp = D.objects["Hangar_Spotlights"]
spy = sorted({round((sp.matrix_world @ Vector(c)).y, 1) for c in sp.bound_box})
for k, y in enumerate(CFG["eave_spot_y"]):
    light(f"Stage_Eave_Spot_{k}", 'SPOT', (CFG["eave_spot_x"], y, CFG["eave_spot_z"]), 2600, (1.0, 0.88, 0.7), rot=(math.radians(22), 0, math.radians(90)), size=0.4, spot=70)
ex, ey, ez = CFG["entrance_light"]
light("Stage_Entrance_Spot", 'SPOT', (ex, ey, ez), 900, (0.85, 0.92, 1.0), rot=(math.radians(30), 0, math.radians(90)), size=0.2, spot=80)
for k, (x, y) in enumerate(CFG["edge_light_xy"]):
    light(f"Stage_Edge_Blue_{k}", 'POINT', (x, y, 0.35), 60, (0.45, 0.72, 1.0), size=0.1)

# ---------------------------------------------------------------- 5. 카메라: 게임 출력 / 영화 비교 구분
for o in D.objects:
    if o.type == 'CAMERA' and o.name in ("Perspective_View_R2_match", "Far_View_R6_match"):
        o.name = "Film_Compare_" + o.name
for n in ("Isometric_View", "Top_View"):
    if n in D.objects:
        D.objects.remove(D.objects[n])
G = CFG["game"]
cd = D.cameras.new("Game_Output_Iso"); cd.type = 'ORTHO'; cd.clip_start = 1; cd.clip_end = 1000; cd.sensor_fit = 'HORIZONTAL'
cam = D.objects.new("Game_Output_Iso", cd); scene.collection.objects.link(cam)
cam.rotation_euler = (math.radians(60), 0, math.radians(-45))
cam["note"] = "게임 투영과 동일: 직교, 고도 30°, 방위 45°. 화면 x = (gx−gy)·20, y = (gx+gy)·10 − z·24.49 (1배). 게임 좌표 gx = OX − Y, gy = OY − X"
scene.camera = cam
scene["stage_config"] = json.dumps(CFG, ensure_ascii=False)
scene["hidden_in_final"] = json.dumps(sorted(set(hidden_log)), ensure_ascii=False)

# ---------------------------------------------------------------- 렌더 설정
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 48; scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6; scene.cycles.light_sampling_threshold = 0.01
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = 0.35
scene.render.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("SAVED", OUT_BLEND, "hidden", len(set(hidden_log)))

if "--preview" in sys.argv:
    sys.path.insert(0, HERE)
    import stage_cam
    den = float(sys.argv[sys.argv.index("--preview") + 1]) if len(sys.argv) > sys.argv.index("--preview") + 1 else 0.5
    W, H, ox, oy = stage_cam.setup(scene, cam, CFG, density=den)
    scene.cycles.samples = 16
    scene.render.filepath = os.path.join(HERE, "renders", "preview_iso.png"); os.makedirs(os.path.dirname(scene.render.filepath), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("PREVIEW", W, H, ox, oy)
