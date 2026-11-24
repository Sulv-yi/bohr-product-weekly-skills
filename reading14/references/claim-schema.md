# Nanopublication 字段字典

## 顶层 result.json

| 字段 | 类型 | 说明 |
|---|---|---|
| `case_id` | str | 原样来自 case.json |
| `status` | enum | success / partial / unable / refused |
| `result.nanopublications` | list | 断言单元数组，每条见下 |
| `sources` | list | 顶层证据登记 `{source_id, location, quote}` |
| `uncertainty` | list[str] | 未报告/无法判断/材料冲突，三类分开 |
| `changes` | list[str] | 处理动作留痕 |

## nanopublication 三分区

### assertion（断言，拆得细）
| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 全篇唯一，如 np-001 |
| `subject` | 是 | 断言主体（方法/变量/数据集/作者） |
| `relation` | 是 | 受控词表 canonical，见 assets/relation_vocab.json |
| `object` | 是 | 断言客体（数值/结论/另一实体） |
| `claim_text` | 是 | 断言的原文或贴近原文的陈述句 |
| `conditions` | 建议 | 成立条件/适用范围；因果与增减断言必填 |
| `confidence` | 建议 | high / medium / low |
| `confidence_basis` | 建议 | 置信度判定依据（直接证据/数值明确/仅推论） |

### provenance（溯源，对得上 + 追得回）
| 字段 | 必填 | 说明 |
|---|---|---|
| `evidence` | 是 | 数组，每条 `{text, location, type}` |
| `evidence[].text` | 是 | 原文逐字片段（规范化后可匹配） |
| `evidence[].location` | 是 | 页码/段落/图表/字段位置 |
| `evidence[].type` | 是 | direct / indirect |
| `source.paper` | 是 | 论文标题 |
| `source.authors` | 是 | 作者列表；无则 `["unknown"]` |
| `source.year` | 是 | 年份（四位） |
| `source.version` | 建议 | 版本/预印本号 |
| `source.identifier` | 是 | DOI/PMID/arXiv ID；无则 `"unknown"` |
| `source.data_source` | 建议 | 数据来源 |

### publication_info
`created_by`（产出者/Agent）、`created_at`（时间）。

## 关系受控词表

见 `assets/relation_vocab.json`。核心 canonical：
reports / increases / decreases / causes / correlates_with / outperforms / achieves / is_a / requires / limits / contradicts。

别名（如 "improve"/"提升"→increases，"相关"→correlates_with）由 verify_nanopub.py 归一；不在词表的关系判 machine failed。

## 粒度判据

- 一条断言只回答一个问题："谁（subject）对什么（object）做了什么/是什么（relation）"。
- 并列连词（and/or/此外/同时）连接的多个客体 → 拆成多条。
- 因果链（A 导致 B，B 提升 C）→ 拆成两条，各自绑定证据。
- 条件/限定（在条件C下、仅数据集D）写入 conditions，不丢进 object 造成断言过宽。
