"""M3·M4 — 카메라 해가 없는 프레임의 픽셀 비율 측정. 입력은 사람이 확대 격자에서 읽은 4K 픽셀(아래 상수)뿐이다.
M3: 11726·11748에서 A자 출입구 크기를 인물 키로 환산한다. 출입구가 인물보다 멀리 있으므로 깊이 비(k)를 곱해야 하는데,
    k는 지평선 높이(= 카메라 높이)에 달려 있어 카메라 높이 1.0~2.5 m를 가정해 범위로 낸다(바닥 평면, 수평에 가까운 카메라).
    계단 상자 높이는 인물과 거의 같은 깊이(같은 바닥 v)라고 보고 환산한다.
M4: 11206의 정면 요소를 분류하고 지붕/몸체 화면 폭 비를 낸다(원거리, 정면에서 비스듬함 — 비율은 참고값).
실행: python3 m3_m4_pixels.py → m3_m4_result.json"""
import json, os

H_ANA = 1.85
FR = {
    # 11726: 아나킨(달리는 중) 머리 꼭대기·발 v, 출입구 꼭대기 조명 v·바닥 v(오른쪽 문설주 밑), 중간 높이 폭(px), 상자 윗면·밑면 v
    "11726": dict(ana_head=470, ana_foot=1290, door_top=315, door_floor=1150, door_width_mid=640, box_top=1000,
                  door_width_sec=dict(desc="문 높이 0.58 지점(y 799)의 안쪽 밝은 테두리 사이, 비스듬한 시점·연기로 테두리 판독 ±30 px", y=799, x=(2384, 2840)), box_floor=1280),
    # 11748: 아나킨(한 발로 서서 차는 중) 머리·디딘 발, 출입구 꼭대기 조명·바닥, 안쪽 개구부 바닥 폭, 오른쪽 상자 윗면·밑면
    "11748": dict(ana_head=420, ana_foot=1370, door_top=290, door_floor=1220, door_width_mid=630, box_top=1030,
                  door_width_sec=dict(desc="경사 테두리가 세로 문설주로 꺾이는 어깨점 사이(문 높이 0.58 지점)", y=826, x=(726, 1322)), box_floor=1260),
}
CAM_H = (1.0, 1.5, 2.5)


def m3():
    out = {}
    for fr, p in FR.items():
        px_ana = p["ana_foot"] - p["ana_head"]; s = px_ana / H_ANA          # 인물 깊이에서 px/m (자세 때문에 키가 줄어 보이면 s가 작아져 환산값이 커짐)
        r = {"anakin_px": px_ana, "px_per_m_at_actor": round(s, 1),
             "door_height_px": p["door_floor"] - p["door_top"],
             "box_px": p["box_floor"] - p["box_top"], "box_height_m_same_depth": round((p["box_floor"] - p["box_top"]) / s, 2), "by_cam_h": {}}
        for ch in CAM_H:
            v_h = p["ana_foot"] - (ch / H_ANA) * px_ana                         # 지평선 v
            k = (p["ana_foot"] - v_h) / (p["door_floor"] - v_h) if p["door_floor"] > v_h else None
            if k is None:
                r["by_cam_h"][str(ch)] = "지평선이 출입구 바닥보다 아래 — 가정 불성립"; continue
            sec = p["door_width_sec"]; wpx = sec["x"][1] - sec["x"][0]
            r["by_cam_h"][str(ch)] = {"horizon_v": round(v_h), "depth_ratio_door_vs_actor": round(k, 2),
                                      "door_height_m": round(r["door_height_px"] / s * k, 2),
                                      "door_width_at_section_m": round(wpx / s * k, 2)}
        r["door_width_section"] = {**p["door_width_sec"], "px": p["door_width_sec"]["x"][1] - p["door_width_sec"]["x"][0]}
        r["note_superseded"] = "door_width_mid(초판)은 두 프레임에서 다른 높이·단면이라 폐기. door_width_section을 프레임별로 따로 쓴다"
        out[fr] = r
    return out


def m4():
    roof = (2050, 2950); body = (2230, 2860)
    elements = [
        {"x": [2250, 2340], "class": "어두운 구역(구조물 섞임)", "verdict": "UNKNOWN"},
        {"x": [2355, 2420], "class": "어두운 A자 개구부, 안쪽에 붉은 점등", "verdict": "실제 개구부 후보 (PROBABLE)"},
        {"x": [2430, 2560], "class": "A자 테두리, 안쪽 중간 밝기", "verdict": "UNKNOWN (개구부/패널 판정 불가)"},
        {"x": [2600, 2680], "class": "밝은 A자·마름모 무늬 면", "verdict": "벽 패널 (PROBABLE)"},
        {"x": [2680, 2760], "class": "밝은 A자·마름모 무늬 면", "verdict": "벽 패널 (PROBABLE)"},
        {"x": [2760, 2850], "class": "밝은 A자 면", "verdict": "벽 패널 (PROBABLE)"},
    ]
    return {"frame": 11206, "cross_frames": [11198, 11203, 11209], "roof_px": roof, "body_px": body,
            "roof_to_body_width_ratio": round((roof[1] - roof[0]) / (body[1] - body[0]), 2),
            "overhang_left_px": body[0] - roof[0], "overhang_right_px": roof[1] - body[1], "facade_elements": elements,
            "edge_post_lights_x": [2150, 2205, 2455, 2650, 2810, 3130]}


if __name__ == "__main__":
    res = {"M3": m3(), "M4": m4()}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "m3_m4_result.json"), "w"), ensure_ascii=False, indent=1)
