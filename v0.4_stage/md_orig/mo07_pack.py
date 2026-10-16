"""MO-7 포장 — mo06이 렌더한 2배 이미지에서 게임 데이터를 만든다(Blender 장면 불필요; .venv-bpy 파이썬으로 실행: mathutils·PIL·numpy).
  ground_hd.webp(2배) / ground_sd.png(1배, 게임 베이커와 같은 색 보정·포스터라이즈·베이어) / sprites_hd.png·sprites_sd.png / stage.json
  (collision.png는 mo06이 만든 것을 그대로 쓴다)
실행: .venv-bpy/bin/python v0.4_stage/md_orig/mo07_pack.py
"""
import json, math, os, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "mo_stage_config.json"), encoding="utf-8"))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", CFG["out_dir"])); TMP = os.path.join(OUT, "_tmp")
meta = json.load(open(os.path.join(TMP, "sprites_meta.json")))
ids = sorted(meta)
BAYER = (np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4) / 16.0 - 0.5)


def grade(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    l = r * 0.3 + g * 0.59 + b * 0.11; k = 0.8
    c = lambda v: np.clip(128 + (v - 128) * 1.14, 0, 255)
    return np.stack([c((l + (r - l) * k) * 1.03), c(l + (g - l) * k), c((l + (b - l) * k) * 0.95)], -1)


def glow_mask(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    return (mn >= 185) & (mx >= 250) & (mx - mn <= 80)


def to_sd(img2x):
    im = img2x.resize((img2x.width // 2, img2x.height // 2), Image.LANCZOS)
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    g = np.where(glow_mask(rgb)[..., None], rgb, grade(rgb))
    H_, W_ = al.shape; t = np.tile(BAYER, (H_ // 4 + 1, W_ // 4 + 1))[:H_, :W_] * (255 / 20)
    q = np.clip(np.round((g + t[..., None]) / (255 / 20)) * (255 / 20), 0, 255)
    return Image.fromarray(np.dstack([q, np.where(al > 127, 255, 0)]).astype(np.uint8), "RGBA")


def to_hd(img2x):
    a = np.asarray(img2x.convert("RGBA")).astype(np.float32); rgb = a[..., :3]
    g = np.where(glow_mask(rgb)[..., None], rgb, grade(rgb))
    return Image.fromarray(np.dstack([g, a[..., 3]]).astype(np.uint8), "RGBA")


FILL = (12, 6, 5)
g2 = Image.open(os.path.join(TMP, "ground_2x.png")).convert("RGBA")
hd = to_hd(g2); arr = np.asarray(hd).astype(np.float32)
yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
f = np.clip(np.minimum.reduce([xx, yy, arr.shape[1] - 1 - xx, arr.shape[0] - 1 - yy]) / 140.0, 0, 1)[..., None]
arr[..., :3] = arr[..., :3] * f + np.array(FILL) * (1 - f)
Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB").save(os.path.join(OUT, "ground_hd.webp"), quality=86, method=5)
to_sd(Image.fromarray(arr.astype(np.uint8), "RGBA")).convert("RGB").save(os.path.join(OUT, "ground_sd.png"), optimize=True)


def pack(images, maxw):
    x = y = rowh = 0; pos = []
    for im in images:
        if x + im.width > maxw:
            x, y, rowh = 0, y + rowh + 2, 0
        pos.append((x, y)); x += im.width + 2; rowh = max(rowh, im.height)
    atl = Image.new("RGBA", (maxw, y + rowh), (0, 0, 0, 0))
    for im, p in zip(images, pos):
        atl.paste(im, p)
    return atl, pos


hd_imgs, sd_imgs, keep = [], [], []
for i in ids:
    im2 = Image.open(os.path.join(TMP, f"spr_{i}_2x.png")).convert("RGBA")
    if im2.getbbox() is None or np.asarray(im2)[..., 3].max() == 0:
        print("빈 조각 건너뜀", i); continue
    keep.append(i); hd_imgs.append(to_hd(im2)); sd_imgs.append(to_sd(im2))
atl_hd, pos_hd = pack(hd_imgs, 4096); atl_sd, pos_sd = pack(sd_imgs, 2048)
atl_hd.save(os.path.join(OUT, "sprites_hd.png"), optimize=True); atl_sd.save(os.path.join(OUT, "sprites_sd.png"), optimize=True)

props = []
for i, ih, is_, ph, ps in zip(keep, hd_imgs, sd_imgs, pos_hd, pos_sd):
    Gc = meta[i]["G"]; cx = cy = Gc / 2.0
    sx, sy = (cx - cy) * SC.HALF_W, (cx + cy) * SC.HALF_H
    c0x, c0y, cw, chh = meta[i]["crop"]
    props.append({"id": i, "x": round(cx, 3), "y": round(cy, 3), "rect": [0.01, 0.01],
                  "sd": {"sx": ps[0], "sy": ps[1], "w": is_.width, "h": is_.height, "ox": round(sx - c0x, 2), "oy": round(sy - c0y, 2)},
                  "hd": {"sx": ph[0], "sy": ph[1], "w": ih.width, "h": ih.height, "ox": round((sx - c0x) * 2, 2), "oy": round((sy - c0y) * 2, 2)}})

fr = SC.frame(CFG); SX0, SY0 = fr[0], fr[1]; W1, H1 = fr[2] - fr[0], fr[3] - fr[1]
col = Image.open(os.path.join(OUT, "collision.png")); wk = CFG["walk"]; cell = wk["cell_m"]
# 충돌 격자 원점(mo06과 같은 계산)
gxa, gya = SC.to_game(CFG, wk["bounds_world"][0], wk["bounds_world"][3]), SC.to_game(CFG, wk["bounds_world"][1], wk["bounds_world"][2])
gx0, gy0 = math.floor(min(gxa[0], gya[0])), math.floor(min(gxa[1], gya[1]))
gpt = lambda xy: [round(v, 3) for v in SC.to_game(CFG, xy[0], xy[1])]
ex = CFG["exit"]; ec, eh = ex["world_center"], ex["half"]
e0 = SC.to_game(CFG, ec[0] + eh[0], ec[1] + eh[1]); e1 = SC.to_game(CFG, ec[0] - eh[0], ec[1] - eh[1])
cb = CFG["combat"]
data = {
    "version": 1, "name": "무스타파 · 착륙장", "layout": CFG["layout"],
    "note": "Movie Duels duel_mus_both 원본 형상 그대로(MO_STAGE). 좌표는 게임 타일(1 m). gx = OX − Y, gy = OY − X (Blender m)",
    "offset": CFG["game"],
    "backdrop": {"sd": "ground_sd.png", "hd": "ground_hd.webp", "x": SX0, "y": SY0, "w": W1, "h": H1, "fill": list(FILL)},
    "sprites": {"sd": "sprites_sd.png", "hd": "sprites_hd.png"},
    "props": props,
    "collision": {"file": "collision.png", "cell": cell, "gx0": gx0, "gy0": gy0, "cols": col.width, "rows": col.height},
    "spawn": gpt(CFG["start"]["world"]),
    "exit": {"x0": round(min(e0[0], e1[0]), 3), "y0": round(min(e0[1], e1[1]), 3), "x1": round(max(e0[0], e1[0]), 3), "y1": round(max(e0[1], e1[1]), 3)},
    "combat": {"area": [gpt(p) for p in cb["area_world"]], "anakinStart": gpt(cb["anakin_start_world"]), "opponentStart": gpt(cb["opponent_start_world"]),
               "trigger": {"center": gpt(cb["trigger_world"]["center"]), "radius": cb["trigger_world"]["radius"]}},
    "ambient": CFG["ambient"],
    "lights": [],
    "region": "무스타파 · 착륙장",
}
json.dump(data, open(os.path.join(OUT, "stage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OUT", OUT, "props", len(props), "backdrop", W1, H1, SX0, SY0)
