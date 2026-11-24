#!/usr/bin/env python3
"""对 result.json 中的图谱执行真实查询，返回结果子图 + 支撑证据 + 不确定关系。

内置查询模板（题面要求至少 3 个真实查询）：
  Q1 按实体名查邻居（1 跳子图）。
  Q2 按关系类型查所有边（如 outperforms / uses）。
  Q3 查某结论节点的所有支撑/反驳证据链（节点->边->evidence->paragraph_id）。
  Q4 查跨篇同形术语（检查是否错误合并 / 是否保留为独立节点）。
  Q5 查某 source_id 下的全部节点（单篇视图，防跨篇污染）。

查询不会凭空生成证据：只从已声明的 graph.nodes/edges/evidence 中检索。
无结果时返回 empty=true 并写入 note，不编造。

用法:
    python3 query_graph.py <result.json> --out query_results.json
    python3 query_graph.py <result.json> --preset neighbors --entity "Method M" --out query_results.json
"""
import argparse
import json
import sys


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def node_label(result, nid):
    for n in (result.get("result") or {}).get("graph", {}).get("nodes", []):
        if n.get("id") == nid:
            return n.get("label", nid)
    return nid


def evidence_of(obj):
    return obj.get("evidence") or []


def run_neighbors(graph, entity):
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    hit = [n for n in nodes if entity.lower() in str(n.get("label", "")).lower()]
    ids = {n["id"] for n in hit}
    sub_edges = []
    for e in edges:
        if e.get("subject") in ids or e.get("object") in ids:
            sub_edges.append(e)
            ids.add(e.get("subject")); ids.add(e.get("object"))
    ev = []
    for n in nodes:
        if n.get("id") in ids:
            ev.extend(evidence_of(n))
    for e in sub_edges:
        ev.extend(evidence_of(e))
    return {
        "question": "查询实体 '%s' 的 1 跳邻居与证据" % entity,
        "result_subgraph": {"nodes": sorted(ids), "edges": [e.get("id") for e in sub_edges]},
        "evidence": ev,
        "uncertain": [{"node": n.get("id"), "reason": "低置信/间接证据"} for n in nodes
                      if n.get("id") in ids and n.get("confidence") in ('low', 'medium')],
        "empty": not hit,
    }


def run_relation(graph, relation):
    edges = [e for e in graph.get("edges", []) if e.get("relation") == relation]
    ev = []
    for e in edges:
        ev.extend(evidence_of(e))
    return {
        "question": "查询关系类型 '%s' 的所有边" % relation,
        "result_subgraph": {
            "edges": [e.get("id") for e in edges],
            "nodes": sorted({x for e in edges for x in (e.get("subject"), e.get("object")) if x}),
        },
        "evidence": ev,
        "uncertain": [],
        "empty": not edges,
    }


def run_conclusion_chain(graph, conclusion_id):
    edges = [e for e in graph.get("edges", [])
             if e.get("subject") == conclusion_id or e.get("object") == conclusion_id]
    ev = []
    for e in edges:
        ev.extend(evidence_of(e))
    for n in graph.get("nodes", []):
        if n.get("id") == conclusion_id:
            ev.extend(evidence_of(n))
    return {
        "question": "查询结论节点 '%s' 的全部支撑/反驳证据链" % conclusion_id,
        "result_subgraph": {"nodes": [conclusion_id], "edges": [e.get("id") for e in edges]},
        "evidence": ev,
        "uncertain": [{"edge": e.get("id"), "reason": e.get("note", "")} for e in edges if e.get("uncertain")],
        "empty": not edges,
    }


def run_cross_source(graph):
    surf = {}
    for n in graph.get("nodes", []):
        srcs = {str(ev.get("source_id")) for ev in evidence_of(n)}
        if len(srcs) > 1:
            surf.setdefault(str(n.get("label")), []).append(n.get("id"))
    merged = [a for a in graph.get("alignments", []) if a.get("action") == "merge"]
    return {
        "question": "查询跨篇同形术语与对齐处置",
        "result_subgraph": {"nodes": [nid for ids in surf.values() for nid in ids]},
        "evidence": [a.get("identity_basis") for a in merged if isinstance(a.get("identity_basis"), dict)],
        "uncertain": [{"surface": s, "ids": ids, "reason": "跨篇同形，需核对是否错误合并"} for s, ids in surf.items()],
        "empty": not surf,
    }


def run_source_view(graph, source_id):
    nodes = [n for n in graph.get("nodes", [])
             if any(str(ev.get("source_id")) == source_id for ev in evidence_of(n))]
    ids = {n["id"] for n in nodes}
    edges = [e for e in graph.get("edges", [])
             if e.get("subject") in ids and e.get("object") in ids and
             any(str(ev.get("source_id")) == source_id for ev in evidence_of(e))]
    ev = []
    for n in nodes:
        ev.extend(evidence_of(n))
    for e in edges:
        ev.extend(evidence_of(e))
    return {
        "question": "查询 source_id='%s' 的单篇子图" % source_id,
        "result_subgraph": {"nodes": sorted(ids), "edges": [e.get("id") for e in edges]},
        "evidence": ev,
        "uncertain": [],
        "empty": not nodes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", choices=["all", "neighbors", "relation", "conclusion", "cross_source", "source"],
                    default="all")
    ap.add_argument("--entity", default="")
    ap.add_argument("--relation", default="")
    ap.add_argument("--conclusion-id", default="")
    ap.add_argument("--source-id", default="")
    args = ap.parse_args()

    result = load_json(args.result)
    graph = (result.get("result") or {}).get("graph") or {}
    out = []
    if args.preset in ("all", "neighbors"):
        ent = args.entity or (graph.get("nodes") or [{}])[0].get("label", "")
        if ent:
            out.append(run_neighbors(graph, ent))
    if args.preset in ("all", "relation"):
        rel = args.relation or "uses"
        out.append(run_relation(graph, rel))
    if args.preset in ("all", "conclusion"):
        cid = args.conclusion_id or (graph.get("nodes") or [{}])[0].get("id", "")
        if cid:
            out.append(run_conclusion_chain(graph, cid))
    if args.preset in ("all", "cross_source"):
        out.append(run_cross_source(graph))
    if args.preset in ("all", "source"):
        sid = args.source_id or "primary"
        out.append(run_source_view(graph, sid))

    payload = {
        "note": "真实查询结果，仅从已声明图谱检索；empty=true 表示确实无结果，不编造证据。",
        "query_count": len(out),
        "queries": out,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps({"out": args.out, "queries": len(out),
                      "empty": [i for i, q in enumerate(out) if q.get("empty")]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
