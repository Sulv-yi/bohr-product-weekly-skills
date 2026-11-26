# -*- coding: utf-8 -*-
"""partition_hrr: 按 Hardy–Ramanujan–Rademacher 级数计算精确 p(n)。

实现严格对应题面公式：
  p(n) = Σ_{k=1..N} sqrt(3/k)·4/(24n-1)·A_k(n)·U(C(n)/k)
  U(x) = cosh(x) − sinh(x)/x ,  C(n) = π/6·sqrt(24n−1)
  A_k(n) 用 Algorithm 1 的循环形式（k≤1 返回 k，k=2 返回 (−1)^n）

截断项数 N：默认 ceil(sqrt(n))（题面注明 n≥65 时充分），
--check-bound 会按式 (1.8) 的余项上界 M(n,N) 逐项验证 < 0.5。
"""
import sys

import mpmath as mp


def A_k(k, n):
    """A_k(n) 的循环实现（题面 Algorithm 1）。"""
    if k <= 1:
        return mp.mpf(k)
    if k == 2:
        return mp.mpf((-1) ** n)
    s = mp.mpf(0)
    r, m = 2 % k, n % k
    for l in range(2 * k):
        if m == 0:
            s += (-1) ** l * mp.cos(mp.pi * (6 * l + 1) / (6 * k))
        m = (m + r) % k
        r = (r + 3) % k
    return mp.sqrt(mp.mpf(k) / 3) * s


def U(x):
    if x == 0:
        return mp.mpf(0)
    return mp.cosh(x) - mp.sinh(x) / x


def remainder_bound(n, N):
    """式 (1.8)：M(n,N)。N 的选法要让 M < 1/2，否则四舍五入不可靠。"""
    t1 = mp.mpf(44) * mp.pi ** 2 / (225 * mp.sqrt(3) * mp.sqrt(N))
    t2 = mp.pi * mp.sqrt(2) / 75 * mp.sqrt(mp.mpf(N) / (n - 1)) * \
        mp.sinh(mp.pi / N * mp.sqrt(mp.mpf(2 * n) / 3))
    return t1 + t2


def p_hrr(n, N=None, dps=80):
    """返回 (取整后的 p(n), 未取整的高精度和, 使用的 N)。"""
    mp.mp.dps = dps
    if N is None:
        N = int(mp.ceil(mp.sqrt(n)))
    C = mp.pi / 6 * mp.sqrt(24 * n - 1)
    total = mp.mpf(0)
    for k in range(1, N + 1):
        total += mp.sqrt(mp.mpf(3) / k) * mp.mpf(4) / (24 * n - 1) * A_k(k, n) * U(C / k)
    return int(mp.nint(total)), total, N


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="+", default=[80, 120, 200, 400, 800])
    ap.add_argument("--dps", type=int, default=80)
    ap.add_argument("--check-bound", action="store_true", help="逐项验证余项上界 M(n,N)<0.5")
    a = ap.parse_args()
    for n in a.n:
        v, raw, N = p_hrr(n, dps=a.dps)
        line = "p(%d) = %d   (N=%d, 余项截断误差 %.3e)" % (n, v, N, abs(raw - v))
        if a.check_bound:
            line += "   M(n,N)=%.3e %s" % (remainder_bound(n, N),
                                           "OK<0.5" if remainder_bound(n, N) < mp.mpf(0.5) else "超界!")
        print(line)


if __name__ == "__main__":
    sys.exit(main())
