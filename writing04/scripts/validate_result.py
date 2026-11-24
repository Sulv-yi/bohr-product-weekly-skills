#!/usr/bin/env python3
"""校验 result.json 结构契约（字段齐全、状态合法、来源/差异/不确定性记录存在）。

用法:
    python3 validate_result.py <result.json> [--case case.json]
退出码：通过 0，否则 1。
"""
import argparse
import json
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case', default='')
    args = ap.parse_args()
    r = json.load(open(args.result, encoding='utf-8'))
    errors, warnings = [], []

    if not r.get('case_id'):
        warnings.append("缺 case_id")
    if r.get('status') not in VALID_STATUS:
        errors.append("status 非法: %r" % r.get('status'))
    res = r.get('result')
    if not isinstance(res, dict):
        errors.append("缺 result 对象"); res = {}

    # 六类动作关键产物提示（缺一告警，不强制）
    for f in ('citations', 'numbering', 'deduplication'):
        if f not in res:
            warnings.append("建议产出字段缺失: " + f)
    if not r.get('sources'):
        warnings.append("缺 sources（文献库/稿件来源快照）")
    for f in ('uncertainty', 'changes'):
        if f not in r:
            warnings.append("缺字段 " + f)
    if r.get('status') == 'partial' and not r.get('uncertainty'):
        warnings.append("partial 应写 uncertainty 说明限制")

    if args.case:
        case = json.load(open(args.case, encoding='utf-8'))
        for f in case.get('output_contract', []):
            if f not in res:
                errors.append("输出契约字段缺失: " + f)

    ok = not errors
    print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
