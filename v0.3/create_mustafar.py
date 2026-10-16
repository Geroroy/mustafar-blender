"""무스타파 착륙장 블록아웃 v0.3(작업 사본) — 2026-10-16 낮은 상자 해석 정정(하강 계단 판정 철회, 가설은 숨긴 컬렉션) — Blender(bpy) 자동 생성. v0.2 스크립트를 복사해 4K 조사로 확인된 구조만 추가했다.
추가: A자 출입구와 보이는 안쪽 통로, 출입구 앞 바닥, 뒤쪽 난간, 상자 근처 연석, 낮은 상자의 바깥 경사 패널·단 테두리·안쪽 반복 부재(기능 UNKNOWN), 엇갈린 길쭉한 육각 바닥 판재. 새 치수는 dimensions.json v03의 후보값.

실행:  <bpy 가상환경>/bin/python create_mustafar.py
입력:  dimensions.json (같은 폴더), ../refs/ (영화 스틸 — 비교 이미지용)
출력:  mustafar_blockout_v0.3.blend, top_view.png, isometric_view.png, perspective_view.png,
       compare_R2.png, compare_R6.png  (+ work/*_raw.png)

좌표: 1 unit = 1 m. X = 짧은 변(+X 시설), Y = 긴 변(+Y 절벽, 뒤), Z 위. 판 중심 원점, 판재 윗면 ≈ 0.
색은 '형태' 신뢰도: 회색 C, 황토 P, 자홍 U. 철사틀 = 임시 자리(형태 미확인), 초록 철사틀 = 우주선 검증용.
라벨의 E/F = 존재(exist)/형태(form) 신뢰도.
"""
import json, math, os, random, time

import bpy  # bmesh보다 먼저
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(os.path.dirname(HERE), "refs")
WORK = os.path.join(HERE, "work")
os.makedirs(WORK, exist_ok=True)
DIM = json.load(open(os.path.join(HERE, "dimensions.json"), encoding="utf-8"))
# 출입구 접근 배치 후보(CR-006). 기본 .blend는 active 후보, MUSTAFAR_LAYOUT=<이름>이면 그 후보를 work/layouts/에 저장(이미지 렌더 생략)
LAYS = DIM["v03"]["entrance_layout"]
LAYOUT_NAME = os.environ.get("MUSTAFAR_LAYOUT") or LAYS["active"]
LAY = LAYS["candidates"][LAYOUT_NAME]
VARIANT = bool(os.environ.get("MUSTAFAR_LAYOUT"))


def v(*path):
    n = DIM
    for p in path:
        n = n[p]
    return n["value"] if isinstance(n, dict) and "value" in n else n


def conf(*path):
    n = DIM
    for p in path:
        n = n[p]
    return n.get("exist", "U"), n.get("form", "U")


# ---------------------------------------------------------------- scene / materials
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

FULL = {"C": "CONFIRMED", "P": "PROBABLE", "U": "UNKNOWN"}
COLORS = {"C": (0.50, 0.50, 0.50), "P": (0.66, 0.56, 0.34), "U": (0.70, 0.28, 0.58),
          "PLATE_A": (0.47, 0.47, 0.47), "PLATE_B": (0.36, 0.36, 0.37),
          "SHIP": (0.20, 0.85, 0.30), "WIRE_U": (0.85, 0.25, 0.70), "LAVA": (0.30, 0.07, 0.04)}
MATS = {}


def material(key, emit=0.0):
    k = (key, emit)
    if k in MATS:
        return MATS[k]
    m = bpy.data.materials.new(f"M_{key}_{emit}")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    c = COLORS.get(key, key) if isinstance(key, str) else key
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = 0.85
    if emit:
        b.inputs["Emission Color"].default_value = (*c, 1)
        b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*c, 1)
    MATS[k] = m
    return m


COLLS = {}


def coll(name):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        COLLS[name] = c
    return COLLS[name]


LABEL = {}   # 객체 이름 → (E, F)


def make_obj(name, bm, ef, basis, collection, mat=None, wire=None, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll(collection).objects.link(ob)
    ob.data.materials.append(mat or material(ef[1]))
    ob["exist"], ob["form"], ob["basis"] = FULL[ef[0]], FULL[ef[1]], basis
    if wire:
        mod = ob.modifiers.new("wire", 'WIREFRAME')
        mod.thickness = wire
        mod.use_replace = True
        ob.visible_shadow = False   # 철사틀(임시·검증용)은 그림자를 드리우지 않음
    if parent:
        ob.parent = parent
    LABEL[name] = ef
    return ob


def add_box(bm, lo, hi, matrix=None):
    lo, hi = Vector(lo), Vector(hi)
    ctr, half = (lo + hi) / 2, (hi - lo) / 2
    vs = []
    for sx, sy, sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        p = Vector((sx*half.x, sy*half.y, sz*half.z))
        if matrix is not None:
            p = matrix @ p
        vs.append(bm.verts.new(ctr + p))
    for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        bm.faces.new([vs[i] for i in f])


def add_prism(bm, poly, z0, z1):
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new([bot[i], bot[j], top[j], top[i]])


def add_prism_x(bm, poly_yz, x0, x1):
    """YZ 평면 볼록 다각형을 X 방향(x0~x1)으로 밀어낸 프리즘."""
    a = [bm.verts.new((x0, y, z)) for y, z in poly_yz]
    b = [bm.verts.new((x1, y, z)) for y, z in poly_yz]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(poly_yz)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))


def clip_rect(poly, x0, y0, x1, y1):
    """볼록 다각형을 축 정렬 사각형 안쪽만 남긴다(Sutherland–Hodgman, 경계 위 꼭짓점은 남김)."""
    def half(pts, inside, cut):
        out = []
        for i in range(len(pts)):
            p, q = pts[i - 1], pts[i]
            ip, iq = inside(p), inside(q)
            if iq:
                if not ip: out.append(cut(p, q))
                out.append(q)
            elif ip:
                out.append(cut(p, q))
        return out
    def cx(v):  # x = v 와의 교점
        return lambda p, q: (v, p[1] + (q[1] - p[1]) * (v - p[0]) / (q[0] - p[0]))
    def cy(v):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (v - p[1]) / (q[1] - p[1]), v)
    for inside, cut in ((lambda t: t[0] >= x0, cx(x0)), (lambda t: t[0] <= x1, cx(x1)),
                        (lambda t: t[1] >= y0, cy(y0)), (lambda t: t[1] <= y1, cy(y1))):
        if len(poly) < 3:
            return []
        poly = half(poly, inside, cut)
    dedup = [q for i, q in enumerate(poly) if math.dist(q, poly[i - 1]) > 1e-6]   # 1) 겹친 점 제거
    clean = []                                                                   # 2) 한 직선 위 점 제거(이음매 inset 계산용)
    for i in range(len(dedup)):
        p, q, r = dedup[i - 1], dedup[i], dedup[(i + 1) % len(dedup)]
        if abs((q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])) > 1e-9:
            clean.append(q)
    poly = clean
    return poly if len(poly) >= 3 and abs(area(poly)) > 1e-3 else []


def inset_polygon(poly, d):
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        e = (b - a).normalized()
        lines.append((a + Vector((-e.y, e.x)) * d, e))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1.x * d2.y - d1.y * d2.x
        t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / den
        q = p1 + d1 * t
        out.append((q.x, q.y))
    return out


def add_ring(bm, outer, inner, z0, z1):
    n = len(outer)
    ob_ = [bm.verts.new((x, y, z0)) for x, y in outer]
    ot = [bm.verts.new((x, y, z1)) for x, y in outer]
    ib = [bm.verts.new((x, y, z0)) for x, y in inner]
    it = [bm.verts.new((x, y, z1)) for x, y in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([ob_[i], ob_[j], ot[j], ot[i]])
        bm.faces.new([it[i], it[j], ib[j], ib[i]])
        bm.faces.new([ot[i], ot[j], it[j], it[i]])
        bm.faces.new([ib[i], ib[j], ob_[j], ob_[i]])


def area(poly):
    return 0.5 * sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly))) * -1


