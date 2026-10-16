"""M6 — 바닥 이음매 방향 비교.
11615: 바닥 영역에서 직선 이음매를 자동 검출(OpenCV LSD)하고, v0.2 기준안 R2 카메라로 바닥면(Z=0)에 역투영해
       모델 좌표계에서의 이음매 방향(0°=+X, 90°=+Y)과 땅 위 길이를 낸다.
11712: 카메라 해가 없어 화면 안 방향만 낸다(정성).
모델: v0.3 floor_plates.json에서 판 변의 방향을 같은 방식으로 집계한다.
1단계(영화 필요): python m6_floor_seams.py detect <11615.jpg> <11712.jpg>  → m6_segments.json (검출 선분 픽셀 좌표 — 영화 없이 2단계 재현 가능)
2단계(영화 불필요): python m6_floor_seams.py analyze                         → m6_result.json"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CX, CY, W4 = 1920.0, 800.0, 3840
D2 = json.load(open(os.path.join(ROOT, "v0.2", "dimensions.json"), encoding="utf-8"))
rc = D2["r2_camera"]; AX, AY = rc["anchor_A"]["value"]; cx, cy, cz = rc["location_from_back_corner"]["value"]
CAM = np.array([AX + cx, AY + cy, cz]); F = rc["lens_mm_36"] / 36.0 * W4
pitch, yaw = math.radians(rc["pitch_deg"]), math.radians(rc["yaw_deg"])
# Blender: rotation_euler = (90°−pitch, 0, yaw), 카메라는 로컬 −Z를 봄
Rx = np.array([[1, 0, 0], [0, math.cos(math.pi / 2 - pitch), -math.sin(math.pi / 2 - pitch)], [0, math.sin(math.pi / 2 - pitch), math.cos(math.pi / 2 - pitch)]])
Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
R = Rz @ Rx; RIGHT, UP, FWD = R[:, 0], R[:, 1], -R[:, 2]
# 11615 바닥 영역(인물·경사로·상자·파드메 제외) — 사각형 [x0,y0,x1,y1] 합집합
ROI = [(0, 1000, 1380, 1600), (1700, 1080, 2380, 1600), (2560, 1080, 3050, 1180), (1380, 1360, 3000, 1600)]
EXCLUDE = [(1180, 960, 1420, 1060), (2300, 800, 2620, 1300), (2700, 1150, 3060, 1330)]


def ground(u, v):
    d = FWD + RIGHT * (u - CX) / F - UP * (v - CY) / F
    t = -CAM[2] / d[2]
    return CAM + t * d if t > 0 else None


def detect(p15, p12):
    import cv2
    out = {}
    for name, path in (("11615", p15), ("11712", p12)):
        g = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g), (5, 5), 0)
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        segs = lsd.detect(g)[0].reshape(-1, 4)
        keep = []
        for x0, y0, x1, y1 in segs:
            L = math.hypot(x1 - x0, y1 - y0)
            if L < (40 if name == "11615" else 120):
                continue
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            if name == "11615":
                if not any(a <= mx <= c and b <= my <= d for a, b, c, d in ROI) or any(a <= mx <= c and b <= my <= d for a, b, c, d in EXCLUDE):
                    continue
            keep.append([round(float(x0), 1), round(float(y0), 1), round(float(x1), 1), round(float(y1), 1)])
        out[name] = keep
    json.dump({"method": "OpenCV LSD on CLAHE+blur grayscale; length ≥40 px (11615) / ≥120 px (11712); 11615 floor ROI only",
               "roi_11615": ROI, "exclude_11615": EXCLUDE, "segments": out}, open(os.path.join(HERE, "m6_segments.json"), "w"), indent=0)
    print({k: len(v) for k, v in out.items()})


def hist(angles, weights, bin_deg=10):
    h = np.zeros(180 // bin_deg)
    for a, w in zip(angles, weights):
        h[int(a % 180) // bin_deg] += w
    return [round(float(x / max(h.sum(), 1e-9)), 3) for x in h]


def analyze():
    S = json.load(open(os.path.join(HERE, "m6_segments.json")))["segments"]
    ang, wt, lens = [], [], []
    for x0, y0, x1, y1 in S["11615"]:
        a, b = ground(x0, y0), ground(x1, y1)
        if a is None or b is None:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        if L > 30: continue
        ang.append(math.degrees(math.atan2(dy, dx)) % 180); wt.append(L); lens.append(L)
    # 모델 판 변 방향 (v0.3 floor_plates.json)
    fp = json.load(open(os.path.join(ROOT, "v0.3", "work", "floor_plates.json")))
    ma, mw = [], []
    for p in fp["plates_before_seam"]:
        for i in range(len(p)):
            (xa, ya), (xb, yb) = p[i - 1], p[i]; L = math.hypot(xb - xa, yb - ya)
            if L > 1e-3: ma.append(math.degrees(math.atan2(yb - ya, xb - xa)) % 180); mw.append(L)
    i_ang = [math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180 for x0, y0, x1, y1 in S["11712"]]
    i_w = [math.hypot(x1 - x0, y1 - y0) for x0, y0, x1, y1 in S["11712"]]
    bins = [f"{b}-{b + 10}" for b in range(0, 180, 10)]
    film_h = hist(ang, wt); model_h = hist(ma, mw)
    def peaks(h):
        return [bins[i] for i in np.argsort(h)[::-1][:3]]
    res = {"camera": "v0.2 기준안 R2 카메라(h 5.05 m, pitch 6.9°, yaw −13°, f 4549 px) — 11615는 같은 고정 카메라",
           "angle_convention": "모델 좌표 바닥면, 0°=+X(시설 쪽), 90°=+Y(절벽 쪽), 180° 주기",
           "bins": bins,
           "film_11615_ground": {"n_segments": len(ang), "length_weighted_hist": film_h, "top_bins": peaks(film_h),
                                 "ground_length_m": {"median": round(float(np.median(lens)), 2), "p90": round(float(np.percentile(lens, 90)), 2), "max": round(float(max(lens)), 2)}},
           "model_v03": {"length_weighted_hist": model_h, "top_bins": peaks(model_h)},
           "film_11712_image_only": {"n_segments": len(i_ang), "length_weighted_hist_image_deg": hist(i_ang, i_w), "top_bins_image": peaks(hist(i_ang, i_w)),
                                     "note": "화면 좌표 각도(0°=화면 오른쪽, 90°=화면 아래). 카메라 해가 없어 모델 방향으로 바꿀 수 없음"}}
    json.dump(res, open(os.path.join(HERE, "m6_result.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: (v["top_bins"] if isinstance(v, dict) and "top_bins" in v else None) for k, v in res.items()}, ensure_ascii=False))
    print(res["film_11615_ground"]["ground_length_m"], res["film_11712_image_only"]["top_bins_image"])


if __name__ == "__main__":
    detect(sys.argv[2], sys.argv[3]) if sys.argv[1] == "detect" else analyze()
