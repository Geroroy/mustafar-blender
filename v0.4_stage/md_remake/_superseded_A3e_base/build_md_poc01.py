"""MD_REMAKE_POC01 — Movie Duels 추출 모델을 참고한 착륙장 리메이크 시험본(Blender bpy).
하는 일:
  1) v0.3 생성기의 MD01 배치(= A3e 시설·출입구·낮은 상자·R·외부 통로 + 새 판 외곽의 기둥·연석)를 연다.
  2) A3e 판(윗판·측벽·판재)을 빼고, duel_mustafar 착륙장의 판 형상(바닥 판재·테두리·아래면·받침 트러스·가장자리 등)을
     캐릭터 축척(0.028125 m/u)으로 옮겨 넣는다. 판 위 소품·우주선·상자·바위·용암·모드 시설 벽은 넣지 않는다.
  3) 시설 쪽 변의 테두리는 지운다(진입 바닥·외부 통로가 판과 끊김 없이 이어져야 함 — 게임 조정).
  4) 앞 끝(영화 R6 길이:너비 1.38)과 앞 바깥 모서리 절삭(사용자 요구)에서 자르고, 잘린 변에 측면·테두리를 새로 둔다.
  5) 결과를 비공개 폴더에 저장한다(모드 형상·질감은 제3자 자산이라 저장소에 올리지 않음).
실행(저장소 루트): .venv-bpy/bin/python v0.4_stage/md_remake/build_md_poc01.py <모드 models 폴더> <출력 .blend>
"""
import json, math, os, sys
import bpy, bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS, OUT = sys.argv[-2], sys.argv[-1]
DIM = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
L = DIM["v03"]["entrance_layout"]["candidates"]["MD01"]; MDR = L["md_remake"]
S = MDR["scale_m_per_unit"]; OX, OY = MDR["origin"]
PAD = [tuple(q) for q in L["pad_outline"]["poly"]]
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "v0.3", "work", "layouts", "layout_MD01.blend"))
D = bpy.data

for n in ("Landing_Platform", "Platform_Sidewalls", "Floor_Plates"):          # A3e 판 → 모드 판으로 교체
    if n in D.objects:
        D.objects.remove(D.objects[n])

before = set(D.objects)
bpy.ops.wm.obj_import(filepath=os.path.join(MODELS, "duel_mustafar.obj"), forward_axis='Y', up_axis='Z', use_split_objects=True, use_split_groups=True)
new = [o for o in D.objects if o not in before]
MTL = {}
cur = None
for line in open(os.path.join(MODELS, "duel_mustafar.mtl")):
    if line.startswith("newmtl"):
        cur = line.split()[1]
    elif line.strip().startswith("map_Kd") and cur:
        MTL[cur] = line.split()[-1]
KEEP = ("floor_", "pipe_1", "trim_4", "trim_2", "trim_3", "basic.jpg", "light_2")
X0m, X1m, Y0m, Y1m = -1310, 990, 6150, 7700                     # 모드 착륙장 판 영역(원본 좌표)
IX0, IX1, IY0, IY1 = -1250, 935, 6205, 7555                      # 판 안쪽(소품 제거용, 테두리 40 u 안)
M = Matrix.Translation((OX, OY, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Scale(S, 4) @ Matrix.Translation((-MDR["mod_pad_back_x"], -MDR["mod_pad_facility_edge_y"], 0))
# 회전 +90°: 우리 X = −(모드 Y − 6160)·S + 14.5, 우리 Y = (모드 X − 976)·S + 22.5. 확인: 아래 식과 같음
deck, struct, lights = bmesh.new(), bmesh.new(), bmesh.new()
mats = {"deck": [], "struct": [], "lights": []}
counts = {}
for o in new:
    key = o.name.split(".")[0]
    tex = MTL.get(key) or ""
    if not any(k in tex for k in KEEP):
        D.objects.remove(o); continue
    bm = bmesh.new(); bm.from_mesh(o.data)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        inside = X0m <= c.x <= X1m and Y0m <= c.y <= Y1m and -1400 <= c.z <= 20
        props = IX0 <= c.x <= IX1 and IY0 <= c.y <= IY1 and c.z > 2.0 and "floor" not in tex and "light_2" not in tex     # 판 위 소품(통·콘솔·상자 등)
        facility_rim = c.y < 6205 and c.z > -2.0 and "floor" not in tex                           # 시설 쪽 변 테두리(진입 연결을 위해 제거)
        if not inside or props or facility_rim:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    if bm.faces:
        tgt = "deck" if ("floor_" in tex and "floor_2_o" not in tex) else "lights" if "light_2" in tex else "struct"
        me = o.data; bm.to_mesh(me); bm.free()
        mi = len(mats[tgt]); mats[tgt].append(me.materials[0])
        dst = {"deck": deck, "struct": struct, "lights": lights}[tgt]
        tmp = bmesh.new(); tmp.from_mesh(me)
        for f in tmp.faces:
            f.material_index = mi
        me2 = D.meshes.new("tmp"); tmp.to_mesh(me2); tmp.free(); dst.from_mesh(me2); D.meshes.remove(me2)
        counts[tex] = counts.get(tex, 0) + len(me.polygons)
    else:
        bm.free()
    D.objects.remove(o)


def finish(bm, name, mlist, clean=False):
    bm.transform(M)
    if clean:                                   # 모드 시설 벽·기초 조각 제거(우리 시설은 틈 너머 A3e) — 판 가장자리 근처 위쪽 조각, 시설 쪽 아래 큰 판
        dead = []
        for f in bm.faces:
            c = f.calc_center_median(); xs = [v.co.x for v in f.verts]
            if max(xs) > OX + 0.1 or (c.x > OX - 4.0 and c.z < -1.7) or c.z > 0.6:
                dead.append(f)
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    for co, no in ((Vector((0, PAD[0][1], 0)), Vector((0, 1, 0))),):                     # 앞 끝 자르기(영화 R6 비율)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_inner=True)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=Vector((OX, 0, 0)), plane_no=Vector((1, 0, 0)), clear_outer=True)   # 판 시설 쪽 변(x 14.5) 너머는 열린 틈 — 모드 바닥이 틈 위로 나오지 않게
    a, b = Vector((*PAD[4], 0)), Vector((*PAD[5], 0))                                       # 앞 바깥 모서리 절삭(사용자 요구)
    e = (b - a).normalized(); nrm = Vector((-e.y, e.x, 0))                                  # 반시계 외곽의 안쪽
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=a, plane_no=nrm, clear_inner=True)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mlist:
        me.materials.append(m)
    ob = D.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob["md_source"] = "Movie Duels duel_mustafar 착륙장(축척·회전·자름)"; return ob


deck_o = finish(deck, "MD_Pad_Deck", mats["deck"])
struct_o = finish(struct, "MD_Pad_Structure", mats["struct"], clean=True)
lights_o = finish(lights, "MD_Pad_EdgeLights", mats["lights"])
# 잘린 변(앞 끝·앞 바깥 절삭)의 측면과 테두리: 모드 테두리 높이 16 u·폭 16 u, 판 두께 56 u를 그대로 씀
RH, RW, TH = 16 * S, 16 * S, 56 * S
bm = bmesh.new()
for a, b in ((PAD[5], PAD[0]), (PAD[4], PAD[5])):
    a, b = Vector((*a, 0)), Vector((*b, 0)); e = (b - a).normalized(); n = Vector((-e.y, e.x, 0))
    pts = [a, b, b + n * RW, a + n * RW]
    for z0, z1, inset in ((-TH, 0.0, 0.0), (0.0, RH, 0.0)):
        vs = [bm.verts.new((p.x, p.y, z)) for z in (z0, z1) for p in pts]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[i] for i in f])
