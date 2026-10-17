"""MO-5 스테이지 장면 — MO_GAMEFIT.blend(형상 불변)에 조명·게임 카메라만 더한다. Blender(bpy).
형상·재질 연결은 그대로. 질감 없는 재질(회색)도 그대로 둔다. 바뀌는 것은 렌더 설정뿐:
  - 조명: 해(햇빛) 하나 + 균일 하늘. 원본 라이트맵은 추출본에 없어서 쓸 수 없다.
  - 용암 재질(질감 'lava')은 원본 게임에서 스스로 밝은 면이라 같은 질감을 발광으로도 쓴다(그림은 원본 질감 그대로).
  - 카메라 Game_Output_Iso: 기존 고정 아이소메트릭(직교, 고도 30°, 방위 45°, 28.284 px/m) — stage_cam.py 공용.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo05_build_stage.py <MO_GAMEFIT.blend> <MO_STAGE.blend>
"""
import json, math, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
CFG = json.load(open(os.path.join(HERE, os.environ.get("MO_CONFIG", "mo_stage_config.json")), encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=SRC)
D = bpy.data
sc = D.scenes["MO_GAMEFIT"]; sc.name = "MO_STAGE"
bpy.context.window.scene = sc if bpy.context.window else None
# 용암: 같은 질감을 발광으로도
for ma in D.materials:
    if not ma.use_nodes:
        continue
    imgs = [n for n in ma.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and "lava" in n.image.name.lower()]
    if not imgs:
        continue
    nt = ma.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(imgs[0].outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.0
    print("lava emission:", ma.name, imgs[0].image.name)
# 조명
for o in [o for o in sc.objects if o.type == 'LIGHT']:
    D.objects.remove(o)
ld = D.lights.new("Stage_Sun", 'SUN'); ld.energy = 3.0; ld.angle = math.radians(8)
so = D.objects.new("Stage_Sun", ld); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(-30))
w = D.worlds.new("Stage_World"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.60, 0.60, 1); bg.inputs[1].default_value = 0.85
# 카메라
cd = D.cameras.new("Game_Output_Iso"); cd.type = 'ORTHO'; cd.clip_start = 1; cd.clip_end = 2000; cd.sensor_fit = 'HORIZONTAL'
cam = D.objects.new("Game_Output_Iso", cd); sc.collection.objects.link(cam); cam.rotation_euler = (math.radians(60), 0, math.radians(-45)); sc.camera = cam
cam["note"] = "게임 투영과 동일: 직교, 고도 30°, 방위 45°. 화면 x = (gx−gy)·20, y = (gx+gy)·10 − z·24.49. 게임 좌표 gx = OX − Y, gy = OY − X"
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.render.film_transparent = False
sc["stage_config"] = json.dumps(CFG, ensure_ascii=False)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
