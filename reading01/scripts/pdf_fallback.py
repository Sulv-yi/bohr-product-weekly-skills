#!/usr/bin/env python3
"""纯标准库 PDF 文本兜底解析（无任何第三方依赖）。

当 PyMuPDF / pdfplumber / pypdf / pdftotext 均不可用时，直接解析 PDF 结构：
  1. 定位所有 page 对象，取 Contents 流引用；
  2. 对内容流做 FlateDecode（zlib）解压；
  3. 扫描 BT..ET 文本块，提取 Tj / TJ / ' / " 操作符的字符串；
  4. 用 Td / TD / Tm / T* 的位置信息估算行 y 坐标，按页内 y 排序输出文本行。

限制（在输出中如实声明）：
  - 不处理字体编码映射（CID / ToUnicode），对子集嵌入字体的中文/特殊符号可能显示为原始码；
  - 不做版面坐标还原，bbox 为估算值；不识别表格结构与图片；
  - 仅保证「有文字层的 PDF 至少能提取出可定位的文本行」，不冒充精确解析。

本模块被 probe_pdf.py / extract_blocks.py 作为最后一级后端调用。
"""
import re
import zlib


def _objects(data: bytes):
    """返回 {obj_num: raw_object_bytes}。"""
    objs = {}
    for m in re.finditer(rb'(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj', data, re.S):
        objs[int(m.group(1))] = m.group(3)
    return objs


def _stream(obj: bytes):
    """取对象的流数据，必要时 FlateDecode。"""
    m = re.search(rb'stream\r?\n(.*?)\r?\nendstream', obj, re.S)
    if not m:
        return b""
    raw = m.group(1)
    if b'FlateDecode' in obj[:m.start()]:
        try:
            return zlib.decompress(raw)
        except Exception:
            try:
                return zlib.decompressobj().decompress(raw)
            except Exception:
                return b""
    return raw


