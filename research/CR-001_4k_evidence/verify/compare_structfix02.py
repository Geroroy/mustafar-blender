"""구조 수정 2차 영화 대조(비공개 출력 전용 — 영화 이미지 포함, 커밋 금지).
78862 ↔ 출입구(A3c 전 / A3d 후, 같은 근사 카메라), 78853 ↔ 베이·칸막이. 카메라는 비슷한 시점의 근사이며 맞춤이 아니다.
실행(저장소 루트): python3 research/CR-001_4k_evidence/verify/compare_structfix02.py <팩 film 폴더> <출력 폴더(_private 안)>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

FILM, OUT = sys.argv[1], sys.argv[2]
assert "_private" in os.path.abspath(OUT), "영화 이미지가 들어가므로 _private 안에만 저장"
os.makedirs(OUT, exist_ok=True)
V = os.path.join(os.path.dirname(__file__), "..", "..", "..", "chatgpt_reviews", "CR-012_structure_fix_02", "views")
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 24)


def content(im):
    """검은 테두리(레터박스)를 잘라 낸 영상 부분."""
    g = im.convert("L").point(lambda v: 255 if v > 12 else 0); return im.crop(g.getbbox())


def label(im, t):
    d = ImageDraw.Draw(im); tw = d.textlength(t, font=FT); d.rectangle((0, 0, tw + 16, 36), fill=(0, 0, 0)); d.text((8, 4), t, font=FT, fill=(255, 255, 255)); return im


# 78862 ↔ 출입구: 세 줄(영화 / A3c / A3d)
f = content(Image.open(os.path.join(FILM, "78862.png")).convert("RGB")).resize((1434, 600), Image.LANCZOS)
rows = [label(f, "영화 78862 (출입구·바깥 테두리·양옆 낮은 구조물)"),
        label(Image.open(os.path.join(V, "A3c_film78862.png")).convert("RGB"), "수정 전 A3c — 같은 근사 카메라"),
        label(Image.open(os.path.join(V, "A3d_film78862.png")).convert("RGB"), "수정 후 A3d — 같은 근사 카메라")]
im = Image.new("RGB", (1434, 600 * 3 + 8), (0, 0, 0))
for k, r in enumerate(rows):
    im.paste(r, (0, k * 604))
im.save(os.path.join(OUT, "C1_78862_vs_entrance.png"), optimize=True)

# 78853 ↔ 베이·칸막이: 나란히(영화 / A3c / A3d)
f = content(Image.open(os.path.join(FILM, "78853.png")).convert("RGB")); f = f.resize((int(f.width * 900 / f.height), 900), Image.LANCZOS)
a = Image.open(os.path.join(V, "A3c_film78853.png")).convert("RGB").resize((900, 900), Image.LANCZOS)
b = Image.open(os.path.join(V, "A3d_film78853.png")).convert("RGB").resize((900, 900), Image.LANCZOS)
im = Image.new("RGB", (f.width + 1808, 900), (0, 0, 0))
im.paste(label(f, "영화 78853"), (0, 0)); im.paste(label(a, "A3c"), (f.width + 4, 0)); im.paste(label(b, "A3d"), (f.width + 908, 0))
im.save(os.path.join(OUT, "C2_78853_vs_bays.png"), optimize=True)
print("OUT", OUT)
