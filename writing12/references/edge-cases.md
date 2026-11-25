# 异常矩阵：什么情况怎么处置

判据：**能定位就定位，定位不了就标注，绝不猜。** 猜出来的内容比缺内容危险得多——
缺内容评审能看出来，猜的内容会进作者稿件。

| 情况 | 识别信号 | 处置 | result 里的落点 |
|---|---|---|---|
| 原文缺页码/缺图 | 材料只有正文，图注缺失 | 译文对应段保留图号引用，不补题注 | `uncertainty: figure_missing` |
| 术语表冲突 | 同 `en` 在两行有不同 `zh` | 以学科主译为锁定值，另一译法入 `variants` | `term_conflict` 会拦；`uncertainty` 记改判理由 |
| 超长文本 | >20 段或 >8000 词 | 分块译，块间段号连续；先出前 10 段标 `partial` | `status: partial`，`changes` 记已译范围 |
| 公式是图片 | 材料里公式为图，无 LaTeX | 保留图位与公式编号，标 `needs_human` | `uncertainty: formula_as_image` |
| 引用格式异常 | 裸数字、`ibid.`、`[?]` | 原样保留，不擅自补作者年份 | `uncertainty: citation_malformed` |
| 语向不支持 | 小语种段、中英混排段 | 只译可识别语言段，其余标 `skipped` | `result.skipped` 列表 |
| 编码错误/乱码 | 替换字符 `�`、乱码段 | 该段标 `unreadable`，不猜 | `uncertainty: encoding_error` + 段号 |
| 原文自身矛盾 | 正文与图注数值不一致 | 两处都照原文译，标 `source_inconsistent` | `uncertainty` 写两个值 + 段号 |
| 单位缺失 | 数值后无单位 | 不补单位；保留数值 | `uncertainty: unit_missing` |
| 表格为扫描件 | 表内容不可解析 | 保留表位与表号，不逐格猜 | `uncertainty: table_unreadable` |
| 预算将尽 | 剩余请求不足以译完 | 先落术语表 + 已译段 + 台账 | `status: partial` + 未译起点段号 |
| 目标语言与任务冲突 | 任务要求中文但材料已是中文 | 按任务执行，标 `already_target_lang` | `status: partial` |

## 处置优先级

1. **先保证已译部分可信**：宁可只交 6 段全部合规，也不要交 10 段里 4 段错。
2. **再保证可续接**：`partial` 必须写明"从 P07 起未译"，下一个人能直接接上。
3. **最后才考虑覆盖面**：覆盖面是在前两条都成立之后才追求的指标。

## 不要做的事

- 不要把没读懂的段落"顺"成一通看起来合理的句子；
- 不要为了凑覆盖率把两段合成一段（`pair_coverage` 会掉，而且丢掉的分段关系无法复原）；
- 不要在 `status` 里写 `success` 而实际有未译段——这是最容易被评审抓到的一处不一致。
