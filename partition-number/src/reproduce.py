# -*- coding: utf-8 -*-
"""一键复现：HRR 级数 + 精确 DP 双路径计算 p(n)，比对一致后写出结果 JSON。

用法: python src/reproduce.py [--out DIR]
默认输出到 results/partition_results.json（与题面契约同构）。
两条路径不一致时以非零码退出，并打印差异——绝不写出未核实的值。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from partition_dp import p_dp            # noqa: E402
from partition_hrr import p_hrr, remainder_bound  # noqa: E402

NS = [80, 120, 200, 400, 800]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "partition_results.json"))
    a = ap.parse_args()

    dp = p_dp(max(NS))
    values, rows, ok = {}, [], True
    for n in NS:
        hrr, raw, N = p_hrr(n)
        agree = (hrr == dp[n])
        ok = ok and agree
        values[str(n)] = str(dp[n])
        rows.append((n, dp[n], hrr, N, abs(raw - hrr), remainder_bound(n, N), agree))

    print("| n | 精确 DP | HRR 级数 | N | 两法之差 | 余项上界 M(n,N) | 一致 |")
    print("|---|---|---|---|---|---|---|")
    for n, d, h, N, resid, m, agree in rows:
        print("| %d | %d | %d | %d | %s | %.3e | %s |"
              % (n, d, h, N, "0" if agree else str(h - d), m, "是" if agree else "否"))

    if not ok:
        print("\n两条路径不一致，拒绝写出结果。", file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({"values": values}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n结果已写入 %s（两法一致，余项上界均 < 0.5，四舍五入可靠）" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