def split(poly, c, d):
    """볼록 다각형을 점 c, 방향 d의 직선으로 둘로 자른다."""
    s = [d[0] * (p[1] - c[1]) - d[1] * (p[0] - c[0]) for p in poly]
    a, b = [], []
    n = len(poly)
    for i in range(n):
        p, q, sp, sq = poly[i], poly[(i + 1) % n], s[i], s[(i + 1) % n]
        (a if sp >= 0 else b).append(p)
        if (sp > 0 > sq) or (sp < 0 < sq):
            t = sp / (sp - sq)
            x = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            a.append(x); b.append(x)
    return a, b


def thin(poly):
    """너무 가는 조각인지: 넓이 대비 둘레."""
    per = sum(math.dist(poly[i], poly[i - 1]) for i in range(len(poly)))
    return abs(area(poly)) / (per * per) < 0.035


# ---------------------------------------------------------------- dimensions
X1 = v("platform", "facility_edge_x")          # 시설 쪽 가장자리 (좌표 기준)
W = v("platform", "width_x")
X0 = X1 - W
Y0, Y1 = v("platform", "front_end_y"), v("platform", "back_end_y")
if LAY["platform_front_y"] is not None:      # 후보 A2: 판 앞 변을 기존 범위(−30~−19) 안에서 옮김
    Y0 = LAY["platform_front_y"]
L = Y1 - Y0
ANG = math.radians(v("platform", "corner_angle_deg"))
EDGE_D, TOP_T = v("platform", "edge_face_depth"), v("platform", "deck_top_thickness")


def outline(w, l, ang):
    """앞 변(+X)과 왼쪽 변이 ang을 이루는 평행사변형(반시계). 앞 오른쪽 모서리(시설 쪽)를 (X1, Y0)에 고정."""
    side = Vector((math.cos(ang), math.sin(ang))) * l
    fr = Vector((X1, Y0)) - Vector((side.x, 0)) * 0
    fl = fr - Vector((w, 0))
    return [tuple(fl), tuple(fr), tuple(fr + side), tuple(fl + side)]


OUT = outline(W, L, ANG)
PLATE_TOP = 0.0
DECK_Z = -0.06   # 판재 아래 윗판 면

GAP, TZ = v("facility", "trench_gap"), v("facility", "trench_floor_z")
BEAM, ROOF = v("facility", "beam_height"), v("facility", "roof_top_z")
OVER, FDEP = v("facility", "roof_overhang"), v("facility", "depth_x")
XW = X1 + GAP           # 시설 벽면
FY0, FY1 = v("facility", "front_end_y"), v("facility", "back_end_y")
FY0_ORIG = FY0                     # 핀 배열 기준(후보가 시설 앞 끝을 연장해도 기존 핀 위치는 그대로, 연장 구간에는 핀을 두지 않음)
_ya_need = LAY["center_y"] - DIM["v03"]["entrance"]["width"]["value"] / 2 - 1.2
if _ya_need < FY0:                  # 후보 A2·A3: 시설 앞 끝은 출입구 테두리를 담을 만큼만 연장(11748 오른쪽은 용암 배경 — 더 늘리지 않음)
    FY0 = _ya_need

# 낮은 상자(이전 이름 '계단 상자', 판 위, 가장자리 안쪽). 판 관통 구멍은 숨긴 가설에서만(DESCENT=True일 때)
SCX, SCY = v("stairwell", "corner_back_left")
SSX, SSY = v("stairwell", "size_x"), v("stairwell", "size_y")
HOLE = (SCX, SCY - SSY, SCX + SSX, SCY)      # x0, y0, x1, y1 — 낮은 상자의 바닥 범위
DESCENT = DIM["v03"]["low_box"]["descent_hypothesis_in_default"]["value"]   # False: 판 관통 구멍 없음(기본안)

facility_root = bpy.data.objects.new("Facility_Structure", None)
coll("Facility_Structure").objects.link(facility_root)

# ---------------------------------------------------------------- 1. Landing_Platform (윗판) + Platform_Sidewalls
bm = bmesh.new()
hx0, hy0, hx1, hy1 = HOLE
for lo, hi in ([((X0, Y0), (hx0, Y1)), ((hx1, Y0), (X1, Y1)), ((hx0, Y0), (hx1, hy0)), ((hx0, hy1), (hx1, Y1))] if DESCENT else [((X0, Y0), (X1, Y1))]):
    if hi[0] - lo[0] > 0.01 and hi[1] - lo[1] > 0.01:
        add_box(bm, (lo[0], lo[1], -TOP_T), (hi[0], hi[1], DECK_Z))   # 윗판 (기본안: 구멍 없음, 각도 90° 기준)
make_obj("Landing_Platform", bm, conf("platform", "width_x"),
         "R1·R2·R3·R6: 판 존재 확인. 외곽은 R6 정사영 분석의 평행사변형(모서리 85~98°), 치수 범위는 dimensions.json. 판재 이음매 아래 면이라 어두운 회색(외곽 불확실성은 Outline_Alt·모서리 표지로 표시)", "Platform",
         mat=material((0.16, 0.16, 0.17)))
bm = bmesh.new(); add_ring(bm, OUT, inset_polygon(OUT, 0.6), -EDGE_D, -TOP_T)
make_obj("Platform_Sidewalls", bm, conf("platform", "edge_face_depth"),
         "R6: 판 앞면 띠 약 4 m", "Platform")

# 모서리 표지: 영화에서 모서리가 보인 정도
CORNER_CONF = {0: ("C", "P", "R6에서 앞 왼쪽 모서리가 보임"), 3: ("P", "U", "R6: 뒤 왼쪽 — 점등 줄이 시작되는 곳"),
               1: ("P", "U", "앞 오른쪽: 시설 쪽 높은 띠에 가려 안 보임"), 2: ("P", "U", "뒤 오른쪽: 가려짐")}
CORNER_NAME = {0: "Corner_FrontLeft", 1: "Corner_FrontRight", 2: "Corner_BackRight", 3: "Corner_BackLeft"}
for i, (e, fm, why) in CORNER_CONF.items():
    x, y = OUT[i]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.35, radius2=0.35, depth=3.0,
                          matrix=Matrix.Translation((x, y, 1.5)))
    make_obj(CORNER_NAME[i], bm, (e, fm), why, "Platform_Corner_Markers")

# 외곽 불확실 범위: 모서리 각도 범위 끝의 두 외곽(철사틀)
for nm, ang, ratio in [("Outline_Alt_84.7deg", 84.7, 1.31), ("Outline_Alt_98.4deg", 98.4, 1.51)]:
    poly = outline(W, W * ratio, math.radians(ang))
    bm = bmesh.new(); add_prism(bm, poly, 0.02, 0.05)
    make_obj(nm, bm, ("P", "U"), f"R6 분석의 카메라 고도 범위 끝(각 {ang}°, 길이:너비 {ratio})", "Platform_Outline_Range",
             mat=material("WIRE_U"), wire=0.12)

# ---------------------------------------------------------------- 2. Floor_Plates (v0.3: 엇갈린 길쭉한 육각 판, 11712)
rng = random.Random(DIM["floor_plates"]["seed"])
HW, HS, HP = (DIM["v03"]["floor_hex"][k]["value"] for k in ("width", "straight", "point"))
inner_ = inset_polygon(OUT, 0.45)
ix0, ix1 = min(q[0] for q in inner_), max(q[0] for q in inner_)
iy0, iy1 = min(q[1] for q in inner_), max(q[1] for q in inner_)
plates = []
step_y = HS + HP
col = 0
x = ix0 - HW
while x < ix1 + HW:
    yoff = step_y if col % 2 else 0.0          # 이웃 열은 한 칸(직선+끝)만큼 엇갈림
    y = iy0 - 2 * step_y + yoff
    while y < iy1 + step_y:
        hexp = [(x, y + HP), (x + HW / 2, y), (x + HW, y + HP), (x + HW, y + HP + HS), (x + HW / 2, y + 2 * HP + HS), (x, y + HP + HS)]
        q = clip_rect(hexp, ix0, iy0, ix1, iy1)
        if q:
            plates.append(q)
        y += 2 * step_y                          # 열 안 세로 간격 = 2×(직선+끝) → 판 면적 = 반복 단위 면적
    x += HW / 2
    col += 1


def cut_hole(p):
    """(가설 DESCENT 전용) 판재에서 상자 바닥 구멍을 뺀다: 구멍 바깥 네 영역(왼·오른·앞·뒤)으로 각각 잘라 모은다(경계 위 꼭짓점 보존)."""
    BIG = 1e4
    out = []
    for r in ((-BIG, -BIG, hx0, BIG), (hx1, -BIG, BIG, BIG), (hx0, -BIG, hx1, hy0), (hx0, hy1, hx1, BIG)):
        q = clip_rect(p, *r)
        if q:
            out.append(q)
    return out


