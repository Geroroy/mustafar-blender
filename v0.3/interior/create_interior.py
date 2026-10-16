"""무스타파 다음 공간 블록아웃(준비본) — 출입구 안 통로 / 리브 복도 / 홀로그램 테이블실. Blender(bpy) 자동 생성.
착륙장과 별도 파일·별도 국소 좌표. 착륙장 미확정 치수에 의존하지 않는 리브 복도·홀로그램실을 먼저 만들고,
통로는 착륙장 출입구 후보값에 의존하는 별도 모듈로 떨어뜨려 둔다. 공간 사이 연결:
  리브 복도 ↔ 홀로그램실 = C9 VERIFIED(11882) → 붙여 만듦
  출입구 안 통로 ↔ 리브 복도 = C4 UNKNOWN → 만들지 않음(모듈을 떨어뜨리고 끝을 철사틀로 표시)
실행:  <bpy 가상환경>/bin/python create_interior.py [<영화 원본 폴더> <영화 비교 출력 폴더(비공개)>]
입력:  interior_dimensions.json, ../dimensions.json(통로 단면만)
출력:  mustafar_interior_v0.1.blend, renders/*.png (영화 없음). 영화 폴더를 주면 근사 구도 나란히 비교(비공개)
색 = 형태 신뢰도: 회색 C, 황토 P, 자홍 U. 철사틀 = 미확인 자리. 발광 = 화면·조명·테이블 윗면.
"""
import json, math, os, sys

import bpy
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders"); os.makedirs(OUT, exist_ok=True)
D = json.load(open(os.path.join(HERE, "interior_dimensions.json"), encoding="utf-8"))
E = json.load(open(os.path.join(os.path.dirname(HERE), "dimensions.json"), encoding="utf-8"))["v03"]["entrance"]
R, C, P = D["room"], D["corridor"], D["passage"]
val = lambda n: n["value"]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
FULL = {"C": "CONFIRMED", "P": "PROBABLE", "U": "UNKNOWN"}
COL = {"C": (0.50, 0.50, 0.50), "P": (0.66, 0.56, 0.34), "U": (0.70, 0.28, 0.58), "WIRE": (0.85, 0.25, 0.70)}
MATS, COLLS, LABEL, ANCH = {}, {}, {}, {}


