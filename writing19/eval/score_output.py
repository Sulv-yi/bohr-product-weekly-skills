#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""score_output.py —— 对任意 nodes.json 复算结构分，并按五维给可核查的提示。

它不冒充平台评分，只做一件事：把「这个产物有没有硬伤」量化成 0–100，
再按五维映射成一张对照表，让评审知道每一分对应哪个可查的事实。

用法：
    python3 eval/score_output.py --blocks work/blocks.json --nodes work/nodes.json
    python3 eval/score_output.py --blocks work/blocks.json --nodes examples/handcrafted-nodes.json --json
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "..", "scripts", "mm_check.py")


def run_check(blocks, nodes, tmp):
    cmd = [sys.executable, CHECK, "--blocks", blocks, "--nodes", nodes, "--out", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    path = tmp + ".json"
    data = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else {}
    return data, r.returncode


def detail(doc):
    nodes = [n for n in doc.get("nodes") or [] if n.get("type") != "root"]
    bad_head = re.compile(
        r"^(?:and|but|however|therefore|thus|moreover|furthermore|additionally|finally|"
        r"in contrast|nevertheless|meanwhile|also|so|then|instead|despite|while|as |"
        r"it |this |these |which |该|此|其|因此|此外|然而)", re.I)
    n_bad = sum(1 for n in nodes if bad_head.match(n.get("title") or ""))
    n_frag = sum(1 for n in nodes if len(n.get("title") or "") < 10)
    kinds = {r.get("kind") for r in doc.get("relations") or []}
    lens = [len(n.get("title") or "") for n in nodes]
    mean = sum(lens) / len(lens) if lens else 0
    cv = ((sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5 / mean) if mean else 0
    return {"nodes": len(nodes), "relations": len(doc.get("relations") or []),
            "kind_types": len(kinds), "bad_head": n_bad, "fragments": n_frag,
            "title_cv": round(cv, 3),
            "uncertainty": len(doc.get("uncertainty") or [])}


def five_dim(check, det):
    """把结构事实映射到五维的提示分，只用于自查排序，不等于平台评分。"""
    ok = check.get("passed", 0)
    total = check.get("total", 10)
    base = ok / total if total else 0
    struct = check.get("struct_score", 0)

    readable = 1.0 if det["bad_head"] == 0 else max(0.0, 1 - det["bad_head"] / max(1, det["nodes"]))
    return {
        "实际效果": round(40 * (0.7 * base + 0.3 * readable), 1),
        "使用增益": round(25 * (0.6 * readable + 0.4 * min(1, det["kind_types"] / 4)), 1),
        "创新增益": round(15 * (0.5 * base + 0.5 * min(1, det["kind_types"] / 5)), 1),
        "可靠体验": round(10 * base, 1),
        "生态贡献": round(10 * (0.5 * base + 0.5 * min(1, det["uncertainty"] / 3)), 1),
        "_struct_score": struct,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True)
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tmp = os.path.join(os.path.dirname(os.path.abspath(args.nodes)), "_score_tmp")
    check, rc = run_check(args.blocks, args.nodes, tmp)
    if not check:
        print("校验器没产出结果，检查路径：%s" % CHECK, file=sys.stderr)
        return 2
    det = detail(json.load(open(args.nodes, encoding="utf-8")))
    dims = five_dim(check, det)
    payload = {"check": {k: check.get(k) for k in ("passed", "total", "struct_score",
                                                   "issue_count")},
               "detail": det, "hint": dims}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0 if rc == 0 else 1

    print("结构分 %s/100（%d/%d 项通过）" % (check.get("struct_score"),
                                          check.get("passed"), check.get("total")))
    print("节点 %d、关系 %d（%d 类）、连接词开头 %d、碎片 %d、标题 CV %.2f、待确认 %d"
          % (det["nodes"], det["relations"], det["kind_types"], det["bad_head"],
             det["fragments"], det["title_cv"], det["uncertainty"]))
    print("\n五维结构余量（满分 = 结构上无硬伤，不代表内容得分）：")
    for k, v in dims.items():
        if k.startswith("_"):
            continue
        print("  %-6s %5.1f" % (k, v))
    print("\n余量由结构事实换算：通过项比例、连接词开头数、关系类型数、待确认条数。")
    print("要让某一维真的上去，改的是产物本身，不是这张表。")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
