"""M7 — 11615 바닥 이음매 수동 표시와 모델 비교. 자동 검출(M6)은 형상 결정에 쓰지 않는다.
SEAMS: 사람이 확대 격자(50 px)에서 판 경계로 식별한 긴 선분(4K px, 판독 ±10 px). 질감·얼룩·그림자 경계는 넣지 않았다.
방법: v0.2 기준안 R2 카메라로 끝점을 바닥면(Z=0)에 역투영 → 땅 위 방향·길이. 같은 위치 부근(중점 3 m 이내)의 모델 판 변(이음매 전 다각형)을
      찾아 방향 차와 중점 수직 거리를 낸다. 모델 판 배치는 생성값이라 위치 일치는 기대하지 않으며, 방향 비교가 주목적이다.
실행: python3 m7_floor_seams_manual.py → m7_result.json  (영화 불필요)
      python3 m7_floor_seams_manual.py overlay <11615.jpg> <out.png>  (영화 위 표시, _private 전용)"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
from m6_floor_seams import ground, CAM, RIGHT, UP, FWD, F, CX, CY  # 같은 기준안 카메라

SEAMS = {  # 이름: (u0, v0, u1, v1)
    "S1": (275, 1006, 253, 1097), "S2": (200, 1300, 159, 1475), "S3": (100, 1275, 306, 1175),
    "S4": (156, 1475, 1000, 1250), "S7": (1059, 1203, 1131, 1347), "S9": (1131, 1347, 1400, 1413),
    "S10": (900, 1481, 1400, 1416), "S11": (2624, 1146, 2749, 1008), "S12": (2601, 1254, 2447, 1471),
    "S13": (2158, 1425, 2349, 1599), "S15": (2158, 1424, 2601, 1254),
}


def project(p):
    d = np.asarray(p) - CAM; return CX + F * (d @ RIGHT) / (d @ FWD), CY - F * (d @ UP) / (d @ FWD)


def model_edges():
    fp = json.load(open(os.path.join(ROOT, "v0.3", "work", "floor_plates.json")))
    E = []
    for p in fp["plates_before_seam"]:
        for i in range(len(p)):
            a, b = np.array(p[i - 1]), np.array(p[i])
            if np.linalg.norm(b - a) > 0.2: E.append((a, b))
    return E


def analyze():
    E = model_edges(); rows = []
    for k, (u0, v0, u1, v1) in SEAMS.items():
        a, b = ground(u0, v0)[:2], ground(u1, v1)[:2]
        d = b - a; L = float(np.linalg.norm(d)); ang = math.degrees(math.atan2(d[1], d[0])) % 180; mid = (a + b) / 2
        best = None
        for ea, eb in E:
            em = (ea + eb) / 2
            if np.linalg.norm(em - mid) > 3.0: continue
            ed = eb - ea; eang = math.degrees(math.atan2(ed[1], ed[0])) % 180
            dang = abs((ang - eang + 90) % 180 - 90)
            n = np.array([-ed[1], ed[0]]) / np.linalg.norm(ed); off = abs(float((mid - ea) @ n))
            if best is None or dang < best[0]: best = (dang, eang, off)
        rows.append({"seam": k, "px": [u0, v0, u1, v1], "ground_mid_xy": [round(float(c), 2) for c in mid], "ground_len_m": round(L, 2),
                     "ground_angle_deg": round(ang, 1),
                     "nearest_model_edge": None if best is None else {"angle_deg": round(best[1], 1), "angle_diff_deg": round(best[0], 1), "mid_offset_m": round(best[2], 2)}})
    angs = [r["ground_angle_deg"] for r in rows]
    res = {"camera": "v0.2 기준안 R2 카메라(11615와 같은 고정 카메라)", "angle_convention": "0°=+X(시설 쪽), 90°=+Y(절벽 쪽), 180° 주기",
           "model_edge_angles_deg": [90.0, round(math.degrees(math.atan2(1.3, 1.5)), 1), round(180 - math.degrees(math.atan2(1.3, 1.5)), 1)],
           "seams": rows, "film_angles_sorted": sorted(angs),
           "note": "모델 판 배치는 생성값 — 위치(mid_offset)는 일치 기대 대상이 아님. 수동 표시 11개, 판독 ±10 px는 먼 쪽에서 방향 오차 수 도에 해당"}
    json.dump(res, open(os.path.join(HERE, "m7_result.json"), "w"), ensure_ascii=False, indent=1)
    for r in rows: print(r["seam"], r["ground_len_m"], r["ground_angle_deg"], r["nearest_model_edge"])


def overlay(src, out):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(src).convert("RGB"); a = np.power(np.asarray(im).astype(float) / 255, 0.7); im = Image.fromarray((a * 255).astype("uint8"))
    dr = ImageDraw.Draw(im); FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 30)
    for ea, eb in model_edges():
        pa, pb = project((*ea, 0)), project((*eb, 0))
        if max(pa[1], pb[1]) > 900: dr.line((*pa, *pb), fill=(255, 70, 70), width=3)
    for k, (u0, v0, u1, v1) in SEAMS.items():
        dr.line((u0, v0, u1, v1), fill=(80, 255, 80), width=7); dr.text((u0 + 8, v0 - 34), k, font=FT, fill=(80, 255, 80))
    dr.rectangle((0, 0, 3840, 46), fill=(0, 0, 0))
    dr.text((10, 6), "11615 바닥: 초록 = 수동 표시한 판 이음매, 빨강 = v0.3 모델 판 변을 v0.2 기준안 R2 카메라로 투영(배치는 생성값)", font=FT, fill=(255, 255, 255))
    im.save(out)


if __name__ == "__main__":
    overlay(sys.argv[2], sys.argv[3]) if len(sys.argv) > 1 and sys.argv[1] == "overlay" else analyze()
