#!/usr/bin/env python3
"""从原文段落预切分候选原子断言骨架（不预填答案，只给稳定的 claim id 与候选片段）。

按句切分 + 并列结构提示，输出每句的候选 subject/relation/object 槽位与"疑似复合"标记，
供 Agent 逐条核定后填入 nanopublications。只做机械预切，不做语义判断。

用法:
    python3 split_claims.py <原文文本|blocks.json> --out candidates.json [--min-chars 8]
"""
import argparse
import json
import re
import sys

SENT = re.compile(r'(?<=[.!?。！？])\s+|\n+')
COMPOUND = re.compile(r'\b(and|or|but|however|moreover|furthermore|while|whereas|此外|并且|同时|但是|然而|而且)\b', re.I)
VERB_HINT = re.compile(r'\b(reach|reaches|achiev\w*|improv\w*|increas\w*|decreas\w*|reduc\w*|show\w*|report\w*|correlat\w*|outperform\w*|require\w*|lead\w*|cause\w*|达到|提升|提高|降低|表明|发现|报告|相关|优于|依赖)\b', re.I)


def load_text(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    if txt.lstrip().startswith('{'):
        o = json.loads(txt)
        if 'full_text' in o:
            return o['full_text']
        if 'blocks' in o:
            return '\n'.join(b.get('text', '') for b in o['blocks'])
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('material')
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-chars', type=int, default=8)
    args = ap.parse_args()
    text = load_text(args.material)
    sents = [s.strip() for s in SENT.split(text) if s.strip()]
    cands = []
    for s in sents:
        if len(s) < args.min_chars:
            continue
        is_compound = bool(COMPOUND.search(s))
        has_relation = bool(VERB_HINT.search(s))
        cands.append({
            'claim_id': 'c-%03d' % (len(cands) + 1),
            'sentence': s,
            'subject': '',
            'relation': '',
            'object': '',
            'conditions': '',
            'hints': {
                'likely_compound': is_compound,
                'has_relation_verb': has_relation,
                'note': '疑似复合，需拆为多条' if is_compound else ('含关系动词，优先作断言候选' if has_relation else '需人工判断是否含可验证断言'),
            },
        })
    out = {
        'source_chars': len(text), 'sentence_count': len(sents),
        'candidate_count': len(cands),
        'compound_candidates': sum(1 for c in cands if c['hints']['likely_compound']),
        'candidates': cands,
        'note': '本文件仅为机械预切骨架，subject/relation/object 需 Agent 按原文核定；候选不等于正式断言。',
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': 'ok', 'out': args.out,
                      'candidates': out['candidate_count'],
                      'likely_compound': out['compound_candidates']},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
