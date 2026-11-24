#!/usr/bin/env python3
"""从原文抽取候选术语，生成术语表骨架（JSON）。

用法:
    python3 build_glossary.py <source.txt> [--out glossary.json] [--top 60]

只做候选抽取，译名需译者确认。抽取规则：
  1) 全大写缩写 (API, CNN, SEI)
  2) 连写复合词 (state-of-the-art, X-ray)
  3) 高频实词短语 (attention mechanism)
输出 glossary.json: {"terms":[{"term","translation":"","scope","note","occurrences"}]}
"""
import argparse
import json
import re
import sys
from collections import Counter

ABBREV = re.compile(r"\b[A-Z][A-Z0-9]{1,9}\b")
COMPOUND = re.compile(r"\b[a-zA-Z]+(?:-[a-zA-Z0-9]+){1,4}\b")
STOP = set("""the a an of in on for with and or to as by from at is are was were be been
this that these those it its we our they their he she i you not no but if then than
into over under between during before after can may might will would should could
which who whom whose where when why how all any each both few more most other some
such only also thus thus therefore however whereas although while""".split())


def extract(text, top):
    abbr = Counter(m.group(0) for m in ABBREV.finditer(text))
    comp = Counter(m.group(0).lower() for m in COMPOUND.finditer(text))
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
    unigrams = Counter(w for w in words if w not in STOP and len(w) >= 4)
    # 二元短语（高频实词相邻）
    toks = [w for w in words if w not in STOP]
    bigrams = Counter(f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1))

    terms = []
    seen = set()
    def add(t, occ, kind):
        if t in seen or t.lower() in seen:
            return
        seen.add(t.lower())
        terms.append({
            "term": t,
            "translation": "",
            "scope": "全文",
            "note": f"候选来源: {kind}; 请确认唯一译名",
            "occurrences": occ,
        })
    for t, n in abbr.most_common(top // 3):
        add(t, n, "缩写")
    for t, n in comp.most_common(top // 3):
        add(t, n, "复合词")
    for t, n in bigrams.most_common(top // 4):
        add(t, n, "二元短语")
    for t, n in unigrams.most_common(top // 4):
        add(t, n, "高频实词")
    return terms[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="glossary.json")
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()
    try:
        text = open(args.source, encoding="utf-8").read()
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    terms = extract(text, args.top)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"terms": terms}, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "status": "candidates_extracted",
        "terms": len(terms),
        "out": args.out,
        "note": "译名需人工确认；确认后 translation 字段即锁定",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
