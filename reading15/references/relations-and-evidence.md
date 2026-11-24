# 关系与证据规则

## 关系方向速查

- uses：researcher|method → material|method|dataset|task
- compares_with：method → method|baseline（不含优劣）
- outperforms：method → method|baseline（必须带 metric + value + dataset + 条件）
- supports / contradicts：evidence|result → conclusion|claim
- measures：metric → task|method|result
- requires：result|method → condition|material（含作者自述局限）
- is_part_of：component → whole
- same_as：alias → canonical_entity（必须带 identity_basis）

## 禁止当关系的情况

- **共现**：两个术语出现在同一段但没有明确关系陈述。
- **综述转述**：作者写 "Smith reported..."，这是他人工作，不能当本文证据；标 `mention_role=other_paraphrase` 且不建立本文直接关系。
- **推测**："may/might/suggest" 未确证，写入 uncertainty。
- **常识补全**：材料未出现的概念，不抽取。

## 证据三要素

1. `source_id`：具体是哪篇（primary / secondary，或清单中的其他 id）。
2. `paragraph_id`：JATS 段落 ID，不是 PDF 页码。
3. `quote`：原文短引，可被规范化回查。

每条边至少一条 direct 证据。indirect 证据只能作为补充并写 uncertainty。
