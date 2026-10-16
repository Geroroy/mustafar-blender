"""11726 대응점 표시(영화 화면 → _private). 범주별 색: 처마 조명·지지부·출입구(꼭대기·어깨·문턱)·계단 상자·바닥선.
관측점과 M5 최적 카메라로 투영한 모델 점을 함께 그린다. 대응 불가 항목은 이름만 표시.
실행: .venv-bpy/bin/python -I research/CR-001_4k_evidence/verify/annotate_11726.py <11726.jpg> <출력.png>"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "measure"))
import m5_11726_camera as m5  # noqa: E402

res = json.load(open(os.path.join(HERE, "..", "measure", "m5_result.json")))
best = [r for r in res["fits"] if r["geometry"] == "model"][0]
import math
cam = (*best["cam"]["xyz"], math.radians(best["cam"]["yaw_deg"]), math.radians(best["cam"]["pitch_deg"]), best["f"])
im = Image.open(sys.argv[1]).convert("RGB")
a = np.power(np.asarray(im).astype(float) / 255, 0.6); im = Image.fromarray((a * 255).astype("uint8")); dr = ImageDraw.Draw(im)
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 34); FS = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 28)
C = {"eave": (255, 230, 0), "fin": (255, 140, 0), "door": (0, 230, 255), "box": (120, 255, 120), "deck": (255, 90, 220), "model": (255, 60, 60)}


def mark(p, col, text, r=18):
    x, y = p; dr.ellipse((x - r, y - r, x + r, y + r), outline=col, width=5)
    w = dr.textlength(text, font=FS); dr.rectangle((x + 22, y - 36, x + 30 + w, y - 2), fill=(0, 0, 0)); dr.text((x + 26, y - 36), text, font=FS, fill=col)


mark(m5.OBS["eave_light_A"], C["eave"], "처마 조명 A"); mark(m5.OBS["eave_light_B"], C["eave"], "처마 조명 B")
dr.line((650, 400, 520, 1150), fill=C["fin"], width=6); dr.text((660, 380), "지지부(대응 모호, 맞춤 제외)", font=FS, fill=C["fin"])
mark(m5.DOOR_OBS["door_light"], C["door"], "출입구 꼭대기 조명(H1 평가)")
mark(m5.DOOR_OBS["door_outer_base_right"], C["door"], "출입구 바깥 테두리 밑(H1 평가)")
dr.text((2420, 440), "안쪽 평평한 윗변 — 모델 대응 없음", font=FS, fill=C["door"])
dr.text((2380, 900), "어깨점 — 이 프레임에서 판독 불가", font=FS, fill=C["door"])
dr.text((2380, 1060), "문턱 — 상자에 가림", font=FS, fill=C["door"])
pts = m5.OBS["box_top_near_edge"]; dr.line((*pts[0], *pts[-1]), fill=C["box"], width=6); dr.text((1620, 950), "상자 근면 윗모서리", font=FS, fill=C["box"])
mark(m5.OBS["box_top_right_end"], C["box"], "상자 윗모서리 −Y 끝(±40)")
mark(m5.OBS["box_base_near_edge"][0], C["box"], "상자 밑변")
dr.text((1380, 1340), "상자 +Y 끝 — 인물에 가림", font=FS, fill=C["box"])
dl = m5.OBS["deck_edge_far"]; dr.line((*dl[0], *dl[1]), fill=C["deck"], width=6); dr.text((200, 1190), "바닥–벽 밑동 선", font=FS, fill=C["deck"])
# M5 카메라로 투영한 모델 점
for y in m5.SPOTS_Y:
    p, d = m5.proj((m5.SPOT_X, y, m5.SPOT_Z), cam)
    if d > 0 and -50 < p[0] < 3900 and -50 < p[1] < 1650: dr.rectangle((p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12), outline=C["model"], width=4); dr.text((p[0] + 14, p[1] + 10), f"모델 조명 y{y}", font=FS, fill=C["model"])
for k, q in m5.door_pts(m5.EYC).items():
    p, _ = m5.proj(q, cam); dr.rectangle((p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12), outline=C["model"], width=4); dr.text((p[0] + 14, p[1] + 10), "모델 " + ("문 조명" if k == "door_light" else "테두리 밑") + " (H1 y−16)", font=FS, fill=C["model"])
dr.rectangle((0, 0, 3840, 50), fill=(0, 0, 0))
dr.text((10, 6), f"11726 대응점 — 원: 영화 관측 / 빨강 사각: M5 최적 카메라(조명 {best['spots_AB']}, f {best['f']}, RMS {best['rms_px']} px)로 투영한 v0.3 모델 점", font=FT, fill=(255, 255, 255))
im.save(sys.argv[2])
