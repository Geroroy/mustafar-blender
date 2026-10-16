"""POC01 ↔ POC02 비교판 묶기(PIL). md07_views.py가 같은 카메라 표로 찍은 두 쌍의 렌더를 짝지어 한 장씩 만든다.
영화 스틸이 들어가므로 출력은 비공개 폴더(_private)에만 둔다(커밋 금지).
순서: 영화 → POC01 → POC02 (왼쪽에서 오른쪽). 게임 카메라 화면은 POC01 → POC02.
실행(저장소 루트): python3 -I v0.4_stage/md_remake/md08_sheets02.py <POC01 렌더 폴더 접두어> <POC02 렌더 폴더 접두어> <영화 폴더> <출력 폴더(_private 안)>
"""
import os, sys

from PIL import Image, ImageDraw, ImageFont

P1, P2, FILM, OUT = sys.argv[1:5]
assert "_private" in os.path.abspath(OUT), "영화 이미지가 들어가므로 _private 안에만 저장"
os.makedirs(OUT, exist_ok=True)
FT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
F, FB = ImageFont.truetype(FT, 20), ImageFont.truetype(FT, 26)


def content(im):
    g = im.convert("L").point(lambda v: 255 if v > 12 else 0); return im.crop(g.getbbox())


def film(name, crop=True):
    p = os.path.join(FILM, name); im = Image.open(p).convert("RGB")
    return content(im) if (crop and name.endswith(".png")) else im


def view(pre, name):
    return Image.open(f"{pre}_{name}.png").convert("RGB")


def fit_w(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def row(cells, w):
    """cells: [(캡션, 이미지)] → 같은 너비로 가로 배치한 한 줄 이미지."""
    ims = [fit_w(i, w) for _, i in cells]; h = max(i.height for i in ims)
    R = Image.new("RGB", (w * len(ims) + 10 * (len(ims) + 1), h + 36), (16, 18, 22)); d = ImageDraw.Draw(R)
    for k, ((cap, _), im) in enumerate(zip(cells, ims)):
        x = 10 + k * (w + 10); R.paste(im, (x, 0)); d.text((x + 4, h + 6), cap, font=F, fill=(255, 220, 120))
    return R


def sheet(title, note, rows, out):
    Wd = max(r.width for r in rows); Ht = 78 + sum(r.height + 6 for r in rows)
    S = Image.new("RGB", (Wd, Ht), (16, 18, 22)); d = ImageDraw.Draw(S)
    d.text((12, 10), title, font=FB, fill=(240, 240, 240)); d.text((12, 46), note, font=F, fill=(190, 200, 210))
    y = 78
    for r in rows:
        S.paste(r, (0, y)); y += r.height + 6
    S.save(os.path.join(OUT, out), optimize=True); print("sheet", out, S.size)


L1, L2 = "POC01(수정 전)", "POC02(수정 후)"
sheet("① 입구 근접 — 영화 78862·11748 ↔ POC01 → POC02",
      "원근 화면은 영화 시점과 비슷한 근사 카메라(맞춤 아님). 1.8 m 인체 대용(회색 형상)을 같은 자리에 둠. 아래 줄: 같은 게임 카메라·같은 화면 범위.",
      [row([("영화 78862 (입구)", film("78862.png")), (f"{L1} 근사 시점", view(P1, "entrance_film78862")), (f"{L2} 같은 시점", view(P2, "entrance_film78862"))], 660),
       row([("영화 11748 (입구·통로)", film("11748.jpg")), (f"{L1} 근사 시점", view(P1, "entrance_film11748")), (f"{L2} 같은 시점", view(P2, "entrance_film11748"))], 660),
       row([(f"{L1} 게임 카메라", view(P1, "entrance_game")), (f"{L2} 게임 카메라", view(P2, "entrance_game"))], 640)],
      "S1_entrance_POC01_vs_POC02.png")
sheet("② 낮은 상자 — 영화 78855 ↔ POC01 → POC02",
      "원근 화면은 근사 카메라. 낮은 장치 2개의 바닥 투영 크기·높이(0.87 m)는 POC01 상자와 같음.",
      [row([("영화 78855 (낮은 상자)", film("78855.png")), (f"{L1} 근사 시점", view(P1, "crate_film78855")), (f"{L2} 같은 시점", view(P2, "crate_film78855"))], 560),
       row([(f"{L1} 근접(−Y 쪽 장치)", view(P1, "crate_close")), (f"{L2} 근접(같은 카메라)", view(P2, "crate_close"))], 720),
       row([(f"{L1} 게임 카메라", view(P1, "crates_game")), (f"{L2} 게임 카메라", view(P2, "crates_game"))], 540)],
      "S2_crates_POC01_vs_POC02.png")
sheet("③ 바닥 + 1.8 m 인체 — 영화 11246 ↔ POC01 → POC02",
      "바닥 재질만 바꿈(MD_Pad_Deck 형상·외곽·충돌 그대로). 인체 대용 형상은 렌더 전용.",
      [row([("영화 11246 (바닥 이음선)", film("11246.jpg")), (f"{L1} 낮은 시점+인체", view(P1, "floor_human")), (f"{L2} 같은 시점", view(P2, "floor_human"))], 660),
       row([(f"{L1} 게임 카메라", view(P1, "floor_game")), (f"{L2} 게임 카메라", view(P2, "floor_game"))], 760)],
      "S3_floor_human_POC01_vs_POC02.png")
sheet("④ 전체 보기 — 같은 게임 카메라·같은 화면 범위(POC01 → POC02)",
      "직교 30°/45°, 28.284 px/m. 화면 범위는 판 윗면·출입구·지붕(마스트)을 중심으로 고정(받침 다리 끝은 담지 않음; 다리는 자르지 않았고 모델 그대로).",
      [row([(L1, view(P1, "full_game")), (L2, view(P2, "full_game"))], 1100)],
      "S4_full_game_POC01_vs_POC02.png")
sheet("⑤ 지붕(보충) — 영화 11206·11233 ↔ POC01 → POC02",
      "윤곽·돌출 2.25 m·두께 1.8 m 그대로. 처마 아래 후퇴부·윗면 비스듬한 가장자리·마스트(높이는 제작값) 추가.",
      [row([("영화 11206 (지붕·마스트)", film("11206.jpg")), (f"{L1} 근사 시점", view(P1, "roof_far")), (f"{L2} 같은 시점", view(P2, "roof_far"))], 660),
       row([("영화 11233 (처마·지붕)", film("11233.jpg")), (f"{L1} 근사 시점", view(P1, "roof_persp")), (f"{L2} 같은 시점", view(P2, "roof_persp"))], 660),
       row([(f"{L1} 게임 카메라(지붕·마스트 범위)", view(P1, "roof_game")), (f"{L2} 게임 카메라", view(P2, "roof_game"))], 640)],
      "S5_roof_POC01_vs_POC02.png")
