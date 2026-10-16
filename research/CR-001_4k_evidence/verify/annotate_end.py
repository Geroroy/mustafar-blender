"""CR-008 영화 표시: 낮은 상자 −Y 끝 부위(P1 테두리 끝, P2 솟은 블록 시작, P3 솟은 블록 끝, P4 끝 단 윗면, P5 바닥 접점)와 윤곽.
상태: 초록 실선 원 = 직접 보임, 노랑 원 = 추정, 회색 글자 = 가려짐·화면 밖. 보라 × = 이전(M5·M9·M10)에 '윗테두리 −Y 끝'으로 쓴 점.
좌표는 measure/m11_box_end.py의 END 상수(영화 없이 커밋). 영화 화면이 들어간 출력은 _private에만 둔다.
실행: <bpy python> -I annotate_end.py <4K 원본 폴더> <출력 폴더>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "measure"))
from m11_box_end import END  # noqa: E402

OUTLINE = {   # 윤곽(직접 보이는 구간만)
    "11246": {"main_rim": [(2445, 895), (3170, 1025)], "raised_top": [(3255, 1000), (3620, 1080)], "tiers": [(3620, 1080), (3840, 1000), (3840, 1470), (3760, 1490)]},
    "11726": {"main_rim": [(1700, 1012), (2555, 1015)], "raised_top": [(2595, 978), (2835, 1012)], "tiers": [(2835, 1012), (2900, 1110), (2990, 1185), (3000, 1235)]},
    "11748": {"main_rim": [(100, 1083), (365, 1084)], "raised_top": [(450, 1033), (775, 1075)], "tiers": [(775, 1075), (830, 1133), (905, 1135), (975, 1283)]},
}
OLD = {"11246": [(3220, 1000)], "11726": [(2560, 1008)], "11748": [(790, 1062), (425, 1078)]}
NAMES = {"P1": "테두리 끝", "P2": "솟은 블록 시작", "P3": "솟은 블록 끝", "P4": "끝 단 윗면", "P5": "바닥 접점"}


def main():
    fr, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    ft = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 30)
    crops = {"11246": (2300, 750, 3840, 1560), "11726": (1500, 850, 3200, 1350), "11748": (0, 950, 1100, 1450)}
    for f, items in END.items():
        im = Image.open(os.path.join(fr, f"{f}.jpg")).convert("RGB")
        a = np.power(np.asarray(im).astype(float) / 255, 0.6); im = Image.fromarray((a * 255).astype("uint8"))
        dr = ImageDraw.Draw(im)
        ol = OUTLINE[f]
        dr.line(ol["main_rim"], fill=(80, 200, 255), width=5); dr.line(ol["raised_top"], fill=(255, 140, 0), width=6); dr.line(ol["tiers"], fill=(255, 80, 200), width=5)
        for q in OLD[f]:
            dr.line((q[0] - 14, q[1] - 14, q[0] + 14, q[1] + 14), fill=(190, 90, 255), width=5); dr.line((q[0] - 14, q[1] + 14, q[0] + 14, q[1] - 14), fill=(190, 90, 255), width=5)
        notes = []
        for part, st, px, desc in items:
            if px is None:
                notes.append(f"{part} {NAMES[part]}: {st} — {desc}"); continue
            col = (60, 255, 90) if st == "direct" else (255, 230, 60)
            r = 13; dr.ellipse((px[0] - r, px[1] - r, px[0] + r, px[1] + r), outline=col, width=5)
            dr.text((px[0] + 14, px[1] - 44), part, font=ft, fill=col)
            notes.append(f"{part} {NAMES[part]} ({st}) {px}: {desc}")
        x0, y0, x1, y1 = crops[f]; im = im.crop(crops[f])
        import textwrap
        leg = ["하늘색 선 = 주 테두리 근면 윗모서리, 주황 선 = 솟은 블록 근면 윗모서리, 분홍 선 = 끝 단 윤곽",
               "초록 원 = 직접 보임, 노랑 원 = 추정, 보라 × = 이전에 '윗테두리 −Y 끝'으로 쓴 점(서로 다른 부위였음)"]
        lines = [w for t in leg + notes for w in textwrap.wrap(t.replace("−", "-"), max(20, im.width // 31))]
        H = 40 * len(lines) + 20; sh = Image.new("RGB", (im.width, im.height + H), (0, 0, 0)); sh.paste(im, (0, 0)); d2 = ImageDraw.Draw(sh)
        for k, t in enumerate(lines):
            d2.text((16, im.height + 10 + 40 * k), t, font=ft, fill=(235, 235, 235))
        sh.save(os.path.join(out, f"A_end_{f}.jpg"), quality=90)
    print("OUT", list(END))


if __name__ == "__main__":
    main()
