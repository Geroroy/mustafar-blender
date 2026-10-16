"""v0.3 바닥 판재 평면 검증: 판끼리 면적이 겹치지 않는지, 덮는 면적이 판 영역과 같은지.
입력: v0.3/work/floor_plates.json (create_mustafar.py가 기록, 이음매 inset 전 다각형)
방법: ① 판 넓이 합 vs (판 영역 − 구멍) 넓이 (구멍이 없으면 판 영역 전체)  ② 0.1 m 격자 점마다 몇 개 판에 들어가는지 세기(0 = 빈틈, 2 이상 = 겹침)
     ③ 육각 판 넓이와 반복 단위 넓이 비교. 평면도 PNG도 만든다(판 경계와 겹침 표시).
실행: python3 check_floor_tiling.py [floor_plates.json] [out.png]"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "v0.3", "work", "floor_plates.json")
d = json.load(open(src)); P = d["plates_before_seam"]; HW, HS, HP = d["hex"]; x0, y0, x1, y1 = d["clip"]
# 구멍 없음(None)이면 판 영역 = 자르기 사각형 전체. 낮은 상자 정정(2026-10-16) 뒤 기본안은 구멍이 없다
HOLE = d.get("hole"); hx0, hy0, hx1, hy1 = HOLE if HOLE else (0.0, 0.0, 0.0, 0.0)


def area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2


def inside(pt, p):
    x, y = pt; c = False
    for i in range(len(p)):
        (xa, ya), (xb, yb) = p[i - 1], p[i]
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            c = not c
    return c


region = (x1 - x0) * (y1 - y0) - max(0, min(x1, hx1) - max(x0, hx0)) * max(0, min(y1, hy1) - max(y0, hy0))
tot = sum(area(p) for p in P)
hex_area = HW * HS + HW * HP; cell = (HW / 2) * 2 * (HS + HP)
step = 0.1; counts = {0: 0, 1: 0, 2: 0}; over_pts = []
boxes = [(min(q[0] for q in p), max(q[0] for q in p), min(q[1] for q in p), max(q[1] for q in p)) for p in P]
y = y0 + step / 2
while y < y1:
    x = x0 + step / 2
    while x < x1:
        if not (hx0 < x < hx1 and hy0 < y < hy1):
            n = sum(1 for p, b in zip(P, boxes) if b[0] <= x <= b[1] and b[2] <= y <= b[3] and inside((x, y), p))
            counts[min(n, 2)] += 1
            if n >= 2: over_pts.append((x, y))
        x += step
    y += step
res = {"plates": len(P), "hex_area_m2": round(hex_area, 3), "repeat_cell_area_m2": round(cell, 3),
       "hex_over_cell": round(hex_area / cell, 3), "sum_plate_area_m2": round(tot, 2), "region_area_m2": round(region, 2),
       "area_ratio": round(tot / region, 4), "grid_step_m": step,
       "grid_points_uncovered": counts[0], "grid_points_single": counts[1], "grid_points_overlap": counts[2]}
print(json.dumps(res, ensure_ascii=False))
json.dump(res, open(os.path.join(HERE, "floor_tiling_result.json"), "w"), ensure_ascii=False, indent=1)
if len(sys.argv) > 2:
    from PIL import Image, ImageDraw
    k = 20; W, H = int((x1 - x0) * k) + 40, int((y1 - y0) * k) + 40
    im = Image.new("RGB", (W, H), (30, 30, 30)); dr = ImageDraw.Draw(im)
    tr = lambda q: (20 + (q[0] - x0) * k, H - 20 - (q[1] - y0) * k)
    for i, p in enumerate(P):
        dr.polygon([tr(q) for q in p], fill=(150, 150, 150) if i % 2 else (115, 115, 120), outline=(255, 255, 255))
    if HOLE:
        dr.rectangle([tr((hx0, hy1)), tr((hx1, hy0))], outline=(255, 200, 0), width=2)
    for q in over_pts[::5]:
        X, Y = tr(q); dr.rectangle((X - 1, Y - 1, X + 1, Y + 1), fill=(255, 0, 0))
    dr.text((24, 4), f"plates {len(P)}  hex/cell {res['hex_over_cell']}  area ratio {res['area_ratio']}  overlap pts {counts[2]}  gaps {counts[0]}  (+X right, +Y up)", fill=(255, 255, 0))
    im.save(sys.argv[2])
