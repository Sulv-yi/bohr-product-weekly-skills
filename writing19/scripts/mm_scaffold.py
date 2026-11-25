#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mm_scaffold.py —— 把科研材料切成带定位号的句子块。

导图出问题的第一因不是"排得不好看"，而是"引不回原文"：节点写了、证据丢了。
这个脚本只做一件事：给材料里每一句一个稳定编号（P3-S2），后续所有节点和
关系都必须挂在这个编号上，挂不上就说明是模型自己加的。

用法：
    python3 mm_scaffold.py --in material.md --out work/
    python3 mm_scaffold.py --in material.md --out work/ --title "论文主题"

输入：
    - 带 <!-- page N --> 锚点的 Markdown（pdf-text-tool 的常见输出）
    - 纯文本（无页码，page 记为 0，并在统计里标 pages_missing）
    - 单页超长（>12000 字）会被按句子边界二次切块，避免一块塞满

输出：
    work/blocks.json   [{id, page, para, text, chars, noise, hints:[...]}]
    work/blocks.md     人工核对用的可读清单
    work/scaffold_stats.json
"""
import argparse
import json
import os
import re
import statistics
import sys

PAGE_RE = re.compile(r"<!--\s*page\s*(\d+)\s*-->", re.I)

# 句末切分：中文句号/问号/叹号后直接切；英文句号后要求跟空白+大写/数字/括号，
# 避免把 0.35、et al.、i.e. 切碎。
SENT_RE = re.compile(r"(?<=[。！？；])|(?<=[.!?])\s+(?=[A-Z0-9(（\"'“])")

# 章节标题：Markdown 标题，或“1 引言 / 2.1 方法 / Results”这类编号行
HEAD_RE = re.compile(
    r"^(#{1,6}\s+.+|(?:\d+(?:\.\d+)*)[.、]?\s+[^\n]{2,40}|"
    r"(?:Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References|"
    r"Acknowledg\w*|摘要|引言|前言|方法|结果|讨论|结论|参考文献|致谢)\s*[:：]?)$",
    re.I,
)

# 噪声：页码行、纯数字、页眉页脚常见串、参考文献条目
NOISE_RES = [
    re.compile(r"^\s*<!--.*$"),                 # 抽取残留的注释/页眉
    re.compile(r"^\s*\d{1,4}\s*$"),
    re.compile(r"^\s*(?:page|p\.)\s*\d+\s*(?:of\s*\d+)?\s*$", re.I),
    re.compile(r"^\s*(?:https?://|www\.)\S+\s*$", re.I),
    re.compile(r"^\s*\[\d{1,3}(?:[-,]\d{1,3})*\]\s*$"),
    # 过渡句：上下文衔接用，不承载可上图的结论
    re.compile(r"^(?:as (?:previously|mentioned|discussed|shown|said)|"
               r"it is (?:important|worth|necessary) to (?:highlight|note|mention)|"
               r"in the following|see (?:below|above|section)|"
               r"如(?:前|上)所述|详见(?:下文|上文)|值得一提的是|需要指出的是)", re.I),
]

# 句子类型提示：只给线索（hints），不做判定。判定交给 Agent，
# 因为同一句话在不同材料里角色不同（"采用 A 方法"在方法节是方法，在引言里是背景）。
HINT_PATTERNS = [
    ("question", re.compile(
        r"研究问题|旨在|拟解决|是否|有待回答|尚不清楚|仍不清楚|"
        r"障碍|瓶颈|挑战|制约|限制因素|challenge|obstacle|bottleneck|"
        r"hypothes[ie]s|we ask|aim of|objective|本文(?:探究|考察|回答)|"
        r"this (?:study|work) (?:asks|investigat|examin|address)|"
        r"we (?:investigat|examin|address|explore|seek|test)|"
        r"remains? (?:unclear|unknown|open)|open question|knowledge gap|"
        r"如何(?:提高|降低|表征|实现|选择)|why |how (?:to|does|do) ", re.I)),
    ("method", re.compile(
        r"采用|使用|通过|基于|制备|测试|表征|试样|仪器|本文用|溶于|配制|组装|"
        r"处理|合成|退火|干燥|protocol|we (?:used|applied|performed|measured|"
        r"prepared)|method|synthes|characteri[sz]", re.I)),
    ("evidence", re.compile(
        r"Fig(?:ure)?\.?\s*\d|Table\s*\d|图\s*\d|表\s*\d|"
        r"\d+(?:\.\d+)?\s*(?:%|°C|℃|MPa|kPa|GPa|nm|μm|µm|mm|cm|mL|mg|g/L|h|min|s)\b", re.I)),
    ("conclusion", re.compile(
        r"表明|说明|因此|可见|证明|揭示|提出|据此|机制|归因|认为|推断|"
        r"indicate|suggest|demonstrat|reveal|conclu|consistent with|"
        r"in line with|confirm|attribute|propose", re.I)),
    ("limitation", re.compile(
        r"局限|不足|未能|仅在|尚需|有待|further (?:work|study)|limited to|"
        r"caveat|however,? (?:the|this) (?:study|work)|do(?:es)? not", re.I)),
    ("task", re.compile(
        r"需要|计划|下一步|应(?:当|该)|目标|待办|milestone|next step|should|must|"
        r"we (?:will|plan)|remaining", re.I)),
]


def split_pages(text):
    """按 <!-- page N --> 切页；无锚点时整篇算第 0 页。"""
    marks = list(PAGE_RE.finditer(text))
    if not marks:
        return [(0, text)]
    pages = []
    if marks[0].start() > 0:
        head = text[: marks[0].start()]
        if head.strip():
            pages.append((0, head))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        pages.append((int(m.group(1)), text[m.end():end]))
    return pages


def split_paras(page_text):
    """按空行切段；单段超长再按句切，避免一段几万字。"""
    raw = re.split(r"\n\s*\n", page_text)
    out = []
    for p in raw:
        p = p.strip()
        if not p:
            continue
        if len(p) <= 12000:
            out.append(p)
        else:
            buf = ""
            for s in SENT_RE.split(p):
                if not s:
                    continue
                if len(buf) + len(s) > 4000 and buf:
                    out.append(buf)
                    buf = s
                else:
                    buf += s
            if buf:
                out.append(buf)
    return out


def split_sents(para):
    parts = [x.strip() for x in SENT_RE.split(para) if x and x.strip()]
    return parts or [para.strip()]


def is_noise(sent):
    return any(r.match(sent) for r in NOISE_RES)


def hints_of(sent):
    return [name for name, rx in HINT_PATTERNS if rx.search(sent)]


def is_heading(sent):
    t = sent.strip()
    if re.match(r"^#{1,6}\s+\S", t):
        return True
    return bool(HEAD_RE.match(t)) and len(t) <= 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="材料文件（.md/.txt）")
    ap.add_argument("--out", dest="out", default="work", help="输出目录")
    ap.add_argument("--title", default="", help="材料标题（用于根节点建议）")
    args = ap.parse_args()

    if not os.path.isfile(args.inp):
        print("找不到输入文件：%s" % args.inp, file=sys.stderr)
        return 2
    text = open(args.inp, encoding="utf-8", errors="replace").read()
    os.makedirs(args.out, exist_ok=True)

    blocks = []
    counters = {}
    pages = split_pages(text)
    for page, ptext in pages:
        for pi, para in enumerate(split_paras(ptext), 1):
            for si, sent in enumerate(split_sents(para), 1):
                s = re.sub(r"\s+", " ", sent).strip()
                if not s:
                    continue
                counters[page] = counters.get(page, 0) + 1
                blocks.append({
                    "id": "P%d-S%d" % (page, counters[page]),
                    "page": page,
                    "para": pi,
                    "text": s,
                    "chars": len(s),
                    "noise": is_noise(s),
                    "heading": is_heading(s),
                    "table": bool(re.search(r"\S\s*\|\s*\S.*\|", s)) or s.count("|") >= 2,
                    "hints": hints_of(s),
                })

    stat = {
        "title": args.title,
        "pages": len({p for p, _ in pages}),
        "pages_missing": all(p == 0 for p, _ in pages),
        "blocks": len(blocks),
        "noise_blocks": sum(1 for b in blocks if b["noise"]),
        "heading_blocks": sum(1 for b in blocks if b["heading"]),
        "chars": sum(b["chars"] for b in blocks),
        "hint_cover": {k: sum(1 for b in blocks if k in b["hints"]) for k, _ in HINT_PATTERNS},
    }
    lens = [b["chars"] for b in blocks if not b["noise"]]
    if lens:
        stat["sent_chars_median"] = statistics.median(lens)
        stat["sent_chars_p90"] = sorted(lens)[int(len(lens) * 0.9) - 1 if len(lens) > 1 else 0]

    with open(os.path.join(args.out, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "scaffold_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stat, f, ensure_ascii=False, indent=1)

    with open(os.path.join(args.out, "blocks.md"), "w", encoding="utf-8") as f:
        f.write("# 材料句子块清单\n\n")
        f.write("共 %d 块 / %d 页 / %d 字。`hints` 只是句式线索，不是分类结论。\n\n"
                % (stat["blocks"], stat["pages"], stat["chars"]))
        for b in blocks:
            if b["noise"]:
                continue
            tag = ""
            if b["heading"]:
                tag += " [标题]"
            if b["hints"]:
                tag += " [%s]" % ",".join(b["hints"])
            f.write("- `%s`%s %s\n" % (b["id"], tag, b["text"][:220]))

    print(json.dumps({k: stat[k] for k in ("blocks", "pages", "chars", "noise_blocks")},
                     ensure_ascii=False))
    print("写出 %s/blocks.json、blocks.md、scaffold_stats.json" % args.out)
    if stat["pages_missing"]:
        print("注意：材料没有页码锚点，evidence 只能用 P0-Sn；如可能请换用保留页码的抽取方式。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
