"""검수용 아이소 화면: 게임 출력과 같은 배치이되 게임용 색 보정·가장자리 어둡게·SD 색 단계를 빼고 Blender 원본 밝기로 합성한다.
게임 데이터(out/)는 건드리지 않는다. 원본 렌더(work_export/<배치>/)가 있어야 한다(export_stage.py가 만든다).
실행(저장소 루트): python3 v0.4_stage/review_view.py → renders/review_iso.png (긴 변 1536 px, 판·시설 전체가 보이게 자름)"""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(HERE, "out", "mustafar_landing"); R = os.path.join(HERE, "renders")
d = json.load(open(os.path.join(S, "stage.json"), encoding="utf-8")); B = d["backdrop"]
RAW = os.path.join(HERE, "work_export", d["layout"])
scr = lambda gx, gy: ((gx - gy) * 20.0, (gx + gy) * 10.0)
k = 2   # 원본 렌더는 2배 크기, 조각 위치는 hd 값을 그대로 쓴다(hd = 2배 원본에 색 보정만 한 것)
bg = Image.open(os.path.join(RAW, "ground_2x.png")).convert("RGBA")
for p in sorted(d["props"], key=lambda p: p["x"] + p["y"] + 0.35 * min(p["rect"])):
    f = p["hd"]; sx, sy = scr(p["x"], p["y"])
    im = Image.open(os.path.join(RAW, f"spr_{p['id']}_2x.png")).convert("RGBA")
    assert im.size == (f["w"], f["h"]), p["id"]
    bg.alpha_composite(im, (int(round((sx - B["x"]) * k - f["ox"])), int(round((sy - B["y"]) * k - f["oy"]))))
# 판·시설 전체가 들어오게 자른다(가로 84 %, 3:2, 가운데를 판·시설 쪽으로 약간 옮김)
W, H = bg.size; cw = int(W * 0.84); ch = int(cw * 2 / 3); cx, cy = int(W * 0.51), int(H * 0.47)
im = bg.crop((cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)).convert("RGB")
im.thumbnail((1536, 1536), Image.LANCZOS)
im.save(os.path.join(R, "review_iso.png"), optimize=True)
print("ok", d["layout"], im.size)
