"""무스타파 착륙장 블록아웃 v0.1 — Blender(bpy) 자동 생성.

실행:  <bpy 가상환경>/bin/python create_mustafar.py   (또는  blender -b -P create_mustafar.py)
입력:  dimensions.json (같은 폴더) — 치수는 전부 여기서 바꾼다.
출력:  mustafar_blockout.blend, top_view.png, isometric_view.png, perspective_view.png
       (+ work/*_raw.png 라벨 없는 원본, work/labels.json)

좌표: 1 Blender unit = 1 m. Blender X = 게임 x, Blender Y = -게임 y, Z 위.
착륙장 중심 = 원점, 바닥 윗면 Z=0. 절벽 +Y(긴 뒤 변), 시설 건물 +X(짧은 변), 용암 -Y·-X.
색: 회색 = CONFIRMED, 황토 = PROBABLE, 자홍 = UNKNOWN, 초록 = 크기 비교용(건축물 아님).
"""
import json, math, os, sys, time

import bpy  # bmesh보다 먼저 (bpy 모듈 빌드는 bpy를 불러야 bmesh가 생김)
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
os.makedirs(WORK, exist_ok=True)

with open(os.path.join(HERE, "dimensions.json"), encoding="utf-8") as f:
    DIM = json.load(f)


def v(*path):
    """dimensions.json 값 읽기: v('platform', 'width_x')."""
    node = DIM
    for p in path:
        node = node[p]
    return node["value"] if isinstance(node, dict) and "value" in node else node


# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

COLORS = {
    "CONFIRMED": (0.50, 0.50, 0.50),
    "PROBABLE":  (0.66, 0.56, 0.34),
    "UNKNOWN":   (0.70, 0.28, 0.58),
    "SCALE_REF": (0.22, 0.66, 0.30),
    "LAVA_REF":  (0.30, 0.07, 0.04),
}
MATS = {}


def material(key):
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(f"M_{key}")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    c = COLORS[key]
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    m.diffuse_color = (*c, 1)
    MATS[key] = m
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*color, 1)
    return m


COLLS = {}


def coll(name):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        COLLS[name] = c
    return COLLS[name]


def make_obj(name, bm, conf, basis, collection, mat=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll(collection).objects.link(ob)
    ob.data.materials.append(mat or material(conf))
    ob["confidence"] = conf
    ob["basis"] = basis
    return ob


def add_box(bm, lo, hi, matrix=None):
    """축 정렬 상자 (lo, hi 모서리). matrix가 있으면 상자 중심 기준으로 변환."""
    lo, hi = Vector(lo), Vector(hi)
    ctr = (lo + hi) / 2
    half = (hi - lo) / 2
    vs = []
    for sx, sy, sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        p = Vector((sx*half.x, sy*half.y, sz*half.z))
        if matrix is not None:
            p = matrix @ p
        vs.append(bm.verts.new(ctr + p))
    for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        bm.faces.new([vs[i] for i in f])


def add_prism(bm, poly, z0, z1):
    """XY 다각형(반시계)을 z0~z1로 세운 기둥."""
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])


def inset_polygon(poly, d):
    """볼록 다각형(반시계)을 안쪽으로 d만큼 줄인다."""
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        e = (b - a).normalized()
        nrm = Vector((-e.y, e.x))  # 반시계 다각형의 안쪽 법선
        lines.append((a + nrm * d, e))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1.x * d2.y - d1.y * d2.x
        t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / den
        q = p1 + d1 * t
        out.append((q.x, q.y))
    return out


def add_ring(bm, outer, inner, z0, z1):
    """바깥·안쪽 다각형 사이의 벽 띠 (측벽용)."""
    n = len(outer)
    ob = [bm.verts.new((x, y, z0)) for x, y in outer]
    ot = [bm.verts.new((x, y, z1)) for x, y in outer]
    ib = [bm.verts.new((x, y, z0)) for x, y in inner]
    it = [bm.verts.new((x, y, z1)) for x, y in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])   # 바깥면
        bm.faces.new([it[i], it[j], ib[j], ib[i]])   # 안쪽면
        bm.faces.new([ot[i], ot[j], it[j], it[i]])   # 윗면
        bm.faces.new([ib[i], ib[j], ob[j], ob[i]])   # 아랫면


