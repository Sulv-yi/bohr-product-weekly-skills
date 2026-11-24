# 笔记字段字典与锚点格式

## paper_card 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | str | 建议 | 论文标题，原样 |
| venue_year | str | 建议 | 发表处/年份 |
| research_question | list[item] | 必填 | 研究问题/目标 |
| data | list[item] | 必填 | 数据/样本/来源/规模 |
| method | list[item] | 必填 | 方法/模型/实验条件/超参 |
| findings | list[item] | 必填 | 主要发现，每条带 conditions |
| limitations | list[item] | 必填 | 局限 |
| premises | list[item] | 建议 | 让结论成立的前提条件（可单列） |

item 结构：`{"text": "笔记正文", "conditions": "（仅 findings）成立前提/适用范围", "source_ids": ["s1","s2"]}`。
未报告：`text` 写"未报告"，并往顶层 `uncertainty` 加一条；不要用臆测填充。

## section_notes

`{"section_id":"S2","order":1,"title":"原文标题","summary":"本节笔记","source_ids":["s1"]}`
- `section_id` / `order` 必须来自 `build_outline.py` 的 outline，不得自创。
- 顺序按 `order` 升序，与论文自身一致；不覆盖的章节可缺失（非 strict 模式），但不能乱序、不能出现骨架外 ID。
- `summary` 用自己的话，不整段照抄；关键事实靠 `source_ids` 回链。

## sources（证据锚点，找得回的落点）

`{"source_id":"s1","location":"p.3 ¶2 / Fig.2 / Table 1 / §3.1","quote":"原文逐字片段"}`
- `source_id` 全篇唯一，被 paper_card / section_notes / knowledge_points 通过 `source_ids` 引用。
- `location` 尽量精确：页码 + 段落序号 + 图表/公式/字段编号；能到段不到章，能到图不到节。
- `quote` 必须是材料中的逐字片段；`verify_notes.py` 会规范化后（忽略大小写、标点、空白）在原文匹配，匹配不到即判 traceable failed。不要改写、缩略或翻译 quote。

## knowledge_points（用得上）

`{"id":"k1","term":"原文术语","aliases":["缩写","同义表述","中文译名"],"definition":"定义/解释","source_ids":["s2"]}`
- `id`、`term` 全篇唯一；别名不得与其他条目的 term 相同。
- 处理术语、缩写、同义表，避免一条概念拆成多条、或多条概念并成一条。

## 状态与不确定性

- `status`: success / partial / unable / refused。
- `uncertainty`: 分三类写——"未报告"（材料确实没有）、"无法判断"（有材料但读不出/冲突）、"材料冲突"（两处不一致）。三类分开，不混为一谈。
- `changes`: 记录本次处理做了哪些动作（骨架生成、阅读顺序校正、降级解析、去重等）。
