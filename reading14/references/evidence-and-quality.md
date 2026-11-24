# 证据绑定与质量检查

## 最小充分证据

- 证据片段要"刚好够"支撑断言：不多到含无关信息，不少到缺关键限定。
- `text` 必须是原文逐字片段；verify_nanopub.py 规范化后（忽略大小写/标点/空白）回原文匹配，匹配不到即 aligned failed。
- 数值型断言的证据片段必须含该数值；结论型断言的证据含结论句。
- 图表里的证据：位置写 `Fig.2 / Table1`，若图表内容为图片未文本化，type 标 indirect 并在 uncertainty 说明。

## 直接 vs 间接

| type | 含义 | 例 |
|---|---|---|
| direct | 原文直接陈述该断言 | "Method M reaches 92.5% accuracy" 支撑 c01 |
| indirect | 需一步推理或来自图表/上下文 | 图2趋势支撑"准确率随epoch上升" |

因果断言（relation=causes）若只有 indirect 证据 → confidence 不应为 high，verify 会告警。

## 质量标记（对应题面质量检查方向）

| flag | 判定 | 处理 |
|---|---|---|
| over_broad | 断言无 conditions 但原文有范围限定 | 补 conditions 或缩小 object |
| insufficient_evidence | 证据片段过短/仅 indirect/与断言无关 | 补证据或降级 confidence |
| wrong_relation | 相关写成因果、方向反了 | 换 canonical，改 subject/object 顺序 |
| subject_confusion | 主体缺失/张冠李戴 | 按原文核定 subject |
| missing_source | 来源字段缺失 | 补 unknown + uncertainty |

## 去重与合并

- 同一 (subject, relation, object) 只保留一条；证据片段可多条。
- 同义关系（improve/提升/increase）归一到同一 canonical 后再判重。
- 数值不同但主体关系相同的两条（如不同数据集上的同一方法）不合并，用 conditions 区分。

## 与 verify_nanopub.py 报错对照

- `证据片段无法在原文匹配` → quote 被改写/翻译/抄错，回原文逐字复制。
- `relation 不在受控词表` → 换 canonical 或在词表加别名（需有依据）。
- `source 缺 X` → 补字段，未知写 unknown + uncertainty。
- `疑似复合断言未拆` → 拆成多条。
- `id 缺失或重复` → 分配唯一 id。
