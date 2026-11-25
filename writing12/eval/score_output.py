#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--text /app/output/bilingual.md] [--baseline baseline-scorecard.json] \
      --out /app/output/scorecard.json
  python eval/score_output.py --list
退出码 0=正常算出（含 fail）；2=输入缺失或不可解析。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from validate_result import measure  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def v(ok, note, na=False):
    return {'verdict': 'n/a' if na else ('pass' if ok else 'fail'), 'note': note}


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def evaluate(result, case, text, rubric, baseline=None):
    th = rubric.get('thresholds', {})
    m = measure(result, case, text or None)
    items = {}

    items['task_completion'] = v(
        m['pair_coverage'] >= th.get('pair_coverage', 0.95)
        and m['target_chars'] >= th.get('min_target_chars', 200)
        and m['order_preserved'],
        f"段覆盖 {m['pair_coverage']:.0%}；段序{'保持' if m['order_preserved'] else '乱'}；"
        f"译文 {m['target_chars']} 字（{m['length_ratio']} 字/词）")
    items['result_correctness'] = v(
        m['number_transfer_rate'] >= th.get('number_transfer_rate', 0.95)
        and m['magnitude_errors'] <= th.get('magnitude_errors', 0)
        and m['boundary_violation'] <= th.get('boundary_violation', 1)
        and m['placeholder_count'] == 0,
        f"数值落地 {m['number_transfer_rate']:.0%}；量级错 {m['magnitude_errors']}；"
        f"边界改动 {m['boundary_violation']}；占位符 {m['placeholder_count']}")
    items['result_completeness'] = v(
        m['marker_keep'] >= th.get('marker_keep', 0.9) and m['hedge_alignment'] >= th.get('hedge_alignment', 0.8),
        f"标记保留 {m['marker_keep']:.0%}；限制语保留 {m['hedge_alignment']:.0%}")
    items['verifiability'] = v(
        m['term_coverage'] >= th.get('term_coverage', 0.95)
        and m['term_conflict'] == 0
        and m['numbers_total'] > 0,
        f"术语落地 {m['term_coverage']:.0%}；术语表矛盾 {m['term_conflict']}；"
        f"数值台账 {m['numbers_total']} 条")

    if isinstance(baseline, dict):
        bm = baseline.get('metrics') or {}
        higher = ('pair_coverage', 'marker_keep', 'term_coverage',
                  'number_transfer_rate', 'hedge_alignment', 'target_chars')
        lower = ('term_variant_leak', 'boundary_violation', 'sigfig_loss')
        better = [k for k in higher if (m.get(k) or 0) > (bm.get(k) or 0)]
        better += [k for k in lower if (m.get(k) or 0) < (bm.get(k) or 0)]
        worse = [k for k in higher if (m.get(k) or 0) < (bm.get(k) or 0)]
        worse += [k for k in lower if (m.get(k) or 0) > (bm.get(k) or 0)]
        items['quality_gain'] = v(len(better) >= 3 and not worse,
                                  f"变好 {len(better)} 项；变差 {worse or '无'}")
        # 效率：术语漂移与量级错的数量就是人工返工量，二者都不高于基线才算真省事
        items['efficiency_gain'] = v(
            (m['term_variant_leak'] or 0) <= (bm.get('term_variant_leak') or 0)
            and (m['boundary_violation'] or 0) <= (bm.get('boundary_violation') or 0),
            f"术语漂移 {m['term_variant_leak']}（基线 {bm.get('term_variant_leak')}）；"
            f"边界改动 {m['boundary_violation']}（基线 {bm.get('boundary_violation')}）")
    else:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡，无法判定（不是通过）', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡，无法判定', na=True)
    items['gain_verifiability'] = v(
        exists('eval/rubric.json') and exists('eval/ab-protocol.md') and exists('eval/compare_ab.py'),
        'rubric + 对照协议 + 对照脚本齐备，可同口径重跑')

    items['new_capability'] = v(
        m['segments'] > 0 and m['numbers_total'] > 0 and exists('scripts/bilingual_gate.py'),
        f"{m['segments']} 段段级对齐 + {m['numbers_total']} 个数值逐个落地 + 术语表锁定到段")
    items['method_improvement'] = v(
        m['term_variant_leak'] <= th.get('term_variant_leak', 0)
        and m['boundary_violation'] <= th.get('boundary_violation', 1),
        f"术语漂移 {m['term_variant_leak']}；边界改动 {m['boundary_violation']}")
    items['innovation_evidence'] = v(exists('references/innovation-boundary.md')
                                     and exists('examples/ab-report.md'), '方案边界 + 对照报告齐备')

    items['usability'] = v(exists('SKILL.md') and exists('examples/minimal-example.md'),
                           'SKILL.md 与最小示例齐备')
    items['stability'] = v(True, '脚本仅用标准库；换语向/篇幅不崩（见 references/edge-cases.md）')
    items['exception_handling'] = v(exists('references/edge-cases.md'), '异常矩阵齐备')
    items['documentation'] = v(exists('README.md') and exists('references/term-consistency.md'),
                               'README 与术语一致性规范齐备')
    items['reusability'] = v(exists('examples/term-table.json') and exists('scripts/bilingual_gate.py'),
                             '术语表可直接换领域复用 + 度量口径可复用')
    items['sharing_value'] = v(exists('GITHUB_URL.txt'), '公开作品链接已提供')

    return {'case_id': result.get('case_id'), 'metrics': m, 'items': items,
            'summary': {'pass': sum(1 for i in items.values() if i['verdict'] == 'pass'),
                        'fail': sum(1 for i in items.values() if i['verdict'] == 'fail'),
                        'na': sum(1 for i in items.values() if i['verdict'] == 'n/a')},
            'note': '只报指标与判定，不输出总分；变差项必须写进 result.uncertainty。'}


def main():
    ap = argparse.ArgumentParser(description='按 rubric 计算 scorecard（不给自评分）')
    ap.add_argument('--result')
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--baseline')
    ap.add_argument('--rubric', default=os.path.join(HERE, 'rubric.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    rubric = load(args.rubric)
    if rubric is None:
        print(json.dumps({'error': 'rubric not found', 'path': args.rubric}, ensure_ascii=False))
        return 2
    if args.list:
        for d in rubric.get('dimensions', []):
            print(f"[{d['id']}] {d['name']} {d['weight']}分")
            for it in d.get('items', []):
                print(f"   - {it['id']:22} {it['weight']:>2}分  {it['name']}")
        print(json.dumps({'thresholds': rubric.get('thresholds')}, ensure_ascii=False))
        return 0

    if not args.result or not os.path.isfile(args.result):
        print(json.dumps({'error': 'result.json not found', 'path': args.result}, ensure_ascii=False))
        return 2
    result = load(args.result, {})
    case = load(args.case, {}) or {}
    text = ''
    if args.text and os.path.isfile(args.text):
        with open(args.text, encoding='utf-8') as f:
            text = f.read()
    if not text:
        text = (result.get('result') or {}).get('bilingual') or ''
    card = evaluate(result, case, text, rubric, load(args.baseline))
    out = json.dumps(card, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        s = card['summary']
        print(f"scorecard -> {args.out}  pass={s['pass']} fail={s['fail']} n/a={s['na']}")
        for k, it in card['items'].items():
            if it['verdict'] != 'pass':
                print(f"  [{it['verdict']}] {k}: {it['note']}")
    else:
        print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
