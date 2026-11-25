# 异常矩阵：六类失败与处置

原则：**能判定就判定，判不了就标出来**。静默跳过、编造一句"未发现问题"是本 Skill
最忌讳的行为。

| 情况 | 识别信号 | 处置 | status |
|---|---|---|---|
| 文献不可得（只给题录） | `sources[]` 只有作者/年份/题名，无原文 | 该条证据等级判 `insufficient`；论断移入待核清单或降级表述；`uncertainty` 标 `not_reported` | `partial` |
| 仅有摘要 | 有 abstract 无全文 | 只能支撑摘要级断言；涉及方法/样本量的论断一律不许用该条；`uncertainty` 注明"仅摘要" | `partial` |
| 原文与摘要矛盾 | 摘录的句子与摘要立场相反 | 以全文为准；`conflicts[]` 记录；正文写明不一致 | `partial` |
| 证据相互冲突 | 两条 `relation=contradicts` | 见 `uncertainty-language.md`：列冲突 → 正文写不一致 → 降级 | `partial` |
| 格式不支持 | 输入是扫描 PDF 无文字层 / 加密 / 图片公式 | 走 OCR 并标注页范围与置信度；公式与符号单独列"未能确认" | `partial` |
| 权限不足 / 文件缺失 | 路径不存在或读报错 | 不猜内容；`status` 标 `blocked`，`uncertainty` 写清缺什么 | `blocked` |

## 其余常见情况

- **材料语言与目标语言不同**：论断用目标语言写，`quote` 保留原文，两者都要在证据表里。
- **同一文献多个版本**（预印本/会议版/期刊版）：取最终版，`sources` 里注版本与日期；
  若只能拿到旧版，`uncertainty` 标 `undetermined`。
- **引用编号与文献表不一致**：以文献表为准，正文编号对齐后重跑 `validate_result.py`。
- **材料里有材料外常识**：材料没写但属于领域共识的，不得作为论断来源；
  要么删，要么写成"一般认为（未在材料中给出依据）"并进 `uncertainty`。
- **运行预算将尽**：先落 `draft.md` 与 `result.json` 的 `partial` 版（有论断清单和已核部分），
  再增量补；交空壳得 0 分，交 partial 至少拿到已核部分的分。

## 不许做的三件事

1. 把 `insufficient` 写成 `moderate` 让门槛通过；
2. 把找不到的引用编一个作者年份；
3. 把 `status` 从 `partial` 改成 `success` 绕过门槛。