# ---------------------------------------------------------------- dimensions
W, D = v("platform", "width_x"), v("platform", "depth_y")
X0, X1, Y0, Y1 = -W / 2, W / 2, -D / 2, D / 2      # +X = 시설 쪽 짧은 변, +Y = 절벽 쪽 긴 변
CFL, CFR = v("platform", "chamfer_front_left"), v("platform", "chamfer_front_right")
DECK_T = v("platform", "deck_thickness")

OUTLINE = [(X0 + CFL, Y0), (X1 - CFR, Y0), (X1, Y0 + CFR), (X1, Y1), (X0, Y1), (X0, Y0 + CFL)]
OUTLINE = [p for i, p in enumerate(OUTLINE) if p != OUTLINE[i - 1]]   # 깎지 않은 모서리의 겹친 점 제거

F_LEN, F_OFF, F_DEP = v("facility", "length_y"), v("facility", "offset_y"), v("facility", "depth_x")
FY0, FY1 = F_OFF - F_LEN / 2, F_OFF + F_LEN / 2
WALL_H, WALL_T = v("facility", "wall_height"), v("facility", "wall_thickness")
ROOF_T, OVERHANG = v("facility", "roof_thickness"), v("facility", "roof_overhang")
XW = X1                     # 시설 정면 벽의 바깥면 (착륙장 쪽, -X를 봄)
XB = X1 + F_DEP             # 시설 뒷면

E_CY, E_W, E_H = v("corridor_entrance", "center_y"), v("corridor_entrance", "width"), v("corridor_entrance", "height")
E_LEN = v("corridor_entrance", "length")
ey0, ey1 = E_CY - E_W / 2, E_CY + E_W / 2

BEH, CTOP, CBOT = v("cliff", "behind_depth"), v("cliff", "top_z"), v("cliff", "bottom_z")
GAP, PIER_Y = v("cliff", "gap_y"), v("cliff", "pier_front_y")
YC = Y1 + GAP               # 절벽 면

# ---------------------------------------------------------------- 1. Landing_Platform
bm = bmesh.new()
add_prism(bm, OUTLINE, -DECK_T, 0.0)
make_obj("Landing_Platform", bm, "CONFIRMED",
         "R1·R2·R3·R6: 넓고 평평한 판(불규칙 다각형 판재), 위에서 보면 거의 직사각형. 치수는 UNKNOWN", "Architecture")

# ---------------------------------------------------------------- 2. Platform_Sidewalls
SW_D, SW_T = v("sidewalls", "depth"), v("sidewalls", "thickness")
bm = bmesh.new()
add_ring(bm, OUTLINE, inset_polygon(OUTLINE, SW_T), -SW_D, -DECK_T)
make_obj("Platform_Sidewalls", bm, "PROBABLE",
         "R1·R6: 판 측면이 두꺼운 어두운 띠. 깊이·두께 미측정", "Architecture")

# ---------------------------------------------------------------- 3. Hangar_Walls (시설 정면, +X 짧은 변)
bm = bmesh.new()
add_box(bm, (XW, FY0, 0), (XW + WALL_T, ey0, WALL_H))            # 개구부 앞쪽(-Y)
add_box(bm, (XW, ey1, 0), (XW + WALL_T, FY1, WALL_H))            # 개구부 뒤쪽(+Y)
add_box(bm, (XW, ey0, E_H), (XW + WALL_T, ey1, WALL_H))          # 개구부 위
make_obj("Hangar_Walls", bm, "CONFIRMED",
         "R2: 착륙장 옆 높은 시설 벽면, R6: 착륙장 오른쪽 시설 탑. 높이 PROBABLE, 길이·개구부 UNKNOWN", "Architecture")

bm = bmesh.new()   # 옆·뒤 벽: 어느 자료에도 안 보임
add_box(bm, (XW, FY0, 0), (XB, FY0 + WALL_T, WALL_H))
add_box(bm, (XW, FY1 - WALL_T, 0), (XB, FY1, WALL_H))
add_box(bm, (XB - WALL_T, FY0, 0), (XB, FY1, WALL_H))
make_obj("Hangar_Walls_Side_Back", bm, "UNKNOWN",
         "시설 옆·뒤 벽: 자료에 안 보임. 건물 부피 표시용", "Architecture")