def material(key, emit=0.0):
    k = (str(key), emit)
    if k not in MATS:
        m = bpy.data.materials.new(f"M_{key}_{emit}"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
        c = COL.get(key, key) if isinstance(key, str) else key
        b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = 0.85
        if emit:
            b.inputs["Emission Color"].default_value = (*c, 1); b.inputs["Emission Strength"].default_value = emit
        m.diffuse_color = (*c, 1); MATS[k] = m
    return MATS[k]


def coll(name):
    if name not in COLLS:
        c = bpy.data.collections.new(name); scene.collection.children.link(c); COLLS[name] = c
    return COLLS[name]


def make(name, bm, ef, basis, collection, anchor, mat=None, wire=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll(collection).objects.link(ob)
    ob.data.materials.append(mat or material(ef[1]))
    ob["exist"], ob["form"], ob["basis"] = FULL[ef[0]], FULL[ef[1]], basis
    if wire:
        md = ob.modifiers.new("wire", 'WIREFRAME'); md.thickness = wire; md.use_replace = True; ob.visible_shadow = False
    LABEL[name] = ef; ANCH[name] = anchor
    return ob


def box(bm, lo, hi):
    vs = [bm.verts.new((x, y, z)) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]
    for f in [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]:
        bm.faces.new([vs[i] for i in f])


def prism(bm, poly, z0, z1):
    """XY 볼록 다각형(반시계)을 z0~z1로 밀어냄."""
    b = [bm.verts.new((x, y, z0)) for x, y in poly]; t = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(b[::-1]); bm.faces.new(t)
    for i in range(len(poly)):
        j = (i + 1) % len(poly); bm.faces.new([b[i], b[j], t[j], t[i]])


def prism_y(bm, poly_xz, y0, y1):
    """XZ 볼록 다각형을 Y 방향(y0~y1)으로 밀어냄."""
    a = [bm.verts.new((x, y0, z)) for x, z in poly_xz]; b = [bm.verts.new((x, y1, z)) for x, z in poly_xz]
    bm.faces.new(a); bm.faces.new(b[::-1])
    for i in range(len(poly_xz)):
        j = (i + 1) % len(poly_xz); bm.faces.new([a[i], b[i], b[j], a[j]])


def seg_box(bm, p0, p1, thick, z0, z1, off=0.0):
    """XY 선분 p0→p1을 따라 놓인 두께 thick 상자(선분에서 왼쪽 법선으로 off만큼 이동)."""
    d = Vector((p1[0] - p0[0], p1[1] - p0[1])); L = d.length; d /= L; n = Vector((-d.y, d.x))
    a, b = Vector(p0) + n * off, Vector(p1) + n * off
    poly = [a, b, b + n * thick, a + n * thick]
    if (poly[1] - poly[0]).cross(poly[2] - poly[1]) < 0:
        poly = poly[::-1]
    prism(bm, [(q.x, q.y) for q in poly], z0, z1)


def hexagon(L, W, s=1.0):
    return [(s * L / 2, 0), (s * (L / 2 - W / 2), s * W / 2), (-s * (L / 2 - W / 2), s * W / 2), (-s * L / 2, 0),
            (-s * (L / 2 - W / 2), -s * W / 2), (s * (L / 2 - W / 2), -s * W / 2)]


# ================================================================ 홀로그램 테이블실 (방 국소 좌표 = 장면 원점)
BY = val(R["back_wall_y"]); BX0, BX1 = val(R["back_wall_x"]); WH = val(R["wall_height"]); YMIN = val(R["floor_extent_y_min"])
RW, LW = val(R["right_wall"]), val(R["left_wall"]); PT = val(R["pit"]); DR = val(R["door"]); SC = val(R["screens"]); CN = val(R["consoles"]); TB = val(R["table"])
px0 = PT["x0"]; py0, py1 = PT["y"]; PD_ = PT["depth"]; pcx = PT["right_cap_x"]
DX0, DX1 = DR["center_x"] - DR["opening_w"] / 2, DR["center_x"] + DR["opening_w"] / 2
xr_at = lambda y: RW["from"][0] + (RW["from"][1] - y) / (RW["from"][1] - RW["to"][1]) * (RW["to"][0] - RW["from"][0])
XR = RW["to"][0]
_d = Vector((RW["to"][0] - RW["from"][0], RW["to"][1] - RW["from"][1])).normalized(); _n = Vector((-_d.y, _d.x)) * -1   # 방 안쪽 법선
_q = Vector(RW["from"]) + _n * PT["right_edge_offset_from_right_wall"]                                                # 구덩이 오른쪽 사선이 지나는 점
pit_x_at = lambda y: _q.x + (_q.y - y) / (-_d.y) * _d.x
PA, PB = (pit_x_at(py1), py1), (pcx, _q.y - (pcx - _q.x) / _d.x * (-_d.y))                                            # 사선 위 끝 / 아래 끝
PIT = [(px0, py0), (pcx, py0), PB, PA, (px0, py1)]

bm = bmesh.new()
for poly in ([(BX0, py1), (xr_at(py1), py1), (RW["from"][0], BY), (BX0, BY)],                 # 뒤 띠
             [PA, PB, (XR, PB[1]), (XR, RW["to"][1]), (xr_at(py1), py1)],                       # 오른쪽 사선 띠(벽과 나란함)
             [(pcx, py0), (XR, py0), (XR, PB[1]), PB],                                          # 오른쪽 아래 띠
             [(BX0, YMIN), (XR, YMIN), (XR, py0), (BX0, py0)],                                  # 앞 띠
             [(BX0, py0), (px0, py0), (px0, py1), (BX0, py1)]):                                 # 왼쪽 띠
    prism(bm, poly, -PD_, 0.0)
make("Room_Ring_Floor", bm, ("C", "P"), "10903·11888: 구덩이를 둘러싼 바깥 바닥(시신이 누운 곳). 오른쪽 경계는 꺾인 벽과 나란한 사선. 범위 −Y 쪽은 모델링 중단(미확인)", "Room", (BX0 + 1.5, py1 + 1.0, 0))
bm = bmesh.new(); prism(bm, PIT, -PD_ - 0.1, -PD_)
make("Room_Pit_Floor", bm, ("C", "P"), "10903·11888: 테이블 둘레의 한 단(약 0.2 m) 낮은 구덩이, 오른쪽은 사선 경계. 크기 후보", "Room", (px0 + 0.8, py0 + 0.8, -PD_))
bm = bmesh.new(); box(bm, (BX0, YMIN - 0.05, -PD_), (XR, YMIN, 0.05))
make("Room_Floor_Extent_Unknown", bm, ("U", "U"), "모델링 중단 범위(측정 아님). 카메라 뒤쪽 벽·화면 배치 미확인 — 만들지 않음", "Room", (0, YMIN, 0.1),
     mat=material("WIRE"), wire=0.04)

bm = bmesh.new()
box(bm, (BX0, BY, 0), (DX0, BY + 0.3, WH)); box(bm, (DX1, BY, 0), (RW["from"][0], BY + 0.3, WH)); box(bm, (DX0, BY, DR["opening_h"]), (DX1, BY + 0.3, WH))
seg_box(bm, RW["from"], RW["to"], 0.3, 0, WH, off=0.0)
for x0, x1 in ((DX0 - DR["pillar_w"], DX0), (DX1, DX1 + DR["pillar_w"]), (SC["x_ranges_back_wall"][1][1], RW["from"][0])):   # 문 옆·모서리 기둥
    box(bm, (x0, BY - 0.9, 0), (x1, BY, WH))
make("Room_Walls_Screen_Side", bm, ("C", "P"), "10903·11098·11888: 화면 세 개가 있는 뒷벽과 꺾인 오른쪽 벽, 문 옆·모서리 기둥. 길이·꺾임 각은 후보, 천장 미확인(만들지 않음)",
     "Room", (BX0 + 0.5, BY, WH))
bm = bmesh.new(); seg_box(bm, LW["to"], LW["from"], 0.3, 0, WH)
make("Room_Left_Wall_Unknown", bm, ("U", "U"), "어느 프레임에도 안 보임. 오른쪽과 대칭 가정 — 철사틀", "Room", ((LW["from"][0] + LW["to"][0]) / 2, (LW["from"][1] + LW["to"][1]) / 2, WH),
     mat=material("WIRE"), wire=0.04)

bm = bmesh.new(); bl = bmesh.new()
for x0, x1 in ((BX0 + 0.2, DX0 - DR["pillar_w"]), (DX1 + DR["pillar_w"], SC["x_ranges_back_wall"][1][1])):
    box(bm, (x0, BY - 0.9 + 0.0, 0), (x1, BY, CN["desk_z"]))
    box(bl, (x0 + 0.05, BY - 0.92, CN["plinth_lit_band_z"][0]), (x1 - 0.05, BY - 0.9, CN["plinth_lit_band_z"][1]))
seg_box(bm, (RW["from"][0] + 0.3, RW["from"][1] - 0.4), (RW["to"][0] - 0.2, RW["to"][1] + 0.3), CN["depth"], 0, CN["desk_z"], off=-CN["depth"] - 0.05)
make("Room_Consoles", bm, ("C", "P"), "10903·11888: 화면 아래 벽을 따라 놓인 콘솔(책상면 0.95 m 후보). 기능 부품은 형태만 생략", "Room", (BX0 + 1.0, BY - 0.9, CN["desk_z"]))
make("Room_Console_Lit_Band", bl, ("C", "P"), "10903·11888: 콘솔 아래 단의 밝은 띠", "Room", (BX0 + 2.0, BY - 0.92, 0.3), mat=material((1.0, 0.82, 0.6), 4.0))

bm = bmesh.new()
for x0, x1 in SC["x_ranges_back_wall"]:
    box(bm, (x0, BY - 0.06, SC["bottom_z"]), (x1, BY, SC["top_z"]))
mid = ((RW["from"][0] + RW["to"][0]) / 2, (RW["from"][1] + RW["to"][1]) / 2); d = Vector((RW["to"][0] - RW["from"][0], RW["to"][1] - RW["from"][1])).normalized()
seg_box(bm, (mid[0] - d.x * SC["width"][2] / 2, mid[1] - d.y * SC["width"][2] / 2), (mid[0] + d.x * SC["width"][2] / 2, mid[1] + d.y * SC["width"][2] / 2), 0.06, SC["bottom_z"], SC["top_z"], off=-0.06)
make("Room_Screens_3", bm, ("C", "P"), "10900·10903·11098·11888: 금빛 지도 화면 세 개(존재·배치 VERIFIED). 크기·높이 후보(11888 인물 축척)", "Room",
     (SC["x_ranges_back_wall"][1][0] + 1.0, BY - 0.06, SC["top_z"]), mat=material((1.0, 0.62, 0.25), 3.0))

tz, sl = TB["top_z"], TB["slab"]
bm = bmesh.new()
top = hexagon(TB["top_len"], TB["top_w"]); prism(bm, top, tz - sl, tz - 0.02)
b = [bm.verts.new((x, y, tz - sl)) for x, y in hexagon(TB["top_len"], TB["top_w"], 0.95)]
f_ = [bm.verts.new((x, y, -PD_)) for x, y in hexagon(TB["top_len"], TB["top_w"], TB["base_scale"])]
bm.faces.new(f_[::-1])
for i in range(6):
    j = (i + 1) % 6; bm.faces.new([f_[i], f_[j], b[j], b[i]])
make("Room_Holo_Table", bm, ("C", "P"), "10903·11098·11888: 길쭉한 육각 홀로그램 테이블, 아래로 좁아지는 몸체(존재 VERIFIED). 길이 3.4 m·높이 후보", "Room", (TB["top_len"] / 2, 0, tz))
bm = bmesh.new(); prism(bm, hexagon(TB["top_len"] - 0.12, TB["top_w"] - 0.1), tz - 0.02, tz)
make("Room_Holo_Table_Top", bm, ("C", "P"), "빛나는 테이블 윗면", "Room", (-TB["top_len"] / 2, 0, tz), mat=material((0.45, 0.9, 1.0), 5.0))

# ================================================================ 리브 복도 (C9: 방 문과 같은 개구부)
S = val(C["section"]); RB = val(C["ribs"]); LP = val(C["light_panels"]); CL = val(C["length"]); DF = val(C["door_frame"])
cx = DR["center_x"]; y0 = BY + 0.3; yf = y0 + DF["frame_depth"]; y1 = yf + CL
fw, mw, ch, wt, cw, cz = S["floor_w"] / 2, S["max_w"] / 2, S["chamfer_top_z"], S["wall_top_z"], S["ceiling_w"] / 2, S["ceiling_z"]
bm = bmesh.new()
box(bm, (cx - DF["opening_w"] / 2 - DF["frame_w"], y0, 0), (cx - DF["opening_w"] / 2, yf, cz + 0.2))
box(bm, (cx + DF["opening_w"] / 2, y0, 0), (cx + DF["opening_w"] / 2 + DF["frame_w"], yf, cz + 0.2))
box(bm, (cx - DF["opening_w"] / 2, y0, DR["opening_h"]), (cx + DF["opening_w"] / 2, yf, cz + 0.2))
make("Corridor_Door_Frame_C9", bm, ("C", "P"), "11882: 리브 복도 끝 두꺼운 문틀 너머로 테이블·화면이 한 화면(C9 VERIFIED). 11098: 방 쪽에서 같은 문 너머 복도. 개구부 1.4 × 2.5 m 후보",
     "Corridor", (cx, y0, DR["opening_h"] + 0.3))
bm = bmesh.new()
box(bm, (cx - mw - 0.2, yf, -0.1), (cx + mw + 0.2, y1, 0.0))
for s in (-1, 1):
    inner = [(fw, 0.0), (mw, ch), (mw, wt), (cw, cz)]
    poly = [(cx + s * x, z) for x, z in inner] + [(cx + s * (x + 0.2), z + (0.2 if z == cz else 0.0)) for x, z in inner[::-1]]
    if s < 0:
        poly = poly[::-1]
    for k in range(len(inner) - 1):                                             # 볼록 조각별로 밀어냄
        a, b2 = inner[k], inner[k + 1]
        q = [(cx + s * a[0], a[1]), (cx + s * b2[0], b2[1]), (cx + s * (b2[0] + 0.2), b2[1]), (cx + s * (a[0] + 0.2), a[1])]
        cxq, czq = sum(t[0] for t in q) / 4, sum(t[1] for t in q) / 4
        prism_y(bm, sorted(q, key=lambda t: -math.atan2(t[1] - czq, t[0] - cxq)), yf, y1)
make("Corridor_Rib_Shell", bm, ("C", "P"), "11877·11878·11880: 밑동이 좁아지고 위가 안쪽으로 기운 단면(폭 1.4/2.4 m, 천장 2.9 m 후보). 길이 9 m는 모델링 중단 위치(측정 아님). 방향은 뒷벽에 수직(가정, 11098은 왼쪽으로 비스듬함을 시사)",
     "Corridor", (cx - mw, yf + 2.0, wt))
bm = bmesh.new(); box(bm, (cx - cw - 0.2, yf, cz), (cx + cw + 0.2, y1, cz + 0.15))
make("Corridor_Ceiling", bm, ("C", "U"), "복도 천장(높이 후보 2.9 m, 영화에서 천장면은 거의 안 보임). 위·아이소 렌더에서는 숨김", "Corridor", (cx, y1 - 1.0, cz + 0.15))
bm = bmesh.new(); bl = bmesh.new(); k = 0; yy = yf + 0.3
while yy < y1 - 0.2:
    for s in (-1, 1):
        box(bm, (cx + s * mw - (RB["depth"] if s > 0 else 0), yy, ch), (cx + s * mw + (RB["depth"] if s < 0 else 0), yy + RB["thick"], wt))
        if k % LP["every_n_bays"] == 0 and yy + RB["pitch"] < y1:
            for z0, z1 in LP["z"]:
                xx = cx + s * (mw - 0.02) if z0 > ch else cx + s * (fw + (mw - fw) * (z0 / ch) + 0.02)
                box(bl, (min(xx, xx - s * 0.04), yy + 0.18, z0), (max(xx, xx - s * 0.04), yy + RB["pitch"] - 0.06, z1))
    yy += RB["pitch"]; k += 1
make("Corridor_Ribs", bm, ("C", "P"), "11878·11880: 세로 리브 반복(간격 0.6 m 후보)", "Corridor", (cx + mw, yf + 4.0, wt - 0.3))
make("Corridor_Light_Panels", bl, ("C", "P"), "11877·11882: 리브 사이 두 높이의 밝은 직사각 조명", "Corridor", (cx - mw, yf + 6.0, 1.8), mat=material((1.0, 0.95, 0.85), 5.0))
bm = bmesh.new(); box(bm, (cx - mw, y1, 0), (cx + mw, y1 + 0.05, cz))
make("Corridor_Unknown_End", bm, ("U", "U"), "모델링 중단 위치. 그 너머(안쪽 홀 C8 PROBABLE, 출입구 안 통로 C4 UNKNOWN) — 연결하지 않음", "Corridor", (cx, y1, cz),
     mat=material("WIRE"), wire=0.04)

# ================================================================ 출입구 안 통로 (착륙장 출입구 후보값에 의존, 떨어진 모듈)
OX, OY = -22.0, 4.0                                                   # 장면 안 배치(방과 떨어뜨림, 의미 없는 위치)
EW = E["width"]["value"]; ELC = E["light_center_height"]["value"]; EH = ELC + E["light_below_apex"]["value"]; EZS = ELC * E["shoulder_frac"]["value"]
PL = val(P["length"]); hw = EW / 2
bm = bmesh.new()
box(bm, (OX - hw - 0.25, OY, -0.1), (OX + hw + 0.25, OY + PL, 0.0))
for s in (-1, 1):
    box(bm, (OX + s * hw - (0 if s > 0 else 0.25), OY, 0.0), (OX + s * hw + (0.25 if s > 0 else 0), OY + PL, EZS))
    q = [(OX + s * hw, EZS), (OX, EH), (OX, EH + 0.25), (OX + s * (hw + 0.25), EZS)]
    cxq, czq = sum(t[0] for t in q) / 4, sum(t[1] for t in q) / 4
    prism_y(bm, sorted(q, key=lambda t: -math.atan2(t[1] - czq, t[0] - cxq)), OY, OY + PL)
k_ = 0.0
while k_ < PL - 0.3:
    for xx in (OX - hw + 0.02, OX + hw - 0.08):
        box(bm, (xx, OY + 0.2 + k_, 0.1), (xx + 0.06, OY + 0.3 + k_, EZS - 0.05))
    k_ += 0.6
make("Passage_From_A_Entrance", bm, ("C", "U"), f"11748: 출입구 안으로 이어지는 통로(존재 VERIFIED). 단면은 착륙장 출입구 후보값(폭 {EW} m, 조명 중심 {ELC} m)을 그대로 씀 — 착륙장 미확정 치수에 의존. 길이 4 m는 모델링 중단",
     "Passage", (OX + hw, OY + 1.0, EZS))
bm = bmesh.new(); box(bm, (OX - hw, OY + PL, 0), (OX + hw, OY + PL + 0.05, EH))
make("Passage_Unknown_End_C4", bm, ("U", "U"), "통로 너머 미확인. 리브 복도와의 연결(C4) UNKNOWN — 만들지 않음", "Passage", (OX, OY + PL, EH), mat=material("WIRE"), wire=0.04)
bm = bmesh.new(); box(bm, (OX - hw - 0.6, OY - 0.05, 0), (OX + hw + 0.6, OY, EH + 0.6))
make("Passage_Landing_Side_Unknown", bm, ("U", "U"), "착륙장 A자 출입구 쪽. 출입구 크기·위치 미확정(착륙장 CR-009·잠정 정리) — 이 파일에서는 연결하지 않음", "Passage", (OX - hw, OY, EH + 0.6),
     mat=material("WIRE"), wire=0.04)

# ================================================================ 사람 크기 확인용 기둥(1.8 m)
bm = bmesh.new()
for p in ((1.0, 3.6, 0.0), (0.0, -2.2, -PD_), (cx + 0.25, yf + 0.7, 0.0), (OX, OY + 1.5, 0.0)):
    box(bm, (p[0] - 0.22, p[1] - 0.15, p[2]), (p[0] + 0.22, p[1] + 0.15, p[2] + 1.8))
make("Scale_Figure_1.8m", bm, ("C", "C"), "크기 확인용 1.8 m 사람 기둥(건축물 아님)", "Scale_Check", (1.0, 3.6, 1.8), mat=material((0.2, 0.85, 0.3)))

# ================================================================ 카메라·렌더
scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.use_denoising = True
scene.render.image_settings.file_format = 'PNG'; scene.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("W"); scene.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.36, 0.40, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
sun = bpy.data.lights.new("Sun", 'SUN'); sun.energy = 1.3; so = bpy.data.objects.new("Sun", sun); scene.collection.objects.link(so); so.rotation_euler = (math.radians(40), math.radians(15), math.radians(30))


def cam(name, ortho, loc=None, look=None, lens=24.0):
    cd = bpy.data.cameras.new(name); cd.type = 'ORTHO' if ortho else 'PERSP'; cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 500
    co = bpy.data.objects.new(name, cd); coll("Cameras").objects.link(co)
    if loc:
        co.location = loc; co.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co


def fit_ortho(co, objs, aspect, margin=1.08):
    rot = co.rotation_euler.to_matrix(); right, up, fwd = rot.col[0], rot.col[1], -rot.col[2]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).bound_box]
    rs = [p.dot(right) for p in pts]; us = [p.dot(up) for p in pts]
    co.data.ortho_scale = max(max(rs) - min(rs), (max(us) - min(us)) * aspect) * margin
    co.location = right * (min(rs) + max(rs)) / 2 + up * (min(us) + max(us)) / 2 - fwd * 200