if DESCENT:
    plates = [q for p in plates for q in cut_hole(p)]
SEAM = v("floor_plates", "seam_width")
HMIN, HMAX = v("floor_plates", "height_min"), v("floor_plates", "height_max")
bm = bmesh.new()
mat_idx = []
for p in plates:
    if area(p) < 0:
        p = p[::-1]
    q = inset_polygon(p, SEAM / 2)
    if abs(area(q)) < 0.3:
        continue
    h = rng.uniform(HMIN, HMAX) - HMAX   # 윗면이 0 근처, 판마다 조금씩 다름
    before = len(bm.faces)
    add_prism(bm, q, DECK_Z, h)
    mat_idx += [0 if rng.random() < 0.55 else 1] * (len(bm.faces) - before)
bm.faces.ensure_lookup_table()
for f_, m in zip(bm.faces, mat_idx):
    f_.material_index = m
ob = make_obj("Floor_Plates", bm, ("C", "U"),
              "11712·11233·11625: 엇갈린 띠로 반복되는 길쭉한 육각(화살촉) 판재(종류 VERIFIED). 폭·길이·띠 방향은 후보값, 배치는 생성값", "Platform",
              mat=material("PLATE_A"))
ob.data.materials.append(material("PLATE_B"))
N_PLATES = len(plates)
os.makedirs(os.path.join(WORK, "layouts"), exist_ok=True)
json.dump({"hex": [HW, HS, HP], "clip": [ix0, iy0, ix1, iy1], "hole": list(HOLE) if DESCENT else None, "plates_before_seam": [[list(map(float, q)) for q in p] for p in plates]},
          open(os.path.join(WORK, "layouts", f"floor_plates_{LAYOUT_NAME}.json") if VARIANT else os.path.join(WORK, "floor_plates.json"), "w"))

# ---------------------------------------------------------------- 3. 시설 구조 (하나로 이어진 건축: 트렌치 통로 → 벽·핀 → 처마 보·지붕)
_E0 = DIM["v03"]["entrance"]
FC_Y1 = (LAY["center_y"] + _E0["width"]["value"] / 2 + 1.2 + LAYS["forecourt_margin"]["value"]) if LAY["forecourt"] else None   # 앞마당 +Y 끝(트렌치 시작)
TR_Y0 = FC_Y1 if LAY["forecourt"] else FY0
bm = bmesh.new()
add_box(bm, (X1, TR_Y0, TZ - 0.5), (XW, FY1, TZ))                       # 아래 통로 바닥(앞마당 후보에서는 앞마당 뒤부터)
add_box(bm, (X1 - 0.01, TR_Y0, TZ - 0.5), (X1 + 0.3, FY1, -TOP_T))       # 판 가장자리 아래 옹벽 (트렌치 쪽 면)
make_obj("Corridor_Lower_Walkway", bm, conf("facility", "trench_gap"),
         "R2: 바닥 가장자리와 시설 벽 사이 낮은 띠 → 벽 밑동을 따라가는 아래 통로로 해석(v0.2 자리 표시). 근거였던 '그쪽으로 내려가는 계단'은 2026-10-16 낮은 상자 해석 정정으로 철회 — 상자와 연결하지 않음. 바닥면·폭·깊이는 안 보임(UNKNOWN)",
         "Facility_Structure", parent=facility_root)

E = DIM["v03"]["entrance"]
EYC, ELC, EW, ESF = (E[k]["value"] for k in ("center_y", "light_center_height", "width", "shoulder_frac"))
EYC = LAY["center_y"]                # 배치 후보의 출입구 중심(H1·A1 −16.0, A2·A3 −20.1)
XE = LAY.get("front_x") or XW        # 출입구 면(문틀 뒤 벽면) x. A3만 판 가장자리 쪽(14.8), 나머지는 시설 벽면
EH = ELC + E["light_below_apex"]["value"]   # 문 안쪽 꼭짓점 (조명 중심 = 영화 측정 "바닥→꼭대기 조명")
EZS = ELC * ESF                      # 어깨점 높이 (측정 정의와 같은 기준: 문 높이 = 바닥→조명)
EY0, EY1 = EYC - EW / 2, EYC + EW / 2
EPAD = 1.2                           # 출입구 테두리 폭
bm = bmesh.new(); bm_bay = bmesh.new()
ya, yb = EY0 - EPAD, EY1 + EPAD
if XE == XW:
    add_box(bm, (XW, FY0, TZ), (XW + 1.0, EY0 - EPAD, BEAM))             # 벽면 (출입구 앞쪽 구간)
    add_box(bm, (XW, EY1 + EPAD, TZ), (XW + 1.0, FY1, BEAM))             # 벽면 (출입구 뒤쪽 구간)
else:
    add_box(bm, (XW, FY0, TZ), (XW + 1.0, FY1, BEAM))                    # 후보 A3: 시설 벽면은 막힌 면(출입구는 앞으로 나온 면에)
for poly in ([(ya, TZ), (EY0, TZ), (EY0, EZS), (ya, EZS)], [(EY1, TZ), (yb, TZ), (yb, EZS), (EY1, EZS)],
             [(EY0, TZ), (EY1, TZ), (EY1, 0.0), (EY0, 0.0)],                                     # 문턱 아래
             [(ya, EZS), (EY0, EZS), (EYC, EH), (ya, EH)], [(EY1, EZS), (yb, EZS), (yb, EH), (EYC, EH)],
             [(ya, EH), (yb, EH), (yb, BEAM), (ya, BEAM)]):
    add_prism_x(bm if XE == XW else bm_bay, poly, XE, XE + 1.0)
make_obj("Hangar_Walls", bm, ("C", "P"),
         "R2: 착륙장 시설 쪽 벽, R6: 판의 시설 쪽 변을 따라가는 높은 띠. 높이는 보까지 측정(6.3~7.1 m)",
         "Facility_Structure", parent=facility_root)

bm = bmesh.new()
add_box(bm, (XW - OVER, FY0, BEAM), (XW + FDEP, FY1, ROOF))             # 보 + 지붕 덩어리
make_obj("Hangar_Roof", bm, conf("facility", "roof_top_z"),
         "R2: 조명이 달린 보가 벽보다 앞으로 나옴(높이 측정 6.7 m). 그 위 지붕 두께·안쪽 깊이는 R6 축척 추정",
         "Facility_Structure", parent=facility_root)

bm = bmesh.new()
add_box(bm, (XW + 1.0, FY0, TZ), (XW + FDEP, FY1, BEAM))                 # 건물 몸체(안쪽 미상)
make_obj("Facility_Body_Unknown", bm, ("P", "U"), "벽 뒤 건물 몸체: 안쪽 형태 자료 없음", "Facility_Structure",
         mat=material("WIRE_U"), wire=0.15, parent=facility_root)
if XE != XW:
    make_obj("Entrance_Bay_Front", bm_bay, ("P", "U"),
             f"배치 후보 {LAYOUT_NAME}: 판 가장자리 쪽으로 나온 출입구 면(x {XE}). M8(11748 역투영) 후보 위치. 문 위 높이(보 높이까지)·폭은 형태용 가정",
             "Facility_Structure", mat=material((0.42, 0.36, 0.30)), parent=facility_root)
    bm = bmesh.new(); add_box(bm, (XE + 1.0, ya, TZ), (XW, yb, BEAM))
    make_obj("Entrance_Bay_Unknown", bm, ("P", "U"),
             f"배치 후보 {LAYOUT_NAME}: 출입구 면(x {XE})이 판 가장자리 쪽으로 나와 있을 때 그 뒤에서 시설 본체(x {XW})까지 이어지는 부분. 형태·크기 자료 없음(UNKNOWN) — 자리 표시만",
             "Facility_Structure", mat=material("WIRE_U"), wire=0.1, parent=facility_root)