bm = bmesh.new()   # 시설 아래: 용암까지 내려가는 탑 몸체
add_box(bm, (XW + 1, FY0 + 2, CBOT), (XB - 1, FY1 - 2, -DECK_T))
make_obj("Facility_Base", bm, "PROBABLE",
         "R6: 시설 탑이 착륙장 높이 아래로 용암까지 이어짐. 형태는 단순 상자", "Architecture")

# ---------------------------------------------------------------- 4. Hangar_Roof
bm = bmesh.new()
add_box(bm, (XW - OVERHANG, FY0, WALL_H), (XB, FY1, WALL_H + ROOF_T))
make_obj("Hangar_Roof", bm, "PROBABLE",
         "R2: 벽 위 보에 조명이 매달려 아래를 비춤 → 지붕 끝/처마. R5(게임)도 처마. 두께·내민 길이 UNKNOWN", "Architecture")

# ---------------------------------------------------------------- 5. Structural_Pillars (비스듬한 핀)
P_SP, P_W, P_D = v("pillars", "spacing"), v("pillars", "width"), v("pillars", "depth")
LEAN = math.radians(v("pillars", "lean_deg"))
P_LEN = WALL_H / math.cos(LEAN)
shift = math.tan(LEAN) * WALL_H / 2
rot = Matrix.Rotation(LEAN, 3, 'X')   # 벽면(YZ) 안에서 옆으로 기울임
bm = bmesh.new()
n_p = 0
y = FY0 + P_SP / 2
while y < FY1 - P_W:
    ends = (y - shift, y, y + shift)
    if not any(ey0 - P_W < e < ey1 + P_W for e in ends):   # 개구부 앞은 비움
        add_box(bm, (XW - P_D, y - P_W / 2, WALL_H / 2 - P_LEN / 2),
                (XW, y + P_W / 2, WALL_H / 2 + P_LEN / 2), matrix=rot)
        n_p += 1
    y += P_SP
make_obj("Structural_Pillars", bm, "CONFIRMED",
         "R2: 벽면에 비스듬한 지지벽(핀)이 평행하게 반복, R6: 시설 탑의 비스듬한 부재. 간격·기울기 PROBABLE", "Architecture")

# ---------------------------------------------------------------- 6. Corridor_Entrance
bm = bmesh.new()
FR = 0.5
add_box(bm, (XW - 0.4, ey0 - FR, 0), (XW + WALL_T, ey0, E_H + FR))           # 문설주
add_box(bm, (XW - 0.4, ey1, 0), (XW + WALL_T, ey1 + FR, E_H + FR))
add_box(bm, (XW - 0.4, ey0, E_H), (XW + WALL_T, ey1, E_H + FR))              # 상인방
xi0, xi1 = XW + WALL_T, XW + WALL_T + E_LEN
add_box(bm, (xi0, ey0 - FR, 0), (xi1, ey0, E_H))                              # 통로 벽
add_box(bm, (xi0, ey1, 0), (xi1, ey1 + FR, E_H))
add_box(bm, (xi0, ey0 - FR, E_H), (xi1, ey1 + FR, E_H + FR))                  # 통로 천장
add_box(bm, (xi1, ey0, 0), (xi1 + FR, ey1, E_H))                              # 통로 끝(임시 막음)
add_box(bm, (xi0, ey0, -DECK_T), (xi1, ey1, 0))                               # 통로 바닥
make_obj("Corridor_Entrance", bm, "UNKNOWN",
         "영화 프레임에 입구가 안 보임. R4·R5(게임 재현)의 건물 정면 개구부를 임시로 따름", "Architecture")

# ---------------------------------------------------------------- 7. Stairwell_Parapet (R2 오른쪽 아래)
SX0, SY0 = v("stair_box", "x0"), v("stair_box", "y0")
SSX, SSY = v("stair_box", "size_x"), v("stair_box", "size_y")
SPH, SDROP = v("stair_box", "parapet_height"), v("stair_box", "stair_drop")
bm = bmesh.new()
T = 0.35
add_box(bm, (SX0, SY0, 0), (SX0 + SSX, SY0 + T, SPH))
add_box(bm, (SX0, SY0 + SSY - T, 0), (SX0 + SSX, SY0 + SSY, SPH))
add_box(bm, (SX0 + SSX - T, SY0, 0), (SX0 + SSX, SY0 + SSY, SPH))
n_steps = 8
run = (SSX - T) / n_steps
for i in range(n_steps):
    z = -SDROP * (i + 1) / n_steps
    add_box(bm, (SX0 + i * run, SY0 + T, z - 0.3), (SX0 + (i + 1) * run, SY0 + SSY - T, z))
