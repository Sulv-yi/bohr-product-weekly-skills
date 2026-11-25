#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""clean_extract.py — 把 PDF 抽取结果整理成可逐字引用的文本。

只做三件事，不改变词序、不改写句子：
  1. 去掉抽取残留的控制符（软连字符被抽成 \\x02，会让 out-performing 变 outperforming）
  2. ◦ -> ° ；保留 <!-- page N --> 锚点
  3. 统一换行，输出 UTF-8

用法: python3 scripts/clean_extract.py --in raw.md --out materials/paper.md
"""
import argparse
import re

CTRL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    a = ap.parse_args()
    s = open(a.src, encoding="utf-8").read()
    before = len(s)
    #  是 PDF 里行末软连字符的抽取残留：out\x02 performing -> outperforming
    s = s.replace("\x02", "\u00ad")
    s = re.sub(r"(\w)\u00ad\s*(\w)", r"\1\2", s)
    s = CTRL.sub("", s).replace("◦", "°")
    s = s.replace("\r\n", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    open(a.dst, "w", encoding="utf-8", newline="\n").write(s)
    print("in=%d bytes, out=%d bytes, ctrl_removed=%d"
          % (before, len(s), before - len(s)))


if __name__ == "__main__":
    main()
