#!/usr/bin/env python3
"""对比两份 scorecard.json，输出 Δ 表与增益判定（只报差值，不报绝对分）。

规则写死在 eval/ab-protocol.md 第 4 节：
  质量增益成立 ⇐ Δ引用闭合率 ≥ 0 且 Δ章节实质字数 > 0 且 至少两项严格变好，
                 且 Δ占位符问题数 ≤ 0，且编译状态不劣化
  效率增益成立 ⇐ Δ编译错误定位率 ≥ 0 且 技能侧 cite_resolved_rate == 1.0

用法: python eval/compare_ab.py baseline-scorecard.json skill-scorecard.json [--md out.md]
"""
import argparse
import json
import os
import sys

HIGHER = ['sections', 'total_real_chars', 'min_section_chars', 'equations', 'tables',
          'cite_keys', 'cite_resolved_rate', 'repro_coverage', 'source_map_count',
          'compile_errors_located_rate']
LOWER = ['compile_errors', 'placeholder_errors']
RANK = {'unavailable': 0, 'skipped': 1, 'not_run': 1, 'timeout': 2, 'failed': 3, 'passed': 4}


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def get(c, k):
    v = (c.get('metrics') or {}).get(k)
    if isinstance(v, bool):
        return int(v)
    return v


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
        d = (vb or 0) - (va or 0)
        direction = 'higher' if k in HIGHER else 'lower'
        rows.append({'metric': k, 'baseline': va, 'skill': vb, 'delta': d, 'direction': direction,
                     'improved': d > 0 if direction == 'higher' else d < 0,
                     'worse': d < 0 if direction == 'higher' else d > 0})
    improved = [r['metric'] for r in rows if r['improved']]
    worse = [r['metric'] for r in rows if r['worse']]
    ca, cb = get(A, 'compile_status'), get(B, 'compile_status')
    compile_ok = RANK.get(cb, 0) >= RANK.get(ca, 0)
    q = (get(B, 'cite_resolved_rate') or 0) >= (get(A, 'cite_resolved_rate') or 0) \
        and (get(B, 'total_real_chars') or 0) > (get(A, 'total_real_chars') or 0) \
        and len(improved) >= 2 and (get(B, 'placeholder_errors') or 0) <= (get(A, 'placeholder_errors') or 0) \
        and compile_ok
    e = (get(B, 'compile_errors_located_rate') or 0) >= (get(A, 'compile_errors_located_rate') or 0) \
        and (get(B, 'cite_resolved_rate') or 0) >= 1.0
    out = {'baseline_case': A.get('case_id'), 'skill_case': B.get('case_id'), 'rows': rows,
           'improved': improved, 'worse': worse,
           'compile_status': {'baseline': ca, 'skill': cb},
           'quality_gain_holds': q, 'efficiency_gain_holds': e,
           'note': '只报差值；变差项必须写进 result.uncertainty，不做选择性报告。'}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if a.md:
        lines = ['# A/B 对照结果（自动生成）', '', f"- baseline: `{a.baseline}`", f"- skill: `{a.skill}`", '',
                 '| 指标 | baseline | skill | Δ | 方向 |', '|---|---|---|---|---|']
        for r in rows:
            lines.append(f"| {r['metric']} | {r['baseline']} | {r['skill']} | {r['delta']:+.3f} | {r['direction']} |")
        lines += ['', f"- 编译状态: baseline=`{ca}` → skill=`{cb}`",
                  f"- 质量增益成立: **{q}**", f"- 效率增益成立: **{e}**",
                  f"- 变差项: {', '.join(worse) if worse else '无'}"]
        open(a.md, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
