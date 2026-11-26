# -*- coding: utf-8 -*-
"""ode_check: 独立复核 —— 解析解 + RK4 数值积分。

模型等价于一个下三角线性 ODE 系统，可逐式积分（v_1 = v_2 = 0）：
  N1(t) = N10
  N2(t) = N20 + u1·N10·t
  N3(t) = N30·e^{v3 t} + (u2·N20/v3)(e^{v3 t} − 1) + (u2·u1·N10/v3²)(e^{v3 t} − 1 − v3 t)
这一式与「五步法 + 泰勒修正」应给出同一组数——两条完全不同的路径互相校验。
"""
import math

U = [0.04, 0.02, 0.01]
N0 = [2.0, 5.0, 15.0]
V3 = 0.01


def analytic(t):
    N1 = N0[0]
    N2 = N0[1] + U[0] * N0[0] * t
    e = math.exp(V3 * t)
    N3 = (N0[2] * e
          + U[1] * N0[1] / V3 * (e - 1)
          + U[1] * U[0] * N0[0] / (V3 * V3) * (e - 1 - V3 * t))
    return [N1, N2, N3]


def rk4(t, steps=20000):
    def f(y):
        return [0.0 * y[0], U[0] * y[0], U[1] * y[1] + V3 * y[2]]
    y = list(N0)
    h = t / float(steps)
    for _ in range(steps):
        k1 = f(y)
        k2 = f([y[i] + h / 2 * k1[i] for i in range(3)])
        k3 = f([y[i] + h / 2 * k2[i] for i in range(3)])
        k4 = f([y[i] + h * k3[i] for i in range(3)])
        y = [y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(3)]
    return y


if __name__ == "__main__":
    for t in (0, 10, 20):
        a, r = analytic(t), rk4(t)
        print("t=%2d  解析 %s  RK4 %s  差 %.1e"
              % (t, " ".join("%.6f" % x for x in a), " ".join("%.6f" % x for x in r),
                 max(abs(x - y) for x, y in zip(a, r))))
