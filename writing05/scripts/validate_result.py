#!/usr/bin/env python3
"""契约 + 证据门槛校验。

分两层，顺序不能反：
  1. 契约层：result.json 是否满足题面要求的字段（case_id/status/sources/uncertainty/changes），
     以及 case.json 里 output_contract 列出的字段是否原样覆盖。
  2. 门槛层：成稿与证据表是否达到「可以直接被第三方回查」的实质标准。

只有两层都过，status 才允许是 success。门槛不过就回第 4 步补内容，
不要改 status 绕过——绕过会被审阅方按"结果完整性/可核验性"扣分。

用法:
  python scripts/validate_result.py /app/output/result.json --case /input/case.json \
      [--text /app/output/draft.md] [--min-chars 1400] [--out report.json]
退出码 0=通过 1=未通过 2=输入缺失。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from evidence_gate import measure  # noqa: E402

# ---- 证据门槛（达不到即 fail，不看 status 自称） ----
GATE_CLAIMS = 12          # 论断清单至少 12 条，否则"整篇支撑"变成抽样
GATE_COVERAGE = 0.8       # 成稿论断单元被清单覆盖的比例
GATE_LOCATOR = 0.9        # 精确定位率（page/section/paragraph 任一）
GATE_HEDGE = 0.8          # 表述强度与证据强度相称率
GATE_SOURCES = 12         # 可回溯来源至少 12 条
GATE_META = 0.9           # 来源元数据齐备率
GATE_EVIDENCE = 0.9       # 每条论断都进证据表的比例
STATUSES = ('success', 'partial', 'blocked', 'unanswerable')
KEEP_FIELDS = ('case_id', 'status', 'result', 'sources', 'uncertainty')


def collect_contract(case):
    """从 case 里读取 output_contract；兼容 list 与 dict 两种写法。"""
    if not isinstance(case, dict):
        return []
    oc = case.get('output_contract')
    if isinstance(oc, list):
        return [str(x) for x in oc]
    if isinstance(oc, dict):
        return list(oc.keys())
    return []


def check(result, case, min_chars=1400, extra_text=''):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是 JSON 对象'], 'warnings': [],
                'metrics': {}, 'contract': {}}

    # ---- 契约层 ----
    for f in KEEP_FIELDS:
        if f not in result:
            errors.append(f'缺少顶层字段 {f}')
    if result.get('status') not in STATUSES:
        errors.append(f"status 非法：{result.get('status')}（允许 {'/'.join(STATUSES)}）")
    if not isinstance(result.get('sources'), list):
        errors.append('sources 必须是数组')

    payload = result.get('result')
    if not isinstance(payload, dict):
        errors.append('result 必须是对象（承载成稿与证据表）')
        payload = {}
    contract = collect_contract(case)
    missing = [f for f in contract if f not in payload]
    if missing:
        errors.append(f'output_contract 字段未覆盖：{missing}')

    for key in ('draft', 'claims', 'evidence_table', 'conflicts', 'conflict_search_note'):
        if key not in payload:
            warnings.append(f'result.{key} 缺失，完整性存疑')

    # ---- 论断清单自身一致性 ----
    claims = payload.get('claims') or []
    ids = [c.get('claim_id') for c in claims]
    if len(ids) != len(set(ids)):
        errors.append('claim_id 有重复')
    if any(not i for i in ids):
        errors.append('存在 claim_id 为空的论断')
    table = payload.get('evidence_table') or []
    for r in table:
        cid = r.get('claim_id')
        if cid and cid not in set(ids):
            errors.append(f'证据表引用了不存在的 claim_id：{cid}')
            break
    no_evidence = [i for i in ids if i and i not in {r.get('claim_id') for r in table}]
    if ids and len(no_evidence) / len(ids) > (1 - GATE_EVIDENCE):
        errors.append(f'{len(no_evidence)} 条论断没有对应证据行（需 ≥{GATE_EVIDENCE:.0%} 有）')

    # ---- 门槛层 ----
    draft = extra_text or payload.get('draft') or ''
    m = measure(draft, result, min_chars=min_chars)

    if result.get('status') == 'success':
        if not m['min_chars_ok']:
            errors.append(f"正文仅 {m['total_chars']} 字（需 ≥{min_chars}）")
        if m['claims_count'] < GATE_CLAIMS:
            errors.append(f"论断仅 {m['claims_count']} 条（需 ≥{GATE_CLAIMS}）")
        if m['claim_coverage'] < GATE_COVERAGE:
            errors.append(f"论断清单只覆盖成稿 {m['claim_coverage']:.0%} 的论断单元（需 ≥{GATE_COVERAGE:.0%}）")
        if m['locator_rate'] < GATE_LOCATOR:
            errors.append(f"精确定位率 {m['locator_rate']:.0%}（需 ≥{GATE_LOCATOR:.0%}）")
        if m['strength_rate'] < 1.0:
            errors.append(f"有 {m['open_items']} 条论断强度未判定或标 needs_review（success 需 100% 判定）")
        if m['hedge_alignment'] < GATE_HEDGE:
            errors.append(f"表述与证据强度相称率 {m['hedge_alignment']:.0%}（需 ≥{GATE_HEDGE:.0%}）")
        if m['source_count'] < GATE_SOURCES:
            errors.append(f"来源仅 {m['source_count']} 条（需 ≥{GATE_SOURCES}）")
        if m['source_metadata_rate'] < GATE_META:
            errors.append(f"来源元数据齐备率 {m['source_metadata_rate']:.0%}（需 ≥{GATE_META:.0%}）")
        if not m['conflict_handled']:
            errors.append('未处理冲突证据：conflicts 为空且无 conflict_search_note')
        if m['placeholder_count']:
            errors.append(f"残留占位符 {m['placeholder_count']} 处")

    # ---- 告警层（不阻断，但要写进 uncertainty） ----
    if m['binding_rate'] < 0.6 and m['draft_units']:
        warnings.append(f"成稿引用绑定率仅 {m['binding_rate']:.0%}，回头补编号或说明理由")
    if m['total_chars'] < min_chars and result.get('status') == 'success':
        warnings.append('篇幅不足（已作为错误处理）')
    if not (result.get('uncertainty') or []):
        warnings.append('uncertainty 为空：至少说明一处材料缺口或需人工确认项')

    ok = not errors
    return {'status': 'passed' if ok else 'failed',
            'case_id': result.get('case_id'),
            'attempted_status': result.get('status'),
            'errors': errors, 'warnings': warnings,
            'metrics': m,
            'contract': {'required': contract,
                         'missing': missing,
                         'present': [k for k in contract if k in payload]}}


def main():
    ap = argparse.ArgumentParser(description='契约 + 证据门槛校验')
    ap.add_argument('result', help='result.json 路径')
    ap.add_argument('--case', help='case.json 路径')
    ap.add_argument('--text', help='成稿（draft.md）路径')
    ap.add_argument('--min-chars', type=int, default=1400)
    ap.add_argument('--out', help='把校验报告写入文件')
    ap.add_argument('--json', action='store_true', help='打印完整 JSON')
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
            print(f"  字数={m['total_chars']} 论断={m['claims_count']} 覆盖={m['claim_coverage']:.0%} "
                  f"定位={m['locator_rate']:.0%} 强度={m['strength_rate']:.0%} "
                  f"相称={m['hedge_alignment']:.0%} 来源={m['source_count']} "
                  f"元数据={m['source_metadata_rate']:.0%}")
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
