#!/usr/bin/env python3
"""readwork —— 在 doctext 的文档模型上做阅读类任务的结构化加工。

同一套工具覆盖五个阅读任务，靠子命令区分：
  glossary   术语抽取与一致性检查（翻译类）
  bilingual  段落级双语对照骨架与译法核验（翻译类）
  notes      章节对齐的结构化笔记骨架（笔记类）
  claims     断言拆解 + 证据片段绑定（Nanopublication 类）
  graph      实体/关系候选 + 图谱查询（知识图谱类）
  verify     结果契约与证据回查自检（通用）

共同原则：
  * 只产出**候选结构**与**可回查证据**，不生成未经材料支持的结论；
  * 每个产物都带 paragraph_id / page / quote，quote 必须能在 doc.json 里逐字找到；
  * 判定不出的地方写进 limitations，不填默认值。

用法示例：
  python readwork.py glossary  doc.json --out work/terms.json
  python readwork.py claims    doc.json --out work/claims.json --max 40
  python readwork.py graph     doc.json --out work/graph.json
  python readwork.py verify    output/result.json --doc work/doc.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CJK = re.compile(r"[\u4e00-\u9fff]")
SENT = re.compile(r"(?<=[.!?。！？])\s+|(?<=[；;])")


# ---------------------------------------------------------------- 工具


def load_doc(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def paras(doc: dict) -> list[dict]:
    return doc.get("paragraphs") or []


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT.split(text) if s and s.strip()]


def find_para(doc: dict, pid: str) -> dict | None:
    for p in paras(doc):
        if p["id"] == pid:
            return p
    return None


def evidence(doc: dict, pid: str, quote: str) -> dict:
    p = find_para(doc, pid) or {}
    q = quote.strip()
    ok = bool(q) and q in (p.get("text") or "")
    return {"page": p.get("page"), "paragraph_id": pid, "quote": q,
            "quote_verified": ok}


# ---------------------------------------------------------------- glossary


_DEF_ABBR = re.compile(r"([A-Za-z][A-Za-z\-\s]{2,60}?)\s*\(([A-Z][A-Za-z0-9\-]{1,9})\)")
_TERM_HEADS = re.compile(
    r"\b(?:the\s+)?([a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,3})\s+"
    r"(?:was|were|is|are|has|have|can|may)\b")


def cmd_glossary(doc: dict, args) -> dict:
    """抽术语候选：缩写定义式 + 高频名词短语；并检查同一术语的译名一致性入口。"""
    terms: dict[str, dict] = {}

    for p in paras(doc):
        t = p.get("text") or ""
        for full, abbr in _DEF_ABBR.findall(t):
            full = full.strip()
            if len(full) < 4:
                continue
            key = abbr.lower()
            e = terms.setdefault(key, {"term": abbr, "full": full, "kind": "abbreviation",
                                       "occurrences": [], "translations": []})
            e["occurrences"].append(evidence(doc, p["id"], abbr))

    freq: dict[str, int] = {}
    for p in paras(doc):
        for m in _TERM_HEADS.finditer((p.get("text") or "").lower()):
            ph = m.group(1)
            if 3 <= len(ph) <= 48:
                freq[ph] = freq.get(ph, 0) + 1
    stop = {"the", "this", "that", "these", "those", "a", "an"}
    for ph, n in sorted(freq.items(), key=lambda kv: -kv[1])[:args.top]:
        if n < 3 or ph.split()[0] in stop:
            continue
        if ph.lower() in terms:
            continue
        pid, quote = None, None
        for p in paras(doc):
            if ph.lower() in (p.get("text") or "").lower():
                pid, quote = p["id"], ph
                break
        terms[ph.lower()] = {"term": ph, "full": None, "kind": "phrase",
                             "occurrences": [evidence(doc, pid, quote)] if pid else [],
                             "translations": [], "freq": n}

    out = {
        "source": doc.get("file"),
        "term_count": len(terms),
        "terms": list(terms.values()),
        "usage": ("把每个 term 的 translations 填上（zh 或 en），然后跑 "
                  "bilingual --check 检查全篇是否同一译名；不得为未出现的词补译名"),
        "limitations": ["术语为规则抽取的候选，需人工确认是否为领域术语"],
    }
    return out


# ---------------------------------------------------------------- bilingual


def cmd_bilingual(doc: dict, args) -> dict:
    """段落级双语对照骨架；--check 时校验译文的数字/单位/引用是否保留。"""
    rows = []
    for p in paras(doc):
        t = p.get("text") or ""
        if len(t) < 12 or p.get("is_heading"):
            continue
        rows.append({
            "paragraph_id": p["id"], "page": p["page"], "section": p.get("section"),
            "source": t, "target": None,
            "numbers": re.findall(r"\d+(?:\.\d+)?", t),
            "units": re.findall(r"\b(?:nm|mm|cm|m|kg|g|mg|mL|L|%|wt%|mol|mM|μM|"
                                r"°C|K|min|h|s|eV|Hz|rpm|MPa|Pa)\b", t),
            "citations": re.findall(r"\[(\d{1,3}(?:[,\-–]\s?\d{1,3})*)\]", t),
            "formulas": re.findall(r"\$[^$]{1,80}\$", t),
        })
    return {"source": doc.get("file"), "n_rows": len(rows), "rows": rows,
            "usage": ("逐行填 target（译文）。填完用 --check 复核：数字、单位、引用、"
                      "公式必须与 source 一一对应，缺一个即标 mismatch"),
            "limitations": ["骨架不保证语义边界正确，跨页续段需人工确认"]}


def check_bilingual(pairs: list[dict]) -> list[dict]:
    problems = []
    for r in pairs:
        tgt = r.get("target") or ""
        if not tgt.strip():
            problems.append({"paragraph_id": r["paragraph_id"], "kind": "untranslated"})
            continue
        miss = [n for n in r.get("numbers") or [] if n not in tgt]
        if miss:
            problems.append({"paragraph_id": r["paragraph_id"],
                             "kind": "number_missing", "detail": miss[:6]})
        missed_u = [u for u in r.get("units") or [] if u not in tgt]
        if missed_u:
            problems.append({"paragraph_id": r["paragraph_id"],
                             "kind": "unit_missing", "detail": missed_u[:6]})
        if r.get("citations") and not re.search(r"[\[［]\s*\d", tgt):
            problems.append({"paragraph_id": r["paragraph_id"],
                             "kind": "citation_missing",
                             "detail": r["citations"][:6]})
        if r.get("formulas") and tgt.count("$") < 2:
            problems.append({"paragraph_id": r["paragraph_id"],
                             "kind": "formula_missing",
                             "detail": r["formulas"][:3]})
    return problems


# ---------------------------------------------------------------- notes


NOTE_FIELDS = ["research_question", "data", "methods", "conditions",
               "findings", "limitations"]


def cmd_notes(doc: dict, args) -> dict:
    """按论文自身章节建笔记骨架，字段留空由 Agent 填，但章节顺序不可改。"""
    secs = doc.get("sections") or []
    blocks = []
    for s in secs:
        text = " ".join(p.get("text") or "" for p in paras(doc)
                        if p.get("section") == s["title"])
        blocks.append({
            "section": s["title"], "page": s["page"], "level": s["level"],
            "paragraph_ids": [p["id"] for p in paras(doc)
                              if p.get("section") == s["title"]][:60],
            "chars": len(text),
            "fields": {k: None for k in NOTE_FIELDS},
            "evidence": [],
        })
    return {"source": doc.get("file"), "sections": blocks,
            "paper_card": {k: None for k in NOTE_FIELDS},
            "metadata": doc.get("metadata"),
            "usage": ("按 sections 顺序填写每节字段，evidence 必须给 "
                      "paragraph_id + quote；章节顺序来自论文本身，不要套通用模板"),
            "limitations": ["未识别到章节时会退化为单节，需人工补齐骨架"]}


# ---------------------------------------------------------------- claims


_CLAIM_SIGNAL = re.compile(
    r"\b(we (?:found|show|demonstrate|report|observe|propose)|"
    r"results? (?:show|indicate|suggest)|it is (?:shown|found)|"
    r"significantly|compared with|increased|decreased|improved|"
    r"correlat|associated with|due to|because|therefore|thus|"
    r"表明|显示|说明|发现|提高|降低|显著|相比|因此|由于)\b", re.I)
_COND = re.compile(
    r"\b(under|at|when|in the presence of|with(?:in)?|for|after|before|"
    r"unless|except|only if)\b[^.;。]{3,60}", re.I)


def cmd_claims(doc: dict, args) -> dict:
    """把含结论信号的句子拆成候选断言，绑定最小证据片段与适用条件。"""
    out = []
    for p in paras(doc):
        t = p.get("text") or ""
        if len(t) < 40 or p.get("is_heading") or p.get("is_caption"):
            continue
        for s in sentences(t):
            if not _CLAIM_SIGNAL.search(s):
                continue
            if len(s) < 30:
                continue
            cond = [m.group(0).strip() for m in _COND.finditer(s)][:4]
            out.append({
                "claim_id": f"c{len(out) + 1:03d}",
                "text": s.strip()[:600],
                "paragraph_id": p["id"], "page": p["page"],
                "section": p.get("section"),
                "conditions": cond,
                "numbers": re.findall(r"\d+(?:\.\d+)?\s*(?:%|wt%|nm|mm|°C|h|min|s)?", s)[:6],
                "needs": ("可直接引用" if cond else "缺条件：需确认适用范围后使用"),
                "evidence": evidence(doc, p["id"], s.strip()[:200]),
                "confidence": "medium",
            })
            if len(out) >= args.max:
                break
        if len(out) >= args.max:
            break
    return {"source": doc.get("file"), "claim_count": len(out), "claims": out,
            "usage": ("逐条判定 subject/relation/object 并补 conditions；"
                      "needs 标了缺条件的，不得当作无条件的普遍结论"),
            "limitations": ["断言由信号句拆得，复合句仍需人工再拆一次"]}


# ---------------------------------------------------------------- graph


_ENTITY_RULES = [
    ("method", re.compile(r"\b(photopolymerization|polymerization|NMR|FTIR|UV[- ]?Vis|"
                          r"irradiation|annealing|chromatography|spectroscopy|"
                          r"mass spectrometry|DFT|simulation|PCR|ELISA)\b", re.I)),
    ("material", re.compile(r"\b(benzophenone|sesamol|monomer|oligomer|polymer|"
                            r"nanoparticle|hydrogel|resin|catalyst|solvent|"
                            r"initiator|TMPTA|PETA|acrylate|silica)\b", re.I)),
    ("metric", re.compile(r"\b(conversion|yield|efficiency|absorbance|"
                          r"wavelength|viscosity|molecular weight|Tg|"
                          r"rate of polymerization|Rp)\b", re.I)),
    ("task", re.compile(r"\b(synthesis|characterization|measurement|curing|"
                        r"coating|printing|fabrication)\b", re.I)),
]
_REL_RULES = [
    ("uses", re.compile(r"\b(using|used|by means of|via|employ\w*)\b", re.I)),
    ("increases", re.compile(r"\b(increas\w*|enhanc\w*|promot\w*|rais\w*)\b", re.I)),
    ("decreases", re.compile(r"\b(decreas\w*|reduc\w*|inhibit\w*|lower\w*)\b", re.I)),
    ("compares_with", re.compile(r"\b(compared (?:with|to)|versus|vs\.?)\b", re.I)),
    ("supports", re.compile(r"\b(confirm\w*|support\w*|consistent with|agree\w*)\b", re.I)),
    ("contradicts", re.compile(r"\b(contradict\w*|inconsistent|disagree\w*)\b", re.I)),
]


def cmd_graph(doc: dict, args) -> dict:
    """规则法抽实体与关系候选，每条都带原文证据；不补齐原文没有的对象。"""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for p in paras(doc):
        t = p.get("text") or ""
        if len(t) < 20:
            continue
        found: dict[str, dict] = {}
        for etype, rx in _ENTITY_RULES:
            for m in rx.finditer(t):
                name = m.group(0)
                key = f"{etype}:{name.lower()}"
                if key not in nodes:
                    nodes[key] = {"id": key, "type": etype, "label": name,
                                  "aliases": [], "evidence": []}
                nodes[key]["evidence"].append(evidence(doc, p["id"], name))
                if name not in found:      # 只记首次出现位置，用于定方向
                    found[name] = {"type": etype, "pos": m.start()}
        if len(found) < 2:
            continue
        # 方向只能由"关系词夹在两个实体之间"确定；否则记为共现，不臆断方向
        trig = [(rt, m.start(), m.group(0)) for rt, rx in _REL_RULES
                for m in [rx.search(t)] if m]
        names = sorted(found.items(), key=lambda kv: kv[1]["pos"])[:3]
        made = 0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if made >= 2:
                    break
                a, b = names[i], names[j]
                pa, pb = a[1]["pos"], b[1]["pos"]
                between = [x for x in trig if pa < x[1] < pb]
                rel = between[0][0] if between else "co_occurs_with"
                kw = between[0][2] if between else None
                edges.append({
                    "edge_id": f"e{len(edges) + 1:04d}",
                    "source": f"{a[1]['type']}:{a[0].lower()}",
                    "target": f"{b[1]['type']}:{b[0].lower()}",
                    "relation": rel, "trigger": kw,
                    "conditions": [c.strip() for c in _COND.findall(t)][:3],
                    "paragraph_id": p["id"], "page": p["page"],
                    "evidence": evidence(doc, p["id"], a[0]),
                    "direction_basis": ("关系词位于两实体之间" if between
                                        else "无中间关系词，仅记共现"),
                    "strength": "medium" if between else "weak",
                })
                made += 1
    edges = edges[:args.max_edges]
    return {
        "source": doc.get("file"),
        "node_count": len(nodes), "edge_count": len(edges),
        "nodes": list(nodes.values())[:1500], "edges": edges,
        "aliases_hint": ("同一实体的大小写/缩写差异在 metadata 里合并；"
                         "规则不合并同义词，需人工确认后写入 aliases"),
        "usage": ("用 query 子命令验证连通性；strength=weak 的边不得作为直接证据"),
        "limitations": ["实体由领域词表规则抽取，领域外术语可能漏抽"],
    }


def graph_query(graph: dict, q: str) -> dict:
    ql = q.lower()
    hit = [n for n in graph["nodes"] if ql in n["label"].lower()]
    ids = {n["id"] for n in hit}
    edges = [e for e in graph["edges"] if e["source"] in ids or e["target"] in ids]
    return {"query": q, "nodes": hit[:20], "edges": edges[:40],
            "answerable": bool(hit),
            "note": ("未命中实体时如实说明图谱未收录，不用常识补答"
                     if not hit else "结果为原文共现关系，方向与条件见 edge")}


# ---------------------------------------------------------------- 导出


def cmd_nanopub(claims: dict, doc: dict | None, args) -> dict:
    """把断言包成 Nanopublication 三段结构（Assertion / Provenance / PublicationInfo）。"""
    src = (doc or {}).get("file") or claims.get("source")
    sha = (doc or {}).get("sha256")
    np_list = []
    for c in claims.get("claims") or []:
        has_triple = all(c.get(k) for k in ("subject", "relation", "object"))
        assertion = ({"subject": c["subject"], "relation": c["relation"],
                      "object": c["object"]} if has_triple else
                     {"assertion_text": c.get("text"),
                      "note": "未拆成三元组，保留自然语言断言，禁止下游当作结构化事实"})
        np_list.append({
            "@context": {"np": "http://www.nanopub.org/nschema#",
                         "prov": "http://www.w3.org/ns/prov#"},
            "@id": f"urn:np:{c.get('claim_id')}",
            "np:assertion": {**assertion,
                             "conditions": c.get("conditions") or []},
            "np:provenance": {
                "prov:wasDerivedFrom": {"file": src, "sha256": sha},
                "prov:atLocation": {"page": c.get("page"),
                                    "paragraph_id": c.get("paragraph_id")},
                "prov:value": (c.get("evidence") or {}).get("quote"),
                "quote_verified": (c.get("evidence") or {}).get("quote_verified"),
            },
            "np:publicationInfo": {
                "created": args.created,
                "assertion_confidence": c.get("confidence"),
                "assertion_needs": c.get("needs"),
            },
        })
    return {"count": len(np_list), "nanopublications": np_list,
            "limitations": ["PublicationInfo 的创建者信息需按实际提交补填"]}


def cmd_graphexport(graph: dict, args) -> str:
    """把图谱导出成可直接执行的 Cypher（含证据属性），便于他人复用。"""
    lines = ["// 由 readwork.py graphexport 生成；每个节点/边都带原文证据", ""]
    for n in graph.get("nodes") or []:
        ev = (n.get("evidence") or [{}])[0]
        lines.append(
            f'MERGE (:`{n.get("type")}` {{id: "{n.get("id")}"}}) '
            f'SET label = "{n.get("label","")}", '
            f'page = {ev.get("page") or "null"}, '
            f'paragraph_id = "{ev.get("paragraph_id") or ""}", '
            f'quote = "{((ev.get("quote") or "").replace(chr(34), chr(39)))[:200]}"')
    lines.append("")
    for e in graph.get("edges") or []:
        lines.append(
            f'MATCH (a {{id: "{e.get("source")}"}}), (b {{id: "{e.get("target")}"}}) '
            f'MERGE (a)-[r:`{e.get("relation")}`]->(b) '
            f'SET r.strength = "{e.get("strength")}", '
            f'r.direction_basis = "{e.get("direction_basis") or ""}", '
            f'r.page = {e.get("page") or "null"}, '
            f'r.paragraph_id = "{e.get("paragraph_id") or ""}"')
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- verify


def cmd_verify(result: dict, doc: dict | None) -> dict:
    """结果契约自检：必需字段、状态合法性、证据可回查、缺证据条目。"""
    problems: list[str] = []
    for k in ("case_id", "status", "result", "sources"):
        if k not in result:
            problems.append(f"缺必需字段 {k}")
    st = result.get("status")
    if st not in ("success", "partial", "blocked", "unanswerable"):
        problems.append(f"status 非法：{st}")
    if st in ("partial", "blocked", "unanswerable") and not result.get("uncertainty"):
        problems.append(f"status={st} 但 uncertainty 为空（必须说明边界）")

    checked = found = 0
    idx = {}
    if doc:
        for p in paras(doc):
            idx[p["id"]] = p.get("text") or ""
    for s in result.get("sources") or []:
        checked += 1
        pid, q = s.get("paragraph_id"), (s.get("quote") or "").strip()
        if not pid:
            problems.append("证据条目缺 paragraph_id")
            continue
        if doc and pid not in idx:
            problems.append(f"证据指向不存在的段落 {pid}")
            continue
        if not q:
            problems.append(f"{pid} 的证据缺 quote")
            continue
        if doc:
            if q in idx[pid]:
                found += 1
            else:
                problems.append(f"{pid} 的 quote 无法逐字回查：{q[:40]}")
        else:
            found += 1

    cov = round(found / checked, 3) if checked else None
    return {"ok": not problems, "checked_sources": checked,
            "verified_sources": found, "evidence_coverage": cov,
            "problems": problems[:40],
            "note": ("未提供 doc.json 时只查字段完整性，不查引文是否可回查"
                     if not doc else "已按 doc.json 逐条回查引文")}


# ---------------------------------------------------------------- CLI


def main() -> int:
    ap = argparse.ArgumentParser(description="阅读类任务的结构化加工工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("glossary"); g.add_argument("doc"); g.add_argument("--out", required=True)
    g.add_argument("--top", type=int, default=40)
    b = sub.add_parser("bilingual"); b.add_argument("doc"); b.add_argument("--out", required=True)
    b.add_argument("--check", metavar="PAIRS_JSON")
    n = sub.add_parser("notes"); n.add_argument("doc"); n.add_argument("--out", required=True)
    c = sub.add_parser("claims"); c.add_argument("doc"); c.add_argument("--out", required=True)
    c.add_argument("--max", type=int, default=60)
    gr = sub.add_parser("graph"); gr.add_argument("doc"); gr.add_argument("--out", required=True)
    gr.add_argument("--max-edges", type=int, default=200)
    gr.add_argument("--query", default=None)
    v = sub.add_parser("verify"); v.add_argument("result"); v.add_argument("--doc", default=None)
    np_ = sub.add_parser("nanopub"); np_.add_argument("claims")
    np_.add_argument("--doc", default=None); np_.add_argument("--out", required=True)
    np_.add_argument("--created", default=None)
    ge = sub.add_parser("graphexport"); ge.add_argument("graph")
    ge.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "verify":
        r = load_doc(a.result)
        d = load_doc(a.doc) if a.doc else None
        out = cmd_verify(r, d)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if out["ok"] else 1

    if a.cmd == "nanopub":
        if not a.created:
            import datetime
            a.created = datetime.datetime.now().isoformat(timespec="seconds")
        claims = load_doc(a.claims)
        d2 = load_doc(a.doc) if a.doc else None
        _np_out = cmd_nanopub(claims, d2, a)
    elif a.cmd == "graphexport":
        text = cmd_graphexport(load_doc(a.graph), a)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(json.dumps({"out": a.out, "bytes": len(text.encode("utf-8"))},
                         ensure_ascii=False))
        return 0

    doc = None if a.cmd == "nanopub" else load_doc(a.doc)
    if a.cmd == "glossary":
        out = cmd_glossary(doc, a)
    elif a.cmd == "bilingual":
        out = cmd_bilingual(doc, a)
        if a.check:
            out["problems"] = check_bilingual(load_doc(a.check).get("rows") or [])
            out["ok"] = not out["problems"]
    elif a.cmd == "notes":
        out = cmd_notes(doc, a)
    elif a.cmd == "claims":
        out = cmd_claims(doc, a)
    elif a.cmd == "graph":
        out = cmd_graph(doc, a)
        if a.query:
            out["query_result"] = graph_query(out, a.query)
    else:                       # nanopub
        out = _np_out

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    brief = {k: v for k, v in out.items()
             if k in ("term_count", "n_rows", "claim_count", "node_count",
                      "edge_count", "ok", "source", "count")}
    brief["out"] = a.out
    print(json.dumps(brief, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
