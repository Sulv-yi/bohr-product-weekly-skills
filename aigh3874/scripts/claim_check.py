#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claim_check.py — 把论文结论逐条钉回原文条件的核对器（仅标准库）。

背景：AI 读完论文给出的"结论串"（2 μm、0.2–0.28、优于原生料、减重 40%）通常丢了
三样东西——条件、口径、对照臂。人工逐条回车核对容易漏，所以把能机械判定的部分写成检查。

两类输入
  evidence/claims.csv  我的读后结论：一条一个命题 + 引文 + 声明页码
  evidence/corpus.csv  证据句底账：正文里能承载该指标的句子，标明料名与页码

检查项（每条 claim）
  B 绑定   引文归一化后在正文逐字存在，且落在我声明的页码
  V 数值   claim 里的每个数值都出现在它自己的引文里
  P 口径   metric 的规范表述与引文用词一致（relative density ≠ weight ≠ density）
  C 覆盖   底账里同料名同指标的数值，是否都落在 claim 声明的区间内
  U 可核   含 first/only 类断言 → 标记需检索依据，不作为已证结论

底账自身也会被校验：每条 corpus 引文必须逐字命中原文，页码必须对。
底账错了，C 项的结论就没有意义。

用法
  python3 scripts/claim_check.py --paper materials/paper.md \
      --claims evidence/claims.csv --corpus evidence/corpus.csv --out-prefix evidence/check
退出码：存在 FAIL / CONFLICT / 底账错误时返回 1
"""
import argparse
import csv
import os
import re
import sys
import unicodedata

LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
NOISE = [
    (re.compile("\u00ad"), ""),                              # soft hyphen
    (re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]"), ""),  # 抽取残留
    (re.compile("◦"), "°"),
    (re.compile("[‐‑‒–—]"), "-"),
    (re.compile("[‘’]"), "'"),
    (re.compile("[“”]"), '"'),
]


def norm(s):
    """压成可逐字比对的形式：接回断词、折叠空白、统一符号、转小写。"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    s = s.replace("\x02", "\u00ad")            # 行末断词的残留
    s = re.sub(r"(\w)\u00ad\s*(\w)", r"\1\2", s)
    for pat, rep in NOISE:
        s = pat.sub(rep, s)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)")


def nums(s):
    return NUM_RE.findall(norm(s))


def floats(s):
    out = []
    for t in nums(s):
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- 正文与页码

