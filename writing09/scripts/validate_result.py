#!/usr/bin/env python3
"""输出契约与状态自检 + 成稿结构门槛（防只交骨架/空壳/薄稿却标 success）。

用法:
    python3 validate_result.py <result.json> [--case case.json] [--min-chars 1800] [--text section.md]

检查两层：
1) 契约层——case_id 一致、status 合法、output_contract 字段齐全、sources/uncertainty/changes 存在、
   blocking 追问与 status 一致。
2) 结构层——六要素是否各自成段、参数表行数与来源列、正文与参数表取值是否对齐、
   对照六项（基线/版本/同预算/指标/统计/重复）、复现六项（版本/环境/种子/命令/数据/划分）、
   限制是否落到具体失效场景。度量实现在 scripts/quality_gate.py。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_gate import measure  # noqa: E402

VALID_STATUS = {"success", "partial", "unable", "refused"}
REQUIRED_RESULT = ["section", "elements", "reproducibility", "questions_for_author", "limitations"]
PLACEHOLDER_RE = re.compile(r'【[^】]*】|\bTODO\b|\bTBD\b|待填|示例文本')
SIX_ELEMENTS = ["steps", "setup", "parameters", "dataset", "baselines", "reproducibility"]

GATE_PARAM_ROWS = 8          # 参数表至少 8 行，否则等于没给参数
GATE_PARAM_SOURCE = 0.8      # 带来源列的行占比
GATE_BASELINE = 0.83         # 对照六项命中率（5/6）
GATE_REPRO = 0.83            # 复现六项命中率（5/6）
GATE_ALIGN = 0.8             # 正文与参数表取值对齐率


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


def validate(result, case, min_chars=0, extra_text=""):
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

    # ---- 结构门槛 ----
    section = r.get("section", "")
    section_text = section if isinstance(section, str) else _collect_text(section)
    text = section_text + "\n" + (extra_text or "")
    # measure(elem_text, body_text, uncertainty, questions, min_chars)：
    # 原来把 uncertainty 传进了 body_text 位，issues 计数与人工核对项都会错位。
    m = measure(text, None, result.get("uncertainty") or [], r.get("questions_for_author") or [],
                min_chars=min_chars or None)
    nchars = m["total_chars"]

    if st == "success":
        if not m["min_chars_ok"]:
            errors.append(f"status=success 但篇幅不足（中文 {m['cjk_chars']} 字 / 英文 {m['en_words']} 词），"
                          f"疑似空壳或薄稿；中文需 ≥1800 字，英文需 ≥1100 词")
        if m["missing_elements"]:
            errors.append(f"六类要素缺件: {', '.join(m['missing_elements'])}（步骤/设置/参数/数据/对照/复现限制须各自成段）")
        if m["param_rows"] < GATE_PARAM_ROWS:
            errors.append(f"参数表仅 {m['param_rows']} 行（需 ≥{GATE_PARAM_ROWS} 行，名称/取值/单位/作用对象/来源）")
        elif m["param_source_rate"] < GATE_PARAM_SOURCE:
            errors.append(f"参数表带来源的行仅 {m['param_source_rate']:.0%}（需 ≥{GATE_PARAM_SOURCE:.0%}，来源=config/log/作者确认）")
        if m["baseline_coverage"] < GATE_BASELINE:
            miss = [k for k in ('baseline_identity', 'baseline_version', 'same_budget', 'metric', 'statistics', 'repeats')
                    if k not in m["baseline_checks"]]
            errors.append(f"对照实验缺可比性要件: {', '.join(miss)}（需说明基线对象/版本/是否同预算/指标/统计方式/重复次数）")
        if m["repro_coverage"] < GATE_REPRO:
            miss = [k for k in ('code_version', 'env', 'seed', 'command', 'data_source', 'split')
                    if k not in m["repro_checks"]]
            errors.append(f"复现清单缺项: {', '.join(miss)}（代码版本/环境/种子/命令/数据获取/划分）")
        if not m["limitation_specific"]:
            errors.append("限制条件未落到具体失效场景（需写出触发条件或阈值，如『当体素边长 <0.01 m 时…』）")
        if m["placeholder_count"]:
            errors.append(f"status=success 但正文残留占位符 {m['placeholder_count']} 处")
        bad = [k for k, ok in m["section_min_ok"].items() if not ok]
        if bad:
            warnings.append(f"章节厚度偏薄（建议补齐再定稿）: {bad}")
        if m["param_rows"] and m["param_body_alignment"] < GATE_ALIGN:
            warnings.append(f"正文与参数表取值对齐率 {m['param_body_alignment']:.0%}，存在正文未引用的表内取值或表外数值")
        if not result.get("sources"):
            errors.append("status=success 但 sources 为空，数值/步骤无法回溯")
    else:
        ph = PLACEHOLDER_RE.findall(_collect_text(r))
        if ph:
            warnings.append(f"正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}")

    rep = r.get("reproducibility") or {}
    if st == "success":
        gaps = [k for k, v in rep.items() if isinstance(v, str) and (not v or '【' in v or 'not_reported' in v)]
        if gaps:
            warnings.append(f"复现清单未落实字段: {', '.join(gaps)}（应填真实值或在 uncertainty 标 not_reported）")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors, "warnings": warnings, "case_id": cid,
        "section_chars": nchars, "metrics": m,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--case")
    ap.add_argument("--min-chars", type=int, default=0,
                    help="显式篇幅门槛；0=按语言自适应（中文 1800 字 / 英文 1100 词）")
    ap.add_argument("--text", help="成稿正文文件（section.md），正文不在 result.json 内时一并度量")
    args = ap.parse_args()
    result = json.load(open(args.result, encoding="utf-8"))
    case = json.load(open(args.case, encoding="utf-8")) if args.case else None
    extra = open(args.text, encoding="utf-8").read() if args.text else ""
    rep = validate(result, case, args.min_chars, extra)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
