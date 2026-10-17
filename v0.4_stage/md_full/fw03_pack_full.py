"""FULL-3 포장 — fw02가 렌더한 배경·조각 층·번호 화면에서 게임 데이터를 만든다(PIL·numpy; .venv-bpy 파이썬으로 실행).
  ground_hd.webp(1.25배) / ground_sd.png(1배): mo07과 같은 색 보정(SD는 포스터라이즈·베이어).
  조각: 번호 화면으로 층을 나눈다(한 장에서 나누므로 띠 이음선이 없다).
    - 가림 띠 b: layer_occ에서 번호가 b인 픽셀. 그중 layer_all에서 지붕에 덮이는 픽셀은 따로 'inside' 조각(실내에 있을 때만 보임).
    - 지붕 띠 r: layer_all에서 번호가 r인 픽셀 → 'roof' 조각(실내에 있으면 숨김).
  heights.png·collision.png는 fw02 결과 그대로. stage.json: 높이 지도, 출구 없음, 목표 문구.
실행: .venv-bpy/bin/python v0.4_stage/md_full/fw03_pack_full.py [--hd-backdrop 1.25]
"""
import json, math, os, shutil, sys

import bpy  # noqa: F401  (mathutils)

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402

CFG = json.load(open(os.path.join(HERE, os.environ.get("FW_CONFIG", "full_stage_config.json")), encoding="utf-8"))
OUT = os.path.normpath(os.path.join(HERE, "..", "out", CFG["out_dir"])); TMP = os.path.join(OUT, "_tmp")
if "--preview" in sys.argv:                                  # fw02 --preview 결과로 시험(모양 확인용)
    TMP = os.path.join(TMP, "preview"); OUT = os.path.join(OUT, "preview"); os.makedirs(OUT, exist_ok=True)
    for f in ("collision.png", "heights.png"):             # (fw02 writes the grids to the main out folder in preview mode too)
        if not os.path.exists(os.path.join(OUT, f)) and os.path.exists(os.path.join(OUT, "..", f)):
            shutil.copy(os.path.join(OUT, "..", f), os.path.join(OUT, f))
HD_BG = float(sys.argv[sys.argv.index("--hd-backdrop") + 1]) if "--hd-backdrop" in sys.argv else 1.25
meta = json.load(open(os.path.join(TMP, "layers_meta.json")))
BAYER = (np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]).reshape(4, 4) / 16.0 - 0.5)


def grade(rgb):                                     # mo07과 같음
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


# ---------------------------------------------------------------- 배경
FILL = (12, 6, 5)
fr = SC.frame(CFG); SX0, SY0 = fr[0], fr[1]; W1, H1 = fr[2] - fr[0], fr[3] - fr[1]
g2 = Image.open(os.path.join(TMP, "ground_2x.png")).convert("RGBA")
hd = to_hd(g2); del g2
arr = np.asarray(hd).astype(np.float32); del hd
yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
f = np.clip(np.minimum.reduce([xx, yy, arr.shape[1] - 1 - xx, arr.shape[0] - 1 - yy]) / 140.0, 0, 1)[..., None]; del yy, xx
arr[..., :3] = arr[..., :3] * f + np.array(FILL) * (1 - f); del f
gim = Image.fromarray(arr.astype(np.uint8), "RGBA"); del arr
gim.convert("RGB").resize((int(round(W1 * HD_BG)), int(round(H1 * HD_BG))), Image.LANCZOS).save(os.path.join(OUT, "ground_hd.webp"), quality=86, method=4)   # (a render at HD_BG already: a no-op resize)
to_sd(gim).convert("RGB").save(os.path.join(OUT, "ground_sd.png"), optimize=True); del gim
print("배경", W1, H1, flush=True)

# ---------------------------------------------------------------- 조각: 번호 화면으로 나누기
def ids(path):
    a = np.asarray(Image.open(path).convert("RGBA"))
    return np.where(a[..., 3] > 127, a[..., 0].astype(np.int32) + 256 * a[..., 1].astype(np.int32), 0)


