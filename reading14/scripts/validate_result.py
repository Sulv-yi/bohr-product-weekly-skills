#!/usr/bin/env python3
"""输出契约与状态自检（阅读14 专用）。

用法:
    python3 validate_result.py <result.json> [--case case.json]

检查 case_id / status / result 顶层字段 / nanopublications 结构 /
sources / uncertainty / changes，及 partial 状态的 uncertainty。
与 verify_nanopub.py 分工：本脚本只看结构与契约齐全，四性质由 verify_nanopub.py 负责。
"""
import argparse
import json
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}


def validate(result, case):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是对象']}
    cid = result.get('case_id')
    if not cid:
        errors.append('缺少 case_id')
    if case:
        exp = case.get('case_id')
        if exp and str(cid) != str(exp):
            errors.append(f'case_id 不符: 期望 {exp}, 得到 {cid}')
        for f in (case.get('output_contract') or []):
            if f not in (result.get('result') or {}):
                errors.append(f'result 缺少契约字段: {f}')
    st = result.get('status')
    if st not in VALID_STATUS:
        errors.append(f'status 非法: {st}')
    nps = (result.get('result') or {}).get('nanopublications')
    if not isinstance(nps, list) or not nps:
        errors.append('result.nanopublications 缺失或为空')
    for f in ('sources', 'uncertainty', 'changes'):
        if f not in result:
            errors.append(f'缺少顶层字段: {f}')
    if st in ('partial', 'unable', 'refused') and not (result.get('uncertainty') or []):
        errors.append(f'status={st} 时必须给出 uncertainty')
    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors, 'warnings': warnings,
        'case_id': cid, 'status_value': st,
        'nanopub_count': len(nps) if isinstance(nps, list) else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case')
    args = ap.parse_args()
    result = json.load(open(args.result, encoding='utf-8'))
    case = json.load(open(args.case, encoding='utf-8')) if args.case else None
    rep = validate(result, case)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
