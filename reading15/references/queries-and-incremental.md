# 查询与增量更新

## 至少 3 个真实查询

推荐覆盖（query_graph.py 内置 5 类）：
1. 实体 1 跳邻居：验证图连通性与证据绑定。
2. 关系类型检索（如所有 outperforms 边）：验证关系约束。
3. 结论证据链：从结论节点回溯支撑/反驳证据到 paragraph_id。
4. 跨篇同形术语：检查是否错误合并或正确保留冲突。
5. 单篇视图（source_id 过滤）：验证无跨篇污染。

每个查询必须写回实际执行结果（result_subgraph + evidence + uncertain）。无结果如实写 empty。

## 增量更新

- 新论文加入时：保留既有节点 id 与编号；新增节点用下一个可用 id。
- 新增候选与既有节点比较：可合并写 alignment + identity_basis；冲突写 conflict。
- 不删除既有边；如新证据推翻旧关系，标注 uncertain 而非静默覆盖。
- 导出 graph.json 保留 alignments/conflicts，便于跨次运行核对。
