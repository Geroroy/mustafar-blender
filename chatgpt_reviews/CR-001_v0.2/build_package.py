"""CR-001 ChatGPT 전달용 ZIP을 만든다 (저장소 파일만 읽음, 원본 무변경).

실행 (저장소 루트에서, Pillow가 있는 파이썬):
    .venv-bridge/bin/python chatgpt_reviews/CR-001_v0.2/build_package.py

결과: chatgpt_reviews/CR-001_v0.2/CR-001_v0.2_for_ChatGPT.zip  (.gitignore 대상 — 영화 스틸이 들어 있으므로
비공개 저장소 밖으로 옮기지 말 것)
"""
import io
import os
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "CR-001_v0.2_for_ChatGPT.zip")
X = "chatgpt_reviews/CR-001_v0.2/extra_renders/"

DOCS = [
    ("request.md", "chatgpt_reviews/CR-001_v0.2/request.md"),
    ("images.md", "chatgpt_reviews/CR-001_v0.2/images.md"),
    ("RENDERS.md", X + "RENDERS.md"),
    ("TEMPLATE_review.md", "chatgpt_reviews/TEMPLATE_review.md"),
    ("v0.2_dimensions.json", "v0.2/dimensions.json"),
    ("v0.2_reference_analysis.md", "v0.2/reference_analysis.md"),
]
ATTACH_1 = [
    ("01_compare_R2.png", "v0.2/compare_R2.png"),
    ("02_compare_R6.png", "v0.2/compare_R6.png"),
    ("03_isometric_view.png", "v0.2/isometric_view.png"),
    ("04_top_view.png", "v0.2/top_view.png"),
    ("05_V2_section.png", X + "V2_section_facility_side.png"),
    ("06_V3_facility_front.png", X + "V3_facility_wall_front.png"),
    ("07_V4_game_scale.png", X + "V4_game_scale_crop.png"),
    ("08_V5_iso_no_roof.png", X + "V5_game_iso_no_roof.png"),
]
ATTACH_2 = [
    ("09_perspective_view.png", "v0.2/perspective_view.png"),
    ("10_R2_film.jpg", "refs/R2_film_lecture.jpg"),
    ("11_R3_film.jpg", "refs/R3_film_lies.jpg"),
    ("12_R6_film_frame43.png", ("refs/R6_film_facility_wide.gif", 43)),
    ("13_R1_film.jpg", "refs/R1_film_wide.jpg"),
    ("14_R4_other_game.jpg", "refs/R4_game_hangar.jpg"),
    ("15_R5_other_game.jpg", "refs/R5_game_platform.jpg"),
]

READ_FIRST = """# CR-001 — ChatGPT 전달 방법 (Blender v0.2 검수)

이 ZIP에는 영화 원본 스틸이 들어 있다. 개인 검수용으로만 쓰고 다른 곳에 올리지 않는다.

## 순서
1. ChatGPT 새 대화를 연다.
2. **첫 메시지:** `request.md`, `images.md`, `RENDERS.md`를 첨부하고, `attach_1/`의 이미지 8장을 첨부한다.
   본문에는 이렇게 적는다.
   "첨부한 request.md대로 검수해 줘. 이미지는 두 번에 나눠 보낼게. 두 번째 묶음을 받은 뒤에 답해 줘."
3. **두 번째 메시지:** `attach_2/`의 이미지 7장(영화 스틸·다른 게임 포함)과 `v0.2_dimensions.json`, `v0.2_reference_analysis.md`를 첨부한다.
   본문에는 이렇게 적는다.
   "이제 전부 보냈어. request.md 6절 형식으로 답해 줘."
4. 답을 그대로 복사해 저장소의 `chatgpt_reviews/CR-001_v0.2/chatgpt_review.md`로 저장한다.
   Claude Code에 붙여 넣고 "저장해 줘"라고 해도 된다.

한 번에 첨부할 수 있는 파일 수가 더 적으면 번호 순서대로 나눠 보낸다. 번호 이름과 저장소 경로의 대응은 request.md 7절에 있다.
`TEMPLATE_review.md`는 request.md 6절과 같은 내용이라 따로 첨부하지 않아도 된다.
"""


def add_file(z, arc, src):
    if isinstance(src, tuple):                                        # GIF 한 프레임 → PNG
        path, frame = src
        im = Image.open(os.path.join(ROOT, path)); im.seek(frame)
        buf = io.BytesIO(); im.convert("RGB").save(buf, "PNG")
        z.writestr(arc, buf.getvalue())
    else:
        z.write(os.path.join(ROOT, src), arc)


with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("00_READ_FIRST.md", READ_FIRST)
    for arc, src in DOCS:
        add_file(z, arc, src)
    for arc, src in ATTACH_1:
        add_file(z, "attach_1/" + arc, src)
    for arc, src in ATTACH_2:
        add_file(z, "attach_2/" + arc, src)

with zipfile.ZipFile(OUT) as z:
    for i in z.infolist():
        print(f"{i.file_size / 1e6:7.2f} MB  {i.filename}")
print(f"ZIP: {OUT}  {os.path.getsize(OUT) / 1e6:.1f} MB")
