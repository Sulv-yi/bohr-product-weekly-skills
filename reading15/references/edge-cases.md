# 边界案例与异常处理

| 情况 | 处置 |
|---|---|
| PDF 无法解析 | status=unable，说明原因与人工接管点；不据标签臆造正文 |
| material 缺 source_id/paragraph_id | build_skeleton 发 warning；补字段再建图，不猜来源 |
| 无 PDF 页码、只有 JATS 段 ID | 用 paragraph_id；严禁写 p.1/page 1/第1页冒充 |
| 行内公式/上下标被线性化 | 按线性化文本记录，不推断未提供的数值 |
| 无图像/补充/底层数据 | 不推断其中数值；写 uncertainty |
| 查询无结果 | result_subgraph 可空 + empty=true + uncertain 说明，不造边 |
| 同名实体跨篇 | 默认独立节点 + conflict；有显式身份依据才 merge |
| 源内冲突 | 写 conflicts/uncertainty，不合成一个结论 |
| 候选误入最终结果 | verify_graph 检出 candidate=true 报错 |
| 重复运行 | 稳定编号；graph.json 可比对差异 |
