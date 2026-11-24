#!/usr/bin/env python3
"""把知识图谱导出为可读文件：nodes.jsonl / edges.jsonl / graph.json（含全部证据字段）。

导出是“可读图谱文件”，每个节点/边保留 source_id、paragraph_id、quote；
并输出 alignments（合并依据）与 conflicts（不得合并的对象），支持增量更新时稳定编号。

用法:
    python3 export_graph.py <result.json> --out-dir graph_export [--check-only]
"""
import argparse
import json
import os


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    result = load_json(args.result)
    g = (result.get("result") or {}).get("graph") or {}
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []
    aligns = g.get("alignments") or []
    conflicts = g.get("conflicts") or []

    problems = []
    seen = set()
    for n in nodes:
        if n.get("id") in seen:
            problems.append("重复 node id: " + str(n.get("id")))
        seen.add(n.get("id"))
        if not n.get("evidence"):
            problems.append("node %s 无证据" % n.get("id"))
    eseen = set()
    for e in edges:
        if e.get("id") in eseen:
            problems.append("重复 edge id: " + str(e.get("id")))
        eseen.add(e.get("id"))
        if e.get("subject") not in seen or e.get("object") not in seen:
            problems.append("edge %s 端点不在节点集" % e.get("id"))
        if not e.get("evidence"):
            problems.append("edge %s 无证据" % e.get("id"))

    payload = {
        "status": "ok" if not problems else "invalid",
        "counts": {"nodes": len(nodes), "edges": len(edges),
                   "alignments": len(aligns), "conflicts": len(conflicts)},
        "problems": problems,
    }
    if not args.check_only and args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        with open(os.path.join(args.out_dir, "nodes.jsonl"), "w", encoding="utf-8") as f:
            for n in nodes:
                f.write(json.dumps(n, ensure_ascii=False) + "\n")
        with open(os.path.join(args.out_dir, "edges.jsonl"), "w", encoding="utf-8") as f:
            for e in edges:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        with open(os.path.join(args.out_dir, "graph.json"), "w", encoding="utf-8") as f:
            json.dump({"nodes": nodes, "edges": edges, "alignments": aligns, "conflicts": conflicts},
                      f, ensure_ascii=False, indent=2)
        payload["files"] = ["nodes.jsonl", "edges.jsonl", "graph.json"]
        payload["out_dir"] = args.out_dir
    print(json.dumps(payload, ensure_ascii=False))
    import sys
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
