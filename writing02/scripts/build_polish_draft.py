#!/usr/bin/env python3
"""从案例材料生成段落对齐的润色工作台（plan + 骨架），保证润色是"逐段产出"而不是"写一段总结"。

用法:
    python3 build_polish_draft.py --case /input/case.json --out /app/work
    python3 build_polish_draft.py --text /input/material.md --out /app/work
    python3 build_polish_draft.py --case case.json --out /app/work --max-paragraphs 40

产出:
    polish_plan.json      每段原文 + 该段锁定的数字/单位/引用/图表指向/限定词/否定词
    polished_skeleton.md  逐段骨架：每段一个「原文 / 润色」槽位，润色槽为空
    term_seed.md          术语候选（供建术语表）

为什么需要它：本题最常见的失分是只交一份"改写总结"或检查报告，没有与原文逐段对齐的成稿。
骨架强制一段对一段，锁定项直接写在旁边，写的时候不会丢数字、不会改否定、不会把因果改成相关。
"""
import argparse
import importlib.util
import json
import os
import re
import sys

CRITICAL = {'number_unit', 'number', 'citation', 'figure_table'}


def _load_lock_mod():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'lock_invariants.py')
    spec = importlib.util.spec_from_file_location('lock_invariants_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_material(case, text_path):
    if text_path and os.path.isfile(text_path):
        return open(text_path, encoding='utf-8', errors='replace').read()
    if not isinstance(case, dict):
        return ''
    # 优先段落数组
    for key in ('paragraphs', 'passages', 'segments'):
        v = case.get(key)
        if isinstance(v, list) and v:
            out = []
            for it in v:
                if isinstance(it, str):
                    out.append(it)
                elif isinstance(it, dict):
                    for k in ('text', 'content', 'original'):
                        if isinstance(it.get(k), str) and it[k].strip():
                            out.append(it[k])
                            break
            if out:
                return '\n\n'.join(out)
    for key in ('text', 'content', 'material', 'source_text', 'draft'):
        v = case.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ''


def split_paragraphs(text):
    """按空行切段；整篇没有空行时按句群聚合，保证不会是"一整块"。"""
    raw = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
    if len(raw) > 1:
        return raw
    sents = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', text) if s.strip()]
    if not sents:
        return raw
    chunk, out = [], []
    for s in sents:
        chunk.append(s)
        if len(chunk) >= 3:
            out.append(' '.join(chunk))
            chunk = []
    if chunk:
        out.append(' '.join(chunk))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--out', default='/app/work')
    ap.add_argument('--max-paragraphs', type=int, default=40)
    args = ap.parse_args()

    case = {}
    if args.case and os.path.isfile(args.case):
        case = json.load(open(args.case, encoding='utf-8'))
    text = read_material(case, args.text)
    if not text.strip():
        print(json.dumps({'status': 'failed',
                          'error': '案例中没有可读的正文（试过 paragraphs/text/content/material/draft），'
                                   '请用 --text 指定材料文件，不要凭空生成原文'},
                         ensure_ascii=False))
        return 2

    lock = _load_lock_mod()
    paras = split_paragraphs(text)[: args.max_paragraphs]

    plan = {'case_id': (case or {}).get('case_id'), 'paragraph_count': len(paras), 'paragraphs': []}
    md = ['# 润色工作台（骨架，润色槽待填）', '',
          '> 每段必须给出润色结果，一段对一段，不允许合并或跳过；',
          '> 「锁定项」是该段润色后必须原样保留的内容，写完用 check_polish.py 复核。', '']
    terms = {}

    for i, p in enumerate(paras, 1):
        pid = f'P{i:02d}'
        info = lock.lock_text(p)
        items = info['items']
        crit = [it for it in items if it['kind'] in CRITICAL]
        hedges = [it for it in items if it['kind'] in ('hedge', 'hedge_zh')]
        negs = [it for it in items if it['kind'] in ('negation', 'negation_zh')]
        plan['paragraphs'].append({
            'pid': pid,
            'original': p,
            'locked': {'critical': [{'kind': it['kind'], 'value': it['value']} for it in crit],
                       'hedge_count': len(hedges),
                       'negation_count': len(negs)},
            'original_chars': len(p),
        })
        md.append(f'## {pid}')
        md.append('**原文**')
        md.append('')
        md.append(p)
        md.append('')
        if crit:
            md.append('**锁定项（必须逐字保留）**：' + '；'.join(f"{it['kind']}={it['value']}" for it in crit))
            md.append('')
        md.append('**润色**')
        md.append('')
        md.append('')
        # 术语候选：连续英文词组/中文专业词块
        for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+[a-z]+){1,3})\b', p):
            t = m.group(1).strip()
            if len(t) > 3:
                terms[t] = terms.get(t, 0) + 1

    os.makedirs(args.out, exist_ok=True)
    plan_path = os.path.join(args.out, 'polish_plan.json')
    skel_path = os.path.join(args.out, 'polished_skeleton.md')
    term_path = os.path.join(args.out, 'term_seed.md')
    json.dump(plan, open(plan_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(skel_path, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    open(term_path, 'w', encoding='utf-8').write(
        '# 术语候选（建表后全篇锁定同一译名/写法）\n\n'
        + '\n'.join(f'- {t}（出现 {n} 次）' for t, n in sorted(terms.items(), key=lambda x: -x[1])[:40])
        + '\n\n> 术语表定稿后写进 result.term_decisions，并保证全篇一致。\n')

    print(json.dumps({
        'status': 'built',
        'paragraphs': len(paras),
        'plan': plan_path, 'skeleton': skel_path, 'term_seed': term_path,
        'next': '逐段填写 polished_skeleton.md 的润色槽，然后按 plan 组装 result.paragraphs 并跑 check_polish.py',
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
