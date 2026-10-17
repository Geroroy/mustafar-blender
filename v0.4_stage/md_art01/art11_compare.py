"""ART01-11 전후 비교판 — art_shots.js로 같은 위치·카메라·배율에서 찍은 실제 게임 화면(전 = MO 데이터, 후 = ART01 데이터)을 나란히 붙인다(PIL).
또 게임처럼 합성한 착륙장 전체 화면(C1)의 전후도 같은 크기로 붙인다.
실행: python3 v0.4_stage/md_art01/art11_compare.py <전 촬영 폴더> <후 촬영 폴더> <전 C1 png> <후 C1 png> <출력 폴더>
"""
import os, sys

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
BEF, AFT, C1B, C1A, OUTD = sys.argv[1:6]
os.makedirs(OUTD, exist_ok=True)
FP = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
FT = ImageFont.truetype(FP, 24) if os.path.exists(FP) else ImageFont.load_default()
SPOTS = {"start": "시작점", "ship_front": "우주선 앞(날개 아래 판 가장자리)", "ship_back": "우주선 뒤(선체 뒤 — 게임 반투명 규칙으로 선체가 비침)",
         "entrance": "시설 입구(계단 앞)", "walkway": "외부 통로(시설 옆)"}
MODES = {"remaster": "리마스터(HD, 기본)", "original": "오리지널(SD)"}


def pair(a, b, title, sub):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    W, H = A.size; band = 76
    out = Image.new("RGB", (W * 2 + 12, H + band), (14, 16, 20)); out.paste(A, (0, band)); out.paste(B, (W + 12, band))
    d = ImageDraw.Draw(out)
    d.text((10, 8), title, fill=(240, 240, 240), font=FT); d.text((10, 42), sub, fill=(180, 190, 200), font=FT)
    d.text((W - 160, 42), "전 (MO)", fill=(255, 200, 120), font=FT); d.text((2 * W - 160, 42), "후 (ART01)", fill=(140, 220, 255), font=FT)
    return out


for mode, mname in MODES.items():
    for z in (1, 2):
        for k, kn in SPOTS.items():
            a, b = os.path.join(BEF, f"{mode}_z{z}_{k}.png"), os.path.join(AFT, f"{mode}_z{z}_{k}.png")
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            zt = "게임 1배(기본 확대, 720p: 게임 1 px = 화면 2 px)" if z == 1 else "확대(게임 확대 2: 게임 1 px = 화면 3 px)"
            pair(a, b, f"{kn} — 같은 캐릭터 위치·카메라·배율", f"{mname} · {zt}").save(os.path.join(OUTD, f"{mode}_z{z}_{k}.png"))
A, B = Image.open(C1B).convert("RGB"), Image.open(C1A).convert("RGB")
W = 1600; A = A.resize((W, int(A.height * W / A.width)), Image.LANCZOS); B = B.resize((W, int(B.height * W / B.width)), Image.LANCZOS)
out = Image.new("RGB", (W, A.height * 2 + 120), (14, 16, 20)); d = ImageDraw.Draw(out)
d.text((10, 14), "착륙장 전체 — 게임 카메라 합성(배경 + 깊이 띠 조각, 유닛 없음). 위 = 전(MO), 아래 = 후(ART01)", fill=(240, 240, 240), font=FT)
out.paste(A, (0, 60)); out.paste(B, (0, 120 + A.height))
out.save(os.path.join(OUTD, "full_game_camera_before_after.png"))
print("OK", sorted(os.listdir(OUTD)))
