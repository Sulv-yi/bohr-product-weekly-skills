#!/usr/bin/env python3
"""从语料清单/材料索引构建知识图谱骨架（可核验工作流第一步）。

用途：
  读取 corpus-manifest.json（各论文 DOI/作者/哈希/许可证）与 material.json（两篇正文段落索引），
  生成一个 result.json 骨架：sources 中逐篇登记真实 source_id 与其自身 DOI/title/authors，
  graph 结构清空待填，并写入 source_map（段落索引）供后续实体/边绑定 paragraph_id。

防污染（对应题面“输入修订”约束）：
  - 根 DOI/title/authors 只登记为 root，不得复制到 secondary；每篇只用自己的元数据。
  - 只登记材料中真实出现的 source_id；material 缺字段时写 unknown，不臆造。
  - 位置统一用 paragraph_id（JATS 段落 ID），不生成 PDF 页码。

用法:
    python3 build_skeleton.py --manifest corpus-manifest.json --material material.json \
        --case case.json --out skeleton.json
"""
import argparse
import json
import re
import sys

UNKNOWN = "unknown"


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def find_paragraphs(material):
    """从多种可能的 material 结构中抽取段落列表。"""
    if isinstance(material, list):
        items = material
    elif isinstance(material, dict):
        for key in ("paragraphs", "blocks", "items", "segments", "passages", "material"):
            if key in material and isinstance(material[key], list):
                items = material[key]
                break
        else:
            # 逐 source_id 的字典：{primary:[...], secondary:[...]}
            items = []
            for sid, val in material.items():
                if isinstance(val, list):
                    for p in val:
                        if isinstance(p, dict):
                            p = dict(p)
                            p.setdefault("source_id", sid)
                            items.append(p)
    else:
        items = []
    out = []
    for p in items:
        if not isinstance(p, dict):
            continue
        out.append({
            "paragraph_id": str(p.get("paragraph_id") or p.get("pid") or p.get("id") or UNKNOWN),
            "source_id": str(p.get("source_id") or p.get("paper_id") or UNKNOWN),
            "section": str(p.get("section") or p.get("section_title") or ""),
            "text": str(p.get("text") or p.get("content") or ""),
        })
    return out


def paper_sources(manifest):
    """登记每篇论文自己的 source_id 与自身元数据；根信息单列，不复用。"""
    papers = []
    root = manifest.get("root") or manifest.get("root_paper") or {}
    for p in manifest.get("papers", []):
        if not isinstance(p, dict):
            continue
        papers.append({
            "source_id": str(p.get("source_id") or p.get("id") or UNKNOWN),
            "doi": str(p.get("doi") or UNKNOWN),
            "title": str(p.get("title") or UNKNOWN),
            "authors": p.get("authors") if isinstance(p.get("authors"), list) else [str(p.get("author") or UNKNOWN)],
            "source_hash": str(p.get("source_hash") or p.get("sha256") or UNKNOWN),
            "license": str(p.get("license") or UNKNOWN),
            "file": str(p.get("file") or p.get("path") or ""),
        })
    sources = {
        "root": {
            "doi": str(root.get("doi") or UNKNOWN),
            "title": str(root.get("title") or UNKNOWN),
            "authors": root.get("authors") if isinstance(root.get("authors"), list) else [],
            "note": "根 DOI/title/authors 属于第一篇论文；不得套用到其他 source_id。",
        },
        "papers": papers,
    }
    return sources


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--material", required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    manifest = load_json(args.manifest)
    material = load_json(args.material)
    case = load_json(args.case)
    sources = paper_sources(manifest)
    paras = find_paragraphs(material)

    known = {p["source_id"] for p in sources["papers"]}
    # 交叉核对：材料中出现的 source_id 是否都在清单登记
    seen = {p["source_id"] for p in paras}
    undeclared = sorted(seen - known - {UNKNOWN})

    skeleton = {
        "case_id": case.get("case_id", UNKNOWN),
        "status": "partial",
        "result": {
            "graph": {"nodes": [], "edges": [], "alignments": [], "conflicts": []},
            "queries": [],
        },
        "sources": sources,
        "source_map": paras,
        "uncertainty": [],
        "changes": [
            "skeleton built from corpus-manifest + material index; no entities/edges/answers prefilled",
        ],
        "contract": {
            "output_contract": case.get("output_contract", []),
            "note": "graph.nodes/edges/alignments/conflicts + queries 必填；每节点/边需 evidence(source_id,paragraph_id,quote,strength)",
        },
        "warnings": [],
    }
    if undeclared:
        skeleton["warnings"].append("材料中 source_id 未在清单登记: " + ", ".join(undeclared))
    if len(known) < 2:
        skeleton["warnings"].append("清单登记的来源少于 2 篇；本题预期两篇独立论文，请核对输入。")
    if not paras:
        skeleton["warnings"].append("未能从 material 解析出段落索引；请检查 material.json 结构。")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "out": args.out,
        "papers": len(sources["papers"]),
        "paragraphs": len(paras),
        "warnings": skeleton["warnings"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
