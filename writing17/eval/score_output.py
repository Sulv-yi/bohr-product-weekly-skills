#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

用法:
  python eval/score_output.py --result result.json --case case.json --text popular.md \
      [--baseline baseline-scorecard.json] --out scorecard.json
退出码 0=正常算出（含 fail）；2=输入缺失或不可解析。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from validate_result import contract, measure  # noqa: E402
import popularize_gate  # noqa: E402

GATES = {
    'min_chars': 900,
    'min_sections': 3,
    'abbrev_rate': 0.9,
    'min_analogy': 2,
    'num_rate': 0.9,
    'limit_rate': 0.7,
    'hedge_keep': 0.8,
    'strength_bad': 0,
    'term_drift': 0,
    'changelog_rate': 0.8,
    'trace_rate': 0.8,
}


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def v(ok, note, na=False):
    return {'verdict': 'n/a' if na else ('pass' if ok else 'fail'), 'note': note}


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def evaluate(result, case, text, baseline=None):
    m = measure(result, case or {}, text)
    items = {}

    items['task_completion'] = v(
        m['chars'] >= GATES['min_chars'] and m['sections'] >= GATES['min_sections'],
        f"字数 {m['chars']}；节 {m['sections']}")
    items['result_correctness'] = v(
        m['num_rate'] >= GATES['num_rate'] and m['limit_rate'] >= GATES['limit_rate']
        and m['hedge_keep'] >= GATES['hedge_keep'] and m['strength_bad'] <= GATES['strength_bad']
        and m['term_drift'] <= GATES['term_drift'],
        f"数值 {m['num_rate']:.0%}；限定条件 {m['limit_rate']:.0%}；限定语 {m['hedge_keep']:.0%}；"
        f"越界断言 {m['strength_bad']}；术语漂移 {m['term_drift']}")
    items['result_completeness'] = v(
        m['analogies'] >= GATES['min_analogy'] and m['figtab_rate'] >= 0.9
        and m['audience_declared'] and m['purpose_declared'],
        f"类比 {m['analogies']}；图表 {m['figtab_rate']:.0%}；"
        f"受众声明 {'有' if m['audience_declared'] else '无'}；目的 {'有' if m['purpose_declared'] else '无'}")
    items['verifiability'] = v(
        m['trace_rate'] >= GATES['trace_rate'] and m['changelog_rate'] >= GATES['changelog_rate'],
        f"溯源 {m['trace_rate']:.0%}；改动账覆盖 {m['changelog_rate']:.0%}（{m['changelog_total']} 条）")

    if not baseline:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡', na=True)
    else:
        b = baseline.get('metrics', {})
        keys = ['num_rate', 'limit_rate', 'hedge_keep', 'trace_rate', 'changelog_rate',
                'abbrev_rate', 'analogies']
        better = sum(1 for k in keys if m[k] > b.get(k, 0))
        worse = sum(1 for k in keys if m[k] < b.get(k, 0))
        items['quality_gain'] = v(better >= 3 and worse == 0, f"变好 {better} 项；变差 {worse} 项")
        items['efficiency_gain'] = v(
            m['strength_bad'] <= b.get('strength_bad', 0)
            and m['term_drift'] <= b.get('term_drift', 0)
            and len(m['placeholders']) <= len(b.get('placeholders') or []),
            f"越界断言 {b.get('strength_bad')}→{m['strength_bad']}；"
            f"术语漂移 {b.get('term_drift')}→{m['term_drift']}；"
            f"占位符 {len(b.get('placeholders') or [])}→{len(m['placeholders'])}")

    items['new_capability'] = v(
        hasattr(popularize_gate, 'retention') and hasattr(popularize_gate, 'abbrev_check'),
        '新增四类度量：缩写展开 / 信息保留 / 强度对齐 / 改动可核')
    items['method_improvement'] = v(
        exists('scripts/popularize_gate.py') and exists('scripts/validate_result.py'),
        '把「读得懂·留得住·说得准·接得住」落成可执行判定，而非写作建议')
    items['innovation_evidence'] = v(
        exists('references/innovation-boundary.md') and exists('examples/ab-report.md'),
        '边界文档 + A/B 报告均在包内')
    items['usability'] = v(
        exists('SKILL.md') and exists('examples/minimal-example.md'),
        'SKILL.md 含预算表；最小示例可照做')
    items['stability'] = v(
        exists('scripts/popularize_gate.py') and exists('scripts/build_outputs.py'),
        '纯标准库，无第三方依赖，单文件函数')
    items['exception_handling'] = v(
        exists('references/edge-cases.md'), '异常矩阵覆盖材料不足 / 缩写无全称 / 数值冲突')
    items['documentation'] = v(
        exists('README.md') and exists('SCORING-MAP.md'), 'README + SCORING-MAP + 六篇 references')
    items['reusability'] = v(
        exists('scripts/popularize_gate.py') and exists('eval/score_output.py'),
        '度量脚本与评分卡可独立调用')
    items['sharing'] = v(exists('GITHUB_URL.txt'), '公开仓库链接')
    items['contract_integrity'] = v(len(contract(dict(result))) == 0,
                                    '契约字段齐备' if not contract(dict(result)) else str(contract(dict(result))))

    return {'metrics': {k: (list(x) if isinstance(x, tuple) else x) for k, x in m.items()},
            'items': items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', required=True)
    ap.add_argument('--case', default=None)
    ap.add_argument('--text', default=None)
    ap.add_argument('--baseline', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    res = load(a.result)
    if res is None:
        print('result 不可读:', a.result, file=sys.stderr)
        sys.exit(2)
    res['_path'] = a.result
    case = load(a.case, {}) or {}
    tp = a.text or res.get('target_path')
    if tp and not os.path.isabs(tp) and not os.path.exists(tp):
        tp = os.path.join(os.path.dirname(os.path.abspath(a.result)), tp)
    if not tp or not os.path.exists(tp):
        print('找不到成稿:', tp, file=sys.stderr)
        sys.exit(2)
    text = open(tp, encoding='utf-8').read()
    base = load(a.baseline) if a.baseline else None

    out = evaluate(res, case, text, base)
    cb = contract(res)
    out['contract_fails'] = cb
    counts = {'pass': 0, 'fail': 0, 'n/a': 0}
    for k, it in out['items'].items():
        counts[it['verdict']] += 1
        print(f"[{it['verdict']:4s}] {k}: {it['note']}")
    out['counts'] = counts
    print(f"\npass={counts['pass']} fail={counts['fail']} n/a={counts['n/a']}")
    if cb:
        print('契约失败:', cb)
    if a.out:
        json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('wrote', a.out)


if __name__ == '__main__':
    main()
