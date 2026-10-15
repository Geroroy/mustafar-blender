"""OpenAI GPT 검수 요청 (공식 OpenAI Python SDK · Responses API).

명령:
  check                       키 등록 여부·SDK·설정·api.openai.com 연결 확인 (과금 없음)
  list-models                 계정에서 쓸 수 있는 모델 목록 (과금 없음, 키·네트워크 필요)
  estimate <검수>             보낼 요청을 만들고 예상 토큰·비용을 계산 (호출 안 함) → estimate.json
  run <검수> --confirm <지문>  실제 호출 1회 (estimate의 지문과 같아야 함, 재시도 없음)
  run <검수> --mock <파일>     호출 없이 모의 응답으로 같은 흐름을 실행
  report <검수>               review.json → report_ko.md 다시 만들기

<검수> = reviews/ 아래 폴더 이름(review_id) 또는 경로.
API 키는 OPENAI_API_KEY 환경변수로만 읽는다. 키는 어떤 파일·로그에도 쓰지 않는다.
"""
import argparse
import base64
import hashlib
import json
import math
import mimetypes
import os
import ssl
import sys
import urllib.error
import urllib.request

from bridge_common import (BRIDGE, append_cost, api_key_present, die, load_config, load_schema, now,
                           read_json, redact, review_dir, write_json)

INSTRUCTIONS = """너는 영화 《Star Wars: Episode III – Revenge of the Sith》(2005)의 무스타파 착륙장을 Blender로 복원하는 작업의 독립 검수자다.
목표: Blender 블록아웃 렌더(검수 대상)를 영화 스틸(근거)과 비교해 구조 오류를 찾는다.

규칙
1. 근거 우선순위: 영화 원본 스틸(film_still) > 사용자 주석(user_annotation) > 다른 게임 이미지(other_game). Blender 렌더(blender_*)는 검수 대상이며 근거가 아니다.
2. 사용자 주석은 공간의 기능과 의도(예: 격납고, 통로 입구가 어디인지)를 설명하는 자료다. 치수나 정확한 형태의 증거로 쓰지 않는다.
3. 영화에서 보이지 않는 구조, 검증되지 않은 수치를 확정하지 않는다. 수치를 제안할 때는 근거 이미지와 함께 범위로 적는다. 근거가 부족하면 confidence는 UNKNOWN, requires_more_reference는 true, proposed_change는 '수정 보류, 추가 자료 필요'.
4. confidence CONFIRMED는 영화 원본 스틸에서 직접 보이는 경우에만 쓴다.
5. 이전 검수에서 확정된 구조(confirmed_structures)는 새 영화 근거가 있을 때만 다시 문제 삼는다. 거절된 제안은 같은 근거로 다시 내지 않는다.
6. 텍스처·조명·장식 같은 미적 디테일은 다루지 않는다. 구조, 배치, 비율, 연결, 높이 관계만 본다.
7. object_id는 아래 객체 목록의 이름 또는 dimensions의 경로(예: facility.trench_gap)를 쓴다. 해당 객체가 없으면 NEW:<이름>.
8. evidence_image에는 입력 이미지 ID를 쓰고 영화 스틸을 먼저 적는다.
9. 모든 설명은 한국어로 쓴다."""


