"""MO-8 사용 영역 표시 — 게임 맞춤 좌표(MO_STAGE)의 상면 렌더에 걷는 칸·시작점·출구·게임 화면 범위를 겹쳐 그린다. Blender(bpy) + PIL.
원본 전체 렌더(O_*)와 게임 화면 사이를 잇는 그림: 원본의 어느 부분을 게임에 쓰는지 보인다.
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo08_region_view.py <MO_STAGE.blend> <collision.png> <stage.json> <출력 png> [--samples 24]
"""
import json, math, os, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import mo_render as R  # noqa: E402
import stage_cam as SC  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

BLEND, COL, STAGE, OUT = (os.path.abspath(p) for p in sys.argv[1:5])
SAMPLES = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 24
bpy.ops.wm.open_mainfile(filepath=BLEND)
D = bpy.data; sc = D.scenes["MO_STAGE"]; CFG = json.loads(sc["stage_config"]); ST = json.load(open(STAGE, encoding="utf-8"))
R.ensure_light(sc, sun_rot=(math.radians(50), 0, math.radians(-30)), sun=2.5, amb=0.9)
CEN = (0.0, -8.0, 0.0); EXT = 80.0; RES = (1600, 1200)
cam = R.camera(sc, CEN, EXT, 'top', dist=500.0)
R.render(sc, OUT, RES, samples=SAMPLES)
# 월드(X,Y) → 이미지 픽셀(위가 +Y, 오른쪽이 +X)
mpp = EXT / RES[0]
px = lambda X, Y: ((X - CEN[0]) / mpp + RES[0] / 2, RES[1] / 2 - (Y - CEN[1]) / mpp)
im = Image.open(OUT).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
C = ST["collision"]; m = Image.open(COL).convert("L"); cell = C["cell"]
mk = Image.new("RGBA", m.size, (0, 0, 0, 0)); a = m.point(lambda v: 110 if v > 127 else 0)
mk.paste(Image.new("RGBA", m.size, (60, 230, 90, 255)), (0, 0), a)
# 게임 격자 → 월드: X = OY − gy, Y = OX − gx
G = ST["offset"]
pts = {}
for (i, j) in ((0, 0), (C["cols"], C["rows"])):
    gx, gy = C["gx0"] + i * cell, C["gy0"] + j * cell; pts[(i, j)] = (G["OY"] - gy, G["OX"] - gx)
(Xa, Ya), (Xb, Yb) = pts[(0, 0)], pts[(C["cols"], C["rows"])]          # i↑ → Y↓, j↑ → X↓
xa, ya = px(Xa, Ya); xb, yb = px(Xb, Yb)
# 마스크 이미지: 행 j ↔ X (감소), 열 i ↔ Y (감소). 월드 상면 이미지 (x=X, y=−Y)에 맞게 전치·뒤집기
mt = mk.transpose(Image.TRANSPOSE)                                  # 이제 가로 = j(X 감소), 세로 = i(Y 감소)
mt = mt.transpose(Image.FLIP_LEFT_RIGHT)                            # 가로 = X 증가
w_px = int(round(abs(xb - xa))); h_px = int(round(abs(yb - ya)))
mt = mt.resize((w_px, h_px), Image.NEAREST)
ov.paste(mt, (int(round(min(xa, xb))), int(round(min(ya, yb)))), mt)
def spot(X, Y, col, txt):
    x, y = px(X, Y); d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=col, width=4); d.text((x + 12, y - 8), txt, fill=col)
spot(*CFG["start"]["world"], (255, 255, 0, 255), "시작점(원본 info_player_start)")
e = CFG["exit"]; (cx, cy), (hx, hy) = e["world_center"], e["half"]
x0, y0 = px(cx - hx, cy + hy); x1, y1 = px(cx + hx, cy - hy); d.rectangle((x0, y0, x1, y1), outline=(255, 90, 200, 255), width=4); d.text((x0, y0 - 16), "출구(입구 계단 위)", fill=(255, 90, 200, 255))
# 게임 화면 범위(배경 이미지가 덮는 곳)
fr = SC.frame(CFG); corners = []
for sx, sy in ((fr[0], fr[1]), (fr[2], fr[1]), (fr[2], fr[3]), (fr[0], fr[3])):
    gx, gy = (sx / SC.HALF_W + sy / SC.HALF_H) / 2, (sy / SC.HALF_H - sx / SC.HALF_W) / 2          # z = 0 평면
    X, Y = SC.to_world(CFG, gx, gy); corners.append(px(X, Y))
d.polygon(corners, outline=(255, 160, 40, 255)); d.text((corners[0][0] + 6, corners[0][1] + 6), "게임 배경 이미지 범위(z=0 투영)", fill=(255, 160, 40, 255))
im = Image.alpha_composite(im, ov).convert("RGB"); im.save(OUT)
R.label(OUT, ["수정 전 원본 duel_mus_both.obj — 게임 맞춤 좌표(MO_FIT: 회전 270°·축척 0.028125 m/u·이동만) 상면. 초록 = 걷는 칸(원본 형상에서 계산)", "노랑 = 시작점(원본 엔티티), 분홍 = 출구, 주황 = 게임 배경 범위. 회색/흰색 면 = 추출본에 질감 없음(원본 색 아님)"])
print("OK", OUT)
