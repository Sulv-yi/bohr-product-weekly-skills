#!/usr/bin/env python3
"""带坐标的 PDF 文本块提取 + 阅读顺序修正。

用法: python extract_blocks.py <pdf> --out blocks.json [--mode reading|raw]
输出块数组: [{id,page,bbox,text,column,font_size,source}]
源统一为 pymupdf / pdfplumber / pdftotext。
"""
import sys
import json
import os
import argparse
import re


def extract_pymupdf(path, mode):
    import fitz
    doc = fitz.open(path)
    if doc.is_encrypted:
        try:
            doc.authenticate("")
        except Exception:
            pass
    blocks = []
    for pno in range(doc.page_count):
        page = doc[pno]
        page_w = page.rect.width
        mid = page_w / 2
        raw = page.get_text("dict").get("blocks", [])
        page_blocks = []
        for b in raw:
            if b.get("type") != 0:  # 0=文本, 1=图像
                continue
            x0, y0, x1, y1 = b["bbox"]
            spans = []
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    spans.append(s)
            text = "\n".join(
                "".join(s.get("text", "") for s in line.get("spans", []))
                for line in b.get("lines", [])
            ).strip()
            if not text:
                continue
            sizes = [s.get("size", 0) for s in spans]
            font_size = round(max(sizes), 1) if sizes else 0
            cx = (x0 + x1) / 2
            column = 0 if (x1 - x0) > page_w * 0.6 else (1 if cx < mid else 2)
            page_blocks.append({
                "bbox": [round(v, 1) for v in (x0, y0, x1, y1)],
                "text": text,
                "column": column,
                "font_size": font_size,
            })
        page_blocks = order_blocks(page_blocks, mode)
        for i, pb in enumerate(page_blocks, 1):
            pb["id"] = f"p{pno+1:03d}-b{i:03d}"
            pb["page"] = pno + 1
            pb["source"] = "pymupdf"
            blocks.append(pb)
    doc.close()
    return blocks


def extract_pdfplumber(path, mode):
    import pdfplumber
    blocks = []
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages):
            mid = page.width / 2
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            rows = {}
            for w in words:
                key = round(w["top"] / 3)
                rows.setdefault(key, []).append(w)
            page_blocks = []
            for key in sorted(rows):
                ws = sorted(rows[key], key=lambda x: x["x0"])
                line = " ".join(w["text"] for w in ws)
                x0 = min(w["x0"] for w in ws)
                x1 = max(w["x1"] for w in ws)
                y0 = min(w["top"] for w in ws)
                y1 = max(w["bottom"] for w in ws)
                cx = (x0 + x1) / 2
                column = 0 if (x1 - x0) > page.width * 0.6 else (1 if cx < mid else 2)
                size = round(max((w.get("height", 0) or 0) for w in ws), 1)
                page_blocks.append({
                    "bbox": [round(v, 1) for v in (x0, y0, x1, y1)],
                    "text": line.strip(), "column": column, "font_size": size,
                })
            page_blocks = order_blocks(page_blocks, mode)
            for i, pb in enumerate(page_blocks, 1):
                pb["id"] = f"p{pno+1:03d}-b{i:03d}"
                pb["page"] = pno + 1
                pb["source"] = "pdfplumber"
                blocks.append(pb)
    return blocks


def extract_pdftotext(path, mode):
    import subprocess
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True)
    pages = (out.stdout or "").split("\f")
    blocks = []
    for pno, page_text in enumerate(pages):
        for i, line in enumerate(page_text.splitlines(), 1):
            if not line.strip():
                continue
            blocks.append({
                "id": f"p{pno+1:03d}-b{i:03d}", "page": pno + 1,
                "bbox": [0, 0, 0, 0], "text": line.strip(), "column": 1,
                "font_size": 0, "source": "pdftotext",
            })
    return blocks


def order_blocks(page_blocks, mode):
    if mode == "raw":
        return sorted(page_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    cols = {b["column"] for b in page_blocks}
    if cols.issubset({1, 2}) and len(cols) == 2:
        # 双栏：栏优先，再按 y
        return sorted(page_blocks, key=lambda b: (b["column"], b["bbox"][1]))
    # 单栏或含跨栏块：按 y，同高度按 x
    return sorted(page_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["reading", "raw"], default="reading")
    args = ap.parse_args()
    if not os.path.isfile(args.pdf):
        print(json.dumps({"error": "file not found"}, ensure_ascii=False))
        return 2
    backend = "none"
    blocks = []
    for name, fn in (("pymupdf", extract_pymupdf),
                     ("pdfplumber", extract_pdfplumber),
                     ("pdftotext", extract_pdftotext)):
        try:
            blocks = fn(args.pdf, args.mode)
            backend = name
            break
        except ImportError:
            continue
        except Exception as e:
            print(json.dumps({"warning": f"{name} failed: {e}"},
                             ensure_ascii=False), file=sys.stderr)
            continue
    if backend == "none":
        # 纯标准库兜底：无需任何第三方依赖
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import pdf_fallback
            blocks = pdf_fallback.blocks(args.pdf, args.mode)
            if blocks:
                backend = "stdlib-fallback"
        except Exception as e:
            print(json.dumps({"warning": f"stdlib-fallback failed: {e}"},
                             ensure_ascii=False), file=sys.stderr)
    result = {"backend": backend, "block_count": len(blocks), "blocks": blocks}
    if backend == "none":
        result["error"] = "no usable backend; install pymupdf"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({"backend": backend, "block_count": len(blocks),
                      "out": args.out, "error": result.get("error")},
                     ensure_ascii=False))
    return 0 if backend != "none" else 1


if __name__ == "__main__":
    sys.exit(main())
