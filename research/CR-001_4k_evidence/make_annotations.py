"""CR-001 4K 근거 주석 이미지 생성. 입력: 사용자 제공 ZIP의 frames/ (경로를 인자로), refs/R2. 출력: annotated/.
실행: .venv-bpy/bin/python -I research/CR-001_4k_evidence/make_annotations.py <패키지 frames 폴더> <사이트에서 받은 full 폴더>
(저장소 루트에서. 출력은 _private/annotated — 커밋 제외. 두 번째 폴더는 갤러리 원본 URL에서 받은 3840×1600 파일, 파일명 = 갤러리 번호.jpg)"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

U = sys.argv[1].rstrip("/") + "/"
V = sys.argv[2].rstrip("/") + "/" if len(sys.argv) > 2 else None
HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.join(HERE, "_private", "annotated") + "/"   # 영화 화면이 들어가므로 커밋하지 않음
R2 = os.path.join(HERE, "..", "..", "refs", "R2_film_lecture.jpg")
FT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
F = ImageFont.truetype(FT, 22); FB = ImageFont.truetype(FT, 26); FS = ImageFont.truetype(FT, 18)
COL = {"V": (90, 230, 120), "P": (250, 200, 80), "U": (240, 110, 210)}
LEG = "초록 = VERIFIED(화면에서 직접 보임)   노랑 = PROBABLE(해석 포함)   자홍 = UNKNOWN(판정 불가)   상자는 관찰 위치 표시이며 정확한 외곽선이 아님"


def base(name, gamma, size=(1920, 800)):
    im = Image.open(U + name).convert("RGB").resize(size)
    a = np.power(np.asarray(im).astype(float) / 255, gamma)
    return Image.fromarray((a * 255).clip(0, 255).astype("uint8"))


def d2(p):
    return [v * 0.96 for v in p]          # 원본 3840폭을 2000폭으로 본 좌표 → 1920폭


def annotate(name, gamma, title, items, out):
    im = base(name, gamma); dr = ImageDraw.Draw(im, "RGBA")
    for kind, lv, coords, text, tpos in items:
        c = COL[lv]
        if kind == "box":
            dr.rectangle(d2(coords), outline=c + (255,), width=3)
        elif kind == "pts":
            for x, y in coords:
                x, y = x * 0.96, y * 0.96
                dr.ellipse((x - 9, y - 9, x + 9, y + 9), outline=c + (255,), width=3)
        elif kind == "poly":
            dr.polygon([tuple(d2(p)) for p in coords], outline=c + (255,), width=3)
        tx, ty = tpos[0] * 0.96, tpos[1] * 0.96
        w = dr.textlength(text, font=F)
        dr.rectangle((tx - 4, ty - 2, tx + w + 4, ty + 26), fill=(0, 0, 0, 200))
        dr.text((tx, ty), text, font=F, fill=c + (255,))
    dr.rectangle((0, 0, 1920, 40), fill=(0, 0, 0, 230)); dr.text((10, 6), title, font=FB, fill=(255, 255, 255))
    dr.rectangle((0, 770, 1920, 800), fill=(0, 0, 0, 230)); dr.text((10, 774), LEG, font=FS, fill=(230, 230, 230))
    im.save(out)


annotate("11615.jpg", 0.8, "11615 (p65) — R2와 같은 고정 카메라. 시설 쪽 경사 지지부·틈·뒤쪽 슬래브", [
    ("box", "V", (1480, 45, 1995, 600), "A01 경사 지지부 3+개, 처마 조명 3점", (1190, 50)),
    ("pts", "V", [(1070, 355), (1210, 420), (1430, 510)], "A04 시설 쪽 가장자리 낮은 등", (960, 520)),
    ("poly", "V", [(1290, 385), (1430, 380), (1490, 560), (1400, 510)], "A02 가장자리 너머 열린 틈(붉은 빛)", (1060, 440)),
    ("box", "P", (880, 265, 1480, 375), "A02/A04 틈 위를 건너는 뒤쪽 슬래브(다리 기능 PROBABLE)", (520, 225)),
    ("box", "U", (1440, 525, 1600, 600), "A02 틈 바닥·깊이: 안 보임", (1110, 610)),
    ("box", "V", (1680, 605, 1998, 830), "A03 빛나는 세로 슬롯이 있는 낮은 상자", (1290, 735)),
], O + "A_11615_facility_gap.png")

annotate("11235.jpg", 0.6, "11235 (p63) — 지상 시점. 처마 조명 3점 옆의 깊은 개방 베이와 두꺼운 지붕", [
    ("pts", "V", [(1226, 498), (1326, 476), (1451, 447)], "A01 처마 조명 3점", (1060, 400)),
    ("box", "V", (1466, 261, 1998, 410), "A01 두꺼운 돌출 지붕 슬래브(두께·깊이 UNKNOWN)", (1080, 215)),
    ("box", "V", (1557, 410, 1647, 629), "A01 바닥선 아래에서 오르는 경사 지지부", (1220, 560)),
    ("box", "V", (1650, 448, 1946, 661), "A01 개방 베이: 안쪽 장비·증기", (1660, 418)),
    ("box", "P", (1397, 629, 1760, 693), "A03 계단식 무늬 낮은 상자(11615 상자와 동일 PROBABLE)", (900, 710)),
], O + "B_11235_open_bay.png")

annotate("11141.jpg", 0.55, "11141 (p62) — 접근 컷(위에서). 판 상판·두꺼운 측면·아래 구조, 오른쪽 시설 탑", [
    ("box", "V", (660, 470, 1260, 700), "A04 판 상판(우주선이 일부 가림)", (660, 425)),
    ("box", "P", (650, 560, 760, 700), "A04 왼쪽 앞 모서리: 꺾인 윤곽(형태 PROBABLE)", (240, 520)),
    ("box", "V", (760, 690, 1500, 833), "A04 상판 아래 패널형 입체 구조(체계 UNKNOWN)", (900, 735)),
    ("box", "V", (1690, 250, 1998, 800), "시설 탑(붉은 삼각 돌출)", (1560, 205)),
], O + "C_11141_platform_approach.png")

annotate("11850.jpg", 0.6, "11850 (p66) — 시설 안에서 밖을 봄. 큰 출입구, 바깥으로 내려가는 계단", [
    ("box", "V", (560, 45, 800, 510), "A03 출입구 왼쪽 문설주(꺾인 형태)", (200, 520)),
    ("box", "V", (1500, 45, 1720, 720), "A03 오른쪽 문설주+경사 받침", (1330, 725)),
    ("box", "V", (900, 370, 1540, 560), "A03 바깥 계단(가장자리 등)", (960, 330)),
    ("box", "U", (760, 250, 1100, 480), "용암까지의 높이차·방위: UNKNOWN", (560, 580)),
], O + "D_11850_entrance.png")

annotate("11844.jpg", 0.8, "11844 (p66) — 용암 옆 낮은 외부 보행로와 짧은 밝은 계단", [
    ("box", "V", (1610, 320, 1920, 490), "A03 짧은 밝은 계단(시설 안쪽으로 오름)", (1290, 280)),
    ("box", "V", (150, 480, 1800, 833), "A03 낮은 보행로, 용암 쪽 가장자리 등", (200, 440)),
    ("box", "U", (0, 45, 600, 300), "착륙장과의 연결: 이 프레임에 없음", (40, 310)),
], O + "E_11844_walkway_stair.png")

a = base("11882.jpg", 0.8, (960, 400)); b = base("11888.jpg", 0.8, (960, 400))
im = Image.new("RGB", (1920, 500), (0, 0, 0)); im.paste(a, (0, 50)); im.paste(b, (960, 50)); dr = ImageDraw.Draw(im, "RGBA")
dr.text((10, 10), "11882 (p67) 리브 복도 → 문틀 너머 홀로그램 테이블·붉은 화면 2개      |      11888 (p67) 방 안 역방향: 화면 2개 사이 문, 쓰러진 분리주의 지도자들", font=FS, fill=(255, 255, 255))
dr.rectangle((310, 80, 640, 260), outline=COL["V"] + (255,), width=3)
dr.rectangle((1392, 92, 1478, 232), outline=COL["V"] + (255,), width=3)
dr.text((10, 460), "VERIFIED: 11882 한 화면에 리브 복도 문틀과 홀로그램실이 함께 보임. 11888: 같은 방(화면·테이블)에 분리주의 지도자 시신. 복도 길이·방위 UNKNOWN", font=F, fill=COL["V"])
im.save(O + "F_11882_11888_corridor_room.png")

k = Image.open(U + "11615.jpg").convert("RGB").resize((1280, 533))
r = Image.open(R2).convert("RGB").crop((0, 288, 2954, 1544)).resize((1280, 533))
ov = Image.blend(k, r, 0.5); im = Image.new("RGB", (1280, 533 * 3 + 90), (0, 0, 0)); dr = ImageDraw.Draw(im)
for i, (x, t) in enumerate([(k, "4K 11615 (p65)"), (r, "R2 (refs/R2_film_lecture.jpg, 화면 캡처 288~1544행)"),
                            (ov, "겹침 50/50 — 구조물은 겹치고 인물 위치는 다름 = 같은 고정 카메라, 다른 순간")]):
    im.paste(x, (0, 30 + i * 563)); dr.text((8, 4 + i * 563), t, font=FS, fill=(255, 255, 255))
im.save(O + "G_R2_vs_11615_same_camera.png")


def annotate2(name, gamma, title, items, out, k=1.0):
    """V 폴더 원본, 좌표는 1920폭 기준(k=1)."""
    global U
    keep = U; U = V
    try:
        annotate(name, gamma, title, [(a, b, c if a == "pts" else tuple(v / 0.96 for v in c), d, (e[0] / 0.96, e[1] / 0.96))
                                      for a, b, c, d, e in [(a, b, [(x / 0.96, y / 0.96) for x, y in c] if a == "pts" else c, d, e)
                                                            for a, b, c, d, e in items]], out)
    finally:
        U = keep


if V:
    annotate2("11206.jpg", 0.6, "11206 (p63) — 우주선 창밖 원거리: 착륙장 시설 전경", [
        ("box", "V", (1000, 282, 1478, 338), "A01 두꺼운 돌출 지붕(버섯형 슬래브)", (560, 240)),
        ("box", "V", (1110, 335, 1430, 452), "A01 정면 A자 요소(잠정 관찰, 개구부 총수 UNKNOWN)", (560, 470)),
        ("box", "V", (1205, 45, 1340, 285), "지붕 위 마스트", (1350, 120)),
        ("box", "V", (930, 405, 1915, 492), "A04 가장자리 키 큰 등 기둥 + 난간", (1360, 500)),
        ("box", "P", (1425, 300, 1645, 450), "오른쪽 낮은 부속 건물(관계 UNKNOWN)", (1460, 250)),
        ("box", "U", (940, 495, 1760, 760), "상판 아래 암반·구조의 경계 UNKNOWN", (980, 700)),
    ], O + "H_11206_far_view.png")
    annotate2("11246.jpg", 0.5, "11246 (p63) — 만남 장면: 계단 상자 안 계단, 가장자리 너머 틈", [
        ("box", "V", (1205, 400, 1918, 745), "A03 계단 상자: 열린 윗면 안에 내려가는 계단", (1080, 755)),
        ("box", "P", (0, 225, 570, 455), "A02 가장자리 등 너머 틈 + 뒤쪽 슬래브(11615와 같은 구성)", (20, 465)),
        ("box", "V", (575, 45, 1915, 470), "A01 경사 지지부와 개방 베이(안쪽 장비)", (1000, 55)),
    ], O + "I_11246_stairwell_gap.png")
    annotate2("11726.jpg", 0.55, "11726 (p66) — 착륙장 결투: 시설 정면 배열 (조명 구간 → 베이 → A자 출입구)", [
        ("box", "V", (0, 90, 330, 585), "A01 처마 조명·경사 지지부", (20, 600)),
        ("box", "P", (330, 360, 560, 525), "A01 개방 베이 안 물체", (300, 315)),
        ("box", "V", (1130, 140, 1565, 595), "A03 A자 출입구(꼭대기 조명)", (1180, 95)),
        ("box", "V", (790, 488, 1500, 635), "A03 계단 상자", (900, 645)),
        ("box", "V", (1700, 488, 1918, 615), "A04 용암 쪽 낮은 연석", (1560, 650)),
    ], O + "J_11726_facade_sequence.png")
    annotate2("11748.jpg", 0.55, "11748 (p66) — 착륙장 바닥과 A자 출입구가 한 화면: 안쪽 통로가 보임", [
        ("box", "V", (230, 140, 845, 612), "A03 A자 출입구, 안쪽 통로 보임(통로가 11878 리브 복도인지는 UNKNOWN)", (40, 95)),
        ("pts", "V", [(540, 145)], "출입구 꼭대기 조명", (590, 160)),
        ("box", "V", (1000, 505, 1405, 645), "A03 계단 상자", (1030, 655)),
        ("box", "V", (1670, 605, 1845, 692), "A04 가장자리 낮은 연석, 너머 용암", (1300, 700)),
    ], O + "K_11748_entrance_from_deck.png")
    annotate2("11712.jpg", 0.55, "11712 (p66) — 위에서 본 결투: 바닥 판재 배열", [
        ("box", "V", (380, 200, 1700, 765), "바닥: 길쭉한 육각(화살촉)판이 평행한 띠로 반복", (420, 160)),
        ("pts", "V", [(375, 62), (990, 47)], "가장자리 낮은 청색 등", (1030, 60)),
    ], O + "L_11712_floor_pattern.png")
    a = base_from = None
    a = Image.open(V + "11625.jpg").convert("RGB").resize((960, 400)); b = Image.open(V + "11633.jpg").convert("RGB").resize((960, 400))
    def g(im, gm):
        x = np.power(np.asarray(im).astype(float) / 255, gm); return Image.fromarray((x * 255).clip(0, 255).astype("uint8"))
    a, b = g(a, 0.55), g(b, 0.55)
    im = Image.new("RGB", (1920, 520), (0, 0, 0)); im.paste(a, (0, 50)); im.paste(b, (960, 50)); dr = ImageDraw.Draw(im, "RGBA")
    dr.text((10, 10), "11625 (p65) 반대 방향: 뒤쪽 키 큰 등 기둥+난간, 오른쪽 가장자리 단차      |      11633 (p65) 계단 상자 너머 바로 용암", font=FS, fill=(255, 255, 255))
    dr.rectangle((650, 50 + 160, 940, 50 + 198), outline=COL["V"] + (255,), width=3)
    dr.rectangle((750, 50 + 200, 960, 50 + 250), outline=COL["P"] + (255,), width=3)
    dr.rectangle((960 + 160, 50 + 230, 960 + 625, 50 + 325), outline=COL["V"] + (255,), width=3)
    dr.rectangle((960 + 550, 50 + 125, 960 + 955, 50 + 280), outline=COL["P"] + (255,), width=3)
    dr.text((10, 460), "초록: A04 뒤쪽 등 기둥+난간(VERIFIED), A03 계단 상자(VERIFIED)   노랑: A02 가장자리 단차(PROBABLE), A04 상자 너머 앞 끝(PROBABLE)", font=FS, fill=(230, 230, 230))
    im.save(O + "M_11625_11633_reverse_angles.png")
print("annotated OK")
