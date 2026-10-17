"""ART01-5 포장 — mo07_pack.py 사본(설정 파일 art_stage_config.json, 그리고 띠 경계 이음선 보정 한 단계 추가 — 아래 "띠 경계 이음선 보정"). art04가 렌더한 2배 이미지에서 게임 데이터를 만든다(Blender 장면 불필요; .venv-bpy 파이썬으로 실행: mathutils·PIL·numpy).
  ground_hd.webp(2배) / ground_sd.png(1배, 게임 베이커와 같은 색 보정·포스터라이즈·베이어) / sprites_hd.png·sprites_sd.png / stage.json
  (collision.png는 mo06이 만든 것을 그대로 쓴다)
실행: .venv-bpy/bin/python v0.4_stage/md_art01/art05_pack.py
"""
import json, math, os, sys

import bpy  # noqa: F401  (mathutils를 쓰려면 bpy를 먼저 불러야 한다)

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "art_stage_config.json"), encoding="utf-8"))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", CFG["out_dir"])); TMP = os.path.join(OUT, "_tmp")
meta = json.load(open(os.path.join(TMP, "sprites_meta.json")))
LAYER = meta.pop("_props_layer", None)
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


# ---- 띠 경계 이음선 보정(ART01 추가): 조각을 띠마다 따로 렌더하면 잘린 경계 픽셀(반쯤 덮임)의 알파·색이 띠마다 달라
# 게임에서 겹쳐 그릴 때 배경이 비치거나 디노이즈 잡음 색이 드러나 어두운 점선이 생긴다(우주선 선체).
# 보정: art04 --props-layer가 만든 '조각 전체 한 번 렌더'(같은 장면·조명·샘플)와 조각 번호 화면을 쓴다.
#   - 띠 b가 맨 앞인 픽셀(번호 = b): 색·알파를 한 번 렌더 값으로 → 보이는 모든 픽셀이 한 장의 렌더와 같아진다.
#   - 이웃 띠(b±1)가 맨 앞이고 띠 b가 반쯤 덮는 픽셀(잘린 경계): 색은 한 번 렌더 값, 알파는 둘 중 큰 값 → 이음매가 닫힌다.
#   - 다른 띠에 가려 안 보이는 띠 b의 부분은 띠 b 자신의 렌더 그대로(게임이 앞 조각을 반투명으로 그릴 때 비치는 부분).
# 한 번 렌더가 없으면(옛 내보내기) 두 띠 알파 합·색 섞기로 대신한다.
raw = {i: np.asarray(Image.open(os.path.join(TMP, f"spr_{i}_2x.png")).convert("RGBA")).copy() for i in ids}
org = {i: (int(round(meta[i]["crop"][0] * 2)), int(round(meta[i]["crop"][1] * 2))) for i in ids}
alpha0 = {i: raw[i][..., 3].astype(np.int32) for i in ids}
rgb0 = {i: raw[i][..., :3].astype(np.float32) for i in ids}
seam_px = 0
if LAYER:
    lay = np.asarray(Image.open(os.path.join(TMP, "props_layer_2x.png")).convert("RGBA"))
    lid_im = np.asarray(Image.open(os.path.join(TMP, "props_layer_id_2x.png")).convert("RGBA"))
    lid = np.where(lid_im[..., 3] > 127, lid_im[..., 0].astype(np.int32), 0)
    lx, ly = int(round(LAYER["crop"][0] * 2)), int(round(LAYER["crop"][1] * 2))
    own_total = 0
    for i in ids:
        bi = int(i.split("_")[1]) + 1
        ax, ay = org[i]; A = alpha0[i]; h_, w_ = A.shape
        x0, y0 = max(ax, lx), max(ay, ly); x1, y1 = min(ax + w_, lx + lay.shape[1]), min(ay + h_, ly + lay.shape[0])
        L = lay[y0 - ly:y1 - ly, x0 - lx:x1 - lx]; I = lid[y0 - ly:y1 - ly, x0 - lx:x1 - lx]; a = A[y0 - ay:y1 - ay, x0 - ax:x1 - ax]
        La = L[..., 3].astype(np.int32)
        own = (I == bi) & (La > 0)
        nb = ((I == bi - 1) | (I == bi + 1)) & (a > 0) & (a < 255) & (La > 0)
        reg = raw[i][y0 - ay:y1 - ay, x0 - ax:x1 - ax]
        m = own | nb
        reg[..., :3] = np.where(m[..., None], L[..., :3], reg[..., :3])
        reg[..., 3] = np.where(own, La, np.where(nb, np.maximum(a, La), reg[..., 3])).astype(np.uint8)
        seam_px += int(nb.sum()); own_total += int(own.sum())
    print("한 번 렌더로 맞춘 보이는 픽셀(2배)", own_total)
    # 바깥 윤곽·배경/조각 분할 경계: 게임 합성 예측(조각 알파 × 조각색 + 나머지 × 배경 그림)이 전체 장면 한 번 렌더와 다르면
    # (배경 그림의 그 자리에 조각 형상이 빠져 검은 구멍·다른 면이 있는 경우) 그 픽셀만 전체 장면 색·불투명으로 맞춘다.
    fpath = os.path.join(TMP, "full_layer_2x.png")
    if os.path.exists(fpath):
        F = np.asarray(Image.open(fpath).convert("RGB")).astype(np.float32)
        GR = np.asarray(Image.open(os.path.join(TMP, "ground_2x.png")).convert("RGB")).astype(np.float32)
        fr0 = SC.frame(CFG); gx0_, gy0_ = int(fr0[0] * 2), int(fr0[1] * 2)
        fringe = 0
        for i in ids:
            bi = int(i.split("_")[1]) + 1
            ax, ay = org[i]; h_, w_ = raw[i].shape[:2]
            x0, y0 = max(ax, lx, gx0_), max(ay, ly, gy0_); x1, y1 = min(ax + w_, lx + F.shape[1], gx0_ + GR.shape[1]), min(ay + h_, ly + F.shape[0], gy0_ + GR.shape[0])
            reg = raw[i][y0 - ay:y1 - ay, x0 - ax:x1 - ax]
            a = reg[..., 3].astype(np.float32)[..., None] / 255.0
            pred = a * reg[..., :3] + (1 - a) * GR[y0 - gy0_:y1 - gy0_, x0 - gx0_:x1 - gx0_]
            f = F[y0 - ly:y1 - ly, x0 - lx:x1 - lx]; I = lid[y0 - ly:y1 - ly, x0 - lx:x1 - lx]
            cand = (reg[..., 3] > 0) & (reg[..., 3] < 255) & ((I == bi) | (I == 0)) & (np.abs(pred - f).mean(-1) > 8.0)
            reg[..., :3] = np.where(cand[..., None], np.clip(np.round(f), 0, 255), reg[..., :3]).astype(np.uint8)
            reg[..., 3] = np.where(cand, 255, reg[..., 3]).astype(np.uint8)
            fringe += int(cand.sum())
        print("윤곽·분할 경계 맞춘 픽셀(2배)", fringe)
