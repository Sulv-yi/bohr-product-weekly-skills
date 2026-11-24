# 译文核验清单（Verification Checklist）

每段译文交付前逐条自查，任一不过则修正或标注。

## A. 覆盖
- [ ] 原文每个 `source_id` 都有译文（无漏段）
- [ ] 无重复段、无错位段
- [ ] 标题 / 摘要 / 正文 / 图注 / 表头 / 公式 / 参考文献（按任务范围）均已覆盖

## B. 术语
- [ ] 术语表已建立并锁定
- [ ] 每段命中术语均用锁定译名
- [ ] 全篇无同术语多译名
- [ ] 缩写前后一致（首次全称 + 译名，后续统一）

## C. 硬信息守恒
- [ ] 数字、范围、比较符、单位与原文一致
- [ ] 引用编号未串位
- [ ] 图表 / 公式编号对应
- [ ] 否定词全部保留（结论未反转）
- [ ] 限定强度未升级 / 降级

## D. 可核验
- [ ] 每段有 `location`（页码 + 段落序号）
- [ ] 每段有 `rationale`（译法依据）
- [ ] `quote`（原文证据片段）可回查
- [ ] 译不准处写入 `untranslated`，不含混带过

## E. 状态与不确定
- [ ] `status` 与实际情况一致（success / partial / unable / refused）
- [ ] 材料缺失、图片公式、扫描件等情况写入 `uncertainty`
- [ ] `changes` 记录了修订过程

## 脚本对应
| 清单项 | 校验脚本 |
|---|---|
| A 覆盖 | `align_paragraphs.py` |
| C 硬信息守恒 | `verify_translation.py` |
| 术语一致 | `verify_translation.py --glossary` |
| D/E 契约 | `validate_result.py` |
| B 语义级 / 指代 | 人工复核（脚本提示 `semantic_review_required`） |
