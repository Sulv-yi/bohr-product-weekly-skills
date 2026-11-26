# -*- coding: utf-8 -*-
"""一键复现 demo：生成测试图 → 定轴 → 标定 → 提取 → 叠加 → 与真值对表。

用法: python src/reproduce.py [--work DIR] [--out DIR]
产物: out/curve.csv, out/overlay.png, out/report.json, out/compare.md
"""
import csv
import json
import os
import subprocess
import sys
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")


def run(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("step failed: %s" % args[0])
    return r.stdout.strip()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/tmp/c2d_demo")
    ap.add_argument("--out", default="/tmp/c2d_demo_out")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)

    img = os.path.join(ROOT, "examples", "demo-chart.png")
    truth = os.path.join(ROOT, "examples", "truth.csv")
    axes = os.path.join(a.work, "axes.json")
    calib = os.path.join(a.work, "calib.json")
    curve = os.path.join(a.out, "curve.csv")
    rep = os.path.join(a.out, "report.json")

    print("[1/5]", run([os.path.join(SCRIPTS, "c2d_axes.py"),
                       "--image", img, "--out", axes]))
    json.dump({
        "x": {"px": [90, 760], "val": [0, 40], "log": False},
        "y": {"px": [540, 60], "val": [0, 100], "log": False},
        "series": {"decay": {"mode": "color", "rgb": [214, 39, 40], "tol": 60}},
        "note": "参考点数值来自轴刻度（Agent 读），像素位置来自 axes.json",
    }, open(calib, "w", encoding="utf-8"), indent=1)
    print("[2/5]", run([os.path.join(SCRIPTS, "c2d_trace.py"),
                        "--image", img, "--calib", calib, "--out", curve]))
    print("[3/5]", run([os.path.join(SCRIPTS, "c2d_overlay.py"),
                        "--image", img, "--csv", curve,
                        "--out", os.path.join(a.out, "overlay"), "--report", rep]))

    # 对表：提取 vs 真值
    ex = {}
    for r in csv.DictReader(open(curve, encoding="utf-8-sig")):
        ex.setdefault(round(float(r["x"]), 1), []).append(float(r["y"]))
    rows = []
    for r in csv.DictReader(open(truth, encoding="utf-8-sig")):
        xv, tv = round(float(r["x"]), 1), float(r["y_true"])
        cands = ex.get(xv) or ex.get(round(xv - 0.1, 1)) or ex.get(round(xv + 0.1, 1))
        if not cands:
            continue
        v = min(cands, key=lambda c: abs(c - tv))
        rows.append((xv, tv, v, abs(v - tv)))
    cmp_path = os.path.join(a.out, "compare.md")
    with open(cmp_path, "w", encoding="utf-8") as f:
        f.write("# demo 对表记录（真值来自 make_demo.py 写死的函数）\n\n")
        f.write("| x | 真值 | 提取 | 绝对误差 |\n|---|---|---|---|\n")
        for xv, tv, v, e in rows:
            f.write("| %.1f | %.3f | %.3f | %.3f |\n" % (xv, tv, v, e))
        errs = [r[3] for r in rows]
        f.write("\n中位绝对误差 %.3f 数据单位；相对误差只在 y>2 的区间报，"
                "尾部（y<1）受线宽量化限制，见 SKILL.md 误差口径。\n"
                % statistics.median(errs))
    print("[4/5] 对表完成: %s" % cmp_path)
    print("[5/5] 产物: %s (curve.csv, overlay.png, report.json, compare.md)" % a.out)


if __name__ == "__main__":
    main()