occ = np.asarray(Image.open(os.path.join(TMP, "layer_occ_2x.png")).convert("RGBA"))
allL = np.asarray(Image.open(os.path.join(TMP, "layer_all_2x.png")).convert("RGBA"))
id_occ = ids(os.path.join(TMP, "layer_occ_id_2x.png")); id_all = ids(os.path.join(TMP, "layer_all_id_2x.png"))
spr = {s["pid"]: s for s in meta["sprites"]}
roof_pids = np.array(sorted(p for p, s in spr.items() if s["roof"]))
is_roof_all = np.isin(id_all, roof_pids)
lcx, lcy = meta["layer_crop"][0], meta["layer_crop"][1]      # 층 왼쪽 위(게임 1배 px)
DEN = meta.get("density", 2)                                 # 층 렌더 밀도(본 렌더 2배)
pieces = []                                                  # (id, layer, G, 2배 RGBA 조각, 왼쪽 위 1배 px)


def cut(ys, xs, src, pid_name, layer, G):
    if not len(ys):
        return
    y0, y1 = ys.min() // 2 * 2, -(-(ys.max() + 1) // 2) * 2; x0, x1 = xs.min() // 2 * 2, -(-(xs.max() + 1) // 2) * 2
    sub = src[y0:y1, x0:x1].copy(); m = np.zeros(sub.shape[:2], bool); m[ys - y0, xs - x0] = True
    sub[..., 3] = np.where(m, sub[..., 3], 0)
    pieces.append((pid_name, layer, G, Image.fromarray(sub, "RGBA"), (lcx + x0 / DEN, lcy + y0 / DEN)))


# 번호마다 픽셀 위치를 정렬 한 번으로 모은다(번호 = R + 256·G, 0 = 없음)
for name, idm, src in (("occ", id_occ, occ), ("all", id_all, allL)):
    Wl = idm.shape[1]; flat = idm.ravel(); order = np.argsort(flat, kind="stable"); vals = flat[order]
    starts = np.searchsorted(vals, np.arange(1, len(spr) + 2))
    for pid in range(1, len(spr) + 1):
        s = spr[pid]; idx = order[starts[pid - 1]:starts[pid]]
        if not len(idx) or (name == "occ") == s["roof"]:
            continue
        ys, xs = np.divmod(idx, Wl)
        if name == "occ":
            cov = is_roof_all[ys, xs]
            cut(ys[~cov], xs[~cov], src, s["id"], None, s["G"])
            cut(ys[cov], xs[cov], src, s["id"] + "_in", "inside", s["G"])
        else:
            cut(ys, xs, src, s["id"], "roof", s["G"])
del occ, allL, id_occ, id_all
print("조각", len(pieces), {k: sum(1 for p in pieces if p[1] == k) for k in (None, "inside", "roof")}, flush=True)


def pack(images, maxw, maxh):
    """선반 쌓기. 한 장이 maxh를 넘으면 다음 장(웹P 한 변 16383 px 제한). 반환: 장 목록, (장, x, y)"""
    pages, pos = [], []; x = y = rowh = 0; cur = []
    for im in images:
        if x + im.width > maxw:
            x, y, rowh = 0, y + rowh + 2, 0
        if y + im.height > maxh:
            pages.append((cur, y)); cur = []; x = y = rowh = 0
        cur.append((im, (x, y))); pos.append((len(pages), x, y)); x += im.width + 2; rowh = max(rowh, im.height)
    pages.append((cur, y + rowh))
    out = []
    for items, h in pages:
        hh = max(p_[1] + im.height for im, p_ in items)
        atl = Image.new("RGBA", (maxw, hh), (0, 0, 0, 0))
        for im, p_ in items:
            atl.paste(im, p_)
        out.append(atl)
    return out, pos