LEAN = math.radians(v("fins", "lean_deg"))
FSP, FW, FD = v("fins", "spacing"), v("fins", "width"), v("fins", "depth")
FH = BEAM - TZ
FLEN_ = FH / math.cos(LEAN)
rot = Matrix.Rotation(-LEAN, 3, 'X')    # 위가 +Y(뒤)로
bm = bmesh.new()
n_fin = 0
y = FY0_ORIG + FSP * 0.6
SWEEP = FH / 2 * math.tan(LEAN) + FW / 2
fins_skipped = []
while y < FY1 - FSP * 0.3:
    zc = (TZ + BEAM) / 2
    if y + SWEEP > EY0 - EPAD and y - SWEEP < EY1 + EPAD:       # 배치 가설 H1: 출입구를 가리는 핀은 두지 않음(배열 근거 UNKNOWN)
        fins_skipped.append(round(y, 1)); y += FSP; continue
    add_box(bm, (XW - FD, y - FW / 2, zc - FLEN_ / 2), (XW, y + FW / 2, zc + FLEN_ / 2), matrix=rot)
    n_fin += 1
    y += FSP
make_obj("Structural_Pillars", bm, ("C", "P"),
         "R2: 벽 앞 핀, 벽면 안에서 위가 뒤로 28~36° 기울어짐(측정). 간격 4~7 m",
         "Facility_Structure", parent=facility_root)

bm = bmesh.new()
n_spot = 0
for y in v("spotlights", "y_positions"):
    if FY0 < y < FY1:
        add_box(bm, (XW - OVER + 0.3, y - 0.35, BEAM - 0.35), (XW - OVER + 1.0, y + 0.35, BEAM)); n_spot += 1
make_obj("Hangar_Spotlights", bm, ("C", "P"), "R2: 보 아래 조명 두 개의 위치·높이 측정(6.4~7.3 m, 간격 6.7 m), 나머지는 같은 간격",
         "Facility_Structure", mat=material((1.0, 0.85, 0.6), 8.0), parent=facility_root)

# ---------------------------------------------------------------- v0.3: A자 출입구 (11726·11748)
FT_ = 0.35
SL_ = (EH - EZS) / (EW / 2)                 # 경사 테두리 기울기(높이/가로)


def a_band(bm, o0, o1, xf):
    """출입구 윤곽을 가로로 o0~o1 m 밖으로 민 A자 띠(세로 문설주 + 경사 테두리), 벽 앞 xf m 돌출."""
    for sgn, yin in ((-1, EY0), (1, EY1)):
        y0_, y1_ = sorted((yin + sgn * o0, yin + sgn * o1))
        add_box(bm, (XE - xf, y0_, 0.0), (XE, y1_, EZS))
        poly = [(yin + sgn * o1, EZS), (yin + sgn * o0, EZS), (EYC, EH + o0 * SL_), (EYC, EH + o1 * SL_)]
        cy_, cz_ = sum(q[0] for q in poly) / 4, sum(q[1] for q in poly) / 4
        add_prism_x(bm, sorted(poly, key=lambda q: math.atan2(q[1] - cz_, q[0] - cy_)), XE - xf, XE)


bm = bmesh.new()
LAYERS = E["frame_layers"]["value"]
for o0r, o1r, xf in LAYERS:                  # 겹친 프레임: 안쪽 층이 더 많이 돌출
    a_band(bm, o0r * EW, o1r * EW, xf)
make_obj("Facility_A_Entrance", bm, ("C", "U"),
         "11726·11748: A자 출입구와 넓은 경사 바깥 테두리·겹친 프레임(존재 VERIFIED). 조명 중심 높이 2.4 m·어깨 폭 1.45 m는 후보(M3), 테두리 폭은 출입구 폭 비율(근사), 돌출 깊이·평면 위치는 UNKNOWN",
         "Facility_Structure", parent=facility_root)
bm = bmesh.new(); add_box(bm, (XE - 0.45, EYC - 0.3, ELC - 0.1), (XE - 0.05, EYC + 0.3, ELC + 0.1))
make_obj("Facility_A_Entrance_Light", bm, ("C", "P"), "11726·11748: 출입구 꼭대기 조명. 중심 높이 = 측정 정의(바닥→꼭대기 조명) 후보 2.4 m", "Facility_Structure",
         mat=material((0.85, 0.9, 1.0), 8.0), parent=facility_root)
PD = E["passage_depth"]["value"]
bm = bmesh.new()
add_box(bm, (XE + 1.0, EY0, -0.1), (XE + 1.0 + PD, EY1, 0.0))                       # 통로 바닥
for y0_, y1_ in ((EY0 - 0.25, EY0), (EY1, EY1 + 0.25)):                             # 통로 옆벽(어깨점까지)
    add_box(bm, (XE + 1.0, y0_, 0.0), (XE + 1.0 + PD, y1_, EZS))
for (ys, ye) in ((EY0, EYC), (EY1, EYC)):                                           # 통로 경사 천장
    sgn = -1 if ys < EYC else 1
    poly = [(ys, EZS), (ye, EH), (ye, EH + 0.25), (ys + sgn * 0.25, EZS)]
    poly = sorted(poly, key=lambda q: math.atan2(q[1] - (EZS + EH) / 2, q[0] - (ys + ye) / 2))
    add_prism_x(bm, poly, XE + 1.0, XE + 1.0 + PD)
k_ = 0.0
while k_ < PD - 0.3:                                                                 # 옆벽 리브(반복 줄무늬로 보임)
    for yy in (EY0 + 0.02, EY1 - 0.08):
        add_box(bm, (XE + 1.2 + k_, yy, 0.1), (XE + 1.3 + k_, yy + 0.06, EZS - 0.05))
    k_ += 0.6
make_obj("Entrance_Passage_Visible", bm, ("C", "U"),
         "11748: 출입구 안으로 이어지는 통로(존재 VERIFIED). 4 m는 미확정 영역 앞 모델링 중단 위치(측정 아님), 벽 줄무늬는 리브로 보임(PROBABLE). 리브 복도(11878)와의 연결은 UNKNOWN — 만들지 않음",
         "Facility_Structure", parent=facility_root)
bm = bmesh.new(); add_box(bm, (XE + 1.0 + PD, EY0, 0.0), (XE + 1.0 + PD + 0.05, EY1, EH))
make_obj("Entrance_Passage_Unknown_End", bm, ("P", "U"), "미확정 영역 앞 모델링 중단 위치(영화에서 보이는 끝이 아님). 그 너머는 미확인 — 연결하지 않음", "Facility_Structure",
         mat=material("WIRE_U"), wire=0.05, parent=facility_root)
if LAY["apron"]:
    bm = bmesh.new(); add_box(bm, (X1, EY0 - 1.0, -TOP_T), (XW, EY1 + 1.0, DECK_Z))
    make_obj("Entrance_Apron", bm, ("P", "U"),
             "배치 가설 H1(출입구 임시 위치·좁은 앞 바닥·핀 2개 삭제를 함께 관리, 보존 후보 — 기본 배치로 확정하지 않음): 11726·11748에서 출입구 앞 바닥이 문턱까지 이어짐(PROBABLE). 좁은 다리 형태 자체는 가설이며 상자 뒤에서만 닿음(CR-006 검사). 트렌치 폭·깊이는 v0.2 그대로",
             "Facility_Structure", mat=material((0.16, 0.16, 0.17)), parent=facility_root)
if LAY["forecourt"]:
    bm = bmesh.new(); add_box(bm, (X1, Y0, -TOP_T), (XE, FC_Y1, DECK_Z))
    make_obj("Entrance_Forecourt_Floor", bm, ("P", "U"),
             f"배치 후보 {LAYOUT_NAME}: 11748에서 상자 옆 바닥이 문턱까지 끊김 없이 이어짐(VERIFIED) → 출입구 앞 구간에서는 트렌치가 끝나고 판 높이 바닥이 벽까지 이어진다고 둔 후보. "
             f"앞마당 +Y 끝(y {FC_Y1:.2f})·트렌치 끝 위치는 UNKNOWN(형태용). 판재 무늬·아래 구조는 만들지 않음",
             "Facility_Structure", mat=material((0.30, 0.29, 0.28)), parent=facility_root)
    bm = bmesh.new(); add_box(bm, (X1, FC_Y1, TZ), (XW, FC_Y1 + 0.05, DECK_Z))
    make_obj("Trench_End_Unknown", bm, ("P", "U"), f"배치 후보 {LAYOUT_NAME}: 트렌치가 시작하는 자리(영화에서 보이지 않음, UNKNOWN)", "Facility_Structure",
             mat=material("WIRE_U"), wire=0.05, parent=facility_root)

