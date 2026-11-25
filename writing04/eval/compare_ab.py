#!/usr/bin/env python3
"""对比两份 scorecard.json，输出 Δ 表与增益判定（只报差值，不报绝对分）。

规则写死在 eval/ab-protocol.md 第 4 节，脚本不含人工加权：
  质量增益成立 ⇐ Δmatch_basis_rate ≥ 0 且 Δclaim_location_rate ≥ 0 且 至少两项严格变好
                 且 Δplaceholder_count ≤ 0
  效率增益成立 ⇐ Δopen_items ≤ 0 且 技能侧 match_basis_rate == 1.0

用法: python eval/compare_ab.py baseline-scorecard.json skill-scorecard.json [--md out.md]
"""
import argparse
import json
import os
import sys

HIGHER = ['claim_rate', 'claim_location_rate', 'match_basis_rate', 'position_ok_rate',
          'ref_resolved_rate', 'cite_count', 'format_mapping_fields', 'preserved_fields']
LOWER = ['dangling_count', 'placeholder_count', 'open_items']


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def get(card, k):
    v = (card.get('metrics') or {}).get(k)
    return int(v) if isinstance(v, bool) else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline'); ap.add_argument('skill'); ap.add_argument('--md')
    a = ap.parse_args()
    for p in (a.baseline, a.skill):
        if not os.path.isfile(p):
            print(json.dumps({'error': 'not found', 'path': p}, ensure_ascii=False)); return 2
    A, B = load(a.baseline), load(a.skill)
    rows = []
    for k in HIGHER + LOWER:
        va, vb = get(A, k), get(B, k)
        if va is None and vb is None:
            continue
        direction = 'higher' if k in HIGHER else 'lower'
        d = (vb or 0) - (va or 0)
        rows.append({'metric': k, 'baseline': va, 'skill': vb, 'delta': d, 'direction': direction,
                     'improved': d > 0 if direction == 'higher' else d < 0,
                     'worse': d < 0 if direction == 'higher' else d > 0})
    improved = [r['metric'] for r in rows if r['improved']]
    worse = [r['metric'] for r in rows if r['worse']]
    q = (get(B, 'match_basis_rate') or 0) >= (get(A, 'match_basis_rate') or 0) \
        and (get(B, 'claim_location_rate') or 0) >= (get(A, 'claim_location_rate') or 0) \
        and len(improved) >= 2 and (get(B, 'placeholder_count') or 0) <= (get(A, 'placeholder_count') or 0)
    e = (get(B, 'open_items') or 0) <= (get(A, 'open_items') or 0) and (get(B, 'match_basis_rate') or 0) >= 1.0
    out = {'baseline_case': A.get('case_id'), 'skill_case': B.get('case_id'), 'rows': rows,
           'improved': improved, 'worse': worse, 'quality_gain_holds': q, 'efficiency_gain_holds': e,
           'note': '只报差值；变差项必须写进 result.uncertainty，不做选择性报告。'}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.md:
        lines = ['# A/B 对照结果（自动生成）', '', f"- baseline: `{a.baseline}`", f"- skill: `{a.skill}`", '',
                 '| 指标 | baseline | skill | Δ | 方向 |', '|---|---|---|---|---|']
        for r in rows:
            lines.append(f"| {r['metric']} | {r['baseline']} | {r['skill']} | {r['delta']:+.3f} | {r['direction']} |")
        lines += ['', f"- 质量增益成立: **{q}**", f"- 效率增益成立: **{e}**",
                  f"- 变差项: {', '.join(worse) if worse else '无'}"]
        open(a.md, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
