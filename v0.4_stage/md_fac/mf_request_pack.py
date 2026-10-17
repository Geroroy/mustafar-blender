"""MF 질감 요청서 — duel_mustafar(Movie Duels 시설 맵) 추출본에서 질감 연결이 없는 재질 16개의 생성 요청 묶음을 만든다.
md_orig의 MUSTAFAR_MISSING_TEXTURES_REQUEST와 같은 구성: 표(csv)·README·GPT 요청문 + 위치 지도·현재 화면·기존 질감 시트(있으면).
16개는 모두 맵 오브젝트(MD3) 질감이다(베이더 셔틀 부품 4·화물 상자·레일 램프 2·조명 기구 7·파란 그라데이션·잠금 표시): 원본은 모델에 펼친
UV 아틀라스지만 UV 배치를 모르므로 이음새 없는 재질 타일로 대신한다(게임 카메라 28 px/m에서는 충분).
실행: python3 -I v0.4_stage/md_fac/mf_request_pack.py <shaders.json(material_N→shader)> <uv.json(uv_tile.py)> <출력 폴더(_private 안)> [--idmap png] [--current jpg] [--style jpg]
"""
import csv, json, math, os, shutil, sys

SH, UV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
assert "_private" in os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)
sh = json.load(open(SH, encoding="utf-8")); uv = json.load(open(UV, encoding="utf-8"))
opt = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
PXM = 57.0  # 리마스터 화면 밀도(px/m)
DESC = {
    "models/map_objects/mustafar/vader-parts": ("베이더 람다급 셔틀의 부품(다리·경첩·배관): 어두운 회색 금속, 패널·볼트·배선", False),
    "models/map_objects/mustafar/vader-cockpit": ("셔틀 조종석 외피: 회백색 선체 패널에 검은 창틀 띠, 패널 이음선", False),
    "models/map_objects/mustafar/vader-hullmap": ("셔틀 선체: 회백색 매끈한 선체 패널, 얇은 이음선·약한 그을음(용암 열기)", False),
    "models/map_objects/mustafar/vader-wings": ("셔틀 날개: 회백색 패널, 가장자리 어두운 띠, 긴 패널 분할", False),
    "models/map_objects/factory/s_crate_01": ("공장 화물 상자 측면: 어두운 회녹색 금속 상자, 모서리 보강재·손잡이 홈·경고 띠 없음", False),
    "models/map_objects/rail/lamp": ("레일 조명등 갓: 어두운 금속 틀에 밝은 유백색 발광면", True),
    "models/map_objects/rail/lamp_pole": ("레일 조명등 기둥: 어두운 금속 기둥, 세로 홈", False),
    "models/map_objects/vjun/block_light": ("베이더 성 계열 블록 조명: 검은 금속 블록에 흰 발광 슬릿", True),
    "models/map_objects/cairn/utilitylight_face": ("작업등 발광면: 흰·연노랑 발광(틀 없음)", True),
    "models/map_objects/cairn/utilitylight": ("작업등 본체: 어두운 금속 갓", False),
    "models/map_objects/cairn/light_wall": ("벽 조명 기구: 금속 틀 + 흰 발광 띠", True),
    "models/map_objects/imp_mine/minelamp_on": ("광산 조명(켜짐): 금속 갓에 밝은 주황빛 발광면", True),
    "models/map_objects/cairn/light": ("천장 조명 기구: 금속 틀 + 흰 발광면", True),
    "models/map_objects/cairn/lightfaces": ("조명 발광면: 흰 발광(틀 없음)", True),
    "textures/plasma_mustafar/blue_gradient": ("파란 그라데이션(홀로그램·계기판 빛): 위 밝은 하늘색 → 아래 짙은 파랑, 세로 그라데이션", True),
    "textures/cairn/lock01open": ("잠금 표시등 '열림': 어두운 패널에 초록 표시등 하나", True),
}
def pow2(v):
    return int(2 ** max(6, min(10, round(math.log2(max(1.0, v))))))
