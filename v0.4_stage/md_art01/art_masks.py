"""ART01 파생 마스크 — 원본 질감에서 '배치 정보'만 뽑아 회색조 마스크로 만든다(PIL·numpy). 색·얼룩·나뭇결은 버린다.
  seam  : 판 경계선(밝기 경계의 기울기) → 바닥·우주선·문 패널 이음선. 원본 UV로 붙이므로 원본 무늬 배치를 그대로 따른다.
  plate : 판마다의 큰 밝기 차이(강하게 흐림) → 판재 톤 차이를 아주 약하게 남길 때 쓴다(0.5 중심).
  glow  : 용암의 밝은 흐름(흐린 밝기) → 용암 발광 세기의 큰 분포만 쓴다.
원본 질감과 이 마스크는 모드 자산 파생물이라 비공개 폴더에만 둔다.
실행: python3 v0.4_stage/md_art01/art_masks.py <textures 폴더> <출력 폴더>
"""
import os, sys

import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def lum(name):
    im = Image.open(os.path.join(SRC, f"textures__{name}.jpg")).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    return im.size, a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def blur(a, r):
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0


def save(a, name):
    Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name))


def wrap_grad(a):
    gx = np.roll(a, -1, 1) - np.roll(a, 1, 1); gy = np.roll(a, -1, 0) - np.roll(a, 1, 0)
    return np.hypot(gx, gy)


def seam(name, pre_blur, widen, pct=98.5, floor=0.38):
    size, L = lum(name)
    g = wrap_grad(blur(L, pre_blur))                     # 잡음(얼룩)보다 큰 밝기 경계만 남김
    g = np.clip((g / np.percentile(g, pct) - floor) / (1 - floor), 0, 1)        # 얼룩 수준의 약한 기울기는 버림
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(widen))).astype(np.float32) / 255
    g = blur(g, 0.8)
    save(g, f"seam_{name.split('__')[1]}.png"); return g


def plate(name, r):
    size, L = lum(name)
    b = blur(L, r); b = (b - b.mean()) / (np.abs(b - b.mean()).max() + 1e-6)
    save(0.5 + 0.5 * b, f"plate_{name.split('__')[1]}.png")


def lines_dark(name, r_big, k):
    """밝은 판 위에 그린 어두운 선(우주선·문): 큰 흐림과의 차이로 선만 뽑음."""
    size, L = lum(name)
    d = np.clip((blur(L, r_big) - L) / k, 0, 1)
    save(blur(d, 0.6), f"seam_{name.split('__')[1]}.png")


seam("plasma_Mustafar__floor_1_o", 3.0, 5)                # 착륙장 바닥 7.2 m/타일, 1024 px → 0.7 cm/px. 선 폭 약 3.5 cm(게임 1배 1 px)
plate("plasma_Mustafar__floor_1_o", 6)
seam("plasma_Mustafar__floor_3_o", 2.5, 3)                # 베이·옆 통로 바닥 6.2 m/타일, 512 px
plate("plasma_Mustafar__floor_3_o", 4)
seam("Asjc_Mustafar__control_floor_2", 1.5, 3)
seam("Asjc_Mustafar__mustafar_door", 1.5, 3)
lines_dark("Asjc_starship__hull", 6, 0.12)
lines_dark("Asjc_starship__silver_wing", 6, 0.10)
lines_dark("Asjc_starship__silver_hull_underside", 6, 0.12)
lines_dark("Asjc_starship__ramp2", 6, 0.12)
size, L = lum("plasma_Mustafar__lava")
g = blur(L, 1.5); g = (g - g.min()) / (g.max() - g.min()); save(g, "glow_lava.png")
print("masks ->", OUT, sorted(os.listdir(OUT)))
