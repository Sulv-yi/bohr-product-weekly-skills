#!/usr/bin/env python3
"""doctext —— 把科研 PDF 解析成"可回查的结构化文档模型"。

与只吐纯文本的抽取器不同，本脚本一次性给出后续所有阅读类任务都需要的结构：

  paragraphs  段落（带 page / 段号 / char 偏移 / 是否标题）
  sections    章节树（按编号与受控词表，含层级）
  metadata    标题 / 作者 / 单位 / 摘要 / 关键词 / DOI
  captions    图表题注（Figure 1 / Table 2 / 图 3 / 表 4 …）含编号与所属段落
  tables      表格（题注定位 + 连续多单元格行；解析不出时如实留空并记原因）
  references  参考文献条目（可解析出作者/年份/DOI 的尽量解析，其余保留原文）
  footnotes   脚注候选
  stats       页数、不可读页、页眉页脚剔除量、后端、耗时

设计约束：
  1) 评测环境可能没有第三方库 → pypdf → pdftotext → 内置 CMap 解码，三级降级；
  2) stdout 只输出一行 JSON 摘要，所有警告走 stderr（避免污染被重定向的 JSON 文件）；
  3) 不猜内容：读不出的页进 stats.unreadable_pages，解析不出结构的表格进
     stats.unparsed_tables 并附原因，绝不编造单元格。

用法：
  python doctext.py paper.pdf --out doc.json
  python doctext.py paper.pdf --out doc.json --probe          # 只探查，不建段落
  python doctext.py paper.pdf --out doc.json --keep-header-footer
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import warnings
import zlib

warnings.filterwarnings("ignore")
for _n in ("pypdf", "pypdf._reader", "pypdf.generic", "pdfminer", "fontTools"):
    logging.getLogger(_n).setLevel(logging.CRITICAL)

VERSION = "1.1.0"

# ---------------------------------------------------------------- 规范化

_LIG = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
    "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
    "\u00ad": "", "\u2010": "-", "\u2011": "-",
    "\ufeff": "", "\u200b": "",
}
_CJK = re.compile(r"[\u4e00-\u9fff]")
_SENT_END = re.compile(r"[.。!?！？；;]\s*$")
_PAGENO = re.compile(r"^\s*(?:[-–—]\s*)?\d{1,4}(?:\s*[-–—])?\s*$")
_STRUCT_HEAD = re.compile(
    r"^\s*(?:\d+(?:\.\d+){0,3}\s*[|.、)]?\s*)?"
    r"(abstract|摘要|introduction|引言|前言|background|results?|讨论|"
    r"conclusions?|结论|references?|参考文献|acknowledg\w*|致谢|"
    r"methods?|materials|experimental|实验)\b", re.I)

# 章节受控词表：中英 + 常见编号写法
SEC_WORDS = [
    ("abstract", 1), ("摘要", 1),
    ("introduction", 1), ("引言", 1), ("前言", 1), ("background", 1),
    ("materials and methods", 1), ("methods", 1), ("method", 1),
    ("experimental section", 1), ("experimental", 1), ("methodology", 1),
    ("材料与方法", 1), ("实验部分", 1), ("方法", 1),
    ("results and discussion", 1), ("results", 1), ("discussion", 1),
    ("结果与分析", 1), ("结果与讨论", 1), ("结果", 1), ("讨论", 1),
    ("conclusions and perspectives", 1), ("conclusion", 1), ("conclusions", 1),
    ("结论与展望", 1), ("结论", 1), ("总结", 1),
    ("acknowledgements", 1), ("acknowledgments", 1), ("致谢", 1),
    ("references", 1), ("reference", 1), ("参考文献", 1),
    ("supplementary", 1), ("appendix", 1), ("附录", 1),
]
_SEC_ALT = "|".join(sorted((w for w, _ in SEC_WORDS), key=len, reverse=True))

_HEAD_RE = re.compile(
    rf"^\s*(?:(?P<num>\d{{1,2}}(?:\.\d{{1,2}}){{0,3}})\s*[|.、)\-–—]?\s*)?"
    rf"(?P<word>{_SEC_ALT})\b", re.I)
_HEAD_SPLIT = re.compile(
    rf"^\s*(?:(?:\d{{1,2}}(?:\.\d{{1,2}}){{0,3}})\s*[|.、)\-–—]?\s*)?"
    rf"(?:{_SEC_ALT})"
    rf"(?:\s*(?:and|与)\s*(?:discussion|讨论|analysis|分析|perspectives?|展望))?"
    rf"(?=\s+\S)", re.I)

# 图表题注
_CAP_RE = re.compile(
    r"^\s*(?P<label>(?:figure|fig\.?|table|scheme|chart|图|表|附图|附表)\s*"
    r"(?P<num>[0-9]{1,3}(?:\.[0-9]{1,3})?[a-z]?))"
    r"\s*(?:[.:|｜、\-–—]\s*)?(?P<cap>.*)$", re.I)

# 参考文献条目起点
_REF_ENTRY = re.compile(
    r"^\s*(?:\[(?P<n>\d{1,3})\]|(?P<n2>\d{1,3})\.\s|(?P<au>[A-Z][A-Za-z'\-]+,\s*[A-Z]))")

_DOI = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")

# ---------------------------------------------------------------- 文本整形


def norm(s: str) -> str:
    for k, v in _LIG.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t\u00a0]+", " ", s)


def reflow(page_text: str) -> list[str]:
    """把 PDF 的硬换行重排成逻辑段落。"""
    lines = [l.strip() for l in norm(page_text or "").split("\n") if l.strip()]
    merged: list[str] = []
    for ln in lines:
        if is_heading(ln) and not re.search(r"[，,；;]", ln):
            merged.append(ln)
            continue
        if _CAP_RE.match(ln) and len(ln) > 8:
            merged.append(ln)
            continue
        if not merged:
            merged.append(ln)
            continue
        prev = merged[-1]
        if prev.endswith("-") and ln[:1].islower():
            merged[-1] = prev[:-1] + ln
            continue
        join = False
        if not _SENT_END.search(prev) and not _STRUCT_HEAD.match(ln):
            join = True
        if _CJK.search(prev) and not _SENT_END.search(prev):
            join = True
        # 上一段是题注则以句读结尾为界，避免把正文并进题注
        if _CAP_RE.match(prev) and _SENT_END.search(prev):
            join = False
        if join:
            sep = "" if (_CJK.search(prev[-1:]) or _CJK.search(ln[:1])) else " "
            merged[-1] = prev + sep + ln
        else:
            merged.append(ln)

    out: list[str] = []
    for blk in merged:
        if len(blk) <= 900:
            out.append(blk)
            continue
        buf = ""
        for s in re.split(r"(?<=[.!?。！？])\s+", blk):
            if len(buf) + len(s) > 600 and buf:
                out.append(buf)
                buf = s
            else:
                buf = (buf + " " + s).strip() if buf else s
        if buf:
            out.append(buf)
    return out


_CN_NUM_HEAD = re.compile(
    r"^\s*(?:第\s*[一二三四五六七八九十百]+\s*[章节部分]\s*)?"
    r"[一二三四五六七八九十]+\s*[、.．]\s*\S{2,40}\s*$")
_NUM_HEAD = re.compile(
    r"^\s*\d{1,2}(?:\.\d{1,2}){0,3}\s+[^\s。，,；;].{0,48}$")


def is_heading(text: str) -> bool:
    if len(text) > 140 or _SENT_END.search(text):
        return False
    if _HEAD_RE.match(text):
        return True
    if _CAP_RE.match(text):
        return False
    # 中文"一、团队介绍" 与 "2.1 开发背景与意义" 这类无受控词的标题
    if _CN_NUM_HEAD.match(text) and not re.search(r"[。，,；;：:]", text):
        return True
    if _NUM_HEAD.match(text) and not re.search(r"[。，,；;：:]", text) \
            and len(text) <= 52:
        rest = re.sub(r"^\s*\d{1,2}(?:\.\d{1,2}){0,3}\s+", "", text)
        lead = re.match(r"^\s*(\d{1,2})", text)
        # 表格数据行也会以数字开头（"1 0.43 ± 0.1 49.3 ± 0.05"），必须排除
        if len(re.findall(r"\d+(?:\.\d+)?", rest)) <= 1 and len(rest) >= 3 \
                and lead and lead.group(1) != "0":
            return True
    return False


def split_leading_heading(chunk: str) -> tuple[str | None, str]:
    m = _HEAD_SPLIT.match(chunk)
    if not m:
        return None, chunk
    head = chunk[:m.end()].strip()
    rest = chunk[m.end():].strip()
    if len(head) > 60 or len(rest) < 40:
        return None, chunk
    return head, rest


# ---------------------------------------------------------------- 后端


def backend_pypdf(path: str) -> dict | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        reader = PdfReader(path, strict=False)
    except Exception:
        return None
    enc = bool(getattr(reader, "is_encrypted", False))
    if enc:
        try:
            reader.decrypt("")
        except Exception:
            return {"backend": "pypdf", "pages_text": [], "encrypted": True,
                    "needs_pass": True}
        if getattr(reader, "is_encrypted", False):
            return {"backend": "pypdf", "pages_text": [], "encrypted": True,
                    "needs_pass": True}
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return {"backend": "pypdf", "pages_text": texts, "encrypted": enc,
            "needs_pass": False}


def backend_pdftotext(path: str) -> dict | None:
    if not shutil.which("pdftotext"):
        return None
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True, errors="replace")
    if out.returncode != 0:
        out = subprocess.run(["pdftotext", path, "-"],
                             capture_output=True, text=True, errors="replace")
    pages = (out.stdout or "").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return {"backend": "pdftotext", "pages_text": pages, "encrypted": False,
            "needs_pass": False}


_OBJ = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)
_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_TOKEN = re.compile(
    rb"\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>|\[|\]|"
    rb"TJ|Tj|T\*|Td|TD|Tm|ET|BT")


def _pdf_objects(data: bytes) -> dict:
    objs = {}
    for m in _OBJ.finditer(data):
        num, body = int(m.group(1)), m.group(3)
        sm = _STREAM.search(body)
        if sm and b"FlateDecode" in body[: sm.start()]:
            try:
                body = zlib.decompress(sm.group(1))
            except Exception:
                continue
        objs[num] = body
    return objs


def _cmap_from(obj: bytes) -> dict:
    table = {}
    txt = obj.decode("latin-1", "replace")
    for blk in re.findall(r"beginbfchar(.*?)endbfchar", txt, re.S):
        for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            try:
                table[int(a, 16)] = bytes.fromhex(b).decode("utf-16-be", "ignore")
            except Exception:
                continue
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", txt, re.S):
        for a, b, c in re.findall(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            try:
                lo, hi, dst = int(a, 16), int(b, 16), int(c, 16)
            except Exception:
                continue
            for i in range(min(hi - lo, 4096) + 1):
                try:
                    table[lo + i] = chr(dst + i)
                except Exception:
                    break
    return table


def _unescape(s: bytes) -> str:
    out, i = bytearray(), 0
    mp = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12,
          0x28: 40, 0x29: 41, 0x5C: 92}
    while i < len(s):
        c = s[i]
        if c == 0x5C and i + 1 < len(s):
            n = s[i + 1]
            if n in mp:
                out.append(mp[n]); i += 2; continue
            m = re.match(rb"[0-7]{1,3}", s[i + 1:i + 4])
            if m:
                out.append(int(m.group(0), 8) & 0xFF)
                i += 1 + len(m.group(0)); continue
            i += 2; continue
        out.append(c); i += 1
    return out.decode("latin-1", "replace")


def _stream_text(stream: bytes, cmap: dict) -> list[str]:
    out, buf = [], []

    def flush():
        if buf:
            out.append("".join(buf)); buf.clear()

    for m in _TOKEN.finditer(stream):
        tok = m.group(0)
        if tok.startswith(b"("):
            buf.append(_unescape(tok[1:-1]))
        elif tok.startswith(b"<"):
            hexs = re.sub(rb"\s", b"", tok[1:-1])
            if len(hexs) % 2:
                hexs += b"0"
            try:
                raw = bytes.fromhex(hexs.decode("ascii"))
            except Exception:
                continue
            if cmap:
                buf.append("".join(
                    cmap.get((raw[i] << 8) | raw[i + 1], "")
                    for i in range(0, len(raw) - 1, 2)))
            else:
                buf.append(raw.decode("latin-1", "replace"))
        elif tok in (b"T*", b"Td", b"TD", b"Tm", b"ET"):
            flush()
    flush()
    return out


def backend_builtin(path: str) -> dict | None:
    """纯标准库后端：先用 pdfmini（页树+坐标+分栏），失败再退到旧路径。"""
    try:
        import pdfmini
        got = pdfmini.extract(path)
        if got and got.get("pages_text"):
            return {"backend": "builtin", "pages_text": got["pages_text"],
                    "pages_chunks": got.get("pages_chunks") or [],
                    "encrypted": False, "needs_pass": False}
    except Exception as exc:  # 解析器自身异常不能吞掉整个流程
        sys.stderr.write("[doctext] pdfmini failed: %s\n" % exc)
    return _builtin_legacy(path)


def _builtin_legacy(path: str) -> dict | None:
    """旧路径：按对象顺序拼流文本，无坐标、无页序纠正（保留作对照基线）。"""
    with open(path, "rb") as fh:
        data = fh.read()
    objs = _pdf_objects(data)
    if not objs:
        return None
    cmap = {}
    for body in objs.values():
        if b"beginbfchar" in body or b"beginbfrange" in body:
            cmap.update(_cmap_from(body))
    pages = []
    for num in sorted(objs):
        body = objs[num]
        if b"BT" not in body or (b"Tj" not in body and b"TJ" not in body):
            continue
        txt = "\n".join(l for l in _stream_text(body, cmap) if l.strip())
        if txt.strip():
            pages.append(txt)
    if not pages:
        return None
    return {"backend": "builtin", "pages_text": pages, "encrypted": False,
            "needs_pass": False}


def layout_pages(path: str) -> list[str]:
    """尽力拿到保留空白的版面文本，仅用于表格行检测。失败返回 []。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path, strict=False)
        if getattr(reader, "is_encrypted", False):
            reader.decrypt("")
        out = []
        for page in reader.pages:
            try:
                out.append(page.extract_text(extraction_mode="layout") or "")
            except Exception:
                out.append("")
        if any(t.strip() for t in out):
            return out
    except Exception:
        pass
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, text=True, errors="replace")
        if r.returncode == 0:
            pages = (r.stdout or "").split("\f")
            if pages and not pages[-1].strip():
                pages.pop()
            return pages
    return []


