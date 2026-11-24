#!/usr/bin/env python3
"""术语一致性回扫：全篇统一术语写法、检查缩写首次出现定义。

用法: python term_consistency.py <lock.json|原文> <draft.json|txt> [--term-map terms.json] [--out terms.json]
纯标准库实现。
"""
import sys
import json
import os
import re


def read_any(path):
    if path.endswith('.json'):
        d = json.load(open(path, encoding='utf-8'))
        for k in ('text', 'polished_text', 'content'):
            if k in d and isinstance(d[k], str):
                return d[k]
        if 'result' in d and isinstance(d['result'], dict):
            for k in ('polished_text', 'text'):
                if k in d['result'] and isinstance(d['result'][k], str):
                    return d['result'][k]
        return None
    return open(path, encoding='utf-8').read()


def load_map(path):
    if not path or not os.path.isfile(path):
        return {}, {}, []
    d = json.load(open(path, encoding='utf-8'))
    return (d.get('term_map') or {}), (d.get('abbreviations') or {}), (d.get('forbidden') or [])


def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'usage: term_consistency.py <original> <draft> [--term-map f.json] [--out f.json]'}))
        return 2
    orig_path, draft_path = sys.argv[1], sys.argv[2]
    term_map, abbr, forbidden = {}, {}, []
    if '--term-map' in sys.argv:
        term_map, abbr, forbidden = load_map(sys.argv[sys.argv.index('--term-map') + 1])
    out = 'terms.json'
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]

    try:
        text = read_any(draft_path)
        if text is None:
            raise ValueError('draft has no readable text field')
    except Exception as e:
        print(json.dumps({'error': f'{type(e).__name__}: {e}'}))
        return 2

    issues = []
    decisions = []

    # 术语映射检查：键出现却没有统一为值
    for src, target in term_map.items():
        pat = re.compile(r'(?<![A-Za-z])' + re.escape(src) + r'(?![A-Za-z])', re.I)
        hits = list(pat.finditer(text))
        if hits and src.lower() != target.lower():
            issues.append({'type': 'term_not_unified', 'found': src,
                           'expected': target, 'count': len(hits)})
        decisions.append({'from': src, 'to': target, 'basis': 'term_map'})

    # 禁止写法
    for bad in forbidden:
        if bad and bad.lower() in text.lower():
            issues.append({'type': 'forbidden_term', 'found': bad})

    # 缩写首次出现定义检查
    for ab, full in abbr.items():
        m = re.search(r'(?<![A-Za-z])' + re.escape(ab) + r'(?![A-Za-z])', text)
        if not m:
            continue
        pos = m.start()
        window = text[max(0, pos - 200): pos + 200]
        defined = (full.lower() in window.lower()) or \
                  (re.search(re.escape(ab) + r'\s*\(', window, re.I) is not None)
        if not defined:
            issues.append({'type': 'abbreviation_undefined', 'abbr': ab,
                           'suggestion': f'{full} ({ab})'})

    # 拼写变体粗查：同一词的大小写/连字符漂移
    words = re.findall(r'\b[A-Za-z][A-Za-z\-]+\b', text)
    variants = {}
    for w in words:
        key = w.lower().replace('-', '')
        variants.setdefault(key, set()).add(w)
    for key, vs in variants.items():
        if len(vs) > 1 and len(key) > 4:
            issues.append({'type': 'spelling_variant', 'word': key,
                           'variants': sorted(vs)})

    result = {
        'status': 'warning' if issues else 'passed',
        'term_map_size': len(term_map),
        'abbreviations_checked': len(abbr),
        'issues': issues,
        'term_decisions': decisions,
        'note': 'term_not_unified 命中不等于错误：确认该写法在上下文中确为同一概念后再改',
    }
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({'status': result['status'], 'issues': len(issues),
                      'out': out}, ensure_ascii=False))
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
