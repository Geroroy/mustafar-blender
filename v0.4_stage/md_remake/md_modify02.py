"""MD_REMAKE_POC02 — POC01의 모든 단계(md_modify.apply)를 그대로 돌린 뒤, 검수서 네 항목만 고친다. md03_build_poc.py가 부른다(--config md_poc02.json).
  1) 바닥 재질: 큰 불규칙 판재 + 가는 이음선(형상·외곽·충돌은 그대로)
  2) 출입구: 3겹 경사 하우징·어깨 턱·테두리·꼭대기 조명(문 구멍 크기는 POC01과 같음)
  3) 낮은 상자: 대각 격자 상자 → 경사 외벽·두꺼운 상부 테두리·겹친 리브·후퇴한 조명부(바닥 투영 크기는 같음)
  4) 지붕: 처마 아래 후퇴부 + 윗면 비스듬한 가장자리 + 지붕 위 마스트(윤곽·돌출 2.25 m·두께 1.8 m는 그대로)
근거 구분: [영화] 첨부 프레임에서 형태 확인 / [제작] 제작 판단(영화 실측 아님). 판 확장·시설 폭·베이·틈 폭·축척·받침 다리 길이는 건드리지 않는다.
"""
import math

import bpy, bmesh
from mathutils import Vector, geometry

import md_modify as M0

D = bpy.data


