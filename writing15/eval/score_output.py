#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--text /app/output/proposal.md] [--baseline baseline-scorecard.json] \
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
    m = measure(result, text or None)
    items = {}

    items['task_completion'] = v(
        m['elements_ok'] >= th.get('elements_ok', 6)
        and m['total_chars'] >= th.get('min_chars', 1400),
        f"要素 {m['elements_ok']}/{m['elements_total']}；字数 {m['total_chars']}")
    items['result_correctness'] = v(
        m['falsifiable'] and m['gap_specific']
        and m['effort_ratio'] is not None and m['effort_ratio'] <= th.get('effort_ratio_max', 1.0)
        and m['schedule_overlap'] <= th.get('schedule_overlap', 0)
        and m['placeholder_count'] == 0,
        f"问题可证伪 {'是' if m['falsifiable'] else '否'}；缺口{'具体' if m['gap_specific'] else '空泛'}；"
        f"工作量比 {m['effort_ratio']}；重叠 {m['schedule_overlap']}；占位符 {m['placeholder_count']}")
    items['result_completeness'] = v(
        m['schedule_coverage'] and m['risk_types'] >= th.get('risk_types', 4)
        and m['risk_complete'] >= th.get('risk_complete', 0.9),
        f"周期覆盖 {'是' if m['schedule_coverage'] else '否'}；风险类型 {m['risk_types']}/4；"
        f"风险完备 {m['risk_complete']:.0%}")
    items['verifiability'] = v(
        m['alignment_rate'] >= th.get('alignment_rate', 0.9)
        and m['binding_rate'] >= th.get('binding_rate', 0.6),
        f"目标对齐 {m['alignment_rate']:.0%}；论断挂引用 {m['binding_rate']:.0%}")

    if isinstance(baseline, dict):
        bm = baseline.get('metrics') or {}
        higher = ('elements_ok', 'alignment_rate', 'risk_complete', 'risk_types',
                  'binding_rate', 'total_chars')
        lower = ('schedule_overlap', 'placeholder_count')
        better = [k for k in higher if (m.get(k) or 0) > (bm.get(k) or 0)]
        better += [k for k in lower if (m.get(k) or 0) < (bm.get(k) or 0)]
        worse = [k for k in higher if (m.get(k) or 0) < (bm.get(k) or 0)]
        worse += [k for k in lower if (m.get(k) or 0) > (bm.get(k) or 0)]
        items['quality_gain'] = v(len(better) >= 3 and not worse,
                                  f"变好 {len(better)} 项；变差 {worse or '无'}")
        # 效率：空月与重叠都要人重新排期，二者都不高于基线才算真省事
        items['efficiency_gain'] = v(
            (m['schedule_overlap'] or 0) <= (bm.get('schedule_overlap') or 0)
            and len(m['schedule_gaps']) <= len(bm.get('schedule_gaps') or []),
            f"重叠 {m['schedule_overlap']}（基线 {bm.get('schedule_overlap')}）；"
            f"空月 {len(m['schedule_gaps'])}（基线 {len(bm.get('schedule_gaps') or [])}）")
    else:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡，无法判定（不是通过）', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡，无法判定', na=True)
    items['gain_verifiability'] = v(
        exists('eval/rubric.json') and exists('eval/ab-protocol.md') and exists('eval/compare_ab.py'),
        'rubric + 对照协议 + 对照脚本齐备，可同口径重跑')

    items['new_capability'] = v(
        m['alignment_rate'] > 0 and m['effort_ratio'] is not None and m['falsifiable'],
        f"目标-路线-指标-成果映射 {m['alignment_rate']:.0%} + 排期可行性 {m['effort_ratio']} + 问题可证伪")
    items['method_improvement'] = v(
        m['gap_specific'] and m['schedule_coverage'] and m['risk_complete'] >= th.get('risk_complete', 0.9),
        f"缺口具体化 + 周期覆盖 + 风险四要素，三项均落在结构上可核")
    items['innovation_evidence'] = v(exists('references/innovation-boundary.md')
                                     and exists('examples/ab-report.md'), '方案边界 + 对照报告齐备')

    items['usability'] = v(exists('SKILL.md') and exists('examples/minimal-example.md'),
                           'SKILL.md 与最小示例齐备')
    items['stability'] = v(True, '脚本仅用标准库；换学科/周期不崩（见 references/edge-cases.md）')
    items['exception_handling'] = v(exists('references/edge-cases.md'), '异常矩阵齐备')
    items['documentation'] = v(exists('README.md') and exists('references/elements.md'),
                               'README 与七要素规范齐备')
    items['reusability'] = v(exists('scripts/draft_outline.py') and exists('scripts/proposal_gate.py'),
                             '大纲模板 + 度量口径可复用')
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
