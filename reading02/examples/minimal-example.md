# 最小调用示例（示意输出，非正式案例结果）

## 输入

`examples/demo-chart.png`：800×600 曲线图，线性轴 x∈[0,40]、y∈[0,100]，
一条红色曲线（rgb 214,39,40），问题："曲线在 x=20 处的值是多少？衰减一半要多久？"

## 调用

```bash
python3 scripts/c2d_axes.py --image examples/demo-chart.png --out axes.json
# Agent 读刻度: x 轴 90px→0、760px→40；y 轴 540px→0、60px→100 → 写 calib.json
python3 scripts/c2d_trace.py --image examples/demo-chart.png --calib calib.json --out curve.csv
python3 scripts/c2d_overlay.py --image examples/demo-chart.png --csv curve.csv --out overlay --report report.json
```

## 示意输出（节选自真实运行，见 compare.md）

curve.csv（前 3 行）：

```
series,x,y,y_unc,x_px,y_px,dropped_segments
decay,0.0625,99.375,0.52,91,77.5,0
decay,0.125,99.375,0.52,92,77.5,0
decay,0.1875,99.271,0.52,93,78.0,0
```

result.json 关键字段（示意）：

```json
{
  "chart_reading": {
    "axes": {"x": {"type": "linear", "unit": "未标注", "range": [0, 40]},
             "y": {"type": "linear", "unit": "未标注", "range": [0, 100]}},
    "direct_readable": [
      "x=20 处 y≈13.1（curve.csv 第 321 行，x_px 330，y_unc 0.21）",
      "曲线单调衰减，无回升（672 点连续，最大断档 1px）"
    ],
    "inference": [
      "按指数衰减拟合 ln(y) 对 x 的斜率 ≈ -0.125（R²=1.00），即 x=8 时减半；"
      "此为从提取数据推断，非图中标注"
    ],
    "cannot_determine": ["轴单位图中未标注"]
  },
  "status": "ok",
  "uncertainty": [
    {"what": "y<1 的尾部点", "why": "线宽量化，绝对误差约 ±0.16，相对误差在此区间无意义",
     "how_checked": "与真值函数对表（compare.md）"}
  ]
}
```
