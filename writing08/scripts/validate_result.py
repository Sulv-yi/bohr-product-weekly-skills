#!/usr/bin/env python3
"""校验 result.json：契约字段、状态、四要素成稿质量、证据映射、不确定性、变更记录。

设计取向：**拦住空壳，不放过薄稿**。
- 挡住的是：标 success 却只交骨架/原则/几句空话、sources 为空、四要素缺件。
- 挤出来的是：段落厚度、相关工作分组数、贡献条数与证据定位、论断-引用绑定率。
结构度量在 scripts/quality_gate.py，本文件只做判定与报错，不重复实现。

用法: python validate_result.py <result.json> [--case case.json] [--min-chars 600] [--text draft.md]
退出码 0=通过, 1=有问题, 2=文件错误。
"""
import sys
import json
import os
import re
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_gate import measure, PLACEHOLDER  # noqa: E402

VALID_STATUS = {'success', 'partial', 'blocked', 'unanswerable'}
VALID_UNC = {'not_reported', 'undetermined', 'conflict', 'needs_human_confirmation'}

# 题面硬要求对应的门槛（success 未达即判失败）
GATE_GROUPS = 3          # 相关工作至少 3 组
GATE_CONTRIB = 3         # 贡献至少 3 条
GATE_SOURCES = 12        # 可回溯来源至少 12 条（覆盖关键工作与近期进展）


def collect_text(obj):
    parts = []

    def walk(x):
        if isinstance(x, str):
            parts.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return "\n".join(parts)


def check(result, case, min_chars=600, extra_text=''):
    errors = []
    warnings = []
    if not isinstance(result, dict):
        return ['顶层必须是对象'], [], {}

    status = result.get('status')
    if status not in VALID_STATUS:
        errors.append(f'status 非法: {status!r}')
    if not result.get('case_id'):
        errors.append('缺少 case_id')
    elif case and case.get('case_id') and str(result['case_id']) != str(case['case_id']):
        errors.append('case_id 与 case.json 不一致')

    contract = case.get('output_contract') if case else None
    payload = result.get('result')
    keys = []
    if contract:
        keys = contract if isinstance(contract, list) else list(contract.keys())
        if not isinstance(payload, dict):
            errors.append('case 有 output_contract，但 result.result 不是对象')
        else:
            for k in keys:
                if k not in payload:
                    errors.append(f'result 缺字段: {k}')
    elif payload is None:
        errors.append('缺少 result 字段')

    # ---- 成稿质量：结构指标 + 硬门槛 ----
    draft_text = collect_text(payload) + "\n" + (extra_text or '')
    sources = result.get('sources', [])
    unc = result.get('uncertainty', [])
    m = measure(draft_text, sources if isinstance(sources, list) else [], unc if isinstance(unc, list) else [],
                min_chars=min_chars)

    if status == 'success':
        if not m['min_chars_ok']:
            errors.append(f'status=success 但成稿篇幅不足（{m["lang"]}：中文 {m["cjk_chars"]} 字 / 英文 {m["en_words"]} 词），'
                          f'疑似空壳或薄稿；中文需 ≥1600 字，英文需 ≥1000 词')
        if m['missing_parts']:
            errors.append(f'status=success 但四要素缺件: {m["missing_parts"]}（背景/相关工作/空白/贡献须分别成段）')
        if m['related_groups'] < GATE_GROUPS:
            errors.append(f'相关工作只有 {m["related_groups"]} 组比较（需 ≥{GATE_GROUPS} 组，按问题/方法/路线分组）')
        if m['contributions'] < GATE_CONTRIB:
            errors.append(f'贡献仅 {m["contributions"]} 条（需 ≥{GATE_CONTRIB} 条逐条列点）')
        if m['source_count'] < GATE_SOURCES:
            errors.append(f'sources 仅 {m["source_count"]} 条（需 ≥{GATE_SOURCES} 条，零来源不能算完整解答）')
        if m['placeholder_count']:
            errors.append(f'status=success 但正文残留占位符 {m["placeholder_count"]} 处，定稿前必须清空')
        bad = [k for k, ok in m['section_min_ok'].items() if not ok]
        if bad:
            warnings.append(f'段落厚度未达标（建议补齐再定稿）: {bad}')
        if m['contribution_evidence_rate'] < 1.0:
            warnings.append(f'仅 {m["contribution_evidence_rate"]:.0%} 贡献条目带证据定位（§/Fig./Table/实验结果）')
        if m['claim_binding_rate'] < 0.3:
            warnings.append(f'论断-引用绑定率仅 {m["claim_binding_rate"]:.0%}，多数论点未落到具体来源')
        if not m['gap_chain_present']:
            warnings.append('研究空白缺少「已引工作限制 → 空白 → 本文对应」推导链')
        if m['source_metadata_rate'] < 0.8:
            warnings.append(f'来源元数据完整率 {m["source_metadata_rate"]:.0%}（claim/quote/file + page 或 section 需齐备）')
    else:
        ph = PLACEHOLDER.findall(draft_text)
        if ph:
            warnings.append(f'正文残留占位符 {len(ph)} 处（partial 可接受，定稿须清）')

    if not isinstance(sources, list):
        errors.append('sources 必须是数组')
    else:
        for i, s in enumerate(sources):
            if not isinstance(s, dict):
                errors.append(f'sources[{i}] 不是对象')
                continue
            if not s.get('claim'):
                warnings.append(f'sources[{i}] 缺 claim')
            if not s.get('quote'):
                warnings.append(f'sources[{i}] 缺 quote（需可回溯原文）')

    if not isinstance(unc, list):
        errors.append('uncertainty 必须是数组')
    else:
        for i, u in enumerate(unc):
            if isinstance(u, dict) and u.get('type') and u['type'] not in VALID_UNC:
                errors.append(f'uncertainty[{i}].type 非法: {u["type"]}')

    if 'changes' not in result:
        warnings.append('缺少 changes 记录')
    if status in ('blocked', 'unanswerable', 'partial') and not unc:
        warnings.append(f'status={status} 但 uncertainty 为空，应说明原因')
    return errors, warnings, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--min-chars', type=int, default=0,
                    help='显式篇幅门槛；0 表示按成稿语言自适应（中文 1600 字 / 英文 1000 词）')
    ap.add_argument('--text', help='成稿正文文件（draft.md），若正文不在 result.json 内则一并度量')
    args = ap.parse_args()
    for p in (args.result, args.case, args.text):
        if p and not os.path.isfile(p):
            print(json.dumps({'error': 'file not found', 'path': p}, ensure_ascii=False))
            return 2
    with open(args.result, encoding='utf-8') as f:
        result = json.load(f)
    case = None
    if args.case:
        with open(args.case, encoding='utf-8') as f:
            case = json.load(f)
    extra = ''
    if args.text:
        with open(args.text, encoding='utf-8') as f:
            extra = f.read()
    errors, warnings, m = check(result, case, args.min_chars, extra)
    print(json.dumps({'ok': not errors, 'errors': errors, 'warnings': warnings,
                      'error_count': len(errors), 'metrics': m}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
