#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mm_check.py —— 对 nodes.json 做结构、证据、粒度、关系四类校验。

为什么要有这一步：导图的失败大多是"看不出来"的失败——节点都在、都好看，
但有的节点回不到原文，有的层级忽深忽浅，有的关系是模型脑补的。这些东西
人眼扫一遍很难发现，脚本一跑就现形。

用法：
    python3 mm_check.py --blocks work/blocks.json --nodes work/nodes.json \
        --out work/check

输出的 check.md 是给人看的，check.json 是给流程看的（fail 时退出码 1，
Agent 应据此修 nodes.json 再跑，而不是凑一份说明文字绕过去）。

校验项：
  C1 schema 完整、id 唯一
  C2 树结构合法（单根、无环、父节点存在）
  C3 类型覆盖（问题/方法/证据/结论四类齐全，且至少一条局限或不确定）
  C4 类型取值合法
  C5 标题质量（长度、重复、空话）
  C6 证据有效（block 存在、非根节点不得无证据）
  C7 数字可核（标题里的数字必须在所挂原文里出现）
  C8 层级与粒度（深度、扇出、同层长度离散度）
  C9 关系（数量、端点、类型、证据）
  C10 推断与不确定标注
"""
import argparse
import json
import math
import os
import re
import statistics
import sys

TYPES = ["root", "question", "method", "evidence", "conclusion", "limitation", "task"]
KINDS = ["cause", "depend", "contrast", "sequence", "cite", "support", "conflict"]
LEVELS = ["fact", "summary", "inference"]

MAX_DEPTH = 4
MAX_FANOUT = 7
MAX_CHILD_CV = 0.55
MAX_TITLE = 40
MIN_TITLE = 3
MAX_RELATIONS_WITHOUT_EVID = 0

# 空话标题：只有这些词的节点等于没写
EMPTY_WORDS = re.compile(
    r"^(?:研究|方法|结果|结论|讨论|背景|意义|问题|内容|其他|相关|进一步|综上|"
    r"introduction|methods?|results?|discussion|conclusion|background|other)s?$", re.I)

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?%?")


def norm_num(x):
    x = x.replace(",", "").rstrip("%")
    if x.startswith("."):
        x = "0" + x
    try:
        f = float(x)
    except ValueError:
        return x
    return ("%g" % f)


def nums(text):
    return {norm_num(m.group(0)) for m in NUM_RE.finditer(text or "")}


def bigrams(s):
    s = re.sub(r"[\s\W_]+", "", s or "")
    return {s[i:i + 2] for i in range(max(0, len(s) - 1))} or ({s} if s else set())


def similar(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True)
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--out", default="work/check")
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    ap.add_argument("--max-fanout", type=int, default=MAX_FANOUT)
    args = ap.parse_args()

    blocks = json.load(open(args.blocks, encoding="utf-8"))
    bmap = {b["id"]: b for b in blocks}
    try:
        doc = json.load(open(args.nodes, encoding="utf-8"))
    except Exception as e:
        print("nodes.json 不是合法 JSON：%s" % e, file=sys.stderr)
        return 2

    res = []          # (code, ok, detail, items)
    node_list = doc.get("nodes") or []
    by_id = {}
    dup_ids = []
    for n in node_list:
        nid = n.get("id")
        if nid in by_id:
            dup_ids.append(nid)
        by_id[nid] = n

    # ---------- C1 schema ----------
    missing = []
    bad_type_field = []
    for n in node_list:
        for f in ("id", "title", "type", "evidence"):
            if f not in n:
                missing.append("%s 缺 %s" % (n.get("id", "?"), f))
        if not isinstance(n.get("evidence"), list):
            missing.append("%s 的 evidence 不是数组" % n.get("id", "?"))
        if not isinstance(n.get("title"), str) or not n.get("title", "").strip():
            missing.append("%s 的 title 为空" % n.get("id", "?"))
    res.append(("C1 schema", not missing and not dup_ids,
                "缺字段 %d 处、重复 id %d 个" % (len(missing), len(dup_ids)),
                missing[:8] + ["重复 id: %s" % d for d in dup_ids[:5]]))

    # ---------- C2 树结构 ----------
    roots = [n for n in node_list if n.get("parent") in (None, "", "null")]
    tree_bad = []
    if len(roots) != 1:
        tree_bad.append("根节点应恰好 1 个，实际 %d 个：%s"
                        % (len(roots), [r.get("id") for r in roots[:6]]))
    for n in node_list:
        p = n.get("parent")
        if p in (None, "", "null"):
            continue
        if p not in by_id:
            tree_bad.append("%s 的父节点 %s 不存在" % (n["id"], p))
    # 环检测
    for n in node_list:
        seen, cur = set(), n.get("id")
        while cur in by_id:
            if cur in seen:
                tree_bad.append("存在环：%s" % n.get("id"))
                break
            seen.add(cur)
            cur = by_id[cur].get("parent")
    res.append(("C2 树结构", not tree_bad, "单根 + 无环 + 父节点存在", tree_bad[:8]))

    # ---------- C3 类型覆盖 ----------
    tc = {t: sum(1 for n in node_list if n.get("type") == t) for t in TYPES}
    cov_bad = []
    # 材料确实没有研究问题句时，允许不设该分支，前提是 uncertainty 里说清楚了
    q_declared = any("研究问题" in (u.get("why") or "") for u in (doc.get("uncertainty") or []))
    need_q = 0 if q_declared else 1
    for t, need in (("question", need_q), ("method", 1), ("evidence", 1), ("conclusion", 1)):
        if tc[t] < need:
            cov_bad.append("缺 %s 类节点（%d 个）" % (t, tc[t]))
    if tc["limitation"] + len(doc.get("uncertainty") or []) < 1:
        cov_bad.append("既没有 limitation 节点，也没有 uncertainty 条目")
    res.append(("C3 覆盖", not cov_bad,
                " / ".join("%s=%d" % (t, tc[t]) for t in TYPES), cov_bad))

    # ---------- C4 类型合法 ----------
    bad_types = ["%s 的 type=%r" % (n.get("id"), n.get("type"))
                 for n in node_list if n.get("type") not in TYPES]
    res.append(("C4 类型取值", not bad_types, "仅允许 %s" % "/".join(TYPES), bad_types[:8]))

    # ---------- C5 标题质量 ----------
    title_bad = []
    for n in node_list:
        t = (n.get("title") or "").strip()
        if n.get("type") == "root":
            continue
        if len(t) < MIN_TITLE:
            title_bad.append("%s 标题过短：%r" % (n.get("id"), t))
        elif len(t) > MAX_TITLE:
            title_bad.append("%s 标题 %d 字，超过 %d" % (n.get("id"), len(t), MAX_TITLE))
        if EMPTY_WORDS.match(t):
            title_bad.append("%s 标题是空话：%r" % (n.get("id"), t))
        if re.search(r"[，。；、]{2,}|的的|。。", t):
            title_bad.append("%s 标题有重复标点：%r" % (n.get("id"), t))
    # 同层（同父）重复
    groups = {}
    for n in node_list:
        groups.setdefault(n.get("parent"), []).append(n)
    for p, kids in groups.items():
        for i in range(len(kids)):
            for j in range(i + 1, len(kids)):
                s = similar(kids[i].get("title", ""), kids[j].get("title", ""))
                if s >= 0.85:
                    title_bad.append("%s 与 %s 同父且高度相似(%.2f)：%s"
                                     % (kids[i].get("id"), kids[j].get("id"), s,
                                        kids[i].get("title", "")[:24]))
    res.append(("C5 标题", not title_bad, "%d–%d 字、不重复、不空话" % (MIN_TITLE, MAX_TITLE),
                title_bad[:10]))

    # ---------- C6 证据有效 ----------
    ev_bad = []
    for n in node_list:
        ev = n.get("evidence") or []
        if n.get("type") != "root" and not ev:
            ev_bad.append("%s 没有证据块" % n.get("id"))
        for e in ev:
            if e not in bmap:
                ev_bad.append("%s 引用了不存在的块 %s" % (n.get("id"), e))
    res.append(("C6 证据", not ev_bad, "全部引用 blocks.json 中真实存在的块", ev_bad[:10]))

    # ---------- C7 数字可核 ----------
    num_bad = []
    for n in node_list:
        t = n.get("title") or ""
        # 分类节点标题里的「（6 条）」是子节点计数，不是材料里的数，先剥掉再比
        t = re.sub(r"[（(]\s*\d+\s*条\s*[)）]", "", t)
        tn = nums(t)
        if not tn:
            continue
        pool = set()
        for e in n.get("evidence") or []:
            if e in bmap:
                pool |= nums(bmap[e]["text"])
        # 标题在字数上限处被截断时，末尾数字可能只剩原文数字的前几位
        # （"7.37" 截成 "7…"），这不算编造，放行。
        def ok_num(x):
            if x in pool:
                return True
            return t.rstrip().endswith("…") and any(p.startswith(x) for p in pool)

        lost = sorted(x for x in tn if not ok_num(x))
        if lost:
            num_bad.append("%s 标题里的 %s 在所挂原文里找不到" % (n.get("id"), ",".join(lost)))
    res.append(("C7 数字", not num_bad, "标题数字逐个在原文中命中", num_bad[:10]))

    # ---------- C8 层级与粒度 ----------
    depth_of = {}

    def depth(nid, guard=0):
        if nid in depth_of:
            return depth_of[nid]
        if guard > 20:
            return 99
        n = by_id.get(nid) or {}
        p = n.get("parent")
        d = 1 if p in (None, "", "null") else depth(p, guard + 1) + 1
        depth_of[nid] = d
        return d

    deep = []
    for nid in by_id:
        d = depth(nid)
        if d > args.max_depth:
            deep.append("%s 深度 %d > %d" % (nid, d, args.max_depth))
    fan = ["%s 有 %d 个子节点 > %d" % (p, len(k), args.max_fanout)
           for p, k in groups.items() if p and len(k) > args.max_fanout]
    cv_note, cv_bad = "", []
    per_level = {}
    for nid, d in depth_of.items():
        n = by_id.get(nid) or {}
        if n.get("type") != "root":
            per_level.setdefault(d, []).append(len((n.get("title") or "").strip()))
    cvs = {}
    for d, lens in per_level.items():
        if len(lens) >= 3:
            m = statistics.mean(lens)
            sd = statistics.pstdev(lens)
            cvs[d] = sd / m if m else 0
            if cvs[d] > MAX_CHILD_CV:
                cv_bad.append("第 %d 层标题长度离散度 %.2f > %.2f（同级粒度不齐）"
                              % (d, cvs[d], MAX_CHILD_CV))
    struct_bad = deep + fan + cv_bad
    res.append(("C8 层级粒度", not struct_bad,
                "最大深度 %d、最大扇出 %d、同层长度 CV %s"
                % (max(depth_of.values()) if depth_of else 0,
                   max((len(k) for p, k in groups.items() if p), default=0),
                   ", ".join("%d:%.2f" % (d, c) for d, c in sorted(cvs.items())) or "样本不足"),
                struct_bad[:8]))

    # ---------- C9 关系 ----------
    rels = doc.get("relations") or []
    rel_bad = []
    if len(rels) < 3:
        rel_bad.append("关系只有 %d 条，至少 3 条" % len(rels))
    for i, r in enumerate(rels):
        tag = "relation#%d" % (i + 1)
        if r.get("from") not in by_id or r.get("to") not in by_id:
            rel_bad.append("%s 端点不存在：%s->%s" % (tag, r.get("from"), r.get("to")))
        if r.get("from") == r.get("to"):
            rel_bad.append("%s 自环" % tag)
        if r.get("kind") not in KINDS:
            rel_bad.append("%s kind=%r 不在允许集合" % (tag, r.get("kind")))
        ev = r.get("evidence") or []
        if len(ev) < 1 + MAX_RELATIONS_WITHOUT_EVID:
            rel_bad.append("%s 没有证据块" % tag)
        for e in ev:
            if e not in bmap:
                rel_bad.append("%s 引用不存在的块 %s" % (tag, e))
    kinds = sorted({r.get("kind") for r in rels if r.get("kind")})
    res.append(("C9 关系", not rel_bad,
                "%d 条，类型 %s" % (len(rels), ",".join(kinds) or "无"), rel_bad[:10]))

    # ---------- C10 推断标注 ----------
    unc = doc.get("uncertainty") or []
    unc_nodes = {u.get("node") for u in unc if u.get("node")}
    level_bad = []
    for n in node_list:
        lv = n.get("level")
        if lv not in LEVELS:
            level_bad.append("%s level=%r" % (n.get("id"), lv))
        elif lv == "inference" and n.get("id") not in unc_nodes:
            level_bad.append("%s 标为 inference，但 uncertainty 里没有它" % n.get("id"))
    for u in unc:
        if not u.get("why"):
            level_bad.append("uncertainty 里 %s 没写原因" % u.get("node"))
    res.append(("C10 推断标注", not level_bad,
                "%d 个 inference 已登记、%d 条不确定说明" % (
                    sum(1 for n in node_list if n.get("level") == "inference"), len(unc)),
                level_bad[:10]))

    # ---------- 汇总 ----------
    ok_n = sum(1 for _, ok, _, _ in res if ok)
    total = len(res)
    struct_score = round(ok_n / total * 100, 1)
    n_bad = sum(len(x[3]) for x in res)
    payload = {
        "case_id": doc.get("case_id"),
        "checks": [{"code": c, "ok": ok, "detail": d, "items": it} for c, ok, d, it in res],
        "passed": ok_n,
        "total": total,
        "struct_score": struct_score,
        "issue_count": n_bad,
        "counts": {"nodes": len(node_list), "relations": len(rels),
                   "uncertainty": len(unc), "types": tc},
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(payload, open(args.out + ".json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    with open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write("# 导图自查报告\n\n")
        f.write("案例：%s　节点 %d、关系 %d、待确认 %d\n\n"
                % (doc.get("case_id") or "(未标 case_id)", len(node_list), len(rels), len(unc)))
        f.write("**结构分 %s / 100（%d/%d 项通过，%d 处问题）**\n\n"
                % (struct_score, ok_n, total, n_bad))
        f.write("结构分只衡量「能不能用」，不等于平台评分；它用来在提交前挡住"
                "「回不到原文、层级失控、关系无据」这三类硬伤。\n\n")
        f.write("| 项 | 结论 | 说明 |\n|-|-|-|\n")
        for c, ok, d, it in res:
            f.write("| %s | %s | %s |\n" % (c, "PASS" if ok else "**FAIL**", d))
        f.write("\n## 待修项\n\n")
        anybad = False
        for c, ok, d, it in res:
            if not ok:
                anybad = True
                f.write("### %s\n\n" % c)
                for x in it:
                    f.write("- %s\n" % x)
                f.write("\n")
        if not anybad:
            f.write("无。全部 %d 项通过。\n" % total)
        f.write("\n## 节点类型分布\n\n")
        f.write("| 类型 | 数量 |\n|-|-|\n")
        for t in TYPES:
            f.write("| %s | %d |\n" % (t, tc[t]))

    print("结构分 %.1f/100，%d/%d 项通过，%d 处问题" % (struct_score, ok_n, total, n_bad))
    print("报告：%s.md / %s.json" % (args.out, args.out))
    return 0 if ok_n == total else 1


if __name__ == "__main__":
    sys.exit(main())
