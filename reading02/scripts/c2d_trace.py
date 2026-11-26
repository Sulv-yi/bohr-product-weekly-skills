# -*- coding: utf-8 -*-
"""c2d_trace: 按标定把曲线像素换算成数据坐标，输出 CSV（纯 PIL）。

标定文件（Agent 填数值，脚本管换算）：
{
  "x": {"px": [x0_px, x1_px], "val": [v0, v1], "log": false},
  "y": {"px": [y0_px, y1_px], "val": [v0, v1], "log": false},
  "series": {"curve1": {"mode": "color", "rgb": [214, 39, 40], "tol": 60},
             "curve2": {"mode": "dark",  "note": "图里最深的主曲线"}}
}
- px/val 各给两个参考点即可，log=true 时按 log10 线性插值（对数轴）。
- mode=color 按颜色容差匹配；mode=dark 取该列最暗的非网格像素（黑白曲线图）。

误差口径：每个输出点都带 pixel 证据列和 dy_px（同一列里匹配像素的散布），
换算成数据单位后写入 uncertainty 区间 —— 不假装比半个像素更准。
"""
import csv
import json
import math
import sys


def load_rgb(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    return im, w, h, list(im.getdata())


def calibrator(spec):
    def make(s):
        p0, p1 = s["px"]
        v0, v1 = s["val"]
        if s.get("log"):
            lv0, lv1 = math.log10(v0), math.log10(v1)

            def f(p):
                if p1 == p0:
                    return v0
                return 10 ** (lv0 + (lv1 - lv0) * (p - p0) / (p1 - p0))
        else:
            def f(p):
                if p1 == p0:
                    return v0
                return v0 + (v1 - v0) * (p - p0) / (p1 - p0)
        return f
    return make(spec["x"]), make(spec["y"])


def color_dist(c, target):
    return max(abs(c[0] - target[0]), abs(c[1] - target[1]), abs(c[2] - target[2]))


def is_grid(c):
    """网格线/背景：接近灰且不深。"""
    r, g, b = c
    return abs(r - g) < 14 and abs(g - b) < 14 and 150 < r < 245


def trace_column(w, h, pxdata, x, spec):
    """第 x 列里属于目标曲线的像素 ys。"""
    out = []
    if spec["mode"] == "color":
        rgb, tol = spec["rgb"], spec.get("tol", 60)
        for y in range(h):
            c = pxdata[y * w + x]
            if color_dist(c, rgb) <= tol:
                out.append(y)
    else:
        best, bestv = None, 256
        for y in range(h):
            c = pxdata[y * w + x]
            if is_grid(c):
                continue
            v = min(c)
            if v < bestv:
                bestv, best = v, y
        if best is not None and bestv < 140:
            # 把连着的同一曲线像素都收进来
            out = [best]
            for d in (1, -1):
                y = best + d
                while 0 <= y < h and min(pxdata[y * w + x][:3]) < 160 and not is_grid(pxdata[y * w + x]):
                    out.append(y)
                    y += d
    return sorted(out)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--out", required=True, help="输出 CSV 路径")
    ap.add_argument("--series", default=None, help="只导出某条曲线，默认全部")
    a = ap.parse_args()
    calib = json.load(open(a.calib, encoding="utf-8"))
    im, w, h, px = load_rgb(a.image)
    fx, fy = calibrator(calib)
    series = calib["series"]
    names = [a.series] if a.series else list(series)
    rows = []
    for name in names:
        spec = series[name]
        pts = []
        x0, x1 = int(min(spec.get("x_range_px", [0, w - 1]))), int(max(spec.get("x_range_px", [0, w - 1])))
        for x in range(x0, x1 + 1):
            ys = trace_column(w, h, px, x, spec)
            if not ys:
                continue
            # 断成多段（如图例框撞色）时取最长段，其余丢弃并计数
            segs, cur = [], [ys[0]]
            for y in ys[1:]:
                if y - cur[-1] <= 2:
                    cur.append(y)
                else:
                    segs.append(cur)
                    cur = [y]
            segs.append(cur)
            seg = max(segs, key=len)
            yc = sum(seg) / len(seg)
            xv, yv = fx(x), fy(yc)
            spread = (max(seg) - min(seg)) / 2.0
            # 半像素 + 散布的合成不确定度，换算到数据单位
            dy_data = abs(fy(yc + max(spread, 0.5)) - fy(yc - max(spread, 0.5))) / 2.0
            pts.append({"x_px": x, "y_px": round(yc, 2),
                        "x": round(xv, 6), "y": round(yv, 6),
                        "y_unc": round(dy_data, 6),
                        "dropped_segments": len(segs) - 1})
        rows.append((name, pts))

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f)
        wr.writerow(["series", "x", "y", "y_unc", "x_px", "y_px", "dropped_segments"])
        for name, pts in rows:
            for p in pts:
                wr.writerow([name, p["x"], p["y"], p["y_unc"], p["x_px"], p["y_px"], p["dropped_segments"]])
    for name, pts in rows:
        n_drop = sum(p["dropped_segments"] for p in pts)
        print("%s: %d 点 (列数=%d, 撞色丢弃段=%d)" % (name, len(pts), (pts[-1]["x_px"] - pts[0]["x_px"] + 1) if pts else 0, n_drop))
    return 0


if __name__ == "__main__":
    sys.exit(main())
