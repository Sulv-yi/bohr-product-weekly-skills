#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdfmini —— 纯标准库 PDF 文字层解析器。

目标不是做完整 PDF 实现，而是在**没有 pypdf / poppler 的环境里**仍然拿到
可排版、可定位的文字块，供 doctext 建段落、切章节、拼表格。

覆盖：
  1. 对象表 + 对象流（/ObjStm）展开，压缩流 FlateDecode；
  2. 按页面树（/Pages /Kids）还原**真实页序**（不是对象号顺序）；
  3. 每页 /Resources /Font 独立解析，字体各自带 ToUnicode，不跨字体混用；
  4. 文字矩阵（Tm/Td/TD/T*/TL/Tf）跟踪，输出带 (x, y, size) 的文字块；
  5. 词间距：TJ 数值位移与相邻块的几何间隙都转成空格；
  6. 双栏阅读顺序：用横向空白找栏缝，整幅跨栏元素作为分段边界。

明确不做：图片、矢量图形、加密解密、扫描件 OCR、字体子集反嵌。
遇到这些情况由上层如实标注，而不是猜。
"""

from __future__ import annotations

import re
import zlib

__version__ = "1.0"

# ------------------------------------------------------------------ 对象层

_OBJ_HDR = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")


def _split_objects(data: bytes) -> dict:
    """obj 号 → {dict: bytes, raw: bytes|None}。只做粗切，不做 xref 校验。"""
    objs: dict[int, dict] = {}
    for m in _OBJ_HDR.finditer(data):
        num = int(m.group(1))
        start = m.end()
        end = data.find(b"endobj", start)
        if end < 0:
            continue
        body = data[start:end]
        si = body.find(b"stream")
        if si >= 0:
            dic = body[:si]
            s = si + 6
            if body[s:s + 2] == b"\r\n":
                s += 2
            elif body[s:s + 1] in (b"\n", b"\r"):
                s += 1
            ei = body.rfind(b"endstream")
            raw = body[s:ei] if ei > s else body[s:]
            objs[num] = {"dict": dic, "raw": raw}
        else:
            objs[num] = {"dict": body, "raw": None}
    return objs


def _inflate(raw: bytes) -> bytes | None:
    for wbits in (15, -15, 47):
        try:
            return zlib.decompress(raw, wbits)
        except Exception:
            continue
    # 尾部缺字节时逐次截断重试
    for cut in (1, 2, 4, 8, 16, 32):
        try:
            return zlib.decompress(raw[:-cut], -15)
        except Exception:
            continue
    return None


def _decoded(objs: dict, num: int) -> bytes | None:
    o = objs.get(num)
    if not o or o["raw"] is None:
        return None
    raw = o["raw"]
    d = o["dict"]
    if b"FlateDecode" in d:
        out = _inflate(raw)
        if out is None:
            return None
        return out
    if b"Filter" in d:          # 其它滤镜（DCT/JPX/LZW）不支持
        return None
    return raw


def _expand_objstm(objs: dict) -> None:
    """把对象流里的对象摊平进 objs，页树与字体常藏在这里。"""
    for num in list(objs):
        d = objs[num]["dict"]
        if b"/ObjStm" not in d:
            continue
        data = _decoded(objs, num)
        if not data:
            continue
        m_n = re.search(rb"/N\s+(\d+)", d)
        m_f = re.search(rb"/First\s+(\d+)", d)
        if not (m_n and m_f):
            continue
        n, first = int(m_n.group(1)), int(m_f.group(1))
        head = data[:first].split()
        try:
            pairs = [(int(head[i]), int(head[i + 1])) for i in range(0, min(len(head), 2 * n), 2)]
        except Exception:
            continue
        for idx, (onum, off) in enumerate(pairs):
            if onum in objs:
                continue
            end = pairs[idx + 1][1] if idx + 1 < len(pairs) else len(data) - first
            body = data[first + off: first + end]
            objs[onum] = {"dict": body, "raw": None}


def _refnum(dic: bytes, key: bytes) -> int | None:
    m = re.search(rb"/" + key + rb"\s+(\d+)\s+\d+\s+R", dic)
    return int(m.group(1)) if m else None


def _inline_subdict(dic: bytes, key: bytes) -> bytes | None:
    """取 `/Key << ... >>` 的内联字典（含嵌套）。"""
    m = re.search(rb"/" + key + rb"\s*<<", dic)
    if not m:
        return None
    i = m.end() - 2
    depth = 0
    for j in range(i, len(dic) - 1):
        if dic[j:j + 2] == b"<<":
            depth += 1
        elif dic[j:j + 2] == b">>":
            depth -= 1
            if depth == 0:
                return dic[i:j + 2]
    return None


def _resolve(objs: dict, dic: bytes, key: bytes) -> bytes | None:
    n = _refnum(dic, key)
    if n is not None:
        o = objs.get(n)
        if not o:
            return None
        return _decoded(objs, n) if o["raw"] is not None else o["dict"]
    return _inline_subdict(dic, key)


# ------------------------------------------------------------------ 页面树

def _is_type(dic: bytes, kind: bytes) -> bool:
    return re.search(rb"/Type\s*/" + kind + rb"(?![A-Za-z])", dic) is not None


def _pages(objs: dict) -> list[bytes]:
    """按 /Kids 顺序返回页面字典。"""
    roots = [n for n, o in objs.items()
             if _is_type(o["dict"], b"Pages") and not re.search(rb"/Parent\s+\d+", o["dict"])]
    if not roots:  # 没有单根时，退到任意 Pages
        roots = [n for n, o in objs.items() if _is_type(o["dict"], b"Pages")]
    out: list[bytes] = []
    seen: set[int] = set()

    def walk(num: int, depth: int = 0) -> None:
        if num in seen or depth > 32:
            return
        seen.add(num)
        o = objs.get(num)
        if not o:
            return
        dic = o["dict"]
        if _is_type(dic, b"Page"):
            out.append(dic)
            return
        kids = _inline_kids(dic)
        for k in kids:
            walk(k, depth + 1)

    def _inline_kids(dic: bytes) -> list[int]:
        m = re.search(rb"/Kids\s*\[(.*?)\]", dic, re.S)
        if not m:
            return []
        return [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1))]

    for r in roots:
        walk(r)
    return out


# ------------------------------------------------------------------ 字体

def _font_table(objs: dict, page_dic: bytes) -> dict:
    """资源里 /Font << /F1 .. >> → {名字: {cmap, two_byte, widths, first_char, size_hint}}"""
    res = _resolve(objs, page_dic, b"Resources")
    if res is None:
        res = _inline_subdict(page_dic, b"Resources")
    if not res:
        return {}
    fonts = _inline_subdict(res, b"Font")
    if not fonts:
        fr = _refnum(res, b"Font")
        if fr is not None:
            fonts = objs.get(fr, {}).get("dict")
    if not fonts:
        return {}

    table: dict[str, dict] = {}
    for name, num in re.findall(rb"/([A-Za-z0-9_.+-]+)\s+(\d+)\s+\d+\s+R", fonts):
        fo = objs.get(int(num))
        if not fo:
            continue
        fd = fo["dict"]
        info = {"cmap": {}, "two_byte": False, "widths": {}, "first": 0, "width": None}
        if b"/Type0" in fd:
            info["two_byte"] = True
        tu = _refnum(fd, b"ToUnicode")
        if tu is not None:
            body = _decoded(objs, tu)
            if body:
                info["cmap"] = _parse_cmap(body)
        fc = re.search(rb"/FirstChar\s+(\d+)", fd)
        if fc:
            info["first"] = int(fc.group(1))
        wm = re.search(rb"/Widths\s*\[(.*?)\]", fd, re.S)
        if wm:
            ws = [int(float(x)) for x in re.findall(rb"-?\d+(?:\.\d+)?", wm.group(1))]
            for i, w in enumerate(ws):
                info["widths"][info["first"] + i] = w
        # Type0 的宽度在 /DescendantFonts 的 /W 里（CID → 宽度）
        if info["two_byte"] and not info["widths"]:
            desc = None
            dn = _refnum(fd, b"DescendantFonts")
            if dn is not None:
                body = _decoded(objs, dn) or objs.get(dn, {}).get("dict") or b""
                r = re.search(rb"(\d+)\s+\d+\s+R", body)
                if r:
                    dnum = int(r.group(1))
                    dob = objs.get(dnum)
                    desc = dob["dict"] if dob else None
            if desc:
                dw = re.search(rb"/DW\s+(\d+)", desc)
                if dw:
                    info["width"] = int(dw.group(1))
                wm2 = re.search(rb"/W\s*\[(.*?)\]\s*(?:/|>>)", desc, re.S)
                if wm2:
                    info["widths"] = _parse_w(wm2.group(1))
        if info["two_byte"] and not info["width"]:
            info["width"] = 1000
        table[name.decode("latin-1")] = info
    return table


def _parse_w(body: bytes) -> dict:
    """解析 /W 数组：`c [w1 w2 ...]` 与 `c1 c2 w` 两种写法。"""
    out: dict[int, float] = {}
    tokens = re.findall(rb"\[|\]|-?\d+(?:\.\d+)?", body)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == b"[":
            i += 1
            continue
        try:
            first = int(float(t))
        except Exception:
            i += 1
            continue
        # 形式一：c [w...]
        if i + 1 < len(tokens) and tokens[i + 1] == b"[":
            i += 2
            idx = first
            while i < len(tokens) and tokens[i] != b"]":
                try:
                    out[idx] = float(tokens[i])
                except Exception:
                    pass
                idx += 1
                i += 1
            i += 1
            continue
        # 形式二：c1 c2 w
        if i + 2 < len(tokens):
            try:
                last = int(float(tokens[i + 1]))
                w = float(tokens[i + 2])
            except Exception:
                i += 1
                continue
            if 0 <= last - first <= 65535:
                for c in range(first, last + 1):
                    out[c] = w
            i += 3
            continue
        i += 1
    return out


def _parse_cmap(body: bytes) -> dict:
    table: dict[int, str] = {}
    txt = body.decode("latin-1", "replace")
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
            for i in range(min(hi - lo, 8192) + 1):
                try:
                    table[lo + i] = chr(dst + i)
                except Exception:
                    break
    return table


# ------------------------------------------------------------------ 内容流

_TOK = re.compile(
    rb"(?P<str>\((?:\\.|[^\\()])*\))"          # 字面串
    rb"|(?P<hex><[0-9A-Fa-f\s]*>)"             # 十六进制串
    rb"|(?P<name>/[^\s/<>\[\](){}%]*)"         # 名字
    rb"|(?P<num>-?\d*\.?\d+)"                  # 数字
    rb"|(?P<arr>[\[\]])"                       # 数组界
    rb"|(?P<op>[A-Za-z*'\"]+)"                 # 操作符
    rb"|(?P<ws>\s+)", re.S)


def _unescape(b: bytes) -> bytes:
    out, i = bytearray(), 0
    mp = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12,
          0x28: 40, 0x29: 41, 0x5C: 92}
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):
            n = b[i + 1]
            if n in mp:
                out.append(mp[n]); i += 2; continue
            m = re.match(rb"[0-7]{1,3}", b[i + 1:i + 4])
            if m:
                out.append(int(m.group(0), 8) & 0xFF)
                i += 1 + len(m.group(0)); continue
            i += 2; continue
        out.append(c); i += 1
    return bytes(out)


def _set_matrix(a, b, c, d, e, f):
    return (a, b, c, d, e, f)


def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def _fs(tm, size: float) -> float:
    """有效字号：Tf 给出的字号要乘上文本矩阵的缩放。"""
    try:
        scale = (abs(tm[0] * tm[3] - tm[1] * tm[2])) ** 0.5 or 1.0
    except Exception:
        scale = 1.0
    return round(float(size) * scale, 2)


def _decode(payload: bytes, font: dict) -> tuple[str, float]:
    """返回 (文字, 宽度占位 em 数)。"""
    cmap = font.get("cmap") or {}
    two = font.get("two_byte")
    widths = font.get("widths") or {}
    total = 0.0
    out = []
    if two:
        codes = [(payload[i] << 8) | payload[i + 1] for i in range(0, len(payload) - 1, 2)]
    else:
        codes = list(payload)
    for code in codes:
        ch = cmap.get(code)
        if ch is None:
            if two:
                ch = ""
            else:
                ch = chr(code) if 32 <= code < 127 else ""
        out.append(ch)
        total += widths.get(code, font.get("width") or (1000 if two else 500)) / 1000.0
    return "".join(out), total


def page_chunks(objs: dict, page_dic: bytes) -> list[dict]:
    """一页的文字块，带 (x, y, size)。"""
    contents: list[int] = []
    cn = _refnum(page_dic, b"Contents")
    if cn is not None:
        contents = [cn]
    else:
        m = re.search(rb"/Contents\s*\[(.*?)\]", page_dic, re.S)
        if m:
            contents = [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1))]
    if not contents:
        return []
    blob = b""
    for c in contents:
        got = _decoded(objs, c)
        if got:
            blob += got + b"\n"
    if not blob:
        return []

    fonts = _font_table(objs, page_dic)
    cur = {"font": {"cmap": {}, "two_byte": False, "widths": {}, "width": 500},
           "size": 10.0}
    tm = tlm = (1, 0, 0, 1, 0, 0)
    leading = 0.0
    chunks: list[dict] = []
    pend: list[str] = []

    def flush(x, y, size):
        if pend:
            txt = "".join(pend)
            pend.clear()
            if txt.strip():
                chunks.append({"x": round(x, 1), "y": round(y, 1),
                               "size": round(size, 1), "text": txt})

    stack: list = []
    op = None
    for m in _TOK.finditer(blob):
        kind = m.lastgroup
        tok = m.group(0)
        if kind == "ws":
            continue
        if kind == "num":
            stack.append(float(tok))
            continue
        if kind == "str":
            stack.append(("str", _unescape(tok[1:-1])))
            continue
        if kind == "hex":
            h = re.sub(rb"\s", b"", tok[1:-1])
            if len(h) % 2:
                h += b"0"
            try:
                stack.append(("str", bytes.fromhex(h.decode("ascii"))))
            except Exception:
                stack.append(("str", b""))
            continue
        if kind == "name":
            stack.append(("name", tok[1:].decode("latin-1", "replace")))
            continue
        if kind == "arr":
            if tok == b"[":
                stack.append(("arr", []))
            else:
                items = []
                while stack and not (isinstance(stack[-1], tuple) and stack[-1][0] == "arr"):
                    items.append(stack.pop())
                if stack:
                    stack.pop()
                stack.append(("arr", list(reversed(items))))
            continue
        # 操作符
        op = tok.decode("latin-1")
        if op == "BT":
            tm = tlm = (1, 0, 0, 1, 0, 0)
            stack.clear()
        elif op == "Tm" and len(stack) >= 6:
            vals = [v for v in stack[-6:] if isinstance(v, float)]
            if len(vals) == 6:
                tm = tlm = _set_matrix(*vals)
                flush(tm[4], tm[5], _fs(tm, cur["size"]))
            stack.clear()
        elif op in ("Td", "TD") and len(stack) >= 2:
            tx, ty = [v for v in stack[-2:] if isinstance(v, float)][:2]
            tlm = _mul((1, 0, 0, 1, tx, ty), tlm)
            tm = tlm
            if op == "TD":
                leading = -ty
            flush(tm[4], tm[5], _fs(tm, cur["size"]))
            stack.clear()
        elif op == "T*":
            tlm = _mul((1, 0, 0, 1, 0, -leading), tlm)
            tm = tlm
            flush(tm[4], tm[5], _fs(tm, cur["size"]))
            stack.clear()
        elif op == "TL" and stack:
            vals = [v for v in stack if isinstance(v, float)]
            if vals:
                leading = vals[-1]
            stack.clear()
        elif op == "Tf" and len(stack) >= 2:
            name = None
            size = None
            for v in reversed(stack):
                if isinstance(v, tuple) and v[0] == "name" and name is None:
                    name = v[1]
                elif isinstance(v, float) and size is None:
                    size = v
            if name is not None:
                cur["font"] = fonts.get(name, cur["font"])
            if size:
                cur["size"] = size
            flush(tm[4], tm[5], _fs(tm, cur["size"]))
            stack.clear()
        elif op in ("Tj", "TJ", "'", '"'):
            if op in ("'", '"'):
                tlm = _mul((1, 0, 0, 1, 0, -leading), tlm)
                tm = tlm
            items = []
            if stack:
                last = stack[-1]
                if isinstance(last, tuple) and last[0] == "arr":
                    items = last[1]
                elif isinstance(last, tuple) and last[0] == "str":
                    items = [last]
            x, y = tm[4], tm[5]
            flush(x, y, _fs(tm, cur["size"]))
            adv = 0.0
            for it in items:
                if isinstance(it, tuple) and it[0] == "str":
                    txt, w = _decode(it[1], cur["font"])
                    step = w * _fs(tm, cur["size"])
                    if txt:
                        chunks.append({"x": round(x + adv, 1), "y": round(y, 1),
                                       "size": _fs(tm, cur["size"]), "text": txt,
                                       "w": round(step, 2)})
                    adv += step
                elif isinstance(it, float):
                    move = -it / 1000.0 * _fs(tm, cur["size"])
                    if -it >= 220:      # TJ 位移达到约 0.22em，语义上是词间距
                        chunks.append({"x": round(x + adv, 1), "y": round(y, 1),
                                       "size": _fs(tm, cur["size"]), "text": " ",
                                       "w": round(move, 2)})
                    adv += move
            tm = (tm[0], tm[1], tm[2], tm[3], x + adv, y)
            stack.clear()
        elif op == "ET":
            flush(tm[4], tm[5], _fs(tm, cur["size"]))
            stack.clear()
        else:
            # 其它操作符（g/rg/cm/Do/q/Q/BT 等）不参与文字，清栈防串
            if op in ("q", "Q", "cm", "re", "m", "l", "c", "v", "y", "h", "S", "s",
                      "f", "F", "f*", "B", "B*", "b", "b*", "n", "W", "W*", "Do",
                      "gs", "g", "G", "rg", "RG", "k", "K", "cs", "CS", "sc", "SC",
                      "scn", "SCN", "sh", "d", "w", "J", "j", "M", "i", "ri"):
                stack.clear()
    flush(tm[4], tm[5], _fs(tm, cur["size"]))
    return _merge(chunks)


def _merge(chunks: list[dict]) -> list[dict]:
    """同一行相邻且间隙很小的块合并，避免逐字成为独立块。"""
    out: list[dict] = []
    for c in chunks:
        if out:
            p = out[-1]
            same_line = abs(p["y"] - c["y"]) <= max(2.0, 0.5 * c["size"])
            gap = c["x"] - (p["x"] + _width(p))
            if c["text"] == " " and same_line and -6 <= gap <= max(6.0, 0.6 * c["size"]):
                p["text"] += " "
                p["w"] = round((p.get("w") or _width(p)) + max(gap, 0) + _width(c), 2)
                continue
            if same_line and -6 <= gap <= max(2.0, 0.3 * c["size"]):
                sep = ""
                if gap > max(1.2, 0.14 * c["size"]) and not p["text"].endswith(" ") \
                        and not c["text"].startswith(" "):
                    sep = " "
                p["text"] += sep + c["text"]
                p["w"] = round(_width(p), 2) if not p.get("w") else round(p["w"] + max(gap, 0) + _width(c), 2)
                continue
        out.append(dict(c))
    return out


def _width(chunk: dict) -> float:
    """优先用解析时的实测推进宽度，缺失时按字符类别估。"""
    if chunk.get("w"):
        return float(chunk["w"])
    w = 0.0
    for ch in chunk["text"]:
        w += chunk["size"] * (1.0 if ord(ch) > 0x2E80 else 0.5)
    return w


# ------------------------------------------------------------------ 版面

def _lines(chunks: list[dict]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for c in sorted(chunks, key=lambda c: (-c["y"], c["x"])):
        if rows and abs(rows[-1][0]["y"] - c["y"]) <= max(2.2, 0.62 * c["size"]):
            rows[-1].append(c)
        else:
            rows.append([c])
    for r in rows:
        r.sort(key=lambda c: c["x"])
    if len(rows) > 2:
        sizes = sorted(c["size"] for r in rows for c in r)
        body = sizes[len(sizes) // 2] or 10.0
        keep: list[list[dict]] = []
        for r in rows:
            txt = "".join(c["text"] for c in r).strip()
            is_mark = re.fullmatch(r"[\d,\-–\s]{1,12}", txt or "x") is not None
            if is_mark and keep:
                ty = r[0]["y"]
                best = min(range(len(keep)), key=lambda i: abs(keep[i][0]["y"] - ty))
                if abs(keep[best][0]["y"] - ty) <= 1.2 * body:
                    keep[best].extend(r)
                    keep[best].sort(key=lambda c: c["x"])
                    continue
            keep.append(r)
        rows = keep
    return rows


def _line_text(row: list[dict]) -> str:
    parts, prev_end = [], None
    for c in row:
        t = c["text"]
        if not t:
            continue
        if prev_end is not None:
            gap = c["x"] - prev_end
            if gap > max(1.2, 0.22 * c["size"]) and not t.startswith(" "):
                parts.append(" ")
        parts.append(t)
        prev_end = c["x"] + _width(c)
    return re.sub(r"[ \t]{2,}", " ", "".join(parts)).strip()


def _column_split(chunks: list[dict]) -> float | None:
    """找栏缝：统计每行内部的大间隙，取在多数行都出现的那条竖缝。

    比"整页横向空白"稳：整幅图题、跨栏标题会把空白填掉，但每一行自己的
    栏缝位置是一致的。
    """
    if len(chunks) < 24:
        return None
    rows = _lines(chunks)
    if len(rows) < 6:
        return None
    lo = min(c["x"] for c in chunks)
    hi = max(c["x"] + _width(c) for c in chunks)
    span = hi - lo
    if span < 200:
        return None
    votes: dict[int, int] = {}
    for r in rows:
        for a, b in zip(r, r[1:]):
            gap = b["x"] - (a["x"] + _width(a))
            if gap < 6:
                continue
            mid = a["x"] + _width(a) + gap / 2
            if not (lo + 0.28 * span <= mid <= lo + 0.72 * span):
                continue
            key = int(round(mid / 4.0))
            votes[key] = votes.get(key, 0) + 1
    if not votes:
        return None
    key, n = max(votes.items(), key=lambda kv: kv[1])
    if n < max(3, int(0.22 * len(rows))):
        return None
    split = key * 4.0
    left = sum(1 for c in chunks if c["x"] + _width(c) <= split)
    right = sum(1 for c in chunks if c["x"] >= split)
    if left < 0.15 * len(chunks) or right < 0.15 * len(chunks):
        return None
    return split


def page_text(chunks: list[dict]) -> str:
    """按阅读顺序输出该页文本：双栏先左后右，整幅元素作分段。"""
    if not chunks:
        return ""
    split = _column_split(chunks)
    rows = _lines(chunks)
    if split is None:
        return "\n".join(_line_text(r) for r in rows if _line_text(r))

    out: list[str] = []
    left_acc: list[str] = []
    right_acc: list[str] = []

    def flush_region():
        out.extend(left_acc)
        out.extend(right_acc)
        left_acc.clear()
        right_acc.clear()

    for r in rows:
        wide, left, right = [], [], []
        for c in r:
            x0, x1 = c["x"], c["x"] + _width(c)
            if x0 < split - 8 and x1 > split + 8:
                wide.append(c)
            elif x1 <= split + 8:
                left.append(c)
            else:
                right.append(c)
        if wide:
            flush_region()
            txt = _line_text(sorted(wide, key=lambda c: c["x"]))
            if txt:
                out.append(txt)
            continue
        if left:
            left_acc.append(_line_text(sorted(left, key=lambda c: c["x"])))
        if right:
            right_acc.append(_line_text(sorted(right, key=lambda c: c["x"])))
    flush_region()
    return "\n".join(x for x in out if x)


# ------------------------------------------------------------------ 入口

def extract(path: str) -> dict | None:
    """返回 {pages_text, pages_chunks}；读不到文字层返回 None。"""
    with open(path, "rb") as fh:
        data = fh.read()
    objs = _split_objects(data)
    if not objs:
        return None
    _expand_objstm(objs)
    pages = _pages(objs)
    if not pages:
        return None
    texts, chunks_all = [], []
    for dic in pages:
        ch = page_chunks(objs, dic)
        chunks_all.append(ch)
        texts.append(page_text(ch))
    if not any(t.strip() for t in texts):
        return None
    return {"pages_text": texts, "pages_chunks": chunks_all}


if __name__ == "__main__":
    import json
    import sys
    got = extract(sys.argv[1])
    if not got:
        print(json.dumps({"error": "no text layer"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({"pages": len(got["pages_text"]),
                      "chars": sum(len(t) for t in got["pages_text"]),
                      "chunks": sum(len(c) for c in got["pages_chunks"])},
                     ensure_ascii=False))