rows = []
for m, d in sorted(uv.items(), key=lambda kv: -kv[1]["area_m2"]):
    s = sh[m]["shader"]; desc, em = DESC.get(s, ("(설명 없음)", False))
    tw, th = d["tile_m"]
    w, h = pow2(tw * PXM), pow2(th * PXM)
    name = s.replace("/", "__") + (".png" if "gradient" in s else ".jpg")
    rows.append(dict(no=len(rows) + 1, priority="A(화면 큼)" if d["area_m2"] >= 20 else "B(작음·발광)" if em else "B(작음)", shader=s, output_file=name,
                     size_px=f"{w}x{h}", tile_m=f"{tw} x {th}", tileable="예(사방 이음새 없이 반복)", emissive="예" if em else "", area_total_m2=d["area_m2"],
                     tris=d["tris"], horizontal_share=d["horizontal_share"], height_m=f"{d['z_m'][0]}~{d['z_m'][1]}", obj_material=m, description_guess=desc))
with open(os.path.join(OUT, "textures_spec.csv"), "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
tbl = "\n".join(f"| {r['no']} | `{r['output_file']}` | {r['size_px']} | {r['tile_m']} | {r['emissive']} | {r['description_guess']} |" for r in rows)
readme = f"""# MUSTAFAR_FACILITY_TEXTURES_REQUEST — 빠진 질감 16개 생성 요청서 (Movie Duels 시설 맵 `duel_mustafar`)

## 배경
- 게임에 넣을 두 번째 Movie Duels 무스타파 맵: `duel_mustafar`(분리주의자 학살 임무의 맵 — 착륙장·보행로·제어실·회의실·발코니·다리·수집 팔). 형상은 원본 그대로 쓴다.
- 추출본의 재질 84개 중 **16개**에 질감 이미지가 없다(삼각형 5,688 / 101,248 = 5.6%). 모두 맵에 박힌 오브젝트(베이더 셔틀, 화물 상자, 램프·조명 기구)의
  질감이다. 원본 이미지는 구할 수 없어 **AI로 대체 질감을 만든다**(결과물은 원본이 아니다. 맵에 연결할 때도 그렇게 기록한다).
- 앞서 받은 30개(`MUSTAFAR_TEXTURES_GEN.zip`)는 이 맵에선 쓰이지 않는 재질이라 겹치지 않는다. 그 30개 중 이 맵에도 있는 재질은 이미 연결돼 있다.

## 들어 있는 파일
| 파일 | 내용 |
|---|---|
| `GPT_PROMPT.txt` | GPT에게 그대로 붙여 넣을 요청문 |
| `textures_spec.csv` | 16개 표: 파일 이름, 크기, 한 장의 실제 크기, 발광 여부, 면적, 수평면 비율, 높이, OBJ 재질 이름, 설명(이름으로 추정) |
| `ID_MAP_missing_textures.png` | (있으면) 게임 카메라 위치 지도. 색 = 빠진 재질(범례 번호 = 표 번호), 회색 = 질감이 이미 있는 재질 |
| `CURRENT_game_camera_full.jpg` | (있으면) 지금 게임 카메라 모습(흰색·회색 면이 빠진 질감) |
| `STYLE_REF_existing_textures.jpg` | (있으면) 같은 맵의 기존 질감(색감·디테일 참고) |

## 숫자는 어떻게 쟀나
- **한 장의 실제 크기(m)**: 원본 모델의 UV에서 질감 좌표 1.0(그림 한 장)이 실제로 몇 m인지를 면적 가중 중앙값으로 쟀다. 오브젝트 질감은 원래 UV 아틀라스(모델 전체를
  한 장에 펼친 것)라 "한 장 = 모델 둘레"에 가깝다. UV 배치를 모르므로 **이음새 없는 재질 타일**로 대신 그린다 — 게임 카메라(28 px/m)에서는 재질감만 보인다.
- **크기(px)**: 리마스터 화면 밀도(약 57 px/m)로 한 장을 덮는 2의 거듭제곱(64~1024).
- 설명은 엔진 경로 이름으로 **추정**한 것이다(vader = 베이더 셔틀, cairn/vjun/imp_mine/rail = 제국 시설 계열 조명·구조물). 원본 그림을 본 것이 아니다.

## 표
| # | 만들 파일 이름 | 크기(px) | 한 장의 실제 크기(m, 가로×세로) | 발광 | 무엇인지(이름으로 추정) |
|---|---|---|---|---|---|
{tbl}

## 받은 뒤 할 일 (Claude Code)
1. 파일 이름·크기·이음새를 검사한다.
2. 원본 MTL은 고치지 않고, 별도 연결표(`mf_gentex_map.json`)로 재질에 붙인다. 발광 표시 재질은 밝은 부분만 발광으로 처리한다.
3. 맵 전체를 한 번 렌더해(CPU 2~3시간) 게임에 넣고 실제 게임에서 확인한다. 형상은 바꾸지 않는다.

## 보안·권리
위치 지도·현재 화면·기존 질감 시트에는 Movie Duels(제3자) 자산이 들어 있다. 공개 GitHub나 공개 링크에 올리지 않는다.
"""
open(os.path.join(OUT, "README_TEXTURE_REQUEST.md"), "w", encoding="utf-8").write(readme)
prompt = """첨부한 MUSTAFAR_FACILITY_TEXTURES_REQUEST.zip을 열고 README_TEXTURE_REQUEST.md를 먼저 읽어라.

Star Wars 무스타파 시설 게임 맵(Jedi Academy 계열 Movie Duels 맵 duel_mustafar를 그대로 쓴 것)에서 질감 파일이 빠진 재질 16개의 대체 질감 이미지를 새로 만들어라.
모두 맵에 박힌 오브젝트(베이더 람다급 셔틀, 화물 상자, 램프·조명 기구, 표시등)의 질감이다. 원본 파일은 구할 수 없다. 원본을 흉내 내거나 다른 게임의 이미지를 복사하지 말고, 이름과 설명에 맞는 새 그림을 그려라.

규칙:
1. 파일 이름·크기는 textures_spec.csv 그대로. 이름이 하나라도 다르면 게임에 연결되지 않는다.
2. 모두 사방 이음새 없이 반복되는 타일 질감(seamless). 표의 '한 장의 실제 크기(m)'만큼을 한 장에 담는다.
3. 위에서 비추는 고른 빛 기준의 색 그림(albedo). 강한 그림자·하이라이트·원근을 넣지 않는다. 글자·로고·숫자 금지.
4. 분위기: 2003년 PC 게임(Jedi Academy) 질감 수준. 셔틀 4종(vader-*)은 회백색 선체 패널(같은 셔틀이라 네 장의 색·패널 느낌을 맞출 것), 상자·기둥·조명 틀은 어둡고 낡은 산업 금속(회흑·청회색, 약한 녹·그을음). 색감은 STYLE_REF_existing_textures.jpg가 있으면 그것에 맞춘다.
5. 발광 표시가 있는 조명 질감은 밝은 발광 부분과 어두운 틀을 함께 그린다(발광 부분은 흰색 또는 표시 색: minelamp_on은 주황, lock01open은 초록, blue_gradient는 파랑). utilitylight_face·lightfaces는 틀 없이 발광면만.
6. blue_gradient는 PNG: 위 밝은 하늘색 → 아래 짙은 파랑 세로 그라데이션, 가로로는 이음새 없이.
7. 어디에 쓰이는지는 ID_MAP_missing_textures.png(색 = 해당 재질 위치)와 CURRENT_game_camera_full.jpg(지금 모습, 흰색·회색 = 빠진 질감)가 있으면 본다.
8. 우선순위: A(면적 큼: 상자·셔틀·광산 조명) → B. 다 못 하면 A만 먼저.

결과: 이미지 파일을 정확한 이름으로 담은 MUSTAFAR_FACILITY_TEXTURES_GEN.zip 하나와, 파일마다 크기·이음새 여부·무엇을 그렸는지 한 줄씩 적은 TEXTURES_GEN_NOTES.md를 함께 줘라.
"""
open(os.path.join(OUT, "GPT_PROMPT.txt"), "w", encoding="utf-8").write(prompt)
for k, name in (("--idmap", "ID_MAP_missing_textures.png"), ("--current", "CURRENT_game_camera_full.jpg"), ("--style", "STYLE_REF_existing_textures.jpg")):
    if opt(k):
        shutil.copyfile(opt(k), os.path.join(OUT, name))
print("pack", OUT, len(rows), "rows")
