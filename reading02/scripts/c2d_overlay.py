# -*- coding: utf-8 -*-
"""c2d_overlay: 把提取的点画回原图生成对照 PNG + 误差报告。

这是自查环节：评审看叠加图就能直接判断提取是否贴合原曲线，
比文字描述"提取了 200 个点"可信得多。
"""
import csv
import json
import sys


def main():
    import argparse
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True, help="叠加图 PNG 前缀")
    ap.add_argument("--report", required=True, help="质量报告 JSON")
    a = ap.parse_args()
    im = Image.open(a.image).convert("RGB")
    d = ImageDraw.Draw(im)
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig")))
    colors = {"1": (0, 150, 0), "2": (150, 0, 200), "3": (0, 100, 220)}
    stats = {}
    for r in rows:
        x, y = int(float(r["x_px"])), round(float(r["y_px"]))
        c = colors.get(r["series"], (0, 150, 0))
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=c)
        s = stats.setdefault(r["series"], {"n": 0, "max_unc": 0.0, "drops": 0})
        s["n"] += 1
        s["max_unc"] = max(s["max_unc"], float(r["y_unc"]))
        s["drops"] += int(r["dropped_segments"])
    im.save(a.out + ".png")

    # 密集度：有没有大段空缺（曲线被漏掉的区域）
    gaps = {}
    for name in stats:
        xs = [int(float(r["x_px"])) for r in rows if r["series"] == name]
        if len(xs) < 2:
            continue
        xs.sort()
        gaps[name] = max(b - a2 for a2, b in zip(xs, xs[1:]))
    rep = {"series_stats": stats, "max_gap_px": gaps,
           "read": "max_gap_px 大于 30 说明该区间提取断档，需检查曲线被遮挡或颜色不符"}
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in stats.items():
        print("%s: %d 点, 最大不确定度 %.4g, 丢弃段 %d, 最大断档 %s px"
              % (k, v["n"], v["max_unc"], v["drops"], gaps.get(k)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
