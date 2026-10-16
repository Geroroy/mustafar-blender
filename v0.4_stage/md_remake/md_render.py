"""Movie Duels 원본·리메이크 검사 렌더 공용(bpy). 렌더 뒤 PIL로 원본 파일명·장면·컬렉션·객체 수·카메라를 이미지에 적는다.
render_view(scene, out_png, label_lines, center, extent, view, ...)
  view: 'top' | ('az', 방위°, 고도°) — 직교. 방위 0° = +Y 쪽에서 −Y를 봄(카메라가 +Y에 있음) 아님 → 카메라 위치 방향(XY 평면의 각, +X에서 반시계)
"""
import math, os

import bpy
from mathutils import Euler, Vector


def ensure_light(scene, sun_rot=(math.radians(40), 0, math.radians(30)), sun=3.0, amb=0.5):
    D = bpy.data
    for o in [o for o in scene.objects if o.name.startswith("CHK_")]:
        D.objects.remove(o)
    ld = D.lights.new("CHK_Sun", 'SUN'); ld.energy = sun; ld.angle = math.radians(8)
    so = D.objects.new("CHK_Sun", ld); scene.collection.objects.link(so); so.rotation_euler = sun_rot
    w = scene.world or D.worlds.new("CHK_World"); scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.57, 0.62, 1); w.node_tree.nodes["Background"].inputs[1].default_value = amb


def camera(scene, center, extent, view, aspect=4 / 3, dist=20000.0):
    D = bpy.data
    cd = D.cameras.new("CHK_Cam"); cd.type = 'ORTHO'; cd.clip_start = 1; cd.clip_end = dist * 3
    cam = D.objects.new("CHK_Cam", cd); scene.collection.objects.link(cam)
    c = Vector(center)
    if view == 'top' or (isinstance(view, tuple) and view[0] == 'top'):
        roll = view[1] if isinstance(view, tuple) else 0.0          # ('top', 180): 회전한 사본을 원본과 같은 방향으로 보기
        cam.rotation_euler = (0, 0, math.radians(roll)); cam.location = c + Vector((0, 0, dist))
    else:
        _, az, el = view
        d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)), math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
        cam.location = c + d * dist
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cd.ortho_scale = extent; cd.sensor_fit = 'HORIZONTAL'
    scene.camera = cam
    return cam


def render(scene, out_png, res=(1280, 960), samples=24):
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = samples; scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = res[0], res[1], 100
    scene.view_settings.view_transform = 'Standard'; scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'; scene.render.filepath = out_png
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    bpy.ops.render.render(write_still=True, scene=scene.name)


def label(png, lines, boxes=None, font_size=18):
    """이미지 위·아래 띠에 글씨. boxes: [(x0,y0,x1,y1,text,color)] 화면 좌표 표시."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(png).convert("RGB")
    fp = None
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            fp = f; break
    ft = ImageFont.truetype(fp, font_size) if fp else ImageFont.load_default()
    ft2 = ImageFont.truetype(fp, font_size - 2) if fp else ft
    pad = 6; lh = font_size + 6
    band = Image.new("RGB", (im.width, pad * 2 + lh * len(lines)), (14, 16, 20))
    dr = ImageDraw.Draw(band)
    for k, t in enumerate(lines):
        dr.text((10, pad + k * lh), t, fill=(235, 235, 235) if k == 0 else (190, 200, 210), font=ft if k == 0 else ft2)
    if boxes:
        d2 = ImageDraw.Draw(im)
        for x0, y0, x1, y1, t, col in boxes:
            d2.rectangle((x0, y0, x1, y1), outline=col, width=3)
            tb = d2.textbbox((x0 + 4, y0 + 4), t, font=ft2); d2.rectangle(tb, fill=(0, 0, 0)); d2.text((x0 + 4, y0 + 4), t, fill=col, font=ft2)
    out = Image.new("RGB", (im.width, im.height + band.height)); out.paste(band, (0, 0)); out.paste(im, (0, band.height))
    out.save(png)


def world_to_px(scene, cam, p):
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(scene, cam, Vector(p))
    return v.x * scene.render.resolution_x, (1 - v.y) * scene.render.resolution_y
