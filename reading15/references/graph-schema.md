# 图谱数据结构（graph schema）

## 节点 node

| 字段 | 必需 | 说明 |
|---|---|---|
| id | 是 | 稳定编号 n001...；增量更新时保留既有编号 |
| label | 是 | 原文表述，不用常识补全 |
| type | 是 | researcher/material/method/task/metric/conclusion |
| mention_role | 建议 | author_self（作者自述）/ other_paraphrase（他人转述） |
| aliases | 否 | 缩写/全称/大小写变体 |
| confidence | 否 | high/medium/low |
| evidence | 是 | 数组：source_id + paragraph_id + quote + strength(direct/indirect) |

## 边 edge

| 字段 | 必需 | 说明 |
|---|---|---|
| id | 是 | 稳定编号 e001... |
| subject / object | 是 | 节点 id，方向 subject->object |
| relation | 是 | 受控词表 canonical（见 relation_vocab.json） |
| conditions | 建议 | metric/value/dataset/section 等适用条件 |
| evidence_type | 建议 | direct（禁止 cooccurrence/speculation 等） |
| evidence | 是 | 同节点证据结构 |

## 对齐 alignments / 冲突 conflicts

- alignment：`from`（别名节点）→ `to`（规范节点），`action=merge|suggest`，`identity_basis` 必填。
  - 合法依据：同篇同段缩写=全称、作者明示 "hereafter X"、 DOI/版本一致。
  - 非法依据：两篇都出现同名通用术语（如 "CNN"、"dataset D"、"accuracy"）。
- conflict：`nodes: [...]`，`reason` 说明为何不得合并（样本/条件/数值/对象不同）。

## 查询 query

`question` + `result_subgraph{nodes[],edges[]}` + `evidence[]` + `uncertain[]`。
无结果时 `result_subgraph` 可空，但须在 note/uncertain 写明"确实无结果"，不得造边。

## 证据强度

- direct：原文直接陈述该实体/关系。
- indirect：需一步推断；必须在 uncertainty 标注，不得单独支撑高置信结论。
