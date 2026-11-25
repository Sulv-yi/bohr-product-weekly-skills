#!/usr/bin/env python3
"""润色成稿的实质门槛：逐段对齐、不丢锁定项、不改事实强度、不留占位。

用法:
    python3 check_polish.py result.json [--case case.json] [--plan polish_plan.json]

判什么：
  对齐   -> result.paragraphs 每段有 pid/original/polished，pid 唯一，polished 非空
  不漏段 -> 给了 polish_plan.json 时，plan 里每段都要在 result 中出现
  锁定   -> 每段的数字/单位/引用/图表指向多重集与原文完全一致（不丢、不新增、不挪段）
  强度   -> 每段否定词数量一致；限定词数量允许 ±1（同义改写），超出报警
  篇幅   -> 润色长度相对原文在 0.4~3.0 之间，0.7~1.6 之外仅提示
  占位   -> 无 TODO / 待润色 / 【】 / XX 等痕迹
  一致   -> result.polished_text 与各段 polished 拼接一致（允许空白差异）

退出码 0 = 通过（可写 status=success）；1 = 未通过。
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter

CRITICAL = {'number_unit', 'number', 'citation', 'figure_table'}
PLACEHOLDERS = ['TODO', 'TBD', 'FIXME', 'XXX', 'placeholder', '待润色', '待补充', '待写', '【', '】']


def _load_lock_mod():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'lock_invariants.py')
    spec = importlib.util.spec_from_file_location('lock_invariants_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm_ws(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def counts_of(lock, text, kinds):
    info = lock.lock_text(text)
    return Counter((it['kind'], it['value'].lower()) for it in info['items'] if it['kind'] in kinds)


def check(result, case, plan):
    errors, warnings = [], []

    if result.get('status') not in ('success', 'partial', 'unable_to_determine', 'refused'):
        errors.append(f"status 非法: {result.get('status')}")

    r = result.get('result') or {}
    paras = r.get('paragraphs')
    if not isinstance(paras, list) or not paras:
        errors.append('result.paragraphs 为空：润色成稿必须逐段对齐（pid/original/polished），'
                      '只给一段总结或一份检查报告不算成稿')
        return _report(errors, warnings)

    lock = _load_lock_mod()
    seen = []
    total_src = total_out = 0

    for i, p in enumerate(paras):
        if not isinstance(p, dict):
            errors.append(f'paragraphs[{i}] 不是对象')
            continue
        pid = str(p.get('pid') or '').strip()
        src = p.get('original')
        out = p.get('polished')
        tag = pid or f'#{i}'
        if not pid:
            errors.append(f'paragraphs[{i}] 缺 pid')
        seen.append(pid)
        if not isinstance(src, str) or not src.strip():
            errors.append(f'{tag} 缺 original（必须保留原文，便于逐段复核）')
            continue
        if not isinstance(out, str) or not out.strip():
            errors.append(f'{tag} 缺 polished（该段未润色）')
            continue

        if out.strip() == src.strip():
            warnings.append(f'{tag} 润色结果与原文完全相同，确认是否真的需要修改或已修改')
        for tok in PLACEHOLDERS:
            if tok in out:
                errors.append(f'{tag} 残留占位符: {tok}')
        # 未替换的骨架提示
        if '润色槽' in out and len(out) < 40:
            errors.append(f'{tag} 仍是骨架占位，未填写润色结果')

        # 锁定项：逐段多重集一致
        cb = counts_of(lock, src, CRITICAL)
        ca = counts_of(lock, out, CRITICAL)
        for key, n in cb.items():
            if ca.get(key, 0) < n:
                errors.append(f'{tag} 丢失锁定项 {key[0]}={key[1]}（原文 {n} 次，现 {ca.get(key, 0)} 次）')
        for key, n in ca.items():
            if cb.get(key, 0) < n:
                errors.append(f'{tag} 新增了原文没有的 {key[0]}={key[1]}（现 {n} 次，原文 {cb.get(key, 0)} 次）')

        # 否定词：数量必须一致
        nb = counts_of(lock, src, {'negation', 'negation_zh'})
        na = counts_of(lock, out, {'negation', 'negation_zh'})
        if sum(nb.values()) != sum(na.values()):
            errors.append(f'{tag} 否定词数量变化（{sum(nb.values())} -> {sum(na.values())}），否定范围可能被改变')

        # 限定词：允许 ±1，超出报警
        hb = sum(counts_of(lock, src, {'hedge', 'hedge_zh'}).values())
        ha = sum(counts_of(lock, out, {'hedge', 'hedge_zh'}).values())
        if abs(hb - ha) > 1:
            warnings.append(f'{tag} 限定词数量变化较大（{hb} -> {ha}），确认结论强度是否被改写')

        ratio = len(out) / max(1, len(src))
        if ratio < 0.4 or ratio > 3.0:
            errors.append(f'{tag} 篇幅异常（润色/原文 = {ratio:.2f}），疑似漏写或大幅增写')
        elif ratio < 0.7 or ratio > 1.6:
            warnings.append(f'{tag} 篇幅比 {ratio:.2f}，建议确认是否漏译/扩写')
        total_src += len(src)
        total_out += len(out)

    dup = [k for k, v in Counter(seen).items() if k and v > 1]
    if dup:
        errors.append('pid 重复: ' + ', '.join(dup))

    if plan and isinstance(plan.get('paragraphs'), list):
        need = [str(x.get('pid')) for x in plan['paragraphs'] if isinstance(x, dict)]
        miss = [p for p in need if p not in set(seen)]
        if miss:
            errors.append(f'漏段 {len(miss)} 处: ' + ', '.join(miss[:8]))

    # polished_text 与分段结果必须一致
    pt = r.get('polished_text')
    if isinstance(pt, str) and pt.strip():
        joined = norm_ws(' '.join(str(p.get('polished') or '') for p in paras if isinstance(p, dict)))
        if norm_ws(pt) != joined:
            warnings.append('polished_text 与 paragraphs 拼接不完全一致，'
                            '建议让 polished_text 直接由分段结果拼接生成，避免两套正文')
    else:
        errors.append('result.polished_text 为空')

    if total_src and total_out / total_src < 0.5:
        errors.append(f'整体篇幅仅为原文的 {total_out / total_src:.2f}，疑似只做了摘要而非逐段润色')

    return _report(errors, warnings, {'paragraphs': len(paras),
                                      'src_chars': total_src, 'out_chars': total_out})


def _report(errors, warnings, stats=None):
    return {'status': 'passed' if not errors else 'failed',
            'errors': errors, 'warnings': warnings, 'stats': stats or {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--plan')
    ap.add_argument('--out')
    args = ap.parse_args()

    try:
        result = json.load(open(args.result, encoding='utf-8'))
    except Exception as e:
        print(json.dumps({'status': 'failed', 'errors': [f'读取 result 失败: {e}']}, ensure_ascii=False))
        return 2
    case = json.load(open(args.case, encoding='utf-8')) if args.case and os.path.isfile(args.case) else None
    plan = json.load(open(args.plan, encoding='utf-8')) if args.plan and os.path.isfile(args.plan) else None

    rep = check(result, case, plan)
    out = json.dumps(rep, ensure_ascii=False, indent=2)
    print(out)
    if args.out:
        open(args.out, 'w', encoding='utf-8').write(out)
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
