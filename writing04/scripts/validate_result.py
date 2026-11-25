#!/usr/bin/env python3
"""校验 result.json：结构契约 + 成稿实质性（防空壳/占位符/零引用却标 success）。

用法:
    python3 validate_result.py <result.json> [--case case.json] [--min-citations 1]
退出码：通过 0，否则 1；文件错误 2。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}
PLACEHOLDER_RE = re.compile(r'【[^】]*】|\bTODO\b|\bTBD\b|示例文本|待填')


def collect_text(obj):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case', default='')
    ap.add_argument('--min-citations', type=int, default=1)
    args = ap.parse_args()
    try:
        r = json.load(open(args.result, encoding='utf-8'))
    except Exception as e:
        print(json.dumps({'error': 'cannot read result', 'detail': str(e)}, ensure_ascii=False))
        return 2
    errors, warnings = [], []

    if not r.get('case_id'):
        warnings.append("缺 case_id")
    if r.get('status') not in VALID_STATUS:
        errors.append("status 非法: %r" % r.get('status'))
    st = r.get('status')
    res = r.get('result')
    if not isinstance(res, dict):
        errors.append("缺 result 对象"); res = {}

    for f in ('citations', 'numbering', 'deduplication'):
        if f not in res:
            warnings.append("建议产出字段缺失: " + f)
    if not r.get('sources'):
        warnings.append("缺 sources（文献库/稿件来源快照）")
    for f in ('uncertainty', 'changes'):
        if f not in r:
            warnings.append("缺字段 " + f)
    if st == 'partial' and not r.get('uncertainty'):
        warnings.append("partial 应写 uncertainty 说明限制")

    # ---- 成稿实质性 ----
    text = collect_text(res)
    ph = PLACEHOLDER_RE.findall(text)
    if ph:
        if st == 'success':
            errors.append(f"status=success 但正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}")
        else:
            warnings.append(f"正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}")
    cites = res.get('citations')
    if st == 'success':
        if not isinstance(cites, list) or len(cites) < args.min_citations:
            errors.append(f"status=success 但 citations 为空或少于 {args.min_citations} 条（无逐条引用不算完整交付）")
        else:
            for i, c in enumerate(cites):
                if not isinstance(c, dict):
                    errors.append(f"citations[{i}] 不是对象"); continue
                if not c.get('claim'):
                    errors.append(f"citations[{i}] 缺 claim（论断原文）")
                if not c.get('ref_key') and not c.get('ref_id'):
                    errors.append(f"citations[{i}] 缺 ref_key/ref_key（未绑定文献）")
                match = c.get('match')
                if isinstance(match, dict) and not match.get('match_basis'):
                    warnings.append(f"citations[{i}] 缺 match_basis（为何该文献支撑此论断）")
        if not r.get('sources'):
            errors.append("status=success 但 sources 为空，文献来源无法回溯")
    # 状态一致性：自称全部通过但仍有失败项
    if st == 'success' and isinstance(res.get('numbering'), dict):
        nb = res['numbering']
        if nb.get('continuous') is False:
            errors.append("numbering.continuous=false 但 status=success，编号不连续")
        if nb.get('dangling'):
            errors.append(f"存在悬空引用 {nb['dangling'][:5]} 但 status=success")

    if args.case:
        try:
            case = json.load(open(args.case, encoding='utf-8'))
            for f in case.get('output_contract', []):
                if f not in res:
                    errors.append("输出契约字段缺失: " + f)
        except Exception as e:
            warnings.append("无法读取 case: " + str(e))

    ok = not errors
    print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings,
                      "cite_count": len(cites) if isinstance(cites, list) else 0}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
