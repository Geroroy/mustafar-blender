"""API 호출 없이 전체 흐름 시험 (모의 데이터).

샌드박스(임시 폴더)에 브리지 코드와 v0.2 사본을 만들어 시험한다 — 실제 v0.2와 실제 reviews/는 건드리지 않는다.
네트워크: 바깥으로 나가지 않는다. 오류 경로 시험은 가짜 키 + 로컬 닫힌 포트(127.0.0.1:9)로만 한다.

사용: python tests/test_flow.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # gpt_review_bridge
PROJ = HERE.parent                                     # mustafar_blender
PY = sys.executable
FAKE_KEY = "sk-test-FAKEKEY-0123456789abcdef"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))


def run(T, *args, env_extra=None, key=False):
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    env["MUSTAFAR_BRIDGE_ROOT"] = str(T / "gpt_review_bridge")
    if key:
        env["OPENAI_API_KEY"] = FAKE_KEY
    env.update(env_extra or {})
    p = subprocess.run([PY, *args], cwd=T / "gpt_review_bridge", env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def hashes(d):
    sys.path.insert(0, str(HERE))
    from bridge_common import sha256_file
    return {f.name: sha256_file(f) for f in sorted(d.iterdir()) if f.is_file()}


def main():
    real_before = hashes(PROJ / "v0.2")
    T = Path(tempfile.mkdtemp(prefix="bridge_selftest_", dir=os.environ.get("SELFTEST_TMP")))
    shutil.copytree(HERE, T / "gpt_review_bridge", ignore=shutil.ignore_patterns("reviews", "costs.jsonl",
                                                                               "confirmed_structures.json", "__pycache__"))
    shutil.copytree(PROJ / "v0.2", T / "v0.2", ignore=shutil.ignore_patterns("work"))
    (T / "refs").symlink_to(PROJ / "refs")
    cfgp = T / "gpt_review_bridge" / "config.json"
    cfg = json.loads(cfgp.read_text())
    cfg["model"] = "TEST-MODEL-not-real"
    cfg["pricing"].update({"input_per_1m_tokens": 1.0, "output_per_1m_tokens": 4.0,
                           "source": "시험용 가짜 가격", "checked_at": "TEST"})
    cfgp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    G = T / "gpt_review_bridge"
    print(f"샌드박스: {T}\n")

    # 1. 입력 검증
    rc, out = run(T, "prepare_images.py", "inputs/001_connection_test.json")
    check("연결 테스트 입력 준비(이미지 2장)", rc == 0 and "이미지 2장" in out, out)
    rc, out = run(T, "prepare_images.py", "inputs/002_landing_full.json")
    check("전체 검수: 사용자 주석 이미지가 없으면 멈춤", rc != 0 and "user_hangar_entrance: 파일 없음" in out, out)
    bad = json.loads((G / "inputs/002_landing_full.json").read_text())
    bad.update(review_id="900_bad", mode="connection_test")
    bad["images"] = [dict(bad["images"][0]), {**bad["images"][2], "frame": None}, {"id": "x", "role": "poster", "path": "../../refs/R1_film_wide.jpg"}]
    (G / "inputs/900_bad.json").write_text(json.dumps(bad, ensure_ascii=False))
    rc, out = run(T, "prepare_images.py", "inputs/900_bad.json")
    check("나쁜 입력 거부: 장수 초과·GIF 프레임 미지정·모르는 역할·검수 대상 없음",
          rc != 0 and "2장까지" in out and "프레임 번호" in out and "알 수 없는 역할" in out and "blender_" in out, out)
    man = json.loads((G / "reviews/001_connection_test/manifest.json").read_text())
    check("준비된 이미지 크기 ≤ 1536 px, 영화 스틸이 먼저", all(max(m["size_px"]) <= 1536 for m in man) and man[0]["role"] == "film_still")

    # 2. 견적과 호출 안전장치
    rc, out = run(T, "review.py", "estimate", "001_connection_test")
    est = json.loads((G / "reviews/001_connection_test/estimate.json").read_text())
    check("견적: 모델·토큰·비용·지문", rc == 0 and est["est_cost_usd_max"] is not None and len(est["fingerprint"]) == 12, out)
    print("      " + out.strip().replace("\n", "\n      "))
    rc, out = run(T, "review.py", "run", "001_connection_test")
    check("--confirm 없이 실제 호출 거부", rc != 0 and "--confirm" in out)
    rc, out = run(T, "review.py", "run", "001_connection_test", "--confirm", "000000000000")
    check("지문이 다르면 거부", rc != 0 and "지문 불일치" in out)
    rc, out = run(T, "review.py", "run", "001_connection_test", "--confirm", est["fingerprint"])
    check("키가 없으면 네트워크 전에 멈춤", rc != 0 and "OPENAI_API_KEY" in out
          and not (G / "reviews/001_connection_test/call_attempted.json").exists(), out)
    cfg_noprice = json.loads(cfgp.read_text()); saved = json.loads(cfgp.read_text())
    cfg_noprice["pricing"]["input_per_1m_tokens"] = None
    cfgp.write_text(json.dumps(cfg_noprice, ensure_ascii=False))
    rc, out = run(T, "review.py", "run", "001_connection_test", "--confirm", est["fingerprint"], key=True)
    check("가격 미설정이면 호출 거부", rc != 0 and "가격 미설정" in out)
    cfgp.write_text(json.dumps(saved, ensure_ascii=False, indent=2))

    # 3. 오류 경로 + 키 가리기 (가짜 키, 로컬 닫힌 포트 — 바깥으로 나가지 않음)
    local = {"OPENAI_BASE_URL": "http://127.0.0.1:9/v1", "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}
    rc, out = run(T, "review.py", "run", "001_connection_test", "--confirm", est["fingerprint"], key=True, env_extra=local)
    err = G / "reviews/001_connection_test/error.json"
    check("연결 실패 → 재시도 없이 멈춤, error.json 기록", rc != 0 and err.exists() and "APIConnectionError" in err.read_text(), out)
    rc2, out2 = run(T, "review.py", "run", "001_connection_test", "--confirm", est["fingerprint"], key=True, env_extra=local)
    check("같은 검수 두 번째 호출 거부(검수당 1회)", rc2 != 0 and "이미 실행" in out2)
    leaked = [str(p) for p in T.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix in (".json", ".jsonl", ".md", ".txt", ".log")
              and FAKE_KEY in p.read_text(errors="ignore")]
    check("키가 어떤 파일에도 남지 않음", not leaked and FAKE_KEY not in out + out2, str(leaked))
    costs = [json.loads(l) for l in (G / "costs.jsonl").read_text().splitlines()]
    check("실패한 호출도 비용 기록에 남김(사용량 없음 표시)", costs and costs[-1]["status"] == "error")

    # 4. 모의 검수 → 계획 → 결정 → 새 버전
    ct = json.loads((G / "inputs/001_connection_test.json").read_text()); ct["review_id"] = "003_mock"
    (G / "inputs/003_mock.json").write_text(json.dumps(ct, ensure_ascii=False))
    run(T, "prepare_images.py", "inputs/003_mock.json")
    rc, out = run(T, "review.py", "run", "003_mock", "--mock", "mock/mock_review_output.json")
    R = G / "reviews/003_mock"
    check("모의 실행: review.json·report_ko.md (스키마 검증 통과)", rc == 0 and (R / "report_ko.md").exists(), out)
    check("보고서에 '모의 데이터' 표시", "모의 데이터" in (R / "report_ko.md").read_text())
    rc, out = run(T, "approval.py", "plan", "003_mock")
    plan = json.loads((R / "plan.json").read_text())
    check("계획 초안: UNKNOWN·추가자료 항목은 '보류' 권고", plan["items"][2]["claude_plan"]["recommend"] == "보류")
    rc, out = run(T, "approval.py", "decide", "003_mock", "F01=승인", "--source", "시험")
    check("계획 확정 전 결정 거부", rc != 0 and "확정되지" in out)
    rc, out = run(T, "approval.py", "finalize", "003_mock")
    check("계획 빈칸이 있으면 확정 거부", rc != 0 and "비어 있는" in out)
    notes = {"F01": "[시험] 새 버전에서 facility.roof_overhang 값만 바꾸고 재렌더",
             "F02": "[시험] 판재 분할에 삼각형 비율 제한 추가",
             "F03": "[시험] 출입구 근거 프레임을 받을 때까지 모델 변경 없음"}
    for k, s in notes.items():
        run(T, "approval.py", "note", "003_mock", k, "--summary", s)
    rc, out = run(T, "approval.py", "finalize", "003_mock")
    check("계획 확정 → plan_ko.md(승인/거절/보류 선택지)", rc == 0 and "☐ 승인 ☐ 거절 ☐ 보류" in (R / "plan_ko.md").read_text(), out)
    p = json.loads((R / "plan.json").read_text()); p["items"][0]["claude_plan"]["summary"] += " (몰래 수정)"
    (R / "plan.json").write_text(json.dumps(p, ensure_ascii=False))
    rc, out = run(T, "approval.py", "decide", "003_mock", "F01=승인", "--source", "시험")
    check("확정 뒤 계획이 바뀌면 결정 거부", rc != 0 and "바뀌었습니다" in out)
    p["items"][0]["claude_plan"]["summary"] = notes["F01"]
    (R / "plan.json").write_text(json.dumps(p, ensure_ascii=False))
    rc, out = run(T, "approval.py", "decide", "003_mock", "F01=승인", "F02=거절", "F03=보류", "--source", "시험(모의)")
    check("결정 기록: 승인·거절·보류", rc == 0 and "F01 승인" in out and "F02 거절" in out and "F03 보류" in out, out)
    rc, out = run(T, "approval.py", "guard", "003_mock")
    check("승인 전후 보호 파일 그대로(guard)", rc == 0, out)
    sbx_before = hashes(T / "v0.2")
    rc, out = run(T, "approval.py", "new-version", "003_mock", "--to", "v0.3")
    nv = T / "v0.3"
    ac = json.loads((nv / "approved_changes.json").read_text()) if nv.exists() else {}
    check("새 버전 v0.3: 승인 항목(F01)만 포함", rc == 0 and [i["id"] for i in ac.get("approved", [])] == ["F01"]
          and ac["not_applied"] == {"F02": "거절", "F03": "보류"}, out)
    check("새 버전을 만들어도 v0.2 원본은 그대로", hashes(T / "v0.2") == sbx_before)
    rc, out = run(T, "approval.py", "new-version", "003_mock", "--to", "v0.3")
    check("이미 있는 버전 폴더를 덮어쓰지 않음", rc != 0 and "덮어쓰지" in out)
    rc, out = run(T, "approval.py", "applied", "003_mock", "F02", "--version", "v0.3")
    check("거절된 항목은 적용 표시 불가", rc != 0)
    rc, out = run(T, "approval.py", "applied", "003_mock", "F01", "--version", "v0.3")
    conf = json.loads((G / "confirmed_structures.json").read_text())
    st = {c["finding_id"]: c["status"] for c in conf}
    check("확정 구조 정보: F01 applied, F02 rejected, F03(보류) 없음", st == {"F01": "applied", "F02": "rejected"}, str(st))

    # 5. 다음 검수가 확정 정보를 받는지 + 승인 0건이면 새 버전 거부 + 보호 파일 변경 감지
    ct["review_id"] = "004_mock"; (G / "inputs/004_mock.json").write_text(json.dumps(ct, ensure_ascii=False))
    run(T, "prepare_images.py", "inputs/004_mock.json")
    ctx = json.loads((G / "reviews/004_mock/context.json").read_text())
    check("다음 검수 입력에 확정·거절 구조가 들어감", len(ctx["confirmed_structures"]) == 2)
    run(T, "review.py", "run", "004_mock", "--mock", "mock/mock_review_output.json")
    run(T, "approval.py", "plan", "004_mock")
    for k in ("F01", "F02", "F03"):
        run(T, "approval.py", "note", "004_mock", k, "--summary", "[시험]")
    run(T, "approval.py", "finalize", "004_mock")
    run(T, "approval.py", "decide", "004_mock", "F01=거절", "F02=보류", "F03=보류", "--source", "시험")
    rc, out = run(T, "approval.py", "new-version", "004_mock", "--to", "v0.4")
    check("승인 0건이면 새 버전 만들지 않음", rc != 0 and not (T / "v0.4").exists())
    with open(T / "v0.2" / "dimensions.json", "a") as f:
        f.write("\n")
    rc, out = run(T, "approval.py", "guard", "004_mock")
    check("보호 파일이 바뀌면 guard가 잡음", rc != 0 and "바뀜" in out)

    real_after = hashes(PROJ / "v0.2")
    check("실제 v0.2 파일은 시험 전후 동일", real_before == real_after)

    keep = PROJ / "gpt_review_bridge" / "tests" / "last_selftest"
    if keep.exists():
        shutil.rmtree(keep)
    keep.mkdir(parents=True)
    for f in ("report_ko.md", "plan_ko.md", "plan.json", "review.json"):
        shutil.copy(R / f, keep / f)
    shutil.copy(G / "reviews/001_connection_test/estimate.json", keep / "estimate_example.json")
    shutil.copy(G / "reviews/001_connection_test/error.json", keep / "error_example.json")
    shutil.copy(G / "costs.jsonl", keep / "costs_example.jsonl")
    shutil.copy(nv / "APPROVED_CHANGES.md", keep / "APPROVED_CHANGES_example.md")
    shutil.rmtree(T)
    n_ok = sum(ok for _, ok in results)
    print(f"\n결과: {n_ok}/{len(results)} 통과 · 예시 결과 → {keep}")
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
