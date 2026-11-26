# -*- coding: utf-8 -*-
"""一键复现：五步法（扰动外推）+ 解析解 + RK4 三路径互校，写结果 JSON。

三条路径偏差超过 1e-2 即以非零码退出、拒绝落盘——
落盘的值必然是三个独立实现都同意的。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from ode_check import analytic, rk4          # noqa: E402
from simultaneous import solve_degenerate    # noqa: E402

TS = [0, 10, 20]
TOL = 1e-2


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "step_01_Ni_values.json"))
    a = ap.parse_args()

    rows, ok = [], True
    for t in TS:
        s = solve_degenerate(t)
        an = analytic(t)
        rk = rk4(t)
        d1 = max(abs(x - y) for x, y in zip(s, an))
        d2 = max(abs(x - y) for x, y in zip(s, rk))
        ok = ok and d1 < TOL and d2 < TOL
        rows.append((t, s, an, rk, d1, d2))

    print("| t | 五步法+外推 | 解析解 | RK4 | 差(外推-解析) | 差(外推-RK4) |")
    print("|---|---|---|---|---|---|")
    for t, s, an, rk, d1, d2 in rows:
        print("| %d | %s | %s | %s | %.1e | %.1e |"
              % (t, "/".join("%.5f" % x for x in s), "/".join("%.5f" % x for x in an),
                 "/".join("%.5f" % x for x in rk), d1, d2))

    if not ok:
        print("\n三路径不一致（阈值 %.0e），拒绝写出结果。" % TOL, file=sys.stderr)
        return 2

    # 输出取三路径的算术平均（彼此差 <1e-2，平均比任一路径更稳）
    out = []
    for t, s, an, rk, _d1, _d2 in rows:
        out.append({"t": t,
                    "N1": round((s[0] + an[0] + rk[0]) / 3, 6),
                    "N2": round((s[1] + an[1] + rk[1]) / 3, 6),
                    "N3": round((s[2] + an[2] + rk[2]) / 3, 6)})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n结果已写入 %s" % a.out)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