else:
    for k, i in enumerate(ids):
        for n in ids[max(0, k - 1):k] + ids[k + 1:k + 2]:
            (ax, ay), (bx, by) = org[i], org[n]
            A, B = alpha0[i], alpha0[n]
            x0, y0 = max(ax, bx), max(ay, by); x1, y1 = min(ax + A.shape[1], bx + B.shape[1]), min(ay + A.shape[0], by + B.shape[0])
            if x0 >= x1 or y0 >= y1:
                continue
            a = A[y0 - ay:y1 - ay, x0 - ax:x1 - ax]; b = B[y0 - by:y1 - by, x0 - bx:x1 - bx]
            both = (a > 0) & (b > 0) & (a < 255)
            if not both.any():
                continue
            ca = rgb0[i][y0 - ay:y1 - ay, x0 - ax:x1 - ax]; cb = rgb0[n][y0 - by:y1 - by, x0 - bx:x1 - bx]
            w = (a + b).astype(np.float32)[..., None]
            mix = (ca * a[..., None] + cb * b[..., None]) / np.maximum(w, 1)
            reg = raw[i][y0 - ay:y1 - ay, x0 - ax:x1 - ax]
            reg[..., :3] = np.where(both[..., None], np.clip(np.round(mix), 0, 255), reg[..., :3]).astype(np.uint8)
            reg[..., 3] = np.where(both, np.maximum(reg[..., 3], np.minimum(255, a + b)), reg[..., 3]).astype(np.uint8)
            seam_px += int(both.sum())
print("띠 경계 보정 픽셀(2배)", seam_px)

hd_imgs, sd_imgs, keep = [], [], []
for i in ids:
    im2 = Image.fromarray(raw[i], "RGBA")
    bb = im2.split()[3].getbbox()
    if bb is None:
        print("빈 조각 건너뜀", i); continue
    x0, y0, x1, y1 = bb[0] // 2 * 2, bb[1] // 2 * 2, -(-bb[2] // 2) * 2, -(-bb[3] // 2) * 2      # 투명 여백을 잘라 낸다(짝수 픽셀 경계 — 1배 축소와 맞춤)
    im2 = im2.crop((x0, y0, x1, y1)); c0x, c0y, cw, chh = meta[i]["crop"]; meta[i]["crop"] = (c0x + x0 / 2, c0y + y0 / 2, (x1 - x0) // 2, (y1 - y0) // 2)
    keep.append(i); hd_imgs.append(to_hd(im2)); sd_imgs.append(to_sd(im2))
atl_hd, pos_hd = pack(hd_imgs, 8192); atl_sd, pos_sd = pack(sd_imgs, 4096)
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
