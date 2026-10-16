"""M11 — 낮은 상자 −Y 끝 형태와 대응점 정리(CR-008).
① 세 프레임(11246·11726·11748)에서 상자 −Y 끝을 부위별로 나눠 적는다. 상태: direct(직접 보임) / occluded(가려짐) / estimated(추정) / out_of_frame.
   P1 테두리 끝: 주 테두리 근면 윗모서리가 끝나고 솟기 시작하는 점
   P2 솟은 블록 시작: 솟아오른 뒤 솟은 블록 근면 윗모서리가 시작하는 점
   P3 솟은 블록 끝: 솟은 블록 근면 윗모서리가 끝나고 끝 단으로 내려가기 시작하는 점
   P4 끝 단 윗면: 끝 단(낮은 단) 윗면 근면 모서리
   P5 바닥 접점: 끝(맨 −Y)의 바닥 접점
   서로 다른 부위를 같은 모델 꼭짓점에 대응시키지 않는다. 이전(M5·M9·M10)의 '윗테두리 −Y 끝'은 프레임마다 P1(11726·11246) 또는 P3 부근(11748 이전 값)이었고,
   모두 모델의 끝 벽 모서리(y −18.5, 높이 1.2 m)에 대응시켰다 — 모델에는 솟은 블록이 없어 같은 물리적 부위가 아니었다.
② 끝 형태와 무관한 점만으로 프레임별 카메라를 맞춘다(형상 = A3 기준: 출입구 h 2.4·w 1.45, 상자 1.2 m 고정).
③ 그 카메라로 끝 부위를 역투영한다: P1~P4는 상자 근면 윗모서리 평면(x = 상자 −X 벽 바깥 − 0.06), P5는 바닥(z 0).
   결과(y 위치·높이)는 카메라·형상 가정에 의존하는 후보값이다. P1의 높이가 1.2 m와 얼마나 다른지도 함께 본다(상자 높이 일관성 점검).
실행: python3 m11_box_end.py → m11_result.json (영화 불필요)"""
import itertools, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m9_a3_shape_fit as m  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
XN = m.HX0 - 0.06                                  # 근면 윗모서리 평면

END = {   # (부위, 상태, 4K px, 설명)
    "11246": [("P1", "direct", (3170, 1025), "주 테두리 근면 윗모서리 끝(밝은 띠 아래 모서리가 꺾여 올라가는 점)"),
              ("P2", "direct", (3255, 1000), "솟은 블록 근면 윗모서리 시작"),
              ("P3", "direct", (3620, 1080), "솟은 블록 근면 윗모서리 끝, 주황 계단식 면이 시작"),
              ("P4", "direct", None, "주황 계단식 면 여러 단(오른쪽 아래로 이어짐) — 단마다 꼭짓점이 겹쳐 하나의 점으로 대응시키지 않음"),
              ("P5", "out_of_frame", None, "끝 단 바닥 접점은 화면 오른쪽 밖")],
    "11726": [("P1", "direct", (2555, 1015), "주 테두리 근면 윗모서리 끝(밝은 띠 오른쪽 끝)"),
              ("P2", "direct", (2595, 978), "솟은 블록 근면 윗모서리 시작(어두운 윤곽)"),
              ("P3", "estimated", (2835, 1012), "솟은 블록 윗모서리가 꺾여 내려가기 시작(흐림, ±25 px)"),
              ("P4", "occluded", None, "끝 단: 흐림·관 모양 밝은 구조물에 겹쳐 구분 안 됨"),
              ("P5", "estimated", (3000, 1235), "끝 바닥 접점(밝은 관에 일부 가림, ±25 px)")],
    "11748": [("P1", "direct", (365, 1084), "주 테두리 근면 윗모서리 끝"),
              ("P2", "direct", (450, 1033), "솟은 블록 근면 윗모서리 시작"),
              ("P3", "direct", (775, 1075), "솟은 블록 근면 윗모서리 끝"),
              ("P4", "direct", (868, 1133), "끝 단 윗면 근면 모서리(가운데, x 830~905)"),
              ("P5", "direct", (975, 1283), "끝 단 앞면 바닥 접점(맨 오른쪽 아래)")],
}
# 끝 형태와 무관한 맞춤 점(이전 '윗테두리 −Y 끝'·'솟은 시작'·'끝 단 발치'는 뺌)
RIM48 = [(100, 1083), (300, 1084)]                 # 11748 주 테두리 근면 윗모서리 직선(P1보다 +Y 쪽)