MESH = [o for o in bpy.data.objects if o.type == 'MESH']
c_top = cam("Top_View", True); fit_ortho(c_top, MESH, 1600 / 1000)
c_iso = cam("Isometric_View", True); c_iso.rotation_euler = (math.radians(60), 0, math.radians(-45)); fit_ortho(c_iso, MESH, 1600 / 1000)
VIEWS = {   # 근사 구도(손으로 둔 카메라, 맞춤 아님) — 영화와 배치 대조용
    "v10903": (cam("Approx_10903", False, (1.2, -8.0, 5.2), (-0.8, 3.0, 0.6), 18.0), "10903 근사(높은 와이드, 화면 세 개·문·테이블·구덩이)"),
    "v11098": (cam("Approx_11098", False, (2.6, -3.6, 1.45), (-1.4, 5.5, 1.6), 22.0), "11098 근사(낮은 시점, 화면 사이 문 너머 리브 복도)"),
    "v11882": (cam("Approx_11882", False, (cx + 0.1, yf + 3.2, 1.55), (cx, -2.0, 1.1), 20.0), "11882 근사(복도에서 문틀 너머 방)"),
    "v11878": (cam("Approx_11878", False, (cx + 0.15, yf + 7.5, 1.6), (cx, yf + 0.5, 1.6), 22.0), "11878 근사(리브 복도 안)"),
}

