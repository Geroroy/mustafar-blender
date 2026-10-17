"""ART01-2 재질·조명 재작업 — MO_STAGE.blend(원본 형상·UV·재질 슬롯 그대로)에서 재질 노드와 조명만 새로 만든다. Blender(bpy).
형상은 한 점도 바꾸지 않는다: 메시·UV·재질 슬롯·객체·MO_FIT 변환·게임 카메라 그대로. 바뀌는 것:
  1) 재질 89개의 노드 트리(이름 material_N 유지 → 면↔재질 연결 불변). art_materials.json의 표면 분류로 하나의 그래픽 기준에서 만든다.
     원본 질감은 '배치'만 쓴다(art_masks.py가 뽑은 이음선·판 톤 마스크를 원본 UV로). 질감이 없는 재질도 용도로 만든다.
  2) 조명: 캐릭터 굽기와 같은 방향의 주광(화면 좌상단·앞쪽, 고도 약 46°), 부드러운 그림자, 반구 앰비언트(위 차가운 회색·아래 따뜻한 갈색),
     용암 발광은 간접광으로만(세기 제한). 카메라 광선에만 깊이 연무(판 아래·먼 곳) → 용암·암벽이 뒤로 물러나게.
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art02_build.py <MO_STAGE.blend> <masks 폴더> <출력 .blend>
"""
import json, math, os, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, MASKS, OUT = (os.path.abspath(p) for p in sys.argv[-3:])
SPEC = json.load(open(os.path.join(HERE, "art_materials.json"), encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data; sc = D.scenes["MO_STAGE"]
CL = SPEC["classes"]; LIGHT = SPEC["lighting"]; HZ = SPEC["haze"]


# ---------------------------------------------------------------- 노드 도우미
class NB:
    def __init__(self, nt):
        self.nt = nt; self.x = 0

    def n(self, kind, **props):
        nd = self.nt.nodes.new(kind); nd.location = (self.x, 0); self.x += 40
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.nt.links.new(a, b)

    def val(self, v):
        nd = self.n("ShaderNodeValue"); nd.outputs[0].default_value = v; return nd.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        nd = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                nd.inputs[i].default_value = x
            else:
                self.link(x, nd.inputs[i])
        return nd.outputs[0]

    def mapr(self, x, a, b, c=0.0, d=1.0, clamp=True, interp='LINEAR'):
        nd = self.n("ShaderNodeMapRange", clamp=clamp, interpolation_type=interp)
        self.link(x, nd.inputs["Value"])
        for k, v in (("From Min", a), ("From Max", b), ("To Min", c), ("To Max", d)):
            nd.inputs[k].default_value = v
        return nd.outputs["Result"]

    def mixc(self, fac, a, b, blend='MIX'):
        nd = self.n("ShaderNodeMix", data_type='RGBA', blend_type=blend, clamp_result=False)
        ins = {i.identifier: i for i in nd.inputs}
        for sock, v in ((ins["Factor_Float"], fac), (ins["A_Color"], a), (ins["B_Color"], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v[:3], 1.0)
            else:
                self.link(v, sock)
        return {o.identifier: o for o in nd.outputs}["Result_Color"]

    def rgb(self, c):
        nd = self.n("ShaderNodeRGB"); nd.outputs[0].default_value = (*c[:3], 1.0); return nd.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        nd = self.n("ShaderNodeTexNoise"); nd.noise_dimensions = '3D'
        self.link(vec, nd.inputs["Vector"]); nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail; nd.inputs["Roughness"].default_value = rough
        return nd.outputs["Fac"]

    def img(self, path, uv, noncolor=True):
        im = D.images.load(path, check_existing=True)
        if noncolor:
            im.colorspace_settings.name = 'Non-Color'
        nd = self.n("ShaderNodeTexImage"); nd.image = im; nd.interpolation = 'Linear'
        self.link(uv, nd.inputs["Vector"]); return nd


def scale_vec(b, vec, s):
    nd = b.n("ShaderNodeVectorMath", operation='MULTIPLY'); b.link(vec, nd.inputs[0]); nd.inputs[1].default_value = (s, s, s) if isinstance(s, (int, float)) else s; return nd.outputs[0]


def haze_wrap(b, shader_out, geo, kind):
    """카메라 광선에만 깊이 연무: 판 윗면(z 0) 아래로 내려갈수록, 판 중심에서 멀어질수록 연무색으로 섞는다(다른 광선에는 영향 없음 → 조명 불변)."""
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(geo.outputs["Position"], sep.inputs[0])
    depth = b.mapr(sep.outputs["Z"], HZ["z_top"], HZ["z_bottom"], 0.0, HZ["max_depth"], interp='SMOOTHSTEP')
    dx = b.math('SUBTRACT', sep.outputs["X"], HZ["center"][0]); dy = b.math('SUBTRACT', sep.outputs["Y"], HZ["center"][1])
    r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', dx, dx), b.math('MULTIPLY', dy, dy)))
    far = b.mapr(r, HZ["r_near"], HZ["r_far"], 0.0, HZ["max_far"], interp='SMOOTHSTEP')
    f = b.math('MAXIMUM', depth, far)
    if kind == "lava":
        f = b.math('MAXIMUM', f, HZ["lava_min"])
    lp = b.n("ShaderNodeLightPath")
    f = b.math('MULTIPLY', f, lp.outputs["Is Camera Ray"])
    em = b.n("ShaderNodeEmission"); em.inputs["Color"].default_value = (*HZ["color"], 1); em.inputs["Strength"].default_value = 1.0
    mx = b.n("ShaderNodeMixShader"); b.link(f, mx.inputs[0]); b.link(shader_out, mx.inputs[1]); b.link(em.outputs[0], mx.inputs[2])
    return mx.outputs[0]


def build(ma, cls_name, mask_name, orig_img):
    c = CL[cls_name]
    nt = ma.node_tree; nt.nodes.clear(); b = NB(nt)
    out = b.n("ShaderNodeOutputMaterial")
    geo = b.n("ShaderNodeNewGeometry"); tc = b.n("ShaderNodeTexCoord")
    uv = tc.outputs["UV"]; P = geo.outputs["Position"]
    sepN = b.n("ShaderNodeSeparateXYZ"); b.link(geo.outputs["Normal"], sepN.inputs[0]); nz = sepN.outputs["Z"]
    kind = c["kind"]

    if kind == "lava":
        # 원본 질감의 큰 흐름(glow_lava, 원본 UV) × 큰 절차 잡음 → 낮은 대비의 발광. 검은 굳은 껍질은 넓고 부드럽게.
        g = b.img(os.path.join(MASKS, "glow_lava.png"), uv).outputs["Color"]
        gs = b.n("ShaderNodeSeparateColor"); b.link(g, gs.inputs[0]); g = gs.outputs[0]
        nz1 = b.noise(scale_vec(b, P, 1.0), c["noise_scale"], 2.0, 0.45)
        m = b.math('ADD', b.math('MULTIPLY', g, 0.75), b.math('MULTIPLY', nz1, 0.25))
        hot = b.mapr(m, c["hot_lo"], c["hot_hi"], 0.0, 1.0, interp='SMOOTHSTEP')
        # 굳은 껍질 판 사이의 가는 균열(보로노이 경계, 수 m 크기). 원본 흐름이 밝은 곳일수록 균열이 더 밝다 → 원본 분포를 유지하며 '용암' 형태로 읽힘
        dn = b.n("ShaderNodeTexNoise"); dn.noise_dimensions = '3D'; b.link(P, dn.inputs["Vector"]); dn.inputs["Scale"].default_value = 0.12; dn.inputs["Detail"].default_value = 3.0
        dv = b.n("ShaderNodeVectorMath", operation='SUBTRACT'); b.link(dn.outputs["Color"], dv.inputs[0]); dv.inputs[1].default_value = (0.5, 0.5, 0.5)
        dw = b.n("ShaderNodeVectorMath", operation='MULTIPLY_ADD'); b.link(dv.outputs[0], dw.inputs[0]); dw.inputs[1].default_value = (c["crack_warp"],) * 3; b.link(P, dw.inputs[2])
        vo = b.n("ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE', voronoi_dimensions='3D'); b.link(dw.outputs[0], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = c["crack_scale"]; vo.inputs["Randomness"].default_value = 0.9
        crack = b.mapr(vo.outputs["Distance"], 0.0, c["crack_w"], 1.0, 0.0, interp='SMOOTHSTEP')
        crack = b.math('MULTIPLY', crack, b.mapr(m, c["crack_from"], 0.8, c["crack_min"], 1.0, interp='SMOOTHSTEP'))
        hot = b.math('MAXIMUM', hot, b.math('MULTIPLY', crack, c["crack_amt"]))
        col = b.mixc(hot, tuple(c["emit_cool"]), tuple(c["emit_hot"]))
        strength = b.mapr(hot, 0.0, 1.0, c["strength_lo"], c["strength_hi"])
        bs = b.n("ShaderNodeBsdfPrincipled"); bs.inputs["Base Color"].default_value = (*c["crust"], 1); bs.inputs["Roughness"].default_value = 0.85
        b.link(col, bs.inputs["Emission Color"]); b.link(strength, bs.inputs["Emission Strength"])
        b.link(haze_wrap(b, bs.outputs[0], geo, "lava"), out.inputs[0]); return

    if kind == "lamp":
        # 원본 조명 기구(셰이더 이름 light_*). 질감이 있으면 그 그림을, 없으면 지정 색을 약한 발광으로. 새 발광 장식은 만들지 않는다.
        em = b.n("ShaderNodeEmission"); em.inputs["Strength"].default_value = c["strength"]
        if orig_img is not None and c.get("use_texture", True):
            it = b.n("ShaderNodeTexImage"); it.image = orig_img; b.link(uv, it.inputs["Vector"]); b.link(it.outputs["Color"], em.inputs["Color"])
        else:
            em.inputs["Color"].default_value = (*c["color"], 1)
        b.link(haze_wrap(b, em.outputs[0], geo, kind), out.inputs[0]); return

    # ---- 공통 표면(금속·바닥·암벽·천): 기준색 × (큰 얼룩 · 이음선 · 판 톤) → 그을음(틈·아래) → 마모(볼록 모서리) → 재(윗면)
    if kind == "cloth" and orig_img is not None:
        it = b.n("ShaderNodeTexImage"); it.image = orig_img; b.link(uv, it.inputs["Vector"])
        base = b.mixc(0.5, it.outputs["Color"], tuple(c["base"]), 'MIX')
    else:
        base = b.rgb(c["base"])
    big = b.noise(scale_vec(b, P, 1.0), c["var_scale"], 2.0, 0.5)                    # 큰 얼룩(수 m) — 게임 배율에서 판 단위로 읽히는 크기
    mul = b.mapr(big, 0.3, 0.7, 1.0 - c["var"], 1.0 + c["var"])
    if c.get("soot_patch", 0) > 0:                                                    # 중간 그을음 반점(0.5~1 m), 낮은 대비
        mid = b.noise(scale_vec(b, P, 1.0), c.get("patch_scale", 1.2), 3.0, 0.55)
        patch = b.mapr(mid, 0.52, 0.72, 0.0, c["soot_patch"], interp='SMOOTHSTEP')
        mul = b.math('MULTIPLY', mul, b.math('SUBTRACT', 1.0, patch))
    if mask_name:                                                                     # 원본 UV 배치의 이음선(어둡게)
        sm = b.img(os.path.join(MASKS, f"seam_{mask_name}.png"), uv).outputs["Color"]
        ss = b.n("ShaderNodeSeparateColor"); b.link(sm, ss.inputs[0])
        mul = b.math('MULTIPLY', mul, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', ss.outputs[0], c["seam"])))
        if c.get("plate", 0) > 0:                                                     # 판마다 아주 약한 톤 차이
            pm = b.img(os.path.join(MASKS, f"plate_{mask_name}.png"), uv).outputs["Color"]
            ps = b.n("ShaderNodeSeparateColor"); b.link(pm, ps.inputs[0])
            mul = b.math('MULTIPLY', mul, b.mapr(ps.outputs[0], 0.0, 1.0, 1.0 - c["plate"], 1.0 + c["plate"]))
    elif c.get("uv_panel", 0) > 0:                                                    # 질감 없는 원본 재질: 원본 UV 격자(타일 1/2)에 낮은 대비 패널 이음선
        sep = b.n("ShaderNodeSeparateXYZ"); b.link(uv, sep.inputs[0]); lines = None
        for ax in ("X", "Y"):
            f = b.math('FRACT', b.math('MULTIPLY', sep.outputs[ax], c.get("uv_panel_div", 2.0)))
            d = b.math('MINIMUM', f, b.math('SUBTRACT', 1.0, f))
            l = b.mapr(d, 0.0, c.get("uv_panel_w", 0.012), 1.0, 0.0)
            lines = l if lines is None else b.math('MAXIMUM', lines, l)
        mul = b.math('MULTIPLY', mul, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', lines, c["uv_panel"])))
    cm = b.n("ShaderNodeCombineColor")
    for i in range(3):
        b.link(mul, cm.inputs[i])
    col = b.mixc(1.0, base, cm.outputs[0], 'MULTIPLY')
    # 그을음: 틈(AO) + 수직면의 아래로 흐른 자국(세로로 늘인 큰 잡음, 약하게)
    ao = b.n("ShaderNodeAmbientOcclusion", samples=8, only_local=False); ao.inputs["Distance"].default_value = c.get("ao_dist", 0.6)
    crev = b.math('SUBTRACT', 1.0, ao.outputs["AO"])
    soot = b.math('MULTIPLY', b.mapr(crev, 0.05, 0.6, 0.0, 1.0, interp='SMOOTHSTEP'), c["soot"])
    if c.get("streak", 0) > 0:
        sv = b.n("ShaderNodeVectorMath", operation='MULTIPLY'); b.link(P, sv.inputs[0]); sv.inputs[1].default_value = (1.4, 1.4, 0.22)
        st = b.mapr(b.noise(sv.outputs[0], 1.0, 2.0, 0.45), 0.5, 0.75, 0.0, 1.0, interp='SMOOTHSTEP')
        side = b.math('SUBTRACT', 1.0, b.math('ABSOLUTE', nz))
        soot = b.math('MAXIMUM', soot, b.math('MULTIPLY', b.math('MULTIPLY', st, side), c["streak"]))
    col = b.mixc(soot, col, tuple(c.get("soot_col", (0.012, 0.011, 0.011))))
    # 마모: 볼록 모서리(베벨 법선이 기하 법선에서 벗어나고 AO가 열린 곳) → 밝게·덜 거칠게
    wear = None
    if c.get("wear", 0) > 0:
        bev = b.n("ShaderNodeBevel", samples=4); bev.inputs["Radius"].default_value = c.get("bevel_r", 0.035)
        dp = b.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); b.link(bev.outputs[0], dp.inputs[0]); b.link(geo.outputs["Normal"], dp.inputs[1])
        edge = b.mapr(dp.outputs["Value"], 0.985, 0.80, 0.0, 1.0, interp='SMOOTHSTEP')
        wear = b.math('MULTIPLY', b.math('MULTIPLY', edge, b.mapr(ao.outputs["AO"], 0.6, 0.95, 0.0, 1.0)), c["wear"])
        col = b.mixc(wear, col, tuple(c.get("wear_col", (0.16, 0.155, 0.15))))
    # 재(윗면): 위를 향한 면에 큰 잡음으로 엷게
    if c.get("ash", 0) > 0:
        an = b.mapr(b.noise(scale_vec(b, P, 1.0), c.get("ash_scale", 0.55), 2.0, 0.5), 0.45, 0.7, 0.0, 1.0, interp='SMOOTHSTEP')
        up = b.mapr(nz, 0.6, 0.9, 0.0, 1.0)
        ash = b.math('MULTIPLY', b.math('MULTIPLY', an, up), c["ash"])
        col = b.mixc(ash, col, tuple(c.get("ash_col", (0.15, 0.14, 0.13))))
    if c.get("low_soot", 0) > 0:                                                      # 우주선 아래쪽 그을음(높이)
        sepP = b.n("ShaderNodeSeparateXYZ"); b.link(P, sepP.inputs[0])
        ls = b.mapr(sepP.outputs["Z"], c["low_soot_z"][1], c["low_soot_z"][0], 0.0, c["low_soot"], interp='SMOOTHSTEP')
        col = b.mixc(ls, col, (0.03, 0.028, 0.027))
    bs = b.n("ShaderNodeBsdfPrincipled")
    b.link(col, bs.inputs["Base Color"]); bs.inputs["Metallic"].default_value = c["metal"]
    rough = b.math('ADD', b.math('MULTIPLY', soot, c.get("soot_rough", 0.2)), c["rough"])
    if wear is not None:
        rough = b.math('SUBTRACT', rough, b.math('MULTIPLY', wear, 0.15))
    b.link(rough, bs.inputs["Roughness"])
    if "specular" in c:
        bs.inputs["Specular IOR Level"].default_value = c["specular"]
    b.link(haze_wrap(b, bs.outputs[0], geo, kind), out.inputs[0])


# ---------------------------------------------------------------- 재질 적용
assign = SPEC["materials"]; done = {}
for ma in D.materials:
    key = ma.name.split(".")[0]
    if not key.startswith("material_") or key not in assign:
        continue
    a = assign[key]
    orig = None
    if ma.node_tree:
        ims = [n.image for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        orig = ims[0] if ims else None
    build(ma, a["class"], a.get("mask"), orig)
    ma["art01_class"] = a["class"]; ma["art01_note"] = a.get("note", "")
    done[key] = a["class"]
used = {ma.name.split(".")[0] for o in sc.collection.all_objects if o.type == 'MESH' for ma in o.data.materials}
missing = sorted(used - set(done))
assert not missing, f"분류 없는 재질: {missing}"

# ---------------------------------------------------------------- 조명
for o in [o for o in sc.objects if o.type == 'LIGHT']:
    D.objects.remove(o)
L = Vector(LIGHT["key_dir_to_light"]).normalized()
ld = D.lights.new("ART_Key", 'SUN'); ld.energy = LIGHT["key_strength"]; ld.angle = math.radians(LIGHT["key_angle_deg"]); ld.color = LIGHT["key_color"]
so = D.objects.new("ART_Key", ld); sc.collection.objects.link(so); so.rotation_euler = L.to_track_quat('Z', 'Y').to_euler()
w = D.worlds.new("ART_World"); sc.world = w; nt = w.node_tree; nt.nodes.clear(); b = NB(nt)
outw = b.n("ShaderNodeOutputWorld"); tc = b.n("ShaderNodeTexCoord")
sep = b.n("ShaderNodeSeparateXYZ"); b.link(tc.outputs["Generated"], sep.inputs[0])
t = b.mapr(sep.outputs["Z"], -0.3, 0.6, 0.0, 1.0, interp='SMOOTHSTEP')
hemi = b.mixc(t, tuple(LIGHT["ground_color"]), tuple(LIGHT["sky_color"]))
bgL = b.n("ShaderNodeBackground"); b.link(hemi, bgL.inputs[0]); bgL.inputs[1].default_value = LIGHT["ambient_strength"]
bgC = b.n("ShaderNodeBackground"); bgC.inputs[0].default_value = (*HZ["color"], 1); bgC.inputs[1].default_value = 1.0
lp = b.n("ShaderNodeLightPath"); mx = b.n("ShaderNodeMixShader")
b.link(lp.outputs["Is Camera Ray"], mx.inputs[0]); b.link(bgL.outputs[0], mx.inputs[1]); b.link(bgC.outputs[0], mx.inputs[2]); b.link(mx.outputs[0], outw.inputs[0])
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.cycles.sample_clamp_indirect = 4.0
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.view_settings.exposure = LIGHT.get("exposure", 0.0)
sc["art01"] = json.dumps({"spec": "art_materials.json", "classes": done}, ensure_ascii=False)
sc.name = "MO_STAGE"                       # 내보내기 스크립트와 같은 장면 이름
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, "materials", len(done))
