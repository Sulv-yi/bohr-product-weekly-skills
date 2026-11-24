#!/usr/bin/env python3
"""从材料段落抽取“候选实体”，每个候选强制绑定 source_id + paragraph_id + 原文短引。

定位：这是辅助 Agent 的候选生成器，输出 candidate=true，明确不是最终答案；
最终实体必须由 Agent 判定类型、别名与对齐，并经 verify_graph.py 核验。

抽得准的硬约束（脚本层保证）：
  - 每个候选的 quote 是材料段落里的原文子串，不是模型改写。
  - word/短语位置可回查 paragraph_id 与 source_id。
  - 不凭常识补概念：只抽取材料中出现的字符串。

用法:
    python3 extract_entities.py --material material.json --out candidates.json
    python3 extract_entities.py --material material.json --vocab assets/entity_types.json --out candidates.json
"""
import argparse
import json
import re

# 英文科研对象模式：首字母大写短语、缩写、带数字/连字符的术语
EN_TERM = re.compile(r'\b(?:[A-Z][A-Za-z0-9\-]*(?:\s+[A-Z][A-Za-z0-9\-]*){0,3})\b')
ABBR = re.compile(r'\b[A-Z]{2,}(?:-[A-Z0-9]+)*\b')
CN_TERM = re.compile(r'[\u4e00-\u9fa5]{2,8}(?:方法|模型|数据集|算法|指标|实验|任务|结论)')
STOP = set('''The This That We Our These Those Table Figure Fig Section Eq In On For As A An It Its
We I He She They Their There Here However Moreover Furthermore Additionally Therefore Thus
Introduction Methods Results Discussion Conclusion Abstract Background Related Work And But Or Not
Study Paper Article Report Nature Science Cell Journal Proceedings Volume Issue'''.split())


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def find_paragraphs(material):
    if isinstance(material, list):
        items = material
    else:
        items = []
        for key in ("paragraphs", "blocks", "items", "segments", "passages", "material"):
            if isinstance(material.get(key), list):
                items = material[key]
                break
        if not items:
            for sid, val in material.items():
                if isinstance(val, list):
                    for p in val:
                        if isinstance(p, dict):
                            p = dict(p); p.setdefault("source_id", sid); items.append(p)
    out = []
    for p in items:
        if isinstance(p, dict):
            out.append({
                "paragraph_id": str(p.get("paragraph_id") or p.get("pid") or p.get("id") or "unknown"),
                "source_id": str(p.get("source_id") or p.get("paper_id") or "unknown"),
                "text": str(p.get("text") or p.get("content") or ""),
                "section": str(p.get("section") or ""),
            })
    return out


def candidates_from(text, source_id, paragraph_id):
    seen = set()
    out = []
    for m in list(EN_TERM.finditer(text)) + list(ABBR.finditer(text)) + list(CN_TERM.finditer(text)):
        term = m.group(0).strip()
        if not term or term in STOP or term.lower() in {s.lower() for s in STOP}:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "candidate": True,
            "surface": term,
            "type_suggestion": "unspecified",  # 由 Agent 判定，脚本不猜
            "source_id": source_id,
            "paragraph_id": paragraph_id,
            "quote": term,
            "char_span": [m.start(), m.end()],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", required=True)
    ap.add_argument("--vocab", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    material = load_json(args.material)
    paras = find_paragraphs(material)
    all_cands = []
    for p in paras:
        if not p["text"]:
            continue
        all_cands.extend(candidates_from(p["text"], p["source_id"], p["paragraph_id"]))

    # 去重统计：同一 surface 在不同来源出现 -> 提示 Agent 做实体对齐判定
    by_surface = {}
    for c in all_cands:
        by_surface.setdefault(c["surface"], set()).add(c["source_id"])

    cross_source = sorted(s for s, srcs in by_surface.items() if len(srcs) > 1)
    payload = {
        "note": "候选实体（candidate=true），非最终答案；请判定类型/别名/对齐后写入 result.graph.nodes。",
        "candidate_count": len(all_cands),
        "cross_source_surfaces": cross_source,
        "cross_source_note": "跨篇同形术语仅表示字符串相同，不等于同一实体实例；需显式身份依据才可合并。",
        "candidates": all_cands,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "out": args.out,
        "candidates": len(all_cands),
        "cross_source_surfaces": len(cross_source),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