# ---------------------------------------------------------------- 공용: 윤곽 보간(loft) 기둥
def _orient(face_vs, want):
    """면 법선이 want 방향이 되게 정점 순서를 맞춘다."""
    n = Vector((0, 0, 0))
    for i, a in enumerate(face_vs):
        b = face_vs[(i + 1) % len(face_vs)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return face_vs if n.dot(want) >= 0 else face_vs[::-1]


def loft_yz(bm, poly_b, poly_f, xb, xf, floor_z=0.2):
    """(y, z) 윤곽 둘(뒤 xb, 앞 xf; 같은 정점 수·순서)을 잇는 기둥. 바닥(z 0) 변은 아래면을 z=floor_z에 둔다(충돌 광선이 바닥 객체보다 먼저 막히게 — POC01 영화 윤곽 판과 같은 방식).
    윤곽은 단순 다각형(오목 가능). 면은 법선이 바깥을 향하게 만든다."""
    n = len(poly_b)
    B = [Vector((xb, y, z)) for y, z in poly_b]; F = [Vector((xf, y, z)) for y, z in poly_f]
    area = sum(poly_b[i][0] * poly_b[(i + 1) % n][1] - poly_b[(i + 1) % n][0] * poly_b[i][1] for i in range(n))
    tris = geometry.tessellate_polygon([[Vector((y, z, 0)) for y, z in poly_b]])
    for ring, want in ((B, Vector((1, 0, 0))), (F, Vector((-1, 0, 0)))):
        for t in tris:
            vs = _orient([ring[i] for i in t], want)
            bm.faces.new([bm.verts.new(v) for v in vs])
    for i in range(n):
        j = (i + 1) % n
        yb0, zb0 = poly_b[i]; yb1, zb1 = poly_b[j]
        d = Vector((0, yb1 - yb0, zb1 - zb0)); out = Vector((0, d.z, -d.y)) * (1 if area > 0 else -1)
        if zb0 == 0.0 and zb1 == 0.0:                                      # 바닥 변: 옆면 대신 z=floor_z 아래면
            quad = [Vector((B[i].x, B[i].y, floor_z)), Vector((B[j].x, B[j].y, floor_z)), Vector((F[j].x, F[j].y, floor_z)), Vector((F[i].x, F[i].y, floor_z))]
            bm.faces.new([bm.verts.new(v) for v in _orient(quad, Vector((0, 0, -1)))])
            continue
        quad = [B[i], B[j], F[j], F[i]]
        bm.faces.new([bm.verts.new(v) for v in _orient(quad, out)])


def loft_rect(bm, r0, z0, r1, z1):
    """직사각형 둘(r = (x0, x1, y0, y1)) 사이 닫힌 기둥: 아래 r0@z0 → 위 r1@z1."""
    def ring(r, z):
        return [Vector((r[0], r[2], z)), Vector((r[1], r[2], z)), Vector((r[1], r[3], z)), Vector((r[0], r[3], z))]
    A, Bv = ring(r0, z0), ring(r1, z1)
    bm.faces.new([bm.verts.new(v) for v in _orient(A, Vector((0, 0, -1)))])
    bm.faces.new([bm.verts.new(v) for v in _orient(Bv, Vector((0, 0, 1)))])
    cen = sum(A + Bv, Vector()) / 8
    for i in range(4):
        j = (i + 1) % 4
        q = [A[i], A[j], Bv[j], Bv[i]]
        mid = sum(q, Vector()) / 4
        bm.faces.new([bm.verts.new(v) for v in _orient(q, mid - cen)])


def prism(bm, prof, axis, a0, a1):
    """볼록 윤곽(2D 점 목록)을 한 축 방향으로 a0~a1만큼 민 닫힌 기둥. axis 'y': 윤곽 = (x, z), 'x': 윤곽 = (y, z)."""
    def p(c, a):
        return Vector((c[0], a, c[1])) if axis == 'y' else Vector((a, c[0], c[1]))
    A = [p(c, a0) for c in prof]; Bv = [p(c, a1) for c in prof]; cen = sum(A + Bv, Vector()) / (2 * len(prof))
    for ring in (A, Bv):
        mid = sum(ring, Vector()) / len(ring)
        bm.faces.new([bm.verts.new(v) for v in _orient(ring, mid - cen)])
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        q = [A[i], A[j], Bv[j], Bv[i]]
        mid = sum(q, Vector()) / 4
        bm.faces.new([bm.verts.new(v) for v in _orient(q, mid - cen)])


# ---------------------------------------------------------------- 재질
def mat_deck(P):
    """큰 불규칙 판재 + 가는 이음선. 직선 이음선 판재(벽돌 배치, 살짝 돌림, 열마다 어긋남) 위에 더 큰 비스듬한 판재를 한 겹 더 겹쳐 비스듬한 이음선이 섞이게 한다.
    월드(객체=원점) 좌표 기준이라 판·다리·통로 바닥의 이음선이 이어진다. 낮은 대비."""
    name = "MDX_DeckPlates"
    m = D.materials.get(name)
    if m:
        return m
    m = D.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); bs = N("ShaderNodeBsdfPrincipled")
    tc = N("ShaderNodeTexCoord")

    def brick(w, h, rot, seam, off, c1, c2):
        mp = N("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot)); L(tc.outputs["Object"], mp.inputs["Vector"])
        b_ = N("ShaderNodeTexBrick"); b_.offset = off; b_.offset_frequency = 2; b_.squash = 1.0
        for k, v in (("Scale", 1.0), ("Mortar Size", seam), ("Mortar Smooth", 0.0), ("Bias", 0.0), ("Brick Width", w), ("Row Height", h)):
            b_.inputs[k].default_value = v
        b_.inputs["Color1"].default_value = (c1, c1, c1, 1); b_.inputs["Color2"].default_value = (c2, c2, c2, 1); b_.inputs["Mortar"].default_value = (0, 0, 0, 1)
        L(mp.outputs[0], b_.inputs["Vector"]); return b_
    lo, hi = P["cell_var"]
    b1 = brick(P["plate_w"], P["plate_h"], P["rot_deg"], P["seam_width"], P["offset"], hi, lo)
    b2 = brick(P["diag_w"], P["diag_h"], P["diag_rot_deg"], P["diag_seam"], 0.5, 1.0, 1.0)
    bw = N("ShaderNodeRGBToBW"); L(b1.outputs["Color"], bw.inputs["Color"])                     # 판재별 밝기(이음선은 0)
    sm1 = N("ShaderNodeMath"); sm1.operation = 'MAXIMUM'; L(b1.outputs["Fac"], sm1.inputs[0]); L(b2.outputs["Fac"], sm1.inputs[1])       # Brick Fac = 이음선 마스크(이음선 1, 판재 0). 둘 중 하나라도 걸리면 이음선
    seam = N("ShaderNodeMapRange"); seam.inputs[3].default_value, seam.inputs[4].default_value = 1.0, P["seam_mul"]; seam.clamp = True; L(sm1.outputs[0], seam.inputs["Value"])      # 판재 1.0 → 이음선 seam_mul
    tone = N("ShaderNodeMath"); tone.operation = 'MAXIMUM'; tone.inputs[1].default_value = lo; L(bw.outputs[0], tone.inputs[0])
    mot = N("ShaderNodeTexNoise"); mot.inputs["Scale"].default_value = 0.22; mot.inputs["Detail"].default_value = 4; L(tc.outputs["Object"], mot.inputs["Vector"])
    mot_r = N("ShaderNodeMapRange"); mot_r.inputs[3].default_value, mot_r.inputs[4].default_value = 0.86, 1.08; L(mot.outputs["Fac"], mot_r.inputs["Value"])
    fine = N("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 24; fine.inputs["Detail"].default_value = 6; L(tc.outputs["Object"], fine.inputs["Vector"])
    fine_r = N("ShaderNodeMapRange"); fine_r.inputs[3].default_value, fine_r.inputs[4].default_value = 0.92, 1.06; L(fine.outputs["Fac"], fine_r.inputs["Value"])
    s1 = N("ShaderNodeMath"); s1.operation = 'MULTIPLY'; L(tone.outputs[0], s1.inputs[0]); L(seam.outputs[0], s1.inputs[1])
    s2 = N("ShaderNodeMath"); s2.operation = 'MULTIPLY'; L(s1.outputs[0], s2.inputs[0]); L(mot_r.outputs[0], s2.inputs[1])
    s3 = N("ShaderNodeMath"); s3.operation = 'MULTIPLY'; L(s2.outputs[0], s3.inputs[0]); L(fine_r.outputs[0], s3.inputs[1])
    col = N("ShaderNodeVectorMath"); col.operation = 'SCALE'; col.inputs[0].default_value = tuple(P["base"]); L(s3.outputs[0], col.inputs["Scale"])
    L(col.outputs[0], bs.inputs["Base Color"])
    bs.inputs["Metallic"].default_value = 0.2
    rr = N("ShaderNodeMapRange"); rr.inputs[3].default_value, rr.inputs[4].default_value = 0.88, 0.58; L(fine.outputs["Fac"], rr.inputs["Value"]); L(rr.outputs[0], bs.inputs["Roughness"])
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.18; bp.inputs["Distance"].default_value = 0.02
    hf = N("ShaderNodeMath"); hf.operation = 'MULTIPLY'; hf.inputs[1].default_value = 0.6; L(seam.outputs[0], hf.inputs[0]); L(hf.outputs[0], bp.inputs["Height"])           # 이음선은 살짝 파임
    L(bp.outputs[0], bs.inputs["Normal"]); L(bs.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------- 본 작업
def apply(scene, objs, C, coll):
    rep = M0.apply(scene, objs, C, coll)          # POC01 단계 전부(형상·틈·출입구 바닥·영화 윤곽 판·평지붕·가장자리 장치·재질 분리)
    Q = C["poc02"]; P = C["modify"]; log = []
    E = P["entrance"]; cy = E["center_y"]; Fm = E["film_outline"]
    mm = lambda n: M0.mat_metal(n[0], *n[1:])

    # ---- 1) 바닥: 재질만 교체(형상·외곽·충돌 그대로)
    deck_mat = mat_deck(Q["floor"])
    for n in Q["floor"]["objects"]:
        ob = D.objects[n]
        for i in range(len(ob.data.materials)):
            ob.data.materials[i] = deck_mat
    log.append(("수정", "바닥 재질(MD_Pad_Deck·MD_Entrance_Floor)", "원본 화살촉 판재 질감 → 큰 불규칙 판재 + 가는 이음선 절차 재질(낮은 대비, 월드 좌표 기준). 형상·외곽·충돌은 그대로. [영화 11246·11615·11748·78855]"))

    # ---- 2) 출입구: 3겹 경사 하우징 + 어깨 턱 + 테두리 + 꼭대기 조명
    EQ = Q["entrance"]
    for n in ("Entrance_Frame", "Entrance_Lamp"):
        D.objects.remove(D.objects[n])
    hole = [(1.0, 0.0), (1.0, Fm["step_z"]), (Fm["w_step"] / 2, Fm["step_z"]), (Fm["w_top"] / 2, Fm["top_z"]),
            (-Fm["w_top"] / 2, Fm["top_z"]), (-Fm["w_step"] / 2, Fm["step_z"]), (-1.0, Fm["step_z"]), (-1.0, 0.0)]
    assert abs(Fm["w_low"] / 2 - 1.0) < 1e-6

    def ring(o):
        """바깥 윤곽(바닥 오른쪽에서 위로 돌아 바닥 왼쪽까지) + 문 구멍(왼쪽 바닥에서 위로 돌아 오른쪽 바닥까지) = 아래가 열린 C자 단순 다각형."""
        bo, sz, to_, tz = o
        outline = [(bo, 0.0), (bo, sz), (to_, tz), (-to_, tz), (-bo, sz), (-bo, 0.0)]
        return [(cy + u, z) for u, z in outline + hole[::-1]]

    bm = bmesh.new(); xb = EQ["x_back"]
    for L_ in EQ["layers"]:
        xf = xb - L_["dx"]
        loft_yz(bm, ring(L_["back"]), ring(L_["front"]), xb, xf)
        xb = xf
    x_front = xb
    sur_mat = M0.mat_metal("MDX_SurroundMetal", (0.155, 0.14, 0.128), (0.07, 0.064, 0.058))
    M0.new_obj("Entrance_Surround", bm, [sur_mat], "MD_Entrance", "새로 만듦",
               "[영화 78862·11748] 문 둘레 넓은 경사 하우징(3겹, 바닥 쪽이 넓고 위로 좁아짐). 문 구멍(하부 수직 문설주 2.0 m → 어깨 단차 1.3 m → 상부 경사 → 꼭대기 2.85 m)은 POC01과 같음. 겹 두께·외곽 폭은 제작값", coll)
    bm = bmesh.new(); Lg = EQ["ledge"]
    for s in (1, -1):
        lo = sorted((cy + s * Lg["y_in"], cy + s * Lg["y_out"]))
        M0.box(bm, (x_front - Lg["dx"], lo[0], Lg["z0"]), (x_front + 0.02, lo[1], Lg["z1"]))
    M0.new_obj("Entrance_Shoulder_Ledge", bm, [M0.mat_metal("MDX_TrimMetal", (0.26, 0.22, 0.19), (0.12, 0.1, 0.09))], "MD_Entrance", "새로 만듦",
               "[영화 78862] 어깨 높이(1.3 m) 수평 턱. 크기는 제작값", coll)
    bm = bmesh.new(); t = EQ["frame_w"]
    for i in range(len(hole)):
        a, b = Vector((x_front - EQ["frame_dx"], cy + hole[i][0], hole[i][1])), Vector((x_front - EQ["frame_dx"], cy + hole[(i + 1) % len(hole)][0], hole[(i + 1) % len(hole)][1]))
        if a.z == 0.0 and b.z == 0.0:
            continue
        d = (b - a); e = d / d.length; nrm = Vector((0, -e.z, e.y))
        nrm = nrm if (Vector((0, a.y - cy, a.z - 1.4)).dot(nrm) > 0) else -nrm
        q = [a, b, b + nrm * t, a + nrm * t]
        vs = [bm.verts.new(p + Vector((dx, 0, 0))) for dx in (0.0, EQ["frame_dx"]) for p in q]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[k] for k in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    M0.new_obj("Entrance_Frame", bm, [M0.mat_metal("MDX_TrimMetal", (0.26, 0.22, 0.19), (0.12, 0.1, 0.09))], "MD_Entrance", "새로 만듦", "[영화 78862] 문 윤곽을 따르는 겹층 테두리(맨 앞 겹 앞면)", coll)
    Lp = EQ["lamp"]; bm = bmesh.new()
    M0.box(bm, (x_front - Lp["dx"], cy - Lp["half_w"], Lp["z0"]), (x_front + 0.02, cy + Lp["half_w"], Lp["z1"]))
    M0.new_obj("Entrance_Lamp", bm, [M0.mat_emit("MDX_LampCool", (0.85, 0.92, 1.0), 25.0)], "MD_Entrance", "새로 만듦", "[영화 78862·11748] 문 꼭대기 바로 위 하향 조명", coll)
    D.objects["Entrance_Film_Infill"].data.materials[0] = D.materials["MDX_FacilityMetal"]      # 영화 윤곽 판을 시설 외벽과 같은 재질로(별도 패치처럼 보이지 않게)
    log.append(("수정", "출입구", f"문 둘레에 3겹 경사 하우징(x {x_front:.2f}~{EQ['x_back']} m, 앞으로 {EQ['x_back'] - x_front:.2f} m) + 어깨 턱 + 맨 앞 테두리 + 꼭대기 조명 재배치. 문 구멍 크기·충돌 통행 폭 2.0 m는 POC01과 같음. 영화 윤곽 판 재질을 외벽과 통일"))

    # ---- 3) 낮은 상자: 대각 격자 → 경사 외벽·테두리·리브·후퇴한 조명부
    DQ = Q["devices"]; old = D.objects["MD_LowCrates"]
    verts = [v.co.copy() for v in old.data.vertices]
    foot = []
    for sel in (lambda y: y < DQ["split_y"], lambda y: y >= DQ["split_y"]):
        vs = [v for v in verts if sel(v.y)]
        foot.append((min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs)))
    D.objects.remove(old)
    body, trim_b, glow = bmesh.new(), bmesh.new(), bmesh.new()
    pl, H = DQ["plinth_h"], DQ["height"]; bt = DQ["batter"]; rm = DQ["rim"]; pk = DQ["pocket"]; rb = DQ["ribs"]
    for k, (x0, x1, y0, y1) in enumerate(foot):
        M0.box(body, (x0, y0, 0.0), (x1, y1, pl))
        ib, it, tz = bt["bottom_inset"], bt["top_inset"], bt["top_z"]
        loft_rect(body, (x0 + ib, x1 - ib, y0 + ib, y1 - ib), pl, (x0 + it, x1 - 0.3, y0 + it, y1 - 0.3), tz)          # 보이는 면(−X·−Y)은 더 크게 기울고 뒷면은 완만
        ro, ri = rm["outer_inset"], rm["inner_inset"]
        xo0, xo1, yo0, yo1 = x0 + ro, x1 - 0.25, y0 + ro, y1 - 0.25
        xi0, xi1, yi0, yi1 = x0 + ri, x1 - ri, y0 + ri, y1 - ri
        z0r = 0.62
        M0.box(trim_b, (xo0, yo0, z0r), (xi0, yo1, rm["z1"])); M0.box(trim_b, (xi1, yo0, z0r), (xo1, yo1, rm["z1"]))
        M0.box(trim_b, (xi0, yo0, z0r), (xi1, yi0, rm["z1"])); M0.box(trim_b, (xi0, yi1, z0r), (xi1, yo1, rm["z1"]))
        # 후퇴한 조명부(윗면 안쪽으로 파인 자리): 발광면 + 세운 가는 살
        gi = pk["inset"]
        M0.box(glow, (x0 + gi, y0 + gi, tz), (x1 - gi, y1 - gi, tz + 0.012))
        ns = pk["slats"]; sx0, sx1 = x0 + gi, x1 - gi
        for s in range(ns):
            cx = sx0 + (sx1 - sx0) * (s + 0.5) / ns
            M0.box(trim_b, (cx - 0.025, y0 + gi, tz), (cx + 0.025, y1 - gi, tz + 0.1))
        # 겹친 리브: −X 면(y 방향으로 줄지음, 한쪽 끝으로 갈수록 낮아짐) · −Y 면(x 방향)
        xb_, xt_ = x0 + ib, x0 + it
        for r in range(rb["count_x"]):
            yc = y0 + 0.55 + (y1 - y0 - 1.1) * r / (rb["count_x"] - 1)
            f = r / (rb["count_x"] - 1); f = f if k == 0 else 1 - f                     # 위쪽 상자(k 0)는 +Y쪽, 다른 쪽은 −Y쪽이 낮음
            zr = rb["z_max"] - (rb["z_max"] - rb["z_min"]) * f
            xr = xb_ + (xt_ - xb_) * (zr - pl) / (tz - pl)
            prism(trim_b, [(xb_, pl), (xb_ - rb["stand"], pl), (xr - rb["stand"], zr), (xr, zr)], 'y', yc - rb["width"] / 2, yc + rb["width"] / 2)
        yb_, yt_ = y0 + ib, y0 + it
        for r in range(rb["count_y"]):
            xc = x0 + 0.9 + (x1 - x0 - 1.8) * r / max(1, rb["count_y"] - 1)
            f = r / max(1, rb["count_y"] - 1)
            zr = rb["z_max"] - (rb["z_max"] - rb["z_min"]) * f * 0.8
            yr = yb_ + (yt_ - yb_) * (zr - pl) / (tz - pl)
            prism(trim_b, [(yb_, pl), (yb_ - rb["stand"], pl), (yr - rb["stand"], zr), (yr, zr)], 'x', xc - rb["width"] / 2, xc + rb["width"] / 2)
    dev_mat = M0.mat_metal("MDX_DeviceMetal", (0.2, 0.172, 0.15), (0.095, 0.082, 0.072))
    trim_m = M0.mat_metal("MDX_TrimMetal", (0.26, 0.22, 0.19), (0.12, 0.1, 0.09))
    glow_m = M0.mat_emit("MDX_PocketGlow", (1.0, 0.78, 0.5), pk.get("glow_strength", 2.4))
    me = D.meshes.new("MD_LowCrates")
    allbm = bmesh.new()
    # 재질 슬롯 3개를 한 메시에: 각 bmesh를 같은 메시로 합치며 재질 번호를 붙임
    for src, mi in ((body, 0), (trim_b, 1), (glow, 2)):
        tmp = D.meshes.new("t"); src.to_mesh(tmp); src.free()
        allbm.from_mesh(tmp)
        for f in allbm.faces[-len(tmp.polygons):]:
            f.material_index = mi
        D.meshes.remove(tmp)
    allbm.to_mesh(me); allbm.free()
    for m_ in (dev_mat, trim_m, glow_m):
        me.materials.append(m_)
    dev = D.objects.new("MD_LowCrates", me); coll("MD_Pad").objects.link(dev)
    dev["md_role"] = "교체"; dev["md_basis"] = "[영화 78855·11246·11615] 경사 외벽·두꺼운 상부 테두리·겹친 리브·후퇴한 조명부(대각 격자 상자 교체). 보이지 않는 뒷면은 추정. 바닥 투영 크기는 POC01 상자와 같음"
    log.append(("교체", "낮은 상자 2개(MD_LowCrates)", f"대각 격자 상자 → 경사 외벽·상부 테두리·리브·후퇴한 조명부 장치. 바닥 크기 {[tuple(round(v, 2) for v in f) for f in foot]}, 높이 {H} m(POC01 상자와 같음)"))

    # ---- 4) 지붕: 처마 아래 후퇴부 + 윗면 비스듬한 가장자리 + 마스트
    RQ = Q["roof"]; R = P["roof"]
    for n in ("MD_Roof_Slab", "MD_Roof_Slab_End"):
        D.objects.remove(D.objects[n])
    lo, hi = R["lo"], R["hi"]; full = (lo[0], hi[0], lo[1], hi[1]); z_lo, z_hi = lo[2], hi[2]
    ins = lambda d: (full[0] + d, full[1] - d, full[2] + d, full[3] - d)
    bm = bmesh.new()
    loft_rect(bm, ins(RQ["soffit_inset"]), z_lo, ins(RQ["soffit_inset"]), RQ["soffit_z1"])              # 처마 아래 후퇴부
    loft_rect(bm, ins(0.0), RQ["soffit_z1"], ins(0.0), RQ["edge_z1"])                                    # 가장자리 두꺼운 띠
    loft_rect(bm, ins(0.0), RQ["edge_z1"], ins(RQ["top_bevel_inset"]), z_hi)                             # 윗면 비스듬한 가장자리
    Mk = RQ["mast"]; mx, my, g, pw = Mk["x"], Mk["y"], Mk["half_gap"], Mk["post"]
    bb = Mk["base"] / 2
    M0.box(bm, (mx - bb, my - bb - g, z_hi), (mx + bb, my + bb + g, z_hi + 0.25))
    for s in (1, -1):
        M0.box(bm, (mx - pw / 2, my + s * g - pw / 2, z_hi + 0.25), (mx + pw / 2, my + s * g + pw / 2, z_hi + Mk["h"]))
    for zr in Mk["rungs"]:
        M0.box(bm, (mx - Mk["rung_t"] / 2, my - g, z_hi + zr), (mx + Mk["rung_t"] / 2, my + g, z_hi + zr + Mk["rung_t"]))
    zs = [0.25] + Mk["rungs"]
    for k_, (a_, b_) in enumerate(zip(zs, zs[1:])):                                                          # 가로대 사이 사선 보강(격자 느낌, 번갈아 방향)
        sg = 1 if k_ % 2 == 0 else -1
        prism(bm, [(my - g * sg, z_hi + a_), (my - g * sg + 0.09 * sg, z_hi + a_), (my + g * sg, z_hi + b_), (my + g * sg - 0.09 * sg, z_hi + b_)], 'x', mx - 0.04, mx + 0.04)
    roof_mat = M0.mat_metal("MDX_RoofMetal", (0.11, 0.10, 0.095), (0.05, 0.045, 0.043))
    roof = M0.new_obj("MD_Roof_Slab", bm, [roof_mat], "MD_Facility", "교체",
                      "[영화 11206·11233] 두껍고 가장자리가 비스듬한 슬래브 + 처마 아래 후퇴부 + 지붕 위 격자 마스트(마스트 높이는 제작값). 윤곽·돌출 2.25 m·두께 1.8 m는 POC01 그대로", coll)
    bm = bmesh.new(); bm.from_mesh(roof.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, P["end_split_y"], 0), plane_no=(0, 1, 0))
    bm.to_mesh(roof.data); bm.free()
    M0.extract(roof, lambda c, f: c.y > P["end_split_y"], "MD_Roof_Slab_End", "MD_Facility", "교체", roof["md_basis"], coll)
    # 마스트 등(작은 발광점): 밑동 양옆·꼭대기
    bm = bmesh.new()
    for yy in (my - g - 0.5, my + g + 0.5):
        M0.box(bm, (mx - 0.1, yy - 0.1, z_hi + 0.25), (mx + 0.1, yy + 0.1, z_hi + 0.55))
    M0.box(bm, (mx - 0.1, my - 0.1, z_hi + Mk["h"]), (mx + 0.1, my + 0.1, z_hi + Mk["h"] + 0.2))
    M0.new_obj("Roof_Mast_Lights", bm, [M0.mat_emit("MDX_MastLight", (0.75, 1.0, 0.8), 14.0)], "MD_Facility", "새로 만듦", "[영화 11206] 지붕·마스트의 작은 녹백색 점등", coll)
    log.append(("교체", "지붕(MD_Roof_Slab·_End)", f"윤곽 그대로(돌출 {R['front_overhang']} m, 두께 {z_hi - z_lo:.1f} m). 처마 아래 후퇴부 {RQ['soffit_inset']} m, 윗면 가장자리 비스듬히({RQ['top_bevel_inset']} m 안쪽), 지붕 위 마스트 높이 {Mk['h']} m(제작값)"))

    for o in (dev, ):
        for p in o.data.polygons:
            p.use_smooth = False
    rep["log"] += [{"구분": a, "대상": b, "내용": c} for a, b, c in log]
    return rep
