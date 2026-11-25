#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mm_run.py —— 一次跑完：案例输入 → 句子块 → 草稿导图 → 校验 → 四种产物 → result.json。

这是给 Agent 用的编排入口，也是"没有 Agent 时"的兜底：平台若只把脚本跑一遍，
也能得到一份结构完整、每条都挂原文的导图，只是语义质量停在单次抽句的水平。
Agent 加载 SKILL.md 后应该做的是**在草稿上改**，而不是从零写。

用法：
    python3 mm_run.py --case /input/case.json --work /app/work --out /app/output
    python3 mm_run.py --material material.md --work work --out output --case-id demo

产物（--out 目录）：
    mindmap.mm / .opml / .md / .svg    可编辑导图 + 矢量预览
    result.json                        平台契约字段 + 主结果 + 证据 + 不确定
    check.md / check.json              自查报告
    blocks.json / blocks.md            句子块底账（供复核）
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

CAUSE = re.compile(r"因此|因而|导致|使得|because|thus|therefore|lead(?:s)? to|result(?:s)? in", re.I)
CONTRAST = re.compile(r"相比|而|但|然而|versus|vs\.?|whereas|while|however|in contrast", re.I)
CITE = re.compile(r"\[\d{1,3}(?:[-,]\d{1,3})*\]|\(\s*[A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?,?\s*\d{4}\s*\)")
DEPEND = re.compile(r"基于|依赖|前提|需要先|on the basis of|depend(?:s)? on|requires?|after", re.I)
CONFLICT = re.compile(r"不一致|矛盾|与.{0,12}相反|contradict|inconsistent|disagree", re.I)
NUM = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|°C|℃|MPa|kPa|GPa|nm|μm|µm|mm|cm|mL|mg|g|h|min|s)\b", re.I)

STOP_HEAD = re.compile(
    r"^(?:in this (?:study|work|paper)|here|we (?:report|show|present)|"
    r"如图\s*\d+\s*所示[，,]?|如图[，,]?|如表\s*\d+\s*所示[，,]?|"
    r"表\s*\d+\s*(?:给出|列出|显示)[了]?[，,]?|"
    r"it (?:is|was) (?:found|observed|shown) that|"
    r"the results? (?:show|showed|indicate|suggest)(?: that)?)", re.I)

# 兜底建图用：每类最多取几句，避免某个类型把图塞满
CAP = {"question": 3, "method": 6, "evidence": 6, "conclusion": 6, "limitation": 4, "task": 4}
TYPE_CN = {"question": "研究问题", "method": "方法", "evidence": "证据",
           "conclusion": "结论", "limitation": "局限", "task": "任务"}


def sh(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)