make_obj("Stairwell_Parapet", bm, "PROBABLE",
         "R2 오른쪽 아래: 안쪽에서 빛나는 세로 틈이 있는 낮은 상자, 아래로 계단. 크기·방향 UNKNOWN", "Architecture")
bm = bmesh.new()
add_box(bm, (SX0, SY0 + T, -0.02), (SX0 + SSX - T, SY0 + SSY - T, 0.02))
make_obj("Stairwell_Opening_Marker", bm, "PROBABLE", "계단 구멍 위치 표시(바닥 절개는 다음 버전)", "Architecture",
         mat=emissive("M_StairGlow", (1.0, 0.75, 0.45), 0.4))

# ---------------------------------------------------------------- 8. Cliff_Connection
bm = bmesh.new()
add_box(bm, (X0 - 25, YC, CBOT), (XB + 15, YC + BEH, CTOP))                   # 뒤 절벽
add_box(bm, (X0 + SW_T, PIER_Y, CBOT), (X1 - SW_T, YC, -SW_D))               # 착륙장 밑 받침 덩어리 (절벽까지)
make_obj("Cliff_Connection", bm, "PROBABLE",
         "R6: 착륙장 뒤는 거대한 절벽, 아래는 어두운 덩어리가 절벽까지 이어짐. 형태·틈(gap) 치수는 UNKNOWN", "Architecture")

# ---------------------------------------------------------------- 9. 정체 불명 아치형 물체 (R1·R6)
UA = lambda k: v("unknown_arched_object", k)
bm = bmesh.new()
ax0, ay0, asx, asy, ah = UA("x0"), UA("y0"), UA("size_x"), UA("size_y"), UA("height")
add_box(bm, (ax0, ay0, 0), (ax0 + asx, ay0 + asy, ah))
make_obj("Unknown_Arched_Object", bm, "UNKNOWN",
         "R1·R6: 착륙장 뒤 오른쪽의 밝은 아치형 갈빗대 물체. 격납고 캐노피인지 우주선인지 판별 불가 → 자리만 표시", "Architecture")

# ---------------------------------------------------------------- 조명 위치(형상만, 실제 광원 아님)
EDGE_SP, EDGE_IN = v("lights", "edge_spacing"), v("lights", "edge_inset")
light_mat = emissive("M_EdgeLight", (0.55, 0.75, 1.0), 6.0)
bm = bmesh.new()
inner_l = inset_polygon(OUTLINE, EDGE_IN)
n_l = 0
for i in range(len(inner_l)):
    a, b = Vector(inner_l[i]), Vector(inner_l[(i + 1) % len(inner_l)])
    if a.x > X1 - EDGE_IN - 0.01 and b.x > X1 - EDGE_IN - 0.01:
        continue  # 시설 벽 쪽 변엔 없음
    L = (b - a).length
    k = max(1, round(L / EDGE_SP))
    for j in range(k):
        p = a + (b - a) * (j / k)
        add_box(bm, (p.x - 0.25, p.y - 0.25, 0), (p.x + 0.25, p.y + 0.25, 0.18))
        n_l += 1
make_obj("Perimeter_Lights", bm, "CONFIRMED",
         "R2·R3: 가장자리 바닥의 청백색 작은 등. 간격 PROBABLE", "Lights", mat=light_mat)

SPOT_SP = v("lights", "spot_spacing")
bm = bmesh.new()
y = FY0 + SPOT_SP / 2
while y < FY1:
    add_box(bm, (XW - OVERHANG + 0.5, y - 0.4, WALL_H - 0.3), (XW - OVERHANG + 1.3, y + 0.4, WALL_H))
    y += SPOT_SP
