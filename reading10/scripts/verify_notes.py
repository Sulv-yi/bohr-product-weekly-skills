#!/usr/bin/env python3
"""核验结构化笔记的四个性质 + 硬损伤回扫（本 Skill 的核心）。

四个性质（对应题面四个关注问题）：
  对得上 alignment  : section_notes 的 section_id 必须在 outline 内、覆盖并按论文自身顺序排列。
  留得住 retention  : paper_card 五要素(研究问题/数据/方法/主要发现/局限)齐备，发现须带成立前提。
  找得回 traceable  : 每条 source.quote 必须能在原文 full_text 中按规范化匹配到；关键笔记须绑定 source。
  用得上 reusable   : 知识点 id/term 唯一，别名不与其他 term 冲突，每条知识点有 definition 与锚点。

硬损伤回扫（可机械判定的部分）：
  - 数字/单位守恒：笔记文本中出现的数值必须在绑定的 source.quote 或材料中出现。
  - 引用标记守恒：[n] / (Author, Year) 类标记在笔记与来源间一致。
  - 锚点可解析：source_id 引用必须存在；location 非空；quote 非空且够长。

用法:
    python3 verify_notes.py <result.json> --outline outline.json --material '<原文文本或blocks.json>'
                            [--case case.json] [--out verify.json] [--strict-align]

说明：--material 可为纯文本文件路径（按原文逐行读）或 blocks.json（读 full_text 字段）。
退出码：通过 0，存在 error 1。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}
CARD_FIELDS = ['research_question', 'data', 'method', 'findings', 'limitations']
NUM_RE = re.compile(r'(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:%|nm|um|µm|μm|ms|s|kg|g|mg|mL|ml|L|k|M|G|e[+-]?\d+)?(?![A-Za-z])', re.I)
CITE_RE = re.compile(r'\[\s*\d+(?:\s*[,;]\s*\d+)*\s*\]|\((?:[A-Z][A-Za-z-]+),?\s*(?:19|20)\d{2}[a-z]?\)')


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[\u2018\u2019\u201c\u201d`\'"]', '', s)
    s = re.sub(r'[\s\u00a0]+', ' ', s)
    s = re.sub(r'[，,。.!！?？;；:：()\[\]{}《》\-—_]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def numbers(s):
    out = set()
    for m in NUM_RE.finditer(s or ''):
        tok = re.sub(r'\s+', '', m.group(0)).lower()
        if re.search(r'\d', tok):
            out.add(tok)
    return out


def cites(s):
    return set(re.sub(r'\s+', '', m.group(0)) for m in CITE_RE.finditer(s or ''))


def load_material(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    stripped = txt.lstrip()
    if stripped.startswith('{'):
        obj = json.loads(txt)
        if 'full_text' in obj:
            return obj['full_text']
        if 'blocks' in obj:
            return '\n'.join(b.get('text', '') for b in obj['blocks'])
    return txt


def verify(result, outline, material_text, case, strict_align):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是对象']}
    cid = result.get('case_id')
    status = result.get('status')
    if not cid:
        errors.append('缺少 case_id')
    if status not in VALID_STATUS:
        errors.append(f'status 非法: {status}')
    if case:
        exp = case.get('case_id')
        if exp and str(cid) != str(exp):
            errors.append(f'case_id 不符: 期望 {exp}, 得到 {cid}')
        for f in (case.get('output_contract') or []):
            if f not in (result.get('result') or {}):
                errors.append(f'result 缺少契约字段: {f}')

    r = result.get('result') or {}
    sources = result.get('sources') or []
    src_index = {}
    for i, s in enumerate(sources):
        sid = str(s.get('source_id', ''))
        if sid in src_index:
            errors.append(f'sources 中 source_id 重复: {sid}')
        src_index[sid] = s
        if not str(s.get('location', '')).strip():
            warnings.append(f'sources[{i}] location 为空')
        q = str(s.get('quote', '')).strip()
        if len(q) < 4:
            errors.append(f'sources[{i}] quote 过短/为空: {q!r}')

    mat_norm = norm(material_text)
    mat_nums = numbers(material_text)
    mat_cites = cites(material_text)

    # 找得回：锚点可解析 + quote 回原文
    unmatched = []
    for sid, s in src_index.items():
        qn = norm(s.get('quote', ''))
        if qn and qn not in mat_norm:
            unmatched.append(sid)
    if unmatched:
        errors.append('quote 无法在原文匹配到（疑似编造/篡改锚点）: ' + ', '.join(unmatched[:10]))

    def bind_check(label, item, need_source=True):
        sids = item.get('source_ids') or []
        if need_source and not sids:
            warnings.append(f'{label} 未绑定 source_ids')
        for sid in sids:
            if str(sid) not in src_index:
                errors.append(f'{label} 引用了不存在的 source_id: {sid}')

    # 留得住：paper_card 五要素 + 发现的前提条件
    card = r.get('paper_card') or {}
    missing_fields = [f for f in CARD_FIELDS if not card.get(f)]
    if missing_fields:
        errors.append('paper_card 缺要素: ' + ', '.join(missing_fields))
    for f in CARD_FIELDS:
        items = card.get(f) or []
        if isinstance(items, dict):
            items = [items]
        for j, it in enumerate(items):
            if isinstance(it, dict):
                bind_check(f'paper_card.{f}[{j}]', it)
                if f == 'findings' and not str(it.get('conditions', '')).strip():
                    warnings.append(f'findings[{j}] 缺 conditions（结论成立前提）')
    premises = card.get('premises') or []
    if not premises and not warnings:
        warnings.append('paper_card 未单列 premises（让结论成立的前提条件）')

    # 对得上：章节骨架对齐
    secs = r.get('section_notes') or []
    sec_ids = [str(s.get('section_id', '')) for s in secs]
    if not secs:
        errors.append('section_notes 为空：没有按论文自身章节做总结')
    if len(sec_ids) != len(set(sec_ids)):
        errors.append('section_notes 出现重复 section_id')
    if outline:
        valid_order = {s['section_id']: s.get('order', i + 1)
                       for i, s in enumerate(outline.get('outline', []))}
        valid_ids = set(valid_order)
        for sid in sec_ids:
            if sid not in valid_ids:
                errors.append(f'section_notes 含骨架外章节: {sid}')
        known = [valid_order[s] for s in sec_ids if s in valid_order]
        if known != sorted(known):
            errors.append('section_notes 顺序与论文章节顺序不一致（对不上）')
        if strict_align:
            miss = valid_ids - set(sec_ids)
            if miss:
                errors.append('section_notes 未覆盖论文章节: ' + ', '.join(sorted(miss)))
        for i, s in enumerate(secs):
            if not str(s.get('summary', '')).strip():
                warnings.append(f'section_notes[{i}] 缺 summary')
            bind_check(f'section_notes[{i}]', s)
    else:
        for i, s in enumerate(secs):
            bind_check(f'section_notes[{i}]', s)

    # 用得上：知识点去重与可用性
    kps = r.get('knowledge_points') or []
    kp_ids, terms = set(), {}
    for i, k in enumerate(kps):
        kid = str(k.get('id', ''))
        term = norm(k.get('term', ''))
        if not kid or kid in kp_ids:
            errors.append(f'knowledge_points[{i}] id 缺失或重复: {kid}')
        kp_ids.add(kid)
        if not term:
            errors.append(f'knowledge_points[{i}] term 为空')
        if term and term in terms:
            errors.append(f'知识点 term 重复: {term}（首次 {terms[term]}）')
        terms[term] = kid
        if not str(k.get('definition', '')).strip():
            warnings.append(f'knowledge_points[{i}] 缺 definition')
        bind_check(f'knowledge_points[{i}]', k)
    # 别名不得撞到别的 term
    for i, k in enumerate(kps):
        for a in (k.get('aliases') or []):
            an = norm(a)
            if an in terms and terms[an] != str(k.get('id', '')):
                errors.append(f'知识点别名与已有 term 冲突: {a}')

    # 硬损伤：数字 / 引用守恒（笔记文本 -> 来源+材料）
    def collect_text(obj, acc):
        if isinstance(obj, dict):
            for v in obj.values():
                collect_text(v, acc)
        elif isinstance(obj, list):
            for v in obj:
                collect_text(v, acc)
        elif isinstance(obj, str):
            acc.append(obj)
    texts = []
    collect_text(card, texts)
    collect_text(secs, texts)
    collect_text(kps, texts)
    note_text = '\n'.join(texts)
    note_nums = numbers(note_text)
    bad_nums = sorted(n for n in note_nums if n not in mat_nums)
    if bad_nums:
        warnings.append('笔记中出现材料中未见的数值: ' + ', '.join(bad_nums[:12]))
    note_cites = cites(note_text)
    bad_cites = sorted(c for c in note_cites if c not in mat_cites)
    if bad_cites:
        warnings.append('笔记中出现材料中未见的引用标记: ' + ', '.join(bad_cites[:12]))

    if status in ('partial', 'unable', 'refused') and not (result.get('uncertainty') or []):
        errors.append(f'status={status} 时必须给出 uncertainty')
    for f in ('sources', 'uncertainty', 'changes'):
        if f not in result:
            errors.append(f'缺少顶层字段: {f}')

    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors,
        'warnings': warnings,
        'checks': {
            'alignment': 'ok' if not any('对不上' in e or '骨架外' in e or '覆盖论文章节' in e for e in errors) else 'failed',
            'retention': 'ok' if not missing_fields else 'failed',
            'traceable': 'ok' if not unmatched else 'failed',
            'reusable': 'ok' if not any('知识点' in e or '别名' in e for e in errors) else 'failed',
        },
        'counts': {
            'sections': len(secs), 'sources': len(sources),
            'knowledge_points': len(kps), 'card_fields': len([f for f in CARD_FIELDS if card.get(f)]),
        },
        'case_id': cid,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--outline')
    ap.add_argument('--material', required=True)
    ap.add_argument('--case')
    ap.add_argument('--out')
    ap.add_argument('--strict-align', action='store_true')
    args = ap.parse_args()
    result = json.load(open(args.result, encoding='utf-8'))
    outline = json.load(open(args.outline, encoding='utf-8')) if args.outline else None
    case = json.load(open(args.case, encoding='utf-8')) if args.case else None
    rep = verify(result, outline, load_material(args.material), case, args.strict_align)
    rep['input'] = {'result': args.result, 'outline': args.outline, 'material': args.material}
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
