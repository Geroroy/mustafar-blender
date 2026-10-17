"""ART01-9 재질 목록 표 — art_materials.json(분류·근거) + 점검 결과(audit.json: 셰이더 경로·원본 질감 유무·화면 픽셀)로 Markdown 표를 만든다.
실행: python3 v0.4_stage/md_art01/art09_material_table.py <audit.json> <출력 md>
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUD, OUT = sys.argv[1:3]
spec = json.load(open(os.path.join(HERE, "art_materials.json"), encoding="utf-8"))
aud = json.load(open(AUD, encoding="utf-8"))["materials"]
tot = sum(v["visible_px_game_cam_1x"] for v in aud.values())
rows = []
for k, a in spec["materials"].items():
    m = aud[k]; vis = m["visible_px_game_cam_1x"]
    rows.append((vis, k, m["shader"], "있음" if m["image"] else "**없음(누락)**", m["tris"], f"{100 * vis / tot:.2f}%" if vis else "0 (화면 밖)", a["class"], a.get("mask") or "—", a.get("note", "")))
rows.sort(key=lambda r: (-r[0], r[1]))
L = ["| 재질 | 원본 셰이더 경로 | 원본 질감 | 삼각형 | 게임 화면 비율(1배) | 새 분류 | 원본 UV로 쓰는 배치 마스크 | 근거·메모 |", "|---|---|---|---:|---:|---|---|---|"]
for r in rows:
    L.append("| " + " | ".join(str(x) for x in r[1:]) + " |")
cls = ["| 분류 | 종류 | 기준 반사율(선형) | 금속성 | 거칠기 | 설명 |", "|---|---|---|---:|---:|---|"]
for k, c in spec["classes"].items():
    base = c.get("base") or c.get("color") or c.get("crust")
    cls.append(f"| `{k}` | {c['kind']} | {base} | {c.get('metal', '—')} | {c.get('rough', '—')} | {c.get('_doc', '')} |")
open(OUT, "w", encoding="utf-8").write("# ART01 재질 목록\n\n자동 생성: `art09_material_table.py` (art_materials.json + audit.json). 화면 비율 = 게임 카메라 1배 배경 범위에서 그 재질이 실제로 보이는 픽셀 비율(조각 포함, 가림 반영).\n\n## 분류(하나의 그래픽 기준)\n\n" + "\n".join(cls) + "\n\n## 재질 89개\n\n" + "\n".join(L) + "\n")
print("OK", OUT, len(rows))