# 낮은 상자(이전 이름 '계단 상자'): 판 위, 시설 쪽 가장자리 안쪽. 2026-10-16 해석 정정 — 안의 반복 부재를 하강 계단으로 본 판정 철회.
# 기본안은 보이는 형태만(벽·테두리·안쪽 반복 부재·밝은 틈). 판 관통 구멍·하강 발판·하부 연결 없음. 기능 UNKNOWN.
PH, SBZ = v("stairwell", "parapet_height"), v("stairwell", "bottom_z")
T_ = 0.35
LB = DIM["v03"]["low_box"]
bm = bmesh.new()
add_box(bm, (hx0, hy0, DECK_Z), (hx0 + T_, hy1, PH))          # −X 벽
add_box(bm, (hx1 - T_, hy0, DECK_Z), (hx1, hy1, PH))          # +X 벽 — 안쪽 면에 밝은 틈
add_box(bm, (hx0, hy1 - T_, DECK_Z), (hx1, hy1, PH))          # +Y 끝 벽
add_box(bm, (hx0, hy0, DECK_Z), (hx1, hy0 + T_, PH))          # −Y 끝 벽(11246: 테두리가 사방으로 닫혀 보임)
make_obj("Low_Box", bm, ("C", "P"),
         "R2·11615·11246: 낮은 상자(존재 VERIFIED, 위치는 R2 측정). 기능 UNKNOWN — 하강 계단 판정은 철회(가설은 숨긴 컬렉션 Hypothesis_Stairwell_Descent). 높이 1.2 m는 v0.2 기준안 유지(후보 0.5~1.0 m는 미반영)",
         "Facility_Structure", parent=facility_root)
NIM, TG = LB["inner_members"]["count"]["value"], LB["inner_members"]["top_gap"]["value"]
bm = bmesh.new()
pitch_i = (hy1 - hy0 - 2 * T_) / NIM
for k in range(NIM):                                            # 안쪽 반복 경사 부재(11246, 톱니 모양) — 판 윗면 위에서만
    y0_ = hy0 + T_ + k * pitch_i
    add_prism_x(bm, [(y0_, DECK_Z), (y0_ + pitch_i, DECK_Z), (y0_ + pitch_i, PH - TG), (y0_ + pitch_i * 0.85, PH - TG)], hx0 + T_, hx1 - T_)
make_obj("Low_Box_Inner_Members", bm, ("C", "U"),
         "11246: 상자 안쪽에 반복되는 밝은 경사 부재(존재 VERIFIED, 개수 약 5 후보). 계단·환기·조명 등 기능 UNKNOWN. 판 윗면 아래 구조는 만들지 않음",
         "Facility_Structure", mat=material((0.75, 0.72, 0.66)), parent=facility_root)

# 숨긴 가설 컬렉션: 이전 하강 계단 해석(판 관통 구멍 표시 + 하강 발판). 기본 렌더·라벨에 나오지 않음
bm = bmesh.new()
nst = 10
for i in range(nst):
    z = DECK_Z + (SBZ - DECK_Z) * (i + 1) / nst
    y0 = hy1 - T_ - (SSY - T_) * (i + 1) / nst
    add_box(bm, (hx0 + T_, y0, z - 0.25), (hx1 - T_, y0 + (SSY - T_) / nst, z))
make_obj("Hypothesis_Descent_Steps", bm, ("P", "U"), "가설(기본안 제외): 상자 안 하강 계단 — 2026-10-16 판정 철회. 깊이 −3 m·도착 지점 미확인",
         "Hypothesis_Stairwell_Descent", mat=material("WIRE_U"), parent=facility_root)
bm = bmesh.new(); add_ring(bm, [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)], [(hx0 + 0.1, hy0 + 0.1), (hx1 - 0.1, hy0 + 0.1), (hx1 - 0.1, hy1 - 0.1), (hx0 + 0.1, hy1 - 0.1)], -TOP_T - 0.02, DECK_Z + 0.02)
make_obj("Hypothesis_Deck_Opening", bm, ("P", "U"), "가설(기본안 제외): 하강 계단을 위한 판 관통 구멍 자리", "Hypothesis_Stairwell_Descent",
         mat=material("WIRE_U"), wire=0.05, parent=facility_root)
coll("Hypothesis_Stairwell_Descent").hide_render = True
coll("Hypothesis_Stairwell_Descent").hide_viewport = True
SK = DIM["v03"]["stairwell_skin"]
SKO, RST, NEND = SK["skirt_out"]["value"], SK["rim_steps"]["value"], SK["end_tiers"]["value"]
bm = bmesh.new()
# 바깥 경사 패널: 위(난간 높이 − 단 높이)에서 아래(판)로 갈수록 SKO만큼 벌어짐. −X 면과 뒤(+Y) 끝만(+X는 판 가장자리)
zt = PH - sum(RST)
add_prism_x(bm, [(hy0, DECK_Z), (hy1, DECK_Z), (hy1, zt), (hy0, zt)], hx0 - 0.02, hx0)          # 이음 면
for poly_xz in ([(hx0 - SKO, DECK_Z), (hx0, DECK_Z), (hx0, zt), (hx0 - 0.06, zt)],):
    a = [bm.verts.new((x_, hy0, z_)) for x_, z_ in poly_xz]; b = [bm.verts.new((x_, hy1 + SKO, z_)) for x_, z_ in poly_xz]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i_ in range(4):
        bm.faces.new((a[i_], a[(i_ + 1) % 4], b[(i_ + 1) % 4], b[i_]))
add_prism_x(bm, [(hy1, DECK_Z), (hy1 + SKO, DECK_Z), (hy1 + 0.06, zt), (hy1, zt)], hx0, hx1)       # 뒤 끝 경사 패널
# 단이 진 윗테두리: 벽 위에 바깥쪽부터 낮아지는 단(형태)
for j, dz_ in enumerate(RST):
    z0_ = zt + sum(RST[:j]); inset = 0.12 * j
    add_box(bm, (hx0 - 0.06 + inset, hy0, z0_), (hx0 + T_, hy1 + 0.06 - inset, z0_ + dz_))
    add_box(bm, (hx0 + T_, hy1 - T_, z0_), (hx1, hy1 + 0.06 - inset, z0_ + dz_))
# 앞 끝(−Y) 계단식으로 낮아지는 바깥 단(형태만, 기능 UNKNOWN): 테두리 높이에서 판까지 NEND단, 상자 밖 0.9 m 안에서
for j in range(NEND):
    z1_ = PH * (NEND - j) / (NEND + 1); y1_ = hy0 - 0.3 * j
    add_box(bm, (hx0 - 0.06, y1_ - 0.3, DECK_Z), (hx0 + T_, y1_, z1_))
    add_box(bm, (hx1 - T_, y1_ - 0.3, DECK_Z), (hx1, y1_, z1_))
TZD = SK["side_trapezoids"]                                     # 긴 옆면(−X)의 반복 사다리꼴 구획(11246, 오목/볼록 미구분)
NT, GD = TZD["count"]["value"], TZD["panel_relief"]["value"]    # GD: 구획 판을 바깥으로 덧붙이는 두께(중립 표현, 홈 깊이 아님)
B0, B1 = TZD["band"]["value"]; WT, WB = TZD["top_bottom_width"]["value"]
pitch_ = (hy1 - hy0) / NT
face_x = lambda z: (hx0 - 0.06) - (SKO - 0.06) * (zt - z) / (zt - DECK_Z)       # 경사 패널 바깥면의 x(높이 z에서)
za, zb = DECK_Z + B0 * (zt - DECK_Z), DECK_Z + B1 * (zt - DECK_Z)
for j in range(NT):
    yc_ = hy0 + pitch_ * (j + 0.5)
    pts = []
    for z_, w_ in ((za, WB), (zb, WT)):
        for s_ in (-1, 1):
            y_ = yc_ + s_ * w_ * pitch_ / 2
            pts += [(face_x(z_) + 0.005, y_, z_), (face_x(z_) - GD, y_, z_)]
    bmesh.ops.convex_hull(bm, input=[bm.verts.new(p_) for p_ in pts])
