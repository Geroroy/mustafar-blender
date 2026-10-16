"""CR-006 영화 표시: 11726·11748에서 ① 낮은 상자의 양 끝과 외곽 ② 출입구 양옆 문설주와 문턱 ③ 상자 옆으로 드러나는 바닥
④ 시설 쪽 가장자리와 틈의 보이는 경계 (+ 모델에 없는 다른 낮은 구조물)를 함께 표시한다. 좌표는 4K px, 확대 격자 판독(±5~20 px).
영화 화면이 들어가므로 출력은 _private에만 둔다. 좌표 자체(아래 상수)는 영화 없이 커밋한다.
실행: <bpy python> -I annotate_access.py <4K 원본 폴더> <출력 폴더>"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

C = {"box": (255, 160, 0), "door": (60, 210, 255), "floor": (60, 230, 90), "edge": (255, 60, 200), "other": (255, 240, 60)}
MARKS = {
    11748: [
        ("box", "poly", [(0, 1078), (340, 1078), (430, 1032), (600, 1035), (790, 1062), (830, 1130), (900, 1135), (975, 1275), (900, 1300), (850, 1382), (0, 1388)],
         "① 낮은 상자 L: 외곽·−Y 끝 단(오른쪽 끝). +Y 끝은 화면 밖"),
        ("door", "line", [(735, 820), (740, 1222)], "② +Y 문설주(아래쪽은 상자 L 끝 단에 가림)"),
        ("door", "line", [(1325, 828), (1352, 1222)], "② −Y 문설주"),
        ("door", "line", [(960, 1222), (1352, 1222)], "② 문턱(밝은 바닥 → 어두운 통로 바닥)"),
        ("floor", "fill", [(975, 1282), (985, 1224), (1450, 1226), (1650, 1280), (1560, 1450), (900, 1450), (880, 1330)],
         "③ 상자 L 끝 옆으로 드러나 문턱까지 이어지는 바닥(판 이음매가 문턱까지 이어짐)"),
        ("edge", "line", [(2800, 1262), (3340, 1300)], "④ 상자 R 너머 바닥 끝(용암 경계) — 앞 변으로 보임"),
        ("edge", "poly", [(3340, 1240), (3650, 1250), (3670, 1375), (3350, 1340)], "④ 가장자리 연석"),
        ("other", "poly", [(1750, 1030), (2100, 1035), (2300, 1012), (2450, 1015), (2785, 1060), (2795, 1258), (2000, 1275), (1750, 1270)],
         "다른 낮은 구조물 R(사다리꼴 구획, +Y 끝은 인물에 가림) — 모델에 없음"),
        ("edge", "text", [(1000, 1180)], "④ 문턱 앞: 틈 경계 안 보임"),
    ],
    11726: [
        ("box", "poly", [(1580, 1010), (2555, 1010), (2560, 975), (2600, 975), (2880, 1000), (2990, 1180), (2990, 1240), (2960, 1292), (1580, 1296)],
         "① 낮은 상자 A: 외곽·−Y 끝(솟았다가 단으로 낮아짐). +Y 끝은 인물에 가림"),
        ("door", "point", [(2590, 322)], "② 출입구 꼭대기 조명"),
        ("door", "point", [(3000, 1168)], "② 바깥 테두리 −Y 발치"),
        ("door", "text", [(2280, 940)], "② 문턱·+Y 문설주 발치: 상자 A에 가림"),
        ("floor", "fill", [(2990, 1186), (3380, 1182), (3840, 1205), (3840, 1320), (2960, 1300)], "③ 상자 A −Y 끝 옆으로 드러나는 바닥"),
        ("edge", "line", [(300, 1170), (900, 1172)], "④ 바닥–벽 밑동 선(위에 주황 띠 v 1000~1170: 틈 PROBABLE)"),
        ("edge", "line", [(3330, 1180), (3560, 1185)], "④ 바닥 끝 위로 용암이 보임"),
        ("other", "poly", [(3380, 1080), (3840, 1060), (3840, 1200), (3380, 1190)], "다른 낮은 구조물 B(11748의 R과 같아 보임) — 모델에 없음"),
    ],
}


def main():
    fr, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    ft = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 34)
    for n, marks in MARKS.items():
        im = Image.open(os.path.join(fr, f"{n}.jpg")).convert("RGB")
        a = np.power(np.asarray(im).astype(float) / 255, 0.6); im = Image.fromarray((a * 255).astype("uint8")).convert("RGBA")
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        legend = []
        for kind, typ, pts, txt in marks:
            col = C[kind]
            if typ == "poly": dr.line(pts + [pts[0]], fill=col + (255,), width=6)
            elif typ == "fill": dr.polygon(pts, fill=col + (80,), outline=col + (255,))
            elif typ == "line": dr.line(pts, fill=col + (255,), width=7)
            elif typ == "point":
                x, y = pts[0]; dr.ellipse((x - 16, y - 16, x + 16, y + 16), outline=col + (255,), width=6)
            k = len(legend) + 1; x, y = pts[0]
            dr.rectangle((x + 6, y - 46, x + 52, y - 6), fill=(0, 0, 0, 200)); dr.text((x + 12, y - 44), str(k), font=ft, fill=col + (255,))
            legend.append((col, f"{k}. {txt}"))
        im = Image.alpha_composite(im, ov).convert("RGB")
        H = 46 * len(legend) + 20; sheet = Image.new("RGB", (im.width, im.height + H), (0, 0, 0)); sheet.paste(im, (0, 0)); d2 = ImageDraw.Draw(sheet)
        for k, (col, t) in enumerate(legend):
            d2.text((20, im.height + 10 + 46 * k), t.replace("−", "-"), font=ft, fill=col)
        sheet.save(os.path.join(out, f"A_{n}_access_marks.jpg"), quality=90)
    json.dump({str(k): [{"kind": a, "type": b, "pts": c, "text": d} for a, b, c, d in v] for k, v in MARKS.items()},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_marks.json"), "w"), ensure_ascii=False, indent=1)
    print("OUT", list(MARKS))


if __name__ == "__main__":
    main()