# ---------------------------------------------------------------- 结构层


def build_sections(paragraphs: list[dict]) -> list[dict]:
    """按标题段建章节树。层级来源：标题编号的段数；无编号则平级。"""
    secs = []
    stack: list[dict] = []
    for p in paragraphs:
        if not p["is_heading"]:
            continue
        t = p["text"].strip()
        m = _HEAD_RE.match(t)
        num = (m.group("num") if m else None) or ""
        level = len(num.split(".")) if num else 1
        node = {"id": p["id"], "page": p["page"], "title": t[:120],
                "number": num or None, "level": min(level, 4),
                "para_start": p["id"], "children": []}
        while stack and stack[-1]["level"] >= node["level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node["id"])
        secs.append(node)
        stack.append(node)
    return secs


def attach_section(paragraphs: list[dict], sections: list[dict]) -> None:
    """给每段标上所属章节标题（就近向上）。"""
    cur = None
    by_id = {s["id"]: s for s in sections}
    for p in paragraphs:
        if p["id"] in by_id:
            cur = by_id[p["id"]]["title"]
        p["section"] = cur


def build_captions(paragraphs: list[dict]) -> list[dict]:
    caps = []
    for p in paragraphs:
        m = _CAP_RE.match(p["text"])
        if not m:
            continue
        label = re.sub(r"\s+", " ", m.group("label")).strip()
        body = (m.group("cap") or "").strip()
        # 题注行本身要短；长文多半是正文里的引用句（"Figure 3 shows ..."）
        if not body and len(p["text"]) > 40:
            continue
        # 正文句里的 "Figure 2B shows that ..." 不是题注：小写动词开头一律排除
        if re.match(r"^(shows?|indicates?|illustrates?|presents?|depicts?|"
                    r"displays?|summari[sz]es?|lists?|report|gives?|reveals?)\b",
                    body, re.I):
            continue
        # "Table 5: The table shows that ..." 是正文引述句，不是题注：
        # 真题注以名词短语开头（"Viscosity and DCf of ..."），
        # 引述句则以 "The/This/As ..." 开头并再次提到表格或图。
        if re.match(r"^(the|this|these|those|as|it|in|from|for)\b", body, re.I) and \
                re.search(r"\b(table|figure|scheme|fig\.)\b", body[:48], re.I):
            continue
        if len(body) > 400:
            body = body[:400]
        kind = "table" if re.match(r"(table|表|附表)", label, re.I) else "figure"
        caps.append({"id": "cap-" + p["id"], "kind": kind, "label": label,
                     "number": m.group("num"), "page": p["page"],
                     "text": (label + (": " + body if body else "")).strip(),
                     "paragraph_id": p["id"],
                     "caption_truncated": len(body) >= 400})
    # 同一编号的题注只保留正文更长的一条：PDF 里同一张表常同时出现
    # 目录式短标签和正式题注，重复条目会把下游表格重建指向同一页两次。
    seen, out = {}, []
    for c in caps:
        key = (c["kind"], c["number"])
        if key not in seen:
            seen[key] = len(out)
            out.append(c)
            continue
        j = seen[key]
        if len(c["text"]) > len(out[j]["text"]):
            out[j] = c
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"\s{2,}", line.strip()) if c.strip()]