from PIL import Image, ImageDraw, ImageFont
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 15); FTB = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 20)
TAG = {"C": (215, 215, 215), "P": (240, 200, 110), "U": (240, 125, 215)}


def render(co, path, res, title, labels=True, extra=()):
    scene.camera = co; scene.render.resolution_x, scene.render.resolution_y = res; scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = Image.open(path).convert("RGB"); dr = ImageDraw.Draw(im); placed = []
    items = []
    if labels:
        for nm, p in ANCH.items():
            c = world_to_camera_view(scene, co, Vector(p))
            if 0.01 <= c.x <= 0.99 and 0.05 <= c.y <= 0.96 and c.z > 0:
                items.append((nm, c.x * im.width, (1 - c.y) * im.height))
    for nm, x, y in sorted(items, key=lambda t: t[2]):
        e, f = LABEL[nm]; t = f"{nm}  E:{e} F:{f}"; tw = dr.textlength(t, font=FT)
        tx = min(max(x + 8, 4), im.width - tw - 6); ty = min(max(y - 8, 34), im.height - 40)
        for _ in range(40):
            if not any(abs(ty - q[1]) < 18 and tx < q[0] + q[2] + 4 and q[0] < tx + tw + 4 for q in placed):
                break
            ty += 18
        placed.append((tx, ty, tw)); dr.line((x, y, tx, ty + 8), fill=TAG[f]); dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=TAG[f])
        dr.rectangle((tx - 3, ty - 1, tx + tw + 3, ty + 17), fill=(0, 0, 0)); dr.text((tx, ty), t, font=FT, fill=TAG[f])
    for t, p in extra:
        c = world_to_camera_view(scene, co, Vector(p))
        if c.z > 0:
            x, y = c.x * im.width, (1 - c.y) * im.height; tw = dr.textlength(t, font=FTB)
            dr.rectangle((x - tw / 2 - 4, y - 2, x + tw / 2 + 4, y + 24), fill=(90, 0, 70)); dr.text((x - tw / 2, y), t, font=FTB, fill=(255, 230, 250))
    dr.rectangle((0, 0, im.width, 30), fill=(0, 0, 0)); dr.text((8, 4), title, font=FTB, fill=(255, 255, 255))
    dr.rectangle((0, im.height - 22, im.width, im.height), fill=(0, 0, 0))
    dr.text((8, im.height - 20), "색 = 형태 신뢰도: 회색 C  황토 P  자홍 U | 철사틀 = 미확인 자리 | 초록 = 1.8 m 사람 기둥 | 치수는 모두 후보", font=FT, fill=(220, 220, 220))
    im.save(path)


