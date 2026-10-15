"""GPT 검수 브리지 공통 함수: 설정, 비밀정보 가리기, 해시, 경로."""
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BRIDGE = Path(os.environ.get("MUSTAFAR_BRIDGE_ROOT", Path(__file__).resolve().parent))
REVIEWS = BRIDGE / "reviews"
COSTS = BRIDGE / "costs.jsonl"
CONFIRMED = BRIDGE / "confirmed_structures.json"

ROLES = {
    # 역할: (우선순위, 설명) — 1이 가장 높음. 블렌더 렌더는 '검수 대상'(참고자료 아님)
    "film_still":          (1, "영화 원본 스틸 — 최우선 근거"),
    "user_annotation":     (2, "사용자 주석 — 공간의 기능·의도 설명. 치수의 근거가 아님"),
    "other_game":          (3, "다른 게임의 재현 — 보조 자료"),
    "blender_top":         (None, "검수 대상: Blender Top View"),
    "blender_iso":         (None, "검수 대상: Blender Isometric View"),
    "blender_perspective": (None, "검수 대상: Blender Reference Perspective (R2 카메라 맞춤)"),
    "blender_compare":     (None, "검수 대상: 영화와 같은 카메라로 겹친 비교 이미지"),
}


def now():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def load_config():
    cfg = json.loads((BRIDGE / "config.json").read_text(encoding="utf-8"))
    env_model = os.environ.get("MUSTAFAR_REVIEW_MODEL")
    if env_model:
        cfg["model"] = env_model
    return cfg


def load_schema(for_api=False):
    s = json.loads((BRIDGE / "review_schema.json").read_text(encoding="utf-8"))
    return strip_comments(s) if for_api else s


def strip_comments(o):
    """API에 보낼 때 $comment 같은 비표준 키 제거."""
    if isinstance(o, dict):
        return {k: strip_comments(v) for k, v in o.items() if not k.startswith("$")}
    if isinstance(o, list):
        return [strip_comments(v) for v in o]
    return o


_KEY_RE = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")


def redact(text):
    """로그·파일에 쓰기 전 API 키 흔적을 지운다."""
    s = str(text)
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        s = s.replace(key, "***REDACTED***")
    return _KEY_RE.sub("sk-***REDACTED***", s)


def api_key_present():
    return bool(os.environ.get("OPENAI_API_KEY"))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def project_dir(cfg):
    return (BRIDGE / cfg["project"]["dir"]).resolve()


def protected_hashes(cfg):
    d = project_dir(cfg)
    out = {}
    for name in cfg["project"]["protected_files"]:
        p = d / name
        out[name] = sha256_file(p) if p.exists() else None
    return out


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    p.write_text(redact(text), encoding="utf-8")


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def append_cost(entry):
    COSTS.parent.mkdir(parents=True, exist_ok=True)
    with open(COSTS, "a", encoding="utf-8") as f:
        f.write(redact(json.dumps(entry, ensure_ascii=False)) + "\n")


def die(msg, code=2):
    print("오류: " + redact(msg), file=sys.stderr)
    sys.exit(code)


def review_dir(arg):
    p = Path(arg)
    if not p.is_absolute() and not p.exists():
        p = REVIEWS / arg
    if not p.exists():
        die(f"검수 폴더가 없습니다: {arg}")
    return p.resolve()
