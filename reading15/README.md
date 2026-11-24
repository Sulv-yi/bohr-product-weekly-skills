# 文献知识图谱构建 Skill

从两篇独立科研论文中构建带证据的可查询知识图谱。四关注点：抽得准 / 连得对 / 对得齐 / 查得到回得去；严格防跨篇污染。

## 目录

- `SKILL.md`：主说明（用途、输入输出、工作流、防污染约束、异常处理）。
- `scripts/`
  - `probe_pdf.py`：PDF 文本块探查（复用，可选）。
  - `build_skeleton.py`：从 manifest + material 建图谱骨架，登记每篇真实元数据。
  - `extract_entities.py`：候选实体抽取（candidate=true，绑定 source_id/paragraph_id/quote）。
  - `verify_graph.py`：**核心核验**（四性质 + 防污染 P1-P7）。
  - `query_graph.py`：5 类真实查询模板。
  - `export_graph.py`：导出 nodes.jsonl/edges.jsonl/graph.json。
  - `validate_result.py`：结果结构契约校验。
- `assets/relation_vocab.json`：受控关系词表；`assets/entity_types.json`：实体类型白名单。
- `references/`：图 schema、关系证据规则、对齐冲突、查询增量、边界案例。
- `examples/minimal-example.md`：完整最小调用示例（示意）。

## 依赖

Python 3 标准库，无需第三方包。

## 使用顺序

1. build_skeleton → 2. extract_entities → 3. Agent 判定填图 → 4. query_graph → 5. verify_graph → 6. export_graph → 7. validate_result。

## 关键规则

- 位置用 JATS `paragraph_id`，不是 PDF 页码。
- 根 DOI/title/authors 只属第一篇，secondary 用自身元数据。
- 跨篇同形通用术语不得仅凭同名合并；数值/样本/条件不得跨篇拼接。
- 每条边直接证据 + 受控 relation；共现/转述/推测/常识不得当关系。
- 至少 3 个真实查询，每个可回源；无结果如实说明。

## GitHub

`https://github.com/Sulv-yi/bohr-product-weekly-skills/tree/main/reading15`
