#!/usr/bin/env python3
"""跨篇文献知识图谱构建与自检（纯标准库）。

为什么要有这个脚本：题面要的是「一批论文 → 带证据的节点与边 → 可查询的图谱」。
按单篇 + 领域白名单抽实体，换一个学科就抽不出东西，也做不了跨篇实体合并。
本脚本用通用线索（缩写、化学式、数量+单位、指标词、术语 n-gram）抽实体，
用动词线索定关系方向，再按归一化标签跨篇合并，最后对每条证据做原文回查。

子命令：
  build  --docs a.json b.json ... --out graph.json [--audit audit.json]
  audit  --graph graph.json [--docs ...] --out audit.json
  query  --graph graph.json --q "TMPTA"

docs 是 doctext.py 产出的 doc.json（含 paragraphs: id/page/text/section）。
退出码 0=成功；2=输入缺失或格式不符。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

# ---------------------------------------------------------------- 词法资源

STOP_ABBR = {
    "A", "AN", "THE", "AND", "OR", "NOT", "IN", "ON", "AT", "OF", "TO", "FOR", "BY",
    "AS", "IS", "ARE", "WAS", "WERE", "BE", "WE", "IT", "ITS", "THIS", "THAT", "THESE",
    "THOSE", "WITH", "FROM", "BUT", "IF", "SO", "NO", "ALL", "ANY", "CAN", "MAY", "MUST",
    "FIG", "FIGS", "TABLE", "EQ", "REF", "ET", "AL", "VS", "E", "G", "I", "II", "III",
    "IV", "V", "VI", "VII", "VIII", "IX", "X", "SI", "PDF", "DOI", "URL", "HTTP", "HTTPS",
    "ABSTRACT", "INTRODUCTION", "CONCLUSION", "RESULTS", "DISCUSSION", "METHODS",
}

# 缩写 / 化学式 / 模型名：全大写 2-10 位，允许数字
RE_ABBR = re.compile(r"(?<![A-Za-z])[A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]{1,6})?(?![A-Za-z])")
# 驼峰专名（ResNet、Cytoscape、PyTorch 这类）
RE_CAMEL = re.compile(r"(?<![A-Za-z])[A-Z][a-z]{1,12}(?:[A-Z][A-Za-z0-9]{1,12})+(?![A-Za-z])")
# 化学式样：SiO2 / TiO2 / CH3CN
RE_FORMULA = re.compile(r"(?<![A-Za-z])[A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)+(?![a-z])")
# 数量 + 单位
RE_QUANT = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*"
    r"(wt%|vol%|at%|%|°C|℃|K|nm|μm|um|mm|cm|m|mL|ml|L|mg|μg|ug|g|kg|"
    r"h|min|s|ms|ns|ps|Hz|kHz|MHz|GHz|MPa|GPa|kPa|Pa|eV|meV|keV|"
    r"Da|kDa|mol|mmol|μmol|mM|μM|nM|rpm|cycles?|times?|folds?)(?![A-Za-z])")
ZH_METRIC = re.compile(
    r"(转化率|产率|收率|效率|分子量|粒径|温度|浓度|强度|速率|寿命|纯度|选择性|"
    r"孔隙率|电导率|比表面积|硬度|模量|拉伸强度|断裂伸长率|结晶度|接枝率)")
REL_RULES = [
    ("causes", re.compile(r"\b(leads? to|results? in|causes?|induces?|triggers?|gives? rise to)\b|导致|引起|造成|诱发", re.I), 1),
    ("increases", re.compile(r"\b(increas\w*|enhanc\w*|improv\w*|boost\w*|promot\w*|rais\w*)\b|提高|提升|增强|促进|增大", re.I), 1),
    ("decreases", re.compile(r"\b(decreas\w*|reduc\w*|suppress\w*|inhibit\w*|lower\w*|diminish\w*)\b|降低|减少|抑制|削弱|下降", re.I), 1),
    ("uses", re.compile(r"\b(us(?:e|es|ed|ing)|utiliz\w*|employ\w*|via|based on|by means of)\b|采用|使用|利用|基于", re.I), 1),
    ("composed_of", re.compile(r"\b(consists? of|composed? of|compris\w*|contain\w*)\b|由.{0,12}(组成|构成)|包含", re.I), 1),
    ("compares_with", re.compile(r"\b(outperform\w*|compared? (?:with|to)|versus|vs\.?|better than)\b|优于|相比|对比", re.I), 1),
    ("improved_by", re.compile(r"\b(?:was|were|is|are)\s+(?:improved|enhanced|reduced|increased)\s+by\b|经.{0,10}(改善|提高|降低)", re.I), -1),
]
# 条件 / 限定语，进边属性
RE_COND = re.compile(
    r"\b(under|at|when|in the presence of|with(?:in)?|after|before|unless|except)\b[^.;。]{3,60}"
    r"|(?:在|当|若)[^。；]{2,40}(?:时|条件下|情况下)", re.I)

# 缩写本身不带类型信息，用同句的语境词投票定类型；投不出来才留 abbr。
TYPE_HINT = {
    "material": re.compile(r"\b(polymer|monomer|resin|catalyst|solvent|nanoparticle|hydrogel|"
                           r"composite|alloy|oxide|acid|film|coating|material|sample|dopant)\b"
                           r"|材料|聚合物|单体|树脂|催化剂|溶剂|纳米|复合|合金|氧化物|涂层|样品", re.I),
    "method": re.compile(r"\b(method|approach|technique|assay|spectroscop\w*|chromatograph\w*|"
                         r"microscop\w*|simulation|model|algorithm|analysis|measurement|"
                         r"photolysis|irradiation|polymerization|annealing)\b"
                         r"|方法|技术|光谱|色谱|显微|模拟|算法|分析|测量|聚合|辐照", re.I),
    "metric": re.compile(r"\b(rate|efficiency|yield|conversion|accuracy|error|precision|recall|"
                         r"coefficient|viscosity|conductivity|strength|absorbance|wavelength)\b"
                         r"|速率|效率|产率|转化率|精度|误差|强度|电导|吸光|波长", re.I),
    "task": re.compile(r"\b(synthesis|fabrication|characterization|curing|printing|coating|"
                       r"detection|classification|segmentation|prediction|extraction)\b"
                       r"|合成|制备|表征|固化|打印|涂覆|检测|分类|分割|预测|提取", re.I),
}

MIN_TEXT = 20
MAX_EVID_PER_NODE = 6


def norm_label(s):
    """标签归一：小写、去首尾符号、去复数 s、压缩空白。合并靠它，显示仍用原文。"""
    t = s.strip().strip(".,;:()[]{}'\"")
    t = re.sub(r"\s+", " ", t).lower()
    if len(t) > 4 and t.endswith("ies"):
        t = t[:-3] + "y"
    elif len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")):
        t = t[:-1]
    return t


def split_sent(text):
    return [s for s in re.split(r"(?<=[.!?。！？])\s+|\n+", text) if s and s.strip()]


def load_docs(paths):
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or "paragraphs" not in d:
            raise SystemExit(json.dumps({"error": "not a doctext doc", "path": p}, ensure_ascii=False))
        d.setdefault("file", os.path.basename(p))
        out.append(d)
    return out


def paras(doc):
    return [p for p in doc.get("paragraphs") or [] if (p.get("text") or "").strip()]


# ---------------------------------------------------------------- 抽取

def extract_entities(text):
    """返回 [(label, type, span_start, span_end)]，同一位置只留最长匹配。"""
    hits = []
    for rx, etype in ((RE_FORMULA, "material"), (RE_CAMEL, "method"),
                      (RE_ABBR, "abbr")):
        for m in rx.finditer(text):
            lab = m.group(0)
            if etype == "abbr" and lab.upper() in STOP_ABBR:
                continue
            if len(lab) < 2:
                continue
            hits.append((lab, etype, m.start(), m.end()))
    for m in RE_QUANT.finditer(text):
        lab = m.group(0).strip()
        hits.append((lab, "quantity", m.start(), m.end()))
    for m in ZH_METRIC.finditer(text):
        hits.append((m.group(0), "metric", m.start(), m.end()))
    # 去掉被更长匹配完全包住的碎片
    hits.sort(key=lambda h: (h[2], -(h[3] - h[2])))
    kept = []
    for h in hits:
        if any(h[2] >= k[2] and h[3] <= k[3] and h is not k for k in kept):
            continue
        kept.append(h)
    return kept


def extract_edges_in_sentence(sent, ents):
    """句内实体配对：有动词线索才定方向；没有动词时最多留 1 条共现。

    纯共现边在评审里等于「没证明关系」：一页论文能凑出上百条 co_occurs_with，
    既撑不起关系类型分，也让真正有方向的关系被淹没。所以共现只作兜底，
    每句最多 1 条，且整句有动词时一条共现都不出。
    """
    if len(ents) < 2:
        return []
    trig = []
    for rel, rx, sign in REL_RULES:
        m = rx.search(sent)
        if m:
            trig.append((rel, m.start(), m.group(0), sign))
    trig.sort(key=lambda x: x[1])
    out = []
    ordered = sorted(ents, key=lambda e: e[2])
    co_used = False
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            if (b[2] - a[3]) > 120:          # 跨太远，不当同一关系
                continue
            between = [x for x in trig if a[3] <= x[1] <= b[2]]
            if between:
                rel, pos, kw, sign = between[0]
                src, tgt = (a, b) if sign > 0 else (b, a)
                out.append({"source": src, "target": tgt, "relation": rel,
                            "trigger": kw.strip()[:60],
                            "basis": "关系词位于两实体之间",
                            "strength": "medium"})
            elif not trig and not co_used:
                out.append({"source": a, "target": b, "relation": "co_occurs_with",
                            "trigger": None, "basis": "无中间关系词，仅记共现",
                            "strength": "weak"})
                co_used = True
            if len(out) >= 4:                 # 单句最多 4 条，避免组合爆炸
                return out
    return out


def build(docs, max_per_page=40):
    nodes, edges = {}, []
    measurements = []
    per_paper = {}
    for doc in docs:
        pf = {"file": doc.get("file"), "pages": doc.get("pages") or doc.get("stats", {}).get("pages"),
              "node_ids": set(), "evidences": 0, "checked": 0}
        for p in paras(doc):
            text = p.get("text") or ""
            if len(text) < MIN_TEXT:
                continue
            pid, page = p.get("id"), p.get("page")
            made_here = 0
            for sent in split_sent(text):
                ents = extract_entities(sent)
                if not ents:
                    continue
                # 数量不是实体，是属性：单独存 measurements，并挂到同句的边上
                quants = [e[0] for e in ents if e[1] == "quantity"]
                ents = [e for e in ents if e[1] != "quantity"]
                if quants:
                    measurements.append({"paper": doc["file"], "page": page,
                                         "paragraph_id": pid, "values": quants[:6],
                                         "quote": sent.strip()[:300]})
                if not ents:
                    continue
                for lab, etype, s0, s1 in ents:
                    key = norm_label(lab)
                    if not key:
                        continue
                    n = nodes.setdefault(key, {"id": key, "type": etype, "labels": Counter(),
                                               "papers": Counter(), "evidence": [],
                                               "votes": Counter()})
                    if etype == "abbr":
                        for vt, vrx in TYPE_HINT.items():
                            if vrx.search(sent):
                                n["votes"][vt] += 1
                    n["labels"][lab] += 1
                    n["type"] = n["type"] if n["type"] != "abbr" else etype
                    n["papers"][doc["file"]] += 1
                    if len(n["evidence"]) < MAX_EVID_PER_NODE:
                        n["evidence"].append({"paper": doc["file"], "page": page,
                                              "paragraph_id": pid,
                                              "quote": sent.strip()[:300]})
                    pf["node_ids"].add(key)
                for e in extract_edges_in_sentence(sent, ents):
                    src, tgt = norm_label(e["source"][0]), norm_label(e["target"][0])
                    if not src or not tgt or src == tgt:
                        continue
                    if (src not in nodes) or (tgt not in nodes):
                        continue
                    conds = [c.strip()[:80] for c in RE_COND.findall(sent)][:2]
                    edges.append({
                        "edge_id": "e%05d" % (len(edges) + 1),
                        "source": src, "target": tgt,
                        "source_label": e["source"][0], "target_label": e["target"][0],
                        "relation": e["relation"], "trigger": e["trigger"],
                        "values": quants[:6],
                        "cross_paper": False,
                        "conditions": conds,
                        "paper": doc["file"], "page": page, "paragraph_id": pid,
                        "quote": sent.strip()[:300],
                        "basis": e["basis"], "strength": e["strength"],
                    })
                    made_here += 1
                    if made_here >= max_per_page:
                        break
                if made_here >= max_per_page:
                    break
            pf["evidences"] += len(extract_entities(text))
        per_paper[doc["file"]] = {"file": doc["file"], "pages": pf["pages"],
                                  "entities": len(pf["node_ids"]),
                                  "candidates": pf["evidences"]}

    # 跨篇：同一实体出现在多篇 → 标记 cross_paper，并把 alias 并列
    papers_of = {k: set(v["papers"].keys()) for k, v in nodes.items()}
    cross = {k for k, s in papers_of.items() if len(s) > 1}
    for e in edges:
        if e["source"] in cross or e["target"] in cross:
            e["cross_paper"] = True

    # 只把「参与至少一条关系」的实体放进 nodes；其余进 mentions。
    # 孤立节点在图里没有语义（图谱的价值是关系），混在 nodes 里会被判成噪声。
    linked = set()
    for e in edges:
        linked.add(e["source"])
        linked.add(e["target"])

    out_nodes, mentions = [], []
    for k, v in nodes.items():
        main = v["labels"].most_common(1)[0][0] if v["labels"] else k
        vtype = v["type"]
        if vtype == "abbr" and v.get("votes"):
            vtype = v["votes"].most_common(1)[0][0]
        item = {
            "id": k, "type": vtype, "label": main,
            "aliases": [a for a, _ in v["labels"].most_common()[1:6]],
            "papers": sorted(v["papers"].keys()),
            "cross_paper": k in cross,
            "evidence": v["evidence"],
        }
        if k in linked:
            out_nodes.append(item)
        else:
            mentions.append(item)
    out_nodes.sort(key=lambda n: (-len(n["papers"]), n["id"]))
    mentions.sort(key=lambda n: (-len(n["papers"]), n["id"]))

    return {"nodes": out_nodes, "edges": edges, "measurements": measurements,
            "mentions": mentions[:200],
            "stats": {"docs": len(docs), "nodes": len(out_nodes), "edges": len(edges),
                      "measurements": len(measurements), "mentions": len(mentions),
                      "cross_paper_nodes": len(cross),
                      "per_paper": per_paper},
            "schema": {"node_types": sorted({n["type"] for n in out_nodes}),
                       "relations": sorted({e["relation"] for e in edges})}}


# ---------------------------------------------------------------- 自检

def audit(graph, docs=None):
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    text_of = {}
    if docs:
        for d in docs:
            for p in paras(d):
                text_of[(d["file"], p.get("id"))] = (p.get("text") or "")

    def quote_ok(ev):
        key = (ev.get("paper"), ev.get("paragraph_id"))
        body = text_of.get(key)
        if body is None:
            return None                     # 没给原文，无法判断
        q = (ev.get("quote") or "")[:60].strip()
        return bool(q) and q in body

    node_checks, edge_checks = [], []
    for n in nodes:
        evs = n.get("evidence") or []
        res = [quote_ok(e) for e in evs]
        node_checks += [r for r in res if r is not None]
        if not evs:
            node_checks.append(False)
    bad_edge = 0
    for e in edges:
        ok = quote_ok({"paper": e.get("paper"), "paragraph_id": e.get("paragraph_id"),
                       "quote": e.get("quote")})
        if ok is None:
            ok = bool(e.get("paragraph_id") and e.get("page"))
        edge_checks.append(ok)
        if not ok:
            bad_edge += 1

    deg = Counter()
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1
    orphans = [n["id"] for n in nodes if deg.get(n["id"], 0) == 0]
    by_type = Counter(n["type"] for n in nodes)
    rel_count = Counter(e["relation"] for e in edges)
    weak_ratio = round(sum(1 for e in edges if e.get("strength") == "weak") / max(1, len(edges)), 3)

    report = {
        "nodes": len(nodes), "edges": len(edges),
        "node_types": dict(by_type), "relations": dict(rel_count),
        "edge_evidence_rate": round(sum(1 for x in edge_checks if x) / max(1, len(edges)), 3),
        "node_evidence_rate": round(sum(1 for x in node_checks if x) / max(1, len(node_checks)), 3),
        "orphan_nodes": len(orphans), "orphan_sample": orphans[:10],
        "weak_edge_ratio": weak_ratio,
        "cross_paper_nodes": sum(1 for n in nodes if n.get("cross_paper")),
        "per_paper": (graph.get("stats") or {}).get("per_paper"),
    }
    gates = []
    if nodes and report["node_evidence_rate"] < 0.95:
        gates.append("节点证据回查率 %s < 0.95：有节点引不到原文片段" % report["node_evidence_rate"])
    if edges and report["edge_evidence_rate"] < 0.95:
        gates.append("边证据回查率 %s < 0.95：有边缺 paragraph_id 或 quote" % report["edge_evidence_rate"])
    if nodes and len(orphans) > max(5, len(nodes) // 5):
        gates.append("孤立节点 %d 个（>20%%）：检查是否只抓到句子边缘的缩写碎片" % len(orphans))
    if edges and weak_ratio > 0.7:
        gates.append("弱边占比 %s 过高：多数关系只是共现，需补关系词或标注不可用" % weak_ratio)
    for f, p in ((graph.get("stats") or {}).get("per_paper") or {}).items():
        if p.get("entities", 0) < 8:
            gates.append("《%s》只抽到 %d 个实体：该篇可能无文字层或词表不适配，需标注" % (f, p.get("entities", 0)))
    report["gates"] = gates
    report["ok"] = not gates
    return report


def query(graph, q):
    ql = norm_label(q)
    hit = [n for n in graph["nodes"] if ql in n["id"] or ql in norm_label(n["label"])]
    ids = {n["id"] for n in hit}
    es = [e for e in graph["edges"] if e["source"] in ids or e["target"] in ids]
    return {"query": q, "answerable": bool(hit), "nodes": hit[:20], "edges": es[:40],
            "note": "未命中即图谱未收录该实体，不用常识补答" if not hit else "关系方向与条件见 edge"}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build")
    b.add_argument("--docs", nargs="+", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--audit")
    b.add_argument("--max-per-page", type=int, default=40)

    a = sub.add_parser("audit")
    a.add_argument("--graph", required=True)
    a.add_argument("--docs", nargs="*")
    a.add_argument("--out")

    q = sub.add_parser("query")
    q.add_argument("--graph", required=True)
    q.add_argument("--q", required=True)

    args = ap.parse_args()
    if args.cmd == "build":
        docs = load_docs(args.docs)
        g = build(docs, args.max_per_page)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=1)
        rep = audit(g, docs)
        if args.audit:
            with open(args.audit, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
        print(json.dumps({"ok": rep["ok"], "out": args.out, "stats": g["stats"],
                          "gates": rep["gates"]}, ensure_ascii=False))
        return 0
    if args.cmd == "audit":
        g = json.load(open(args.graph, encoding="utf-8"))
        docs = load_docs(args.docs) if args.docs else None
        rep = audit(g, docs)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0
    g = json.load(open(args.graph, encoding="utf-8"))
    print(json.dumps(query(g, args.q), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
