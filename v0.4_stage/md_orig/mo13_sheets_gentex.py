"""MO-13 생성 대체 질감 전후 비교판(PIL). mo12_views.py가 같은 카메라로 찍은 BEFORE/AFTER와 실제 게임 화면 전후를 짝지어 묶는다.
모드 형상이 들어간 이미지이므로 출력은 비공개 폴더(_private)에만 둔다(커밋 금지). 순서: 왼쪽 = 수정 전(질감 없음, 흰/회색), 오른쪽 = 생성 질감 연결 후.
실행: python3 -I v0.4_stage/md_orig/mo13_sheets_gentex.py <views 폴더> <게임 전 폴더> <게임 후 폴더> <출력 폴더(_private 안)>
"""
import os, sys

from PIL import Image, ImageDraw, ImageFont

V, GB, GA, OUT = sys.argv[1:5]
assert "_private" in os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)
FT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
F, FB = ImageFont.truetype(FT, 20), ImageFont.truetype(FT, 26)
L0, L1 = "수정 전(질감 없음 = 흰색·회색)", "생성 대체 질감 연결 후"


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def row(pairs, w):
    ims = [fit(Image.open(p).convert("RGB"), w) for _, p in pairs]; h = max(i.height for i in ims)
    R = Image.new("RGB", (w * len(ims) + 10 * (len(ims) + 1), h + 34), (16, 18, 22)); d = ImageDraw.Draw(R)
    for k, ((cap, _), im) in enumerate(zip(pairs, ims)):
        x = 10 + k * (w + 10); R.paste(im, (x, 0)); d.text((x + 4, h + 6), cap, font=F, fill=(255, 220, 120))
    return R


def sheet(title, note, rows, out):
    Wd = max(r.width for r in rows); Ht = 80 + sum(r.height + 6 for r in rows)
    S = Image.new("RGB", (Wd, Ht), (16, 18, 22)); d = ImageDraw.Draw(S)
    d.text((12, 10), title, font=FB, fill=(240, 240, 240)); d.text((12, 46), note, font=F, fill=(190, 200, 210))
    y = 80
    for r in rows:
        S.paste(r, (0, y)); y += r.height + 6
    S.save(os.path.join(OUT, out), optimize=True); print("sheet", out, S.size)


v = lambda tag, n: os.path.join(V, f"{tag}_{n}.png")
pair = lambda n, cap="": [(f"{L0}{cap}", v("BEFORE", n)), (f"{L1}{cap}", v("AFTER", n))]
sheet("① 전체 — 같은 게임 카메라·같은 화면 범위(실행 패키지 배경 범위)", "직교 30°/45°, 28.284 px/m. 형상·UV·카메라·조명은 그대로이고 질감 없던 재질 30개에만 생성 대체 질감을 붙였다.",
      [row(pair("game_full"), 1100)], "S1_full_game_before_after.png")
sheet("② 암벽(musend2/terrain_0·terrain_1·terrain_0to1)", "위: 게임 카메라 같은 배율 일부. 아래: 근사 원근 근접(판 서쪽 가장자리에서 서쪽 암벽).",
      [row(pair("game_rocks"), 760), row(pair("persp_rocks"), 900)], "S2_rocks_before_after.png")
sheet("③ 시설 벽·지붕(vjun/basemetal4·basemetal1, imperial/wall_6, vjun/vader_trim2_mask, imp_mine/blastshield)", "위: 게임 카메라 같은 배율 일부. 아래: 판 위에서 시설 정면(근사 원근).",
      [row(pair("game_facility_roof"), 900), row(pair("persp_facade_roof"), 900)], "S3_facility_roof_before_after.png")
sheet("④ 받침 기둥(vjun/vader_floor2_mask)", "위: 게임 카메라 같은 배율 일부(판 아래). 아래: 판 아래 근사 원근. 붉은 기는 용암 반사광이며 질감 색이 아니다.",
      [row(pair("game_pillars"), 760), row(pair("persp_pillars"), 900)], "S4_pillars_before_after.png")
sheet("⑤ 조명(impdetention/light_white·light_blue, hoth/light_ceiling)", "위: 판 가장자리·옆 통로 조명 띠(게임 카메라 일부). 아래: 처마 밑·베이 천장 조명(근사 원근). 밝은 광원부만 발광, 틀은 일반 재질.",
      [row(pair("game_pad_edge_lights"), 900), row(pair("persp_eave_lights"), 900)], "S5_lights_before_after.png")
sheet("⑥ 유리(common/glass, PNG 알파 90/255)", "시설 뒤 먼 다리의 창(게임 화면에는 거의 안 보임, 근사 원근 근접).",
      [row(pair("persp_glass"), 900)], "S6_glass_before_after.png")
gm = [("v01_start_original_mode.png", "시작 위치"), ("v02_under_ship.png", "우주선 아래"), ("v03_pad_tip.png", "판 끝"), ("v04_walkway_end.png", "옆 통로 끝")]
sheet("⑦ 실제 게임 화면 — 같은 자동 조작·같은 위치(오리지널 그래픽)", "왼쪽 = 실행 패키지(게임 커밋 1633ff9 데이터), 오른쪽 = 같은 빌드에 생성 질감판 맵 데이터 6개만 바꿔 넣음. 카메라는 플레이어를 따라감.",
      [row([(f"{L0} · {t}", os.path.join(GB, f)), (f"{L1} · {t}", os.path.join(GA, f))], 900) for f, t in gm], "S7_ingame_before_after.png")
