"""구조 수정 3차 비교 묶음.
1) 전/후 묶음(영화 없음, 커밋 가능): CR-013 iso·views의 A3d/A3e 같은 카메라 화면을 나란히.
2) 영화 대조(비공개 출력 전용 — 영화 이미지 포함, 커밋 금지): 78862·78855·11206 원본 영역과 렌더 영역을 표시해 한 장에.
카메라는 비슷한 시점의 근사이며 맞춤이 아니다(카메라 재계산·치수 탐색 아님).
실행(저장소 루트): python3 research/CR-001_4k_evidence/verify/compare_structfix03.py <팩 film 폴더> <비공개 출력 폴더>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

FILM, PRIV = sys.argv[1], sys.argv[2]
assert "_private" in os.path.abspath(PRIV), "영화 이미지가 들어가므로 _private 안에만 저장"
os.makedirs(PRIV, exist_ok=True)
R = os.path.join(os.path.dirname(__file__), "..", "..", "..", "chatgpt_reviews", "CR-013_structure_fix_03")
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 24)


def label(im, t, col=(255, 255, 255), bg=(0, 0, 0)):
    d = ImageDraw.Draw(im); tw = d.textlength(t, font=FT); d.rectangle((0, 0, tw + 16, 36), fill=bg); d.text((8, 4), t, font=FT, fill=col); return im


def content(im):
    g = im.convert("L").point(lambda v: 255 if v > 12 else 0); return im.crop(g.getbbox())


def fit(im, w=None, h=None):
    if w:
        return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


def side(ims, out, gap=8):
    h = max(i.height for i in ims); W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    o = Image.new("RGB", (W, h), (0, 0, 0)); x = 0
    for i in ims:
        o.paste(i, (x, 0)); x += i.width + gap
    o.save(out, optimize=True); print(out, o.size)


def stack(ims, out, gap=8):
    w = max(i.width for i in ims); H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    o = Image.new("RGB", (w, H), (0, 0, 0)); y = 0
    for i in ims:
        o.paste(i, (0, y)); y += i.height + gap
    o.save(out, optimize=True); print(out, o.size)


V = lambda n: Image.open(os.path.join(R, "views", n)).convert("RGB")
I = lambda n: Image.open(os.path.join(R, "iso", n)).convert("RGB")
# 1) 전/후(영화 없음)
side([label(I("before_A3d_full.png"), "전 A3d — 게임 카메라·같은 확대"), label(I("after_A3e_full.png"), "후 A3e — 같은 카메라·같은 확대")], os.path.join(R, "01_before_after_full.png"))
side([label(I("A3d_R_entrance.png"), "전 A3d: 짧은 R·뾰족한 A자 문"), label(I("A3e_R_entrance.png"), "후 A3e: 확장부 위 큰 R·영화 윤곽 문")], os.path.join(R, "02_R_entrance_iso.png"))
stack([fit(label(V("A3d_R_oblique.png"), "전 A3d — R·측면"), 1400), fit(label(V("A3e_R_oblique.png"), "후 A3e — 같은 카메라: 측면 확장 + R 재구성"), 1400)], os.path.join(R, "03_R_extension_before_after.png"))
side([label(V("A3d_entrance_front.png"), "전 A3d — 출입구 정면"), label(V("A3e_entrance_front.png"), "후 A3e — 같은 카메라")], os.path.join(R, "04_entry_front_before_after.png"))
stack([fit(label(V("A3d_entrance_oblique.png"), "전 A3d — 출입구 비스듬히"), 1400), fit(label(V("A3e_entrance_oblique.png"), "후 A3e — 같은 카메라"), 1400)], os.path.join(R, "05_entry_oblique_before_after.png"))
side([label(I("A3d_pad.png"), "전 A3d: 직사각 판"), label(I("A3e_pad.png"), "후 A3e: 큰 사선 절삭 + 측면 확장")], os.path.join(R, "06_pad_outline_iso.png"))
stack([fit(label(V("A3d_pad_overview.png"), "전 A3d — 판 외곽(높은 시점)"), 1400), fit(label(V("A3e_pad_overview.png"), "후 A3e — 같은 카메라"), 1400)], os.path.join(R, "07_pad_outline_before_after.png"))
side([label(I("A3d_side.png"), "전 A3d: 통로 없음"), label(I("A3e_side.png"), "후 A3e: 시설 왼쪽 끝 외부 통로(끝 = 작업 경계)")], os.path.join(R, "08_side_iso.png"))
stack([fit(label(V("A3d_side_walkway.png"), "전 A3d"), 1400), fit(label(V("A3e_side_walkway.png"), "후 A3e — 같은 카메라: 외부 통로"), 1400)], os.path.join(R, "09_side_before_after.png"))

# 2) 영화 대조(비공개)
F = lambda n: content(Image.open(os.path.join(FILM, n)).convert("RGB"))
TAGF, TAGR = (255, 220, 120), (140, 220, 255)
f = fit(F("78862.png"), 1434)
stack([label(f, "[영화 원본] 78862 — 출입구 윤곽·단차·볼판·가로 처마", TAGF), label(V("A3d_film78862.png"), "[렌더] 전 A3d — 같은 근사 카메라", TAGR),
       label(V("A3e_film78862.png"), "[렌더] 후 A3e — 같은 근사 카메라", TAGR)], os.path.join(PRIV, "C1_78862_vs_entry.png"))
f = fit(F("78855.png"), h=1100)
side([label(f, "[영화] 78855", TAGF), label(V("A3d_film78855.png"), "[렌더] 전 A3d", TAGR), label(V("A3e_film78855.png"), "[렌더] 후 A3e — R(대응 미확정)", TAGR)], os.path.join(PRIV, "C2_78855_vs_R.png"))
f = fit(F("11206.jpg"), 1600)
stack([label(f, "[영화 원본] 11206 — 원경 실루엣(가려진 외곽 미확정)", TAGF), label(V("A3d_film11206.png"), "[렌더] 전 A3d — 먼 옆 근사 시점", TAGR),
       label(V("A3e_film11206.png"), "[렌더] 후 A3e — 같은 근사 시점", TAGR)], os.path.join(PRIV, "C3_11206_vs_pad.png"))
