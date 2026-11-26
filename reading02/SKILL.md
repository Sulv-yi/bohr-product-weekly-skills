---
name: chart2data
description: |
  科研图表解析：从论文曲线图/统计图中提取带不确定度的结构化数据。
  脚本负责像素测量与标定换算（纯 PIL，不依赖 numpy/opencv/tesseract），
  Agent 负责读刻度数值、图例与图注。输出 CSV + 叠加自查图 + result.json，
  每个数值带像素证据列，误差口径明确到半个像素。
---

# 图表取数 Skill（chart2data）

## 分工原则（为什么这样设计）

视觉模型直接"读曲线"经常编数字：它看到趋势，但给不出可复核的坐标。
本 Skill 把两件事拆开——

| 谁做 | 做什么 | 为什么 |
|---|---|---|
| **脚本** | 定位轴线/刻度像素位置、按颜色/灰度逐列扫曲线、像素↔数据换算、不确定度、叠加自查图 | 像素测量必须可复现，模型做这个不可靠 |
| **Agent（视觉）** | 读刻度上的数字、判断轴类型（线性/对数）、读图例对应哪条线、认出显著性标记 | 识别文字和语义是模型的强项 |

脚本永远不猜数值，Agent 永远不报像素位置。

## 调用流程

```
输入: 一张图表图片 (PNG/JPG) + 图片里的问题
 1. c2d_axes.py   --image 图.png --out axes.json
    → 轴线与刻度的像素位置。0 个刻度时改用 Agent 目测边界，
      在标定文件里手写 px（并在 uncertainty 里记"边界为目测"）。
 2. Agent 看 axes.json + 原图，写 calib.json：
    x/y 各给两个参考点 (px, val)，log=true 表示对数轴；
    series 里每条线给 mode=color+rgb（彩色图）或 mode=dark（黑白主线）。
    刻度数值与 axes.json 里的 x_ticks_px 按位置顺序一一对应。
 3. c2d_trace.py  --image 图.png --calib calib.json --out curve.csv
    → 数据坐标 CSV，每行带 x_px/y_px 证据列和 y_unc 不确定度。
 4. c2d_overlay.py --image 图.png --csv curve.csv --out overlay --report report.json
    → 提取点画回原图的 PNG + 质量报告（断档/撞色统计）。
 5. Agent 看叠加图自查：点是否贴合原曲线？断档区（max_gap_px>30）
    要回原图解释原因（遮挡/图例框撞色/曲线出界）。
 6. 按"输出契约"写 result.json。
```

## 输出契约

每个案例返回一份 result.json，字段固定：

```json
{
  "case_id": "...",
  "chart_reading": {
    "axes": {"x": {"type": "linear|log", "unit": "...", "range": [a, b]},
             "y": {"type": "...", "unit": "...", "range": [a, b]}},
    "series": [{"name": "图例原文", "color_evidence": "rgb(214,39,40) 在 x_px 240-672",
                "points": "见 curve.csv", "n": 672}],
    "direct_readable": ["图中直接可读的结论，逐条附像素证据"],
    "inference": ["合理推断，注明依据与置信度"],
    "cannot_determine": ["无法判断的项 + 缺什么信息"]
  },
  "evidence": "axes.json + curve.csv + overlay.png 的路径与关键行",
  "status": "ok | partial | failed",
  "uncertainty": [
    {"what": "尾部 x>36 的 y 值", "why": "线宽量化，绝对误差约 ±0.16 数据单位，相对误差在此区间无意义",
     "how_checked": "overlay.png 目测 + 真值对表"}
  ]
}
```

三类陈述（直接可读 / 推断 / 无法判断）**必须分开**，混写视为错误。

## 误差口径（固定，不得改口）

- 每个 y 值的不确定度 = 半像素 + 同列像素散布，换算到数据单位，写在 y_unc 列。
- 报相对误差时必须同时给绝对误差：值小于 2 个不确定度时只报绝对误差。
- 对数轴换算在 log10 空间线性插值（c2d_trace 已实现），不确定度同样在 log 空间报。

## 已知边界与异常处置

| 情况 | 处置 |
|---|---|
| 无框图（只有左/下轴） | axes.json 的 top_y/right_x 为 null，绘图区按刻度范围估计，uncertainty 记录 |
| 找不到轴线 | c2d_axes 返回 failed；改用 Agent 目测边界手写 px |
| 图例框与曲线同色 | trace 已按"最长段"丢弃撞色段并计数（dropped_segments 列），结果里如实报告 |
| 曲线重叠 | 只报最上层的，其余记 cannot_determine，不硬拆 |
| 分辨率 < 300px | 直接拒答（status=failed）：半个像素的误差会超过数据有效位 |
| 显著性标记/误差线 | Agent 读出来写进 direct_readable，带像素位置；不试图转成数值 |

## 文件清单

- scripts/c2d_axes.py — 轴线与刻度像素定位（纯 PIL）
- scripts/c2d_trace.py — 标定换算 + 逐列扫描 + CSV 输出（纯 PIL）
- scripts/c2d_overlay.py — 叠加自查图 + 质量报告（PIL）
- scripts/make_demo.py — 生成已知真值的测试图（自检用）
- src/reproduce.py — 一键跑通 demo 全流程
- examples/ — demo 图、真值、标定、对表记录
- references/ — 对数轴/统计图/多子图的补充规则