order = sorted(range(len(pieces)), key=lambda k: -pieces[k][3].height)     # 높이순으로 쌓아 아틀라스를 작게
pieces = [pieces[k] for k in order]
hd_imgs = [to_hd(p[3]) for p in pieces]; sd_imgs = [to_sd(p[3]) for p in pieces]
atl_hd, pos_hd = pack(hd_imgs, 8192, 16000); atl_sd, pos_sd = pack(sd_imgs, 4096, 16000)
hd_files = [f"sprites_hd_{k}.webp" for k in range(len(atl_hd))]; sd_files = [f"sprites_sd_{k}.png" for k in range(len(atl_sd))]
for a, f in zip(atl_hd, hd_files):
    a.save(os.path.join(OUT, f), quality=90, method=4)
for a, f in zip(atl_sd, sd_files):
    a.save(os.path.join(OUT, f), optimize=True)
print("아틀라스 HD", [a.size for a in atl_hd], "SD", [a.size for a in atl_sd], flush=True)

props = []
for (pid, layer, Gc, im2, (c0x, c0y)), ih, is_, ph, ps in zip(pieces, hd_imgs, sd_imgs, pos_hd, pos_sd):
    cx = cy = Gc / 2.0
    sx, sy = (cx - cy) * SC.HALF_W, (cx + cy) * SC.HALF_H
    e = {"id": pid, "x": round(cx, 3), "y": round(cy, 3), "rect": [0.01, 0.01],
         "sd": {"p": ps[0], "sx": ps[1], "sy": ps[2], "w": is_.width, "h": is_.height, "ox": round(sx - c0x, 2), "oy": round(sy - c0y, 2)},
         "hd": {"p": ph[0], "sx": ph[1], "sy": ph[2], "w": ih.width, "h": ih.height, "ox": round((sx - c0x) * DEN, 2), "oy": round((sy - c0y) * DEN, 2)}}
    if layer:
        e["layer"] = layer
    props.append(e)

col = Image.open(os.path.join(OUT, "collision.png")); wk = CFG["walk"]; cell = wk["cell_m"]
gxa, gya = SC.to_game(CFG, wk["bounds_world"][0], wk["bounds_world"][3]), SC.to_game(CFG, wk["bounds_world"][1], wk["bounds_world"][2])
gx0, gy0 = math.floor(min(gxa[0], gya[0])), math.floor(min(gxa[1], gya[1]))
gpt = lambda xy: [round(v, 3) for v in SC.to_game(CFG, xy[0], xy[1])]
cb = CFG["combat"]
data = {
    "version": 1, "name": "무스타파 · 착륙장과 시설", "layout": CFG["layout"],
    "note": "Movie Duels duel_mus_both 원본 형상·질감 그대로(MO_STAGE). 걸어서 닿는 곳 전체(문·방어막 열림). 좌표는 게임 타일(1 m). gx = OX − Y, gy = OY − X (Blender m)",
    "offset": CFG["game"],
    "backdrop": {"sd": "ground_sd.png", "hd": "ground_hd.webp", "x": SX0, "y": SY0, "w": W1, "h": H1, "fill": list(FILL)},
    "sprites": {"sd": sd_files, "hd": hd_files, "hd_density": DEN},
    "props": props,
    "collision": {"file": "collision.png", "cell": cell, "gx0": gx0, "gy0": gy0, "cols": col.width, "rows": col.height},
    "heights": {"file": "heights.png", "scale": 1000, "offset": 10, "note": "R·G = (바닥 높이 m + offset) × scale, B = 실내(255)"},
    "spawn": gpt(CFG["start"]["world"]),
    "exit": None,
    "objective": "착륙장과 시설 안을 자유롭게 둘러본다",
    "combat": {"area": [gpt(p) for p in cb["area_world"]], "anakinStart": gpt(cb["anakin_start_world"]), "opponentStart": gpt(cb["opponent_start_world"]),
               "trigger": {"center": gpt(cb["trigger_world"]["center"]), "radius": cb["trigger_world"]["radius"]}},
    "ambient": CFG["ambient"],
    "lights": [],
    "region": "무스타파",
}
json.dump(data, open(os.path.join(OUT, "stage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OUT", OUT, "props", len(props), "backdrop", W1, H1, SX0, SY0)
