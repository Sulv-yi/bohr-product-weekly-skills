# 证据映射与不确定性标注

## 证据格式

每条来源条目：

```json
{
  "id": "s-003",
  "claim": "该工作在该数据集上报告 82% 准确率",
  "file": "paper_a.pdf",
  "page": 4,
  "section": "4.1 Results",
  "quote": "Our method achieves 82% accuracy on ..."
}
```

quote 必须逐字来自原文；转述/改写类产物同样附原文引用。

## 三类边界

| 类型 | 含义 | status 影响 |
|---|---|---|
| `not_reported` | 材料里没有该事实/引用 | partial |
| `undetermined` | 有材料但读不出或需人工确认 | partial |
| `conflict` | 材料内部两处不一致 | partial |

每条写清 item / type / reason / 位置（若有）。

## 状态

- `success`：完成，证据齐全。
- `partial`：完成主要部分但有明确缺口。
- `blocked`：无法开始（材料损坏/加密无密码），说明人工接管点。
- `unanswerable`：材料充分但确实无法回答，说明依据。

## 禁止

- 不编造事实、数字、引用元数据、图表编号。
- 不把他人结果写成本文结果。
- 不编造运行日志或评分。
