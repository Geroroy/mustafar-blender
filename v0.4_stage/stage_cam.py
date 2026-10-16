"""게임 투영 카메라·좌표 변환(빌드·내보내기 공용).
게임(Isometric-RPG src/core/iso.js): 화면 x = (gx − gy)·20, y = (gx + gy)·10 − z·24.4949 (1배, 게임 픽셀). 1 단위 = 1 m.
Blender → 게임: gx = OX − Y, gy = OY − X (게임 좌표계는 화면 기준이라 축이 뒤집힘 — 렌더 화면은 거울상이 아님).
"""
import math
from mathutils import Vector

HALF_W, HALF_H = 20.0, 10.0
PX = HALF_W / math.sqrt(0.5)          # 28.2843 px/m (카메라 가로축)
Z_PX = PX * math.cos(math.pi / 6)     # 24.4949
FWD = Vector((math.cos(math.radians(30)) * math.sqrt(0.5), math.cos(math.radians(30)) * math.sqrt(0.5), -0.5))


def to_game(cfg, X, Y):
    g = cfg["game"]; return g["OX"] - Y, g["OY"] - X


def to_world(cfg, gx, gy):
    g = cfg["game"]; return g["OY"] - gy, g["OX"] - gx


def screen(cfg, X, Y, Z=0.0):
    gx, gy = to_game(cfg, X, Y); return (gx - gy) * HALF_W, (gx + gy) * HALF_H - Z * Z_PX


def frame(cfg):
    """배경 이미지가 덮는 게임 화면 범위(1배 px): 지정한 월드 상자들의 투영 + 여백."""
    xs, ys = [], []
    for (x0, y0, z0), (x1, y1, z1) in cfg["frame_boxes"]:
        for X in (x0, x1):
            for Y in (y0, y1):
                for Z in (z0, z1):
                    sx, sy = screen(cfg, X, Y, Z); xs.append(sx); ys.append(sy)
    mx, my = cfg["frame_margin_px"]
    return math.floor(min(xs) - mx), math.floor(min(ys) - my), math.ceil(max(xs) + mx), math.ceil(max(ys) + my)


def setup(scene, cam, cfg, density=1, sub=None):
    """게임 출력 카메라를 맞춘다. sub=(sx0, sy0, sx1, sy1)이면 그 화면 범위만(자르기 렌더). 반환: 이미지 W, H, 왼쪽 위의 게임 화면 좌표(1배 px)."""
    sx0, sy0, sx1, sy1 = sub or frame(cfg)
    W, H = int(round((sx1 - sx0) * density)), int(round((sy1 - sy0) * density))
    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    gx, gy = (cx / HALF_W + cy / HALF_H) / 2, (cy / HALF_H - cx / HALF_W) / 2       # z = 0 바닥 위 점
    X, Y = to_world(cfg, gx, gy)
    cam.data.type = 'ORTHO'; cam.data.sensor_fit = 'HORIZONTAL' if W >= H else 'VERTICAL'
    cam.data.ortho_scale = max(W, H) / (PX * density)
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.rotation_euler = (math.radians(60), 0, math.radians(-45))
    cam.location = Vector((X, Y, 0.0)) - FWD * 400.0
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, H, 100
    scene.render.use_border = False; scene.render.use_crop_to_border = False
    return W, H, sx0, sy0


def obj_screen_bbox(cfg, objs, pad=6):
    """객체들(평가된 메시)의 게임 화면 상자(1배 px)."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get(); xs, ys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            p = o.matrix_world @ Vector(c); sx, sy = screen(cfg, p.x, p.y, p.z); xs.append(sx); ys.append(sy)
    return math.floor(min(xs) - pad), math.floor(min(ys) - pad), math.ceil(max(xs) + pad), math.ceil(max(ys) + pad)