bpy.data.objects["Corridor_Ceiling"].hide_render = True
GAP = [("C4 연결 UNKNOWN — 만들지 않음", (OX + 5.5, OY + PL + 1.5, 1.0)), ("C9 VERIFIED (11882)", (cx + 2.6, y0 + 0.3, 3.4))]
render(c_top, os.path.join(OUT, "I_top.png"), (1600, 1000), "다음 공간 블록아웃 v0.1 — 위에서(천장 없음). 왼쪽: 출입구 안 통로(떨어진 모듈) / 오른쪽: 홀로그램실 + 리브 복도", extra=GAP)
ppm = 1600 / c_top.data.ortho_scale; im = Image.open(os.path.join(OUT, "I_top.png")); dr = ImageDraw.Draw(im)
dr.rectangle((10, im.height - 56, 40 + 5 * ppm + 50, im.height - 26), fill=(0, 0, 0)); dr.line((20, im.height - 41, 20 + 5 * ppm, im.height - 41), fill=(255, 255, 255), width=3)
dr.text((28 + 5 * ppm, im.height - 52), "5 m", font=FT, fill=(255, 255, 255)); im.save(os.path.join(OUT, "I_top.png"))
render(c_iso, os.path.join(OUT, "I_iso.png"), (1600, 1000), "다음 공간 블록아웃 v0.1 — 아이소메트릭(게임 투영 30°/45°)", extra=GAP)
bpy.data.objects["Corridor_Ceiling"].hide_render = False
for k, (co, t) in VIEWS.items():
    render(co, os.path.join(OUT, f"I_{k}.png"), (1280, 533), t, labels=(k in ("v10903", "v11882")))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "mustafar_interior_v0.1.blend"))
print("OUT ok", ppm)

if len(sys.argv) > 2 and os.path.isdir(sys.argv[-2]):                  # 영화 근사 구도 나란히(비공개 출력)
    FR, FO = sys.argv[-2], sys.argv[-1]; os.makedirs(FO, exist_ok=True)
    for k in VIEWS:
        n = k[1:]; fm = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB").resize((1280, 533)); rd = Image.open(os.path.join(OUT, f"I_{k}.png")).convert("RGB")
        sh = Image.new("RGB", (1280, 1066)); sh.paste(fm, (0, 0)); sh.paste(rd, (0, 533)); dr = ImageDraw.Draw(sh)
        dr.rectangle((0, 0, 1280, 28), fill=(0, 0, 0)); dr.text((6, 3), f"4K {n} (영화)", font=FTB, fill=(255, 255, 255)); sh.save(os.path.join(FO, f"IF_{k}.png"))
    print("OUT film", len(VIEWS))
