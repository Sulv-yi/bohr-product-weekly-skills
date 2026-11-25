#!/usr/bin/env python3
"""校验 result.json：契约字段、状态、证据映射、不确定性、变更记录，
以及【成稿实质性】——防止只交空壳/占位符却标 success 拿到高分的漏洞。

用法: python validate_result.py <result.json> [--case case.json] [--min-chars 200]
退出码 0=通过, 1=有问题, 2=文件错误。
"""
import sys
import json
import os
import re
import argparse

VALID_STATUS = {'success', 'partial', 'blocked', 'unanswerable'}
VALID_UNC = {'not_reported', 'undetermined', 'conflict', 'needs_human_confirmation'}
# 成稿中禁止残留的占位标记（骨架阶段的槽位，定稿必须清空）
PLACEHOLDER_RE = re.compile(r'【[^】]*】|\[证据槽\]|\[evidence slot\]|\bTODO\b|\bTBD\b|示例文本|非正式结果')


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


def check(result, case, min_chars=200):
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
    keys = []
    if contract:
        keys = contract if isinstance(contract, list) else list(contract.keys())
        if not isinstance(payload, dict):
            errors.append('case 有 output_contract，但 result.result 不是对象')
        else:
            for k in keys:
                if k not in payload:
                    errors.append(f'result 缺字段: {k}')
    elif payload is None:
        errors.append('缺少 result 字段')

    # ---- 成稿实质性：标 success 必须交出成稿本体，不是骨架/空话 ----
    draft_text = collect_text(payload)
    nchars = len(re.sub(r'\s', '', draft_text))
    if status == 'success' and nchars < min_chars:
        errors.append(f'status=success 但成稿正文仅 {nchars} 字（<{min_chars}），疑似空壳')
    ph = PLACEHOLDER_RE.findall(draft_text)
    if ph:
        if status == 'success':
            errors.append(f'status=success 但正文残留占位符 {len(ph)} 处：{sorted(set(ph))[:5]}')
        else:
            warnings.append(f'正文残留占位符 {len(ph)} 处（partial 可接受但定稿须清）：{sorted(set(ph))[:5]}')

    # 四要素齐全性（背景/相关工作/空白/贡献）——正文或键名任一命中即可
    four = ['背景', '相关工作', '研究空白', '贡献']
    hit = {name: (name in draft_text or any(name in str(k) for k in keys)) for name in four}
    missing = [name for name, ok in hit.items() if not ok]
    if status == 'success' and missing:
        warnings.append(f'success 但未显式覆盖四要素中的: {", ".join(missing)}（请确认是否被合并表述）')

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
        if status == 'success' and not sources:
            errors.append('status=success 但 sources 为空，无法逐条回溯（零来源不能算完整解答）')

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
    ap.add_argument('--min-chars', type=int, default=200)
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
    errors, warnings = check(result, case, args.min_chars)
    print(json.dumps({'ok': not errors, 'errors': errors, 'warnings': warnings,
                      'error_count': len(errors)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
