"""科研成果转化写作的门槛校验：契约层 + 门槛层。

用法：
  python3 scripts/validate_result.py result.json --case case.json --text popular.md
  python3 scripts/validate_result.py result.json --text popular.md --json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from popularize_gate import (  # noqa: E402
    abbrev_check, analogy_present, audience_fit, changelog_rate, hedge_retention,
    placeholders, readability, retention, strength_align, term_consistency, trace_rate,
    _nchars,
)

MIN_CHARS = 900
GATE_ABBREV = 0.9
GATE_LONG = 0.3
GATE_JARGON = 0.35
GATE_NUM = 0.9
GATE_LIMIT = 0.7
GATE_HEDGE_KEEP = 0.8
MAX_STRENGTH_BAD = 0
MAX_TERM_DRIFT = 0
GATE_CHANGELOG = 0.8
GATE_TRACE = 0.8
MIN_ANALOGY = 2
MAX_PLACEHOLDER = 0
MIN_SECTIONS = 3


REQUIRED_KEYS = ['task', 'audience', 'source_ref', 'target_path', 'terms', 'changes']


def contract(res):
    """契约层：result.json 的必需字段与类型。"""
    bad = []
    for k in REQUIRED_KEYS:
        if k not in res:
            bad.append(f'缺字段 {k}')
    if not isinstance(res.get('terms'), list) or not res.get('terms'):
        bad.append('terms 必须是非空列表 [(概念, [变体...])]')
    if not isinstance(res.get('changes'), list) or not res.get('changes'):
        bad.append('changes 必须是逐条改动清单')
    tp = res.get('target_path')
    if tp and not os.path.exists(tp):
        # target_path 可能相对于 result.json 所在目录
        alt = os.path.join(os.path.dirname(os.path.abspath(res.get('_path', '.'))), tp)
        if not os.path.exists(alt):
            bad.append(f'target_path 不存在: {tp}')
    return bad


def measure(res, case, text):
    source = res.get('source_text') or ''
    if not source and res.get('source_path') and os.path.exists(res['source_path']):
        source = open(res['source_path'], encoding='utf-8').read()
    if not source:
        # 从 case 里取
        for k in ('materials', 'source', 'excerpt'):
            if isinstance(case.get(k), str):
                source = case[k]
                break

    # 缩写展开只看正文：修改清单里为说明"删了什么"而引用原缩写，不算未展开
    import re as _re
    body_only = '\n'.join(
        b for _l, t, b in __import__('popularize_gate').split_sections(text)
        if not _re.search(r'修改|变更|改动|清单', t or '')
    ) or text
    a_rate, a_rows = abbrev_check(source, body_only)
    rd = readability(text)
    ana_n, ana_hits = analogy_present(text)
    ret = retention(source, text)
    hr = hedge_retention(source, text)
    sa = strength_align(source, text)
    tc = term_consistency(text, res.get('terms') or [])
    cl = changelog_rate(text)
    tr = trace_rate(text)
    af = audience_fit(text, res.get('audience') or '')
    ph = placeholders(text)
    secs = [
        _l for _l, _t, _b in __import__('popularize_gate').split_sections(text)
    ]

    return {
        'chars': _nchars(text),
        'sections': len(secs),
        'abbrev_rate': a_rate,
        'abbrev_missing': [r[0] for r in a_rows if not r[1]][:8],
        'avg_sent_len': rd['avg_len'],
        'long_sent_ratio': rd['long_ratio'],
        'long_sents': rd['long_sents'],
        'jargon_density': rd['jargon_density'],
        'analogies': ana_n,
        'analogy_hits': [h for h in ana_hits if h[1]],
        'num_total': ret['num_total'],
        'num_rate': ret['num_rate'],
        'num_missing': ret['num_missing'],
        'limit_total': ret['limit_total'],
        'limit_rate': ret['limit_rate'],
        'limit_missing': ret['limit_missing'],
        'figtab_rate': ret['figtab_rate'],
        'figtab_missing': ret['figtab_missing'],
        'hedge_src': hr['src_hedged'],
        'hedge_tgt': hr['tgt_hedged'],
        'hedge_keep': hr['keep_rate'],
        'assertive_sents': hr['tgt_assertive'],
        'strength_sents': sa['strong_sents'],
        'strength_bad': sa['violations'],
        'strength_bad_rows': sa['bad_rows'],
        'term_drift': tc['drift'],
        'term_drift_rows': tc['drift_rows'],
        'changelog_total': cl['total'],
        'changelog_rate': cl['rate'],
        'trace_claims': tr['claims'],
        'trace_hit': tr['traced'],
        'trace_rate': tr['rate'],
        'audience_declared': af['audience_declared'],
        'purpose_declared': af['purpose_declared'],
        'placeholders': ph,
    }


def gate(m):
    """门槛层：返回失败项列表。"""
    fails = []
    if m['chars'] < MIN_CHARS:
        fails.append(f"篇幅：{m['chars']} 字 < {MIN_CHARS}")
    if m['sections'] < MIN_SECTIONS:
        fails.append(f"结构：{m['sections']} 节 < {MIN_SECTIONS}")
    if m['abbrev_rate'] < GATE_ABBREV:
        fails.append(f"缩写展开：{m['abbrev_rate']:.0%} < {GATE_ABBREV:.0%}，未展开 {m['abbrev_missing']}")
    if m['long_sent_ratio'] > GATE_LONG:
        fails.append(f"长句占比：{m['long_sent_ratio']:.0%} > {GATE_LONG:.0%}，如 {m['long_sents'][:2]}")
    if m['jargon_density'] > GATE_JARGON:
        fails.append(f"术语密集句：{m['jargon_density']:.0%} > {GATE_JARGON:.0%}")
    if m['analogies'] < MIN_ANALOGY:
        fails.append(f"类比/解释性衔接：{m['analogies']} 处 < {MIN_ANALOGY}")
    if m['num_rate'] < GATE_NUM:
        fails.append(f"数值保留：{m['num_rate']:.0%} < {GATE_NUM:.0%}，丢失 {m['num_missing']}")
    if m['limit_total'] and m['limit_rate'] < GATE_LIMIT:
        fails.append(f"限定条件保留：{m['limit_rate']:.0%} < {GATE_LIMIT:.0%}，丢失 {m['limit_missing']}")
    if m['hedge_keep'] < GATE_HEDGE_KEEP:
        fails.append(f"限定语保留：{m['hedge_keep']:.0%} < {GATE_HEDGE_KEEP:.0%}（源 {m['hedge_src']} 句 → 成稿 {m['hedge_tgt']} 句）")
    if m['strength_bad'] > MAX_STRENGTH_BAD:
        fails.append(f"论断越界：{m['strength_bad']} 句强断言既无限定语也无溯源，如 {m['strength_bad_rows'][:1]}")
    if m['term_drift'] > MAX_TERM_DRIFT:
        fails.append(f"术语漂移：{m['term_drift']} 个概念多说法，如 {m['term_drift_rows'][:1]}")
    if m['changelog_rate'] < GATE_CHANGELOG:
        fails.append(f"修改清单：覆盖 {m['changelog_rate']:.0%} < {GATE_CHANGELOG:.0%}（{m['changelog_total']} 条 / {m['chars']} 字稿）")
    if m['trace_rate'] < GATE_TRACE:
        fails.append(f"溯源：{m['trace_rate']:.0%} < {GATE_TRACE:.0%}（{m['trace_hit']}/{m['trace_claims']} 条论断）")
    if len(m['placeholders']) > MAX_PLACEHOLDER:
        fails.append(f"占位符：{len(m['placeholders'])} 处 {m['placeholders'][:3]}")
    return fails


def main():
    global MIN_CHARS
    ap = argparse.ArgumentParser(description='科研成果转化写作门槛校验')
    ap.add_argument('result')
    ap.add_argument('--case', default=None)
    ap.add_argument('--text', default=None, help='成稿路径（默认取 result.target_path）')
    ap.add_argument('--min-chars', type=int, default=MIN_CHARS)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    res['_path'] = a.result
    case = json.load(open(a.case, encoding='utf-8')) if a.case else {}
    tp = a.text or res.get('target_path')
    if not tp or not os.path.exists(tp):
        alt = os.path.join(os.path.dirname(os.path.abspath(a.result)), tp or '')
        tp = alt if os.path.exists(alt) else None
    if not tp:
        print('找不到成稿文件', file=sys.stderr)
        sys.exit(2)
    text = open(tp, encoding='utf-8').read()

    MIN_CHARS = a.min_chars
    cb = contract(res)
    m = measure(res, case, text)
    fails = gate(m)

    if a.json:
        print(json.dumps({'contract': cb, 'metrics': m, 'fails': fails}, ensure_ascii=False, indent=1))
        return

    print(f"字数={m['chars']} 节={m['sections']} 缩写展开={m['abbrev_rate']:.0%} "
          f"句均长={m['avg_sent_len']} 长句={m['long_sent_ratio']:.0%} 术语密集={m['jargon_density']:.0%} 类比={m['analogies']}")
    print(f"数值={m['num_rate']:.0%}({m['num_total']}) 限定条件={m['limit_rate']:.0%} 图表={m['figtab_rate']:.0%} "
          f"限定语={m['hedge_keep']:.0%}")
    print(f"越界断言={m['strength_bad']} 术语漂移={m['term_drift']} 修改清单={m['changelog_total']} "
          f"溯源={m['trace_rate']:.0%} 占位符={len(m['placeholders'])}")
    if cb:
        print('\n契约层失败:')
        for x in cb:
            print('  -', x)
    if fails:
        print('\n门槛未通过:')
        for x in fails:
            print('  -', x)
    ok = not cb and not fails
    print('\n结果:', 'passed' if ok else 'failed')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
