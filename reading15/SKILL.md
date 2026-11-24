---
name: literature-knowledge-graph
description: 文献知识图谱构建 Skill。从两篇独立科研论文材料中抽取实体与关系、绑定原文证据、做别名对齐与冲突保留、支持真实查询与可读图谱导出。适用于需要从论文批量构建带证据的知识图谱并回答查询的场景。核心保证：抽得准、连得对、对得齐、查得到回得去，并严格防止跨篇污染（根 DOI 复用、PDF 页码冒充 JATS 段 ID、跨篇数值拼接、通用术语同名错误合并）。
---

# 文献知识图谱构建 Skill

从论文材料构建**可核验、可查询、可回源**的最小知识图谱工作流。聚焦一个明确问题：把一批论文转成"带证据的节点与边"，并保证每个节点/边能回到论文的具体段落与原文片段。

## 何时使用 / 不适用

- **适用**：给定 1~N 篇论文文本/段落索引，需要抽取科研实体（研究者/材料/方法/任务/指标/结论）、建立有证据的关系、处理别名与同名冲突、回答查询并导出图谱。
- **不适用**：需要推断材料未报告的数值/图像/底层实验数据；材料无法解析且无其他来源时（应返回 `unable` 并说明，不臆造）。

## 输入

平台固定案例提供：
- `/input/case.json`：`case_id`、`task`、`output_contract`（通常含 `graph`、`queries` 或等价字段）。
- `material.json`：两篇正文段落汇总索引（每段含 `paragraph_id`、`source_id`、`text`，可能含 `section`）。
- `corpus-manifest.json`：各论文 `source_id`、`doi`、`title`、`authors`、`source_hash`、`license`；根 `root` 字段只描述第一篇。
- `primary-material.json` / `secondary-material.json`：两篇原文，可按 `source_id` 回溯。

## 输出

`/app/output/result.json`（字段对应 `output_contract`）：

```jsonc
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "graph": {
      "nodes": [{
        "id": "n001", "label": "Method M", "type": "method",
        "mention_role": "author_self | other_paraphrase",
        "aliases": ["M"], "confidence": "high",
        "evidence": [{"source_id": "primary", "paragraph_id": "p3",
                      "quote": "原文短引", "strength": "direct | indirect"}]
      }],
      "edges": [{
        "id": "e001", "subject": "n001", "relation": "outperforms", "object": "n003",
        "conditions": {"metric": "accuracy", "value": "92.5%", "dataset": "D"},
        "evidence_type": "direct",
        "evidence": [{"source_id": "primary", "paragraph_id": "p3", "quote": "...", "strength": "direct"}]
      }],
      "alignments": [{"from": "n005", "to": "n001", "action": "merge",
                      "identity_basis": "同一段缩写=全称，同 source，非跨篇同形"}],
      "conflicts": [{"nodes": ["n002", "n006"], "reason": "同名数据集但样本/条件不同，不得合并"}]
    },
    "queries": [{
      "question": "...", "result_subgraph": {"nodes": [...], "edges": [...]},
      "evidence": [{"source_id": "...", "paragraph_id": "...", "quote": "..."}],
      "uncertain": [{"edge": "...", "reason": "..."}]
    }]
  },
  "sources": {...},
  "uncertainty": [...],
  "changes": [...]
}
```

## 工作流（严格顺序）

