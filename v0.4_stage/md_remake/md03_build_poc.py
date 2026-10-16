"""4·5단계 — MD_REMAKE_POC01: Movie Duels duel_mus_both 착륙장 영역을 출발 형상으로 복사하고, 축척 보정 후 영화·게임에 맞게 고친다. Blender(bpy).
입력: MD_SOURCE_IMPORT.blend(md01) — 장면 SRC_duel_mus_both만 쓴다(duel_mustafar는 합치지 않음). 기존 A3e·v0.3 형상은 열지 않는다.
설정: md_poc01.json (선택 영역, 좌표 변환, 제거·수정 규칙, 영화 근거)
출력: <출력 .blend> — 장면 하나(MD_REMAKE_POC01), 객체마다 "md_role"(유지/수정/교체/새로 만듦)과 "md_basis"(근거)를 기록
단계:
  1) 영역 복사: 원본 좌표(u)에서 선택 영역 안 면만 복사(원본 장면은 그대로).
  2) 제거(D): 맵에 박힌 우주선, 판 위 잡동사니, 크레넬레이션 기둥, 용암 — 규칙은 md_poc01.json "remove".
  3) 축척·축 보정: X = (3888 − x)·S + 14.5, Y = −(y + 952)·S, Z = (z − 168)·S, S = 0.028125 m/u (JKA 플레이어 64 u = 1.8 m).
     → 시설이 +X(게임 카메라 오른쪽 위), 판 윗면 z 0. 기존 게임 카메라(stage_cam)와 같은 방향 관계.
  4) 영화 기준 수정(--stage modify): 틈, 출입구 바닥, 지붕, 판 확장·절삭, 가장자리 장치, 재질 분리.
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/md_remake/md03_build_poc.py <MD_SOURCE_IMPORT.blend> <출력 .blend> [--stage copy|modify]
"""
import json, math, os, sys

import bpy, bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = sys.argv[1], sys.argv[2]
STAGE = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "modify"
C = json.load(open(os.path.join(HERE, "md_poc01.json"), encoding="utf-8"))
T = C["transform"]; S = T["scale_m_per_u"]
M = Matrix.Translation(Vector(T["offset_m"])) @ Matrix.Scale(S, 4) @ Matrix.Rotation(math.radians(T["rot_z_deg"]), 4, 'Z') @ Matrix.Translation(Vector(T["pre_translate_u"]))

bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
src_scene = D.scenes["SRC_" + C["source_map"]]
for sc in list(D.scenes):                       # 다른 맵 장면은 이 파일에서 뺌(합치지 않음 — 원본 .blend는 그대로)
    if sc is not src_scene:
        for o in list(sc.collection.all_objects):
            D.objects.remove(o)
        D.scenes.remove(sc)
src_objs = list(src_scene.collection.all_objects)
scene = D.scenes.new("MD_REMAKE_POC01"); bpy.context.window.scene = scene if bpy.context.window else None
COLS = {}


def coll(name):
    if name not in COLS:
        c = D.collections.new(name); scene.collection.children.link(c); COLS[name] = c
    return COLS[name]


def tex_of(ma):
    im = [n.image.name for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image] if ma and ma.node_tree else []
    return im[0].replace("textures__", "") if im else ""


def in_box(c, b):
    return all(b[0][i] <= c[i] <= b[1][i] for i in range(3))


def rule_hit(rule, c, tex):
    if "tex" in rule and not any(t in tex for t in rule["tex"]):
        return False
    if "box_u" in rule and not in_box(c, rule["box_u"]):
        return False
    if "not_box_u" in rule and any(in_box(c, b) for b in rule["not_box_u"]):
        return False
    return True


