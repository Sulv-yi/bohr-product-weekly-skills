# 边界案例与异常处理

| 情况 | 处置 |
|---|---|
| 文献库字段缺失 | 解析留空；DOI 缺失且无 URL 判 error，其余告警 |
| DOI 解析失败 / 无网络 | 只做本地格式校验，uncertainty 写"未联网核验真实性" |
| 同一文献中英文题名 | 无 DOI 一致证据不合并，保留独立条目 + uncertainty |
| 预印本 vs 正式版 | 题名相似+作者年份一致+版本关系证据才合并 |
| 同名作者不同文献 | D5 判 do_not_merge，禁止合并 |
| 去重字段不足 | 进 pending + uncertainty，交人工确认 |
| 编号冲突/不连续 | check_numbering R2-R5 报具体项与人工接管点 |
| 稿件格式不支持 | status=unable，说明原因，不臆造引用 |
| 引用挂在图表注/段尾 | 判 position_ok=false，挂得对 failed |
| claim 不在稿件原文 | 疑似编造论断，判错 |
| 主题不符且无 match_basis | 判错引 |
| 重复运行 | 脚本只读输入写独立输出，编号按实际标记重算 |
