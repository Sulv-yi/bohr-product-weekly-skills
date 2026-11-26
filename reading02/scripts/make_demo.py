# -*- coding: utf-8 -*-
"""make_demo: 用 PIL 生成一张已知真值的测试图，用于端到端自检。

真值曲线：y = 100 * exp(-x/8)，x∈[0,40]。写死在 TRUTH 里，
提取结果直接和它对表 —— 误差是实测的，不是估的。
"""
import math
import sys

from PIL import Image, ImageDraw

W, H = 800, 600
X0, X1, Y0, Y1 = 90, 760, 60, 540      # 绘图区像素
VX0, VX1, VY0, VY1 = 0.0, 40.0, 0.0, 100.0  # 数据范围（y 轴向上）


def TRUTH(x):
    return 100.0 * math.exp(-x / 8.0)


def main():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)

    def px(xv):
        return X0 + (xv - VX0) / (VX1 - VX0) * (X1 - X0)

    def py(yv):
        return Y1 - (yv - VY0) / (VY1 - VY0) * (Y1 - Y0)

    # 网格（浅灰，脚本要能跳过）
    for i in range(0, 41, 5):
        d.line([px(i), Y0, px(i), Y1], fill=(220, 220, 220))
    for j in range(0, 101, 20):
        d.line([X0, py(j), X1, py(j)], fill=(220, 220, 220))

    # 轴 + 刻度
    d.line([X0, Y0, X0, Y1], fill=(0, 0, 0), width=2)
    d.line([X0, Y1, X1, Y1], fill=(0, 0, 0), width=2)
    for i in range(0, 41, 5):
        d.line([px(i), Y1, px(i), Y1 + 6], fill=(0, 0, 0))
    for j in range(0, 101, 20):
        d.line([X0 - 6, py(j), X0, py(j)], fill=(0, 0, 0))

    # 真值曲线（红）
    pts = [(px(x / 10.0), py(TRUTH(x / 10.0))) for x in range(0, 401)]
    d.line(pts, fill=(214, 39, 40), width=3)

    im.save(sys.argv[1] if len(sys.argv) > 1 else "demo-chart.png")
    # 输出真值供对表
    with open((sys.argv[2] if len(sys.argv) > 2 else "truth.csv"), "w", encoding="utf-8") as f:
        f.write("x,y_true\n")
        for i in range(0, 41, 2):
            f.write("%.1f,%.4f\n" % (i, TRUTH(i)))
    print("demo chart saved")


if __name__ == "__main__":
    main()