make_obj("Low_Box_Outer_Skin", bm, ("C", "U"),
         "11246·11224·11736: 낮은 상자 바깥 경사 패널·단이 진 윗테두리·앞 끝의 계단식 바깥 단·긴 옆면의 반복 사다리꼴 구획(존재 VERIFIED, 형태만, 기능 UNKNOWN). 벌어짐·단 높이·단 수·구획 수·구획 판 두께(0.05 m, 오목/볼록 미구분의 중립 표현)는 후보. 높이 1.2 m·위치는 기준안 유지",
         "Facility_Structure", parent=facility_root)
bm = bmesh.new()
for k in range(5):   # 빛나는 틈 위치(형상만)
    yy = hy1 - 0.9 - k * 1.15
    add_box(bm, (hx1 - T_ - 0.06, yy - 0.3, 0.2), (hx1 - T_, yy + 0.3, 1.0))
make_obj("Low_Box_Lit_Slots", bm, ("C", "P"), "R2·11615: 상자 안쪽 면에서 밝게 보이는 세로 틈(존재 VERIFIED). 조명·반사 등 기능 UNKNOWN", "Facility_Structure",
         mat=material((1.0, 0.9, 0.75), 6.0), parent=facility_root)

# ---------------------------------------------------------------- 4. 조명·뒤 변 기둥
INS = v("edge_lights", "inset")
bm = bmesh.new(); n_l = 0
for y in v("edge_lights", "facility_edge_y"):
    add_box(bm, (X1 - INS - 0.3, y - 0.3, DECK_Z), (X1 - INS + 0.3, y + 0.3, 0.12)); n_l += 1
make_obj("Edge_Lights_Facility_Side", bm, ("C", "P"), "R2: 시설 쪽 가장자리 청색 등 3개, 위치 측정(간격 10.6·11.6 m)", "Lights",
         mat=material((0.55, 0.75, 1.0), 6.0))
bsp = v("edge_lights", "back_edge_spacing")
bl, br = Vector(OUT[3]), Vector(OUT[2])
bm = bmesh.new(); n_post = 0
k = max(1, round((br - bl).length / bsp))
for j in range(k + 1):
    p = bl + (br - bl) * (j / k) + Vector((0, 0.6))
    add_box(bm, (p.x - 0.2, p.y - 0.2, DECK_Z), (p.x + 0.2, p.y + 0.2, v("back_edge_posts", "height"))); n_post += 1
make_obj("Back_Edge_Posts", bm, ("P", "U"), "R6: 뒤 변 바로 바깥 점등 줄, R2: 먼 쪽 턱의 청색 등, R3: 등 달린 낮은 기둥", "Lights")
bm = bmesh.new()
for j in range(k + 1):
    p = bl + (br - bl) * (j / k) + Vector((0, 0.6))
    add_box(bm, (p.x - 0.22, p.y - 0.22, 0.8), (p.x + 0.22, p.y + 0.22, 1.0))
make_obj("Back_Edge_Post_Lights", bm, ("C", "U"), "R2·R6 점등", "Lights", mat=material((0.55, 0.75, 1.0), 6.0))
RH_ = DIM["v03"]["back_rail"]["height"]["value"]
bm = bmesh.new()
for j in range(k):                                     # v0.3: 기둥 사이 난간
    p = bl + (br - bl) * (j / k) + Vector((0, 0.6)); q = bl + (br - bl) * ((j + 1) / k) + Vector((0, 0.6))
    add_box(bm, (p.x + 0.2, p.y - 0.04, RH_ - 0.05), (q.x - 0.2, q.y + 0.04, RH_ + 0.03))
make_obj("Back_Edge_Rail", bm, ("C", "U"), "11206·11575·11625: 뒤쪽 키 큰 등 기둥 사이 난간(존재 VERIFIED). 높이는 후보", "Lights")
CB = DIM["v03"]["curbs"]
ch, cl, cg = CB["height"]["value"], CB["length"]["value"], CB["gap"]["value"]
cx0, cx1 = CB["x_range"]["value"]
bm = bmesh.new(); xx = cx0; n_curb = 0
while xx + cl <= cx1 + 1e-6:                           # v0.3: 상자 근처 앞 가장자리 연석
    add_box(bm, (xx, Y0 + 0.15, DECK_Z), (xx + cl, Y0 + 0.75, ch)); xx += cl + cg; n_curb += 1
make_obj("Edge_Curbs_Near_Stairwell", bm, ("C", "U"), "11726·11736·11748: 상자 근처 가장자리의 낮은 직사각 연석(존재 VERIFIED). 크기·구간은 후보", "Lights")

# ---------------------------------------------------------------- 5. 임시 자리(철사틀): 판 밑 지지, 시설 아래, 절벽
SB = v("placeholders", "support_bottom_z")
bm = bmesh.new()
inner = inset_polygon(OUT, 3.0)
top = [Vector((x, y, -EDGE_D)) for x, y in inner]
bot = [Vector((X0 + 5, Y1 - 12, SB)), Vector((X1 - 3, Y1 - 12, SB)), Vector((X1 - 3, Y1 + 2, SB)), Vector((X0 + 5, Y1 + 2, SB))]
bmesh.ops.convex_hull(bm, input=[bm.verts.new(p) for p in top + bot])
make_obj("Support_Placeholder", bm, ("P", "U"), "R6: 판 아래 어두운 덩어리. 형태를 확정하지 않음 — 임시 자리", "Placeholders",
         mat=material("WIRE_U"), wire=0.25)
bm = bmesh.new(); add_box(bm, (X1, FY0, SB), (XW + FDEP, FY1, TZ - 0.5))
make_obj("Facility_Base_Placeholder", bm, ("P", "U"), "R6: 시설 탑이 아래로 이어짐. 형태 미확인", "Placeholders",
         mat=material("WIRE_U"), wire=0.25)
CG, CH = v("placeholders", "cliff_gap"), v("placeholders", "cliff_height")
bm = bmesh.new(); add_box(bm, (X0 - 30, Y1 + CG, SB), (XW + FDEP + 20, Y1 + CG + 15, CH))
make_obj("Cliff_Placeholder", bm, ("C", "U"), "R6: 판 뒤 절벽(존재 확인). 거리·형태 미확인", "Placeholders",
         mat=material("WIRE_U"), wire=0.3)

# ---------------------------------------------------------------- 6. 우주선 검증 (초록 철사틀, 건축물 아님)
SL, SWS = v("skiff_check", "length"), v("skiff_check", "wingspan")
scx, scy = v("skiff_check", "center")
bm = bmesh.new()
add_box(bm, (scx - 4, scy - SL / 2, 2.0), (scx + 4, scy + SL / 2, 6.0))          # 몸체(폭은 임의)
add_box(bm, (scx - SWS / 2, scy - 4, 4.5), (scx + SWS / 2, scy + 2, 5.0))        # 날개폭 표시
make_obj("Skiff_Check_29m_x_49m", bm, ("C", "U"),
         "파드메 우주선 공개 설정 길이 29.2·날개폭 49.3 m(팬 자료). 위치는 R2 경사로 발치 측정에서 추정 — 검증 대상", "Scale_Check",
         mat=material("SHIP"), wire=0.18)
rfx, rfy = v("skiff_check", "ramp_foot")
bm = bmesh.new()
bmesh.ops.convex_hull(bm, input=[bm.verts.new(p) for p in [(rfx, rfy - 1.2, 0.02), (rfx, rfy + 1.2, 0.02), (scx + 4, rfy + 3.5 - 1.2, 2.5), (scx + 4, rfy + 3.5 + 1.2, 2.5)]])
make_obj("Ramp_Foot_Measured", bm, ("C", "P"), "R2 측정: 경사로 발치(가장자리에서 9.6~11.3 m)", "Scale_Check",
         mat=material("SHIP"), wire=0.1)
for nm, key, hh in [("Ref_ObiWan", "obiwan", 1.78), ("Ref_Anakin", "anakin", 1.85)]:
    x, y = DIM["characters_r2"][key]["value"]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.28, radius2=0.28, depth=hh,
                          matrix=Matrix.Translation((x, y, hh / 2)))
    make_obj(nm, bm, ("C", "P"), "R2 측정 위치(카메라 맞춤의 기준점)", "Scale_Check", mat=material("SHIP"))
x, y = DIM["characters_r2"]["padme"]["value"]
bm = bmesh.new(); add_box(bm, (x - 0.8, y - 0.25, 0), (x + 0.8, y + 0.25, 0.3))
make_obj("Ref_Padme", bm, ("C", "P"), "R2 측정 위치", "Scale_Check", mat=material("SHIP"))

