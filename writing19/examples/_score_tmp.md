# 导图自查报告

案例：merillas-2026-rpet-foam　节点 21、关系 6、待确认 4

**结构分 100.0 / 100（10/10 项通过，0 处问题）**

结构分只衡量「能不能用」，不等于平台评分；它用来在提交前挡住「回不到原文、层级失控、关系无据」这三类硬伤。

| 项 | 结论 | 说明 |
|-|-|-|
| C1 schema | PASS | 缺字段 0 处、重复 id 0 个 |
| C2 树结构 | PASS | 单根 + 无环 + 父节点存在 |
| C3 覆盖 | PASS | root=1 / question=2 / method=5 / evidence=5 / conclusion=3 / limitation=3 / task=2 |
| C4 类型取值 | PASS | 仅允许 root/question/method/evidence/conclusion/limitation/task |
| C5 标题 | PASS | 3–40 字、不重复、不空话 |
| C6 证据 | PASS | 全部引用 blocks.json 中真实存在的块 |
| C7 数字 | PASS | 标题数字逐个在原文中命中 |
| C8 层级粒度 | PASS | 最大深度 3、最大扇出 6、同层长度 CV 2:0.05, 3:0.13 |
| C9 关系 | PASS | 6 条，类型 conflict,contrast,depend,sequence,support |
| C10 推断标注 | PASS | 2 个 inference 已登记、4 条不确定说明 |

## 待修项

无。全部 10 项通过。

## 节点类型分布

| 类型 | 数量 |
|-|-|
| root | 1 |
| question | 2 |
| method | 5 |
| evidence | 5 |
| conclusion | 3 |
| limitation | 3 |
| task | 2 |
