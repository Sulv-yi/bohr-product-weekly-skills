# 异常与边界处理

| 情形 | 识别信号 | 处理 | status |
|---|---|---|---|
| 扫描件/无文字层 | probe: has_text_layer=false / image_only_pages 高 | 说明需 OCR；不编造原文 | partial |
| 加密/权限受限 | probe: encrypted 且无密码 | 说明需密码或授权 | unable |
| 双栏错序 | column_hint 双栏、块 bbox x 分两组 | build_outline 的 order 校正，changes 记录 | success/partial |
| 图表公式图片化 | 图注在、内容缺失 | 保留编号，正文写"图片内容未识别" | partial |
| 超长文 | 页数多、节多 | 分节处理，`--strict-align` 查覆盖，防漏节 | success/partial |
| 非中文论文 | 原文英文/德文等 | term 用原文，中文译名入 aliases | success |
| 材料冲突 | 两处数字/结论矛盾 | 两处都登记为 source，uncertainty 写"材料冲突" | partial |
| 未报告 | 五要素某字段材料无 | text 写"未报告"，uncertainty 写明 | partial |
| 无法判断 | 有材料但读不出 | uncertainty 写明原因与需人工接管位置 | partial |
| 任务越界 | 要求原创结论/无材料编造 | refused + 原因 | refused |

## 与 verify_notes.py 报错对照

- `quote 无法在原文匹配` → quote 被改写/翻译/抄错，回第 3 步用逐字原文。
- `section_notes 顺序与论文章节顺序不一致` → 按 outline 的 order 重排。
- `含骨架外章节` → 删掉自创节，改用 outline 的 section_id。
- `paper_card 缺要素` → 回第 4 步补齐五字段。
- `findings 缺 conditions` → 补每条发现的成立前提。
- `知识点 term 重复 / 别名与已有 term 冲突` → 合并或改名，保证唯一。
- `笔记中出现材料中未见的数值/引用` → 核对是否臆造或串位，改成材料中出现的值或补 source。
- `status=partial 但无 uncertainty` → 补 uncertainty 说明限制。
