#!/usr/bin/env python3
"""输出契约与状态自检 + 成稿实质性检查（防只交骨架/空壳却标 success）。

用法:
    python3 validate_result.py <result.json> [--case case.json] [--min-chars 200]

检查：case_id 一致、status 合法、result 含目标产物/elements/reproducibility/
questions_for_author/limitations、sources 可回溯、change 记录、缺口与状态一致；
标 success 时正文须达最小篇幅且无占位符，六类要素须齐全。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {"success", "partial", "unable", "refused"}
REQUIRED_RESULT = ["section", "elements", "reproducibility", "questions_for_author", "limitations"]
PLACEHOLDER_RE = re.compile(r'【[^】]*】|\bTODO\b|\bTBD\b|待填|示例文本')
SIX_ELEMENTS = ["steps", "setup", "parameters", "dataset", "baselines", "reproducibility"]


def _collect_text(obj):
    parts = []
    def walk(x):
        if isinstance(x, str):
            parts.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return "\n".join(parts)


def validate(result, case, min_chars=200):
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

    # ---- 成稿实质性 ----
    section = r.get("section", "")
    nchars = len(re.sub(r'\s', '', section if isinstance(section, str) else _collect_text(section)))
    if st == "success" and nchars < min_chars:
        errors.append(f"status=success 但 section 正文仅 {nchars} 字（<{min_chars}），疑似空壳")
    ph = PLACEHOLDER_RE.findall(_collect_text(r))
    if ph:
        if st == "success":
            errors.append(f"status=success 但正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}")
        else:
            warnings.append(f"正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}")
    elems = r.get("elements") or {}
    if st == "success":
        miss6 = [e for e in SIX_ELEMENTS if e not in elems or not elems[e]]
        if miss6:
            errors.append(f"status=success 但缺六类要素: {', '.join(miss6)}")
        if not result.get("sources"):
            errors.append("status=success 但 sources 为空，数值/步骤无法回溯")
    rep = r.get("reproducibility") or {}
    if st == "success":
        gaps = [k for k, v in rep.items() if isinstance(v, str) and (not v or '【' in v or 'not_reported' in v)]
        if gaps:
            warnings.append(f"复现清单未落实字段: {', '.join(gaps)}（应填真实值或在 uncertainty 标 not_reported）")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors, "warnings": warnings, "case_id": cid,
        "section_chars": nchars,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--case")
    ap.add_argument("--min-chars", type=int, default=200)
    args = ap.parse_args()
    result = json.load(open(args.result, encoding="utf-8"))
    case = json.load(open(args.case, encoding="utf-8")) if args.case else None
    rep = validate(result, case, args.min_chars)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
