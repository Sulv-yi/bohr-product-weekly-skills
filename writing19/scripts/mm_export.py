#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mm_export.py —— 把 nodes.json 导出为可编辑、可打开、可核对的四种格式。

为什么要四种：评审说"可继续编辑"是指能用通用工具打开，不是"我给了 JSON"。
  .mm    FreeMind / XMind / MindMaster 直接打开并继续改
  .opml  大纲类工具（OmniOutliner、幕布、Workflowy）通用交换格式
  .md    纯文本大纲，diff 友好，便于进版本库
  .svg   矢量预览，浏览器/Office/Illustrator 都能开，节点上带证据编号

用法：
    python3 mm_export.py --nodes work/nodes.json --blocks work/blocks.json \
        --out work/mindmap --title "材料标题"

退出码 0 表示四种格式都写出。
"""
import argparse
import html
import json
import os
import re
import sys

FONT = "'Microsoft YaHei','PingFang SC','Noto Sans CJK SC','Source Han Sans SC',sans-serif"

# 层级配色：按深度取，浅色主题下也能看清
PALETTE = ["#1f3b63", "#2f6f8f", "#3f8f7f", "#8a6d3b", "#6b5b95", "#7f5a58"]
TYPE_LABEL = {
    "root": "主题", "question": "问题", "method": "方法", "evidence": "证据",
    "conclusion": "结论", "limitation": "局限", "task": "任务",
}
KIND_LABEL = {
    "cause": "因果", "depend": "依赖", "contrast": "对比", "sequence": "时序",
    "cite": "引用", "support": "支撑", "conflict": "冲突",
}


def load(p):
    return json.load(open(p, encoding="utf-8"))


def tree_of(doc):
    nodes = doc.get("nodes") or []
    by_id = {n["id"]: n for n in nodes}
    kids = {}
    root = None
    for n in nodes:
        p = n.get("parent")
        if p in (None, "", "null"):
            root = n
        else:
            kids.setdefault(p, []).append(n)
    def natkey(n):
        m = re.search(r"\d+", n.get("id") or "")
        return (n.get("order") if isinstance(n.get("order"), int) else 0,
                int(m.group()) if m else 0)

    for v in kids.values():
        v.sort(key=natkey)
    return by_id, kids, root


def walk(root, kids, depth=0, out=None):
    out = out if out is not None else []
    out.append((root, depth))
    for k in kids.get(root["id"], []):
        walk(k, kids, depth + 1, out)
    return out


def note_of(n):
    parts = []
    if n.get("type"):
        parts.append("类型：%s" % TYPE_LABEL.get(n["type"], n["type"]))
    if n.get("level"):
        parts.append("依据级别：%s" % {"fact": "原文直读", "summary": "概括",
                                       "inference": "推断"}.get(n["level"], n["level"]))
    if n.get("evidence"):
        parts.append("证据：%s" % ", ".join(n["evidence"]))
    if n.get("note"):
        parts.append(n["note"])
    return "；".join(parts)


# ---------------- .mm ----------------
def to_mm(doc, blocks_map):
    by_id, kids, root = tree_of(doc)

    def emit(n):
        attrs = ' TEXT="%s"' % html.escape(n.get("title", ""), quote=True)
        if n.get("type") and n["type"] != "root":
            attrs += ' STYLE="fork"'
        note = note_of(n)
        inner = ""
        if note:
            inner += ('<richcontent TYPE="NOTE"><html><head></head><body><p>%s</p>'
                      '</body></html></richcontent>' % html.escape(note))
        ev = n.get("evidence") or []
        if ev and ev[0] in blocks_map:
            b = blocks_map[ev[0]]
            if b.get("page"):
                inner += '<attribute NAME="page" VALUE="%d"/>' % b["page"]
        for c in kids.get(n["id"], []):
            inner += emit(c)
        return "<node%s>%s</node>" % (attrs, inner)

    return ('<?xml version="1.0" encoding="UTF-8"?>\n<map version="1.0.1">\n%s\n</map>\n'
            % emit(root))


# ---------------- .opml ----------------
def to_opml(doc, blocks_map, title):
    by_id, kids, root = tree_of(doc)

    def emit(n, ind):
        pad = "  " * ind
        note = note_of(n)
        attrs = ' text="%s"' % html.escape(n.get("title", ""), quote=True)
        if note:
            attrs += ' _note="%s"' % html.escape(note, quote=True)
        if n.get("type"):
            attrs += ' type="%s"' % n["type"]
        cs = kids.get(n["id"], [])
        if not cs:
            return "%s<outline%s/>\n" % (pad, attrs)
        s = "%s<outline%s>\n" % (pad, attrs)
        for c in cs:
            s += emit(c, ind + 1)
        return s + "%s</outline>\n" % pad

    return ('<?xml version="1.0" encoding="UTF-8"?>\n<opml version="2.0">\n<head>\n'
            '<title>%s</title>\n</head>\n<body>\n%s</body>\n</opml>\n'
            % (html.escape(title), emit(root, 1)))


# ---------------- .md ----------------
def to_md(doc, blocks_map, title):
    by_id, kids, root = tree_of(doc)
    lines = ["# %s" % (title or root.get("title", "思维导图")), ""]
    lines.append("> 每个节点后的 `P页-S句` 是原文定位；`[推断]` 表示该节点跨了"
                 "原文未直接连接的段落，需人工确认。")
    lines.append("")

    def emit(n, d):
        tag = TYPE_LABEL.get(n.get("type"), "")
        ev = ", ".join(n.get("evidence") or [])
        lv = " [推断]" if n.get("level") == "inference" else ""
        if n.get("type") == "root":
            lines.append("- **%s**" % n.get("title"))
        else:
            lines.append("%s- %s%s%s　`%s`"
                         % ("  " * d, ("【%s】" % tag) if tag else "", n.get("title"), lv, ev))
        for c in kids.get(n["id"], []):
            emit(c, d + 1)

    emit(root, 0)

    rels = doc.get("relations") or []
    if rels:
        lines += ["", "## 关系", "", "| 从 | 到 | 类型 | 依据 |", "|-|-|-|-|"]
        for r in rels:
            lines.append("| %s | %s | %s | %s |" % (
                by_id.get(r.get("from"), {}).get("title", r.get("from")),
                by_id.get(r.get("to"), {}).get("title", r.get("to")),
                KIND_LABEL.get(r.get("kind"), r.get("kind")),
                ", ".join(r.get("evidence") or [])))

    unc = doc.get("uncertainty") or []
    if unc:
        lines += ["", "## 待人工确认", ""]
        for u in unc:
            nm = by_id.get(u.get("node"), {}).get("title", u.get("node"))
            lines.append("- **%s**：%s（需要：%s）"
                         % (nm, u.get("why", ""), u.get("needs", "—")))
    return "\n".join(lines) + "\n"


# ---------------- .svg ----------------
def text_width(s, size):
    w = 0.0
    for ch in s:
        w += size * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w


def wrap(s, max_chars=14, max_lines=3):
    s = s or ""
    out, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= max_chars:
            out.append(cur)
            cur = ""
            if len(out) == max_lines:
                break
    if cur and len(out) < max_lines:
        out.append(cur)
    if len(out) == max_lines and sum(len(x) for x in out) < len(s):
        out[-1] = out[-1][:-1] + "…"
    return out or [""]


def to_svg(doc, blocks_map, title):
    """一级分支横排、分支内纵向堆叠的树形布局。

    纯横向铺开在高扇出时会拉到六七千像素，读者要一直左右拖。
    这里把一级分支当列（横排），每列内部按深度缩进、纵向堆叠，
    宽度只跟分支数有关，高度跟节点总数有关——32 个节点大约 1500×1800。
    """
    by_id, kids, root = tree_of(doc)
    FS, LH, PADX, PADY, ROWGAP, INDENT, COLGAP = 14, 19, 14, 9, 13, 26, 34

    lines_of, wnode, hnode = {}, {}, {}
    for nid, n in by_id.items():
        ls = wrap(n.get("title"))
        lines_of[nid] = ls
        wnode[nid] = max(max(text_width(x, FS) for x in ls) + PADX * 2, 96)
        hnode[nid] = max(34, len(ls) * LH + PADY * 2)

    def subtree(n, out):
        out.append(n)
        for c in kids.get(n["id"], []):
            subtree(c, out)
        return out

    branches = kids.get(root["id"], [])
    cols = []
    for b in branches:
        ns = subtree(b, [])
        rel_depth = {}
        d = {}

        def mark(n, dep):
            d[n["id"]] = dep
            for c in kids.get(n["id"], []):
                mark(c, dep + 1)
        mark(b, 0)
        rel_depth = d
        colw = max(wnode[x["id"]] + rel_depth[x["id"]] * INDENT for x in ns)
        colh = sum(hnode[x["id"]] + ROWGAP for x in ns)
        cols.append((b, ns, rel_depth, colw, colh))

    top = 34 + hnode[root["id"]] + 58
    total_w = sum(c[3] for c in cols) + COLGAP * max(0, len(cols) - 1) + 48
    W = int(max(total_w, wnode[root["id"]] + 48))
    H = int(top + max([c[4] for c in cols] or [0]) + 34)

    pos = {root["id"]: ((W - wnode[root["id"]]) / 2.0, 34)}
    x = 24.0
    for b, ns, rd, colw, colh in cols:
        y = float(top)
        for n in ns:
            pos[n["id"]] = (x + rd[n["id"]] * INDENT, y)
            y += hnode[n["id"]] + ROWGAP
        x += colw + COLGAP

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FONT),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="4" '
           'markerWidth="6" markerHeight="6" orient="auto">'
           '<path d="M0 0 L10 4 L0 8 z" fill="#c8873c"/></marker></defs>',
           '<text x="18" y="22" font-size="12" fill="#9aa1ab">%s</text>'
           % html.escape(title or "", quote=False)]

    # 父子连线：从父框底边中点到子框左边中点，走直角折线
    for nid, (px, py) in pos.items():
        for c in kids.get(nid, []):
            cx, cy = pos[c["id"]]
            x1 = px + wnode[nid] / 2.0
            y1 = py + hnode[nid]
            x2 = cx
            y2 = cy + hnode[c["id"]] / 2.0
            mid = (y1 + y2) / 2.0
            out.append('<path d="M%.1f %.1f V%.1f H%.1f V%.1f" fill="none" '
                       'stroke="#c3ccd8" stroke-width="1.3"/>'
                       % (x1, y1, mid, x2, y2))

    for r in doc.get("relations") or []:
        a, b2 = r.get("from"), r.get("to")
        if a not in pos or b2 not in pos:
            continue
        ax, ay = pos[a]
        bx, by = pos[b2]
        out.append('<path d="M%.1f %.1f L%.1f %.1f" stroke="#c8873c" stroke-width="1.1" '
                   'stroke-dasharray="5 4" marker-end="url(#ar)"/>'
                   % (ax + wnode[a] / 2.0, ay + hnode[a] / 2.0,
                      bx + wnode[b2] / 2.0, by + hnode[b2] / 2.0))

    dep = {root["id"]: 0}
    for b, ns, rd, _w, _h in cols:
        for n in ns:
            dep[n["id"]] = rd[n["id"]] + 1

    for nid, (x0, y0) in pos.items():
        d = dep.get(nid, 0)
        w, h = wnode[nid], hnode[nid]
        c = PALETTE[min(d, len(PALETTE) - 1)]
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="7" '
                   'fill="%s" stroke="%s" stroke-width="1.6"/>'
                   % (x0, y0, w, h, c if d == 0 else "#ffffff", c))
        for i, ln in enumerate(lines_of[nid]):
            out.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s">%s</text>'
                       % (x0 + PADX, y0 + PADY + LH * (i + 0.76), FS,
                          "#ffffff" if d == 0 else "#20262f",
                          html.escape(ln, quote=False)))
        ev = by_id[nid].get("evidence") or []
        if ev and d > 0:
            out.append('<text x="%.1f" y="%.1f" font-size="9" fill="#98a0aa" '
                       'text-anchor="end">%s</text>'
                       % (x0 + w - 7, y0 + h - 6, html.escape(ev[0])))

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--blocks", required=True)
    ap.add_argument("--out", default="work/mindmap")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    doc = load(args.nodes)
    blocks_map = {b["id"]: b for b in load(args.blocks)}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    title = args.title or (doc.get("title") or "")

    files = {
        ".mm": to_mm(doc, blocks_map),
        ".opml": to_opml(doc, blocks_map, title),
        ".md": to_md(doc, blocks_map, title),
        ".svg": to_svg(doc, blocks_map, title),
    }
    total = 0
    for ext, content in files.items():
        p = args.out + ext
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        total += len(content.encode("utf-8"))
        print("写出 %s（%d 字节）" % (p, len(content.encode("utf-8"))))
    print("合计 %d 字节" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
