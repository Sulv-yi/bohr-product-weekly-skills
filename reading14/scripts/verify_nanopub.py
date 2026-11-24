#!/usr/bin/env python3
"""核验 Nanopublication 结构化结果的四性质 + 硬损伤回扫（本 Skill 的核心）。

四性质（对应题面四问）：
  拆得细 granular : 每条 nanopub 只含一个 subject/relation/object 核心断言，非整段塞进一个字段。
  对得上 aligned  : 每条断言的证据片段能在原文按规范化匹配到；证据标注 direct/indirect；位置非空。
  追得回 traceable: 断言→证据→论文→作者→年份→版本→标识符 链路字段齐全。
  读得懂 machine  : 导出结构字段齐全、relation 命中受控词表 canonical、id 唯一、可 JSON 序列化。

硬损伤回扫：
  - 证据片段不在材料中（疑似编造/篡改）。
  - relation 不在受控词表（同义未归一）。
  - 复合断言（claim_text 含并列连词且 object 多项）。
  - 因果降级：relation=causes 但 confidence 低且证据为 indirect。
  - 主体缺失 / id 重复 / 字段缺失。

用法:
    python3 verify_nanopub.py <result.json> --material <原文文本|blocks.json> \
        [--vocab assets/relation_vocab.json] [--case case.json] [--out verify.json] [--strict]

退出码：无 error 为 0，否则 1。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}
REQUIRED_NP = ['id', 'assertion', 'provenance']
ASSERT_FIELDS = ['subject', 'relation', 'object', 'claim_text']
PROV_FIELDS = ['evidence', 'source']
SOURCE_FIELDS = ['paper', 'authors', 'year', 'identifier']
EVID_FIELDS = ['text', 'location', 'type']
COMPOUND = re.compile(r'\b(?:and|or|but|however|moreover|furthermore|additionally|while|whereas|此外|并且|同时|但是|然而|而且)\b', re.I)


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[\u2018\u2019\u201c\u201d`\'"]', '', s)
    s = re.sub(r'[\s\u00a0]+', ' ', s)
    s = re.sub(r'[，,。.!！?？;；:：()\[\]{}《》\-—_]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


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


def load_vocab(path):
    v = json.load(open(path, encoding='utf-8'))
    canonical = set()
    alias = {}
    for r in v.get('relations', []):
        c = r['canonical']
        canonical.add(c)
        alias[c] = c
        for a in r.get('aliases', []):
            alias[norm(a)] = c
    return canonical, alias


def verify(result, material_text, vocab, case, strict):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是对象']}
    cid, st = result.get('case_id'), result.get('status')
    if not cid:
        errors.append('缺少 case_id')
    if st not in VALID_STATUS:
        errors.append(f'status 非法: {st}')
    if case:
        exp = case.get('case_id')
        if exp and str(cid) != str(exp):
            errors.append(f'case_id 不符: 期望 {exp}, 得到 {cid}')
        for f in (case.get('output_contract') or []):
            if f not in (result.get('result') or {}):
                errors.append(f'result 缺少契约字段: {f}')

    r = result.get('result') or {}
    nps = r.get('nanopublications') or []
    if not nps:
        errors.append('result.nanopublications 缺失或为空')
    mat_norm = norm(material_text)
    canonical, alias = vocab
    ids = set()

    for i, np_ in enumerate(nps):
        tag = 'nanopub[%d]' % i
        if not isinstance(np_, dict):
            errors.append(f'{tag} 不是对象')
            continue
        for f in REQUIRED_NP:
            if f not in np_:
                errors.append(f'{tag} 缺字段: {f}')
        nid = str(np_.get('id', ''))
        if not nid or nid in ids:
            errors.append(f'{tag} id 缺失或重复: {nid}')
        ids.add(nid)

        a = np_.get('assertion') or {}
        for f in ASSERT_FIELDS:
            if not str(a.get(f, '')).strip():
                errors.append(f'{tag}.assertion 缺 {f}')
        subject = str(a.get('subject', '')).strip()
        obj = str(a.get('object', '')).strip()
        relation = str(a.get('relation', '')).strip()
        claim = str(a.get('claim_text', '')).strip()
        conditions = str(a.get('conditions', '')).strip()

        # 对得上：relation 归一到受控词表。canonical 先按原值精确匹配
        # （norm 会去掉下划线，is_a 等 canonical 不能被归一化后才查）。
        rel_canon = relation if relation in canonical else alias.get(norm(relation))
        if not rel_canon:
            errors.append(f'{tag} relation 不在受控词表: {relation}')
        elif rel_canon != relation:
            warnings.append(f'{tag} relation 应归一为 {rel_canon}（当前 {relation}）')

        # 拆得细：复合断言（一个 claim 含并列连词 + object 多项）
        if COMPOUND.search(claim) and len(re.split(r'\band\b|\bor\b|并且|同时|此外|而且', obj, flags=re.I)) > 1:
            warnings.append(f'{tag} 疑似复合断言未拆（object 含多项且含并列连词）')
        # 条件范围：causes 主张应保留 conditions
        if rel_canon in ('causes', 'increases', 'decreases') and not conditions:
            warnings.append(f'{tag} 因果/增减断言未写 conditions（可能过宽）')

        # 追得回 + 对得上：证据
        p = np_.get('provenance') or {}
        for f in PROV_FIELDS:
            if f not in p:
                errors.append(f'{tag}.provenance 缺 {f}')
        evs = p.get('evidence') or []
        if not evs:
            errors.append(f'{tag} 无证据片段')
        direct_count = 0
        for j, ev in enumerate(evs):
            etag = f'{tag}.evidence[{j}]'
            if not isinstance(ev, dict):
                errors.append(f'{etag} 不是对象')
                continue
            for f in EVID_FIELDS:
                if f not in ev:
                    errors.append(f'{etag} 缺 {f}')
            etxt = str(ev.get('text', ''))
            if len(etxt.strip()) < 4:
                errors.append(f'{etag} text 过短/为空')
            elif norm(etxt) not in mat_norm:
                errors.append(f'{etag} 证据片段无法在原文匹配（疑似编造/篡改）')
            if not str(ev.get('location', '')).strip():
                errors.append(f'{etag} location 为空')
            etype = str(ev.get('type', '')).strip()
            if etype not in ('direct', 'indirect'):
                errors.append(f'{etag} type 应为 direct/indirect，得到 {etype}')
            if etype == 'direct':
                direct_count += 1

        # 证据不足：因果断言却只有间接证据
        if rel_canon == 'causes' and direct_count == 0:
            warnings.append(f'{tag} 因果断言仅间接证据，confidence 不应为 high')

        src = p.get('source') or {}
        for f in SOURCE_FIELDS:
            if not src.get(f):
                errors.append(f'{tag}.provenance.source 缺 {f}')
        if not src.get('authors') and isinstance(src.get('authors'), list):
            errors.append(f'{tag} source.authors 为空列表')
        if not src.get('year') or not re.search(r'(19|20)\d{2}', str(src.get('year'))):
            warnings.append(f'{tag} source.year 缺失或格式异常')

        # 置信度依据
        conf = a.get('confidence') or np_.get('confidence')
        basis = a.get('confidence_basis') or np_.get('confidence_basis')
        if not conf:
            warnings.append(f'{tag} 缺 confidence')
        if conf in ('high', 'medium', 'low') and not basis:
            warnings.append(f'{tag} 有 confidence 但缺 confidence_basis（判定依据）')

    # 读得懂：可序列化 + 顶层结构
    try:
        json.dumps(result, ensure_ascii=False)
    except Exception as e:
        errors.append(f'结果不可 JSON 序列化: {e}')
    for f in ('sources', 'uncertainty', 'changes'):
        if f not in result:
            errors.append(f'缺少顶层字段: {f}')
    if st in ('partial', 'unable', 'refused') and not (result.get('uncertainty') or []):
        errors.append(f'status={st} 时必须给出 uncertainty')

    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors, 'warnings': warnings,
        'checks': {
            'granular': 'ok' if not any('复合断言' in e for e in errors + warnings) else 'warn',
            'aligned': 'ok' if not any('证据片段无法' in e or 'type' in e for e in errors) else 'failed',
            'traceable': 'ok' if not any('缺' in e and ('source' in e or 'provenance' in e) for e in errors) else 'failed',
            'machine': 'ok' if not any('受控词表' in e or '序列化' in e or 'id' in e for e in errors) else 'failed',
        },
        'counts': {'nanopubs': len(nps), 'errors': len(errors), 'warnings': len(warnings)},
        'case_id': cid,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--material', required=True)
    ap.add_argument('--vocab')
    ap.add_argument('--case')
    ap.add_argument('--out')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()
    result = json.load(open(args.result, encoding='utf-8'))
    vocab = load_vocab(args.vocab) if args.vocab else (set(), {})
    if not args.vocab:
        print('警告: 未提供 --vocab，relation 受控词表校验跳过', file=sys.stderr)
    case = json.load(open(args.case, encoding='utf-8')) if args.case else None
    rep = verify(result, load_material(args.material), vocab, case, args.strict)
    rep['input'] = {'result': args.result, 'material': args.material, 'vocab': args.vocab}
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