def _unescape(s: bytes) -> bytes:
    """反转义 PDF 字符串中的 \\n \\r \\t \\( \\) \\\\ 与八进制。"""
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == 0x5c and i + 1 < len(s):
            n = s[i + 1]
            mp = {0x6e: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
            if n in mp:
                out.append(mp[n]); i += 2; continue
            if 0x30 <= n <= 0x37:
                j = i + 1
                octal = bytearray()
                while j < len(s) and len(octal) < 3 and 0x30 <= s[j] <= 0x37:
                    octal.append(s[j]); j += 1
                out.append(int(octal, 8) & 0xFF); i = j; continue
            out.append(n); i += 2; continue
        out.append(c); i += 1
    return bytes(out)


def _strings_in_content(content: bytes):
    """从内容流提取 (x, y, text) 行片段。"""
    rows = []
    cur_y = None
    # 文本定位操作符：Td / TD / Tm / T*
    pos_re = re.compile(rb'(?:(-?[\d.]+)\s+(-?[\d.]+)\s+(?:Td|TD))|'
                        rb'(?:(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+'
                        rb'(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+Tm)|'
                        rb'(T\*)', re.S)
    # 文本显示操作符：字面串 (...) 与十六进制串 <...> 都要支持
    # 中文子集字体普遍用 <0440> 形式，若只认 (...) 会提取到空文本。
    str_atom = rb'(?:\(((?:\\.|[^\\()])*)\)|<([0-9A-Fa-f\s]+)>)'
    show_re = re.compile(
        str_atom + rb'\s*(Tj|\'|")|'
        rb'\[((?:[^\[\]]|\\.)*)\]\s*TJ', re.S)

    def _hex_bytes(h: bytes) -> bytes:
        h = re.sub(rb'\s', b'', h)
        if len(h) % 2:
            h += b'0'
        try:
            return bytes.fromhex(h.decode('ascii'))
        except Exception:
            return b""

    def _decode_atom(g_lit, g_hex):
        if g_lit is not None:
            return _unescape(g_lit)
        if g_hex is not None:
            return _hex_bytes(g_hex)
        return b""

    tokens = []
    for m in pos_re.finditer(content):
        if m.group(5):
            y = float(m.group(5))
        elif m.group(1):
            y = float(m.group(2))
        else:
            continue
        tokens.append((m.start(), 'pos', y))
    for m in show_re.finditer(content):
        if m.group(1) is not None or m.group(2) is not None:
            txt = _decode_atom(m.group(1), m.group(2))
        else:
            arr = m.group(4) or b""
            parts = []
            for am in re.finditer(str_atom, arr):
                parts.append(_decode_atom(am.group(1), am.group(2)))
            txt = b"".join(parts)
        tokens.append((m.start(), 'text', txt))
    tokens.sort(key=lambda t: t[0])

    buf = []
    for _, kind, val in tokens:
        if kind == 'pos':
            if buf:
                rows.append((cur_y if cur_y is not None else 0, b"".join(buf)))
                buf = []
            cur_y = val
        else:
            buf.append(val)
    if buf:
        rows.append((cur_y if cur_y is not None else 0, b"".join(buf)))
    return rows


def parse(path: str):
    """返回 (pages, rows_per_page)。pages 为页数估值。"""
    with open(path, 'rb') as f:
        data = f.read()
    objs = _objects(data)
    # 页对象：/Type /Page（排除 /Pages）
    page_objs = []
    for num, obj in objs.items():
        if re.search(rb'/Type\s*/Page\b', obj):
            page_objs.append((num, obj))
    if not page_objs:
        # 退化：把整份文件当一个内容流
        return 1, [_strings_in_content(data)]

    # 按对象号排序作为页序近似
    page_objs.sort(key=lambda x: x[0])
    result = []
    for num, obj in page_objs:
        streams = []
        # 直接 /Contents N 0 R
        for m in re.finditer(rb'/Contents\s+(\d+)\s+\d+\s+R', obj):
            ref = int(m.group(1))
            if ref in objs:
                streams.append(_stream(objs[ref]))
        # /Contents [ ... ]
        mm = re.search(rb'/Contents\s*\[(.*?)\]', obj, re.S)
        if mm:
            for r in re.finditer(rb'(\d+)\s+\d+\s+R', mm.group(1)):
                ref = int(r.group(1))
                if ref in objs:
                    streams.append(_stream(objs[ref]))
        content = b"\n".join(streams) if streams else b""
        result.append(_strings_in_content(content))
    return len(result), result


def probe(path: str):
    """给 probe_pdf.py 用的版式探测结果。"""
    pages, per = parse(path)
    stats = []
    for i, rows in enumerate(per, 1):
        chars = sum(len(t.decode('latin-1', 'replace')) for _, t in rows)
        stats.append({
            "page": i,
            "char_count": chars,
            "block_count": len(rows),
            "image_count": 0,
            "width": 0,
            "height": 0,
        })
    return {
        "backend": "stdlib-fallback",
        "limitations": "no font/CID mapping, no layout bbox, no table/image parsing",
        "pages": pages,
        "page_stats": stats,
        "column_hint": [1] * pages,
        "image_only_pages": [],
        "encrypted": False,
        "needs_pass": False,
    }


def blocks(path: str, mode: str = "reading"):
    """给 extract_blocks.py 用的块列表。"""
    pages, per = parse(path)
    out = []
    for pno, rows in enumerate(per, 1):
        rows = sorted(rows, key=lambda r: (-r[0]))
        for i, (y, raw) in enumerate(rows, 1):
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('latin-1', 'replace')
            text = re.sub(r'\s+', ' ', text).strip()
            if not text:
                continue
            out.append({
                "id": f"p{pno:03d}-b{i:03d}",
                "page": pno,
                "bbox": [0, round(float(y), 1), 0, round(float(y), 1)],
                "text": text,
                "column": 1,
                "font_size": 0,
                "source": "stdlib-fallback",
            })
    return out


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("usage: pdf_fallback.py <pdf> [probe|blocks]")
        raise SystemExit(2)
    mode = sys.argv[2] if len(sys.argv) > 2 else "probe"
    result = probe(sys.argv[1]) if mode == "probe" else blocks(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=1))
