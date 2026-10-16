"""제출 비교판 묶기(PIL). 렌더·게임 화면을 짝지어 한 장으로. 이미지마다 무엇·어디서 나왔는지 적는다.
실행: .venv-bpy/bin/python v0.4_stage/md_remake/md06_sheets.py <md_remake_v2 폴더> <출력 폴더>
"""
import os, sys

from PIL import Image, ImageDraw, ImageFont

V2, OUT = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(OUT, exist_ok=True)
FT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
F, FB = ImageFont.truetype(FT, 20), ImageFont.truetype(FT, 26)


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def sheet(title, cols, out, w=900, note=None):
    """cols: [(캡션, 이미지 경로)] 가로로 나란히."""
    ims = [fit(Image.open(p).convert("RGB"), w) for _, p in cols]
    h = max(i.height for i in ims); top = 50 + (30 if note else 0)
    S = Image.new("RGB", (w * len(ims) + 10 * (len(ims) + 1), h + top + 40), (16, 18, 22)); d = ImageDraw.Draw(S)
    d.text((12, 10), title, font=FB, fill=(240, 240, 240))
    if note:
        d.text((12, 46), note, font=F, fill=(190, 200, 210))
    for k, ((cap, _), im) in enumerate(zip(cols, ims)):
        x = 10 + k * (w + 10); S.paste(im, (x, top)); d.text((x + 4, top + h + 8), cap, font=F, fill=(255, 220, 120))
    S.save(out); print("sheet", out, S.size)


A, B, G = os.path.join(V2, "A_source"), os.path.join(V2, "B_remake"), os.path.join(V2, "C_gamecam")
# A/B 전후 짝: 같은 시점(원본 좌표 → 같은 변환)
for k, n in ((1, "region_top"), (2, "front_oblique_A"), (3, "front_oblique_B"), (4, "front_noship")):
    sheet(f"A→B {k:02d} {n}: Movie Duels 원본 영역 → MD_REMAKE_POC01 리메이크(같은 시점)",
          [("A 수정 전: duel_mus_both.obj 원본(02_models.zip)", os.path.join(A, f"A_source_duel_mus_both_{k:02d}_{n}.png")),
           ("B 수정 후: 형상 확인(같은 중립 조명)", os.path.join(B, f"B_remake_layout_{k:02d}_{n}.png")),
           ("B 수정 후: 게임용 재질·조명", os.path.join(B, f"B_remake_stage_{k:02d}_{n}.png"))],
          os.path.join(OUT, f"AB_{k:02d}_{n}.png"), w=760)
# 영역 선택: 두 맵의 착륙장·시설 정면
sheet("영역 선택: 두 맵의 착륙장·시설 정면(합치지 않음 — 하나만 선택)",
      [("duel_mustafar: 닫힌 평벽 + 닫힌 A판 문 2개, 지붕·베이·틈 없음", os.path.join(A, "A_source_duel_mustafar_02_front_oblique_A.png")),
       ("duel_mus_both(선택): 처마 등·열린 베이·경사 기둥·사다리꼴 입구·옆 통로", os.path.join(A, "A_source_duel_mus_both_02_front_oblique_A.png"))],
      os.path.join(OUT, "A_select_two_maps.png"), w=900)
# C: 같은 게임 카메라
sheet("C 같은 게임 카메라(직교 30°/45°, 28.284 px/m, 같은 게임 좌표 OX 96·OY 95.5, 같은 화면 범위)",
      [("기존 A3e (mustafar_landing_stage_A3e.blend)", os.path.join(G, "C_gamecam_A3e_full.png")),
       ("MD_REMAKE_POC01 (Movie Duels duel_mus_both 기반)", os.path.join(G, "C_gamecam_POC_full.png"))],
      os.path.join(OUT, "C_01_same_game_camera_full.png"), w=1100)
sheet("C 같은 게임 카메라·같은 배율, 출입구 중심(배치마다 출입구 위치가 다름)",
      [("기존 A3e 출입구", os.path.join(G, "C_gamecam_A3e_entrance.png")), ("MD_REMAKE_POC01 출입구", os.path.join(G, "C_gamecam_POC_entrance.png"))],
      os.path.join(OUT, "C_02_same_game_camera_entrance.png"), w=900)
PA = os.path.join(ROOT, "v0.4_stage", "renders", "play_A3e"); PP = os.path.join(V2, "play")
for n, (a, b, t) in enumerate(((("01_start.png", "01_start.png", "시작 위치")), ("06b_inside_door.png", "08_in_passage.png", "출입구 안"),
                                ("08f_walkway_end.png", "10_walkway_occlusion.png", "외부/옆 통로(시설 뒤 가림)")), 3):
    sheet(f"C 실제 게임 화면 — {t}(같은 게임 카메라, 화면은 플레이어를 따라감)",
          [(f"기존 A3e: renders/play_A3e/{a}", os.path.join(PA, a)), (f"MD_REMAKE_POC01: play/{b}", os.path.join(PP, b))],
          os.path.join(OUT, f"C_{n:02d}_game_{os.path.splitext(b)[0]}.png"), w=900)
