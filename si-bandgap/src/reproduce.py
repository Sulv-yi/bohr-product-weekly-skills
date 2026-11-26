# -*- coding: utf-8 -*-
"""一键复现：算 A、B 与四个温度的 ΔE_g，写 results.json 并做内部一致性检查。

不一致（用 A、B 反算的 ΔE_g 与直接算配分函数的值差 > 1e-5 eV）时拒绝落盘。
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from derive_AB import coeffs, delta_g   # noqa: E402

TS = [100, 200, 300, 400]


def main():
    A, B = coeffs()
    res = {"A": round(A, 9), "B": round(B, 9)}
    bad = []
    for T in TS:
        direct = delta_g(T)
        res["DeltaEg_%dK" % T] = round(direct, 6)
        via = A * T - B * T * math.log(T)
        if abs(via - direct) > 1e-5:
            bad.append((T, via, direct))
    print("A = %.6e eV/K, B = %.6e eV/K (1.5k = %.6e)" % (A, B, 1.5 * 8.617333262e-5))
    for T in TS:
        print("  DeltaEg(%3d K) = %+.6f eV" % (T, res["DeltaEg_%dK" % T]))
    if bad:
        print("\n内部一致性失败：%s" % bad, file=sys.stderr)
        return 2
    p = os.path.join(ROOT, "results", "results.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(res, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(res, open(os.path.join(ROOT, "results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n已写入 %s（内部一致性通过）" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
