#!/usr/bin/env python3
"""契约层 + 门槛层：开题方案的结构不对直接拒，度量不达标不判 success。

用法：
  python validate_result.py /app/output/result.json --case /input/case.json --text /app/output/proposal.md
  python validate_result.py ... --json

退出码：0 通过；1 结构错；2 门槛未达。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proposal_gate import (element_map, gap_specific, falsifiable, alignment, schedule,
                           risks, binding_rate, placeholders, _nchars,
                           split_sections, ELEMENTS)  # noqa: E402

REQUIRED_TOP = ['case_id', 'status', 'result', 'sources', 'uncertainty', 'changes']
REQUIRED_RESULT = ['manuscript', 'plan']

GATE_ELEMENTS = 6          # 七要素至少齐 6，缺哪项要在 uncertainty 写明
GATE_ALIGN = 0.9
GATE_RISK = 0.9
GATE_RISK_TYPES = 4
GATE_BINDING = 0.6
GATE_EFFORT = 1.0
MIN_CHARS = 1400


def _section_text(text, pat):
    best = ''
    for _lvl, title, body in split_sections(text):
        if pat.lower() in (title or '').lower() and _nchars(body) > _nchars(best):
            best = body
    return best


def measure(result, text=None):
    r = result.get('result') or {}
    body = text if text else (r.get('manuscript') or '')
    plan = r.get('plan') or {}

    emap = element_map(body)
    got = sum(1 for v in emap.values() if v[0])
    q_text = _section_text(body, '研究问题') or _section_text(body, '问题定义') or body
    gap_ok, gap_note = gap_specific(body, q_text)
    fal_ok, fal_note = falsifiable(q_text)
    align, align_bad = alignment(plan, body)
    sch = schedule(plan)
    risk_ok, risk_n, risk_bad = risks(plan)
    bind, bind_hit, bind_all = binding_rate(body)

    return {
        'total_chars': _nchars(body),
        'elements': {k: {'ok': v[0], 'chars': v[1], 'need': v[2]} for k, v in emap.items()},
        'elements_ok': got,
        'elements_total': len(ELEMENTS),
        'gap_specific': gap_ok,
        'gap_note': gap_note,
        'falsifiable': fal_ok,
        'falsifiable_note': fal_note,
        'alignment_rate': align,
        'alignment_bad': align_bad,
        'schedule_coverage': sch['coverage'],
        'schedule_gaps': sch.get('gaps') or [],
        'schedule_overlap': sch['overlap'],
        'effort_ratio': sch['effort_ratio'],
        'schedule_bad': sch.get('bad') or [],
        'risk_complete': risk_ok,
        'risk_types': risk_n,
        'risk_bad': risk_bad,
        'binding_rate': bind,
        'binding_claims': bind_hit,
        'binding_total': bind_all,
        'placeholder_count': len(placeholders(body)),
    }


def gate(m, min_chars=MIN_CHARS):
    fails = []
    if m['total_chars'] < min_chars:
        fails.append(f"篇幅：{m['total_chars']} 字 < {min_chars}")
    if m['elements_ok'] < GATE_ELEMENTS:
        miss = [k for k, v in m['elements'].items() if not v['ok']]
        fails.append(f"要素：齐 {m['elements_ok']}/{m['elements_total']} < {GATE_ELEMENTS}，缺 {miss}")
    if not m['gap_specific']:
        fails.append('立得住：' + m['gap_note'])
    if not m['falsifiable']:
        fails.append('立得住：研究问题不可证伪（' + m['falsifiable_note'] + '）')
    if m['alignment_rate'] < GATE_ALIGN:
        fails.append(f"对得上：目标-路线-指标-成果对齐 {m['alignment_rate']:.0%} < {GATE_ALIGN:.0%}；"
                     f"{m['alignment_bad']}")
    if not m['schedule_coverage']:
        fails.append(f"排得开：里程碑未覆盖全周期，空月 {m['schedule_gaps']}")
    if m['schedule_overlap']:
        fails.append(f"排得开：里程碑时间重叠 {m['schedule_overlap']} 处")
    if m['effort_ratio'] is not None and m['effort_ratio'] > GATE_EFFORT:
        fails.append(f"排得开：工作量/可用人力 {m['effort_ratio']} > {GATE_EFFORT}")
    if m['risk_complete'] < GATE_RISK:
        fails.append(f"说得清：风险完备率 {m['risk_complete']:.0%} < {GATE_RISK:.0%}；{m['risk_bad']}")
    if m['risk_types'] < GATE_RISK_TYPES:
        fails.append(f"说得清：风险类型覆盖 {m['risk_types']}/4 类")
    if m['binding_rate'] < GATE_BINDING:
        fails.append(f"说得清：论断挂引用 {m['binding_rate']:.0%} < {GATE_BINDING:.0%}")
    if m['placeholder_count']:
        fails.append(f"干净度：占位符 {m['placeholder_count']} 处")
    return fails


def main():
    ap = argparse.ArgumentParser(description='开题方案门槛校验')
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--min-chars', type=int, default=MIN_CHARS)
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    text = open(a.text, encoding='utf-8').read() if a.text else None

    missing = [k for k in REQUIRED_TOP if k not in res]
    missing += [k for k in REQUIRED_RESULT if k not in (res.get('result') or {})]
    if missing:
        print('结构错误：缺字段 ' + ', '.join(missing))
        return 1

    m = measure(res, text)
    fails = gate(m, a.min_chars)
    if a.out:
        json.dump(m, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps(m, ensure_ascii=False, indent=1))
        return 0 if not fails else 2

    print(('passed ' if not fails else 'failed ') + f"case={res.get('case_id')} status={res.get('status')}")
    print(f"  字数={m['total_chars']} 要素={m['elements_ok']}/{m['elements_total']} "
          f"缺口={'具体' if m['gap_specific'] else '空泛'} 可证伪={'是' if m['falsifiable'] else '否'} "
          f"对齐={m['alignment_rate']:.0%} 周期覆盖={'是' if m['schedule_coverage'] else '否'} "
          f"重叠={m['schedule_overlap']} 工作量比={m['effort_ratio']} "
          f"风险完备={m['risk_complete']:.0%}/{m['risk_types']}类 引用绑定={m['binding_rate']:.0%}")
    for f in fails:
        print('  [fail] ' + f)
    return 0 if not fails else 2


if __name__ == '__main__':
    sys.exit(main())
