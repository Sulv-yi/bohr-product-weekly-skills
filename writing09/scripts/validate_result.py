#!/usr/bin/env python3
"""输出契约与状态自检。

用法:
    python3 validate_result.py <result.json> [--case case.json]

检查：case_id 一致、status 合法、result 含目标产物/elements/reproducibility/
questions_for_author/limitations、sources 可回溯、change 记录、缺口与状态一致。
"""
import argparse
import json
import sys

VALID_STATUS = {"success", "partial", "unable", "refused"}
REQUIRED_RESULT = ["section", "elements", "reproducibility", "questions_for_author", "limitations"]


def validate(result, case):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {"status": "failed", "errors": ["result 不是对象"]}
    cid = result.get("case_id")
    if not cid:
        errors.append("缺少 case_id")
    if case:
        expected = case.get("case_id")
        if expected and str(cid) != str(expected):
            errors.append(f"case_id 不符: 期望 {expected}, 得到 {cid}")
        for field in (case.get("output_contract") or []):
            if field not in (result.get("result") or {}):
                errors.append(f"result 缺少契约字段: {field}")
    st = result.get("status")
    if st not in VALID_STATUS:
        errors.append(f"status 非法: {st}")
    r = result.get("result") or {}
    for field in REQUIRED_RESULT:
        if field not in r:
            errors.append(f"result 缺少: {field}")
    if isinstance(r.get("questions_for_author"), list):
        blocking = [q for q in r["questions_for_author"]
                    if isinstance(q, dict) and q.get("blocking")]
        if blocking and st == "success":
            errors.append("存在 blocking 追问但 status=success，应为 partial")
    if st == "partial" and not result.get("uncertainty"):
        errors.append("status=partial 时必须给出 uncertainty")
    for k in ("sources", "uncertainty", "changes"):
        if k not in result:
            errors.append(f"缺少顶层字段: {k}")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors, "warnings": warnings, "case_id": cid,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--case")
    args = ap.parse_args()
    result = json.load(open(args.result, encoding="utf-8"))
    case = json.load(open(args.case, encoding="utf-8")) if args.case else None
    rep = validate(result, case)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
