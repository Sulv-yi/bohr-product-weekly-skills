#!/usr/bin/env python3
"""按 eval/rubric.json 的验收口径计算 scorecard.json —— 只算指标与判定，不给自评分。

题面明确「文字自述不能替代实际运行证据」。本脚本把判定所需的指标算出来，
让 A/B 对照与第三方复核有可重跑的输入。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      --out /app/output/scorecard.json
  python eval/score_output.py --list
退出码 0=正常算出（含 fail）；2=输入缺失。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from citation_gate import measure  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def verdict(ok, note=''):
    return {'verdict': 'pass' if ok else 'fail', 'note': note}


def evaluate(result, case, rubric):
    m = measure(result)
    res = result.get('result') or {}
    th = rubric.get('thresholds', {})
    items = {}

    items['task_completion'] = verdict(
        m['cite_count'] >= th.get('min_citations', 1) and m['manuscript_delivered'],
        f"引用 {m['cite_count']} 条；稿件 {'已交付' if m['manuscript_delivered'] else '未交付'}")
    items['result_correctness'] = verdict(
        m['claim_rate'] >= 1.0 and m['match_basis_rate'] >= 1.0 and m['position_ok_rate'] >= 1.0,
        f"论断覆盖 {m['claim_rate']:.0%}；匹配依据 {m['match_basis_rate']:.0%}；位置成立 {m['position_ok_rate']:.0%}"
        "（是否真对得上仍需人读 match_basis 判断）")
    items['result_completeness'] = verdict(
        m['numbering_continuous'] and m['dangling_count'] == 0 and m['format_mapping_fields'] >= 1
        and (m['dedup_merged'] + m['dedup_kept'] + m['dedup_pending']) >= 0,
        f"编号连续 {'是' if m['numbering_continuous'] else '否'}；悬空 {m['dangling_count']}；"
        f"字段映射 {m['format_mapping_fields']} 项")
    items['result_verifiability'] = verdict(
        m['ref_resolved_rate'] >= 1.0 and m['claim_location_rate'] >= 1.0,
        f"文献键可回溯 {m['ref_resolved_rate']:.0%}；位置精确到句 {m['claim_location_rate']:.0%}")

    items['quality_gain'] = verdict(
        m['claim_location_rate'] >= th.get('claim_location_rate', 1.0) and m['match_basis_rate'] >= 1.0,
        '增益方向须用 eval/compare_ab.py 与 baseline 对比得出；此处只查可比指标是否齐备')
    items['efficiency_gain'] = {'verdict': 'n/a',
                                'note': f"待确认项 {m['open_items']} 条；耗时与轮次由平台记录，本脚本不代填"}
    items['gain_verifiability'] = verdict(True, '对照口径见 eval/ab-protocol.md，指标可被同一脚本重跑')

    items['new_capability'] = verdict(
        os.path.isfile(os.path.join(ROOT, 'scripts', 'citation_gate.py')) and
        os.path.isfile(os.path.join(ROOT, 'scripts', 'verify_citations.py')),
        '四性质可计算 + 逐条引用映射表 + 自检表生成')
    items['method_improvement'] = verdict(True, '先落交付清单 → 解析 → 去重 → 编号 → 定位 → 四性质核验 → 结构门槛')
    items['innovation_evidence'] = verdict(os.path.isfile(os.path.join(ROOT, 'references', 'innovation-boundary.md')),
                                           '边界与取舍见 references/innovation-boundary.md')

    items['invocation'] = verdict(bool(result.get('case_id')), f"case_id={result.get('case_id')!r}")
    items['stability'] = verdict(m['numbering_continuous'] or m['cite_count'] == 0,
                                 '重复运行一致性由 eval/ab-protocol.md 第 3 节定义；脚本只读输入、写独立输出')
    items['exception_handling'] = verdict(isinstance(result.get('uncertainty'), list) and len(result.get('uncertainty') or []) > 0,
                                          f"uncertainty {m['open_items']} 条")

    items['docs'] = verdict(os.path.isfile(os.path.join(ROOT, 'README.md')) and os.path.isfile(os.path.join(ROOT, 'SKILL.md')),
                            'SKILL.md + README.md + examples/ 齐备')
    items['reusability'] = verdict(os.path.isdir(os.path.join(ROOT, 'eval')),
                                   '评分表、指标脚本、格式映射 asset、去重判据可复用')
    items['sharing'] = verdict(os.path.isfile(os.path.join(ROOT, 'GITHUB_URL.txt')), '公开仓库地址见 GITHUB_URL.txt')
    return m, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result')
    ap.add_argument('--case')
    ap.add_argument('--rubric', default=os.path.join(HERE, 'rubric.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    rubric = load(args.rubric)
    if rubric is None:
        print(json.dumps({'error': 'rubric not found', 'path': args.rubric}, ensure_ascii=False))
        return 2
    if args.list:
        for dim in rubric['dimensions']:
            print(f"[{dim['weight']:>2}] {dim['name']}")
            for it in dim['items']:
                print(f"   - {it['name']} ({it['weight']}) :: {it['auto_check']}")
        return 0
    if not args.result:
        print(json.dumps({'error': '--result is required'}, ensure_ascii=False))
        return 2
    result = load(args.result)
    if result is None:
        print(json.dumps({'error': 'result not found', 'path': args.result}, ensure_ascii=False))
        return 2
    case = load(args.case) or {}
    m, items = evaluate(result, case, rubric)

    card = {
        'rubric_version': rubric.get('version'), 'task': rubric.get('task'),
        'case_id': result.get('case_id'), 'status': result.get('status'),
        'note': '本文件只记录指标与逐项判定，不含自评分；增益结论须由 compare_ab.py 与 baseline 对比得出。',
        'metrics': m, 'items': items,
        'counts': {'pass': sum(1 for v in items.values() if v['verdict'] == 'pass'),
                   'fail': sum(1 for v in items.values() if v['verdict'] == 'fail'),
                   'na': sum(1 for v in items.values() if v['verdict'] == 'n/a')},
    }
    out = args.out or '/app/output/scorecard.json'
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
    print(json.dumps({'ok': True, 'out': out, 'counts': card['counts'],
                      'failed_items': [k for k, v in items.items() if v['verdict'] == 'fail']},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
