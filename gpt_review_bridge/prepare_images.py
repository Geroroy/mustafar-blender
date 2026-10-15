"""검수 입력 준비: 이미지 검증·축소, 치수 JSON·확정 구조 정보 묶기, 보호 파일 해시 스냅숏.

사용:  python prepare_images.py inputs/<입력 목록>.json
결과:  reviews/<review_id>/ (prepared/*.png, manifest.json, context.json, snapshot.json)

네트워크를 쓰지 않는다. 원본 파일은 읽기만 한다.
"""
import argparse
import math
import shutil
import sys
from pathlib import Path

from PIL import Image

from bridge_common import (BRIDGE, CONFIRMED, REVIEWS, ROLES, die, load_config, now,
                           protected_hashes, read_json, sha256_file, write_json)


def image_tokens(w, h, cfg):
    """이미지 입력 토큰 추정(모델마다 다름 — 실제 값은 호출 뒤 usage로 기록)."""
    it = cfg["image_tokens"]
    if it["method"] == "patch":
        n = math.ceil(w / it["patch_size"]) * math.ceil(h / it["patch_size"])
        return int(min(n, it["patch_cap"]) * it["patch_multiplier"])
    # tile: 2048 안에 맞춘 뒤 짧은 변 768, 512px 타일 수
    s = min(1.0, 2048 / max(w, h)); w2, h2 = w * s, h * s
    s = min(1.0, 768 / min(w2, h2)); w2, h2 = w2 * s, h2 * s
    tiles = math.ceil(w2 / 512) * math.ceil(h2 / 512)
    return it["tile_base_tokens"] + it["tile_tokens"] * tiles


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", help="입력 목록 JSON (inputs/ 예시 참고)")
    ap.add_argument("--force", action="store_true", help="아직 호출하지 않은 검수 폴더를 다시 만든다")
    a = ap.parse_args()

    cfg = load_config()
    inp_path = Path(a.inputs).resolve()
    inp = read_json(inp_path)
    base = inp_path.parent
    rid = inp["review_id"]
    mode = inp.get("mode", "review")
    if mode not in ("connection_test", "review"):
        die(f"mode는 connection_test 또는 review: {mode}")
    out = REVIEWS / rid
    if out.exists():
        if (out / "call_attempted.json").exists():
            die(f"{rid}는 이미 API 호출이 있었던 검수입니다. 새 review_id를 쓰세요.")
        if not a.force:
            die(f"{out} 이 이미 있습니다 (--force로 다시 만들기)")
        shutil.rmtree(out)
    (out / "prepared").mkdir(parents=True)

    imgs = inp.get("images", [])
    lim = cfg["limits"]["connection_test_max_images"] if mode == "connection_test" else cfg["limits"]["review_max_images"]
    errors, warns = [], []
    if not imgs:
        errors.append("이미지가 하나도 없습니다")
    if len(imgs) > lim:
        errors.append(f"{mode} 모드는 이미지 {lim}장까지 (입력 {len(imgs)}장)")
    ids = [i.get("id") for i in imgs]
    if len(set(ids)) != len(ids):
        errors.append("이미지 id가 겹칩니다")
    roles = [i.get("role") for i in imgs]
    if "film_still" not in roles:
        errors.append("영화 원본 스틸(film_still)이 최소 1장 필요합니다")
    if mode == "review" and "user_annotation" not in roles:
        warns.append("사용자 주석 이미지(user_annotation)가 없습니다 — 격납고·통로 입구 의도는 텍스트로만 전달됩니다")
    if not any(r and r.startswith("blender_") for r in roles):
        errors.append("검수 대상 Blender 렌더(blender_*)가 최소 1장 필요합니다")

    icfg = cfg["images"]
    manifest, total = [], 0
    for it in imgs:
        iid, role = it.get("id"), it.get("role")
        if role not in ROLES:
            errors.append(f"{iid}: 알 수 없는 역할 '{role}' (가능: {', '.join(ROLES)})"); continue
        src = (base / it["path"]).resolve()
        if not src.exists():
            errors.append(f"{iid}: 파일 없음 {src}"); continue
        if src.suffix.lower() not in icfg["allowed_suffixes"]:
            errors.append(f"{iid}: 지원하지 않는 형식 {src.suffix}"); continue
        try:
            im = Image.open(src)
            if getattr(im, "n_frames", 1) > 1:
                fr = it.get("frame")
                if fr is None:
                    errors.append(f"{iid}: 움직이는 GIF — 쓸 프레임 번호(frame)를 지정하세요 (0~{im.n_frames - 1})"); continue
                im.seek(int(fr))
            im = im.convert("RGB")
        except Exception as e:  # 깨진 파일
            errors.append(f"{iid}: 이미지를 열 수 없음 ({e})"); continue
        if it.get("crop"):
            im = im.crop(tuple(it["crop"]))
        w0, h0 = im.size
        if min(w0, h0) < icfg["min_side_px"]:
            errors.append(f"{iid}: 너무 작음 {w0}×{h0} (짧은 변 {icfg['min_side_px']} px 이상)"); continue
        s = min(1.0, icfg["max_side_px"] / max(w0, h0))
        if s < 1:
            im = im.resize((round(w0 * s), round(h0 * s)), Image.LANCZOS)
        dst = out / "prepared" / f"{iid}.png"
        im.save(dst, optimize=True)          # 다시 저장 → EXIF 등 메타데이터 제거
        size = dst.stat().st_size
        if size > icfg["max_bytes_per_image"]:
            im.save(dst.with_suffix(".jpg"), quality=90); dst.unlink(); dst = dst.with_suffix(".jpg")
            size = dst.stat().st_size
            if size > icfg["max_bytes_per_image"]:
                errors.append(f"{iid}: 줄여도 {size} 바이트 — 너무 큼"); continue
        total += size
        pr, desc = ROLES[role]
        manifest.append({
            "id": iid, "role": role, "priority": pr, "role_desc": desc,
            "note": it.get("note", ""), "source": str(src), "source_sha256": sha256_file(src),
            "crop": it.get("crop"), "frame": it.get("frame"),
            "file": str(dst.relative_to(out)), "size_px": list(im.size), "bytes": size,
            "est_tokens": image_tokens(*im.size, cfg),
        })
    if total > icfg["max_total_bytes"]:
        errors.append(f"전체 이미지 {total} 바이트 > 한도 {icfg['max_total_bytes']}")

    if errors:
        shutil.rmtree(out)
        print("입력 검증 실패:")
        for e in errors:
            print("  - " + e)
        sys.exit(2)

    # 우선순위 순서: 영화 → 주석 → 다른 게임 → 검수 대상
    manifest.sort(key=lambda m: (m["priority"] is None, m["priority"] or 0))

    dims_path = (base / inp["dimensions_json"]).resolve() if inp.get("dimensions_json") else None
    if dims_path and not dims_path.exists():
        shutil.rmtree(out)
        die(f"치수 JSON 없음: {dims_path}")
    context = {
        "review_id": rid, "mode": mode, "created_at": now(),
        "user_notes": inp.get("user_notes", ""),
        "dimensions_json_path": str(dims_path) if dims_path else None,
        "dimensions": read_json(dims_path) if dims_path else None,
        "confirmed_structures": read_json(CONFIRMED) if CONFIRMED.exists() else [],
    }
    write_json(out / "manifest.json", manifest)
    write_json(out / "context.json", context)
    write_json(out / "snapshot.json", {"taken_at": now(), "project_dir": str(BRIDGE / cfg["project"]["dir"]),
                                       "protected": protected_hashes(cfg)})
    shutil.copy(inp_path, out / "inputs.json")

    print(f"준비 완료: {out}")
    print(f"  모드 {mode} · 이미지 {len(manifest)}장 · {total / 1e6:.2f} MB")
    for m in manifest:
        pr = f"우선순위 {m['priority']}" if m["priority"] else "검수 대상"
        print(f"  - {m['id']:18s} {m['role']:20s} {pr:9s} {m['size_px'][0]}×{m['size_px'][1]}  추정 {m['est_tokens']} 토큰")
    for w in warns:
        print("  경고: " + w)


if __name__ == "__main__":
    main()
