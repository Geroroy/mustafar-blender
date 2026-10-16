"""MD_REMAKE_POC01 — 복사한 Movie Duels(duel_mus_both) 형상을 영화·게임 기준으로 고치는 단계. md03_build_poc.py가 부른다.
모든 수치는 우리 미터 좌표(+X 시설, 판 윗면 z 0). 근거 구분: [영화] 영화 프레임에서 확인 / [게임] 게임 보행·카메라 요구 / [제작] 제작 판단.
고친 내용은 반환값(보고)과 객체 속성 md_role·md_basis에 남긴다.
"""
import math

import bpy, bmesh
from mathutils import Vector

D = bpy.data


# ---------------------------------------------------------------- 공용
def mat_metal(name, base, dark, rough=(0.5, 0.85), metallic=0.5, scale=1.0):
    m = D.materials.get(name)
    if m:
        return m
    m = D.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    fn = nt.nodes.new("ShaderNodeTexNoise"); fn.inputs["Scale"].default_value = 30; nt.links.new(mp.outputs[0], fn.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.3; rp.color_ramp.elements[0].color = (*dark, 1)
    rp.color_ramp.elements[1].position = 0.72; rp.color_ramp.elements[1].color = (*base, 1); nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs[0], bs.inputs["Base Color"]); bs.inputs["Metallic"].default_value = metallic
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs[3].default_value, rr.inputs[4].default_value = rough
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs[0], bs.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.1; nt.links.new(fn.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs[0], bs.inputs["Normal"])
    nt.links.new(bs.outputs[0], out.inputs[0]); return m


def mat_emit(name, color, strength):
    m = D.materials.get(name)
    if m:
        return m
    m = D.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1); e.inputs[1].default_value = strength; nt.links.new(e.outputs[0], out.inputs[0]); return m


def has_image(ma):
    return bool(ma and ma.node_tree and any(n.type == 'TEX_IMAGE' and n.image for n in ma.node_tree.nodes))


def box(bm, lo, hi):
    vs = [bm.verts.new((x, y, z)) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]
    for f in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)):
        bm.faces.new([vs[i] for i in f])


def new_obj(name, bm, mats, col, role, basis, coll):
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    ob = D.objects.new(name, me); coll(col).objects.link(ob); ob["md_role"] = role; ob["md_basis"] = basis; return ob


def delete_faces(ob, pred):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if pred(f.calc_center_median(), f)]
    n = len(dead); bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(ob.data); bm.free(); return n


def extract(ob, pred, name, col, role, basis, coll):
    """조건에 맞는 면을 새 객체로 떼어냄(재질 유지)."""
    bm = bmesh.new(); bm.from_mesh(ob.data); b2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if pred(f.calc_center_median(), f)], context='FACES')
    bmesh.ops.delete(b2, geom=[f for f in b2.faces if not pred(f.calc_center_median(), f)], context='FACES')
    bm.to_mesh(ob.data); bm.free()
    return new_obj(name, b2, list(ob.data.materials), col, role, basis, coll)


def inbox(c, lo, hi):
    return all(lo[i] <= c[i] <= hi[i] for i in range(3))


def planar_uv(ob, scale):
    me = ob.data
    uv = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        n = p.normal
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.6:
                uv.data[li].uv = (co.x / scale, co.y / scale)
            elif abs(n.x) > abs(n.y):
                uv.data[li].uv = (co.y / scale, co.z / scale)
            else:
                uv.data[li].uv = (co.x / scale, co.z / scale)


