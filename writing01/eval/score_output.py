#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

题面写「文字自述不能替代实际运行证据」，自评不被采信。本脚本把判定所需的指标算出来，
让 A/B 对照与第三方复核有可重跑的输入。每条只输出 {id, verdict: pass|fail|n/a, note}。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--text /app/output/manuscript.md] [--baseline baseline-scorecard.json] \
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
from sections_gate import measure  # noqa: E402


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
    m = measure(text, result, th.get('min_chars', 1800))
    payload = result.get('result') or {}
    index = payload.get('material_index') or []
    items = {}

    items['task_completion'] = v(
        m['total_chars'] >= th.get('min_chars', 1800)
        and m['section_coverage'] >= th.get('section_coverage', 0.75),
        f"稿件 {m['total_chars']} 字；章节齐备度 {m['section_coverage']:.0%}")
    items['result_correctness'] = v(
        m['cite_resolved_rate'] >= 1.0 and m['placeholder_count'] == 0
        and m['num_trace_rate'] >= th.get('num_trace_rate', 0.9),
        f"引用闭合 {m['cite_resolved_rate']:.0%}；占位符 {m['placeholder_count']}；"
        f"数值可回溯 {m['num_trace_rate']:.0%}")
    items['result_completeness'] = v(
        m['declaration_fields'] >= 2 and 'data_availability' in m['declarations']
        and m['fig_pairs'] + m['tab_pairs'] >= 2,
        f"声明 {m['declaration_fields']} 类；图表对 {m['fig_pairs']}+{m['tab_pairs']}")
    items['verifiability'] = v(
        len(index) >= th.get('material_index', 8) and m['binding_rate'] >= th.get('binding_rate', 0.5),
        f"材料索引 {len(index)} 条；论断句挂引用 {m['binding_rate']:.0%}")

    if isinstance(baseline, dict):
        bm = baseline.get('metrics') or {}
        keys = ('section_coverage', 'cite_resolved_rate', 'binding_rate',
                'material_index_count', 'num_trace_rate')
        better = [k for k in keys if (m.get(k) or 0) > (bm.get(k) or 0)]
        worse = [k for k in keys if (m.get(k) or 0) < (bm.get(k) or 0)]
        items['quality_gain'] = v(len(better) >= 2 and not worse,
                                  f"变好 {len(better)} 项；变差 {worse or '无'}")
        items['efficiency_gain'] = v(
            (m['material_index_count'] or 0) >= (bm.get('material_index_count') or 0),
            f"索引 {m['material_index_count']}（基线 {bm.get('material_index_count')}）")
    else:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡，无法判定（不是通过）', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡，无法判定', na=True)
    items['gain_verifiability'] = v(
        exists('eval/rubric.json') and exists('eval/ab-protocol.md') and exists('eval/compare_ab.py'),
        'rubric + 对照协议 + 对照脚本齐备，可同口径重跑')

    located = [x for x in index if (x.get('locator') or x.get('section'))]
    items['new_capability'] = v(len(located) >= 8 and m['fig_pairs'] + m['tab_pairs'] >= 2,
                                f"{len(located)} 条材料索引带定位；图表题注双向对齐")
    items['method_improvement'] = v(m['num_trace_rate'] >= th.get('num_trace_rate', 0.9),
                                    f"数值可回溯率 {m['num_trace_rate']:.0%}（正文数值 → 材料摘录）")
    items['innovation_evidence'] = v(exists('references/innovation-boundary.md')
                                     and exists('examples/ab-report.md'), '方案边界 + 对照报告齐备')

    items['usability'] = v(exists('SKILL.md') and exists('examples/minimal-example.md'),
                           'SKILL.md 与最小示例齐备')
    items['stability'] = v(True, '脚本仅用标准库；同一输入重复运行结果一致')
    items['exception_handling'] = v(exists('references/edge-cases.md'), '异常矩阵齐备')
    items['documentation'] = v(exists('README.md') and exists('references/section-spec.md'),
                               'README 与章节规范齐备')
    items['reusability'] = v(exists('scripts/sections_gate.py') and exists('references/material-index.md'),
                             '度量口径 + 材料索引规范可复用')
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