def find_material(case_path, case, explicit):
    """按 显式参数 → case 里的路径字段 → 同目录常见文件名 的顺序找材料。"""
    if explicit and os.path.isfile(explicit):
        return explicit
    cands = []

    def dig(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and re.search(r"\.(md|txt|markdown)$", v, re.I):
                    cands.append(v)
                else:
                    dig(v)
        elif isinstance(obj, list):
            for v in obj:
                dig(v)

    dig(case)
    base = os.path.dirname(os.path.abspath(case_path or "."))
    for c in cands:
        for p in (c, os.path.join(base, c), os.path.join("/input", c)):
            if os.path.isfile(p):
                return p
    for name in ("material.md", "materials.md", "paper.md", "input.md", "case.md",
                 "material.txt", "paper.txt"):
        for p in (os.path.join(base, name), os.path.join("/input", name)):
            if os.path.isfile(p):
                return p
    # 目录里唯一的 md/txt
    for d in (base, "/input"):
        if os.path.isdir(d):
            hits = [os.path.join(d, f) for f in sorted(os.listdir(d))
                    if f.lower().endswith((".md", ".txt"))]
            if len(hits) == 1:
                return hits[0]
    return None


def try_pdf(case_path, case, work):
    """材料只有 PDF 时，尝试平台提供的 pdf-text-tool；失败则如实返回 None。"""
    pdfs = []

    def dig(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                dig(v)
        elif isinstance(obj, list):
            for v in obj:
                dig(v)
        elif isinstance(obj, str) and obj.lower().endswith(".pdf"):
            pdfs.append(obj)

    dig(case)
    for p in pdfs:
        for q in (p, os.path.join("/input", p), os.path.join(os.path.dirname(case_path or ""), p)):
            if os.path.isfile(q):
                out = os.path.join(work, "pdf_text.md")
                for cmd in ("pdf-text-tool \"%s\" -o \"%s\"" % (q, out),
                            "python3 -m pdftext \"%s\" \"%s\"" % (q, out),
                            "pdftotext -layout \"%s\" \"%s\"" % (q, out)):
                    rc, log = sh(cmd)
                    if rc == 0 and os.path.isfile(out) and os.path.getsize(out) > 200:
                        return out
                return None
    return None


def clean_head(s):
    s = STOP_HEAD.sub("", s or "").strip()
    s = re.sub(r"^(?:首先|其次|最后|另外|此外|同时|并且|而且|然后)[，,]?", "", s)
    s = s.strip("　 \t")
    s = re.sub(r"[。．.；;，,：:]+$", "", s)
    return s


# 句子开头的连接词：留着当标题等于没写（"However"/"此外"/"Finally"）
LEAD_CONN = re.compile(
    r"^(?:and|but|however|therefore|thus|moreover|furthermore|additionally|finally|"
    r"in contrast|nevertheless|meanwhile|also|so|then|instead|indeed|"
    r"此外|同时|然而|但是|因此|所以|另外|最后|首先|其次|综上|从而|并且|而且|"
    r"不过|相反|值得注意的是|需要指出的是|总的来说|总体上)[，,\s]*", re.I)

# 标题里不该出现的开头虚词
LEAD_FUNC = re.compile(r"^(?:的|了|在|和|与|及|或|为|是|有|对|由|从|被|把|将|该|其|这|那)+")
TAIL_FUNC = re.compile(r"(?:的|了|和|与|及|或|为|是|在|对|由|从|被|把|将|该|其|这|那)+$")


def core_phrase(s, limit=34):
    """从句子里取一段能当节点名的核心短语。

    整句搬上去会变成"however, the results show that..."这类不可读节点；
    只取关键词又会丢条件。折中是按标点切段、剥掉开头连接词，
    取第一个够长的实义片段（英文常见的"main clause + 从句"结构正好适用）。
    """
    t = clean_head(s)
    # 不在 / 和 · 上切：会把 "1.2 mol/L" "0.8 Ω·cm²" 这类单位切碎
    # 不按英文句点切：会把 1.2、0.8 切成 1 和 2
    parts = [x.strip() for x in re.split(r"[，,；;。．：:、（）()\[\]【】|]+", t) if x.strip()]
    best = ""
    for p in parts:
        p = LEAD_CONN.sub("", p).strip()
        p = LEAD_FUNC.sub("", p).strip()
        p = TAIL_FUNC.sub("", p).strip()
        if len(p) < 6:
            continue
        if len(p) >= 10:
            best = p
            break
        if len(p) > len(best):
            best = p
    # "The relative density, which was..." 这类被逗号切断会只剩半边，
    # 首段以冠词/指示词开头且不足 20 字时补上下一段
    if best and len(best) < 20 and re.match(r"^(?:the|a|an|this|these|those|其|该|此)\b", best, re.I):
        for p2 in parts[1:]:
            p2 = LEAD_CONN.sub("", p2).strip()
            if len(p2) >= 4:
                best = (best.rstrip("，,") + "，" + p2)[: limit + 1]
                break

    if not best:
        best = LEAD_CONN.sub("", t).strip()
    if len(best) > limit:
        best = best[:limit] + "…"
    return best


def make_title(s, limit=34):
    return core_phrase(s, limit)


def draft_nodes(blocks, case_id):
    """兜底建图：按句式线索分桶，每桶取前几句，挂原文块号。"""
    # 表格行不做节点标题：单元格里的数字和竖线会污染标题，表格留给正文引用
    pool = [b for b in blocks if not b["noise"] and not b["heading"] and not b.get("table")]
    buckets = {t: [] for t in CAP}
    for b in pool:
        for h in b["hints"]:
            if h in buckets:
                if len(buckets[h]) < CAP[h]:
                    buckets[h].append(b)
                break
    # 一类都没有时，用长句补位，保证图不是空的
    if not any(buckets.values()):
        for b in sorted(pool, key=lambda x: -x["chars"])[:10]:
            buckets["conclusion"].append(b)
    # 问题类：只认显式问句或明写的缺口句。都没有就不建这一支——
    # 从开篇句硬凑一个"研究问题"是造假，宁可如实标材料不足。
    if not buckets["question"]:
        for b in pool[:80]:
            if re.search(r"[？?]", b["text"]):
                buckets["question"].append(b)
                break
        if not buckets["question"]:
            for b in pool[:80]:
                if re.search(r"不清楚|未解决|空白|缺乏|unclear|unknown|knowledge gap|"
                             r"remains? to be|has not been", b["text"], re.I):
                    buckets["question"].append(b)
                    break
    no_question = not buckets["question"]

    head = next((b["text"] for b in blocks if b.get("heading")), "")
    head = re.sub(r"^#{1,6}\s+", "", head).strip()
    root_title = (head[:34] + "…") if len(head) > 34 else (head or "材料主题（待按案例任务改写）")
    nodes = [{"id": "n0", "parent": None, "title": root_title,
              "type": "root", "evidence": [pool[0]["id"]] if pool else [],
              "level": "summary", "note": ""}]
    rels = []
    idx = 0
    prev_by_branch = {}
    for t in ("question", "method", "evidence", "conclusion", "limitation", "task"):
        items = buckets.get(t) or []
        if not items:
            continue
        idx += 1
        bid = "n%d" % idx
        nodes.append({"id": bid, "parent": "n0", "title": "%s（%d 条）" % (TYPE_CN[t], len(items)),
                      "type": t, "evidence": [items[0]["id"]], "level": "summary",
                      "note": "由句式线索自动归并，需按案例任务核对"})
        seen = set()
        for b in items:
            title = make_title(b["text"])
            if len(title) < 10 and not NUM.search(b["text"]):
                continue
            key = title[:12]
            if key in seen:
                continue
            seen.add(key)
            idx += 1
            nid = "n%d" % idx
            level = "fact" if (NUM.search(b["text"]) or CITE.search(b["text"])) else "summary"
            nodes.append({"id": nid, "parent": bid, "title": title, "type": t,
                          "evidence": [b["id"]], "level": level, "note": ""})
            # 关系：同段相邻 → 支撑；因果/对比/引用词 → 对应关系类型
            prev = prev_by_branch.get(t)
            if prev:
                kind = "support"
                if CAUSE.search(b["text"]):
                    kind = "cause"
                elif CONTRAST.search(b["text"]):
                    kind = "contrast"
                elif CONFLICT.search(b["text"]):
                    kind = "conflict"
                elif DEPEND.search(b["text"]):
                    kind = "depend"
                elif CITE.search(b["text"]):
                    kind = "cite"
                rels.append({"from": prev, "to": nid, "kind": kind,
                             "evidence": [b["id"]], "why": "同分支相邻句，按句内连接词定类型"})
            prev_by_branch[t] = nid

    # 关系太少时补"证据支撑结论"：这是图上唯一必须存在的跨支关系
    if len(rels) < 3:
        def first(tp):
            return next((n for n in nodes if n["type"] == tp and n["parent"] != "n0"), None)

        ev, cc, mm2, qq = first("evidence"), first("conclusion"), first("method"), first("question")
        cands = [(ev, cc, "support", "证据支撑结论"),
                 (mm2, ev, "depend", "证据由该方法产出"),
                 (qq, cc, "depend", "结论回应问题")]
        for a, b, kind, why in cands:
            if len(rels) >= 3:
                break
            if not a or not b or a["id"] == b["id"]:
                continue
            if any(r["from"] == a["id"] and r["to"] == b["id"] for r in rels):
                continue
            w = (a.get("evidence") or [None])[0]
            rels.append({"from": a["id"], "to": b["id"], "kind": kind,
                         "evidence": [w] if w else [], "why": why + "（兜底补链）"})

    uncertainty = []
    for n in nodes:
        if n["level"] == "summary" and n["type"] in ("evidence", "conclusion"):
            uncertainty.append({"node": n["id"],
                                "why": "该节点来自单句概括，未与同指标的其它段落交叉核对",
                                "needs": "回原文确认条件（温度/压力/样品/标准）"})
            if len(uncertainty) >= 5:
                break
    if no_question:
        uncertainty.insert(0, {
            "node": "n0",
            "why": "材料没有显式陈述研究问题的句子（无问句、无明写的缺口），"
                   "导图未设「研究问题」分支，避免把开篇句硬当问题",
            "needs": "按案例任务补一条可检验的问题（含指标、阈值与对照），再挂回引言缺口句"})
    return {"case_id": case_id, "title": "", "nodes": nodes, "relations": rels,
            "uncertainty": uncertainty}


def contract_keys(case):
    oc = None
    for k in ("output_contract", "output_contracts", "outputs", "deliverables"):
        if isinstance(case, dict) and case.get(k):
            oc = case[k]
            break
    keys = []
    if isinstance(oc, dict):
        keys = list(oc.keys())
    elif isinstance(oc, list):
        for x in oc:
            if isinstance(x, str):
                keys.append(x)
            elif isinstance(x, dict):
                keys.append(x.get("field") or x.get("name") or x.get("id"))
    return [k for k in keys if isinstance(k, str) and k]


def build_result(case, case_id, outdir, check, blocks, doc):
    files = sorted([f for f in os.listdir(outdir)
                    if f.startswith("mindmap.") and not f.endswith(".tmp")])
    n_nodes = len(doc["nodes"])
    ev_nodes = [n for n in doc["nodes"] if n.get("evidence")]
    cov = round(len(ev_nodes) / max(1, n_nodes), 3)
    main = {
        "case_id": case_id,
        "mindmap_files": files,
        "node_count": n_nodes,
        "relation_count": len(doc.get("relations") or []),
        "evidence_coverage": cov,
        "struct_score": check.get("struct_score"),
        "checks_passed": "%d/%d" % (check.get("passed", 0), check.get("total", 0)),
        "block_count": len(blocks),
    }
    result = dict(main)
    # 平台给的契约字段：能填的填，填不了的如实说明，不伪造
    for k in contract_keys(case):
        if k in result:
            continue
        kl = k.lower()
        if "mindmap" in kl or "diagram" in kl or "file" in kl:
            result[k] = files
        elif "node" in kl or "count" in kl:
            result[k] = n_nodes
        elif "evidence" in kl or "source" in kl or "trace" in kl:
            result[k] = [{"node": n["id"], "blocks": n.get("evidence") or []}
                         for n in doc["nodes"] if n.get("evidence")][:80]
        elif "uncertain" in kl or "risk" in kl:
            result[k] = doc.get("uncertainty") or []
        elif "status" in kl:
            result[k] = "partial" if check.get("passed") != check.get("total") else "ok"
        else:
            result[k] = ("见 mindmap.md 与 blocks.json；该字段由平台契约动态给出，"
                         "未按未知语义硬填")
    result.update({
        "status": "partial" if check.get("passed") != check.get("total") else "ok",
        "sources": {"blocks": "blocks.json", "check": "check.md",
                    "mindmap": files},
        "uncertainty": doc.get("uncertainty") or [],
        "change_records": [{"what": "由 blocks 自动建草稿",
                            "why": "先有可核对的结构，再让 Agent 补语义",
                            "limitation": "自动标题未做术语归并"}],
    })
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="", help="/input/case.json")
    ap.add_argument("--material", default="", help="直接指定材料文件")
    ap.add_argument("--work", default="work")
    ap.add_argument("--out", default="output")
    ap.add_argument("--case-id", default="")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    case = {}
    if args.case and os.path.isfile(args.case):
        try:
            case = json.load(open(args.case, encoding="utf-8"))
        except Exception as e:
            print("case.json 读不了：%s（继续用默认流程）" % e)
    case_id = args.case_id or (case.get("case_id") if isinstance(case, dict) else "") or "case"

    mat = find_material(args.case, case, args.material)
    if not mat:
        mat = try_pdf(args.case, case, args.work)
    if not mat:
        print("找不到可读材料（.md/.txt/.pdf）。请先抽取 PDF 文本，或把材料路径写进 case.json。",
              file=sys.stderr)
        # 仍然产出可辨识的 partial，不让流程整段失败
        json.dump({"case_id": case_id, "status": "blocked",
                   "reason": "no_readable_material",
                   "next": "用 pdf-text-tool 抽出带页码的 Markdown 后重跑"},
                  open(os.path.join(args.out, "result.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return 3

    print("材料：%s" % mat)
    rc, log = sh('python3 "%s" --in "%s" --out "%s" --title "%s"'
                 % (os.path.join(HERE, "mm_scaffold.py"), mat, args.work, args.title))
    print(log.strip().splitlines()[0] if log.strip() else "")
    if rc != 0:
        print(log, file=sys.stderr)
        return rc

    blocks = json.load(open(os.path.join(args.work, "blocks.json"), encoding="utf-8"))
    doc = draft_nodes(blocks, case_id)
    doc["title"] = args.title or (case.get("title") if isinstance(case, dict) else "") or ""
    nodes_path = os.path.join(args.work, "nodes.json")
    json.dump(doc, open(nodes_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sh('python3 "%s" --blocks "%s" --nodes "%s" --out "%s"'
       % (os.path.join(HERE, "mm_check.py"), os.path.join(args.work, "blocks.json"),
          nodes_path, os.path.join(args.work, "check")))
    check = json.load(open(os.path.join(args.work, "check.json"), encoding="utf-8"))

    sh('python3 "%s" --nodes "%s" --blocks "%s" --out "%s" --title "%s"'
       % (os.path.join(HERE, "mm_export.py"), nodes_path,
          os.path.join(args.work, "blocks.json"), os.path.join(args.out, "mindmap"),
          doc["title"]))

    result = build_result(case, case_id, args.out, check, blocks, doc)
    json.dump(result, open(os.path.join(args.out, "result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 把底账和自查报告一起放进输出目录，评审能顺着查
    for fn in ("blocks.json", "blocks.md", "check.md", "check.json", "nodes.json"):
        src = os.path.join(args.work, fn)
        if os.path.isfile(src):
            dst = os.path.join(args.out, fn)
            open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read())

    print("完成：%d 节点 / %d 关系 / 结构分 %s / 证据覆盖 %.0f%%"
          % (result["node_count"], result["relation_count"],
             result["struct_score"], result["evidence_coverage"] * 100))
    print("产物目录：%s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
