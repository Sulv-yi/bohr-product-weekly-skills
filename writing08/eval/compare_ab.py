#!/usr/bin/env python3
"""对比两份 scorecard.json，输出 Δ 表与增益判定（只报差值，不报绝对分）。

判定规则写死在 eval/ab-protocol.md 第 4 节，本脚本不含人工加权：
  质量增益成立 ⇐ Δ论断绑定率 ≥ 0 且 Δ分组数 ≥ 0 且 至少两项严格变好
                 且 Δ占位符 ≤ 0（不能靠删内容换指标）
  效率增益成立 ⇐ 技能侧 errors 列表为空（交付前零错误）且不多于基线
                 且 技能侧 contribution_evidence_rate == 1.0

人工确认项（manual_review_items）只展示、不判优劣：这一项少只说明标注得少，
不能说明结果更好。把它放进「越少越好」等于惩罚如实标注——如实写了 2 条
不确定项反而被判「变差」，是评价口径的错，不是产物的错。

用法:
  python eval/compare_ab.py baseline-scorecard.json skill-scorecard.json [--md out.md]
退出码 0=已对比（无论增益是否成立）；2=输入错误。
"""
import argparse
import json
import os
import sys

HIGHER_BETTER = ['four_part_coverage', 'section_total', 'related_groups', 'contributions',
                 'contribution_evidence_rate', 'claim_binding_rate', 'source_count',
                 'source_metadata_rate']
LOWER_BETTER = ['placeholder_count', 'errors_before_accept']
# 只展示、不判优劣：如实标注的不确定项数量随标注详细程度变化，
# 拿它当效率代理会让「标得越诚实」看起来越差。
INFO = ['manual_review_items']


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def get(card, key):
    m = card.get('metrics') or {}
    if key == 'section_total':
        return sum((m.get('section_chars') or {}).values())
    if key == 'errors_before_accept':
        # 交付前必须消除的错误条数：同一评分脚本给出的 errors 列表长度，
        # 可确定性复现，不靠估时。
        return len(card.get('errors') or [])
    return m.get(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline')
    ap.add_argument('skill')
    ap.add_argument('--md', help='同时写一份 Markdown 报告')
    args = ap.parse_args()
    for p in (args.baseline, args.skill):
        if not os.path.isfile(p):
            print(json.dumps({'error': 'not found', 'path': p}, ensure_ascii=False))
            return 2
    a, b = load(args.baseline), load(args.skill)

    rows = []
    for key in HIGHER_BETTER + LOWER_BETTER + INFO:
        va, vb = get(a, key), get(b, key)
        if va is None and vb is None:
            continue
        if key in INFO:
            rows.append({'metric': key, 'baseline': va, 'skill': vb,
                         'delta': (vb or 0) - (va or 0), 'direction': 'info',
                         'improved': False, 'worse': False})
            continue
        direction = 'higher' if key in HIGHER_BETTER else 'lower'
        delta = (vb or 0) - (va or 0)
        better = delta > 0 if direction == 'higher' else delta < 0
        rows.append({'metric': key, 'baseline': va, 'skill': vb, 'delta': delta,
                     'direction': direction, 'improved': better, 'worse': (delta < 0 if direction == 'higher' else delta > 0)})

    improved = [r['metric'] for r in rows if r['improved']]
    worse = [r['metric'] for r in rows if r['worse']]
    q_ok = (get(b, 'claim_binding_rate') or 0) >= (get(a, 'claim_binding_rate') or 0) \
        and (get(b, 'related_groups') or 0) >= (get(a, 'related_groups') or 0) \
        and len(improved) >= 2 and (get(b, 'placeholder_count') or 0) <= (get(a, 'placeholder_count') or 0)
    e_ok = (get(b, 'errors_before_accept') or 0) == 0 \
        and (get(b, 'errors_before_accept') or 0) <= (get(a, 'errors_before_accept') or 0) \
        and (get(b, 'contribution_evidence_rate') or 0) >= 1.0

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
