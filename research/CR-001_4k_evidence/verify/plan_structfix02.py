"""구조 수정 2차(A3d) 평면도: 위에서 본 렌더(지붕·처마 숨김) 위에 열린 틈 / 베이 3개 / 칸막이 / 진입 바닥(판 → 문턱 → 통로)을 구분해 표시.
실행(저장소 루트): .venv-bpy/bin/python research/CR-001_4k_evidence/verify/plan_structfix02.py <출력 png>"""
import json, math, os, sys
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTP = sys.argv[-1]
D = json.load(open(os.path.join(ROOT, "v0.3", "dimensions.json"), encoding="utf-8"))
L = D["v03"]["entrance_layout"]["candidates"]["A3d"]
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "v0.3", "work", "layouts", "layout_A3d.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
for o in bpy.data.objects:
    o.hide_render = o.name in ("Hangar_Roof", "Hangar_Spotlights", "Lava_Level_Ref", "Hangar_Bay_Shell") or o.name.startswith("Outline_Alt") or any(m.type == 'WIREFRAME' for m in o.modifiers)
for c in bpy.data.collections:
    c.hide_render = c.name.startswith("Hypothesis") or c.name in ("Scale_Check", "Placeholders", "Platform_Corner_Markers", "Platform_Outline_Range")
CX, CY, S, W, H = 16.0, -4.0, 50.0, 1000, 1400
cd = bpy.data.cameras.new("PLAN"); cd.type = 'ORTHO'; cd.ortho_scale = S; cd.sensor_fit = 'VERTICAL'
cam = bpy.data.objects.new("PLAN", cd); sc.collection.objects.link(cam); cam.location = (CX, CY, 80); sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = W, H
tmp = OUTP + ".raw.png"; sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)

from PIL import Image, ImageDraw, ImageFont
FT = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18); FB = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 22)
k = H / S
px = lambda X, Y: (W / 2 + (X - CX) * k, H / 2 - (Y - CY) * k)
im = Image.open(tmp).convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
X1, XW = 14.5, 22.5
ED = L["entrance_dims"]; EW = ED["width"]
EYC, XE = L["center_y"], L["front_x"]; HB = L["wing"]["base_half"]
HBY = L["hangar_bays"]; PY = HBY["partition_y"]; PWB = HBY["base_half"]; PBX = HBY["back_x"]
FY0, FY1 = L["facility_front_y"], 19.5


def rect(x0, y0, x1, y1, fill, outline, w=3):
    a, b = px(x0, y1), px(x1, y0); dr.rectangle((a[0], a[1], b[0], b[1]), fill=fill, outline=outline, width=w)


def text(X, Y, t, col=(255, 255, 255), f=FT):
    x, y = px(X, Y); tw = dr.textlength(t, font=f); dr.rectangle((x - tw / 2 - 4, y - 12, x + tw / 2 + 4, y + 14), fill=(0, 0, 0, 200)); dr.text((x - tw / 2, y - 11), t, font=f, fill=col)


rect(X1, FY0, XW, EYC - HB, (255, 60, 40, 70), (255, 80, 60, 255))            # 열린 틈(진입 바닥 −Y 쪽)
rect(X1, EYC + HB, XW, FY1, (255, 60, 40, 70), (255, 80, 60, 255))            # 열린 틈(+Y 쪽)
rect(X1, EYC - HB, XE - 0.39, EYC + HB, (60, 220, 90, 110), (60, 255, 90, 255))     # 진입 바닥(판 가장자리 → 문틀 앞)
rect(XE - 0.39, EYC - EW / 2, XE + 1.0, EYC + EW / 2, (60, 220, 90, 150), (255, 230, 60, 255), 3)   # 문틀 안 진입 바닥(개구부 폭)
for b in range(3):                                                            # 베이(바닥 높이 기준, 칸막이 사이)
    rect(XW, PY[b] + PWB, PBX, PY[b + 1] - PWB, (60, 120, 255, 80), (90, 150, 255, 255))
    text(XW + 3.5, (PY[b] + PY[b + 1]) / 2, f"베이 {b + 1}", (170, 200, 255), FB)
for y in PY:                                                                  # 칸막이 밑동
    rect(HBY["front_x_base"], y - PWB, PBX, y + PWB, (200, 200, 200, 90), (235, 235, 235, 255), 2)
text(18.5, 3.0, "열린 틈 — 아래 용암 (바닥 띠 없음)", (255, 170, 160))
text(19.5, EYC - HB - 0.7, "열린 틈", (255, 170, 160))
text(18.6, EYC - HB - 2.2, "진입 바닥 (판 → 문턱 → 통로)", (150, 255, 170))
text(XW + 3.5, PY[0] - 2.2, "칸막이 밑동(위로 넓어짐·기울어짐)", (235, 235, 235))
text(XE + 0.4, EYC, "문", (255, 240, 120))
text(12.8, -15.0, "낮은 상자", (255, 220, 200)); text(13.0, -22.9, "R", (255, 220, 200))
dr.rectangle((0, 0, W, 34), fill=(0, 0, 0, 230)); dr.text((10, 5), "A3d 평면(지붕 숨김): 열린 틈 / 베이 3개 / 진입 바닥. 높이: 판 0 m, 베이 -3 m(형태용)", font=FB, fill=(255, 255, 255))
x0, y0 = px(6.0, -24.0); dr.line((x0, y0, x0 + 5 * k, y0), fill=(255, 255, 255, 255), width=4); dr.text((x0 + 5 * k + 6, y0 - 12), "5 m", font=FT, fill=(255, 255, 255))
Image.alpha_composite(im, ov).convert("RGB").save(OUTP); os.remove(tmp); print("OUT", OUTP)
