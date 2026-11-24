# 格式转换与来源核验

## 格式转换

- 支持 BibTeX / RIS / JSON 输入，目标 GB/T 7714-2015 或指定 APA 版本。
- 关键字段必须保留：doi、volume、issue、pages、title、authors、year（见 assets/format_mapping.json）。
- DOI 规范化：去 https://doi.org/ 前缀、转小写、去尾部斜杠。
- 中文文献用全角标点、英文用半角；作者超 3 名按目标规范缩写。
- 类型标识：article=[J]、book=[M]、inproceedings=[C]、thesis=[D]、preprint=[Z]。

## 来源核验（对得上）

- 条目必须真实存在（ref_key 命中文献库）；元数据缺 DOI 且无 URL 视为 error。
- DOI 只做格式校验（10.xxxx/...）；无网络时**不得宣称已联网核验真实性**，写入 uncertainty。
- 逐句判定：claim 的主题词应与所引文献 title/abstract 有交集，或给出明确 match_basis。
- 编造条目、元数据错配、错引（主题不符无依据）均判错。
- 证据不足的句子标 strength=indirect 并写入 uncertainty。
