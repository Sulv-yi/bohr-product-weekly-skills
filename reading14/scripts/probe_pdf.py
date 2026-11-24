#!/usr/bin/env python3
"""探查 PDF 版式：后端、加密、页数、文字层、栏数线索、图像型页面。

用法: python probe_pdf.py <pdf> [--json]
只读输入文件，不修改。输出 JSON 到 stdout。
"""
import sys
import json
import os


def pick_backend():
    try:
        import fitz  # PyMuPDF
        return "pymupdf"
    except Exception:
        pass
    try:
        import pdfplumber
        return "pdfplumber"
    except Exception:
        pass
    try:
        import pypdf
        return "pypdf"
    except Exception:
        pass
    import shutil
    if shutil.which("pdftotext"):
        return "pdftotext"
    # 纯标准库兜底：无第三方依赖，至少能提取有文字层 PDF 的文本行
    try:
        import pdf_fallback  # noqa: F401
        return "stdlib-fallback"
    except Exception:
        pass
    return "none"


def probe_pymupdf(path):
    import fitz
    doc = fitz.open(path)
    info = {
        "encrypted": bool(doc.is_encrypted),
        "needs_pass": False,
        "pages": doc.page_count,
        "page_stats": [],
        "column_hint": [],
        "image_only_pages": [],
    }
    if doc.is_encrypted:
        try:
            doc.authenticate("")
        except Exception:
            pass
        if doc.is_encrypted:
            info["needs_pass"] = True
            return info
    for i in range(doc.page_count):
        page = doc[i]
        text = page.get_text("text") or ""
        blocks = page.get_text("blocks") or []
        chars = len(text.strip())
        imgs = len(page.get_images(full=True))
        info["page_stats"].append({
            "page": i + 1,
            "char_count": chars,
            "block_count": len(blocks),
            "image_count": imgs,
            "width": round(page.rect.width, 1),
            "height": round(page.rect.height, 1),
        })
        if chars < 50 and imgs >= 1:
            info["image_only_pages"].append(i + 1)
        # 栏目线索：按块中点 x 分成左右两半，统计两侧文本量
        mid = page.rect.width / 2
        left = right = 0
        for b in blocks:
            if len(b) < 5:
                continue
            x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4]
            if y1 - y0 > page.rect.height * 0.25:  # 跳过跨栏大块
                continue
            n = len((txt or "").strip())
            cx = (x0 + x1) / 2
            if cx < mid:
                left += n
            else:
                right += n
        info["column_hint"].append(2 if left > 0 and right > 0 else 1)
    doc.close()
    return info


def probe_pdfplumber(path):
    import pdfplumber
    info = {"encrypted": False, "needs_pass": False, "pages": 0,
            "page_stats": [], "column_hint": [], "image_only_pages": []}
    with pdfplumber.open(path) as pdf:
        info["pages"] = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            chars = len(text.strip())
            imgs = len(page.images)
            info["page_stats"].append({
                "page": i + 1, "char_count": chars,
                "block_count": len(page.extract_words()), "image_count": imgs,
                "width": round(page.width, 1), "height": round(page.height, 1),
            })
            if chars < 50 and imgs >= 1:
                info["image_only_pages"].append(i + 1)
            info["column_hint"].append(1)
    return info


def probe_pypdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    info = {"encrypted": bool(reader.is_encrypted), "needs_pass": False,
            "pages": len(reader.pages), "page_stats": [], "column_hint": [],
            "image_only_pages": []}
    if reader.is_encrypted:
        info["needs_pass"] = True
        return info
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        chars = len(text.strip())
        info["page_stats"].append({
            "page": i + 1, "char_count": chars, "block_count": 0,
            "image_count": len(getattr(page, "images", [])),
            "width": 0, "height": 0,
        })
        if chars < 50:
            info["image_only_pages"].append(i + 1)
        info["column_hint"].append(1)
    return info


def probe_pdftotext(path):
    import subprocess
    import shutil
    info = {"encrypted": False, "needs_pass": False, "pages": 0,
            "page_stats": [], "column_hint": [], "image_only_pages": []}
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            info["pages"] = int(line.split(":", 1)[1].strip())
    txt = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True)
    pages = (txt.stdout or "").split("\f")
    for i, p in enumerate(pages):
        chars = len(p.strip())
        info["page_stats"].append({"page": i + 1, "char_count": chars,
                                   "block_count": 0, "image_count": 0,
                                   "width": 0, "height": 0})
        info["column_hint"].append(1)
        if chars < 50:
            info["image_only_pages"].append(i + 1)
    return info


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: probe_pdf.py <pdf>"}, ensure_ascii=False))
        return 2
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(json.dumps({"error": "file not found", "path": path}, ensure_ascii=False))
        return 2
    backend = pick_backend()
    result = {"file": os.path.basename(path), "path": path, "backend": backend,
              "size_bytes": os.path.getsize(path)}
    try:
        if backend == "pymupdf":
            result.update(probe_pymupdf(path))
        elif backend == "pdfplumber":
            result.update(probe_pdfplumber(path))
        elif backend == "pypdf":
            result.update(probe_pypdf(path))
        elif backend == "pdftotext":
            result.update(probe_pdftotext(path))
        elif backend == "stdlib-fallback":
            import pdf_fallback
            fb = pdf_fallback.probe(path)
            fb.pop("backend", None)
            result.update(fb)
        else:
            result["error"] = ("no PDF backend available; install pymupdf: "
                               "pip install pymupdf")
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
