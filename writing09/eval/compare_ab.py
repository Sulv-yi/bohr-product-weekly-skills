#!/usr/bin/env python3
"""对比两份 scorecard.json，输出 Δ 表与增益判定（只报差值，不报绝对分）。

判定规则写死在 eval/ab-protocol.md 第 4 节，本脚本不含人工加权：
  质量增益成立 ⇐ Δ六要素覆盖 ≥ 0 且 Δ参数带来源比例 ≥ 0 且 至少两项严格变好
                 且 Δ占位符 ≤ 0（不能靠删内容换指标）
  效率增益成立 ⇐ Δ缺口/待确认条数 ≤ 0 且 技能侧 param_source_rate == 1.0

用法:
  python eval/compare_ab.py baseline-scorecard.json skill-scorecard.json [--md out.md]
退出码 0=已对比；2=输入错误。
"""
import argparse
import json
import os
import sys

HIGHER_BETTER = ['element_coverage', 'section_total', 'param_rows', 'param_source_rate',
                 'param_body_alignment', 'baseline_coverage', 'repro_coverage', 'source_count']
LOWER_BETTER = ['placeholder_count', 'open_gaps']


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def get(card, key):
    m = card.get('metrics') or {}
    if key == 'section_total':
        return sum((m.get('section_chars') or {}).values())
    if key == 'source_count':
        return m.get('source_count')
    v = m.get(key)
    if isinstance(v, bool):
        return 1 if v else 0
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline')
    ap.add_argument('skill')
    ap.add_argument('--md')
    args = ap.parse_args()
    for p in (args.baseline, args.skill):
        if not os.path.isfile(p):
            print(json.dumps({'error': 'not found', 'path': p}, ensure_ascii=False))
            return 2
    a, b = load(args.baseline), load(args.skill)

    rows = []
    for key in HIGHER_BETTER + LOWER_BETTER:
        va, vb = get(a, key), get(b, key)
        if va is None and vb is None:
            continue
        direction = 'higher' if key in HIGHER_BETTER else 'lower'
        delta = (vb or 0) - (va or 0)
        rows.append({'metric': key, 'baseline': va, 'skill': vb, 'delta': delta,
                     'direction': direction,
                     'improved': delta > 0 if direction == 'higher' else delta < 0,
                     'worse': delta < 0 if direction == 'higher' else delta > 0})

    improved = [r['metric'] for r in rows if r['improved']]
    worse = [r['metric'] for r in rows if r['worse']]
    q_ok = (get(b, 'element_coverage') or 0) >= (get(a, 'element_coverage') or 0) \
        and (get(b, 'param_source_rate') or 0) >= (get(a, 'param_source_rate') or 0) \
        and len(improved) >= 2 \
        and (get(b, 'placeholder_count') or 0) <= (get(a, 'placeholder_count') or 0)
    e_ok = (get(b, 'open_gaps') or 0) <= (get(a, 'open_gaps') or 0) \
        and (get(b, 'param_source_rate') or 0) >= 1.0

    out = {'baseline_case': a.get('case_id'), 'skill_case': b.get('case_id'),
           'rows': rows, 'improved': improved, 'worse': worse,
           'quality_gain_holds': q_ok, 'efficiency_gain_holds': e_ok,
           'note': '只报差值；某项变差必须写进 result.uncertainty，不做选择性报告。'}
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.md:
        lines = ['# A/B 对照结果（自动生成）', '',
                 f"- baseline: `{args.baseline}`", f"- skill: `{args.skill}`", '',
                 '| 指标 | baseline | skill | Δ | 方向 |', '|---|---|---|---|---|']
        for r in rows:
            lines.append(f"| {r['metric']} | {r['baseline']} | {r['skill']} | {r['delta']:+.3f} | {r['direction']} |")
        lines += ['', f"- 质量增益成立: **{q_ok}**", f"- 效率增益成立: **{e_ok}**",
                  f"- 变差项: {', '.join(worse) if worse else '无'}"]
        with open(args.md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