def res48(c, h=2.4, w=1.45):
    P = m.ent(h, w); r = []
    for k in ("door_light", "shoulder_plusY", "shoulder_minusY", "jamb_minusY_foot"):
        q, df = m.proj(P[k], c); r += list(q - m.O48[k]) if df > 0 else [1e4, 1e4]
    r += [x * 0.5 for x in m.line_res(m.O48["threshold_line"], (m.XE - m.XF0, m.EYC + 1, 0), (m.XE - m.XF0, m.EYC - 1, 0), c)]
    r += m.line_res(m.O48["boxL_base_line"], (m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, m.HY0, 0), c)
    r += m.line_res(RIM48, (XN, m.HY1, m.PH), (XN, m.HY0, m.PH), c)
    r += [max(0.0, 0.2 - c[2]) * 1e4]
    return np.array(r)


def res26(c, fam, h=2.4, w=1.45):
    P = m.ent(h, w); r = []
    for key, sy in (("eave_light_A", fam[0]), ("eave_light_B", fam[1])):
        q, df = m.proj((m.SPOT_X, sy, m.SPOT_Z), c); r += list(q - m.O26[key]) if df > 0 else [1e4, 1e4]
    r += m.line_res(m.O26["box_rim_line"], (XN, m.HY1, m.PH), (XN, m.HY0, m.PH), c)
    r += [x / 2.0 for x in m.line_res(m.O26["box_base_line"], (m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, m.HY0, 0), c)]
    r += m.line_res(m.O26["deck_edge_line"], (m.X1, 10.0, 0), (m.X1, -5.0, 0), c)
    for k in ("door_light", "door_outer_base_minusY"):
        q, df = m.proj(P[k], c); r += list(q - m.O26[k]) if df > 0 else [1e4, 1e4]
    r += [max(0.0, 0.2 - c[2]) * 1e4]
    return np.array(r)


O46 = {"edge_light_near": (1003, 870), "deck_edge_line": [(300, 905), (700, 893)], "box_plusY_top_near": (2445, 895), "box_plusY_top_far": (2780, 835),
       "box_base_line": [(2700, 1320), (3300, 1420)], "box_far_rim_line": [(2900, 845), (3400, 870)]}
INS = m.D["edge_lights"]["inset"]["value"]


def res46(c, lamp_y):
    r = []
    q, df = m.proj((m.X1 - INS, lamp_y, 0.06), c); r += list(q - O46["edge_light_near"]) if df > 0 else [1e4, 1e4]
    r += m.line_res(O46["deck_edge_line"], (m.X1, lamp_y + 6, 0), (m.X1, lamp_y - 6, 0), c)
    for k, p in (("box_plusY_top_near", (XN, m.HY1 + 0.06, m.PH)), ("box_plusY_top_far", (m.HX1, m.HY1 + 0.06, m.PH))):
        q, df = m.proj(p, c); r += list(q - O46[k]) if df > 0 else [1e4, 1e4]
    r += m.line_res(O46["box_base_line"], (m.HX0 - m.SKO, m.HY1, 0), (m.HX0 - m.SKO, m.HY0, 0), c)
    r += [x * 0.5 for x in m.line_res(O46["box_far_rim_line"], (m.HX1, m.HY1, m.PH), (m.HX1, m.HY0, m.PH), c)]
    r += [max(0.0, 0.3 - c[2]) * 1e4]
    return np.array(r)


def ray(px, c):
    fwd, right, up = m.R_of(c[3], c[4]); return c[:3], fwd + right * (px[0] - m.CX) / c[5] - up * (px[1] - m.CY) / c[5]


def on_plane_x(px, c, x0):
    o, d = ray(px, c)
    if abs(d[0]) < 1e-9: return None
    t = (x0 - o[0]) / d[0]; return None if t <= 0 else o + t * d