# ---------------------------------------------------------------- 본 작업
def apply(scene, objs, C, coll):
    P = C["modify"]; log = []
    fac, pad, deck = objs["MD_Facility"], objs["MD_Pad_Structure"], objs["MD_Pad_Deck"]
    PE, FX = C["pad_facility_edge_x_m"], C["facility_front_x_m"]

    # 1) 낮은 상자(모드 격자 상자 2개) 분리 — 판 가장자리 클리핑 전에
    crates = extract(pad, lambda c, f: any(inbox(c, b[0], b[1]) for b in P["crates_boxes"]), "MD_LowCrates", "MD_Pad", "유지",
                     "duel_mus_both 출입구 양옆 격자 상자 2개. 영화 78855 낮은 상자와 위치 관계(출입구 옆)는 같고 형태는 다름 → 형상 유지, 기록", coll)
    log.append(("유지", "MD_LowCrates", "출입구 양옆 격자 상자 2개(위치 관계는 영화 낮은 상자와 같음, 형태 다름)"))

    # 2) [영화] 크레넬레이션·시설 쪽 파이프 턱 제거: 판·통로 영역(시설 정면 앞)에서 판 윗면 위 0.03 m 넘는 판 구조를 자름
    bm = bmesh.new(); bm.from_mesh(pad.data)
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, 0, 0.03), plane_no=(0, 0, 1), clear_outer=True)
    bm.to_mesh(pad.data); bm.free()
    log.append(("교체", "판 가장자리 크레넬레이션 기둥·시설 쪽 파이프 턱", "판 윗면 위 판 구조 절단(z 0.03). 영화 가장자리 장치(뒤 변 기둥·난간, 시설 쪽 낮은 청색 등)로 교체"))

    # 3) [영화] 판과 시설 사이 열린 틈: 베이 앞·출입구 −Y 쪽 낮은 띠 바닥·경사로·턱을 지움(출입구 앞 다리는 새 바닥으로 남김)
    n_gap = 0
    for lo, hi in P["gap_boxes"]:
        for ob in (pad, fac, deck):
            n_gap += delete_faces(ob, lambda c, f, lo=lo, hi=hi: inbox(c, lo, hi))
    # 경사 기둥 밑동이 사라진 낮은 띠 바닥에 떠 있지 않게 틈 아래로 내림
    sb = P["strut_extend"]; n_v = 0
    for v in fac.data.vertices:
        if inbox(v.co, sb["lo"], sb["hi"]):
            v.co.z = sb["to_z"]; n_v += 1
    log.append(("수정", "판↔시설 사이 낮은 띠(z −1.8 m 바닥·경사로)", f"열린 틈으로 바꿈(면 {n_gap}개 삭제, 경사 기둥 밑동 정점 {n_v}개를 z {sb['to_z']}까지 내림). 영화 11615·11246 틈 VERIFIED"))

    # 4) [게임+영화] 출입구: 바깥 계단·통로 낮은 바닥(−1.8 m)을 판 높이 바닥으로 교체, 통로 끝 막음
    E = P["entrance"]; cy = E["center_y"]
    n_st = 0
    for lo, hi in E["clear_boxes"]:
        for ob in (pad, fac, deck):
            n_st += delete_faces(ob, lambda c, f, lo=lo, hi=hi: inbox(c, lo, hi))
    floor_mat = next((m for m in fac.data.materials if m and has_image(m) and any("floor_3_o" in n.image.name for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)), None)
    bm = bmesh.new()
    for lo, hi in E["floor_boxes"]:
        box(bm, lo, hi)
    ef = new_obj("MD_Entrance_Floor", bm, [floor_mat or mat_metal("MDX_FloorMetal", (0.2, 0.18, 0.16), (0.1, 0.09, 0.08))], "MD_Entrance", "수정",
                 "[게임] 모드 출입구는 판에서 계단으로 1.8 m 내려간 통로 → 판 높이(z 0)의 다리·통로 바닥으로 교체(모드 통로 바닥 질감 floor_3_o 재사용). [영화] 78862·11748 출입구 앞 바닥이 이어짐", coll)
    planar_uv(ef, 3.6)
    bm = bmesh.new(); box(bm, *E["end_wall"])
    new_obj("MD_Entrance_EndWall", bm, [mat_metal("MDX_GapFace", (0.03, 0.027, 0.025), (0.012, 0.011, 0.01), rough=(0.85, 0.98), metallic=0.1)], "MD_Entrance", "새로 만듦",
            "[게임] 통로 끝 막음(영화에서 통로 너머 UNKNOWN). 어두운 면", coll)
    log.append(("수정", "출입구 바깥 계단·통로 바닥", f"판 높이 바닥으로 교체(면 {n_st}개 삭제). 모드 통로 반복 프레임·천장·사다리꼴 윗선은 유지"))

    # 5) [영화] 출입구 윤곽: 모드 개구부(폭 6.1 m)는 영화보다 3배 넓다 → 개구부 안쪽에 영화 윤곽 판(아래 2.0 m·세로 문설주 → 1.3 m 단차 → 위 사다리꼴 1.56→0.84 m, 꼭대기 2.85 m)
    F = E["film_outline"]; xp, th = F["x"], F["thick"]
    hole = [(cy + s * w, z) for s, w, z in ((1, F["w_low"] / 2, 0.0), (1, F["w_low"] / 2, F["step_z"]), (1, F["w_step"] / 2, F["step_z"]), (1, F["w_top"] / 2, F["top_z"]),
                                              (-1, F["w_top"] / 2, F["top_z"]), (-1, F["w_step"] / 2, F["step_z"]), (-1, F["w_low"] / 2, F["step_z"]), (-1, F["w_low"] / 2, 0.0))]
    y0, y1, z1 = F["panel_y0"], F["panel_y1"], F["panel_top"]
    bm = bmesh.new()
    for x in (xp, xp + th):
        outer = [bm.verts.new((x, y, z)) for y, z in ((y0, 0.0), (y1, 0.0), (y1, z1), (y0, z1))]
        inner = [bm.verts.new((x, y, z)) for y, z in hole]
        es = [bm.edges.new((outer[i], outer[(i + 1) % 4])) for i in range(4)] + [bm.edges.new((inner[i], inner[(i + 1) % len(inner)])) for i in range(len(inner))]
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=es)
    # 구멍 둘레 두께 면
    for i in range(len(hole)):
        a, b = hole[i], hole[(i + 1) % len(hole)]
        if a[1] == 0.0 and b[1] == 0.0:
            continue
        bm.faces.new([bm.verts.new((xp, a[0], a[1])), bm.verts.new((xp, b[0], b[1])), bm.verts.new((xp + th, b[0], b[1])), bm.verts.new((xp + th, a[0], a[1]))])
    # 바깥 둘레(아래·위·양끝): 아래면이 있어야 위에서 쏜 충돌 광선이 판에서 멈춤
    # 아래면은 바닥(z 0)과 같은 높이면 광선이 바닥을 먼저 맞을 수 있어 0.2 m 위에 둠(앞뒤 면은 z 0부터라 보이는 형상은 같음)
    for ya, yb, za, zb in ((y0, cy - F["w_low"] / 2, 0.2, 0.2), (cy + F["w_low"] / 2, y1, 0.2, 0.2), (y0, y1, z1, z1), (y0, y0, 0.0, z1), (y1, y1, 0.0, z1)):
        bm.faces.new([bm.verts.new((xp, ya, za)), bm.verts.new((xp, yb, zb if ya == yb else za)), bm.verts.new((xp + th, yb, zb if ya == yb else za)), bm.verts.new((xp + th, ya, za))]
                     if ya != yb else [bm.verts.new((xp, ya, za)), bm.verts.new((xp, ya, zb)), bm.verts.new((xp + th, ya, zb)), bm.verts.new((xp + th, ya, za))])
    facade = mat_metal("MDX_FacadeMetal", (0.17, 0.155, 0.145), (0.085, 0.078, 0.072))
    new_obj("Entrance_Film_Infill", bm, [facade], "MD_Entrance", "새로 만듦",
            "[영화] 78862·11748 출입구 윤곽(아래 넓은 개구부·세로 문설주 → 단차 → 위 사다리꼴, 꼭대기 조명). 모드 개구부 안쪽을 채워 영화 비례로 좁힘", coll)
    bm = bmesh.new(); t = F["frame"]
    for i in range(len(hole)):
        a, b = Vector((xp - 0.06, *hole[i])), Vector((xp - 0.06, *hole[(i + 1) % len(hole)]))
        if a.z == 0.0 and b.z == 0.0:
            continue
        d = (b - a); L = d.length; e = d / L; n = Vector((0, -e.z, e.y))       # 구멍 바깥쪽 법선(판 평면 안)
        n = n if (Vector((0, a.y - cy, a.z - 1.4)).dot(n) > 0) else -n
        q = [a, b, b + n * t, a + n * t]
        vs = [bm.verts.new(p + Vector((dx, 0, 0))) for dx in (0.0, 0.14) for p in q]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[k] for k in f])
    new_obj("Entrance_Frame", bm, [mat_metal("MDX_TrimMetal", (0.26, 0.22, 0.19), (0.12, 0.1, 0.09))], "MD_Entrance", "새로 만듦", "[영화] 윤곽을 따르는 겹층 테두리(78862)", coll)
    bm = bmesh.new(); box(bm, (xp - 0.32, cy - 0.28, F["top_z"] + 0.02), (xp - 0.02, cy + 0.28, F["top_z"] + 0.3))
    new_obj("Entrance_Lamp", bm, [mat_emit("MDX_LampCool", (0.85, 0.92, 1.0), 25.0)], "MD_Entrance", "새로 만듦", "[영화] 출입구 꼭대기 작은 하향 조명(78862·11748)", coll)
    log.append(("수정", "사다리꼴 출입구 개구부", "모드 개구부(폭 6.1 m, 높이 4.5~6.1 m)를 유지하고 안쪽에 영화 윤곽 판·테두리·꼭대기 조명을 둠(통행 폭 2.0 m)"))

    # 6) [영화] 지붕: 모드 맞배지붕 → 두꺼운 평지붕 돌출 슬래브(영화 A01-1 버섯형 지붕). 처마 높이는 모드값 유지
    R = P["roof"]
    bm = bmesh.new(); bm.from_mesh(fac.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, R["cut_z"]), plane_no=(0, 0, 1), clear_outer=True)
    bm.to_mesh(fac.data); bm.free()
    bm = bmesh.new(); box(bm, R["lo"], R["hi"])
    roof = new_obj("MD_Roof_Slab", bm, [mat_metal("MDX_RoofMetal", (0.11, 0.10, 0.095), (0.05, 0.045, 0.043))], "MD_Facility", "교체",
                   "[영화] 11206·11233·11235 두꺼운 버섯형 돌출 슬래브 지붕(VERIFIED). 모드 맞배지붕(z 7.25 m 위)을 잘라내고 교체. 앞 돌출·두께는 제작값", coll)
    log.append(("교체", "모드 맞배지붕", f"z {R['cut_z']} m 위를 잘라내고 두꺼운 평지붕 슬래브(앞으로 {R['front_overhang']} m 돌출)로 교체"))

    # 7) [영화] 가장자리 장치: 뒤 변(+Y) 기둥·등·난간, 시설 쪽(틈 가장자리) 낮은 청색 등. 통로 끝 막음(게임)
    Q = P["edges"]; posts, plights, rails = bmesh.new(), bmesh.new(), bmesh.new()
    pts = []
    for (xa, ya), (xb, yb) in zip(Q["post_path"], Q["post_path"][1:]):
        a, b = Vector((xa, ya)), Vector((xb, yb)); k = max(1, round((b - a).length / Q["post_spacing"]))
        for j in range(0 if not pts else 1, k + 1):
            pts.append(a + (b - a) * (j / k))
    for p in pts:
        box(posts, (p.x - 0.18, p.y - 0.18, 0.0), (p.x + 0.18, p.y + 0.18, Q["post_h"]))
        box(plights, (p.x - 0.2, p.y - 0.2, Q["post_h"]), (p.x + 0.2, p.y + 0.2, Q["post_h"] + 0.18))
    for p, q in zip(pts, pts[1:]):
        lo_ = (min(p.x, q.x) - 0.04, min(p.y, q.y) - 0.04, Q["rail_h"] - 0.05); hi_ = (max(p.x, q.x) + 0.04, max(p.y, q.y) + 0.04, Q["rail_h"] + 0.03)
        box(rails, lo_, hi_)
        cw = Q["curb_w"] / 2                                               # 바닥 턱: 충돌 판정점(0.30 m)이 걸쳐 넘지 못하게 폭 0.45 m·높이 0.2 m(광선 허용 0.15 m 위)
        box(rails, (min(p.x, q.x) - cw, min(p.y, q.y) - cw, 0.0), (max(p.x, q.x) + cw, max(p.y, q.y) + cw, Q["curb_h"]))
    trim = mat_metal("MDX_TrimMetal", (0.26, 0.22, 0.19), (0.12, 0.1, 0.09)); blue = mat_emit("MDX_LightBlue", (0.45, 0.75, 1.0), 18.0)
    new_obj("Back_Edge_Posts", posts, [trim], "MD_Edges", "새로 만듦", "[영화] 11206·11575·11625·R6 뒤 변 키 큰 등 기둥 줄(VERIFIED). 높이 0.8 m 후보", coll)
    new_obj("Back_Edge_Post_Lights", plights, [blue], "MD_Edges", "새로 만듦", "[영화] R2·R6 점등", coll)
    new_obj("Back_Edge_Rail", rails, [trim], "MD_Edges", "새로 만듦", "[영화] 뒤 변 기둥 사이 난간(VERIFIED, 높이 후보 0.65 m) + [게임] 바닥 턱(보행 경계)", coll)
    bm = bmesh.new()
    for x, y in Q["facility_side_lights"]:
        box(bm, (x - 0.25, y - 0.25, 0.0), (x + 0.25, y + 0.25, 0.12))
    new_obj("Edge_Lights_Facility_Side", bm, [blue], "MD_Edges", "새로 만듦", "[영화] R2 시설 쪽 가장자리 낮은 청색 등(간격 측정 10.6·11.6 m의 비례로 둠)", coll)
    bm = bmesh.new()
    for lo, hi in Q["end_barriers"]:
        box(bm, lo, hi)
    new_obj("Side_Walkway_EndRail", bm, [trim], "MD_Edges", "새로 만듦", "[게임] 옆 통로 끝 막음(모드 통로는 벽으로 끝남, 그 너머 영화 근거 없음)", coll)
    log.append(("교체", "가장자리 장치", f"뒤 변 기둥 {len(pts)}개·난간, 시설 쪽 청색 등 {len(Q['facility_side_lights'])}개, 옆 통로 끝 막음"))

    # 8) [영화] 재질: 질감 없는 회색 재질(원본 색 아님) → 어두운 중성 금속. 틈 속·받침은 아주 어두운 면
    dark = mat_metal("MDX_FacilityMetal", (0.115, 0.108, 0.102), (0.055, 0.052, 0.05))
    n_m = 0
    for ob in [o for o in scene.collection.all_objects if o.type == 'MESH' and o.name.startswith("MD_")]:
        for i, m in enumerate(ob.data.materials):
            if m is not None and not has_image(m) and not m.name.startswith("MDX_"):
                ob.data.materials[i] = dark; n_m += 1
    base = extract(fac, lambda c, f: c.z < P["base_split_z"], "MD_Facility_Base", "MD_Facility", "유지",
                   "duel_mus_both 시설 밑동 벽·경사 받침 다리(영화 A01-4 경사 지지부가 바닥선 아래에서 오름과 같은 계열)", coll)
    gapm = mat_metal("MDX_GapFace", (0.03, 0.027, 0.025), (0.012, 0.011, 0.01), rough=(0.85, 0.98), metallic=0.1)
    for i in range(len(base.data.materials)):
        base.data.materials[i] = gapm
    log.append(("수정", "회색(질감 연결 없음) 재질", f"슬롯 {n_m}개를 어두운 중성 금속으로, 틈 속 밑동은 아주 어두운 면으로(형상 그대로)"))

    # 9) [게임] 가림 조각용으로 시설을 나눔: 옆 통로 쪽 끝(베이 포함) / 나머지(출입구 앞 조각은 내보내기에서 clip_x)
    bm = bmesh.new(); bm.from_mesh(roof.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, P["end_split_y"], 0), plane_no=(0, 1, 0))
    bm.to_mesh(roof.data); bm.free()
    end_roof = extract(roof, lambda c, f: c.y > P["end_split_y"], "MD_Roof_Slab_End", "MD_Facility", "교체", roof["md_basis"], coll)
    end = extract(fac, lambda c, f: c.y > P["end_split_y"], "MD_Facility_EndBlock", "MD_Facility", "유지",
                  "duel_mus_both 시설 +Y 끝(열린 베이·경사 기둥 2개·처마 등 상자 포함). [게임] 옆 통로가 그 뒤로 지나가 가림 조각으로 따로 구움", coll)
    log.append(("수정", "시설 분할(게임 가림)", f"Y > {P['end_split_y']} m 끝 덩어리를 가림 조각으로 분리"))

    # 처마 등 상자 위치(조명 배치용)
    eave = sorted({round(f.center.y, 1) for o in (fac, end) for f in o.data.polygons if FX - 0.6 <= f.center.x <= FX + 0.2 and 5.4 <= f.center.z <= 7.2 and f.normal.z < -0.5 and f.area < 1.0})
    for o in (fac, end, roof, end_roof, base, crates, ef):
        for p in o.data.polygons:
            p.use_smooth = False
    return {"log": [{"구분": a, "대상": b, "내용": c} for a, b, c in log], "eave_fixture_y_candidates": eave}
