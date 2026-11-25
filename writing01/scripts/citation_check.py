#!/usr/bin/env python3
"""引用核验：稿件引用键覆盖、来源元数据完整性、编号连续性、论断绑定提示。

用法: python citation_check.py <result.json> [--sources sources.json] [--case case.json]
退出码 0=通过, 1=有问题, 2=文件错误。
"""
import sys
import json
import os
import re
import argparse


def extract_keys(text):
    """从稿件文本抽取引用键：[1], [1,2], (Author, 2020), Author et al. (2020)"""
    keys = set()
    for m in re.finditer(r'\[(\d+(?:\s*[,，;；]\s*\d+)*)\]', text):
        for n in re.findall(r'\d+', m.group(1)):
            keys.add(('num', int(n)))
    for m in re.finditer(r'\(([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?)\s*,\s*(\d{4})\)',
                         text):
        keys.add(('author', m.group(1).strip() + ',' + m.group(2)))
    return keys


def collect_text(obj):
    """递归收集 result.result 里所有字符串（稿件正文）。"""
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


def check(result, sources_doc, case):
    errors = []
    warnings = []
    payload = result.get('result', {})
    text = collect_text(payload)
    keys = extract_keys(text)

    # 来源清单：优先独立文件，否则 result.sources
    sources = []
    if sources_doc and isinstance(sources_doc, dict):
        sources = sources_doc.get('sources', sources_doc.get('items', []))
    if not sources:
        sources = result.get('sources', [])

    # 来源元数据完整性
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            warnings.append(f'sources[{i}] 不是对象')
            continue
        for k in ('id', 'claim'):
            if not s.get(k):
                warnings.append(f'sources[{i}] 缺 {k}')
        author = s.get('author') or s.get('authors')
        year = s.get('year')
        venue = s.get('venue') or s.get('source') or s.get('journal')
        missing = [k for k, v in (('author', author), ('year', year), ('venue', venue)) if not v]
        if missing:
            warnings.append(f"引用元数据不全 {s.get('id', i)}: 缺 {', '.join(missing)}")

    # 数字引用键覆盖
    numeric_keys = sorted(n for t, n in keys if t == 'num')
    if numeric_keys:
        source_ids = {str(s.get('id', '')) for s in sources if isinstance(s, dict)}
        has_numbered = any(re.fullmatch(r'\d+', sid) for sid in source_ids)
        if has_numbered:
            for n in numeric_keys:
                if str(n) not in source_ids:
                    errors.append(f'稿件引用 [{n}] 在 sources 中无对应条目')
        else:
            warnings.append('稿件使用数字引用键，但 sources 无数字 id，无法自动核对覆盖')
        # 编号连续性
        for a, b in zip(numeric_keys, numeric_keys[1:]):
            if b != a + 1:
                warnings.append(f'数字引用编号跳号: {a} -> {b}')

    # 反向覆盖：sources 里带 used 标记或被 claim 引用
    if not keys and sources:
        warnings.append('稿件未检测到任何引用键，请人工确认论断是否都有引用')

    # 未核引用标记
    if re.search(r'引用待核|待核|TODO', text):
        warnings.append('稿件含"引用待核/TODO"标记，确认是否已转写 uncertainty')

    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--sources')
    ap.add_argument('--case')
    args = ap.parse_args()
    for p in (args.result, args.sources, args.case):
        if p and not os.path.isfile(p):
            print(json.dumps({'error': 'file not found', 'path': p}, ensure_ascii=False))
            return 2
    with open(args.result, encoding='utf-8') as f:
        result = json.load(f)
    sources_doc = None
    if args.sources:
        with open(args.sources, encoding='utf-8') as f:
            sources_doc = json.load(f)
    case = None
    if args.case:
        with open(args.case, encoding='utf-8') as f:
            case = json.load(f)
    errors, warnings = check(result, sources_doc, case)
    print(json.dumps({'ok': not errors, 'errors': errors, 'warnings': warnings,
                      'error_count': len(errors)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
