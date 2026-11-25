# 验收表（H1–H12）

每条都是可执行检查，不是自评。

| 编号 | 断言 | 检查方式 | 本次结果 |
|---|---|---|---|
| H1 | 七要素至少齐 6 项 | `element-map.csv` 中 `present=yes` ≥6 | 7/7 ✓ |
| H2 | 各节达到最低字数 | `element-map.csv` 的 `chars ≥ need` | ✓ |
| H3 | 缺口从背景推导到问题（不脱节） | `gap_specific=true`（线索词 + 主题词重叠 ≥2） | 具体（线索 6、重叠 19）✓ |
| H4 | 研究问题可证伪 | `falsifiable=true`（指标 + 阈值 + 对照/时点） | 是 ✓ |
| H5 | 目标-路线-指标-成果四元组齐全 | `alignment_rate` ≥90% | 100% ✓ |
| H6 | 指标在正文有呼应 | `alignment_bad` 为空 | 空 ✓ |
| H7 | 里程碑覆盖全周期、无重叠 | `schedule_coverage=true` 且重叠 =0 | 是 / 0 ✓ |
| H8 | 工作量不超过可用人力 | `effort_ratio` ≤1.0 | 1.0 ✓ |
| H9 | 风险四要素齐全率 ≥90% | `risk_complete` | 100% ✓ |
| H10 | 风险覆盖 4 类 | `risk_types` =4 | 4 ✓ |
| H11 | 论断挂引用 ≥60% | `binding_rate` | 89% ✓ |
| H12 | 相对 baseline 有增益且无变差项 | `compare_ab.py` → `quality_gain_holds` 且 `worse` 空 | ✓ |

## 结构层补充

| 编号 | 断言 | 检查方式 | 结果 |
|---|---|---|---|
| H13 | `plan` 与正文同源（不是各写各的） | 指标串前 4 字在正文出现 | ✓ |
| H14 | 未确认项写进 `uncertainty` 且带条目标识 | `result.uncertainty` 非空、item/status/note 齐全 | ✓（3 条） |
| H15 | 状态与内容一致 | 有缺节或缺 `plan` 时 `status` 不得为 `success` | ✓ |
| H16 | 脚本无第三方依赖 | `grep '^import\|^from' scripts/*.py` 仅标准库 | ✓ |

## 未覆盖项（诚实标注）

- **科学价值与创新性**：脚本不判断。工具只保证结构上"说清了"，不保证"值得做"。
- **阈值合理性**：只检查有没有阈值、是否与正文一致，不判断阈值是否来自数据。
- **经费论证合理性**：只校验分项合计 = 总额。
- **人文艺术类题目**："指标 + 阈值"的强制可能不适用，需放宽并在 `uncertainty` 说明。
