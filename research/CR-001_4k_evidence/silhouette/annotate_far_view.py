"""CR-004 시설 전체 실루엣 — 11198·11203·11206·11209 원거리 구분 표시(영화 화면 → _private).
11206에서 사람이 확대 격자로 읽은 영역(REGIONS, 4K px)을 다른 세 장에는 지붕·몸체 부분의 템플릿 맞춤(평행이동만)으로 옮긴다.
평행이동으로 설명되지 않는 이동(시점 변화)은 고려하지 않으므로, 다른 프레임의 상자는 근사 표시다.
실행: .venv-bpy/bin/python -I research/CR-001_4k_evidence/silhouette/annotate_far_view.py <프레임 폴더> <출력 폴더>"""
import json, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FR, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
# 11206 기준 영역 (x0, y0, x1, y1), 범주, 판정
REGIONS = [
    ("roof", (2015, 585, 2945, 668), "지붕 외곽(버섯형 돌출 슬래브)", "V"),
    ("body", (2223, 668, 2860, 900), "몸체 외곽(지붕 아래)", "V"),
    ("facade", (2255, 700, 2850, 880), "정면 반복 A자 요소(약 5개; 개구부 후보 1, 나머지 패널/UNKNOWN)", "P"),
    ("mast", (2470, 0, 2655, 590), "마스트(지붕 위, 위끝은 화면 밖)", "V"),
    ("roof_lights", (2560, 525, 2655, 560), "지붕 위 조명 2점", "V"),
    ("annex", (2860, 595, 3295, 950), "옆 구조물(오른쪽, 작은 슬래브 지붕·기둥·조명 2점) — 본체와의 연결 UNKNOWN", "P"),
    ("rail", (1855, 820, 3840, 905), "가장자리 난간 + 등 기둥(본체 앞을 가림)", "V"),
    ("deck_edge", (1855, 900, 3840, 1050), "판 측면(오른쪽으로 내려감 = 원근 또는 기울기, UNKNOWN)", "P"),
    ("under_mass", (1855, 1000, 3520, 1300), "상판 아래 어두운 덩어리(암반/구조 경계 UNKNOWN, 오른쪽 끝 아래 용암)", "U"),
    ("left_post", (1840, 800, 1900, 1300), "왼쪽 끝 세로 부재(아래로 이어짐)", "P"),
]
COL = {"V": (90, 230, 120), "P": (250, 200, 80), "U": (240, 110, 210)}
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 30); FB = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 40)
ref = cv2.cvtColor(cv2.imread(os.path.join(FR, "11206.jpg")), cv2.COLOR_BGR2GRAY)
tpl = ref[560:920, 2000:2960]
shifts = {}
for n in (11198, 11203, 11206, 11209):
    g = cv2.cvtColor(cv2.imread(os.path.join(FR, f"{n}.jpg")), cv2.COLOR_BGR2GRAY)
    r = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
    dx, dy = loc[0] - 2000, loc[1] - 560; shifts[n] = {"dx": int(dx), "dy": int(dy), "score": round(float(mx), 3)}
    im = Image.open(os.path.join(FR, f"{n}.jpg")).convert("RGB"); a = np.power(np.asarray(im).astype(float) / 255, 0.6)
    im = Image.fromarray((a * 255).astype("uint8")); dr = ImageDraw.Draw(im)
    for key, (x0, y0, x1, y1), text, lv in REGIONS:
        b = (x0 + dx, y0 + dy, x1 + dx, y1 + dy); dr.rectangle(b, outline=COL[lv], width=5)
        w = dr.textlength(text, font=FT); tx, ty = b[0] + 6, b[1] + 6 if key not in ("mast",) else b[1] + 60
        if key in ("rail",): ty = b[1] - 40
        if key in ("under_mass",): ty = b[3] - 46
        dr.rectangle((tx - 4, ty - 2, tx + w + 4, ty + 36), fill=(0, 0, 0)); dr.text((tx, ty), text, font=FT, fill=COL[lv])
    dr.rectangle((0, 0, 3840, 56), fill=(0, 0, 0))
    dr.text((10, 6), f"{n}  시설 원거리 — 초록 VERIFIED / 노랑 PROBABLE / 자홍 UNKNOWN   (11206 기준 영역을 평행이동 dx {dx}, dy {dy}, 일치도 {mx:.2f})", font=FB, fill=(255, 255, 255))
    im.save(os.path.join(OUT, f"S_{n}_regions.png"))
json.dump({"regions_11206": [{"key": k, "box": b, "label": t, "level": l} for k, b, t, l in REGIONS], "shifts": shifts},
          open(os.path.join(HERE, "far_view_regions.json"), "w"), ensure_ascii=False, indent=1)
sheet = Image.new("RGB", (1920 * 2, 800 * 2))
for i, n in enumerate((11198, 11203, 11206, 11209)):
    sheet.paste(Image.open(os.path.join(OUT, f"S_{n}_regions.png")).resize((1920, 800)), ((i % 2) * 1920, (i // 2) * 800))
sheet.save(os.path.join(OUT, "S_4frames_regions.png")); print(shifts)