# 용암 높이 기준면
bm = bmesh.new(); add_box(bm, (-200, -200, SB - 0.5), (200, 200, SB))
make_obj("Lava_Level_Ref", bm, ("C", "U"), "높이 비교용", "Environment", mat=material("LAVA"))

# ---------------------------------------------------------------- world / render
world = bpy.data.worlds.new("World"); world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.20, 0.20, 0.22, 1); bg.inputs["Strength"].default_value = 0.9
scene.world = world
sun = bpy.data.objects.new("Key_Sun", bpy.data.lights.new("Key_Sun", 'SUN'))
sun.data.energy = 2.2; sun.data.angle = math.radians(4)
coll("Environment").objects.link(sun)
sun.rotation_euler = (math.radians(42), 0, math.radians(-150))

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = DIM["render"]["samples"]
scene.cycles.use_denoising = True
RX, RY = DIM["render"]["resolution"]
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = 'Standard'


def set_res(x, y):
    scene.render.resolution_x, scene.render.resolution_y = x, y


def new_cam(name, ortho):
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO' if ortho else 'PERSP'
    cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd)
    coll("Cameras").objects.link(co)
    return co


def fit_ortho(cam, objs, aspect, margin=1.06):
    rot = cam.rotation_euler.to_matrix()
    right, up, fwd = rot.col[0], rot.col[1], -rot.col[2]
    pts = []
    for o in objs:
        dg = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        pts += [o.matrix_world @ Vector(c) for c in dg.bound_box]
    rs = [p.dot(right) for p in pts]; us = [p.dot(up) for p in pts]
    cam.data.ortho_scale = max(max(rs) - min(rs), (max(us) - min(us)) * aspect) * margin
    cam.location = right * (min(rs) + max(rs)) / 2 + up * (min(us) + max(us)) / 2 - fwd * 400


SHOW = [o for o in bpy.data.objects if o.type == 'MESH' and o.users_collection[0].name in
        ("Platform", "Facility_Structure", "Lights", "Platform_Corner_Markers")]

cam_top = new_cam("Top_View", True)
fit_ortho(cam_top, SHOW + [bpy.data.objects["Skiff_Check_29m_x_49m"]], RX / RY, 1.04)
cam_iso = new_cam("Isometric_View", True)
cam_iso.rotation_euler = (math.radians(60), 0, math.radians(-45))   # 게임 2:1 투영, 높은 구조가 뒤로
fit_ortho(cam_iso, SHOW, RX / RY, 1.06)

# R2 맞춤 카메라 (Reference Perspective)
cx_, cy_, cz_ = v("r2_camera", "location_from_back_corner")
cam_r2 = new_cam("Perspective_View_R2_match", False)
cam_r2.data.sensor_fit = 'HORIZONTAL'; cam_r2.data.sensor_width = 36.0
cam_r2.data.lens = DIM["r2_camera"]["lens_mm_36"]
AX, AY = DIM["r2_camera"]["anchor_A"]["value"]   # 측정의 기준점(시설 쪽 가장자리 선 위)
cam_r2.location = (AX + cx_, AY + cy_, cz_)
cam_r2.rotation_euler = (math.radians(90 - DIM["r2_camera"]["pitch_deg"]), 0, math.radians(DIM["r2_camera"]["yaw_deg"]))

# R6 맞춤 카메라 (멀리서 본 정사영 근사)
cam_r6 = new_cam("Far_View_R6_match", True)
cam_r6.rotation_euler = (math.radians(90 - DIM["r6_camera"]["elevation_deg"]), 0, math.radians(DIM["r6_camera"]["yaw_deg"]))
fit_ortho(cam_r6, SHOW, RX / RY, 1.6)

# ---------------------------------------------------------------- labels
from PIL import Image, ImageDraw, ImageFont
FD_ = "/usr/share/fonts/truetype/dejavu/"
FONT = ImageFont.truetype(FD_ + "DejaVuSans.ttf", 13)
FONTB = ImageFont.truetype(FD_ + "DejaVuSans-Bold.ttf", 17)
TAGC = {"C": (215, 215, 215), "P": (240, 200, 110), "U": (240, 125, 215)}
ANCH = {
    "Landing_Platform": (X0 + 6, Y0 + 5, 0), "Floor_Plates": (X0 + 12, Y0 + 14, 0), "Platform_Sidewalls": (X0 + 10, Y0, -2),
    "Hangar_Walls": (XW, FY0 + 3, BEAM * 0.5), "Hangar_Roof": (XW + FDEP / 2, FY1 - 6, ROOF),
    "Structural_Pillars": (XW - FD, 3, 2.0), "Hangar_Spotlights": (XW - OVER, FY0 + 9, BEAM - 0.3),
    "Corridor_Lower_Walkway": (X1 + GAP / 2, 17, TZ), "Low_Box": (hx0, hy0 + 1, PH),
    "Edge_Lights_Facility_Side": (X1 - INS, Y1 - 1.5, 0), "Back_Edge_Posts": (*OUT[3], 1.0), "Low_Box_Lit_Slots": (hx1 - T_, hy1 - 2, 1.0), "Low_Box_Inner_Members": (hx0 + 1.2, hy0 + 2.5, PH - TG),
    "Corner_FrontLeft": (*OUT[0], 3.0), "Corner_FrontRight": (*OUT[1], 3.0), "Corner_BackLeft": (*OUT[3], 3.0),
    "Support_Placeholder": (X0 + 10, Y0 + 12, -14), "Cliff_Placeholder": (X0 - 10, Y1 + CG, 20),
    "Skiff_Check_29m_x_49m": (scx - SWS / 2 + 4, scy, 5), "Facility_Body_Unknown": (XW + FDEP, 0, 3),
    "Outline_Alt_98.4deg": (*outline(W, W * 1.51, math.radians(98.4))[3], 0.05),
    "Facility_A_Entrance": (XE - 0.3, EYC, EH), "Entrance_Passage_Visible": (XE + 2.0, EYC, EZS * 0.5),
    "Back_Edge_Rail": ((OUT[2][0] + OUT[3][0]) / 2, OUT[3][1] + 0.6, RH_), "Edge_Curbs_Near_Stairwell": (cx0 + 1, Y0 + 0.4, ch),
    "Entrance_Apron": (X1 + 3, EY1 + 0.8, 0), "Low_Box_Outer_Skin": (hx0 - 0.3, hy1 + 0.3, 0.5),
}
if LAY["forecourt"]:
    ANCH["Entrance_Forecourt_Floor"] = (X1 + 3, (Y0 + FC_Y1) / 2, 0)


def annotate(raw, out, cam, title, skip=()):
    im = Image.open(raw).convert("RGB"); dr = ImageDraw.Draw(im)
    items = []
    for nm, p in ANCH.items():
        ob = bpy.data.objects.get(nm)
        if ob is None or ob.hide_render or nm in skip:
            continue
        c = world_to_camera_view(scene, cam, Vector(p))
        if 0.01 <= c.x <= 0.99 and 0.04 <= c.y <= 0.97 and c.z > 0:
            items.append((nm, LABEL[nm], c.x * im.width, (1 - c.y) * im.height))
    placed = []
    for nm, (e, fm), x, y in sorted(items, key=lambda t: t[3]):
        txt = f"{nm}  E:{e} F:{fm}"
        col = TAGC[fm]
        tw = dr.textlength(txt, font=FONT)
        tx = min(max(x + 8, 4), im.width - tw - 6); ty = min(max(y - 8, 36), im.height - 40)
        for _ in range(30):
            if not any(abs(ty - py) < 17 and tx < px + pw + 4 and px < tx + tw + 4 for px, py, pw in placed):
                break
            ty += 17
        placed.append((tx, ty, tw))
        dr.line((x, y, tx, ty + 7), fill=col)
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col, outline=(0, 0, 0))
        dr.rectangle((tx - 3, ty - 1, tx + tw + 3, ty + 15), fill=(0, 0, 0))
        dr.text((tx, ty), txt, font=FONT, fill=col)
    dr.rectangle((0, 0, im.width, 28), fill=(0, 0, 0))
    dr.text((8, 5), title, font=FONTB, fill=(255, 255, 255))
    leg = "colour = FORM confidence: grey C  ochre P  magenta U | wire = placeholder | green = ship/scale check | E/F = exist/form"
    dr.rectangle((0, im.height - 20, im.width, im.height), fill=(0, 0, 0))
    dr.text((8, im.height - 18), leg, font=FONT, fill=(220, 220, 220))
    im.save(out)
    return items


