# result.json 字段说明

## citations（引用定位与匹配）

- `cite_id`：稳定编号 c1, c2...
- `claim`：需要来源支撑的论断句原文（必须是稿件中的句子，逐字可回查）。
- `claim_location`：精确到句的位置（如 sec2.p3.s2）；不得用"图2附近""段尾"等凑数位置。
- `ref_key`：文献库中的条目 key（必须真实存在）。
- `position_ok`：引用是否挂在真正需要支撑的句子（false 判错）。
- `match.topic_terms`：论断与文献共有的主题词。
- `match.match_basis`：逐句说明为何该文献支撑此论断。
- `match.strength`：direct（文献直接支撑）/ indirect（需一步推断，写入 uncertainty）。

## numbering（编号同步）

`body_numbers` / `list_numbers` 为整数数组；`continuous`、`dangling`（正文有列表无）、`uncited`（列表有正文无）。

## deduplication（去重）

- `merged`：{a, b, basis} —— basis 必须是可解释判据（DOI一致、预印本与正式版、题名相似+作者年份）。
- `kept_separate`：{a, b, reason} —— 明确不得合并的对（如同名作者不同题名）。
- `pending`：字段不足、需人工确认的歧义项。

## format_conversion（格式转换）

`from` / `to` / `field_mapping` / `preserved_fields`。关键字段 doi/volume/issue/pages 必须声明保留。

## 来源与边界

`sources` 记录稿件与文献库快照；`uncertainty` 记录未联网核验、间接匹配、去重歧义；`changes` 逐条记录改动。
