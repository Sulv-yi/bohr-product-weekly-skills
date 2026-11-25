# 语义边界：否定、情态与限定条件

## 1. 三类边界，三种错法

| 类型 | 原文 | 错译 | 为什么错 |
|---|---|---|---|
| 否定范围 | `did not differ significantly` | 差异显著 | 结论反了 |
| 情态强度 | `may be associated with` | 导致了 | 相关性变因果 |
| 限定条件 | `in vitro` / `pilot` / `single-centre` | 省略 | 结论外推到不该外推的范围 |

这三类错误有一个共同点：**读起来更顺、更像结论**，所以机器翻译和赶工的译稿特别容易犯。

## 2. 否定

- 英语否定常在谓语上（`did not`、`cannot`），中文可落在"未/不/无/未见/无法"上，位置可变，**语义不能丢**。
- `not all` ≠ `none`：前者是"并非全部"，后者是"全都没有"。
- `cannot exclude` 是"无法排除"，不是"可以排除"——这是译文里最高频的翻转。
- `no significant difference` 译"未见显著差异"，不写"无差异"（后者是更强的主张）。

## 3. 情态与归因

| 弱 | 中 | 强（慎用） |
|---|---|---|
| `may` / `might` / `could` | `suggest` / `appears to` / `is consistent with` | `demonstrates` / `proves` / `causes` |
| 可能 / 或许 | 提示 / 似乎 / 与…一致 | 证明 / 导致 / 决定 |

规则：**只能平移，不能升级**。原文用弱情态，译文必须用弱情态；原文用强情态，译文可以按学
科惯例略降（如 `demonstrates` → "表明"），但降级要在 `human_review` 里记一笔。

`associated with` / `correlated with` 一律译"相关/伴随"，不译"导致/引起"。

## 4. 限定条件清单

译文中必须跟着走、不能省的范围词：

- 实验层级：`in vitro`（体外）、`in vivo`（体内）、`ex vivo`（离体）
- 样本属性：`murine`（小鼠）、`rat`（大鼠）、`human`（人源）
- 研究阶段：`pilot`（预实验）、`preliminary`（初步）、`exploratory`（探索性）
- 设计限制：`single-centre`（单中心）、`retrospective`（回顾性）、`cross-sectional`（横断面）
- 时间/剂量范围：`up to 7.0 wt%`（至 7.0 wt%）、`within 24 h`（24 h 内）

`up to X` 是"不超过 X"，不是"达到 X 以上"；`at least` 反之。这类边界词一个都不能省。

## 5. 增译与省译

- **增译**只允许补语法必需成分（量词、连接词）与读者必需的解释性同位语；补出的内容在
  `changes` 里标 `added`，不得引入原文没有的事实、数值或结论。
- **省译**只允许省重复的过渡语与冗余修饰；省掉限定条件、否定、引用、数值一律算错。

## 6. 检查口径

`boundary_check` 报三类：`negation_dropped`、`strength_up`、`scope_dropped`，
每条带段号与具体词。门槛是"改动 ≤1 条"，因为极少数情况下中英表达习惯确实要求微调，
但**不允许成批出现**——成批出现说明译者在"改写"而不是"翻译"。
