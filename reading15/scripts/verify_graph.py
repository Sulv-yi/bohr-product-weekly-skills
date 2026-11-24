#!/usr/bin/env python3
"""核验知识图谱结果的四性质 + 防污染硬损伤回扫（本 Skill 的核心）。

四性质（对应题面四问）：
  抽得准 grounded  : 每个节点必须是材料里真实出现的对象；有 source_id+paragraph_id+原文短引；短引能在材料回查；不凭常识补概念。
  连得对 linked    : 每条边的 relation 命中受控词表 canonical/alias；方向合法；有直接证据；禁止共现/综述转述/推测当证据。
  对得齐 aligned   : 别名归一用 same_as 边且带 identity_basis；跨篇同形术语不得仅凭通用名词合并；冲突对象保留为独立节点。
  查得到回得去 queryable: 至少 3 个查询，每个返回结果子图+证据；每个节点/边可回到论文具体位置原文片段。

防污染硬损伤回扫（对应题面“输入修订”约束）：
  P1 根 DOI/title/authors 套用到第二篇（secondary 用了 root 的 DOI/作者）。
  P2 paragraph_id 用 PDF 页码/自建页码冒充 JATS 段落 ID（如 p.1、page 1、第1页、P1）。
  P3 跨篇数值/样本/条件拼接成一个结论（edge 或 node 的 evidence 跨 source_id 且含数值）。
  P4 无 source_id / 无 paragraph_id / 无 quote 的裸节点或裸边。
  P5 same_as 合并缺 identity_basis；通用术语同名被强制合并。
  P6 关系证据类型写成 forbidden_relation_kinds。
  P7 未报告/源内冲突被写成事实（uncertainty 为空但存在低置信节点）。

用法:
    python3 verify_graph.py <result.json> --material material.json [--manifest corpus-manifest.json]
        [--vocab assets/relation_vocab.json] [--case case.json] [--out verify.json] [--strict]
退出码：无 error 为 0，否则 1。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}
# 只匹配明确的 PDF 页码写法（p.1 / p 1 / page 1 / 第1页）；
# 不匹配 JATS 段 ID 常见的 p2 / p3 / sec2.p1 等（p 与数字之间无点无空格）。
PDF_PAGE_RE = re.compile(r'^\s*(?:p\.\s*\d+|p\s+\d+|page\s+\d+|第\s*\d+\s*页)\s*$', re.I)
NUM_RE = re.compile(r'\d+(?:\.\d+)?\s*(?:%|x|倍|nm|um|ms|s\b|kg|mg|mL\b)')
CANON_REL = None
ALIASES = None
FORBIDDEN = None


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[\u2018\u2019\u201c\u201d`\'"]', '', s)
    s = re.sub(r'[\s\u00a0]+', ' ', s)
    s = re.sub(r'[，,。.!！?？;；:：()\[\]{}《》\-—_]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def load_vocab(path):
    global CANON_REL, ALIASES, FORBIDDEN
    v = load_json(path)
    CANON_REL = {r["canonical"] for r in v.get("relations", [])}
    ALIASES = {}
    for r in v.get("relations", []):
        ALIASES[norm(r["canonical"])] = r["canonical"]
        for a in r.get("aliases", []):
            ALIASES[norm(a)] = r["canonical"]
    FORBIDDEN = set(v.get("forbidden_relation_kinds", []))
    return v


def material_paragraphs(material):
    """返回 {(source_id, paragraph_id): text} 和 {source_id: set(paragraph_id)}。

    用联合键避免两篇独立论文的段落 ID（都叫 p1/p2）互相串篇。
    """
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
    by_pid = {}   # (source_id, paragraph_id) -> text，联合键防串篇
    by_sid = {}
    for p in items:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("paragraph_id") or p.get("pid") or p.get("id") or "")
        sid = str(p.get("source_id") or p.get("paper_id") or "")
        txt = str(p.get("text") or p.get("content") or "")
        if pid:
            by_pid[(sid, pid)] = txt
        if sid:
            by_sid.setdefault(sid, set()).add(pid)
    return by_pid, by_sid


def quote_verified(evs, by_pid):
    """证据数组中是否有至少一条 direct 且短引能在其段落回查成功 —— 表示原文明确表述。"""
    for ev in evs or []:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("strength")) != "direct":
            continue
        sid, pid, quote = str(ev.get("source_id") or ""), str(ev.get("paragraph_id") or ""), str(ev.get("quote") or "")
        hay = norm(by_pid.get((sid, pid), ""))
        needle = norm(quote)
        if needle and needle in hay:
            return True
    return False


def root_doi_titles(manifest):
    if not manifest:
        return set(), set()
    root = manifest.get("root") or manifest.get("root_paper") or {}
    dois = {norm(x) for x in [root.get("doi")] if x}
    authors = set()
    for a in (root.get("authors") or []):
        if a and norm(a):
            authors.add(norm(a))
    return dois, authors


def paper_meta(manifest):
    if not manifest:
        return {}
    out = {}
    for p in manifest.get("papers", []):
        sid = str(p.get("source_id") or p.get("id") or "")
        out[sid] = {
            "doi": norm(p.get("doi")),
            "authors": {norm(a) for a in (p.get("authors") or [])},
        }
    return out


def check_evidence(ev_list, by_pid, by_sid, errors, warnings, tag, allow_missing=False):
    """校验证据数组字段齐全 + 短引可在材料回查 + paragraph_id 非 PDF 页码。"""
    if not isinstance(ev_list, list) or not ev_list:
        errors.append(tag + " 无 evidence")
        return []
    srcs = []
    for ev in ev_list:
        if not isinstance(ev, dict):
            errors.append(tag + " evidence 元素非对象")
            continue
        sid = str(ev.get("source_id") or "")
        pid = str(ev.get("paragraph_id") or "")
        quote = str(ev.get("quote") or "")
        strength = str(ev.get("strength") or "")
        if not sid or sid == "unknown":
            errors.append(tag + " 缺合法 source_id")
        if not pid or pid == "unknown":
            errors.append(tag + " 缺合法 paragraph_id")
        if PDF_PAGE_RE.match(pid):
            errors.append(tag + " paragraph_id 用了 PDF 页码 '%s'（应为 JATS 段落 ID）" % pid)
        if not quote:
            errors.append(tag + " 缺原文短引 quote")
        if strength not in ('direct', 'indirect'):
            warnings.append(tag + " evidence.strength 非法: %r" % strength)
        # 短引回查（宽松规范化，容忍线性化差异）；用 (source_id,paragraph_id) 联合键防串篇
        if pid and quote and (sid, pid) in by_pid:
            hay = norm(by_pid[(sid, pid)])
            needle = norm(quote)
            if needle and needle not in hay:
                # 允许分段短引：逐词覆盖率 >= 0.85（更严格，避免跨篇误命中）
                toks = [t for t in needle.split() if len(t) > 1]
                hit = sum(1 for t in toks if t in hay)
                if not toks or hit / len(toks) < 0.85:
                    errors.append(tag + " 短引不在 %s/%s 原文中: %r" % (sid, pid, quote[:50]))
        elif pid and quote:
            warnings.append(tag + " 段落 %s/%s 不在 material 段索引中，无法回查短引" % (sid, pid))
        if sid:
            srcs.append(sid)
        if pid and sid and by_sid and sid in by_sid and pid not in by_sid[sid]:
            warnings.append(tag + " paragraph_id=%s 不属于 source_id=%s" % (pid, sid))
    return srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--material", required=True)
    ap.add_argument("--manifest", default="")
    ap.add_argument("--vocab", default="")
    ap.add_argument("--case", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    result = load_json(args.result)
    material = load_json(args.material)
    manifest = load_json(args.manifest) if args.manifest else None
    if args.vocab:
        load_vocab(args.vocab)
    else:
        # 默认内建最小词表，保证脚本独立可用
        global CANON_REL, ALIASES, FORBIDDEN
        CANON_REL = {"uses", "compares_with", "outperforms", "supports", "contradicts",
                     "measures", "requires", "is_part_of", "same_as"}
        ALIASES = {norm(r): r for r in CANON_REL}
        FORBIDDEN = {"cooccurrence", "review_paraphrase", "speculation", "common_knowledge"}

    by_pid, by_sid = material_paragraphs(material)
    root_dois, root_authors = root_doi_titles(manifest)
    pmeta = paper_meta(manifest)

    errors, warnings = [], []
    checks = {"grounded": "ok", "linked": "ok", "aligned": "ok", "queryable": "ok"}
    g = (result.get("result") or {}).get("graph") or {}
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []
    aligns = g.get("alignments") or []
    conflicts = g.get("conflicts") or []
    queries = (result.get("result") or {}).get("queries") or []

    if result.get("status") not in VALID_STATUS:
        errors.append("status 非法: %r" % result.get("status"))

    if not isinstance(nodes, list) or not nodes:
        errors.append("graph.nodes 为空")
        checks["grounded"] = "failed"
    node_by_id = {}
    for i, n in enumerate(nodes):
        tag = "node[%s]" % (n.get("id") if isinstance(n, dict) else i)
        if not isinstance(n, dict):
            errors.append(tag + " 非对象"); continue
        nid = str(n.get("id") or "")
        if not nid:
            errors.append(tag + " 缺 id")
        if nid in node_by_id:
            errors.append("重复 node id: " + nid)
        node_by_id[nid] = n
        if n.get("type") not in ("researcher", "material", "method", "task", "metric", "conclusion"):
            errors.append(tag + " type 非法: %r" % n.get("type")); checks["grounded"] = "failed"
        if n.get("mention_role") not in ('author_self', 'other_paraphrase'):
            warnings.append(tag + " mention_role 未标明作者自述/他人转述")
        if (n.get("candidate") is True):
            errors.append(tag + " 仍是候选(candidate=true)，未确认为最终实体")
        srcs = check_evidence(n.get("evidence"), by_pid, by_sid, errors, warnings, tag)
        # 抽得准：短引必须等于 label 所在原文（label 至少一词出现在短引或段落）
        label = str(n.get("label") or "")
        if label and n.get("evidence"):
            ev0 = n["evidence"][0]
            q = norm(ev0.get("quote"))
            if label and norm(label) not in q and len(norm(label)) > 2:
                warnings.append(tag + " label '%s' 未直接出现在首选短引中（可能为概括，需核对）" % label[:30])
        # P1 根 DOI/作者套用到非第一篇
        for ev in (n.get("evidence") or []):
            sid = str(ev.get("source_id") or "")
            if sid and sid != "primary" and manifest:
                meta = pmeta.get(sid, {})
                # 该节点若声明了 doi/authors 字段，检查是否误用根
                for key, val in [("doi", n.get("doi")), ("authors", n.get("authors"))]:
                    vals = val if isinstance(val, list) else [val]
                    for v in vals:
                        if v and norm(v) in (root_dois if key == "doi" else root_authors):
                            errors.append(tag + " P1: source=%s 使用了根%s（属于第一篇）" % (sid, key))
                            checks["grounded"] = "failed"

    # 边核验
    eids = set()
    for i, e in enumerate(edges):
        tag = "edge[%s]" % (e.get("id") if isinstance(e, dict) else i)
        if not isinstance(e, dict):
            errors.append(tag + " 非对象"); continue
        eid = str(e.get("id") or "")
        if eid in eids:
            errors.append("重复 edge id: " + eid)
        eids.add(eid)
        s = str(e.get("subject") or "")
        o = str(e.get("object") or "")
        if s not in node_by_id or o not in node_by_id:
            errors.append(tag + " 端点不存在: %s -> %s" % (s, o)); checks["linked"] = "failed"
        rel_raw = str(e.get("relation") or "")
        # ALIASES 覆盖 canonical 自身与所有别名 -> canonical
        rel = ALIASES.get(norm(rel_raw)) if rel_raw else None
        if not rel:
            errors.append(tag + " relation 不在受控词表: %r" % rel_raw); checks["linked"] = "failed"
        else:
            if rel == "outperforms" and not (e.get("conditions") or {}).get("metric"):
                warnings.append(tag + " outperforms 缺 metric 条件")
        ev_type = str(e.get("evidence_type") or (e.get("evidence") or [{}])[0].get("type") or "direct")
        if ev_type in FORBIDDEN:
            errors.append(tag + " P6: 证据类型为禁止项 '%s'（共现/转述/推测/常识）" % ev_type)
            checks["linked"] = "failed"
        srcs = check_evidence(e.get("evidence"), by_pid, by_sid, errors, warnings, tag)
        # P3 跨篇数值拼接：边两端节点 evidence 来自不同 source_id 且边含数值结论
        if s in node_by_id and o in node_by_id:
            s_sids = {str(ev.get("source_id")) for ev in (node_by_id[s].get("evidence") or [])}
            o_sids = {str(ev.get("source_id")) for ev in (node_by_id[o].get("evidence") or [])}
            cross = (s_sids and o_sids and not (s_sids & o_sids))
            cond_txt = json.dumps(e.get("conditions") or {}, ensure_ascii=False)
            if cross and (NUM_RE.search(cond_txt) or rel in ('outperforms', 'supports', 'contradicts')):
                if quote_verified(e.get("evidence"), by_pid):
                    # 原文确有明确跨篇表述（如 "contradicts the earlier 92.5% claim (Smith, 2020)"），
                    # 属合法跨篇关系，但必须提示在 uncertainty 记录，避免被当成自行拼接。
                    warnings.append(tag + " P3-warn: 跨篇(source %s vs %s)关系有原文直接证据；请确认非自行拼接并在 uncertainty 记录"
                                    % (sorted(s_sids), sorted(o_sids)))
                else:
                    errors.append(tag + " P3: 跨篇(source %s vs %s)拼接数值/结论边且无原文直接证据"
                                  % (sorted(s_sids), sorted(o_sids)))
                    checks["linked"] = "failed"

    # 对齐核验
    for i, a in enumerate(aligns):
        tag = "align[%s]" % i
        if not isinstance(a, dict):
            errors.append(tag + " 非对象"); continue
        src = str(a.get("from") or "")
        dst = str(a.get("to") or "")
        if src not in node_by_id or dst not in node_by_id:
            errors.append(tag + " 端点不存在"); checks["aligned"] = "failed"
        basis = str(a.get("identity_basis") or "").strip()
        if not basis:
            errors.append(tag + " P5: same_as 合并缺 identity_basis"); checks["aligned"] = "failed"
        if a.get("action") not in ('merge', 'suggest'):
            warnings.append(tag + " action 应为 merge/suggest")
    if not aligns and not conflicts:
        warnings.append("未提供 alignments 或 conflicts：请记录别名合并依据与不得合并的冲突对象")

    # 查询核验
    if not isinstance(queries, list) or len(queries) < 3:
        errors.append("查询少于 3 个（要求至少 3 个真实查询）"); checks["queryable"] = "failed"
    for i, q in enumerate(queries):
        tag = "query[%s]" % i
        if not isinstance(q, dict):
            errors.append(tag + " 非对象"); continue
        if not str(q.get("question") or "").strip():
            errors.append(tag + " 缺 question")
        sub = q.get("result_subgraph") or {}
        if not (sub.get("nodes") or sub.get("edges")):
            warnings.append(tag + " 结果子图为空（可能是真实的“查无结果”，需在 uncertainty 说明）")
        if not q.get("evidence"):
            errors.append(tag + " 查询无支撑证据"); checks["queryable"] = "failed"
        else:
            check_evidence(q.get("evidence"), by_pid, by_sid, errors, warnings, tag)
        if "uncertain" not in q:
            warnings.append(tag + " 未标注无法确定的关系（空数组表示已检查且无，可保留 []）")

    # P7 低置信无 uncertainty
    low_conf = [n.get("id") for n in nodes if isinstance(n, dict) and
                (n.get("confidence") in ('low', 'medium') or str(n.get("evidence_strength")) == 'indirect')]
    if low_conf and not result.get("uncertainty"):
        warnings.append("存在低置信/间接证据节点 %s 但 uncertainty 为空" % low_conf[:5])

    # 契约字段
    if args.case:
        case = load_json(args.case)
        for f in case.get("output_contract", []):
            if f not in (result.get("result") or {}):
                warnings.append("输出契约字段缺失: " + f)

    failed = [k for k, v in checks.items() if v != 'ok']
    status = 'partial' if errors or failed or warnings else ('success' if not args.strict or not warnings else 'partial')
    out = {
        "status": status,
        "checks": checks,
        "counts": {"errors": len(errors), "warnings": len(warnings),
                   "nodes": len(nodes), "edges": len(edges),
                   "alignments": len(aligns), "conflicts": len(conflicts), "queries": len(queries)},
        "errors": errors,
        "warnings": warnings,
        "failed_properties": failed,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
