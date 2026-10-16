"""내보낸 스테이지 데이터 확인: 배경 + 가림 조각을 게임과 같은 규칙(ox/oy, 깊이 순)으로 합성하고, 충돌 마스크·출구·전투 자리를 겹쳐 그린다.
실행: python3 v0.4_stage/compose_check.py → renders/final_iso_hd.png, renders/final_iso_sd.png, renders/collision_overlay.png"""
import json, os
from PIL import Image, ImageDraw
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(HERE, "out", "mustafar_landing"); R = os.path.join(HERE, "renders"); os.makedirs(R, exist_ok=True)
d = json.load(open(os.path.join(S, "stage.json"), encoding="utf-8")); B = d["backdrop"]
scr = lambda gx, gy: ((gx - gy) * 20.0, (gx + gy) * 10.0)
for mode, k in (("hd", 2), ("sd", 1)):
    bg = Image.open(os.path.join(S, B[mode])).convert("RGBA"); atl = Image.open(os.path.join(S, d["sprites"][mode])).convert("RGBA")
    for p in sorted(d["props"], key=lambda p: p["x"] + p["y"] + 0.35 * min(p["rect"])):
        f = p[mode]; sx, sy = scr(p["x"], p["y"])
        x, y = int(round((sx - B["x"]) * k - f["ox"])), int(round((sy - B["y"]) * k - f["oy"]))
        bg.alpha_composite(atl.crop((f["sx"], f["sy"], f["sx"] + f["w"], f["sy"] + f["h"])), (x, y))
    bg.convert("RGB").save(os.path.join(R, f"final_iso_{mode}.png"))
bg = Image.open(os.path.join(R, "final_iso_sd.png")).convert("RGBA"); ov = Image.new("RGBA", bg.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
C = d["collision"]; m = np.asarray(Image.open(os.path.join(S, C["file"])))
for j in range(C["rows"]):
    for i in range(C["cols"]):
        gx, gy = C["gx0"] + i * C["cell"], C["gy0"] + j * C["cell"]
        pts = [scr(gx, gy), scr(gx + C["cell"], gy), scr(gx + C["cell"], gy + C["cell"]), scr(gx, gy + C["cell"])]
        pts = [(x - B["x"], y - B["y"]) for x, y in pts]
        dr.polygon(pts, fill=(60, 255, 90, 70) if m[j, i] else (255, 40, 40, 60))
E = d["exit"]; dr.polygon([(x - B["x"], y - B["y"]) for x, y in (scr(E["x0"], E["y0"]), scr(E["x1"], E["y0"]), scr(E["x1"], E["y1"]), scr(E["x0"], E["y1"]))], outline=(80, 200, 255, 255), width=2)
A = d["combat"]["area"]; dr.polygon([(x - B["x"], y - B["y"]) for x, y in (scr(*q) for q in A)], outline=(255, 220, 60, 255), width=2)
for key, col in (("anakinStart", (80, 160, 255, 255)), ("opponentStart", (255, 80, 80, 255))):
    x, y = scr(*d["combat"][key]); dr.ellipse((x - B["x"] - 6, y - B["y"] - 3, x - B["x"] + 6, y - B["y"] + 3), fill=col)
x, y = scr(*d["spawn"]); dr.ellipse((x - B["x"] - 7, y - B["y"] - 4, x - B["x"] + 7, y - B["y"] + 4), fill=(255, 255, 255, 255))
Image.alpha_composite(bg, ov).convert("RGB").save(os.path.join(R, "collision_overlay.png"))
print("ok")
