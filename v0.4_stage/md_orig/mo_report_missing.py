"""누락 재질 목록 — 추출본(duel_mus_both.obj/.mtl)에서 질감 연결이 없는 재질을 기록한다(대체·새 디자인 없음).
입력: mo01 보고 json, 추출 인벤토리 json(재질 이름·삼각형 수·이미지 연결). 출력: Markdown.
실행: python3 mo_report_missing.py <mo01_import_report.json> <duel_mus_both_inventory.json> <duel_mus_both.obj> <출력 .md>
"""
import json, os, sys
import numpy as np

rep = json.load(open(sys.argv[1], encoding="utf-8")); inv = json.load(open(sys.argv[2], encoding="utf-8"))
mats = [dict(name=k, **v) for k, v in inv["materials"].items()]       # 인벤토리 순서 = OBJ 재질 번호 순서(material_N ↔ N번째)
for i, m in enumerate(mats):
    m["mtl"] = f"material_{i}"
# 착륙장 영역(원본 u) 안 삼각형 수를 OBJ에서 직접 센다
REG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mo_regions.json"), encoding="utf-8"))["region"]
V = []; cnt = {}; cur = None; facev = []
for line in open(sys.argv[3], encoding="latin1"):
    if line.startswith("v "):
        V.append([float(t) for t in line.split()[1:4]])
    elif line.startswith("usemtl"):
        cur = line.split()[1]
    elif line.startswith("f "):
        idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
        for k in range(1, len(idx) - 1):
            facev.append((cur, idx[0], idx[k], idx[k + 1]))
V = np.array(V)
for cur, a, b, c in facev:
    ctr = (V[a] + V[b] + V[c]) / 3
    if all(REG[0][i] <= ctr[i] <= REG[1][i] for i in range(3)):
        cnt[cur] = cnt.get(cur, 0) + 1
for m in mats:
    m["in_region"] = cnt.get(m["mtl"], 0)
grey = sorted([m for m in mats if not m["image"]], key=lambda m: -m["triangles"])
tot = sum(m["triangles"] for m in mats); gt = sum(m["triangles"] for m in grey)
L = ["# 누락 재질 목록 (원본 복원 문제 — 임의 대체 없음)", "",
     "추출 모델 `duel_mus_both.obj`(SHA256 `%s`)의 재질 %d개 중 **%d개**에 질감 연결이 없다(삼각형 %d / %d = %.0f%%)." % (rep["sha256"]["duel_mus_both.obj"][:16] + "…", len(mats), len(grey), gt, tot, 100 * gt / tot),
     "경로 이름(vjun·imperial·cairn·musend2 등)은 추출 패키지에 이미지가 들어 있지 않은 질감이다(전달 README: 일부 공유 재질은 원본 게임의 다른 패키지에 있을 수 있다). 착륙장 영역 안 삼각형 수는 OBJ에서 직접 센 값이다.",
     "렌더에서는 추출본이 준 기본 재질(회색/흰색 확산)로 나온다. **원래 색이 아니다.** 새로 만든 질감으로 바꾸지 않았다. 원본 기본 자료의 해당 질감을 받으면 같은 이름으로 연결만 하면 된다.", "",
     "| 재질(엔진 셰이더 경로) | OBJ 재질 | 삼각형 전체 | 착륙장 영역 안 |", "|---|---|---:|---:|"]
for m in grey:
    L.append("| `%s` | `%s` | %d | %d |" % (m["name"], m["mtl"], m["triangles"], m["in_region"]))
L += ["", "연결된 재질(질감 파일 있음) %d개는 원본 질감 그대로 입혔다. 질감 파일이 디스크에 없는 경우: %s." % (len(mats) - len(grey), rep["missing_texture_file"] or "없음"),
      "", "※ 이 목록은 mo01(원본 가져오기) 결과다. 이후 단계(게임 맞춤·내보내기)는 재질을 바꾸지 않는다(용암 질감만 같은 그림을 발광으로 쓴다)."]
open(sys.argv[4], "w", encoding="utf-8").write("\n".join(L) + "\n")
print(len(grey), gt, tot)
