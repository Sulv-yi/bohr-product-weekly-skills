#!/usr/bin/env python3
"""契约 + 整篇稿件门槛校验。

两层，顺序不能反：契约（字段齐不齐）→ 门槛（交的是不是能进修改环节的稿子）。
门槛不过就回流程补内容，不改 status 绕过。

用法:
  python scripts/validate_result.py /app/output/result.json --case /input/case.json \
      [--text /app/output/manuscript.md] [--min-chars 1800] [--out report.json]
退出码 0=通过 1=未通过 2=输入缺失。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sections_gate import measure  # noqa: E402

GATE_SECTIONS = 0.75       # 八类章节里至少 6 类有实质内容
GATE_REFS = 12             # 参考文献至少 12 条
GATE_FIGTAB = 2            # 图/表题注与正文提及成对的数量 ≥2
GATE_INDEX = 8             # 材料索引至少 8 条（否则等于没用素材）
GATE_BINDING = 0.5         # 论断句挂引用编号的比例
GATE_DECL = 2              # 声明字段至少 2 类，且必须含数据可得性
STATUSES = ('success', 'partial', 'blocked', 'unanswerable')
KEEP_FIELDS = ('case_id', 'status', 'result', 'sources', 'uncertainty')


def collect_contract(case):
    if not isinstance(case, dict):
        return []
    oc = case.get('output_contract')
    if isinstance(oc, list):
        return [str(x) for x in oc]
    if isinstance(oc, dict):
        return list(oc.keys())
    return []


def check(result, case, min_chars=1800, extra_text=''):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是 JSON 对象'], 'warnings': [], 'metrics': {}}
    for f in KEEP_FIELDS:
        if f not in result:
            errors.append(f'缺少顶层字段 {f}')
    if result.get('status') not in STATUSES:
        errors.append(f"status 非法：{result.get('status')}")

    payload = result.get('result')
    if not isinstance(payload, dict):
        errors.append('result 必须是对象（承载稿件与材料索引）')
        payload = {}
    contract = collect_contract(case)
    missing = [f for f in contract if f not in payload]
    if missing:
        errors.append(f'output_contract 字段未覆盖：{missing}')
    for key in ('manuscript', 'material_index'):
        if key not in payload:
            warnings.append(f'result.{key} 缺失，完整性存疑')

    index = payload.get('material_index') or []
    for m in index:
        if not (m.get('locator') or m.get('section')):
            warnings.append('材料索引有条目缺 locator/section，正文对应关系会失准')
            break

    text = extra_text or payload.get('manuscript') or ''
    m = measure(text, result, min_chars)

    if result.get('status') == 'success':
        if not m['min_chars_ok']:
            errors.append(f"稿件仅 {m['total_chars']} 字（需 ≥{min_chars}）")
        if m['section_coverage'] < GATE_SECTIONS:
            gone = [k for k, v in m['sections'].items() if not v['ok']]
            errors.append(f"章节齐备度 {m['section_coverage']:.0%}（需 ≥{GATE_SECTIONS:.0%}），缺：{gone}")
        if m['ref_entries'] < GATE_REFS:
            errors.append(f"参考文献仅 {m['ref_entries']} 条（需 ≥{GATE_REFS}）")
        if m['cite_keys'] == 0:
            errors.append('正文没有任何引用编号')
        elif m['cite_resolved_rate'] < 1.0:
            errors.append(f"正文引用未闭合，悬空编号：{m['cite_dangling']}")
        if m['fig_pairs'] + m['tab_pairs'] < GATE_FIGTAB:
            errors.append(f"图/表题注与正文提及成对仅 {m['fig_pairs'] + m['tab_pairs']} 组（需 ≥{GATE_FIGTAB}）")
        if m['fig_orphan_caps'] or m['tab_orphan_caps']:
            errors.append(f"有题注但正文未提及：图 {m['fig_orphan_caps']} 表 {m['tab_orphan_caps']}")
        if m['material_index_count'] < GATE_INDEX:
            errors.append(f"材料索引仅 {m['material_index_count']} 条（需 ≥{GATE_INDEX}）")
        if m['binding_rate'] < GATE_BINDING:
            errors.append(f"论断句挂引用比例 {m['binding_rate']:.0%}（需 ≥{GATE_BINDING:.0%}）")
        if m['declaration_fields'] < GATE_DECL:
            errors.append(f"声明字段仅 {m['declaration_fields']} 类（需 ≥{GATE_DECL}）")
        if 'data_availability' not in m['declarations']:
            errors.append('缺数据可得性声明')
        if m['placeholder_count']:
            errors.append(f"残留占位符 {m['placeholder_count']} 处")

    if m['num_untraced']:
        warnings.append(f"有 {len(m['num_untraced'])} 个数值未能在材料/来源中找到同值：{m['num_untraced'][:6]}")
    if not (result.get('uncertainty') or []):
        warnings.append('uncertainty 为空：至少写一处材料缺口或需人工确认项')

    ok = not errors
    return {'status': 'passed' if ok else 'failed', 'case_id': result.get('case_id'),
            'attempted_status': result.get('status'), 'errors': errors, 'warnings': warnings,
            'metrics': m, 'contract': {'required': contract, 'missing': missing}}


def main():
    ap = argparse.ArgumentParser(description='契约 + 整篇稿件门槛校验')
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--min-chars', type=int, default=1800)
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
            print(f"  字数={m['total_chars']} 章节={m['section_coverage']:.0%} 引用={m['cite_keys']}/"
                  f"{m['ref_entries']} 图表对={m['fig_pairs']}+{m['tab_pairs']} "
                  f"索引={m['material_index_count']} 绑定={m['binding_rate']:.0%} "
                  f"数值可回溯={m['num_trace_rate']:.0%}")
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