def b64_data_url(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def build_request(rd, cfg, with_images=True):
    """Responses API 요청 본문. with_images=False면 이미지 대신 자리표시(추정·저장용)."""
    manifest = read_json(rd / "manifest.json")
    ctx = read_json(rd / "context.json")
    inp = read_json(rd / "inputs.json")
    parts, texts = [], []

    head = [f"검수 ID: {ctx['review_id']} ({'연결 테스트' if ctx['mode'] == 'connection_test' else '전체 검수'})",
            "입력 이미지(우선순위 순):"]
    for m in manifest:
        pr = f"근거 우선순위 {m['priority']}" if m["priority"] else "검수 대상"
        head.append(f"- {m['id']}: {m['role_desc']} [{pr}]" + (f" — {m['note']}" if m["note"] else ""))
    if inp.get("object_ids"):
        head.append("Blender 객체 목록: " + ", ".join(inp["object_ids"]))
    t = "\n".join(head)
    parts.append({"type": "input_text", "text": t}); texts.append(t)

    for m in manifest:
        t = f"[이미지 {m['id']}] {m['role_desc']}"
        parts.append({"type": "input_text", "text": t}); texts.append(t)
        img_path = rd / m["file"]
        parts.append({"type": "input_image", "detail": cfg["images"]["detail"],
                      "image_url": b64_data_url(img_path) if with_images else f"<{m['file']} sha256 omitted>"})

    tail = []
    if ctx.get("user_notes"):
        tail.append("사용자 메모:\n" + ctx["user_notes"])
    if ctx.get("dimensions") is not None:
        tail.append("현재 모델 치수 JSON (exist/form = 존재/형태 신뢰도):\n" + json.dumps(ctx["dimensions"], ensure_ascii=False, separators=(",", ":")))
    tail.append("이전 검수에서 확정·거절된 구조:\n" + json.dumps(ctx.get("confirmed_structures", []), ensure_ascii=False, separators=(",", ":")))
    tail.append("요청: 위 규칙에 따라 검수 대상 렌더와 영화 스틸의 구조 차이를 찾아 JSON으로만 답하라. 문제 없는 객체는 적지 않는다.")
    t = "\n\n".join(tail)
    parts.append({"type": "input_text", "text": t}); texts.append(t)

    req = {
        "model": cfg["model"],
        "instructions": INSTRUCTIONS,
        "input": [{"role": "user", "content": parts}],
        "text": {"format": {"type": "json_schema", "name": "mustafar_review", "strict": True,
                            "schema": load_schema(for_api=True)}},
        "max_output_tokens": cfg["limits"]["max_output_tokens"],
        "store": bool(cfg.get("store_responses_on_openai", False)),
    }
    return req, texts, manifest


def fingerprint(req_no_images, manifest):
    blob = json.dumps({"req": req_no_images, "images": [(m["id"], m["source_sha256"], m["file"]) for m in manifest]},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def price_ok(cfg):
    p = cfg["pricing"]
    return p.get("input_per_1m_tokens") is not None and p.get("output_per_1m_tokens") is not None


def cost_usd(cfg, inp_tokens, out_tokens, cached=0):
    p = cfg["pricing"]
    if not price_ok(cfg):
        return None
    cin = p.get("cached_input_per_1m_tokens")
    c = (inp_tokens - cached) * p["input_per_1m_tokens"] / 1e6 + out_tokens * p["output_per_1m_tokens"] / 1e6
    c += cached * (cin if cin is not None else p["input_per_1m_tokens"]) / 1e6
    return round(c, 6)


# ------------------------------------------------------------------ commands
def cmd_check(a):
    cfg = load_config()
    import openai
    print(f"OPENAI_API_KEY 등록: {'예' if api_key_present() else '아니오'} (값은 표시하지 않음)")
    try:
        from openai.resources.responses import Responses  # noqa: F401
        has_resp = "있음"
    except ImportError:
        has_resp = "없음 — SDK 업그레이드 필요"
    print(f"openai SDK: {openai.__version__} · Responses API: {has_resp}")
    print(f"설정 모델: {cfg['model'] or '(미설정)'} · 가격: {'설정됨' if price_ok(cfg) else '(미설정)'}")
    ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") or None)
    req = urllib.request.Request("https://api.openai.com/v1/models", method="GET")  # 키 없이 → 401이면 연결 가능
    try:
        urllib.request.urlopen(req, timeout=20, context=ctx)
        print("api.openai.com: 응답 200 (예상 밖 — 키 없이 성공)")
    except urllib.error.HTTPError as e:
        print(f"api.openai.com: 연결 가능 (키 없는 요청에 HTTP {e.code} — 정상)")
    except urllib.error.URLError as e:
        r = str(e.reason)
        if "403" in r or "Tunnel" in r:
            print("api.openai.com: 차단됨 — 이 환경의 네트워크 정책(프록시 403). 허용 목록에 api.openai.com 추가 필요(사용자 승인 사항)")
        else:
            print(f"api.openai.com: 연결 실패 ({redact(r)})")
        return 3
    return 0


def client(cfg):
    if not api_key_present():
        die("OPENAI_API_KEY 환경변수가 없습니다. 클라우드 환경 설정에 등록하세요(README 참고). 키를 채팅이나 파일에 넣지 마세요.")
    from openai import OpenAI
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=cfg["limits"]["max_retries"],
                  timeout=cfg["limits"]["timeout_seconds"])


def cmd_list_models(a):
    cfg = load_config()
    c = client(cfg)
    try:
        ids = sorted(m.id for m in c.models.list())
    except Exception as e:
        die(f"모델 목록 실패: {type(e).__name__}: {e}")
    print("\n".join(ids))
    print("\n주의: 목록만으로는 이미지 입력 지원 여부를 알 수 없습니다. OpenAI 모델 문서에서 'image input' 지원을 확인하고 config.json에 적으세요.")


def cmd_estimate(a):
    cfg = load_config()
    rd = review_dir(a.review)
    if not cfg["model"]:
        die("모델이 설정되지 않았습니다 (config.json model 또는 MUSTAFAR_REVIEW_MODEL)")
    req, texts, manifest = build_request(rd, cfg, with_images=False)
    text_chars = sum(len(t) for t in texts) + len(INSTRUCTIONS) + len(json.dumps(req["text"], ensure_ascii=False))
    text_tok = math.ceil(text_chars / 2)          # 한국어 섞인 글: 보수적으로 2자당 1토큰
    img_tok = sum(m["est_tokens"] for m in manifest)
    out_max = cfg["limits"]["max_output_tokens"]
    fp = fingerprint(req, manifest)
    est = {
        "review_id": rd.name, "created_at": now(), "model": cfg["model"], "fingerprint": fp,
        "images": len(manifest), "image_ids": [m["id"] for m in manifest],
        "est_input_tokens": text_tok + img_tok, "est_text_tokens": text_tok, "est_image_tokens": img_tok,
        "max_output_tokens": out_max,
        "est_cost_usd_max": cost_usd(cfg, text_tok + img_tok, out_max),
        "est_cost_usd_typical": cost_usd(cfg, text_tok + img_tok, min(out_max, 2500)),
        "pricing": cfg["pricing"],
        "note": "추정치. 이미지 토큰 계산법은 모델마다 다르다. 실제 사용량은 호출 뒤 usage.json·costs.jsonl에 기록.",
    }
    write_json(rd / "estimate.json", est)
    write_json(rd / "request_preview.json", req)   # 이미지 본문 없이 보낼 내용 확인용
    print(f"모델: {est['model']}")
    print(f"이미지 {est['images']}장 ({', '.join(est['image_ids'])})")
    print(f"예상 입력 토큰 ≈ {est['est_input_tokens']:,} (글 {text_tok:,} + 이미지 {img_tok:,}) · 출력 최대 {out_max:,}")
    if est["est_cost_usd_max"] is None:
        print("예상 비용: 계산 불가 — config.json pricing 미설정. 실제 호출 전에 공식 가격을 적어야 합니다.")
    else:
        print(f"예상 비용: 보통 ${est['est_cost_usd_typical']:.4f} · 최대 ${est['est_cost_usd_max']:.4f} "
              f"(가격 출처: {cfg['pricing'].get('source')}, {cfg['pricing'].get('checked_at')})")
    print(f"승인 지문: {fp}   → 실제 호출: python review.py run {rd.name} --confirm {fp}")


def finish(rd, cfg, out_obj, usage, meta, mock):
    """응답 검증 → review.json, usage.json, costs.jsonl, report_ko.md."""
    import jsonschema
    jsonschema.validate(out_obj, load_schema())
    for i, f in enumerate(out_obj["findings"], 1):
        f["finding_id"] = f"F{i:02d}"
    write_json(rd / "review.json", {**meta, "mock": mock, "result": out_obj})
    write_json(rd / "usage.json", usage)
    write_report(rd)
    print(f"검수 결과 {len(out_obj['findings'])}건 → {rd / 'review.json'}")
    print(f"한국어 보고서 → {rd / 'report_ko.md'}")


def cmd_run(a):
    cfg = load_config()
    rd = review_dir(a.review)
    if (rd / "call_attempted.json").exists():
        die("이 검수는 이미 실행되었습니다(검수당 1회). 다시 하려면 새 review_id로 준비하세요.")
    if a.mock:
        out_obj = read_json(a.mock)
        write_json(rd / "call_attempted.json", {"at": now(), "mock": True, "source": str(a.mock)})
        usage = {"mock": True, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        append_cost({"at": now(), "review_id": rd.name, "mock": True, "status": "ok", "model": "mock",
                     "usage": usage, "cost_usd": 0.0, "note": "모의 실행 — API 호출 없음"})
        finish(rd, cfg, out_obj, usage, {"model": "mock", "response_id": None, "created_at": now()}, True)
        return

    # ---- 실제 호출: 조건을 모두 확인한 뒤 1회만
    if not a.confirm:
        die("실제 호출에는 --confirm <지문>이 필요합니다. 먼저 estimate로 모델·예상 비용을 확인·승인하세요.")
    if not cfg["model"]:
        die("모델 미설정")
    if not price_ok(cfg):
        die("가격 미설정 — 예상 비용을 낼 수 없어 호출하지 않습니다")
    est_p = rd / "estimate.json"
    if not est_p.exists():
        die("estimate.json 없음 — 먼저 estimate")
    est = read_json(est_p)
    req_preview, _, manifest = build_request(rd, cfg, with_images=False)
    fp = fingerprint(req_preview, manifest)
    if a.confirm != est["fingerprint"] or fp != est["fingerprint"]:
        die(f"지문 불일치 (승인 {a.confirm}, 견적 {est['fingerprint']}, 현재 {fp}) — 입력이나 설정이 바뀌었으면 estimate를 다시")
    c = client(cfg)
    req, _, _ = build_request(rd, cfg, with_images=True)
    write_json(rd / "call_attempted.json", {"at": now(), "mock": False, "fingerprint": fp, "model": cfg["model"]})
    entry = {"at": now(), "review_id": rd.name, "mock": False, "model": cfg["model"], "fingerprint": fp}
    try:
        resp = c.responses.create(**req)
    except Exception as e:
        import openai
        kind = type(e).__name__
        hint = ""
        if isinstance(e, openai.APIConnectionError):
            hint = "api.openai.com에 연결하지 못했습니다 — 이 환경의 네트워크 정책이 막았을 수 있습니다(허용 목록 변경은 사용자 승인 사항)."
        elif isinstance(e, openai.AuthenticationError):
            hint = "키가 거부되었습니다."
        elif isinstance(e, openai.BadRequestError):
            hint = "요청 거부 — 모델이 이미지 입력·구조화 출력을 지원하는지 확인하세요."
        elif isinstance(e, openai.RateLimitError):
            hint = "한도 초과 또는 결제 한도."
        err = {"at": now(), "error": kind, "message": redact(str(e))[:2000], "hint": hint}
        write_json(rd / "error.json", err)
        append_cost({**entry, "status": "error", "error": kind, "usage": None,
                     "note": "실패한 호출도 일부 과금될 수 있음 — OpenAI 플랫폼 Usage에서 확인"})
        die(f"호출 실패 ({kind}). {hint} 자동 재시도하지 않습니다. 자세한 내용: {rd / 'error.json'}")
    u = resp.usage
    usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "total_tokens": u.total_tokens,
             "cached_tokens": getattr(u.input_tokens_details, "cached_tokens", 0),
             "reasoning_tokens": getattr(u.output_tokens_details, "reasoning_tokens", 0)}
    cost = cost_usd(cfg, usage["input_tokens"], usage["output_tokens"], usage["cached_tokens"])
    usage["cost_usd_from_config_prices"] = cost
    append_cost({**entry, "status": resp.status, "model_returned": resp.model, "response_id": resp.id,
                 "usage": usage, "cost_usd": cost, "pricing_source": cfg["pricing"].get("source"),
                 "estimate_usd_max": est.get("est_cost_usd_max"),
                 "note": "비용은 config 가격 × 사용량. 실제 청구액은 OpenAI 플랫폼 Usage가 기준"})
    write_json(rd / "response_raw.json", {"id": resp.id, "model": resp.model, "status": resp.status,
                                          "output_text": resp.output_text})
    if resp.status != "completed":
        die(f"응답 상태 {resp.status} (출력이 잘렸을 수 있음). 재시도하지 않습니다. response_raw.json 확인")
    try:
        out_obj = json.loads(resp.output_text)
    except json.JSONDecodeError:
        die("응답이 JSON이 아닙니다 — response_raw.json 확인")
    finish(rd, cfg, out_obj, usage, {"model": resp.model, "response_id": resp.id, "created_at": now()}, False)
    print(f"사용량: 입력 {usage['input_tokens']:,} · 출력 {usage['output_tokens']:,} 토큰 · 비용(설정 가격 기준) ${cost}")


CONF_KO = {"CONFIRMED": "확인", "PROBABLE": "추정", "UNKNOWN": "불명"}


def write_report(rd):
    rv = read_json(rd / "review.json")
    res = rv["result"]
    manifest = read_json(rd / "manifest.json")
    usage = read_json(rd / "usage.json") if (rd / "usage.json").exists() else {}
    L = [f"# 무스타파 착륙장 GPT 검수 보고서 — {rd.name}", ""]
    if rv.get("mock"):
        L += ["> **모의 데이터** — 실제 GPT 응답이 아님. 승인 흐름 시험용.", ""]
    L += [f"- 모델: {rv.get('model')} · 응답 ID: {rv.get('response_id') or '-'} · 작성: {rv.get('created_at')}",
          f"- 사용량: 입력 {usage.get('input_tokens', '-')} · 출력 {usage.get('output_tokens', '-')} 토큰"
          + (f" · 비용(설정 가격 기준) ${usage['cost_usd_from_config_prices']}" if usage.get("cost_usd_from_config_prices") is not None else ""),
          "- 입력 이미지: " + ", ".join(f"{m['id']}({m['role']})" for m in manifest), "",
          "## 요약", "", res["summary_ko"], "", "## 지적 사항", ""]
    if not res["findings"]:
        L.append("없음")
    for f in res["findings"]:
        L += [f"### {f['finding_id']} · `{f['object_id']}` — {f['issue']}", "",
              f"- 신뢰도: **{f['confidence']}** ({CONF_KO[f['confidence']]})"
              + (" · 추가 자료 필요" if f["requires_more_reference"] else ""),
              f"- 근거 이미지: {', '.join(f['evidence_image'])}",
              f"- 관찰: {f['observation']}",
              f"- 제안: {f['proposed_change']}", ""]
    if res["missing_references"]:
        L += ["## 필요한 추가 자료", ""] + [f"- {x}" for x in res["missing_references"]] + [""]
    L += ["---", "이 보고서는 제안일 뿐이다. 모델 수정은 approval.py로 사용자가 승인한 항목만 새 버전에 적용한다."]
    (rd / "report_ko.md").write_text(redact("\n".join(L)), encoding="utf-8")


def cmd_report(a):
    write_report(review_dir(a.review))
    print("보고서 다시 만듦")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("check").set_defaults(fn=cmd_check)
    sp.add_parser("list-models").set_defaults(fn=cmd_list_models)
    p = sp.add_parser("estimate"); p.add_argument("review"); p.set_defaults(fn=cmd_estimate)
    p = sp.add_parser("run"); p.add_argument("review"); p.add_argument("--confirm"); p.add_argument("--mock")
    p.set_defaults(fn=cmd_run)
    p = sp.add_parser("report"); p.add_argument("review"); p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
