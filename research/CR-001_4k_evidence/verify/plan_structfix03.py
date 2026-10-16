"""구조 수정 3차(A3e) 평면도: 위에서 본 렌더(지붕·처마·위 몸체 숨김) 위에 바뀐 외곽 / 보행 영역 / 열린 틈 / R / 문 / 외부 통로(SIDE) / 미확정 경계를 구분해 표시.
보행 영역은 내보낸 게임 충돌 마스크(out/mustafar_landing/collision.png)를 그대로 겹친다(그림이 아닌 실제 데이터).
실행(저장소 루트): .venv-bpy/bin/python research/CR-001_4k_evidence/verify/plan_structfix03.py <출력 png>"""
import json, os, sys
import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTP = sys.argv[-1]
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
L = D["v03"]["entrance_layout"]["candidates"]["A3e"]
ST = json.load(open(os.path.join(ROOT, "v0.4_stage", "out", "mustafar_landing", "stage.json"), encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "v0.3", "work", "layouts", "layout_A3e.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
for o in bpy.data.objects:
    o.hide_render = o.name in ("Hangar_Roof", "Hangar_Spotlights", "Lava_Level_Ref", "Hangar_Bay_Shell", "Entrance_Housing", "Entrance_Outer_Frame") or o.name.startswith("Outline_Alt") or any(m.type == 'WIREFRAME' for m in o.modifiers)
for c in bpy.data.collections:
    c.hide_render = c.name.startswith("Hypothesis") or c.name in ("Scale_Check", "Placeholders", "Platform_Corner_Markers", "Platform_Outline_Range")
CX, CY, S, W, H = 6.5, -3.5, 58.0, 1100, 1300
cd = bpy.data.cameras.new("PLAN"); cd.type = 'ORTHO'; cd.ortho_scale = S; cd.sensor_fit = 'VERTICAL'
cam = bpy.data.objects.new("PLAN", cd); sc.collection.objects.link(cam); cam.location = (CX, CY, 80); sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = W, H
tmp = OUTP + ".raw.png"; sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)

from PIL import Image, ImageDraw, ImageFont
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 17); FB = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 21)
k = H / S
px = lambda X, Y: (W / 2 + (X - CX) * k, H / 2 - (Y - CY) * k)
im = Image.open(tmp).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
# 보행 영역: 게임 충돌 마스크(초록)
c = ST["collision"]; m = np.array(Image.open(os.path.join(ROOT, "v0.4_stage", "out", "mustafar_landing", "collision.png"))) > 0
OX, OY = ST["offset"]["OX"], ST["offset"]["OY"]
for j in range(c["rows"]):
    for i in range(c["cols"]):
        if m[j, i]:
            gx, gy = c["gx0"] + (i + 0.5) * c["cell"], c["gy0"] + (j + 0.5) * c["cell"]
            X, Y = OY - gy, OX - gx
            a = px(X - c["cell"] / 2, Y + c["cell"] / 2); b = px(X + c["cell"] / 2, Y - c["cell"] / 2)
            dr.rectangle((a[0], a[1], b[0], b[1]), fill=(40, 230, 90, 70))
# 열린 틈(빨강): 판 가장자리 ↔ 시설 벽, 진입 바닥·외부 통로 제외
X1, XW = 14.5, 22.5
EYC, XE = L["center_y"], L["front_x"]; WB = L["entry_contour"]["wing_base_half"]
SW = L["side_walkway"]; FY0, FY1 = L["facility_front_y"], 19.5
def rect(x0, y0, x1, y1, fill, outline, w=3):
    a, b = px(x0, y1), px(x1, y0); dr.rectangle((a[0], a[1], b[0], b[1]), fill=fill, outline=outline, width=w)
def text(X, Y, t, col=(255, 255, 255), f=FT):
    x, y = px(X, Y); tw = dr.textlength(t, font=f); dr.rectangle((x - tw / 2 - 4, y - 11, x + tw / 2 + 4, y + 13), fill=(0, 0, 0, 210)); dr.text((x - tw / 2, y - 10), t, font=f, fill=col)