make_obj("Hangar_Spotlights", bm, "PROBABLE",
         "R2: 벽 위에서 아래로 비추는 조명. 개수·간격 PROBABLE", "Lights",
         mat=emissive("M_Spot", (1.0, 0.85, 0.6), 8.0))

# ---------------------------------------------------------------- 크기 비교용 (초록, 건축물 아님)
HH = v("scale_refs", "human_height")
for nm, key in [("Ref_ObiWan_1.8m", "obiwan_xy"), ("Ref_Anakin_1.8m", "anakin_xy")]:
    x, y = v("scale_refs", key)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.28, radius2=0.28, depth=HH,
                          matrix=Matrix.Translation((x, y, HH / 2)))
    make_obj(nm, bm, "SCALE_REF", "크기 비교용 인물 1.8 m", "Scale_Refs")
x, y = v("scale_refs", "padme_xy")
bm = bmesh.new()
add_box(bm, (x - 0.8, y - 0.25, 0), (x + 0.8, y + 0.25, 0.3))
make_obj("Ref_Padme_lying", bm, "SCALE_REF", "R2: 쓰러진 파드메 위치", "Scale_Refs")

SL, SWD = v("scale_refs", "skiff_length"), v("scale_refs", "skiff_width")
scx, scy = v("scale_refs", "skiff_center")
RW = v("scale_refs", "ramp_width")
bm = bmesh.new()
add_box(bm, (scx - SWD / 2, scy - SL / 2, 1.5), (scx + SWD / 2, scy + SL / 2, 6.5))   # 긴 축 = Y
ramp_y = v("scale_refs", "obiwan_xy")[1] + 1.5
r0, r1 = scx + SWD / 2 - 1.0, scx + SWD / 2 + 4.5      # 시설 쪽(+X)으로 내려오는 경사로
vs = [bm.verts.new(p) for p in [(r0, ramp_y - RW/2, 2.5), (r0, ramp_y + RW/2, 2.5), (r1, ramp_y + RW/2, 0.05), (r1, ramp_y - RW/2, 0.05),
                                 (r0, ramp_y - RW/2, 2.2), (r0, ramp_y + RW/2, 2.2), (r1 - 0.4, ramp_y + RW/2, 0.0), (r1 - 0.4, ramp_y - RW/2, 0.0)]]
bmesh.ops.convex_hull(bm, input=vs)
make_obj("Ref_Skiff_29m_box", bm, "SCALE_REF", "파드메 우주선 외곽 상자(공개 설정 약 29 m)+경사로 2.4 m. 위치 UNKNOWN", "Scale_Refs")

# ---------------------------------------------------------------- 용암 높이 기준면
bm = bmesh.new()
LZ = v("lava_level_z")
add_box(bm, (-150, -150, LZ - 0.5), (150, 150, LZ))
make_obj("Lava_Level_Ref", bm, "UNKNOWN", "용암 높이 비교용 평면", "Environment", mat=material("LAVA_REF"))

# ---------------------------------------------------------------- 조명·월드
world = bpy.data.worlds.new("World")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.20, 0.20, 0.22, 1)
bg.inputs["Strength"].default_value = 0.9
scene.world = world

sun_data = bpy.data.lights.new("Key_Sun", 'SUN')
sun_data.energy = 2.2
sun_data.angle = math.radians(4)
sun = bpy.data.objects.new("Key_Sun", sun_data)
coll("Environment").objects.link(sun)
sun.rotation_euler = (math.radians(42), 0, math.radians(-150))

# ---------------------------------------------------------------- 렌더 설정
R = DIM["render"]
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = R["samples"]
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = R["resolution"]
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
ASPECT = scene.render.resolution_x / scene.render.resolution_y

FIT = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in ("Lava_Level_Ref", "Cliff_Connection")]


def fit_ortho(cam, objs, margin=1.08):
    """카메라 방향은 두고, 위치·ortho_scale을 objs가 다 들어오게 맞춘다."""
    rot = cam.rotation_euler.to_matrix()
    right, up, fwd = rot.col[0], rot.col[1], -rot.col[2]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    rs = [p.dot(right) for p in pts]
    us = [p.dot(up) for p in pts]
    fs = [p.dot(fwd) for p in pts]
    cr, cu = (min(rs) + max(rs)) / 2, (min(us) + max(us)) / 2
    w, h = max(rs) - min(rs), max(us) - min(us)
    cam.data.ortho_scale = max(w, h * ASPECT) * margin
    cam.location = right * cr + up * cu - fwd * 300
    cam.data.clip_end = 1000


