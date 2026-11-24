#!/usr/bin/env python3
"""改前锁定不可变项：数字/单位、引用编号、图表指向、限定词、否定词。

用法: python lock_invariants.py <原文文件|JSON> --out lock.json
输出 lock.json，作为改后 invariant_guard.py 的基准线。
纯标准库实现。
"""
import sys
import json
import re
import os


HEDGES = {
    'may', 'might', 'could', 'possibly', 'suggest', 'suggests', 'suggested',
    'appear', 'appears', 'appeared', 'seem', 'seems', 'seemed', 'tend', 'tends',
    'likely', 'indicate', 'indicates', 'generally', 'usually', 'often',
    'typically', 'demonstrate', 'demonstrates', 'clearly', 'definitely',
    'always', 'invariably', 'must', 'all', 'every', 'none', 'never',
}
HEDGE_ZH = ['可能', '或许', '似乎', '似乎', '倾向于', '往往', '通常', '一般',
            '总是', '所有', '每个', '证明', '显然', '必定', '必须', '不', '未', '无']
NEG_EN = {'no', 'not', 'none', 'never', 'neither', 'nor', 'without'}
NEG_ZH = ['不', '未', '无', '没有', '非']


def read_text(path):
    if path.endswith('.json'):
        d = json.load(open(path, encoding='utf-8'))
        for k in ('text', 'content', 'polished_text', 'original'):
            if k in d and isinstance(d[k], str):
                return d[k]
        return json.dumps(d, ensure_ascii=False)
    return open(path, encoding='utf-8').read()


def tokenize(text):
    """按句子切分，保留位置。"""
    parts = re.split(r'(?<=[.!?。！？;；])\s+|\n+', text)
    return [p.strip() for p in parts if p.strip()]


def lock_text(text):
    sents = tokenize(text)
    items = []
    for i, s in enumerate(sents, 1):
        # 数字 + 单位组合（含不等号、有效数字）
        for m in re.finditer(r'[<>=≤≥≈~]?\s*\d+(?:\.\d+)?\s*(?:%|mg/kg|mg|kg|g|mL|ml|L|°C|℃|nm|µm|um|mm|cm|m|s|min|h|Hz|kPa|MPa|p\s*<|n\s*=|\bns\b)', s, re.I):
            items.append({'kind': 'number_unit', 'value': m.group(0).strip(), 'sentence': i})
        # 裸数字（含小数、科学计数）
        for m in re.finditer(r'(?<![\w])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w])', s):
            v = m.group(0)
            if not any(it['value'].find(v) >= 0 and it['sentence'] == i for it in items):
                items.append({'kind': 'number', 'value': v, 'sentence': i})
        # 引用编号 [n] / (Author, year) / Ref. n / 上标数字
        for m in re.finditer(r'\[\s*\d+\s*\]|\(\s*[A-Z][A-Za-z\-]+\s*,\s*\d{4}\s*\)|Ref\.?\s*\d+|\d{4}', s):
            items.append({'kind': 'citation', 'value': m.group(0), 'sentence': i})
        # 图表指向
        for m in re.finditer(r'(?:Fig\.?|Figure|Table|Tab\.?|图|表)\s*\d+[A-Za-z]?(?:\([a-z]\))?', s, re.I):
            items.append({'kind': 'figure_table', 'value': m.group(0), 'sentence': i})
        # 限定词（英语）
        words = re.findall(r"[A-Za-z]+", s.lower())
        for w in words:
            if w in HEDGES:
                items.append({'kind': 'hedge', 'value': w, 'sentence': i})
        # 限定词（中文）
        for w in HEDGE_ZH:
            for _ in range(s.count(w)):
                items.append({'kind': 'hedge_zh', 'value': w, 'sentence': i})
        # 否定词（英语）
        for w in words:
            if w in NEG_EN:
                items.append({'kind': 'negation', 'value': w, 'sentence': i})
        # 否定词（中文）
        for w in NEG_ZH:
            for _ in range(s.count(w)):
                items.append({'kind': 'negation_zh', 'value': w, 'sentence': i})
        # 因果/相关信号词
        for m in re.finditer(r'\b(cause[sd]?|lead[s]? to|result[s]? in|due to|because|correlat\w*|associat\w*|therefore|thus|hence)\b', s, re.I):
            items.append({'kind': 'relation', 'value': m.group(0).lower(), 'sentence': i})

    counts = {}
    for it in items:
        k = (it['kind'], it['value'].lower())
        counts[k] = counts.get(k, 0) + 1
    return {
        'sentence_count': len(sents),
        'items': items,
        'counts': [{'kind': k[0], 'value': k[1], 'count': v} for k, v in sorted(counts.items())],
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'usage: lock_invariants.py <text-file|json> --out lock.json'}))
        return 2
    path = sys.argv[1]
    out = 'lock.json'
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    if not os.path.isfile(path):
        print(json.dumps({'error': 'file not found', 'path': path}))
        return 2
    try:
        text = read_text(path)
    except Exception as e:
        print(json.dumps({'error': f'{type(e).__name__}: {e}'}))
        return 2
    result = {'source': os.path.basename(path), 'char_count': len(text)}
    result.update(lock_text(text))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({'out': out, 'sentences': result['sentence_count'],
                      'items': len(result['items'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
