#!/usr/bin/env python3
"""输出契约与状态自检。

用法:
    python3 validate_result.py <result.json> [--case case.json]

检查：case_id 一致、status 合法、result.segments 结构、每段定位/依据、
sources/uncertainty/changes 字段、以及段落覆盖。
"""
import argparse
import json
import sys

VALID_STATUS = {"success", "partial", "unable", "refused"}


def validate(result, case):
    errors = []
    warnings = []
    if not isinstance(result, dict):
        return {"status": "failed", "errors": ["result 不是对象"]}
    cid = result.get("case_id")
    if not cid:
        errors.append("缺少 case_id")
    if case:
        expected = case.get("case_id")
        if expected and str(cid) != str(expected):
            errors.append(f"case_id 不符: 期望 {expected}, 得到 {cid}")
        contract = case.get("output_contract") or []
        r = result.get("result") or {}
        for field in contract:
            if field not in r:
                errors.append(f"result 缺少契约字段: {field}")
    st = result.get("status")
    if st not in VALID_STATUS:
        errors.append(f"status 非法: {st} (应为 {sorted(VALID_STATUS)})")
    r = result.get("result") or {}
    segs = r.get("segments")
    if not isinstance(segs, list) or not segs:
        errors.append("result.segments 缺失或为空")
    else:
        for i, s in enumerate(segs):
            if not isinstance(s, dict):
                errors.append(f"segments[{i}] 不是对象")
                continue
            for k in ("source_id", "source_text", "translation"):
                if k not in s:
                    errors.append(f"segments[{i}] 缺少 {k}")
            if st == "success" and not s.get("location"):
                warnings.append(f"segments[{i}] 缺 location（success 时应有定位）")
            if st == "success" and not s.get("rationale"):
                warnings.append(f"segments[{i}] 缺 rationale（success 时应有译法依据）")
    for k in ("sources", "uncertainty", "changes"):
        if k not in result:
            errors.append(f"缺少顶层字段: {k}")
    if st == "partial" and not result.get("uncertainty"):
        errors.append("status=partial 时必须给出 uncertainty")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "segment_count": len(segs) if isinstance(segs, list) else 0,
        "case_id": cid,
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
