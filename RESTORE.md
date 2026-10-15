# 복원 절차 — 새 Claude Code 세션

클라우드 세션 컨테이너는 끝나면 사라진다. 이 저장소만 있으면 아래 순서로 작업 환경을 되살릴 수 있다.
Claude Code에게 "RESTORE.md대로 복원해 줘"라고 하면 된다.

## 0. 준비물

- 이 저장소(비공개)에 대한 GitHub 접근 — 세션에 저장소를 추가(add_repo)하거나 세션 생성 때 선택.
- 네트워크: PyPI(`pypi.org`, `files.pythonhosted.org`)는 기본 허용. GPT 실제 호출에는 `api.openai.com` 허용 필요(3단계부터).
- 비밀정보: GPT 실제 호출에만 `OPENAI_API_KEY` (환경 설정의 Network secrets 또는 환경 변수). 복원·모의 시험에는 필요 없음.

## 1. 저장소 받기

```bash
git clone https://github.com/<소유자>/<저장소>.git ~/mustafar-blender
cd ~/mustafar-blender
git log --oneline | head -3
```
(Git LFS를 쓰지 않으므로 `git lfs pull`은 필요 없다.)

## 2. 가상환경 두 개 (저장소 안 `.venv-*` — .gitignore로 제외됨)

```bash
uv venv -q -p 3.13 .venv-bpy
VIRTUAL_ENV=$PWD/.venv-bpy uv pip install bpy==5.2.2          # 공식 Blender 모듈, 약 400 MB, 1분 안팎
uv venv -q -p 3.13 .venv-bridge
VIRTUAL_ENV=$PWD/.venv-bridge uv pip install -r gpt_review_bridge/requirements.txt
```
확인:
```bash
.venv-bpy/bin/python -c "import bpy; print(bpy.app.version_string)"      # 5.2.2 LTS
.venv-bridge/bin/python -c "import openai; print(openai.__version__)"    # 3.31.0
```
- bpy 5.2.2는 Python 3.13 전용. `uv`가 없으면 `python3.13 -m venv` + `pip install`.
- 이 컨테이너에는 `libEGL`이 없어 EEVEE·Workbench가 안 된다 → 스크립트는 Cycles CPU로 렌더한다(시스템 패키지는 설치하지 않음).

## 3. 검수 모듈 모의 시험 (API 호출 없음)

```bash
cd gpt_review_bridge
../.venv-bridge/bin/python review.py check              # 키 등록 여부·SDK·api.openai.com 연결 (과금 없음)
SELFTEST_TMP=/tmp ../.venv-bridge/bin/python tests/test_flow.py
```
기대 결과: `결과: 31/31 통과`. 시험은 임시 사본에서 돌고 실제 `v0.2/`와 `reviews/`를 바꾸지 않는다
(마지막 항목 "실제 v0.2 파일은 시험 전후 동일"이 이를 확인).

## 4. (선택) 블록아웃 재생성 확인 — 반드시 사본에서

`create_mustafar.py`는 **자기 폴더의 .blend와 렌더를 덮어쓴다.** 보존 버전 폴더에서 직접 실행하지 않는다.
```bash
T=$(mktemp -d); cp -r v0.2 "$T/v0.2"; ln -s "$PWD/refs" "$T/refs"
.venv-bpy/bin/python "$T/v0.2/create_mustafar.py"       # 약 1분 30초 (렌더 5장)
```
`$T/v0.2/compare_R2.png`를 저장소의 `v0.2/compare_R2.png`와 비교한다. 2026-10-15 같은 환경(bpy 5.2.2, Cycles CPU)에서
백업 파일만으로 재생성한 결과 렌더 3장이 원본과 픽셀까지 같았다(평균 차이 0.00). bpy 버전이나 CPU가 다르면 노이즈 수준의 차이가 날 수 있다.

## 5. 버전 규칙

- 보존된 버전 폴더(`v0.1/`, `v0.2/` …)는 고치지 않는다. 수정은 `gpt_review_bridge/approval.py new-version`으로
  만든 새 폴더에서, 사용자가 승인한 항목만.
- 커밋 전 확인: `git status`에 `.venv-*`, `costs.jsonl`, `*.blend1`, `reviews/*/prepared/`가 나오지 않아야 한다.

## 6. 용량 — Git LFS를 쓰지 않는 이유

- 지금 가장 큰 파일은 `refs/R6_film_facility_wide.gif` 10.4 MB, `.blend`는 0.1~0.2 MB. GitHub의 파일당 경고(50 MB)·차단(100 MB)과
  거리가 멀다. 백업 전체 약 30 MB.
- LFS는 별도 저장·전송 한도가 있고, 복원 때 `git lfs` 설치·`pull`이 하나 더 늘어난다.
- 다시 검토할 때: `.blend`가 수십 MB로 커지거나, 버전마다 렌더가 쌓여 저장소가 수백 MB에 가까워질 때.
  그때는 `git lfs track "*.blend"`(새 파일부터) 또는 오래된 렌더를 GitHub Release 첨부로 옮기는 방법을 쓴다.
