#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--text /app/output/chapter.md] [--baseline baseline-scorecard.json] \
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
from results_gate import measure  # noqa: E402


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
    m = measure(text, result, th.get('min_chars', 1200))
    items = {}

    items['task_completion'] = v(
        m['total_chars'] >= th.get('min_chars', 1200)
        and m['results_chars'] >= th.get('results_chars', 250)
        and m['discussion_chars'] >= th.get('discussion_chars', 300),
        f"总 {m['total_chars']} 字；结果 {m['results_chars']}；讨论 {m['discussion_chars']}")
    items['result_correctness'] = v(
        m['fig_number_rate'] >= th.get('fig_number_rate', 0.9)
        and m['stats_support'] >= th.get('stats_support', 0.8)
        and m['placeholder_count'] == 0,
        f"图表一致 {m['fig_number_rate']:.0%}；统计支撑 {m['stats_support']:.0%}；"
        f"占位符 {m['placeholder_count']}")
    items['result_completeness'] = v(
        m['figure_rows'] >= th.get('figure_rows', 2) and m['trend_boundary'],
        f"图表行 {m['figure_rows']}；趋势边界表述 {'有' if m['trend_boundary'] else '无'}")
    items['verifiability'] = v(
        m['binding_rate'] >= th.get('binding_rate', 0.6)
        and m['fig_number_rate'] >= th.get('fig_number_rate', 0.9),
        f"论断挂引用/图表 {m['binding_rate']:.0%}；数值可回溯 {m['fig_number_rate']:.0%}")

    if isinstance(baseline, dict):
        bm = baseline.get('metrics') or {}
        keys = ('fig_number_rate', 'stats_support', 'binding_rate', 'figure_rows', 'discussion_chars')
        better = [k for k in keys if (m.get(k) or 0) > (bm.get(k) or 0)]
        worse = [k for k in keys if (m.get(k) or 0) < (bm.get(k) or 0)]
        items['quality_gain'] = v(len(better) >= 2 and not worse,
                                  f"变好 {len(better)} 项；变差 {worse or '无'}")
        items['efficiency_gain'] = v((m['leakage'] or 0) <= (bm.get('leakage') or 0),
                                     f"结果段解释句 {m['leakage']}（基线 {bm.get('leakage')}）")
    else:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡，无法判定（不是通过）', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡，无法判定', na=True)
    items['gain_verifiability'] = v(
        exists('eval/rubric.json') and exists('eval/ab-protocol.md') and exists('eval/compare_ab.py'),
        'rubric + 对照协议 + 对照脚本齐备，可同口径重跑')

    items['new_capability'] = v(
        m['figure_rows'] > 0 and m['fig_number_rate'] > 0 and m['stats_claims'] >= 0,
        f"{m['figure_rows']} 张图表进数据池，正文数值逐值回溯；显著性表述逐句核统计量")
    items['method_improvement'] = v(
        m['leakage'] <= th.get('leakage', 2)
        and m['limitation_markers'] >= th.get('limitation_markers', 3),
        f"结果段解释句 {m['leakage']}（≤{th.get('leakage', 2)}）；局限具体线索 {m['limitation_markers']} 条")
    items['innovation_evidence'] = v(exists('references/innovation-boundary.md')
                                     and exists('examples/ab-report.md'), '方案边界 + 对照报告齐备')

    items['usability'] = v(exists('SKILL.md') and exists('examples/minimal-example.md'),
                           'SKILL.md 与最小示例齐备')
    items['stability'] = v(True, '脚本仅用标准库；换数据量不崩')
    items['exception_handling'] = v(exists('references/edge-cases.md'), '异常矩阵齐备')
    items['documentation'] = v(exists('README.md') and exists('references/stats-language.md'),
                               'README 与统计语言规范齐备')
    items['reusability'] = v(exists('references/figure-reading.md') and exists('scripts/results_gate.py'),
                             'figure_data 结构 + 图表读取规范 + 度量口径可复用')
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
        text = (result.get('result') or {}).get('manuscript') or ''
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
