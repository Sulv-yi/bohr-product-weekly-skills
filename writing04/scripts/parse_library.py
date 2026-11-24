#!/usr/bin/env python3
"""解析文献库（BibTeX / RIS / JSON），输出统一条目结构，供去重与核验使用。

只做字段抽取，不联网、不编造。字段缺失标空字符串，由后续脚本报告。
支持：
  - .bib   BibTeX：@type{key, field={value}, ...}
  - .ris   RIS：TY  - / ER  - 块
  - .json  数组或 {items:[...]}/{entries:[...]}

统一字段：key, type, title, authors[], year, journal, volume, issue, pages,
          doi, publisher, address, edition, url, raw_types(原类型标识)

用法:
    python3 parse_library.py refs.bib --out entries.json
    python3 parse_library.py refs.ris refs2.bib --out entries.json
"""
import argparse
import json
import os
import re

FIELDS = ["title", "author", "authors", "year", "journal", "journaltitle", "booktitle",
          "volume", "number", "issue", "pages", "doi", "publisher", "address",
          "edition", "url", "abstract", "language"]


def clean(v):
    if v is None:
        return ""
    v = str(v).strip()
    v = re.sub(r'^\{|\}$', '', v)  # 去掉包在最外的花括号
    return v.strip()


def split_authors(v):
    v = clean(v)
    if not v:
        return []
    return [a.strip() for a in re.split(r'\s+and\s+|\s*;\s*|,\s*(?=[A-Z\u4e00-\u9fa5])', v) if a.strip()]


def parse_bib(text):
    entries = []
    # 匹配 @type{key, ...} 到配对右花括号（简单嵌套深度计数）
    for m in re.finditer(r'@(\w+)\s*\{', text):
        etype = m.group(1)
        i = m.end()
        depth = 1
        start = i
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        body = text[start:i - 1]
        if ',' not in body:
            continue
        key, rest = body.split(',', 1)
        rec = {"key": clean(key), "type": etype.lower(), "raw_types": [etype]}
        # 解析字段：name = {value} 或 name = "value" 或 name = number
        for fm in re.finditer(r'(\w+)\s*=\s*(\{.*?\}|"[^"]*"|[^,\n]+)', rest, re.S):
            name, val = fm.group(1).lower().strip(), fm.group(2).strip()
            val = clean(val.strip('{}').strip('"'))
            if name == 'author':
                rec['authors'] = split_authors(val)
            elif name in ('journal', 'journaltitle'):
                rec['journal'] = val
            elif name in ('number', 'issue'):
                rec['issue'] = val
            else:
                rec[name] = val
        entries.append(rec)
    return entries


def parse_ris(text):
    entries = []
    cur = None
    tag_map = {
        'TY': 'type', 'TI': 'title', 'T1': 'title', 'JF': 'journal', 'JO': 'journal',
        'PY': 'year', 'Y1': 'year', 'VL': 'volume', 'IS': 'issue', 'SP': 'pages',
        'DO': 'doi', 'PB': 'publisher', 'CY': 'address', 'UR': 'url', 'AB': 'abstract',
        'AU': 'author', 'A1': 'author', 'A2': 'author', 'LA': 'language',
    }
    for line in text.splitlines():
        if re.match(r'^\s*ER\s*-', line):
            if cur:
                entries.append(cur); cur = None
            continue
        m = re.match(r'^\s*([A-Z0-9]{2})\s*-\s*(.*)$', line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == 'TY':
            cur = {"key": "", "type": val.lower(), "raw_types": [val], "authors": []}
            continue
        if cur is None:
            continue
        name = tag_map.get(tag)
        if not name:
            continue
        if name == 'author':
            cur['authors'].append(val)
        elif name in ('title', 'journal', 'year', 'volume', 'issue', 'pages', 'doi',
                      'publisher', 'address', 'url', 'abstract', 'language'):
            if name in ('pages',) and cur.get('pages'):
                cur['pages'] += '-' + val
            else:
                cur[name] = val
    return entries


def parse_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        items = data.get('items') or data.get('entries') or data.get('references') or []
    else:
        items = data
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rec = {
            "key": str(it.get('key') or it.get('id') or ''),
            "type": str(it.get('type') or 'misc').lower(),
            "raw_types": [str(it.get('type') or 'misc')],
            "authors": it.get('authors') if isinstance(it.get('authors'), list)
                       else split_authors(it.get('author', '')),
        }
        for f in ('title', 'year', 'journal', 'volume', 'issue', 'pages', 'doi',
                  'publisher', 'address', 'edition', 'url', 'abstract', 'language'):
            rec[f] = clean(it.get(f, ''))
        out.append(rec)
    return out


def normalize(rec):
    base = {
        "key": "", "type": "misc", "raw_types": [], "authors": [],
        "title": "", "year": "", "journal": "", "volume": "", "issue": "",
        "pages": "", "doi": "", "publisher": "", "address": "", "edition": "",
        "url": "", "abstract": "", "language": "",
    }
    base.update(rec)
    if not isinstance(base['authors'], list):
        base['authors'] = split_authors(base['authors'])
    base['doi'] = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', clean(base['doi'])).strip()
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    all_entries = []
    by_file = {}
    for path in args.files:
        txt = open(path, encoding='utf-8', errors='replace').read()
        ext = os.path.splitext(path)[1].lower()
        if ext == '.bib':
            recs = parse_bib(txt)
        elif ext == '.ris':
            recs = parse_ris(txt)
        else:
            recs = parse_json(txt)
        recs = [normalize(r) for r in recs]
        for r in recs:
            r['_source_file'] = os.path.basename(path)
        by_file[os.path.basename(path)] = len(recs)
        all_entries.extend(recs)
    payload = {
        "note": "文献库解析结果；字段缺失为空字符串，不臆造。_source_file 标来源文件。",
        "file_counts": by_file,
        "entry_count": len(all_entries),
        "entries": all_entries,
    }
    json.dump(payload, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(json.dumps({"out": args.out, "entries": len(all_entries), "files": by_file}, ensure_ascii=False))


if __name__ == '__main__':
    main()
