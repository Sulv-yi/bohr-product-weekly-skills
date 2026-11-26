# -*- coding: utf-8 -*-
"""c2d_axes: 从科研图表 PNG/JPG 中定位绘图区与刻度（纯 PIL，无 numpy/opencv）。

职责边界：只做像素级测量（绘图区边界、刻度线位置、网格线），不读数值——
刻度上的数字由 Agent 用视觉读出后写进标定文件，标定换算在 c2d_trace 里做。
输出所有坐标都是 (像素x, 像素y)，y 向下为正，报告里原样保留。
"""
import json
import sys


def load_gray(path):
    from PIL import Image
    im = Image.open(path).convert("L")
    return im, list(im.getdata())


def dark_runs(px, w, h, y, thresh=120):
    """第 y 行上连续暗段的 [(起,止), ...]，段长 >= 3 才算。"""
    runs, start = [], None
    for x in range(w):
        dark = px[y * w + x] < thresh
        if dark and start is None:
            start = x
        elif not dark and start is not None:
            if x - start >= 3:
                runs.append((start, x - 1))
            start = None
    if start is not None and w - start >= 3:
        runs.append((start, w - 1))
    return runs


def col_dark_runs(px, w, h, x, thresh=120):
    runs, start = [], None
    for y in range(h):
        dark = px[y * w + x] < thresh
        if dark and start is None:
            start = y
        elif not dark and start is not None:
            if y - start >= 3:
                runs.append((start, y - 1))
            start = None
    if start is not None and h - start >= 3:
        runs.append((start, h - 1))
    return runs


def find_axes(im, px, thresh=120):
    """绘图区 = 最长的连续水平暗线 + 最长的连续竖直暗线。

    论文图常有边框（4 条边）或只有左/下两条轴；先找最长横线与最长竖线，
    若横线不止一条且长度接近（差 < 5%），视为上下边框都存在。
    """
    w, h = im.size
    best_h = []  # (长度, y, (x0,x1))
    for y in range(0, h, 2):
        for a, b in dark_runs(px, w, h, y, thresh):
            best_h.append((b - a + 1, y, (a, b)))
    best_h.sort(reverse=True)
    best_v = []
    for x in range(0, w, 2):
        for a, b in col_dark_runs(px, w, h, x, thresh):
            best_v.append((b - a + 1, x, (a, b)))
    best_v.sort(reverse=True)
    if not best_h or not best_v:
        return None
    hl, hy, (hx0, hx1) = best_h[0]
    vl, vx, (vy0, vy1) = best_v[0]
    # 与最长横线长度差 < 5% 的另一条 → 顶边框
    top = None
    for l, y, (a, b) in best_h[1:8]:
        if abs(l - hl) < hl * 0.05 and abs(y - hy) > 10:
            top = y
            break
    right = None
    for l, x, (a, b) in best_v[1:8]:
        if abs(l - vl) < vl * 0.05 and abs(x - vx) > 10:
            right = x
            break
    return {
        "left_x": vx, "bottom_y": hy,
        "top_y": top, "right_x": right,
        "left_span": (vy0, vy1), "bottom_span": (hx0, hx1),
        "image": [w, h],
    }


def find_ticks(im, px, axis_box, thresh=120, tick_min=4, tick_max=14):
    """刻度线 = 从轴外侧伸出来的短暗线。

    底轴刻度：从 bottom_y+1 向下的短竖线（高 4~14px）；
    左轴刻度：从 left_x-1 向左的短横线（宽 4~14px）。
    """
    w, h = im.size
    bx, by = axis_box["left_x"], axis_box["bottom_y"]
    x_a, x_b = axis_box["bottom_span"]
    tx = []
    for x in range(x_a, x_b + 1):
        run, y = 0, by + 1
        while y < h and px[y * w + x] < thresh:
            run += 1
            y += 1
        if tick_min <= run <= tick_max:
            tx.append(x)
    y_a, y_b = axis_box["left_span"]
    ty = []
    for y in range(y_a, y_b + 1):
        run, x = 0, bx - 1
        while x >= 0 and px[y * w + x] < thresh:
            run += 1
            x -= 1
        if tick_min <= run <= tick_max:
            ty.append(y)
    # 合并相邻（<3px）的检测
    def merge(vs):
        out = []
        for v in sorted(vs):
            if out and v - out[-1] < 4:
                out[-1] = (out[-1] + v) // 2
            else:
                out.append(v)
        return out
    return {"x_ticks_px": merge(tx), "y_ticks_px": merge(ty)}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--thresh", type=int, default=120)
    a = ap.parse_args()
    im, px = load_gray(a.image)
    box = find_axes(im, px, a.thresh)
    if not box:
        json.dump({"status": "failed", "reason": "未找到连续的轴线，可能是无框散点图，改用 --manual 边界"},
                  open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("FAILED: no axes found")
        return 1
    ticks = find_ticks(im, px, box, a.thresh)
    box.update(ticks)
    box["status"] = "ok"
    box["notes"] = [
        "top_y/right_x 为 None 表示该边无框，绘图区边界要用对侧轴 + 刻度范围估计",
        "x_ticks_px/y_ticks_px 是刻度线的像素位置（已合并相邻检测），"
        "数值由 Agent 从原图读出后按同序号对应写入标定文件",
    ]
    json.dump(box, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("axes ok: left_x=%s bottom_y=%s top_y=%s right_x=%s ticks x=%d y=%d"
          % (box["left_x"], box["bottom_y"], box["top_y"], box["right_x"],
             len(box["x_ticks_px"]), len(box["y_ticks_px"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
