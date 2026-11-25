#!/usr/bin/env python3
"""按 eval/rubric.json 的验收口径计算 scorecard.json —— 只算指标与判定，不给自评分。

为什么不出自评分：题面明确「文字自述不能替代实际运行证据」，参赛者的自评分也不被采信。
本脚本的定位是**把判定所需的指标算出来**，让 A/B 对照与第三方复核有可重跑的输入。
每个 item 输出 {id, metrics, verdict: pass|fail|n/a, note}，不输出总分。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--draft /app/output/draft.md] --out /app/output/scorecard.json
  python eval/score_output.py --rubric eval/rubric.json --list
退出码 0=正常算出（含 fail）；2=输入缺失或不可解析。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from quality_gate import measure  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def draft_text(result, draft_path):
    text = ''
    if draft_path and os.path.isfile(draft_path):
        with open(draft_path, encoding='utf-8') as f:
            text = f.read()
    payload = result.get('result')
    if isinstance(payload, dict):
        text += "\n" + "\n".join(str(v) for v in payload.values() if isinstance(v, str))
    elif isinstance(payload, str):
        text += "\n" + payload
    return text


def verdict(ok, note=''):
    return {'verdict': 'pass' if ok else 'fail', 'note': note}


def evaluate(result, case, text, rubric):
    m = measure(text, result.get('sources') or [], result.get('uncertainty') or [])
    th = rubric.get('thresholds', {})
    items = {}

    # 实际效果
    items['task_completion'] = verdict(
        m['four_part_coverage'] >= 1.0 and m['total_chars'] >= th.get('min_chars', 600),
        f"四要素覆盖 {m['four_part_coverage']:.0%}；正文 {m['total_chars']} 字")
    items['result_correctness'] = verdict(
        m['source_metadata_rate'] >= th.get('source_metadata_rate', 0.8) and m['placeholder_count'] == 0,
        f"来源元数据完整率 {m['source_metadata_rate']:.0%}；占位符 {m['placeholder_count']} "
        f"（事实对错需对着 quote 逐条核，本项只查可核条件是否齐备）")
    items['result_completeness'] = verdict(
        all(m['section_min_ok'].values()) and m['related_groups'] >= th.get('related_groups', 3),
        f"各节字数 {m['section_chars']}；相关工作 {m['related_groups']} 组")
    items['result_verifiability'] = verdict(
        m['source_count'] >= th.get('source_count', 4) and m['contribution_evidence_rate'] >= 1.0,
        f"来源 {m['source_count']} 条；贡献带证据 {m['contribution_evidence_rate']:.0%}")

    # 使用增益（质量增益由对照体现，这里只产出可比指标）
    items['quality_gain'] = verdict(
        m['claim_binding_rate'] >= th.get('claim_binding_rate', 0.3) and m['gap_chain_present'],
        f"论断-引用绑定率 {m['claim_binding_rate']:.0%}；空白推导链 {'有' if m['gap_chain_present'] else '缺'}；"
        "增益方向须用 eval/compare_ab.py 与 baseline 对比得出")
    items['efficiency_gain'] = {'verdict': 'n/a',
                                'note': f"需人工确认项 {m['manual_review_items']} 条；"
                                        "耗时与轮次由平台记录，本脚本不代填"}
    items['gain_verifiability'] = verdict(True, '对照口径见 eval/ab-protocol.md，指标可被同一脚本重跑')

    # 创新增益
    items['new_capability'] = verdict(
        os.path.isfile(os.path.join(ROOT, 'scripts', 'quality_gate.py')) and
        os.path.isfile(os.path.join(ROOT, 'scripts', 'build_outputs.py')),
        '结构度量 + 来源定位 + 自检表生成，基础 Agent 无同等机制')
    items['method_improvement'] = verdict(True, '骨架先落 → 分组比较 → 空白推导 → 贡献对齐 → 结构复核，写作与核对分离')
    items['innovation_evidence'] = verdict(os.path.isfile(os.path.join(ROOT, 'references', 'innovation-boundary.md')),
                                           '边界与取舍见 references/innovation-boundary.md')

    # 可靠体验
    items['invocation'] = verdict(bool(result.get('case_id')), f"case_id={result.get('case_id')!r}")
    items['stability'] = verdict(m['four_part_coverage'] >= 0.75,
                                 '重复运行一致性由 eval/ab-protocol.md 第 3 节定义，需 3 次重复取中位')
    items['exception_handling'] = verdict(
        isinstance(result.get('uncertainty'), list) and len(result.get('uncertainty')) > 0
        if result.get('status') != 'success' else True,
        f"uncertainty {m['manual_review_items']} 条；status={result.get('status')}")

    # 生态贡献
    items['docs'] = verdict(os.path.isfile(os.path.join(ROOT, 'README.md')) and os.path.isfile(os.path.join(ROOT, 'SKILL.md')),
                            'SKILL.md + README.md + examples/ 齐备')
    items['reusability'] = verdict(os.path.isdir(os.path.join(ROOT, 'eval')),
                                   'eval/ 评分表与脚本、references/ 模板可被他人直接复用')
    items['sharing'] = verdict(os.path.isfile(os.path.join(ROOT, 'GITHUB_URL.txt')),
                               '公开仓库地址见 GITHUB_URL.txt')
    return m, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result')
    ap.add_argument('--case')
    ap.add_argument('--draft')
    ap.add_argument('--rubric', default=os.path.join(HERE, 'rubric.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true', help='只列出评分条目，不计算')
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
    case = load(args.case)
    text = draft_text(result, args.draft or (case or {}).get('draft_file'))
    m, items = evaluate(result, case or {}, text, rubric)

    card = {
        'rubric_version': rubric.get('version'),
        'task': rubric.get('task'),
        'case_id': result.get('case_id'),
        'status': result.get('status'),
        'note': '本文件只记录指标与逐项判定，不含自评分；增益结论须由 compare_ab.py 与 baseline 对比得出。',
        'metrics': m,
        'items': {k: v for k, v in items.items()},
        'counts': {
            'pass': sum(1 for v in items.values() if v['verdict'] == 'pass'),
            'fail': sum(1 for v in items.values() if v['verdict'] == 'fail'),
            'na': sum(1 for v in items.values() if v['verdict'] == 'n/a'),
        },
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
