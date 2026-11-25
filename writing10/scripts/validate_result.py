#!/usr/bin/env python3
"""契约 + 结果与讨论章节门槛校验。

两层：契约（字段齐不齐）→ 门槛（写的是不是"能投稿的结果与讨论"）。
门槛不过就回流程补内容或降表述强度，不改 status 绕过。

用法:
  python scripts/validate_result.py /app/output/result.json --case /input/case.json \
      [--text /app/output/chapter.md] [--min-chars 1200] [--out report.json]
退出码 0=通过 1=未通过 2=输入缺失。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from results_gate import measure  # noqa: E402

GATE_RESULTS = 250         # 结果段最低字数
GATE_DISCUSSION = 300      # 讨论段最低字数
GATE_FIGROWS = 2           # 至少 2 张图/表的数据进 figure_data
GATE_FIGNUM = 0.9          # 结果段数值能在图表数据里找到同值的比例
GATE_STATS = 0.8           # 显著性措辞带统计量的比例
GATE_LEAK = 2              # 结果段允许的解释性句子数
GATE_BINDING = 0.6         # 论断句挂引用或图表编号的比例
GATE_LIMIT = 3             # 局限的具体线索条数
STATUSES = ('success', 'partial', 'blocked', 'unanswerable')
KEEP = ('case_id', 'status', 'result', 'sources', 'uncertainty')


def collect_contract(case):
    if not isinstance(case, dict):
        return []
    oc = case.get('output_contract')
    if isinstance(oc, list):
        return [str(x) for x in oc]
    if isinstance(oc, dict):
        return list(oc.keys())
    return []


def check(result, case, min_chars=1200, extra_text=''):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是 JSON 对象'], 'warnings': [], 'metrics': {}}
    for f in KEEP:
        if f not in result:
            errors.append(f'缺少顶层字段 {f}')
    if result.get('status') not in STATUSES:
        errors.append(f"status 非法：{result.get('status')}")

    payload = result.get('result')
    if not isinstance(payload, dict):
        errors.append('result 必须是对象（承载章节文本与图表数据）')
        payload = {}
    missing = [f for f in collect_contract(case) if f not in payload]
    if missing:
        errors.append(f'output_contract 字段未覆盖：{missing}')
    for key in ('manuscript', 'figure_data'):
        if key not in payload:
            warnings.append(f'result.{key} 缺失，完整性存疑')

    text = extra_text or payload.get('manuscript') or ''
    m = measure(text, result, min_chars)

    if result.get('status') == 'success':
        if not m['min_chars_ok']:
            errors.append(f"章节仅 {m['total_chars']} 字（需 ≥{min_chars}）")
        if m['results_chars'] < GATE_RESULTS:
            errors.append(f"结果段 {m['results_chars']} 字（需 ≥{GATE_RESULTS}）")
        if m['discussion_chars'] < GATE_DISCUSSION:
            errors.append(f"讨论段 {m['discussion_chars']} 字（需 ≥{GATE_DISCUSSION}）")
        if m['figure_rows'] < GATE_FIGROWS:
            errors.append(f"figure_data 仅 {m['figure_rows']} 行（需 ≥{GATE_FIGROWS}，否则数值无处可核）")
        if m['fig_number_rate'] < GATE_FIGNUM:
            errors.append(f"结果段数值与图表数据一致率 {m['fig_number_rate']:.0%}"
                          f"（需 ≥{GATE_FIGNUM:.0%}），未对上：{m['fig_numbers_untraced'][:5]}")
        if m['stats_support'] < GATE_STATS:
            errors.append(f"显著性表述带统计量的比例 {m['stats_support']:.0%}"
                          f"（需 ≥{GATE_STATS:.0%}），例：{m['stats_unsupported'][:2]}")
        if m['leakage'] > GATE_LEAK:
            errors.append(f"结果段有 {m['leakage']} 句解释性表述（上限 {GATE_LEAK}），"
                          f"例：{m['leakage_samples']}")
        if not m['trend_boundary']:
            errors.append('未见"趋势一致但未达显著"一类边界表述（有小幅差异时必须有）')
        if m['binding_rate'] < GATE_BINDING:
            errors.append(f"论断句挂引用/图表编号比例 {m['binding_rate']:.0%}（需 ≥{GATE_BINDING:.0%}）")
        if m['limitation_markers'] < GATE_LIMIT:
            errors.append(f"局限的具体线索仅 {m['limitation_markers']} 条（需 ≥{GATE_LIMIT}）")
        if m['placeholder_count']:
            errors.append(f"残留占位符 {m['placeholder_count']} 处")

    if m['limitation_vague']:
        warnings.append(f"局限里有套话：{m['limitation_vague']}——换成可检验的表述")
    if not (result.get('uncertainty') or []):
        warnings.append('uncertainty 为空：至少写一处缺图/缺统计量/需人工确认项')

    ok = not errors
    return {'status': 'passed' if ok else 'failed', 'case_id': result.get('case_id'),
            'attempted_status': result.get('status'), 'errors': errors, 'warnings': warnings,
            'metrics': m, 'contract': {'missing': missing}}


def main():
    ap = argparse.ArgumentParser(description='契约 + 结果与讨论门槛校验')
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--min-chars', type=int, default=1200)
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    if not os.path.isfile(args.result):
        print(json.dumps({'error': 'result.json not found', 'path': args.result}, ensure_ascii=False))
        return 2
    with open(args.result, encoding='utf-8') as f:
        result = json.load(f)
    case = {}
    if args.case and os.path.isfile(args.case):
        with open(args.case, encoding='utf-8') as f:
            case = json.load(f)
    text = ''
    if args.text and os.path.isfile(args.text):
        with open(args.text, encoding='utf-8') as f:
            text = f.read()

    rep = check(result, case, args.min_chars, text)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(json.dumps(rep, ensure_ascii=False, indent=2) + '\n')
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"{rep['status']}  case={rep.get('case_id')}  status={rep.get('attempted_status')}")
        for e in rep['errors']:
            print('  ✗ ' + e)
        for w in rep['warnings']:
            print('  ! ' + w)
        m = rep['metrics']
        if m:
            print(f"  字数={m['total_chars']} 结果={m['results_chars']} 讨论={m['discussion_chars']} "
                  f"图表一致={m['fig_number_rate']:.0%} 统计支撑={m['stats_support']:.0%} "
                  f"泄漏={m['leakage']} 绑定={m['binding_rate']:.0%} 局限线索={m['limitation_markers']}")
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
