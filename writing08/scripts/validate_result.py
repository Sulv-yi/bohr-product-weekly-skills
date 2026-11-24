#!/usr/bin/env python3
"""校验 result.json：契约字段、状态、证据映射、不确定性、变更记录。

用法: python validate_result.py <result.json> [--case case.json]
退出码 0=通过, 1=有问题, 2=文件错误。
"""
import sys
import json
import os
import argparse

VALID_STATUS = {'success', 'partial', 'blocked', 'unanswerable'}
VALID_UNC = {'not_reported', 'undetermined', 'conflict', 'needs_human_confirmation'}


def check(result, case):
    errors = []
    warnings = []
    if not isinstance(result, dict):
        return ['顶层必须是对象'], []

    status = result.get('status')
    if status not in VALID_STATUS:
        errors.append(f'status 非法: {status!r}')
    if not result.get('case_id'):
        errors.append('缺少 case_id')
    elif case and case.get('case_id') and str(result['case_id']) != str(case['case_id']):
        errors.append('case_id 与 case.json 不一致')

    contract = case.get('output_contract') if case else None
    payload = result.get('result')
    if contract:
        if not isinstance(payload, dict):
            errors.append('case 有 output_contract，但 result.result 不是对象')
        else:
            keys = contract if isinstance(contract, list) else list(contract.keys())
            for k in keys:
                if k not in payload:
                    errors.append(f'result 缺字段: {k}')
    elif payload is None:
        errors.append('缺少 result 字段')

    sources = result.get('sources', [])
    if not isinstance(sources, list):
        errors.append('sources 必须是数组')
    else:
        for i, s in enumerate(sources):
            if not isinstance(s, dict):
                errors.append(f'sources[{i}] 不是对象')
                continue
            if not s.get('claim'):
                warnings.append(f'sources[{i}] 缺 claim')
            if not s.get('quote'):
                warnings.append(f'sources[{i}] 缺 quote（需可回溯原文）')

    unc = result.get('uncertainty', [])
    if not isinstance(unc, list):
        errors.append('uncertainty 必须是数组')
    else:
        for i, u in enumerate(unc):
            if isinstance(u, dict) and u.get('type') and u['type'] not in VALID_UNC:
                errors.append(f'uncertainty[{i}].type 非法: {u["type"]}')

    if 'changes' not in result:
        warnings.append('缺少 changes 记录')
    if status in ('blocked', 'unanswerable', 'partial') and not unc:
        warnings.append(f'status={status} 但 uncertainty 为空，应说明原因')
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case')
    args = ap.parse_args()
    for p in (args.result, args.case):
        if p and not os.path.isfile(p):
            print(json.dumps({'error': 'file not found', 'path': p}, ensure_ascii=False))
            return 2
    with open(args.result, encoding='utf-8') as f:
        result = json.load(f)
    case = None
    if args.case:
        with open(args.case, encoding='utf-8') as f:
            case = json.load(f)
    errors, warnings = check(result, case)
    print(json.dumps({'ok': not errors, 'errors': errors, 'warnings': warnings,
                      'error_count': len(errors)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