# ---------------------------------------------------------------- 1~3. 영역 복사 · 제거 · 축척
REG = C["region_u"]; removed = {}; kept = {}
groups = {}                                      # 역할 → bmesh
for o in src_objs:
    ma = o.data.materials[0] if o.data.materials else None
    tex = tex_of(ma)
    bm = bmesh.new(); bm.from_mesh(o.data); dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        if not in_box(c, REG):
            dead.append(f); continue
        for r in C["remove"]:
            if rule_hit(r, c, tex):
                dead.append(f); removed[r["id"]] = removed.get(r["id"], 0) + 1; break
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    if not bm.faces:
        bm.free(); continue
    bm.transform(M)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])          # 원본 BSP 감김 방향이 반대(법선 아래) → 위로
    # 역할 분류(변환 후 미터 좌표)
    for f in bm.faces:
        f.material_index = 0
    role = None
    for g in C["groups"]:
        if "tex" in g and any(t in tex for t in g["tex"]):
            role = g["name"]; break
    me = D.meshes.new("tmp_" + o.name); bm.to_mesh(me); bm.free()
    if ma:
        me.materials.append(ma)
    groups.setdefault(role or "AUTO", []).append(me)
    kept[tex or ("grey:" + (ma.name if ma else "?"))] = kept.get(tex or ("grey:" + (ma.name if ma else "?")), 0) + len(me.polygons)

# AUTO 그룹은 위치로 나눈다(미터): 시설(X ≥ 시설 정면) / 판·통로 구조
FX = C["facility_front_x_m"]


def join(meshes, name, col, role, basis):
    bm = bmesh.new(); mats = []
    for me in meshes:
        off = len(mats); mats += list(me.materials)
        t = bmesh.new(); t.from_mesh(me)
        for f in t.faces:
            f.material_index += off
        m2 = D.meshes.new("t"); t.to_mesh(m2); t.free(); bm.from_mesh(m2); D.meshes.remove(m2)
    out = D.meshes.new(name); bm.to_mesh(out); bm.free()
    for m in mats:
        out.materials.append(m)
    ob = D.objects.new(name, out); coll(col).objects.link(ob)
    ob["md_role"] = role; ob["md_basis"] = basis; ob["md_source"] = f"Movie Duels {C['source_map']}.obj (원본 좌표 → md_poc01.json transform)"
    return ob


def split_by(meshes, pred):
    a, b = [], []
    for me in meshes:
        bm = bmesh.new(); bm.from_mesh(me); bm2 = bm.copy()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not pred(f.calc_center_median())], context='FACES')
        bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if pred(f.calc_center_median())], context='FACES')
        for dst, src in ((a, bm), (b, bm2)):
            if src.faces:
                m2 = D.meshes.new(me.name); src.to_mesh(m2)
                for mt in me.materials:
                    m2.materials.append(mt)
                dst.append(m2)
            src.free()
    return a, b


objs = {}
for g in C["groups"]:
    if g["name"] in groups:
        objs[g["name"]] = join(groups.pop(g["name"]), g["name"], g["collection"], "유지", g["basis"])
auto = groups.pop("AUTO", [])
fac, rest = split_by(auto, lambda c: c.x >= FX - 0.05 or (c.x >= C["pad_facility_edge_x_m"] + 0.05 and c.z > 0.3))     # 시설 정면 너머 + 판 끝과 정면 사이 위로 선 것(경사 기둥 등)
objs["MD_Facility"] = join(fac, "MD_Facility", "MD_Facility", "유지", "duel_mus_both 시설 몸체·정면·베이·사다리꼴 입구(원본 형상)")
objs["MD_Pad_Structure"] = join(rest, "MD_Pad_Structure", "MD_Pad", "유지", "duel_mus_both 판 측면·테두리·아래면·받침·시설 앞 경사로(원본 형상)")

rep = {"removed_faces_by_rule": removed, "kept_faces_by_texture": kept}
if STAGE == "copy":
    scene["md_stage"] = "copy"
else:
    sys.path.insert(0, HERE)
    import md_modify
    rep["modify"] = md_modify.apply(scene, objs, C, coll)
D.scenes.remove(src_scene)
for o in [o for o in D.objects if not o.users_scene]:
    D.objects.remove(o)
for me in [m for m in D.meshes if m.users == 0]:
    D.meshes.remove(me)
bpy.context.window.scene = scene if bpy.context.window else None
scene["md_report"] = json.dumps(rep, ensure_ascii=False)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT))
json.dump(rep, open(os.path.splitext(os.path.abspath(OUT))[0] + "_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for o in scene.objects:
    if o.type == 'MESH' and o.data.vertices:
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        print(o.name, len(o.data.polygons), [round(min(v[i] for v in vs), 2) for i in range(3)], [round(max(v[i] for v in vs), 2) for i in range(3)])
print("SAVED", OUT, json.dumps(removed, ensure_ascii=False))
