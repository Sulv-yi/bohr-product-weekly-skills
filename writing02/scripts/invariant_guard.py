#!/usr/bin/env python3
"""改后守恒校验：数字/单位/引用/图表/限定词/否定词不得丢失或强度漂移。

用法: python invariant_guard.py <lock.json> <draft.json|txt> [--out guard.json]
draft.json 优先取 result.polished_text，其次 result.revised / text / polished_text。
纯标准库实现。
"""
import sys
import json
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lock_invariants import lock_text, read_text

# 限定词强度等级：跨级替换 = 失败
LEVELS = {
    'no': 0, 'not': 0, 'none': 0, 'never': 0,
    'may': 1, 'might': 1, 'could': 1, 'possibly': 1, 'suggest': 1,
    'suggests': 1, 'suggested': 1,
    'appear': 2, 'appears': 2, 'seem': 2, 'seems': 2, 'tend': 2,
    'tends': 2, 'likely': 2, 'indicate': 2, 'indicates': 2,
    'generally': 3, 'usually': 3, 'often': 3, 'typically': 3,
    'is': 4, 'are': 4, 'was': 4, 'were': 4, 'demonstrate': 4,
    'demonstrates': 4, 'clearly': 4, 'definitely': 4,
    'all': 5, 'every': 5, 'always': 5, 'invariably': 5, 'must': 5,
}
ZH_LEVELS = {
    '不': 0, '未': 0, '无': 0, '没有': 0,
    '可能': 1, '或许': 1, '提示': 1,
    '似乎': 2, '倾向于': 2, '指示': 2,
    '通常': 3, '一般': 3, '往往': 3,
    '是': 4, '证明': 4, '显然': 4, '必定': 4,
    '所有': 5, '每个': 5, '总是': 5, '必须': 5,
}
CRITICAL = {'number_unit', 'number', 'citation', 'figure_table'}


def draft_text(path):
    if path.endswith('.json'):
        d = json.load(open(path, encoding='utf-8'))
        for getter in (
            lambda x: x['result']['polished_text'],
            lambda x: x['result']['revised'],
            lambda x: x['polished_text'],
            lambda x: x['text'],
            lambda x: x['result']['text'],
        ):
            try:
                v = getter(d)
                if isinstance(v, str) and v.strip():
                    return v
            except (KeyError, TypeError):
                pass
        return json.dumps(d, ensure_ascii=False)
    return open(path, encoding='utf-8').read()


def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'usage: invariant_guard.py <lock.json> <draft.json|txt> [--out guard.json]'}))
        return 2
    lock_path, draft_path = sys.argv[1], sys.argv[2]
    out = 'guard.json'
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    try:
        lock = json.load(open(lock_path, encoding='utf-8'))
        text = draft_text(draft_path)
        revised = lock_text(text)
    except Exception as e:
        print(json.dumps({'error': f'{type(e).__name__}: {e}'}))
        return 2

    before = Counter((x['kind'], x['value'].lower()) for x in lock['counts']
                     for _ in range(x['count']))
    after = Counter((x['kind'], x['value'].lower()) for x in revised['counts']
                    for _ in range(x['count']))

    failures = []
    warnings = []

    # 关键项：不可丢失、不可新增
    for key, n in before.items():
        if key[0] not in CRITICAL:
            continue
        if after.get(key, 0) < n:
            failures.append({'kind': key[0], 'value': key[1],
                             'expected_min': n, 'actual': after.get(key, 0),
                             'reason': '润色后数量减少（丢失数字/单位/引用/图表指向）'})
    for key, n in after.items():
        if key[0] not in CRITICAL:
            continue
        if before.get(key, 0) < n:
            failures.append({'kind': key[0], 'value': key[1],
                             'expected_max': before.get(key, 0), 'actual': n,
                             'reason': '润色后数量增加（新增数字/单位/引用/图表指向）'})

    # 限定词：按等级总量守恒，跨级漂移报警
    def level_total(counter, kind):
        table = ZH_LEVELS if kind == 'hedge_zh' else LEVELS
        agg = Counter()
        for (k, v), n in counter.items():
            if k != kind:
                continue
            lvl = None
            if kind == 'hedge_zh':
                # 中文取最长匹配
                for zh in sorted(table, key=len, reverse=True):
                    if zh in v:
                        lvl = table[zh]
                        break
            else:
                lvl = table.get(v)
            if lvl is not None:
                agg[lvl] += n
        return agg

    for kind in ('hedge', 'hedge_zh'):
        b = level_total(before, kind)
        a = level_total(after, kind)
        for lvl in sorted(set(b) | set(a)):
            if b.get(lvl, 0) != a.get(lvl, 0):
                failures.append({'kind': kind, 'level': lvl,
                                 'expected': b.get(lvl, 0), 'actual': a.get(lvl, 0),
                                 'reason': '限定词强度等级数量变化（语义漂移）'})

    # 否定词总量
    for kind in ('negation', 'negation_zh'):
        b = sum(n for (k, _), n in before.items() if k == kind)
        a = sum(n for (k, _), n in after.items() if k == kind)
        if b != a:
            failures.append({'kind': kind, 'expected': b, 'actual': a,
                             'reason': '否定词数量变化（否定范围可能被改变）'})

    # 逻辑关系词：不允许因果与相关互换
    causal = {'cause', 'causes', 'caused', 'lead to', 'leads to', 'result in',
              'results in', 'due to', 'because', 'therefore', 'thus', 'hence'}
    correl = {'correlate', 'correlates', 'correlated', 'correlation',
              'associate', 'associates', 'associated', 'association'}
    for key, n in before.items():
        if key[0] != 'relation':
            continue
        v = key[1]
        if v in causal and after.get(('relation', v), 0) == 0:
            warnings.append({'value': v, 'reason': '因果关系词消失，人工确认是否改为相关表述'})
        if v in correl and after.get(('relation', v), 0) == 0:
            warnings.append({'value': v, 'reason': '相关关系词消失，人工确认是否改为因果表述'})

    result = {
        'status': 'failed' if failures else ('warning' if warnings else 'passed'),
        'lock_items': len(lock['items']),
        'revised_items': len(revised['items']),
        'failures': failures,
        'warnings': warnings,
        'note': 'passed 仅表示逐字锁定项与强度等级守恒，不替代语义人工判断',
    }
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({'status': result['status'], 'failures': len(failures),
                      'warnings': len(warnings), 'out': out}, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
