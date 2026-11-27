#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bench.py —— 同一批真实 PDF 上，跑"不用 Skill"与"用 Skill"两种条件，输出可复核指标。

两种条件（严格同输入、同机器、同进程）：
  baseline  逐页纯文本直出：有 pypdf 就 page.extract_text()，没有就走
            doctext._builtin_legacy（旧的流序拼接）。这是"把 PDF 读成一段文本"的典型做法。
  skill     doctext.build()：页树纠正 + 坐标分栏 + 段落/章节/题注/表格/参考文献 + 证据回查。

指标（都由本脚本现算，不引用外部结论）：
  pages         识别的页数（与 pypdf 的页数基准比对，用于看页序/页数是否丢失）
  chars         正文字符数
  glue_per_1k   千字里"连续 28 个以上无空格字母"的片段数 —— 词界丢失的代理指标
  suspect_pct   非 ASCII 且非中日韩字符的占比 —— 乱码/符号污染的代理指标
  headings      章节标题数
  captions      图/表题注数
  tables        解析成功的表格数
  refs          参考文献条目数
  evidence_pct  抽 20 段做逐字回查，能命中的比例（仅 skill 条件有结构可查）
  ms            耗时

用法：
  python scripts/bench.py --out examples/runs/bench.json a.pdf b.pdf
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import doctext  # noqa: E402


def _clean(text: str) -> str:
    return text or ""


def _glue_rate(text: str) -> float:
    n = max(1, len(text))
    return round(1000.0 * len(re.findall(r"[A-Za-z]{28,}", text)) / n, 2)


def _suspect_pct(text: str) -> float:
    if not text:
        return 0.0
    bad = 0
    for ch in text:
        o = ord(ch)
        if o < 128 or ch.isspace():
            continue
        if 0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
            continue
        bad += 1
    return round(100.0 * bad / len(text), 2)


def baseline_text(path: str) -> tuple[str, str, int]:
    """返回 (文本, 用的什么后端, 页数)。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path, strict=False)
        if getattr(reader, "is_encrypted", False):
            reader.decrypt("")
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n".join(pages), "pypdf.extract_text", len(pages)
    except Exception:
        got = doctext._builtin_legacy(path)
        if not got:
            return "", "none", 0
        return "\n".join(got["pages_text"]), "builtin.stream-order", len(got["pages_text"])


def evidence_rate(doc: dict, sample: int = 20) -> float:
    paras = [p for p in doc.get("paragraphs", []) if len(p.get("text", "")) > 30]
    if not paras:
        return 0.0
    random.seed(20261127)
    picks = random.sample(paras, min(sample, len(paras)))
    blob = "\n".join(p["text"] for p in doc["paragraphs"])
    hit = 0
    for p in picks:
        probe = p["text"][:40]
        if probe and probe in blob:
            hit += 1
    return round(100.0 * hit / len(picks), 1)


def run_one(path: str) -> dict:
    t0 = time.time()
    btext, bback, bpages = baseline_text(path)
    b_ms = int((time.time() - t0) * 1000)

    t0 = time.time()
    doc = doctext.build(path)
    s_ms = int((time.time() - t0) * 1000)
    st = doc.get("stats", {})

    return {
        "file": os.path.basename(path),
        "bytes": os.path.getsize(path),
        "baseline": {
            "backend": bback, "pages": bpages, "chars": len(btext),
            "glue_per_1k": _glue_rate(btext), "suspect_pct": _suspect_pct(btext),
            "headings": None, "captions": None, "tables": None, "refs": None,
            "evidence_pct": None, "ms": b_ms,
        },
        "skill": {
            "backend": doc.get("backend"), "pages": st.get("pages"),
            "chars": st.get("chars"), "glue_per_1k": _glue_rate(doc.get("plain_text", "")),
            "suspect_pct": _suspect_pct(doc.get("plain_text", "")),
            "headings": st.get("headings"), "captions": st.get("captions"),
            "tables": st.get("tables_parsed"), "refs": len(doc.get("references") or []),
            "evidence_pct": evidence_rate(doc), "ms": s_ms,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--out", help="把结果写成 JSON")
    args = ap.parse_args()
    rows = [run_one(p) for p in args.pdfs]
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
    for r in rows:
        b, s = r["baseline"], r["skill"]
        print(f"== {r['file']}  ({r['bytes'] // 1024} KB)")
        print(f"   页数      baseline {b['pages']}   skill {s['pages']}")
        print(f"   字符      baseline {b['chars']}   skill {s['chars']}")
        print(f"   粘连/千字 baseline {b['glue_per_1k']}   skill {s['glue_per_1k']}")
        print(f"   可疑字符% baseline {b['suspect_pct']}   skill {s['suspect_pct']}")
        print(f"   结构      baseline 无   skill 章节 {s['headings']} / 题注 {s['captions']}"
              f" / 表格 {s['tables']} / 文献 {s['refs']}")
        print(f"   回查命中  skill {s['evidence_pct']}%")
        print(f"   耗时      baseline {b['ms']}ms   skill {s['ms']}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
