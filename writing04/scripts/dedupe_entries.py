#!/usr/bin/env python3
"""文献去重归并建议（收得净）：产出可解释的合并判据，不替用户强制合并。

判据（可解释、可复核）：
  D1 DOI 完全一致（规范化后） -> strong
  D2 题名规范化完全一致 + 作者首姓一致 + 年份相同 -> strong
  D3 题名高度相似(>=0.92) + 作者首姓一致 + 年份相同 -> medium（预印本/正式版、期刊/会议）
  D4 题名相似(0.80~0.92) + DOI 一致 或 作者全匹配 -> medium
  D5 仅作者同名、题名不同 -> 明确建议 NOT merge（防同名作者误合并）

中英文题名：不做跨语言语义合并（无可靠依据），仅当 DOI 一致才合并。
每条建议给出 evidence 字段列出命中的判据与字段值；歧义项写 confidence=low 让人确认。

用法:
    python3 dedupe_entries.py entries.json --out dedupe.json
"""
import argparse
import json
import re
import sys


def norm_title(t):
    t = (t or '').lower()
    t = re.sub(r'[^\w\u4e00-\u9fa5]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # 去常见后缀噪声
    t = re.sub(r'\b(preprint|published version|accepted manuscript|in press)\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def norm_doi(d):
    return (d or '').lower().strip().rstrip('/')


def first_surname(authors):
    if not authors:
        return ''
    a = authors[0]
    # "Smith, J." / "J. Smith" / "张三" -> 取首token或逗号前
    if ',' in a:
        return a.split(',')[0].strip().lower()
    toks = a.split()
    return toks[-1].strip().lower() if toks else a.strip().lower()


def authors_overlap(a1, a2):
    s1 = {first_surname([a]) for a in a1}
    s2 = {first_surname([a]) for a in a2}
    s1.discard(''); s2.discard('')
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / max(len(s1), len(s2))


def sim(a, b):
    """字符二元组 Dice 相似度。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    bg = lambda s: {s[i:i+2] for i in range(len(s)-1)}
    A, B = bg(a), bg(b)
    if not A or not B:
        return 0.0
    return 2 * len(A & B) / (len(A) + len(B))


def decide(e1, e2):
    d1, d2 = norm_doi(e1.get('doi')), norm_doi(e2.get('doi'))
    t1, t2 = norm_title(e1.get('title')), norm_title(e2.get('title'))
    y1, y2 = str(e1.get('year') or ''), str(e2.get('year') or '')
    s1, s2 = first_surname(e1.get('authors')), first_surname(e2.get('authors'))
    ts = sim(t1, t2)
    ao = authors_overlap(e1.get('authors', []), e2.get('authors', []))
    ev = []

    if d1 and d2 and d1 == d2:
        return ("merge", "strong", ["D1 DOI一致: " + d1], 1.0)
    # 同名作者但题名差异大 -> 明确不合并
    if s1 and s2 and s1 == s2 and ts < 0.65:
        return ("do_not_merge", "high", ["D5 作者首姓相同(%s)但题名差异大(sim=%.2f)" % (s1, ts)], 0.0)
    # 年份容差：预印本常比正式版早 1 年，±1 视为同年区间
    def year_near():
        if y1 and y2 and y1.isdigit() and y2.isdigit():
            return abs(int(y1) - int(y2)) <= 1
        return y1 == y2

    if t1 and t2 and t1 == t2 and s1 and s1 == s2 and year_near():
        return ("merge", "strong", ["D2 题名完全一致+作者首姓一致+年份相近(%s/%s)" % (y1, y2)], 0.95)
    if ts >= 0.92 and s1 and s1 == s2 and year_near():
        return ("merge", "medium", ["D3 题名相似%.2f+作者首姓一致+年份相近(预印本/正式版)" % ts], 0.82)
    # 题名高度相似 + 作者全体高度重合 + 年份相近：预印本带 preprint/正式版后缀等情形
    if ts >= 0.85 and ao >= 0.8 and year_near():
        return ("merge", "medium", ["D3b 题名相似%.2f+作者重合%.2f+年份相近(预印本/会议版)" % (ts, ao)], 0.75)
    if 0.80 <= ts < 0.92 and ((d1 and d1 == d2) or ao >= 0.6):
        return ("merge", "medium", ["D4 题名相似%.2f+%s" % (ts, "DOI一致" if d1 and d1 == d2 else "作者高度重合%.2f" % ao)], 0.7)
    return ("uncertain", "low", ["题名相似%.2f/作者重合%.2f/DOI %s-%s，依据不足需人工确认" % (ts, ao, d1 or '无', d2 or '无')], 0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entries')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    data = json.load(open(args.entries, encoding='utf-8'))
    entries = data.get('entries', [])
    suggestions = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            act, conf, evidence, score = decide(entries[i], entries[j])
            if act == 'uncertain' and score < 0.4:
                # 只在题名有一定相似度时才记录歧义，避免 N^2 噪声
                if sim(norm_title(entries[i].get('title')), norm_title(entries[j].get('title'))) < 0.5:
                    continue
            suggestions.append({
                "a": entries[i].get('key') or 'entry#%d' % i,
                "b": entries[j].get('key') or 'entry#%d' % j,
                "action": act,
                "confidence": conf,
                "score": round(score, 2),
                "evidence": evidence,
            })
    order = {'merge': 0, 'uncertain': 1, 'do_not_merge': 2}
    suggestions.sort(key=lambda x: (order.get(x['action'], 9), -x['score']))
    payload = {
        "note": "去重建议，非强制操作；merge 需人工确认后执行，do_not_merge 为明确的防误合并提示。",
        "entry_count": len(entries),
        "merge": [s for s in suggestions if s['action'] == 'merge'],
        "uncertain": [s for s in suggestions if s['action'] == 'uncertain'],
        "do_not_merge": [s for s in suggestions if s['action'] == 'do_not_merge'],
        "all": suggestions,
    }
    json.dump(payload, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(json.dumps({"out": args.out, "merge": len(payload['merge']),
                      "uncertain": len(payload['uncertain']),
                      "do_not_merge": len(payload['do_not_merge'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