def new_cam(name, ortho):
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO' if ortho else 'PERSP'
    co = bpy.data.objects.new(name, cd)
    coll("Cameras").objects.link(co)
    return co


cam_top = new_cam("Top_View", True)
cam_top.rotation_euler = (0, 0, 0)
fit_ortho(cam_top, FIT + [bpy.data.objects["Cliff_Connection"]], 1.04)

cam_iso = new_cam("Isometric_View", True)
# 게임 투영(src/core/iso.js): 직교, 고도 30°, 방위 45° (2:1). -X-Y 쪽에서 봐서 절벽(+Y)·시설(+X)이 뒤로 감
cam_iso.rotation_euler = (math.radians(60), 0, math.radians(-45))
fit_ortho(cam_iso, FIT, 1.06)

cam_per = new_cam("Perspective_View", False)
cam_per.data.lens = 24
cam_per.data.clip_end = 1000
cam_per.location = (-4.0, -31.0, 10.0)     # R2처럼: 우주선 왼쪽, 시설 벽 오른쪽, 절벽 쪽을 봄
target = Vector((13.0, 8.0, 4.0))
cam_per.rotation_euler = (target - cam_per.location).to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- 렌더 + 라벨
LABEL_ANCHOR = {   # 라벨을 붙일 월드 좌표(보이는 곳)
    "Landing_Platform": (-8, -12, 0), "Platform_Sidewalls": (-6, Y0, -3),
    "Hangar_Walls": (XW, FY0 + 4, WALL_H * 0.75), "Hangar_Walls_Side_Back": (XB, FY0 + 6, WALL_H * 0.5),
    "Hangar_Roof": (XW + F_DEP / 2, FY0 + 8, WALL_H + ROOF_T),
    "Structural_Pillars": (XW - P_D, FY1 - 8, WALL_H * 0.35), "Corridor_Entrance": (XW - 0.4, E_CY, E_H * 0.5),
    "Facility_Base": (XB, FY0 + 6, -20),
    "Stairwell_Parapet": (SX0 + SSX / 2, SY0, SPH), "Cliff_Connection": (X0 - 10, YC, CTOP * 0.5),
    "Unknown_Arched_Object": (ax0 + asx / 2, ay0 + asy / 2, ah),
    "Perimeter_Lights": (X0 + 1.2, Y0 + 8, 0), "Hangar_Spotlights": (XW - OVERHANG, FY1 - 4, WALL_H),
    "Ref_Skiff_29m_box": (scx, scy, 6.5), "Ref_Anakin_1.8m": (*v("scale_refs", "anakin_xy"), HH),
}
TAG_COL = {"CONFIRMED": (210, 210, 210), "PROBABLE": (240, 200, 110), "UNKNOWN": (240, 125, 215),
           "SCALE_REF": (120, 235, 140)}


