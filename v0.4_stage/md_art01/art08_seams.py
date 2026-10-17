"""ART01-8 이음선·밝기 차이·알파 테두리 검사 — 게임처럼 합성한 화면(배경 + 깊이 띠 조각, art06_compose 결과)을
같은 카메라의 '나누지 않은 한 번 렌더'(art03_region.py, 2배)와 구역마다 비교한다(PIL·numpy).
조각 분할에서 생긴 이음선·띠 사이 밝기 단차·알파 테두리는 두 그림의 차이에 선·띠로 나타난다(디노이즈 잡음은 흩어진 점으로만 나타남).
출력: 구역마다 [합성 | 한 번 렌더 | 차이×4] 판, 통계 json(평균·99분위 차이, 차이 큰 픽셀 비율, 띠 경계 근처와 나머지의 차이 비교).
실행: python3 v0.4_stage/md_art01/art08_seams.py <게임 데이터 폴더> <합성 C1 png> <한 번 렌더 폴더(보정 전, 스크립트가 같은 보정을 건다)> <출력 폴더>
"""
import json, math, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 22) if os.path.exists("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc") else ImageFont.load_default()
HERE = os.path.dirname(os.path.abspath(__file__))
DATA, COMP, REF, OUTD = sys.argv[1:5]
os.makedirs(OUTD, exist_ok=True)
st = json.load(open(os.path.join(DATA, "stage.json"), encoding="utf-8")); bd = st["backdrop"]
cfg = json.load(open(os.path.join(HERE, "art_stage_config.json"), encoding="utf-8")); g = cfg["game"]
REG = json.load(open(os.path.join(HERE, "art_regions.json"), encoding="utf-8"))["regions"]
comp = Image.open(COMP).convert("RGB")


def grade_like_pack(a):
    """art05_pack.py(= mo07)의 to_hd와 같은 색 보정을 한 번 렌더에도 건다(합성은 이미 보정됨). 밝은 발광 픽셀은 보정 제외."""
    r, g_, b = a[..., 0], a[..., 1], a[..., 2]
    l = r * 0.3 + g_ * 0.59 + b * 0.11; k = 0.8
    c = lambda v: np.clip(128 + (v - 128) * 1.14, 0, 255)
    gr = np.stack([c((l + (r - l) * k) * 1.03), c(l + (g_ - l) * k), c((l + (b - l) * k) * 0.95)], -1)
    mx, mn = a.max(-1), a.min(-1); glow = (mn >= 185) & (mx >= 250) & (mx - mn <= 80)
    return np.where(glow[..., None], a, gr).astype(np.uint8)
# 조각 화면 영역(알파>0)과 그 테두리(조각 경계·띠 경계) 마스크(2배 합성 좌표)
spr = Image.open(os.path.join(DATA, st["sprites"]["hd"])).convert("RGBA")
alpha = np.zeros((comp.height, comp.width), np.uint8); bandid = np.zeros((comp.height, comp.width), np.int16)
for k, p in enumerate(sorted(st["props"], key=lambda p: p["x"] + p["y"])):
    h = p["hd"]; a = np.asarray(spr.crop((h["sx"], h["sy"], h["sx"] + h["w"], h["sy"] + h["h"])))[..., 3]
    sx, sy = (p["x"] - p["y"]) * 20, (p["x"] + p["y"]) * 10
    dx = int(round((sx - h["ox"] / 2 - bd["x"]) * 2)); dy = int(round((sy - h["oy"] / 2 - bd["y"]) * 2))
    y0, x0 = max(dy, 0), max(dx, 0); y1, x1 = min(dy + a.shape[0], comp.height), min(dx + a.shape[1], comp.width)
    sub = a[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], sub)
    bandid[y0:y1, x0:x1][sub > 127] = k + 1
edge = np.zeros_like(alpha, bool)
for s in ((0, 1), (1, 0)):
    edge |= (np.roll(bandid, s, (0, 1)) != bandid) & ((bandid > 0) | (np.roll(bandid, s, (0, 1)) > 0))
semi = (alpha > 0) & (alpha < 255)
k3 = edge.copy()
for s in ((0, 1), (1, 0), (0, -1), (-1, 0)):
    k3 |= np.roll(edge, s, (0, 1))
stats = {}
for name, r in REG.items():
    rp = os.path.join(REF, f"{name}.png")
    if not os.path.exists(rp):
        continue
    gx, gy = g["OX"] - r["world"][1], g["OY"] - r["world"][0]
    sx, sy = (gx - gy) * 20, (gx + gy) * 10; w, h = r["size_px"]
    bx0, by0 = round(sx - w / 2), round(sy - h / 2)
    X0, Y0 = int((bx0 - bd["x"]) * 2), int((by0 - bd["y"]) * 2)
    ref = Image.fromarray(grade_like_pack(np.asarray(Image.open(rp).convert("RGB")).astype(np.float32))); W2, H2 = ref.size
    c = comp.crop((X0, Y0, X0 + W2, Y0 + H2))
    A = np.asarray(c).astype(np.float32); B = np.asarray(ref).astype(np.float32)
    d = np.abs(A - B).mean(-1)
    e = k3[Y0:Y0 + H2, X0:X0 + W2]; sm = semi[Y0:Y0 + H2, X0:X0 + W2]; ins = (alpha[Y0:Y0 + H2, X0:X0 + W2] > 0)
    stats[name] = {
        "mean_abs_diff": round(float(d.mean()), 2), "p99_abs_diff": round(float(np.percentile(d, 99)), 1),
        "frac_px_diff_gt_24": round(float((d > 24).mean()), 4),
        "band_edge_px": int(e.sum()), "mean_diff_on_band_edges(±1px)": round(float(d[e].mean()), 2) if e.any() else None,
        "mean_diff_inside_sprites": round(float(d[ins & ~e].mean()), 2) if (ins & ~e).any() else None,
        "mean_diff_backdrop_only": round(float(d[~ins].mean()), 2) if (~ins).any() else None,
        "semi_alpha_px": int(sm.sum()), "mean_diff_on_semi_alpha": round(float(d[sm].mean()), 2) if sm.any() else None,
    }
    dv = Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).convert("RGB")
    board = Image.new("RGB", (W2 * 3 + 20, H2 + 40), (16, 16, 18)); board.paste(c, (0, 40)); board.paste(ref, (W2 + 10, 40)); board.paste(dv, (2 * W2 + 20, 40))
    ImageDraw.Draw(board).text((8, 10), f"{name}: 게임 합성(배경+조각) | 나누지 않은 한 번 렌더 | 차이 x4  — 평균 {stats[name]['mean_abs_diff']}, 띠 경계 {stats[name]['mean_diff_on_band_edges(±1px)']}, 조각 안 {stats[name]['mean_diff_inside_sprites']}", fill=(230, 230, 230), font=FT)
    board.save(os.path.join(OUTD, f"seam_{name}.png"))
json.dump(stats, open(os.path.join(OUTD, "seams.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False, indent=1))
