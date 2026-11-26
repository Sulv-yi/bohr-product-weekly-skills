# -*- coding: utf-8 -*-
"""simultaneous: 三房室细胞群体模型的「同时求解」五步法（复现论文算法）。

模型：dN_i/dt = v_i·N_i + u_{i-1}·N_{i-1}，u = [0.04, 0.02, 0.01]，
v = [0, 0, 0.01]（v_2 取 0 时 v_1=v_2 退化，算法除以 v_ν−v_μ 会崩）。

五步：
  1. d_{νμ} = −(v_ν − v_μ)
  2. p_{νμ} = u_{ν−1} / d_{νμ}
  3. q_{νμ}：ν<μ 为 0，ν=μ 为 1，ν>μ 递推 p_{νμ}·q_{ν−1,μ}
  4. a_i = N_i0 − Σ_{ν<i} q_{iν}·a_ν
  5. N_i(t) = Σ_{ν≤i} a_ν·q_{iν}·e^{v_ν t}

退化处理：题目要求把 v_2 扰动到 0.001 再泰勒展开回真值。
本实现用两档扰动 (ε, 2ε) 的线性外推实现一阶泰勒修正——
数学上就是 N(0) ≈ 2N(ε) − N(2ε)，避免手工展开长表达式出错。
"""
import math

U = [0.04, 0.02, 0.01]
N0 = [2.0, 5.0, 15.0]
V3 = 0.01


def q_of(v, nu, mu, cache):
    """q_{νμ} 递推（带缓存）。"""
    if nu < mu:
        return 0.0
    if nu == mu:
        return 1.0
    key = (nu, mu)
    if key in cache:
        return cache[key]
    d = -(v[nu - 1] - v[mu - 1])
    p = U[nu - 2] / d
    val = p * q_of(v, nu - 1, mu, cache)
    cache[key] = val
    return val


def solve(v, t):
    """返回 [N1(t), N2(t), N3(t)]。要求 v_ν 两两不等。"""
    cache = {}
    a = {}
    for i in range(1, 4):
        a[i] = N0[i - 1] - sum(q_of(v, i, nu, cache) * a[nu] for nu in range(1, i))
    return [sum(a[nu] * q_of(v, i, nu, cache) * math.exp(v[nu - 1] * t)
                for nu in range(1, i + 1)) for i in range(1, 4)]


def solve_degenerate(t, eps=1e-3):
    """v_2 = 0 与 v_1 重合时的解：扰动后线性外推到 ε→0（一阶泰勒修正）。"""
    n_eps = solve([0.0, eps, V3], t)
    n_2eps = solve([0.0, 2 * eps, V3], t)
    return [2 * x - y for x, y in zip(n_eps, n_2eps)]


if __name__ == "__main__":
    for t in (0, 10, 20):
        print("t=%2d  " % t + "  ".join("%.6f" % x for x in solve_degenerate(t)))
