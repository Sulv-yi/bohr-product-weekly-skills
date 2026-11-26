# -*- coding: utf-8 -*-
"""partition_dp: 用精确整数 DP 独立复算 p(n)。

与 HRR 完全不同的算法路径（动态规划 vs 解析级数），
两条路径结果一致才认为答案可信 —— 这是本作品的自查机制。
复杂度 O(n²)，n≤800 时瞬时完成。
"""
import sys


def p_dp(nmax):
    p = [0] * (nmax + 1)
    p[0] = 1
    for k in range(1, nmax + 1):
        for n in range(k, nmax + 1):
            p[n] += p[n - k]
    return p


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="+", default=[80, 120, 200, 400, 800])
    a = ap.parse_args()
    p = p_dp(max(a.n))
    for n in a.n:
        print("p(%d) = %d" % (n, p[n]))


if __name__ == "__main__":
    sys.exit(main())
