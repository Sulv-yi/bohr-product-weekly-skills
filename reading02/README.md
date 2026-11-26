# chart2data — 科研图表取数 Skill

把论文里的曲线图/统计图读成带不确定度的结构化数据（CSV），
每个数值可以指回原图的像素位置，并自动生成叠加自查图。

## 为什么不是"让多模态模型直接读图"

多模态模型看图能说对趋势，但报出的数值经常编造且无法复核。
本 Skill 把任务拆成两半：

- **脚本（纯 PIL，无 numpy/opencv/tesseract 依赖）**：轴线定位、刻度像素测量、
  逐列扫线、像素↔数据换算、不确定度合成、叠加自查图。
- **Agent（视觉）**：读刻度数值、判轴类型（线性/对数）、认图例、读显著性标记。

脚本不猜数值，Agent 不报像素——各自的输出都有对方做不了的部分。

## 实测精度（demo：y = 100·exp(−x/8)，800×600 图）

| 指标 | 数值 |
|---|---|
| 轴线定位 | left_x=90, bottom_y=540，与真值零偏差 |
| 刻度定位 | x 9 格 / y 6 格，间隔与真值一致 |
| 提取点数 | 672（无断档，撞色丢弃 0） |
| **中位绝对误差** | **0.08 数据单位**（y 满量程 100，即 0.08%） |
| 尾部（y<1） | 绝对误差 ≈0.16 单位（≈0.8 像素），为线宽量化极限，如实记录不美化 |

对表明细见 `examples/compare.md`，叠加自查图见 `examples/demo-overlay.png`。

## 快速开始

```bash
# 一键复现（生成→定轴→标定→提取→叠加→与真值对表）
python3 src/reproduce.py --work /tmp/c2dw --out /tmp/c2do
```

在自己的图上用（完整流程见 SKILL.md）：

```bash
python3 scripts/c2d_axes.py  --image fig.png --out axes.json
# Agent 看 axes.json 和原图，写 calib.json（刻度数值、轴类型、曲线颜色）
python3 scripts/c2d_trace.py  --image fig.png --calib calib.json --out curve.csv
python3 scripts/c2d_overlay.py --image fig.png --csv curve.csv --out overlay --report report.json
```

## 输出

- `curve.csv`：series, x, y, y_unc, x_px, y_px, dropped_segments
  —— x/y 是数据坐标，x_px/y_px 是可回查的像素证据，y_unc 是不确定度。
- `overlay.png`：提取点画回原图，评审一眼可判断贴合度。
- `report.json`：各系列点数、最大断档、撞色统计。

## 误差口径

每个 y 值的不确定度 = 半像素 + 同列像素散布，换算到数据单位。
值小于 2 个不确定度时只报绝对误差，不报相对误差（避免"23% 误差"这种
其实是 0.16 个单位的误导性表述）。对数轴在 log10 空间报不确定度。

## 限制

- 只处理栅格图（PNG/JPG），不解析矢量 PDF 内嵌数据。
- 曲线重叠时只取最上层，其余记 cannot_determine，不硬拆。
- 图宽 < 300px 拒答：半像素误差会超过数据有效位。
- 显著性标记、误差线帽由 Agent 读数值，脚本不做 OCR。

## 目录

```
SKILL.md                  Agent 调用说明（评分主文档）
scripts/c2d_axes.py       轴线与刻度像素定位
scripts/c2d_trace.py      标定换算 + 逐列扫描 + CSV
scripts/c2d_overlay.py    叠加自查图 + 质量报告
scripts/make_demo.py      生成已知真值的测试图
src/reproduce.py          一键复现
examples/                 demo 图、真值、对表记录、叠加图
references/               对数轴/统计图/多子图规则、边界情况
```
