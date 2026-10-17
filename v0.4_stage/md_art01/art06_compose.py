"""MO-10 게임 카메라 합성 — 게임이 그리는 순서(배경 → 깊이 정렬 조각)로 stage.json의 데이터를 합쳐 '우리 카메라에서의 착륙장 전체 화면'을 만든다(유닛 없음).
또 충돌 마스크(걷는 칸)·시작점·출구·전투 자리를 같은 화면 좌표 위에 겹친 판도 만든다. PIL·numpy만 쓴다.
실행: python3 v0.4_stage/md_orig/mo10_compose.py <out 폴더(게임 데이터)> <출력 폴더>
"""
import json, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
D, OUTD = sys.argv[1], sys.argv[2]
st = json.load(open(os.path.join(D, "stage.json"), encoding="utf-8"))
bd = st["backdrop"]; bg = Image.open(os.path.join(D, bd["hd"])).convert("RGBA"); spr = Image.open(os.path.join(D, st["sprites"]["hd"])).convert("RGBA")
full = bg.copy()
for p in sorted(st["props"], key=lambda p: p["x"] + p["y"] + 0.35 * min(p["rect"])):      # 게임: 멀리(x+y 작은 것)부터
    h = p["hd"]; tile = spr.crop((h["sx"], h["sy"], h["sx"] + h["w"], h["sy"] + h["h"]))
    sx, sy = (p["x"] - p["y"]) * 20, (p["x"] + p["y"]) * 10
    dx = int(round((sx - h["ox"] / 2 - bd["x"]) * 2)); dy = int(round((sy - h["oy"] / 2 - bd["y"]) * 2))
    full.alpha_composite(tile, (dx, dy)) if dx >= 0 and dy >= 0 else full.paste(tile, (dx, dy), tile)
os.makedirs(OUTD, exist_ok=True)
full.convert("RGB").save(os.path.join(OUTD, "C1_game_camera_full.png"))
bg.convert("RGB").save(os.path.join(OUTD, "C0_backdrop_only.png"))
# 걷는 칸 겹침
C = st["collision"]; m = np.array(Image.open(os.path.join(D, C["file"])).convert("L")); cell = C["cell"]
ov = Image.new("RGBA", full.size, (0, 0, 0, 0)); px = ov.load()
G = st["offset"]
def scr(gx, gy): return ((gx - gy) * 20 - bd["x"]) * 2, ((gx + gy) * 10 - bd["y"]) * 2          # 바닥(z=0) → 이미지 픽셀(2배)
d = ImageDraw.Draw(ov)
rows, cols = m.shape
for j in range(0, rows):
    for i in range(0, cols):
        if m[j, i] > 127:
            gx, gy = C["gx0"] + (i + 0.5) * cell, C["gy0"] + (j + 0.5) * cell
            x, y = scr(gx, gy)
            d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=(60, 235, 90, 70))
fp = next((f for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc") if os.path.exists(f)), None)
ft = ImageFont.truetype(fp, 34) if fp else ImageFont.load_default()
def mark(gxy, col, txt, r=18):
    x, y = scr(*gxy); d.ellipse((x - r, y - r / 2, x + r, y + r / 2), outline=col, width=5); d.text((x + r + 6, y - 22), txt, fill=col, font=ft, stroke_width=3, stroke_fill=(0, 0, 0, 255))
mark(st["spawn"], (255, 255, 0, 255), "시작점")
e = st["exit"]; pts = [scr(e["x0"], e["y0"]), scr(e["x1"], e["y0"]), scr(e["x1"], e["y1"]), scr(e["x0"], e["y1"])]; d.line(pts + [pts[0]], fill=(255, 90, 200, 255), width=6)
d.text((pts[0][0] - 30, pts[0][1] - 60), "출구", fill=(255, 90, 200, 255), font=ft, stroke_width=3, stroke_fill=(0, 0, 0, 255))
cb = st["combat"]; mark(cb["anakinStart"], (120, 200, 255, 255), "전투 자리: 아나킨", 14); mark(cb["opponentStart"], (255, 140, 100, 255), "상대", 14)
Image.alpha_composite(full, ov).convert("RGB").save(os.path.join(OUTD, "C2_game_camera_walk_overlay.png"))
print("OK", full.size, len(st["props"]))