def annotate(raw, out, cam, title, extra=None):
    from PIL import Image, ImageDraw, ImageFont
    labels = []
    for nm, p in LABEL_ANCHOR.items():
        ob = bpy.data.objects[nm]
        if ob.hide_render:
            continue
        c = world_to_camera_view(scene, cam, Vector(p))
        if 0.02 <= c.x <= 0.98 and 0.05 <= c.y <= 0.98 and c.z > 0:
            labels.append((nm, ob["confidence"], c.x * scene.render.resolution_x,
                           (1 - c.y) * scene.render.resolution_y))
    im = Image.open(raw).convert("RGB")
    dr = ImageDraw.Draw(im)
    fdir = "/usr/share/fonts/truetype/dejavu/"
    f = ImageFont.truetype(fdir + "DejaVuSans.ttf", 14)
    fb = ImageFont.truetype(fdir + "DejaVuSans-Bold.ttf", 17)
    placed = []
    for nm, conf, x, y in sorted(labels, key=lambda l: l[3]):
        txt = f"{nm} [{conf}]"
        col = TAG_COL[conf]
        tw = dr.textlength(txt, font=f)
        tx = min(max(x + 8, 4), im.width - tw - 6)
        ty = min(max(y - 9, 38), im.height - 22)
        while any(abs(ty - py) < 19 and tx < px + pw and px < tx + tw for px, py, pw in placed):
            ty += 19   # 겹치면 아래로
        placed.append((tx, ty, tw))
        dr.line((x, y, tx, ty + 8), fill=col, width=1)
        dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=col, outline=(0, 0, 0))
        dr.rectangle((tx - 3, ty - 1, tx + tw + 3, ty + 17), fill=(0, 0, 0))
        dr.text((tx, ty), txt, font=f, fill=col)
    dr.rectangle((0, 0, im.width, 30), fill=(0, 0, 0))
    dr.text((10, 5), title, font=fb, fill=(255, 255, 255))
    legend = [("CONFIRMED", "grey CONFIRMED"), ("PROBABLE", "ochre PROBABLE"),
              ("UNKNOWN", "magenta UNKNOWN"), ("SCALE_REF", "green scale-ref")]
    lx = im.width - 10 - sum(dr.textlength(n, font=f) + 14 for _, n in legend)
    for k, name in legend:
        dr.text((lx, 7), name, font=f, fill=TAG_COL[k])
        lx += dr.textlength(name, font=f) + 14
    if extra:
        extra(im, dr, f)
    im.save(out)
    return labels


def scale_bar(px_per_m):
    def draw(im, dr, f):
        L = 10 * px_per_m
        x0, y0 = 20, im.height - 26
        dr.rectangle((x0 - 6, y0 - 18, x0 + L + 60, y0 + 12), fill=(0, 0, 0))
        dr.line((x0, y0, x0 + L, y0), fill=(255, 255, 255), width=3)
        for xx in (x0, x0 + L):
            dr.line((xx, y0 - 6, xx, y0 + 6), fill=(255, 255, 255), width=2)
        dr.text((x0 + L + 8, y0 - 9), "10 m", font=f, fill=(255, 255, 255))
    return draw


VIEWS = [
    ("top_view", cam_top, "Top View (ortho, roof hidden; +Y cliff, +X facility) - blockout v0.1"),
    ("isometric_view", cam_iso, "Isometric View (ortho, 30 deg elevation, 45 deg azimuth = game 2:1) - v0.1"),
    ("perspective_view", cam_per, "Reference Perspective (compare with film still R2) - v0.1"),
]
all_labels = {}
for key, cam, title in VIEWS:
    scene.camera = cam
    for nm in ("Hangar_Roof", "Hangar_Spotlights"):   # 위에서 볼 땐 지붕을 숨겨 벽·기둥·입구 배치를 보이게
        bpy.data.objects[nm].hide_render = (key == "top_view")
    raw = os.path.join(WORK, f"{key}_raw.png")
    scene.render.filepath = raw
    t = time.time()
    bpy.ops.render.render(write_still=True)
    extra = None
    if cam.data.type == 'ORTHO':
        ppm = scene.render.resolution_x / cam.data.ortho_scale
        if key == "top_view":
            extra = scale_bar(ppm)
        print(f"VIEW {key}: ortho_scale={cam.data.ortho_scale:.1f} m -> {ppm:.2f} px/m (game = 28.28 px/m)")
    out = os.path.join(HERE, f"{key}.png")
    all_labels[key] = annotate(raw, out, cam, title, extra)
    print(f"RENDER OK {key} {time.time() - t:.1f}s -> {out}")

with open(os.path.join(WORK, "labels.json"), "w", encoding="utf-8") as f:
    json.dump(all_labels, f, ensure_ascii=False, indent=1)

for o in bpy.data.objects:
    o.hide_render = False
scene.camera = cam_iso
blend = os.path.join(HERE, "mustafar_blockout.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("SAVED", blend)
print(f"SUMMARY pillars={n_p} edge_lights={n_l} mesh_objects={len([o for o in bpy.data.objects if o.type == 'MESH'])}")
for o in bpy.data.objects:
    o.hide_render = False
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == 'MESH':
        d = o.dimensions
        print(f"  {o.name:26s} {o.get('confidence', ''):10s} {d.x:6.1f} x {d.y:6.1f} x {d.z:6.1f} m")
