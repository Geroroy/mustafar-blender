"""착륙장 잠정 정리 — 핵심 비교 이미지: A3b / A3를 아이소메트릭 전체와 영화 구도(11748·11726) 렌더로 나란히(렌더는 CR-009 그대로, 새 렌더 없음).
실행 (저장소 루트): python3 research/CR-001_4k_evidence/verify/compose_provisional.py <영화 없는 출력 png> [<영화 겹침 출력 png(비공개)>]"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
V = os.path.join(ROOT, "chatgpt_reviews", "CR-009_v0.3", "views")
F = os.path.join(ROOT, "research", "CR-001_4k_evidence", "_private", "cr009_film")
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 22)
NOTE = {"A3b": ["A3b — 임시 작업 기준 추천(영화 확정 아님)", "+ 11748 가림 3/3, 두 프레임 독립 위치 단서와 일치",
                "− 11726 바깥 발치가 상자에 가림(영화: 보임), 문턱 접근 0.68 m, 상자 끝 가정 +0.34 m"],
        "A3": ["A3 — 대안 보존", "+ 11726 가림 3/3, 상자 끝 가정 고정, 접근 1.17 m",
               "− 11748 +Y 문설주 발치 안 가림, 상자 끝 화소에 출입구 면, 위치 단서보다 0.7~1.0 m −Y"]}


def rows(name, film):
    i = 0 if name == "A3b" else 1
    iso = Image.open(os.path.join(V, "V_iso.png")).crop((0, i * 720 + 28, 1280, (i + 1) * 720))
    out = [iso]
    for k in ("c11748", "c11726"):
        if film:
            im = Image.open(os.path.join(F, f"F_{k}.png")); h = im.height // 3; out.append(im.crop((0, (i + 1) * h, 1280, (i + 2) * h)))
        else:
            im = Image.open(os.path.join(V, f"V_{k}.png")); h = im.height // 2; out.append(im.crop((0, i * h, 1280, (i + 1) * h)))
    return out


def sheet(film, path):
    cols = {n: rows(n, film) for n in ("A3b", "A3")}
    H = sum(r.height for r in cols["A3b"]); hdr = 110
    top = []
    if film:
        im = Image.open(os.path.join(F, "F_c11748.png")); top.append(im.crop((0, 0, 1280, im.height // 3)))
        im = Image.open(os.path.join(F, "F_c11726.png")); top.append(im.crop((0, 0, 1280, im.height // 3)))
    th = top[0].height if top else 0
    sh = Image.new("RGB", (2560, hdr + th + H), (0, 0, 0)); dr = ImageDraw.Draw(sh)
    for j, n in enumerate(("A3b", "A3")):
        for li, t in enumerate(NOTE[n]):
            dr.text((j * 1280 + 10, 6 + li * 34), t.replace("−", "-"), font=FT, fill=(255, 255, 255) if li == 0 else (220, 220, 160))
        y = hdr + th
        for r in cols[n]:
            sh.paste(r, (j * 1280, y)); y += r.height
    for j, t in enumerate(top):
        sh.paste(t, (j * 1280, hdr))
    sh.save(path); print("OUT", path, sh.size)


sheet(False, sys.argv[1])
if len(sys.argv) > 2:
    sheet(True, sys.argv[2])
