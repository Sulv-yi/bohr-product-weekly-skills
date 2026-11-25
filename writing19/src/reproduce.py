#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reproduce.py —— 一键复现入口。

平台按 arm_manifest 的 entrypoint 找这个文件。它只做三件事：
1. 找到案例输入（优先 /input/case.json）；
2. 调 scripts/mm_run.py 跑完整流程（切块 → 兜底建图 → 校验 → 导出 → result.json）；
3. 把产物留在 /app/output（本地运行时退回 ./output）。

本地演示：
    python3 src/reproduce.py --case examples/selftest-case.json
    python3 src/reproduce.py --material examples/selftest-material.md
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pick(path, fallback):
    return path if os.path.exists(path) else fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="")
    ap.add_argument("--material", default="")
    ap.add_argument("--work", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    case = args.case or pick("/input/case.json", "")
    work = args.work or pick("/app/work", os.path.join(ROOT, "work"))
    out = args.out or pick("/app/output", os.path.join(ROOT, "output"))
    run = os.path.join(ROOT, "scripts", "mm_run.py")

    cmd = [sys.executable, run, "--work", work, "--out", out]
    if case:
        cmd += ["--case", case]
    if args.material:
        cmd += ["--material", args.material]

    print("复现命令：%s" % " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print("流程返回 %d。产物与状态见 %s/result.json" % (rc, out), file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