rect(X1, EYC + WB, XW, SW["y"][0], (255, 60, 40, 60), (255, 80, 60, 255))
rect(X1, FY0, XW, EYC - WB, (255, 60, 40, 60), (255, 80, 60, 255))
# 바뀐 외곽(노랑)
P = [px(*q) for q in L["pad_outline"]["poly"]]
dr.line(P + [P[0]], fill=(255, 220, 40, 255), width=4)
# R(주황 테두리), 문(노랑 칸), 외부 통로(하늘색), 미확정 경계(보라 점선)
R = L["r_structure"]; rect(R["x"][0], R["y"][0], R["x"][1], R["y"][1], None, (255, 150, 40, 255), 3)
ex = ST["exit"]
rect(OY - ex["y1"], OX - ex["x1"], OY - ex["y0"], OX - ex["x0"], (80, 160, 255, 120), (80, 160, 255, 255), 2)
rect(SW["x"][0], SW["y"][0], SW["x"][1], SW["y"][1], None, (90, 220, 255, 255), 3)
for (xa, ya, xb, yb) in ((SW["end_x"], SW["y"][0] - 0.5, SW["end_x"], SW["y"][1] + 0.5), (XE + 5.0, EYC - 1.3, XE + 5.0, EYC + 1.3)):
    a, b = px(xa, ya), px(xb, yb)
    for t in range(0, 12, 2):
        dr.line((a[0] + (b[0] - a[0]) * t / 12, a[1] + (b[1] - a[1]) * t / 12, a[0] + (b[0] - a[0]) * (t + 1) / 12, a[1] + (b[1] - a[1]) * (t + 1) / 12), fill=(220, 120, 255, 255), width=5)
text(18.5, 3.0, "열린 틈 — 아래 용암 (바닥 없음)", (255, 170, 160))
text(18.5, EYC - WB - 0.7, "열린 틈", (255, 170, 160))
text(XE - 1.5, EYC + 3.4, "진입 바닥", (150, 255, 170)); text(XE + 0.45, EYC - 0.2, "문", (170, 210, 255))
text(R["x"][0] - 3.0, sum(R["y"]) / 2, "R (확장부 위)", (255, 190, 110))
text(19.5, (SW["y"][0] + SW["y"][1]) / 2, "외부 통로 SIDE", (140, 230, 255)); text(SW["end_x"] - 1.0, SW["y"][0] - 1.0, "작업 경계(너머 UNKNOWN)", (230, 160, 255))
text(XE + 5.0, EYC - 2.0, "통로 끝(너머 UNKNOWN)", (230, 160, 255))
text(-12.5, -22.2, "앞 바깥 모서리 절삭", (255, 230, 120)); text(-12.5, 20.6, "뒤 바깥 모서리 절삭", (255, 230, 120)); text(7.0, -31.2, "측면 확장(R 수용)", (255, 230, 120))
text(25.5, -6.0, "베이 1~3(시설 안, 바닥 -3 m)", (170, 200, 255))
dr.rectangle((0, 0, W, 32), fill=(0, 0, 0, 230)); dr.text((10, 4), "A3e 평면(지붕 숨김) — 노랑 외곽 / 초록 = 실제 보행 칸(게임 충돌) / 빨강 = 열린 틈 / 보라 점선 = 미확정 경계", font=FB, fill=(255, 255, 255))
x0, y0 = px(-15.0, -29.0); dr.line((x0, y0, x0 + 5 * k, y0), fill=(255, 255, 255, 255), width=4); dr.text((x0 + 5 * k + 6, y0 - 11), "5 m", font=FT, fill=(255, 255, 255))
Image.alpha_composite(im, ov).convert("RGB").save(OUTP); os.remove(tmp); print("OUT", OUTP)