1. **探查与骨架**：`scripts/probe_pdf.py`（若给 PDF）→ `scripts/build_skeleton.py --manifest ... --material ... --case case.json --out skeleton.json`。确认清单登记 ≥2 篇来源、段落索引非空。
2. **候选抽取**：`scripts/extract_entities.py --material material.json --out candidates.json`。输出 `candidate=true` 的候选，**不是最终答案**；关注 `cross_source_surfaces`（跨篇同形术语）。
3. **人工/Agent 判定并填图**：为每个节点定 `type`/`mention_role`/`aliases`、绑定真实 `source_id`+`paragraph_id`+原文 `quote`；为每条边定受控 `relation`+方向+`conditions`+直接证据；为别名写 `alignments`（带 `identity_basis`），为不得合并的对象写 `conflicts`。**至少 3 个真实查询**。
4. **查询**：`scripts/query_graph.py result.json --out query_results.json`（内置 5 类查询模板：邻居/关系/结论证据链/跨篇同形/单篇视图）。把实际执行结果写回 `result.queries`。
5. **核验（核心）**：`scripts/verify_graph.py result.json --material material.json --manifest corpus-manifest.json --vocab assets/relation_vocab.json --case case.json --out verify.json [--strict]`。有 error 必须修复；warning 要么修复要么写入 `uncertainty`。
6. **导出**：`scripts/export_graph.py result.json --out-dir graph_export`（输出 nodes.jsonl/edges.jsonl/graph.json）。Office/图预览如需可渲染，但本 Skill 交付以 JSON 图谱为主。
7. **契约校验**：`scripts/validate_result.py result.json --case case.json`。通过后交付。

## 四个关注点如何被脚本保证

| 关注点 | 脚本保证 |
|---|---|
| 抽得准 | `verify_graph.py` 校验每个节点 type 在白名单、有 source_id+paragraph_id+quote，短引规范化回查段落原文；`candidate=true` 的候选不得混入最终节点 |
| 连得对 | relation 必须命中受控词表；禁止 `cooccurrence/review_paraphrase/speculation/common_knowledge` 作证据；`outperforms` 必须有 metric；跨篇数值结论边直接判错 |
| 对得齐 | `same_as`/alignments 必须带 `identity_basis`；跨篇同形术语默认保持独立节点，`conflicts` 记录不得合并对象 |
| 查得到回得去 | 至少 3 个查询，每个带结果子图+证据；每节点/边 evidence 精确到 source_id + paragraph_id + quote |

## 防污染硬约束（题面“输入修订”，必须遵守）

1. **根 DOI/title/authors 只属于第一篇**；secondary 不得复用根元数据，每篇用各自 `source_id` 与自身 DOI/作者。
2. **位置用 JATS `paragraph_id`**（如 `p3`、`sec2.p1`），不得写 `p.1`/`page 1`/`第1页` 冒充 PDF 页码——本包无 PDF 页码。
3. **不得跨篇拼接**：不同论文的样本/条件/数值结果不能合成一个结论；同一通用术语≠同一物理样品/模型实例/数据集/实验条件。
4. **同篇多格式不算跨篇证据**：primary-material.json 与某同篇 Markdown 属同一来源，不算两篇。
5. **不推断未提供的数值**：行内公式/上下标已线性化；无图像像素、补充附件、底层临床/实验数据，不据此推断数值。
6. **未报告与源内冲突明确保留**：写入 `uncertainty` / `conflicts`，不写成事实。

## 异常处理

- PDF 无法解析：写 `status=unable`，说明原因与可人工接管位置，不用标签臆造正文。
- 材料缺 source_id/paragraph_id：`build_skeleton.py` 会发 warning；补字段后再建图，不猜测来源。
- 查询无结果：`result_subgraph` 可为空但须 `empty=true` 且在 `uncertain` 说明，禁止造边。
- 重复运行：`build_skeleton.py` 每次重建骨架，节点 id 用稳定规则（如 `n001`），支持增量更新时保留既有编号。

## 资源

- `assets/relation_vocab.json`：受控关系词表（canonical/别名/方向/证据强度门槛）。
- `assets/entity_types.json`：实体类型白名单与证据规则。
- `references/`：图 schema、关系与证据规则、实体对齐、查询与增量更新、边界案例。
- `examples/minimal-example.md`：一组完整最小调用示例（示意输出已标注）。

依赖：Python 3 标准库（json/re/argparse/os），无需第三方包。脚本均可用 `python3 scripts/<name>.py --help` 查看参数。
