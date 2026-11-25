# 提示词 A2 · 结论绑定（一条结论一行）

目的：把"读后结论"变成可核对的记录，避免结论里出现原文没有的数。

```
读 materials/paper.md，只做一件事：把论文里所有"带数字的结论"抽成条目，
每条写成一个 CSV 行，列为：

claim_id, subject, metric, value, page, quote, claim

- subject：这条讲的是哪种料（PET_V / PET_B / PET_C / 3D-printed / none）
- metric：relative_density / cell_size / mfi / density_reduction / none
- value：这条结论里的数值（多个用逗号，区间写两端）
- page：你从 page 锚点读到的页码
- quote：支撑这条结论的原文片段，逐字复制，不改写、不拼接、不跨页
- claim：你自己的中文表述

硬性要求：
1. quote 必须能在 paper.md 里逐字找到；找不到就说明你记错了，重读原文。
2. 摘要里的数字和结果段的数字分开记条目，不要合并成一条。
3. 拿不准的写成 metric=none，不要硬塞进某个指标。
```
