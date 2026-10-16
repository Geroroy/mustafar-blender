"""측정 인계 묶음 생성: 측정에 쓴 무주석 4K 원본 사본 + 픽셀 대응점 표시 이미지 + SHA256 목록.
대응점 좌표는 measure/ 스크립트의 상수를 그대로 가져온다(값이 한 곳에만 있도록).
실행 (저장소 루트에서): .venv-bpy/bin/python -I research/CR-001_4k_evidence/make_handoff.py <사이트 원본 폴더> <패키지 frames 폴더>
출력: research/CR-001_4k_evidence/_private/handoff/  (영화 화면 포함 — Git 제외, .gitignore의 */_private/)"""
import hashlib
import os
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "measure"))
import m1_r2_camera_4k as m1  # noqa: E402
import m3_m4_pixels as m34    # noqa: E402

SITE, PKG = sys.argv[1], sys.argv[2]
OUT = os.path.join(HERE, "_private", "handoff")
RAW, MARK = os.path.join(OUT, "raw_4k"), os.path.join(OUT, "points")
os.makedirs(RAW, exist_ok=True); os.makedirs(MARK, exist_ok=True)
FT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F = ImageFont.truetype(FT, 26); FB = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 34)


def src(n):
    for d in (SITE, PKG):
        p = os.path.join(d, f"{n}.jpg")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(n)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def cross(dr, x, y, col, label, r=14):
    dr.line((x - r, y, x + r, y), fill=col, width=3); dr.line((x, y - r, x, y + r), fill=col, width=3)
    dr.ellipse((x - 4, y - 4, x + 4, y + 4), outline=col, width=2)
    w = dr.textlength(label, font=F); dr.rectangle((x + 16, y - 30, x + 22 + w, y - 2), fill=(0, 0, 0))
    dr.text((x + 19, y - 30), label, font=F, fill=col)


def marked(n, title, draw_fn):
    im = Image.open(src(n)).convert("RGB"); dr = ImageDraw.Draw(im)
    draw_fn(dr)
    dr.rectangle((0, 0, im.width, 46), fill=(0, 0, 0)); dr.text((10, 5), f"{n}  {title}  (4K 원본 좌표, 원본 크기)", font=FB, fill=(255, 255, 255))
    im.save(os.path.join(MARK, f"{n}_points.png"))


Y, C, G, M = (255, 230, 0), (0, 230, 255), (90, 255, 120), (255, 90, 220)
frames = set()
# M1 인물 관측
for fr in sorted({o[0] for o in m1.OBS}):
    frames.add(fr)
    def d(dr, fr=fr):
        for f_, w, u, vf, vh in m1.OBS:
            if f_ != fr:
                continue
            cross(dr, u, vf, Y, f"{w} foot ({u},{vf})"); cross(dr, u, vh, C, f"{w} head v={vh}")
            dr.line((u, vh, u, vf), fill=(255, 255, 255), width=1)
        if fr == 11615:
            for k, (u, v) in m1.PTS.items():
                if k not in ("obiwan", "anakin"):
                    cross(dr, u, v, G, f"{k} ({u},{v})")
            cross(dr, *m1.BOX_RIM, G, f"box_rim {m1.BOX_RIM}")
            for i, (u, v) in enumerate(m1.SPOTS):
                cross(dr, u, v, M, f"spot{i+1} ({u},{v})")
            for (a, b) in m1.FIN_EDGE:
                dr.line((*a, *b), fill=M, width=4); cross(dr, *a, M, f"fin top {a}"); cross(dr, *b, M, f"fin bottom {b}")
    marked(fr, "M1 대응점", d)
# M3
for fr, p in m34.FR.items():
    fr = int(fr); frames.add(fr)
    def d(dr, p=p, fr=fr):
        x_ana = 2050 if fr == 11748 else 1800
        cross(dr, x_ana, p["ana_head"], C, f"anakin head v={p['ana_head']}"); cross(dr, x_ana, p["ana_foot"], Y, f"anakin foot v={p['ana_foot']}")
        x_door = 1080 if fr == 11748 else 2570
        cross(dr, x_door, p["door_top"], G, f"door top light v={p['door_top']}"); cross(dr, x_door, p["door_floor"], G, f"door floor v={p['door_floor']}")
        sec = p["door_width_sec"]; y = sec["y"]
        dr.line((sec["x"][0], y, sec["x"][1], y), fill=M, width=4)
        cross(dr, sec["x"][0], y, M, f"width L {sec['x'][0]}"); cross(dr, sec["x"][1], y, M, f"width R {sec['x'][1]}")
        x_box = 2500 if fr == 11748 else 2200
        cross(dr, x_box, p["box_top"], Y, f"box top v={p['box_top']}"); cross(dr, x_box, p["box_floor"], Y, f"box floor v={p['box_floor']}")
    marked(fr, "M3 대응점 (x 위치는 표시용, 계산은 v만 사용)", d)
# M4
m4 = m34.m4(); frames.update([m4["frame"], *m4["cross_frames"]])
def d4(dr):
    for e in m4["facade_elements"]:
        x0, x1 = e["x"]; dr.rectangle((x0, 690, x1, 860), outline=G if "PROBABLE" in e["verdict"] else M, width=3)
        dr.text((x0, 865), e["verdict"][:12], font=ImageFont.truetype(FT, 16), fill=(255, 255, 255))
    for a, col, lab in ((m4["roof_px"], C, "roof"), (m4["body_px"], Y, "body")):
        yy = 600 if lab == "roof" else 680
        dr.line((a[0], yy, a[1], yy), fill=col, width=4); cross(dr, a[0], yy, col, f"{lab} {a[0]}"); cross(dr, a[1], yy, col, f"{lab} {a[1]}")
marked(m4["frame"], "M4 정면 요소·지붕 폭", d4)

with open(os.path.join(OUT, "SHA256SUMS.txt"), "w") as fh:
    for n in sorted(frames):
        dst = os.path.join(RAW, f"{n}.jpg"); shutil.copy2(src(n), dst)
        fh.write(f"{sha(dst)}  raw_4k/{n}.jpg\n")
    for f in sorted(os.listdir(MARK)):
        fh.write(f"{sha(os.path.join(MARK, f))}  points/{f}\n")
with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
    fh.write("# CR-001 측정 인계 묶음 (비공개, Git 제외)\n\n"
             "- `raw_4k/`: 측정에 쓴 무주석 4K 원본 사본. 갤러리 원본 URL에서 받은 파일 그대로(파일명 = 갤러리 번호). 패키지 원본은 11615.\n"
             "- `points/`: 같은 원본 위에 measure/ 스크립트의 픽셀 대응점을 원본 크기로 표시한 이미지.\n"
             "- 원본 URL: https://i0.wp.com/imgs.screencaps.us/200/4k-5-revengesith/full/revengesith-4k-starwarsscreencaps.com-<번호>.jpg?ssl=1&quality=95\n"
             "- 대응점 값의 원본: `measure/m1_r2_camera_4k.py`(OBS, PTS, BOX_RIM, SPOTS, FIN_EDGE), `measure/m3_m4_pixels.py`(FR, m4).\n"
             "- 무결성: `SHA256SUMS.txt`.\n")
print("handoff:", OUT, sorted(frames))