me = D.meshes.new("MD_Pad_CutEdge"); bm.to_mesh(me); bm.free()
me.materials.append(struct_o.data.materials[0] if struct_o.data.materials else None)
cut_o = D.objects.new("MD_Pad_CutEdge", me); bpy.context.scene.collection.objects.link(cut_o)
cut_o["md_source"] = "새로 만듦: 잘린 변의 측면·테두리(모드 테두리 치수 그대로)"
# 판 전체 받침면(새로 만듦): 모드 소품을 뺀 자리의 구멍이 걷기를 막지 않도록 외곽 전체에 판재 바로 아래(−0.02 m) 채움 면
bm = bmesh.new()
top = [bm.verts.new((x, y, -0.02)) for x, y in PAD]; bot = [bm.verts.new((x, y, -TH + 0.02)) for x, y in PAD]
bm.faces.new(top); bm.faces.new(bot[::-1])
for i in range(len(PAD)):
    j = (i + 1) % len(PAD); bm.faces.new((bot[i], bot[j], top[j], top[i]))
me = D.meshes.new("MD_Pad_DeckFill"); bm.to_mesh(me); bm.free()
me.materials.append(struct_o.data.materials[0] if struct_o.data.materials else None)
fill_o = D.objects.new("MD_Pad_DeckFill", me); bpy.context.scene.collection.objects.link(fill_o)
fill_o["md_source"] = "새로 만듦: 소품 제거 자리 채움 면(게임 보행용)"
# 시설 쪽 변: 모드 판재가 x 14.05에서 끝나고 테두리를 지웠으므로 판 끝까지 같은 바닥 띠를 이어 진입 바닥·외부 통로와 끊김 없게(새로 만듦)
bm = bmesh.new()
xs_ = max(v.co.x for v in deck_o.data.vertices)
vs = [bm.verts.new(p) for p in ((xs_ - 0.05, PAD[0][1], -TH), (OX, PAD[0][1], -TH), (OX, PAD[1][1], -TH), (xs_ - 0.05, PAD[1][1], -TH),
                                 (xs_ - 0.05, PAD[0][1], 0.0), (OX, PAD[0][1], 0.0), (OX, PAD[1][1], 0.0), (xs_ - 0.05, PAD[1][1], 0.0))]
for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
    bm.faces.new([vs[i] for i in f])
me = D.meshes.new("MD_Pad_FacilityEdge"); bm.to_mesh(me); bm.free()
me.materials.append(deck_o.data.materials[0] if deck_o.data.materials else None)
edge_o = D.objects.new("MD_Pad_FacilityEdge", me); bpy.context.scene.collection.objects.link(edge_o)
edge_o["md_source"] = "새로 만듦: 시설 쪽 변 바닥 띠(테두리 제거 자리)"
for ob in (deck_o, struct_o, lights_o, cut_o, edge_o, fill_o):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    bpy.data.collections.get("Platform").objects.link(ob)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, json.dumps(counts, ensure_ascii=False))
for ob in (deck_o, struct_o, lights_o, cut_o):
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    if not vs:
        continue
    print(ob.name, len(ob.data.polygons), [round(min(v[i] for v in vs), 2) for i in range(3)], [round(max(v[i] for v in vs), 2) for i in range(3)])