def render(cam, path, res):
    scene.camera = cam; set_res(*res); scene.render.filepath = path
    t = time.time(); bpy.ops.render.render(write_still=True)
    return time.time() - t


if VARIANT:                                   # 배치 후보 사본: 이미지 렌더 없이 저장만(가설 컬렉션은 컬렉션 단위로 계속 숨김)
    scene.camera = cam_iso; set_res(RX, RY)
    out_ = os.path.join(WORK, "layouts", f"layout_{LAYOUT_NAME}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out_)
    print("SAVED", out_, f"layout={LAYOUT_NAME} entrance_y={EYC} forecourt_y1={FC_Y1} platform_front_y={Y0} fins_skipped={fins_skipped}")
    raise SystemExit(0)

# 위에서 볼 땐 지붕을 숨겨 아래 구조가 보이게
LOG = {}
for nm in ("Hangar_Roof", "Hangar_Spotlights", "Facility_Body_Unknown", "Cliff_Placeholder"):
    bpy.data.objects[nm].hide_render = True
t = render(cam_top, os.path.join(WORK, "top_raw.png"), (RX, RY))
ppm = RX / cam_top.data.ortho_scale
LOG["top"] = annotate(os.path.join(WORK, "top_raw.png"), os.path.join(HERE, "top_view.png"), cam_top,
                      f"Top View v0.3 (roof/cliff hidden)  +X facility  +Y cliff   {ppm:.1f} px/m")
im = Image.open(os.path.join(HERE, "top_view.png")); dr = ImageDraw.Draw(im)
Lpx = 10 * ppm; dr.rectangle((10, im.height - 52, 30 + Lpx + 50, im.height - 24), fill=(0, 0, 0))
dr.line((20, im.height - 38, 20 + Lpx, im.height - 38), fill=(255, 255, 255), width=3)
dr.text((28 + Lpx, im.height - 46), "10 m", font=FONT, fill=(255, 255, 255)); im.save(os.path.join(HERE, "top_view.png"))
print(f"RENDER OK top {t:.1f}s  {ppm:.2f} px/m  plates={N_PLATES}")
for o in bpy.data.objects:
    o.hide_render = False

t = render(cam_iso, os.path.join(WORK, "iso_raw.png"), (RX, RY))
LOG["iso"] = annotate(os.path.join(WORK, "iso_raw.png"), os.path.join(HERE, "isometric_view.png"), cam_iso,
                      f"Isometric View v0.3 (ortho 30 deg / 45 deg = game 2:1)  {RX / cam_iso.data.ortho_scale:.1f} px/m")
print(f"RENDER OK iso {t:.1f}s")

for nm in ("Outline_Alt_84.7deg", "Outline_Alt_98.4deg"):
    bpy.data.objects[nm].hide_render = True
t = render(cam_r2, os.path.join(WORK, "persp_raw.png"), (RX, RY))
LOG["persp"] = annotate(os.path.join(WORK, "persp_raw.png"), os.path.join(HERE, "perspective_view.png"), cam_r2,
                        "Reference Perspective v0.3 = camera matched to film still R2 (f=3500px, h=5.05m)")
print(f"RENDER OK persp {t:.1f}s")

# ---------------------------------------------------------------- 비교 이미지
# R2: 같은 카메라, 영화 화면비(2954×1238)로 렌더 → 나란히 + 겹침
t = render(cam_r2, os.path.join(WORK, "r2match_raw.png"), (1280, 536))
film = Image.open(os.path.join(REFS, "R2_film_lecture.jpg")).convert("RGB").crop((0, 305, 2954, 1543)).resize((1280, 536), Image.LANCZOS)
from PIL import ImageEnhance, ImageOps
film_b = ImageEnhance.Brightness(ImageOps.autocontrast(film, 1)).enhance(1.4)
ren = Image.open(os.path.join(WORK, "r2match_raw.png")).convert("RGB")
over = Image.blend(film_b, ren, 0.45)
H = 536
sheet = Image.new("RGB", (1280, H * 3 + 3 * 30), (0, 0, 0)); dr = ImageDraw.Draw(sheet)
for i, (img, cap) in enumerate([(film_b, "FILM R2 (brightened)  'Don't lecture me'"),
                                (ren, "BLOCKOUT v0.3 - same camera (fitted from the two actors' heights)"),
                                (over, "OVERLAY 55% film / 45% render")]):
    y0 = i * (H + 30)
    dr.text((8, y0 + 6), cap, font=FONTB, fill=(255, 255, 255))
    sheet.paste(img, (0, y0 + 30))
sheet.save(os.path.join(HERE, "compare_R2.png"))
print(f"RENDER OK compare_R2 {t:.1f}s")

# R6: 정사영 근사 카메라. 앞 왼쪽 모서리와 앞 오른쪽 모서리를 영화 좌표에 맞춰 닮음 변환
t = render(cam_r6, os.path.join(WORK, "r6match_raw.png"), (1280, 720))
ren6 = Image.open(os.path.join(WORK, "r6match_raw.png")).convert("RGB")


def px(cam, p, w, h):
    c = world_to_camera_view(scene, cam, Vector(p))
    return (c.x * w, (1 - c.y) * h)


set_res(1280, 720)
a_r = px(cam_r6, (*OUT[0], 0), 1280, 720); b_r = px(cam_r6, (*OUT[1], 0), 1280, 720)
gif = Image.open(os.path.join(REFS, "R6_film_facility_wide.gif")); gif.seek(43)
f6 = gif.convert("RGB")
S6 = 4   # 영화 픽셀 4배 확대
crop = (40, 230, 340, 400)
f6c = f6.crop(crop).resize(((crop[2] - crop[0]) * S6, (crop[3] - crop[1]) * S6), Image.LANCZOS)
a_f = ((120 - crop[0]) * S6, (321 - crop[1]) * S6); b_f = ((200 - crop[0]) * S6, (335 - crop[1]) * S6)
# 렌더 → 영화 닮음 변환 (두 점)
import cmath
za, zb, wa, wb = complex(*a_r), complex(*b_r), complex(*a_f), complex(*b_f)
k = (wb - wa) / (zb - za); c0 = wa - k * za
inv = 1 / k
# PIL affine: 출력 좌표 → 입력 좌표
coef = (inv.real, -inv.imag, (-c0 * inv).real, inv.imag, inv.real, (-c0 * inv).imag)
ren6w = ren6.transform(f6c.size, Image.AFFINE, coef, resample=Image.BICUBIC)
over6 = Image.blend(f6c, ren6w, 0.5)
Wc, Hc = f6c.size
sheet = Image.new("RGB", (Wc * 3, Hc + 60), (0, 0, 0)); dr = ImageDraw.Draw(sheet)
for i, (img, cap) in enumerate([(f6c, "FILM R6 (frame 43, x4)"), (ren6w, "v0.3 ortho, elev 18 / yaw 30"), (over6, "OVERLAY")]):
    sheet.paste(img, (i * Wc, 30)); dr.text((i * Wc + 8, 6), cap, font=FONTB, fill=(255, 255, 255))
dr.text((8, Hc + 36), "aligned on the front-left and front-right deck corners only; low-res GIF, see reference_analysis.md",
        font=FONT, fill=(220, 220, 220))
sheet.save(os.path.join(HERE, "compare_R6.png"))
print(f"RENDER OK compare_R6 {t:.1f}s")

for o in bpy.data.objects:
    o.hide_render = False
scene.camera = cam_iso; set_res(RX, RY)
blend = os.path.join(HERE, "mustafar_blockout_v0.3.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("SAVED", blend)
print(f"V03 layout={LAYOUT_NAME} entrance y={EYC} h={EH} w={EW} fins_skipped={fins_skipped} curbs={n_curb}")
print(f"SUMMARY plates={N_PLATES} fins={n_fin} spots={n_spot} facility_edge_lights={n_l} back_posts={n_post}")
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == 'MESH':
        d = o.dimensions
        print(f"  {o.name:30s} E:{o['exist'][0]} F:{o['form'][0]}  {d.x:6.1f} x {d.y:6.1f} x {d.z:6.1f}")
