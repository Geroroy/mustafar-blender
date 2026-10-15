# Mustafar Landing Platform — Blender 복원 프로젝트

영화 《Star Wars: Episode III – Revenge of the Sith》(2005)의 무스타파 착륙장을 Blender Python(bpy)으로 블록아웃하고,
OpenAI GPT 독립 검수 + 사용자 승인으로 고쳐 나가는 작업 저장소. 게임 저장소(Isometric-RPG)와 분리되어 있다.

> **이 저장소는 비공개(private)로만 유지한다.** `refs/`의 영화 스틸은 저작권 자료로, 개인 참고용이다.

| 폴더 | 내용 |
|---|---|
| `refs/` | 참고 이미지: R1·R2·R3·R6 영화 스틸, R4·R5 다른 게임 재현 |
| `v0.1/` | 블록아웃 v0.1 (첫 시도, 직사각형 판) — 보존용 |
| `v0.2/` | 블록아웃 v0.2 (영화 스틸 카메라 맞춤 측정 반영) — 현재 기준 |
| `v0.2/work/` | R2 카메라 맞춤 측정 스크립트·결과(`r2_*.py`, `r2_*.json`) |
| `gpt_review_bridge/` | GPT 검수 연동 모듈 (README 참고) |

각 버전 폴더: `create_mustafar.py`(생성 스크립트), `dimensions.json`(치수·신뢰도), `.blend`, 렌더 PNG, `reference_analysis.md`.

복원·재실행 절차: **[RESTORE.md](RESTORE.md)**
