"""검수 결과 → 수정 계획 → 사용자 결정(승인·거절·보류) → 승인 항목만 새 버전으로.

명령:
  plan <검수>                         review.json에서 계획 초안(plan.json) 만들기 — 모델 파일은 건드리지 않음
  note <검수> F01 --summary ... [--targets a,b] [--recommend 승인|거절|보류]
                                      Claude가 항목별 수정 계획을 적는다
  finalize <검수>                     계획 확정 → plan_ko.md (사용자에게 보여 줄 선택지)
  decide <검수> F01=승인 F02=거절 F03=보류 --source "<누가 어디서>"
                                      사용자 결정 기록 (승인/거절/보류 또는 approve/reject/hold)
  status <검수>                       항목별 상태
  guard <검수>                        보호 파일(.blend·스크립트·dimensions.json)이 검수 이후 그대로인지 해시로 확인
  new-version <검수> --to v0.3        승인 항목이 있을 때만 프로젝트 폴더를 새 버전으로 복사 + 승인 목록 첨부
  applied <검수> F01 --version v0.3   새 버전에 적용 완료 표시
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from bridge_common import (CONFIRMED, die, load_config, now, project_dir, protected_hashes, read_json,
                           review_dir, write_json)

CHOICES = {"승인": "approve", "approve": "approve", "거절": "reject", "reject": "reject", "보류": "hold", "hold": "hold"}
KO = {"approve": "승인", "reject": "거절", "hold": "보류", None: "미결정"}


def plan_path(rd):
    return rd / "plan.json"


def load_plan(rd):
    p = plan_path(rd)
    if not p.exists():
        die("plan.json 없음 — 먼저 plan")
    return read_json(p)


def plan_hash(plan):
    core = [{k: it[k] for k in ("id", "object_id", "gpt_proposed_change", "claude_plan")} for it in plan["items"]]
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def guess_targets(object_id):
    if object_id.startswith("NEW:"):
        return ["create_mustafar.py (새 객체)", "dimensions.json (새 항목)"]
    if "." in object_id:
        return [f"dimensions.json ({object_id})"]
    return [f"create_mustafar.py ({object_id})"]


def cmd_plan(a):
    rd = review_dir(a.review)
    if plan_path(rd).exists() and not a.force:
        die("plan.json이 이미 있습니다 (--force로 다시)")
    rv = read_json(rd / "review.json")
    items = []
    for f in rv["result"]["findings"]:
        rec = "보류" if (f["confidence"] == "UNKNOWN" or f["requires_more_reference"]) else None
        items.append({
            "id": f["finding_id"], "object_id": f["object_id"], "issue": f["issue"],
            "confidence": f["confidence"], "requires_more_reference": f["requires_more_reference"],
            "evidence_image": f["evidence_image"], "observation": f["observation"],
            "gpt_proposed_change": f["proposed_change"],
            "claude_plan": {"summary": None, "targets": guess_targets(f["object_id"]), "recommend": rec,
                            "reason": "근거가 UNKNOWN이거나 추가 자료가 필요한 항목" if rec else None},
        })
    plan = {"review_id": rd.name, "mock": rv.get("mock", False), "created_at": now(), "status": "draft",
            "items": items, "decisions": [], "applied": {}}
    write_json(plan_path(rd), plan)
    print(f"계획 초안 {len(items)}건 → {plan_path(rd)} (Claude가 note로 항목별 계획을 적은 뒤 finalize)")


def cmd_note(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    if plan["status"] != "draft":
        die("확정된 계획은 고칠 수 없습니다 (plan --force로 새 초안)")
    it = next((i for i in plan["items"] if i["id"] == a.item), None)
    if not it:
        die(f"항목 없음: {a.item}")
    it["claude_plan"]["summary"] = a.summary
    if a.targets:
        it["claude_plan"]["targets"] = [t.strip() for t in a.targets.split(",")]
    if a.recommend:
        if a.recommend not in CHOICES:
            die("recommend는 승인/거절/보류")
        it["claude_plan"]["recommend"] = a.recommend
    if a.reason:
        it["claude_plan"]["reason"] = a.reason
    write_json(plan_path(rd), plan)
    print(f"{a.item} 계획 기록")


def cmd_finalize(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    missing = [i["id"] for i in plan["items"] if not i["claude_plan"]["summary"]]
    if missing:
        die("계획이 비어 있는 항목: " + ", ".join(missing))
    plan["status"] = "awaiting_decision"
    plan["finalized_at"] = now()
    plan["plan_hash"] = plan_hash(plan)
    write_json(plan_path(rd), plan)
    L = [f"# 수정 계획 — 검수 {rd.name}" + (" (모의 데이터)" if plan["mock"] else ""), "",
         "각 항목에 **승인 / 거절 / 보류** 중 하나를 골라 주세요. 승인한 항목만 새 버전에 적용하고, 그 전에는 기존 .blend·스크립트·dimensions.json을 바꾸지 않습니다.",
         f"계획 지문: `{plan['plan_hash']}`", ""]
    for i in plan["items"]:
        cp = i["claude_plan"]
        L += [f"## {i['id']} · `{i['object_id']}` — {i['issue']}", "",
              f"- GPT 신뢰도: {i['confidence']}" + (" · 추가 자료 필요" if i["requires_more_reference"] else ""),
              f"- 근거: {', '.join(i['evidence_image'])} — {i['observation']}",
              f"- GPT 제안: {i['gpt_proposed_change']}",
              f"- **Claude 수정 계획**: {cp['summary']}",
              f"- 바뀔 파일: {', '.join(cp['targets'])}",
              f"- Claude 권고: {cp['recommend'] or '판단 맡김'}" + (f" ({cp['reason']})" if cp.get("reason") else ""),
              "- 선택: ☐ 승인 ☐ 거절 ☐ 보류", ""]
    (rd / "plan_ko.md").write_text("\n".join(L), encoding="utf-8")
    print(f"계획 확정 (지문 {plan['plan_hash']}) → {rd / 'plan_ko.md'}")


def latest(plan):
    d = {}
    for rec in plan["decisions"]:
        d.update(rec["choices"])
    return d


def update_confirmed(rd, plan):
    data = read_json(CONFIRMED) if CONFIRMED.exists() else []
    data = [e for e in data if e.get("review_id") != rd.name]
    for i in plan["items"]:
        c = latest(plan).get(i["id"])
        if c in ("approve", "reject"):
            data.append({"review_id": rd.name, "finding_id": i["id"], "object_id": i["object_id"],
                         "status": ("applied" if i["id"] in plan["applied"] else "approved") if c == "approve" else "rejected",
                         "decision": KO[c], "issue": i["issue"], "change": i["claude_plan"]["summary"],
                         "mock": plan["mock"]})
    write_json(CONFIRMED, data)


def cmd_decide(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    if plan["status"] not in ("awaiting_decision", "decided"):
        die("계획이 확정되지 않았습니다 (finalize 먼저)")
    if plan_hash(plan) != plan["plan_hash"]:
        die("계획 내용이 확정 후 바뀌었습니다 — 다시 finalize하고 사용자에게 다시 보여 주세요")
    if not a.source:
        die("--source로 누가 어디서 결정했는지 적어 주세요 (예: '사용자, 채팅 답변')")
    ids = {i["id"] for i in plan["items"]}
    choices = {}
    for kv in a.choices:
        if "=" not in kv:
            die(f"형식: F01=승인 ({kv})")
        k, val = kv.split("=", 1)
        if k not in ids:
            die(f"항목 없음: {k}")
        if val not in CHOICES:
            die(f"{k}: 승인/거절/보류 중 하나 ({val})")
        choices[k] = CHOICES[val]
    plan["decisions"].append({"at": now(), "source": a.source, "plan_hash": plan["plan_hash"], "choices": choices})
    plan["status"] = "decided"
    write_json(plan_path(rd), plan)
    update_confirmed(rd, plan)
    cmd_status(a)


def cmd_status(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    d = latest(plan)
    print(f"검수 {rd.name} · 계획 상태 {plan['status']}" + (" · 모의" if plan["mock"] else ""))
    for i in plan["items"]:
        ap = f" · 적용됨({plan['applied'][i['id']]})" if i["id"] in plan["applied"] else ""
        print(f"  {i['id']} {KO[d.get(i['id'])]:4s} `{i['object_id']}` — {i['issue']}{ap}")


def guard_ok(rd, verbose=True):
    cfg = load_config()
    snap = read_json(rd / "snapshot.json")["protected"]
    cur = protected_hashes(cfg)
    ok = True
    for name, h in snap.items():
        same = cur.get(name) == h
        ok &= same
        if verbose:
            print(f"  {'그대로' if same else '바뀜!'}  {name}")
    return ok


def cmd_guard(a):
    rd = review_dir(a.review)
    print(f"보호 파일 확인 ({project_dir(load_config())}):")
    ok = guard_ok(rd)
    print("결과: " + ("검수 이후 변경 없음" if ok else "변경됨 — 승인 없이 바뀐 파일이 있습니다"))
    sys.exit(0 if ok else 1)


def cmd_new_version(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    d = latest(plan)
    approved = [i for i in plan["items"] if d.get(i["id"]) == "approve"]
    if not approved:
        die("승인된 항목이 없습니다 — 새 버전을 만들지 않습니다")
    if not guard_ok(rd, verbose=False):
        die("보호 파일이 검수 이후 바뀌었습니다 — 먼저 guard로 확인")
    src = project_dir(load_config())
    dst = src.parent / a.to
    if dst.exists():
        die(f"{dst} 이미 있음 — 기존 버전을 덮어쓰지 않습니다")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.blend1"))
    write_json(dst / "approved_changes.json", {"from_version": src.name, "review_id": rd.name, "mock": plan["mock"],
                                                "plan_hash": plan["plan_hash"], "created_at": now(),
                                                "approved": approved,
                                                "not_applied": {i["id"]: KO[d.get(i["id"])] for i in plan["items"] if d.get(i["id"]) != "approve"}})
    L = [f"# {a.to} — 승인된 수정만 적용 (검수 {rd.name}, {src.name}에서 복사)", ""]
    for i in approved:
        L += [f"- [ ] {i['id']} `{i['object_id']}`: {i['claude_plan']['summary']}  (파일: {', '.join(i['claude_plan']['targets'])})"]
    L += ["", "거절·보류·미결정 항목은 적용하지 않는다."]
    (dst / "APPROVED_CHANGES.md").write_text("\n".join(L), encoding="utf-8")
    plan.setdefault("versions", []).append({"at": now(), "to": a.to, "from": src.name, "approved": [i["id"] for i in approved]})
    write_json(plan_path(rd), plan)
    print(f"새 버전 폴더 {dst} (승인 {len(approved)}건만 적용 대상). {src.name}은 그대로.")


def cmd_applied(a):
    rd = review_dir(a.review)
    plan = load_plan(rd)
    if latest(plan).get(a.item) != "approve":
        die(f"{a.item}은 승인된 항목이 아닙니다 — 적용할 수 없음")
    plan["applied"][a.item] = a.version
    write_json(plan_path(rd), plan)
    update_confirmed(rd, plan)
    print(f"{a.item} → {a.version} 적용 기록")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("plan"); p.add_argument("review"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_plan)
    p = sp.add_parser("note"); p.add_argument("review"); p.add_argument("item"); p.add_argument("--summary", required=True)
    p.add_argument("--targets"); p.add_argument("--recommend"); p.add_argument("--reason"); p.set_defaults(fn=cmd_note)
    p = sp.add_parser("finalize"); p.add_argument("review"); p.set_defaults(fn=cmd_finalize)
    p = sp.add_parser("decide"); p.add_argument("review"); p.add_argument("choices", nargs="+"); p.add_argument("--source")
    p.set_defaults(fn=cmd_decide)
    p = sp.add_parser("status"); p.add_argument("review"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("guard"); p.add_argument("review"); p.set_defaults(fn=cmd_guard)
    p = sp.add_parser("new-version"); p.add_argument("review"); p.add_argument("--to", required=True); p.set_defaults(fn=cmd_new_version)
    p = sp.add_parser("applied"); p.add_argument("review"); p.add_argument("item"); p.add_argument("--version", required=True)
    p.set_defaults(fn=cmd_applied)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