def load_paper(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    segs = re.split(r"<!--\s*page\s+(\d+)\s*-->", raw)
    pages = [(1, segs[0])] if segs[0].strip() else []
    for i in range(1, len(segs), 2):
        pages.append((int(segs[i]), segs[i + 1]))
    return [(p, norm(t)) for p, t in pages]


def find_page(pages, needle):
    for p, text in pages:
        if needle and needle in text:
            return p
    return None


# ---------------------------------------------------------------- 口径词表

CANON = {
    "relative_density": ("relative density",
                         ["relative density", "relative densities", "ρr"]),
    "cell_size": ("cell size", ["cell size", "cell sizes", "mean cell size"]),
    "mfi": ("MFI", ["mfi", "melt flow index"]),
    "density_reduction": ("relative density",
                          ["reduction", "reduced by", "density reduction"]),
}

DRIFT = {
    "relative_density": ["weight reduction", "weight reductions", "mass loss"],
    "density_reduction": ["weight reduction", "weight reductions", "mass loss"],
}

UNVERIFIABLE = re.compile(
    r"\b(first time|for the first|only report|unprecedented|never been|no previous)\b"
    r"|首次|首创|唯一|未见报道|尚无报道|国际领先",
    re.I,
)


# ---------------------------------------------------------------- 检查

def check_claim(c, pages, corpus):
    nq = norm(c["quote"])
    page = c["page"].strip()
    found = find_page(pages, nq) if nq else None
    bind = "ok" if found else "MISS"
    page_ok = "ok" if str(found) == page else "MISMATCH(p%s)" % found

    vn = nums(c["value"])
    qn = set(nums(c["quote"]))
    missing = [t for t in vn if t not in qn]
    value_ok = "ok" if not missing else "MISS:" + ",".join(missing)

    metric = c["metric"].strip()
    if metric == "none":
        unit_ok = "skip"
    else:
        canon, syn = CANON.get(metric, (metric, [metric]))
        unit_ok = "ok"
        if not any(w in nq for w in syn):
            unit_ok = "NO-ANCHOR(%s)" % canon
        for bad in DRIFT.get(metric, []):
            if bad in nq and canon not in nq:
                unit_ok = "DRIFT(%s)" % bad

    # 覆盖：底账里同料名同指标的数值必须落在 claim 区间内
    lo_hi = floats(c["value"])
    rows = [r for r in corpus
            if r["subject"].strip() == c["subject"].strip() and r["metric"].strip() == metric]
    outside, seen = [], []
    for r in rows:
        for v in floats(r["value"]):
            seen.append(v)
            if lo_hi and not (min(lo_hi) - 0.005 <= v <= max(lo_hi) + 0.005):
                outside.append("%g" % v)
    outside = sorted(set(outside), key=float)
    if metric == "none" or not rows:
        consist = "no-corpus"
    elif outside:
        consist = "out-of-range:" + ",".join(outside)
    else:
        consist = "ok"

    unver = "flag" if UNVERIFIABLE.search(c["claim"] + " " + c["quote"]) else ""

    verdict = "PASS"
    if bind != "ok" or value_ok != "ok" or unit_ok not in ("ok", "skip"):
        verdict = "FAIL"
    elif consist.startswith("out-of-range"):
        verdict = "CONFLICT"

    note = []
    if outside:
        note.append("底账内同料名数值 %s 越出声明区间 %s"
                    % (",".join(outside), c["value"]))
    if unver:
        note.append("含 first/only 类断言，需检索依据")
    if seen and consist == "ok":
        note.append("底账覆盖 %s" % ",".join("%g" % v for v in sorted(set(seen))))

    return {
        "claim_id": c["claim_id"].strip(),
        "subject": c["subject"].strip(),
        "metric": metric,
        "value": c["value"].strip(),
        "page": page,
        "bind": bind,
        "page_ok": page_ok,
        "value_ok": value_ok,
        "unit_ok": unit_ok,
        "consist": consist,
        "unverifiable": unver,
        "verdict": verdict,
        "note": " | ".join(note),
    }


def check_corpus(corpus, pages):
    bad = []
    for i, r in enumerate(corpus, 1):
        nq = norm(r["quote"])
        found = find_page(pages, nq) if nq else None
        if not found:
            bad.append("corpus 第 %d 行（%s / %s）引文未逐字命中"
                       % (i, r["subject"], r["metric"]))
        elif str(found) != r["page"].strip():
            bad.append("corpus 第 %d 行页码不符：声明 p%s，实际 p%s（%s / %s）"
                       % (i, r["page"], found, r["subject"], r["metric"]))
    return bad


def write_out(results, bad_corpus, prefix):
    d = os.path.dirname(prefix)
    if d:
        os.makedirs(d, exist_ok=True)
    cols = ["claim_id", "subject", "metric", "value", "page", "bind", "page_ok",
            "value_ok", "unit_ok", "consist", "unverifiable", "verdict", "note"]
    with open(prefix + ".csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)

    fail = [r for r in results if r["verdict"] == "FAIL"]
    conf = [r for r in results if r["verdict"] == "CONFLICT"]
    ok = [r for r in results if r["verdict"] == "PASS"]

    out = ["# 结论核对报告", ""]
    out.append("- 结论条数：%d" % len(results))
    out.append("- PASS：%d" % len(ok))
    out.append("- FAIL（引文/数值/口径对不上）：%d —— %s"
               % (len(fail), ", ".join(r["claim_id"] for r in fail) or "无"))
    out.append("- CONFLICT（底账里有越出声明区间的数值）：%d —— %s"
               % (len(conf), ", ".join(r["claim_id"] for r in conf) or "无"))
    out.append("- 底账错误：%d" % len(bad_corpus))
    for b in bad_corpus:
        out.append("  - %s" % b)
    out += ["", "## 需要处理的条目", ""]
    anybad = False
    for r in results:
        if r["verdict"] == "PASS" and not r["unverifiable"]:
            continue
        anybad = True
        out.append("### %s · %s%s" % (
            r["claim_id"], r["verdict"], "（不可核验断言）" if r["unverifiable"] else ""))
        out.append("- 命题：%s / %s = %s（声明 p%s）" % (
            r["subject"], r["metric"], r["value"] or "—", r["page"]))
        out.append("- 绑定 %s；页码 %s；数值 %s；口径 %s"
                   % (r["bind"], r["page_ok"], r["value_ok"], r["unit_ok"]))
        out.append("- 覆盖：%s" % r["consist"])
        if r["note"]:
            out.append("- 备注：%s" % r["note"])
        out.append("")
    if not anybad:
        out.append("全部条目通过。")
    with open(prefix + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return len(fail) + len(conf) + len(bad_corpus)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out-prefix", default="evidence/check")
    a = ap.parse_args()

    pages = load_paper(a.paper)
    with open(a.claims, encoding="utf-8-sig", newline="") as f:
        claims = list(csv.DictReader(f))
    with open(a.corpus, encoding="utf-8-sig", newline="") as f:
        corpus = list(csv.DictReader(f))

    bad_corpus = check_corpus(corpus, pages)
    results = [check_claim(c, pages, corpus) for c in claims]
    bad = write_out(results, bad_corpus, a.out_prefix)

    for r in results:
        print("%4s  %-8s %-18s %-14s p%-3s %s" % (
            r["claim_id"], r["verdict"], r["metric"], r["value"] or "-",
            r["page"], r["consist"]))
    print("\n%d 条 claim，底账 %d 行；需处理 %d 项；报告 %s.md"
          % (len(results), len(corpus), bad, a.out_prefix))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
