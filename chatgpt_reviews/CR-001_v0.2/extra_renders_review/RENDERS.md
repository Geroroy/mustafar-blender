# CR-001 V2~V5 — 빠른 검수용 렌더 (review 프리셋)

`../extra_renders/`(original)와 **같은 카메라·같은 숨김 객체·같은 모델**로, 해상도와 Cycles 설정만 낮춰 다시 만든 것이다.
카메라·숨긴 객체의 설명은 [`../extra_renders/RENDERS.md`](../extra_renders/RENDERS.md), 실제 값은 이 폴더의 `render_log.json`에 있다.

다시 만들기 (저장소 루트, 약 11초):
```bash
.venv-bpy/bin/python chatgpt_reviews/CR-001_v0.2/extra_renders/make_extra_views.py --preset review            # 12 samples
.venv-bpy/bin/python chatgpt_reviews/CR-001_v0.2/extra_renders/make_extra_views.py --preset review --samples 16
```

## 환경 (2026-10-15 측정)

| 항목 | 값 |
|---|---|
| CPU | Intel Xeon 2.10 GHz, **4 vCPU** (GPU 없음) |
| 메모리 | 16 GB, 스왑 없음 |
| Blender | bpy 5.2.2 LTS |
| EEVEE / Workbench | **사용 불가** — `libEGL.so.1` 없음(GPU·OpenGL 컨텍스트 없음). 시스템 패키지는 설치하지 않음 |
| 엔진 | Cycles CPU (CUDA 등 GPU 라이브러리 없음) |

## 설정 비교

| 설정 | original (v0.2 .blend 그대로) | review |
|---|---|---|
| 해상도 | 1280×720 (V4 1536×864) | **768×432** |
| 샘플 | 24, 적응형(임계 0.01) | **12**, 적응형(임계 0.02) |
| 빛 튕김 max/diffuse/glossy/transmission/transparent | 12 / 4 / 4 / 12 / 8 | **4 / 2 / 2 / 0 / 2** |
| caustics | 켬 | 끔 |
| 노이즈 제거 | OIDN, prefilter ACCURATE, 품질 HIGH | OIDN, prefilter **FAST**, 품질 **BALANCED** |
| persistent data | 끔 | **켬** (카메라만 바꾸는 연속 렌더에서 장면 데이터 재사용) |
| 스레드 | AUTO (4) | FIXED 4 (쓸 수 있는 CPU 수) |

- 모든 재질은 불투명 Principled BSDF라 유리·부피·투명 재질이 없다. 그래서 transmission·volume 튕김을 0으로 해도 결과가 같다.
- 장면 로드는 한 번만 한다. V2→V5를 같은 프로세스에서 **순서대로** 렌더한다(병렬 없음).

## 화면 범위

- V2·V3·V5: 화면 범위(ortho_scale)는 original과 같고, 픽셀만 적다.
  - V2·V3: 25.6 → 15.4 px/m
  - V5: 15.7 → 9.4 px/m
- V4: **게임 축척 28.28 px/m와 중심점을 유지**한다. 그래서 보이는 범위가 original의 절반(54 m → 27 m 폭)이다.
  인물, 계단 상자, 경사로 발치, 시설 모퉁이는 들어온다.
- 라벨·격자 글자는 해상도에 맞춰 줄였다(최소 9 px).

## 시간·메모리 (렌더만, 장면 로드 0.7초 별도)

| 프리셋 | V2 | V3 | V4 | V5 | 합계 | 최대 메모리 |
|---|---|---|---|---|---|---|
| original 24 samples | 9.8 s | 14.8 s | 31.9 s | 17.0 s | **73.5 s** | 1563 MB |
| review 8 samples | 1.0 | 1.3 | 2.6 | 1.8 | 6.7 s | 549 MB |
| **review 12 samples (이 폴더)** | 1.2 | 1.9 | 3.8 | 2.5 | **9.4 s** | 548 MB |
| review 16 samples | 1.4 | 2.3 | 5.1 | 3.3 | 12.1 s | 548 MB |

- 12 samples에서 약 **7.8배** 빨라졌고 메모리는 약 1/3이다.
- 첫 렌더(V2)가 가장 가볍다. 전체 시간은 첫 렌더의 약 6.6~7.5배다. 스크립트가 첫 렌더 직후 이 비율로 예상 시간을 출력한다.
- 품질: 노이즈가 보이지 않고, 구조 경계·격자 숫자·라벨이 읽힌다. 그래서 해상도와 샘플을 올리지 않았다.
  ChatGPT에 보낼 고해상도 판(original)은 `../extra_renders/`에 그대로 있다.
