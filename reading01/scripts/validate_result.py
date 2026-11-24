#!/usr/bin/env python3
"""校验 result.json：契约字段齐全、证据 quote 可回溯、状态合法。

用法: python validate_result.py <result.json> [--blocks blocks.json] [--case case.json]
退出码 0=通过, 1=有问题, 2=参数/文件错误。
"""
import sys
import json
import os
import argparse

VALID_STATUS = {"success", "partial", "blocked", "unanswerable"}
VALID_UNC = {"not_reported", "undetermined", "conflict"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check(result, blocks_doc, case):
    errors = []
    warnings = []
    if not isinstance(result, dict):
        return ["result.json 顶层必须是对象"], []

    # 状态
    status = result.get("status")
    if status not in VALID_STATUS:
        errors.append(f"status 非法: {status!r}，应为 {sorted(VALID_STATUS)}")

    # case_id
    if "case_id" not in result or result["case_id"] in (None, ""):
        errors.append("缺少 case_id")
    elif case and "case_id" in case and str(result["case_id"]) != str(case["case_id"]):
        errors.append(f"case_id 与 case.json 不一致: {result['case_id']} vs {case['case_id']}")

    # output_contract 字段
    contract = case.get("output_contract") if isinstance(case, dict) else None
    result_payload = result.get("result")
    if contract:
        if not isinstance(result_payload, dict):
            errors.append("case.json 有 output_contract，但 result.result 不是对象")
        else:
            keys = contract if isinstance(contract, list) else list(contract.keys())
            for k in keys:
                if k not in result_payload:
                    errors.append(f"result 缺少 output_contract 字段: {k}")
    elif not isinstance(result_payload, (dict, list, str)):
        errors.append("result 字段缺失或类型不对")

    # sources + quote 回溯
    sources = result.get("sources", [])
    if not isinstance(sources, list):
        errors.append("sources 必须是数组")
    else:
        by_id = {}
        if blocks_doc and isinstance(blocks_doc.get("blocks"), list):
            by_id = {b["id"]: b for b in blocks_doc["blocks"]}
        for i, s in enumerate(sources):
            if not isinstance(s, dict):
                errors.append(f"sources[{i}] 不是对象")
                continue
            for k in ("page", "block_id", "quote"):
                if k not in s:
                    errors.append(f"sources[{i}] 缺字段: {k}")
            q = s.get("quote")
            bid = s.get("block_id")
            if q and by_id:
                if bid not in by_id:
                    errors.append(f"sources[{i}] block_id 不存在: {bid}")
                elif str(q).strip() not in by_id[bid].get("text", ""):
                    errors.append(f"sources[{i}] quote 无法在 {bid} 中找到（必须逐字来自原文）")
            elif q and not by_id:
                warnings.append(f"sources[{i}] 未提供 blocks.json，quote 未做回溯校验")

    # uncertainty
    unc = result.get("uncertainty", [])
    if not isinstance(unc, list):
        errors.append("uncertainty 必须是数组")
    else:
        for i, u in enumerate(unc):
            if isinstance(u, dict):
                t = u.get("type")
                if t and t not in VALID_UNC:
                    errors.append(f"uncertainty[{i}].type 非法: {t}")

    if "changes" not in result:
        warnings.append("缺少 changes 记录（建议记录本轮改动）")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--blocks")
    ap.add_argument("--case")
    args = ap.parse_args()
    for p in (args.result, args.blocks, args.case):
        if p and not os.path.isfile(p):
            print(json.dumps({"error": "file not found", "path": p},
                             ensure_ascii=False))
            return 2
    result = load(args.result)
    blocks_doc = load(args.blocks) if args.blocks else None
    case = load(args.case) if args.case else None
    errors, warnings = check(result, blocks_doc, case)
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                      "error_count": len(errors)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