def on_floor(px, c):
    o, d = ray(px, c)
    if d[2] >= 0: return None
    t = -o[2] / d[2]; return o + t * d


def backproject(frame, c):
    out = {}
    for part, st, px, _ in END[frame]:
        if px is None: continue
        q = on_floor(px, c) if part == "P5" else on_plane_x(px, c, XN)
        if q is not None: out[part] = {"status": st, "x": round(float(q[0]), 2), "y": round(float(q[1]), 2), "z": round(float(q[2]), 2)}
    return out


def main():
    out = {"parts": {f: [{"part": p, "status": s, "px": px, "desc": d} for p, s, px, d in v] for f, v in END.items()},
           "fit_sets": {"11748": "출입구(조명·어깨 2·−Y 문설주 발치·문턱선) + 상자 L 근면 밑변 + 주 테두리 근면 윗모서리 직선",
                        "11726": "처마 조명 2(계열별) + 주 테두리 직선 + 상자 밑변 + 바닥선 + 출입구(조명·바깥 발치)",
                        "11246": "가장자리 등 + 바닥선 + 상자 +Y 끝 윗모서리 2 + 상자 밑변 + 먼 쪽 테두리 직선"},
           "model_now": {"main_rim_end_y(=HY0)": m.HY0, "tiers_end_y": round(m.YEND, 2), "box_height": m.PH}, "frames": {}}
    i48 = [(m.XE + dx, m.EYC + dy, z, math.radians(yw), 0.08, f) for dx, dy, z, yw, f in itertools.product((-6.0, -10.0), (-1.0, 1.5), (0.5, 1.5), (-15,), (2400, 4000))]
    s, c, _ = m.best_fit(res48, i48)
    out["frames"]["11748"] = [{"cam": m.cam_dict(c), "rms_weighted": round(s, 1), "f_at_bound": bool(c[5] >= 7999), "end_backprojected": backproject("11748", c)}]
    m5 = [x for x in json.load(open(os.path.join(HERE, "m5_result.json"), encoding="utf-8"))["fits"] if x["geometry"] == "model"]
    out["frames"]["11726"] = []
    for fam in ((0.0, -6.7), (6.7, 0.0)):
        i26 = [np.array([*x["cam"]["xyz"], math.radians(x["cam"]["yaw_deg"]), math.radians(x["cam"]["pitch_deg"]), x["f"]]) for x in m5 if x["spots_AB"] == list(fam)][:3]
        i26 += [np.array([cx, cy, 2.0, math.radians(yw), 0.03, 3000]) for cx, cy, yw in itertools.product((-6.0, 2.0), (-26.0, -18.0), (8, 25))]
        s, c, _ = m.best_fit(lambda q: res26(q, fam), i26)
        out["frames"]["11726"].append({"family_spots_AB": list(fam), "cam": m.cam_dict(c), "rms_weighted": round(s, 1), "f_at_bound": bool(c[5] >= 7999),
                                       "end_backprojected": backproject("11726", c)})
    out["frames"]["11246"] = []
    i46 = [(x, y, 1.6, math.radians(yw), -0.05, f) for x, y, yw, f in itertools.product((2.0, 6.0), (-8.0, -3.0, 2.0), (-60, -30, 0), (3000, 4500))]
    for ly in m.D["edge_lights"]["facility_edge_y"]["value"][:2]:
        s, c, _ = m.best_fit(lambda q: res46(q, ly), i46)
        out["frames"]["11246"].append({"near_lamp_y": ly, "cam": m.cam_dict(c), "rms_weighted": round(s, 1), "f_at_bound": bool(c[5] >= 7999),
                                       "end_backprojected": backproject("11246", c)})
    json.dump(out, open(os.path.join(HERE, "m11_result.json"), "w"), ensure_ascii=False, indent=1)
    for f, rows in out["frames"].items():
        for r in rows:
            print(f, {k: v for k, v in r.items() if k not in ("end_backprojected",)}, r["end_backprojected"], flush=True)


if __name__ == "__main__":
    main()