def page_chunks(path: str) -> list[list[dict]]:
    """用 pypdf 的 visitor 拿到带坐标的文本块，仅用于表格分栏。失败返回 []。"""
    try:
        from pypdf import PdfReader
    except Exception:
        return []
    try:
        reader = PdfReader(path, strict=False)
        if getattr(reader, "is_encrypted", False):
            reader.decrypt("")
    except Exception:
        return []
    out_pages: list[list[dict]] = []
    for page in reader.pages:
        chunks: list[dict] = []

        def visit(text, cm=None, tm=None, font_dict=None, font_size=None):
            s = (text or "").strip()
            if not s:
                return
            try:
                x = float(tm[4]) if tm else 0.0
                y = float(tm[5]) if tm else 0.0
            except Exception:
                x = y = 0.0
            chunks.append({"x": round(x, 1), "y": round(y, 1),
                           "size": float(font_size or 0), "text": s})

        try:
            page.extract_text(visitor_text=visit)
        except Exception:
            chunks = []
        out_pages.append(chunks)
    return out_pages


def _rows_from_chunks(chunks: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for c in sorted(chunks, key=lambda c: (-c["y"], c["x"])):
        if rows and abs(rows[-1][0]["y"] - c["y"]) <= y_tol:
            rows[-1].append(c)
        else:
            rows.append([c])
    for r in rows:
        r.sort(key=lambda c: c["x"])
    return rows


def _table_region(rows: list[list[dict]], start: int, max_rows: int = 90) -> list[list[dict]]:
    """从题注下一行起取表格块。

    结束条件取三种信号，任一触发即停：纵向间距突变（>4 倍常规行距）、
    出现下一个题注、或整行文字过长（正文段落，不是表格行）。
    """
    block, gaps = [], []
    for r in rows[start + 1: start + max_rows]:
        txt = " ".join(x["text"] for x in r).strip()
        if not txt:
            continue
        if re.match(r"^\s*(Table|Tab\.|FIGURE|Figure|Scheme|图|表)\s*\d", txt, re.I):
            break
        # 表格行是碎片；单块且偏长的行已经是正文段落（尤其双栏版面里
        # 每栏一行就是一段的一部分），继续往下取只会把正文算进表格。
        if len(r) == 1 and len(r[0]["text"]) > 55:
            break
        if len(txt) > 260:
            break
        if block:
            dy = block[-1][0]["y"] - r[0]["y"]
            if dy <= 0:
                continue
            gaps.append(dy)
            med = sorted(gaps)[len(gaps) // 2] if gaps else dy
            if med > 0 and dy > med * 2.2:
                break
            if dy > 40:
                break
        block.append(r)
    return block


def _columns_by_anchor(rows: list[list[dict]], tol: float = 10.0,
                       min_support: int = 2) -> list[float]:
    """按块左边缘聚类出列锚点。

    表格每一列在版面上有固定的左边界，纵向合并单元格只会让某些行缺值，
    不会移动其余行的边界。因此聚类比「逐行切缝」稳；稀疏列（只有表头或
    少数行有值）也能保留下来。
    """
    xs = sorted(c["x"] for r in rows for c in r)
    clusters: list[list[float]] = []
    for x in xs:
        if clusters and x - clusters[-1][-1] <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    anchors = [sum(c) / len(c) for c in clusters if len(c) >= min_support]
    # 表头里的列即使全表只出现一次，也必须留作锚点
    if rows:
        for c in rows[0]:
            if all(abs(c["x"] - a) > tol for a in anchors):
                anchors.append(c["x"])
    return sorted(anchors)


def _assign_to_anchors(row: list[dict], anchors: list[float]) -> list[str]:
    cells = ["" for _ in anchors]
    for c in row:
        i = min(range(len(anchors)), key=lambda j: abs(c["x"] - anchors[j]))
        t = c["text"].strip()
        if not t:
            continue
        if cells[i]:
            sep = "" if (_CJK.search(cells[i][-1:]) or _CJK.search(t[:1])) else " "
            cells[i] = cells[i] + sep + t
        else:
            cells[i] = t
    return cells


def build_tables_proj(chunks_pages: list[list[dict]], captions: list[dict],
                      stats: dict) -> list[dict]:
    """投影法重建表格：跨行找列缝，再按列归位。纵向合并单元格不再导致整表丢弃。"""
    tables = []
    for c in captions:
        if c["kind"] != "table":
            continue
        pno = c["page"] - 1
        if not (0 <= pno < len(chunks_pages)):
            continue
        # 双栏版面上题注在右栏，整行文本会以左栏正文开头，
        # 因此按「块」而不是按「行」找题注，并锁定题注所在的横坐标带。
        page = chunks_pages[pno]
        hit = None
        for ch in page:
            if re.match(rf"^\s*{re.escape(c['label'])}\b", ch["text"], re.I):
                hit = ch
                break
        if hit is None:
            continue
        cx = hit["x"]
        band = [ch for ch in page if ch["x"] >= cx - 4.0]
        rows_all = _rows_from_chunks(band, y_tol=4.0)
        start = None
        for i, r in enumerate(rows_all):
            if any(ch is hit for ch in r):
                start = i
                break
        if start is None:
            continue
        block = _table_region(rows_all, start)
        # 表格行是短句片段：从第一处出现长句的行截断，后面必是正文
        for i, r in enumerate(block):
            if len(r) == 1 and len(r[0]["text"]) > 55:
                block = block[:i]
                break
        if len(block) < 2:
            continue
        anchors = _columns_by_anchor(block)
        if len(anchors) < 2 or len(anchors) > 14:
            continue
        grid = [_assign_to_anchors(r, anchors) for r in block]
        # 全空列剔除（表头才有值的装饰列），但把被剔的列数记进产出
        used = [i for i in range(len(anchors)) if any(g[i] for g in grid)]
        if len(used) < 2:
            continue
        dropped = len(anchors) - len(used)
        grid = [[g[i] for i in used] for g in grid]
        ncol = len(used)
        filled = [sum(1 for t in g if t) for g in grid]
        # 纵向合并单元格表现为「该行只有部分列有字」；这是表格特征而非错误，
        # 只统计有多少行带跨列文字，作为置信度信号。
        ragged = sum(1 for f in filled if f < ncol)
        ratio = round(1 - ragged / max(1, len(grid)), 2)
        tables.append({
            "id": "tbl-" + c["id"], "page": c["page"], "label": c["label"],
            "caption_id": c["id"], "n_rows": len(grid), "n_cols": ncol,
            "n_cols_total": len(anchors),
            "columns_without_body_values": dropped,
            "header": grid[0], "rows": grid[1:],
            "raw_rows": [" ".join(c["text"].strip() for c in r) for r in block][:40],
            "cell_confidence": "high" if ratio >= 0.95 else ("medium" if ratio >= 0.7 else "low"),
            "extraction": "column-projection",
            "row_full_ratio": ratio,
            "merged_cell_rows": ragged,
            "column_anchors_pt": [round(anchors[i], 1) for i in used],
            "evidence": {"page": c["page"], "caption_id": c["id"]},
            "limitation": ("纵向合并单元格的行会出现空格位，内容未跨行复制；"
                           "多层表头合并为一行，需人工确认层级" if ragged else
                           "按跨行列投影切分，未检出合并单元格"),
        })
    stats["projection_tables"] = len(tables)
    return tables


def _row_cells(row: list[dict], gap: float = 10.0) -> list[str]:
    cells, cur, prev_x_end = [], "", None
    for c in row:
        if prev_x_end is not None and (c["x"] - prev_x_end) > gap:
            if cur.strip():
                cells.append(cur.strip())
            cur = c["text"]
        else:
            sep = "" if (cur[-1:] and c["text"][:1] and
                         (_CJK.search(cur[-1:]) or _CJK.search(c["text"][:1]))) else " "
            cur = (cur + sep + c["text"]).strip() if cur else c["text"]
        prev_x_end = c["x"] + len(c["text"]) * 0.45 * max(1.0, c["size"] or 8.0)
    if cur.strip():
        cells.append(cur.strip())
    return cells


def build_tables_coord(chunks_pages: list[list[dict]], captions: list[dict],
                       stats: dict) -> list[dict]:
    """坐标法：按 y 聚行、按 x 间隙切单元格，要求连续多行列数一致。

    单元格切分阈值不写死：同一张表在不同字号/栏宽下格间距差别很大，
    这里对每组候选阈值各切一遍，取"行数多、列数稳定"的那一组。
    """
    tables = []
    for c in captions:
        if c["kind"] != "table":
            continue
        pno = c["page"] - 1
        if not (0 <= pno < len(chunks_pages)):
            continue
        rows_all = _rows_from_chunks(chunks_pages[pno])
        start = None
        for i, r in enumerate(rows_all):
            txt = " ".join(x["text"] for x in r)
            if re.match(rf"^\s*{re.escape(c['label'])}", txt, re.I):
                start = i
                break
        if start is None:
            continue

        best = None
        for gap in (2.2, 3.0, 4.0, 5.5, 7.5, 10.0, 14.0, 20.0):
            grid, raw = [], []
            for r in rows_all[start + 1: start + 80]:
                cells = _row_cells(r, gap=gap)
                txt = " ".join(x["text"] for x in r)
                if len(cells) >= 2:
                    grid.append(cells)
                    raw.append(txt[:300])
                elif grid and len(cells) <= 1:
                    note = txt.strip()
                    if len(note) < 200 and re.match(r"^([a-z]\.?|\*|†|Note|注)[\s)]", note, re.I):
                        continue
                    break
            if len(grid) < 3:
                continue
            cnt = {}
            for r in grid:
                cnt[len(r)] = cnt.get(len(r), 0) + 1
            mode_cols, mode_n = max(cnt.items(), key=lambda kv: kv[1])
            ratio = mode_n / len(grid)
            rows_ok = [r for r in grid if len(r) == mode_cols]
            if not (2 <= mode_cols <= 12 and ratio >= 0.6 and len(rows_ok) >= 3):
                continue
            score = (ratio, len(rows_ok), mode_cols)
            if best is None or score > best[0]:
                best = (score, mode_cols, rows_ok, raw, gap)
        if best is None:
            continue
        score, mode_cols, rows, raw, gap = best
        tables.append({
            "id": "tbl-" + c["id"], "page": c["page"], "label": c["label"],
            "caption_id": c["id"], "n_rows": len(rows), "n_cols": mode_cols,
            "header": rows[0], "rows": rows[1:],
            "cell_confidence": "high" if score[0] >= 0.8 else "medium",
            "extraction": "coordinate-grid",
            "cell_gap_threshold_pt": gap,
            "row_consistency": round(score[0], 2),
            "evidence": {"page": c["page"], "caption_id": c["id"]},
            "raw_lines": raw[:6],
            "limitation": "按坐标栅格切分；跨行合并单元格会表现为空串，需人工确认",
        })
    stats["coordinate_tables"] = len(tables)
    return tables


def _stub_table(c: dict, reason: str) -> dict:
    """不可解析的表格也留条目：宁可在产出里写明失败原因，也不要静默丢表。"""
    return {
        "id": "tbl-" + c["id"], "page": c["page"], "label": c["label"],
        "caption_id": c["id"], "n_rows": 0, "n_cols": 0,
        "header": [], "rows": [],
        "cell_confidence": "unparsed",
        "extraction": "caption-only",
        "evidence": {"page": c["page"], "caption_id": c["id"]},
        "limitation": reason,
    }


def build_tables(path: str, captions: list[dict], stats: dict,
                 chunks_pages: list[list[dict]] | None = None) -> list[dict]:
    """三级重建：跨行列投影 → 单行间隙栅格 → 版面空白。

    三级都失败的表格不再静默消失，而是留一条 `caption-only` 占位，
    把失败原因写进 `limitation`，上层据此在 uncertainty 里如实说明。
    """
    tables: list[dict] = []
    chunks = chunks_pages if chunks_pages else page_chunks(path)
    if chunks and any(chunks):
        tables += build_tables_proj(chunks, captions, stats)
        done0 = {t["caption_id"] for t in tables}
        rest = [c for c in captions if c["kind"] == "table" and c["id"] not in done0]
        if rest:
            tables += build_tables_coord(chunks, rest, stats)
    done = {t["caption_id"] for t in tables}

    pages = layout_pages(path)
    if not pages:
        stats["table_region_source"] = "coordinate-only"
        for c in captions:
            if c["kind"] == "table" and c["id"] not in done:
                stats["unparsed_tables"].append(
                    {"label": c["label"], "page": c["page"],
                     "reason": "no layout text backend"})
                tables.append(_stub_table(c, "无可用的版面文本后端，仅保留题注"))
        return tables
    stats["table_region_source"] = "coordinate+layout"
    for c in captions:
        if c["kind"] != "table" or c["id"] in done:
            continue
        pno = c["page"] - 1
        rows, notes = [], []
        if 0 <= pno < len(pages):
            lines = [l.rstrip() for l in pages[pno].split("\n")]
            # 从题注行往下找，允许跨页续 1 页
            start = 0
            for i, l in enumerate(lines):
                if l.strip().startswith(c["label"].split()[0]) and \
                        c["number"] and c["number"] in l[:40]:
                    start = i + 1
                    break
            for i in range(start, min(len(lines), start + 60)):
                cells = _cells(lines[i])
                if len(cells) >= 2:
                    rows.append(cells)
                elif rows and not lines[i].strip():
                    break
                elif rows and len(cells) < 2 and lines[i].strip():
                    notes.append(lines[i].strip()[:120])
                    if len(notes) > 3:
                        break
        ncol = max((len(r) for r in rows), default=0)
        # 正文在两栏版面里也会出现"大量空白"，必须用列数的一致性把它们排除：
        # 真表格每行列数稳定，正文串栏得到的"行"列数忽多忽少。
        cnt = {}
        for r in rows:
            cnt[len(r)] = cnt.get(len(r), 0) + 1
        mode_cols, mode_n = max(cnt.items(), key=lambda kv: kv[1]) if cnt else (0, 0)
        stable = bool(rows) and mode_n / len(rows) >= 0.7 and 2 <= mode_cols <= 10
        if len(rows) < 3 or not stable:
            reason = ("位于图片或版面无稳定列边界" if len(rows) < 3
                      else "列数不一致（疑似正文串栏）")
            stats["unparsed_tables"].append(
                {"label": c["label"], "page": c["page"], "reason": reason})
            tables.append(_stub_table(c, reason + "；坐标与版面两条路径均未得到稳定栅格"))
            continue
        rows = [r for r in rows if len(r) == mode_cols]
        tables.append({
            "id": "tbl-" + c["id"], "page": c["page"], "label": c["label"],
            "caption_id": c["id"], "n_rows": len(rows), "n_cols": mode_cols,
            "header": rows[0], "rows": rows[1:],
            "cell_confidence": "medium",
            "extraction": "layout-gap",
            "notes": notes[:3],
            "evidence": {"page": c["page"], "caption_id": c["id"]},
            "limitation": "单元格由版面空白切分得到；合并单元格与多层表头需人工确认",
        })
    return tables


def build_references(paragraphs: list[dict], stats: dict) -> list[dict]:
    """定位参考文献区并切条目。切不动的整段保留为一条并记原因。"""
    start = None
    for i, p in enumerate(paragraphs):
        if p["is_heading"] and re.match(r"^\s*(references?|参考文献)", p["text"], re.I):
            start = i
            break
    if start is None:
        stats["reference_section"] = None
        return []
    seg = paragraphs[start + 1:]
    # 参考文献之后若还有致谢/附录，截断
    for j, p in enumerate(seg):
        if p["is_heading"] and re.match(r"^\s*(supplementary|appendix|附录|acknowledg|致谢)",
                                        p["text"], re.I):
            seg = seg[:j]
            break
    entries, cur = [], None
    for p in seg:
        t = p["text"].strip()
        if not t:
            continue
        m = _REF_ENTRY.match(t)
        if m:
            if cur:
                entries.append(cur)
            cur = {"paragraph_id": p["id"], "page": p["page"], "raw": t,
                   "index": (m.group("n") or m.group("n2")) or None}
        elif cur:
            cur["raw"] = (cur["raw"] + " " + t)[:1200]
        else:
            cur = {"paragraph_id": p["id"], "page": p["page"], "raw": t,
                   "index": None}
    if cur:
        entries.append(cur)

    out = []
    for k, e in enumerate(entries, 1):
        raw = re.sub(r"^\s*\[?\d{1,3}\]?[.)]?\s*", "", e["raw"]).strip()
        year = re.search(r"\b(19|20)\d{2}\b", raw)
        doi = _DOI.search(raw)
        # 第一作者姓：条目开头到第一个逗号/句点
        au = re.match(r"^([A-Z][A-Za-z'\-]{1,24})", raw)
        out.append({
            "id": f"ref-{k:03d}",
            "index": e["index"] or str(k),
            "raw": raw[:600],
            "first_author": au.group(1) if au else None,
            "year": int(year.group(0)) if year else None,
            "doi": doi.group(1) if doi else None,
            "paragraph_id": e["paragraph_id"],
            "page": e["page"],
            "parse_confidence": "high" if (au and year) else "low",
        })
    stats["reference_entries"] = len(out)
    stats["reference_unparsed"] = sum(1 for o in out if not o["first_author"])
    return out


def build_footnotes(paragraphs: list[dict]) -> list[dict]:
    out = []
    rx = re.compile(r"^\s*(?:[*†‡§¶]|\d{1,2})\s*[.)]?\s+\S")
    for p in paragraphs:
        t = p["text"].strip()
        if len(t) <= 240 and rx.match(t) and not p["is_heading"]:
            if re.search(r"(corresponding author|e-?mail|@|基金|资助|收稿)", t, re.I):
                out.append({"id": "fn-" + p["id"], "page": p["page"],
                            "text": t, "paragraph_id": p["id"],
                            "kind": "author_note"})
    return out


_JOURNAL_LABEL = re.compile(
    r"^\s*(?:research article|original article|review article|full paper|"
    r"research paper|communication|letter|article|review|perspective|"
    r"研究论文|综述|研究快报)\s*[:：]?\s*", re.I)
_BAD_TITLE = re.compile(
    r"(@|doi|correspondence|universit|institut|college|laborator|department|"
    r"school of|faculty|politecnico|academy|centre for|center for|"
    r"e-?mail|abstract|key\s?words|received|accepted|基金|通讯作者)", re.I)


def _clean_title_line(t: str) -> tuple[str, bool]:
    """从首页首段里剥出论文标题。返回 (标题, 是否做了可靠切分)。"""
    s = _JOURNAL_LABEL.sub("", t).strip()
    cut = False
    # 作者名紧跟其上标数字，或出现 " | " 分隔的一行作者
    m = re.search(r"\s+(?=[A-Z][a-zA-Z'\-]+(?:\s[A-Z][a-zA-Z'\-]+)?\s*[0-9*,†‡]{1,3}\b)", s)
    if m and m.start() >= 20:
        s, cut = s[:m.start()], True
    elif " | " in s:
        head = s.split(" | ")[0]
        if len(head) >= 20:
            s, cut = head, True
    return s.strip(), cut


def build_metadata(paragraphs: list[dict], captions: list[dict]) -> dict:
    head_paras = [p for p in paragraphs[:6] if not p["is_heading"]]
    title, title_conf, title_src = None, "low", None
    best = -1.0
    for pos, p in enumerate(head_paras):
        cand, cut = _clean_title_line(p["text"])
        if not (10 <= len(cand) <= 260):
            continue
        if _BAD_TITLE.search(cand):
            continue
        score = 0.0
        score += 1.0 if cut else 0.0
        score += 0.6 if 20 <= len(cand) <= 180 else 0.0
        upper = sum(1 for ch in cand if ch.isupper()) / max(1, len(cand))
        score += 0.4 if upper > 0.02 else 0.0
        score -= 0.8 if _CAP_RE.match(cand) else 0.0
        score += 0.5 * (1.0 - pos / max(1, len(head_paras)))   # 标题通常在首页最前
        if score > best:
            best, title, title_conf = score, cand, ("medium" if cut else "low")
            title_src = p["id"]
    authors, affil = None, None
    for p in head_paras:
        t = p["text"].strip()
        if authors is None and re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", t) and len(t) < 400 \
                and not re.search(r"abstract|摘要", t, re.I):
            if re.search(r"[,;]|\band\b|、|\d", t):
                authors = t[:400]
                continue
        if authors and affil is None and re.search(
                r"(universit|institut|college|laborator|大学|学院|研究所|实验)", t, re.I):
            affil = t[:400]
    abstract = None
    for i, p in enumerate(paragraphs):
        if p["is_heading"] and re.match(r"^\s*(abstract|摘要)", p["text"], re.I):
            if i + 1 < len(paragraphs):
                abstract = paragraphs[i + 1]["text"][:1600]
                abstract = {"text": abstract, "paragraph_id": paragraphs[i + 1]["id"],
                            "page": paragraphs[i + 1]["page"]}
            break
    kw = None
    for p in paragraphs[:40]:
        m = re.match(r"^\s*(?:key\s?words?|关键词)\s*[:：]\s*(.+)$", p["text"], re.I)
        if m:
            kw = [k.strip() for k in re.split(r"[;；,，]", m.group(1)) if k.strip()][:12]
            break
    doi = None
    for p in paragraphs[:20]:
        m = _DOI.search(p["text"])
        if m:
            doi = m.group(1)
            break
    return {"title": title, "title_confidence": title_conf,
            "title_paragraph_id": title_src,
            "authors": authors, "affiliations": affil,
            "abstract": abstract, "keywords": kw, "doi": doi,
            "figure_count": sum(1 for c in captions if c["kind"] == "figure"),
            "table_count": sum(1 for c in captions if c["kind"] == "table")}


# ---------------------------------------------------------------- 组装


def build(path: str, keep_hf: bool = False, probe_only: bool = False) -> dict:
    t0 = time.time()
    got = (backend_pypdf(path) or backend_pdftotext(path)
           or backend_builtin(path))
    if got is None:
        return {"error": "no backend could read this PDF",
                "file": os.path.basename(path), "status": "blocked"}
    if got.get("needs_pass"):
        return {"error": "pdf is encrypted and requires a password",
                "file": os.path.basename(path), "backend": got["backend"],
                "status": "blocked"}

    pages_text = got["pages_text"]
    stats = {"pages": len(pages_text), "empty_pages": [], "unreadable_pages": [],
             "removed_header_footer": 0, "unparsed_tables": [],
             "table_region_source": None, "reference_section": "searched",
             "reference_entries": 0, "reference_unparsed": 0}

    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()

    if probe_only:
        empt = [i + 1 for i, t in enumerate(pages_text) if len(t.strip()) < 20]
        return {"file": os.path.basename(path), "sha256": sha,
                "bytes": os.path.getsize(path),
                "backend": got["backend"], "encrypted": got.get("encrypted", False),
                "stats": {**stats, "unreadable_pages": empt,
                          "image_only_pages": empt,
                          "chars": sum(len(t) for t in pages_text)},
                "probe_only": True, "version": VERSION,
                "elapsed_ms": int((time.time() - t0) * 1000)}

    per_page_lines = [[l.strip() for l in t.split("\n") if l.strip()]
                      for t in pages_text]
    freq: dict[str, int] = {}
    for lines in per_page_lines:
        for ln in set(lines[:2] + lines[-2:]):
            if 0 < len(ln) <= 80:
                freq[ln] = freq.get(ln, 0) + 1
    repeat = {ln for ln, c in freq.items() if c >= max(3, len(pages_text) // 2)}
    stats["repeated_lines_dropped"] = sorted(repeat)[:10]

    paragraphs: list[dict] = []
    for pno, text in enumerate(pages_text, 1):
        kept = []
        for ln in text.split("\n"):
            s = ln.strip()
            if not keep_hf and (s in repeat or _PAGENO.match(s)):
                stats["removed_header_footer"] += 1
                continue
            kept.append(ln)
        page_text = "\n".join(kept)
        if len(page_text.strip()) < 20:
            stats["empty_pages"].append(pno)
            stats["unreadable_pages"].append(pno)
            continue
        chunks = [c.strip() for c in re.split(r"\n\s*\n+", norm(page_text)) if c.strip()]
        if len(chunks) <= 1:
            chunks = reflow(page_text)
        seq = 0
        for c in chunks:
            c = c.strip()
            if len(c) < 2:
                continue
            head, rest = split_leading_heading(c)
            if head:
                paragraphs.append({"id": f"p{pno:03d}-{seq + 1:02d}", "page": pno,
                                   "seq": seq, "text": head, "is_heading": True,
                                   "confidence": 0.9})
                seq += 1
                c = rest
            is_cap = bool(_CAP_RE.match(c))
            paragraphs.append({"id": f"p{pno:03d}-{seq + 1:02d}", "page": pno,
                               "seq": seq, "text": c,
                               "is_heading": is_heading(c),
                               "is_caption": is_cap,
                               "confidence": 0.95 if got["backend"] == "pypdf" else 0.75})
            seq += 1

    pos = 0
    for p in paragraphs:
        p["char_start"] = pos
        p["char_end"] = pos + len(p["text"])
        pos = p["char_end"] + 2

    sections = build_sections(paragraphs)
    attach_section(paragraphs, sections)
    captions = build_captions(paragraphs)
    for c in captions:
        for p in paragraphs:
            if p["id"] == c["paragraph_id"]:
                p["kind"] = c["kind"] + "_caption"
                break
    tables = build_tables(path, captions, stats, got.get("pages_chunks"))
    references = build_references(paragraphs, stats)
    footnotes = build_footnotes(paragraphs)
    metadata = build_metadata(paragraphs, captions)

    plain = "\n\n".join(p["text"] for p in paragraphs)
    stats.update({
        "chars": len(plain),
        "paragraphs": len(paragraphs),
        "headings": len(sections),
        "captions": len(captions),
        "tables_parsed": len(tables),
        "tables_unparsed": len(stats["unparsed_tables"]),
        "footnotes": len(footnotes),
        "readable_ratio": round(
            (len(pages_text) - len(stats["unreadable_pages"])) / max(1, len(pages_text)), 3),
    })

    return {
        "tool": "doctext", "version": VERSION,
        "file": os.path.basename(path), "sha256": sha,
        "bytes": os.path.getsize(path),
        "backend": got["backend"], "encrypted": got.get("encrypted", False),
        "stats": stats, "metadata": metadata,
        "sections": sections, "paragraphs": paragraphs,
        "captions": captions, "tables": tables,
        "references": references, "footnotes": footnotes,
        "plain_text": plain,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="科研 PDF → 可回查结构化文档模型")
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true", help="只探查版式与文字层")
    ap.add_argument("--keep-header-footer", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(a.pdf):
        print(json.dumps({"error": "file not found", "path": a.pdf},
                         ensure_ascii=False))
        return 2
    doc = build(a.pdf, keep_hf=a.keep_header_footer, probe_only=a.probe)
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    st = doc.get("stats", {})
    print(json.dumps({
        "backend": doc.get("backend"), "error": doc.get("error"),
        "pages": st.get("pages"), "paragraphs": st.get("paragraphs"),
        "headings": st.get("headings"), "captions": st.get("captions"),
        "tables": st.get("tables_parsed"),
        "references": st.get("reference_entries"),
        "unreadable_pages": st.get("unreadable_pages"),
        "elapsed_ms": doc.get("elapsed_ms"), "out": out,
    }, ensure_ascii=False))
    return 0 if "error" not in doc else 1


if __name__ == "__main__":
    sys.exit(main())
