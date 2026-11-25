# 验收表（H1–H10）

每一条都是可执行检查，不是自评。全部满足才算"本作品可用"。

| 编号 | 断言 | 检查方式 | 本次结果 |
|---|---|---|---|
| H1 | 段级双语稿能被解析出与原文等量的段 | `validate_result.py` → `segments` = 材料段数 | 10 = 10 ✓ |
| H2 | 没有漏译段、没有调序 | `pair_coverage`=100% 且 `order_preserved`=true | ✓ |
| H3 | 引用/图表/公式/脚注标记全部保留 | `marker_keep` ≥90% | 100% ✓ |
| H4 | 术语锁定译法逐段落地 | `term_coverage` ≥95% | 100% ✓ |
| H5 | 无术语漂移 | `term_variant_leak` = 0 | 0 ✓ |
| H6 | 原文每个数值在译文同值出现 | `number_transfer_rate` ≥95% | 100%（24/24）✓ |
| H7 | 无四舍五入导致的有效数字损失 | `sigfig_loss` = 0 | 0 ✓ |
| H8 | 否定/情态/限定条件未被改动 | `boundary_violation` ≤1 且 `hedge_alignment` ≥80% | 0 / 100% ✓ |
| H9 | 译文篇幅与原文相称（防漏译与凑字） | `length_ratio` ≥1.2 且 `target_chars` ≥200 | 1.4 / 360 ✓ |
| H10 | 相对 baseline 有稳定增益且无变差项 | `compare_ab.py` → `quality_gain_holds` 且 `worse` 为空 | ✓（6 项变好） |

## 补充断言（结构层）

| 编号 | 断言 | 检查方式 | 结果 |
|---|---|---|---|
| H11 | 三张台账齐备且行数对得上 | `term-audit.csv` 行数 = 术语条数；`number-audit.csv` 行数 = 原文数值个数 | ✓ |
| H12 | 未确认项都写进 `uncertainty` | `result.uncertainty` 非空且每条带段号 | ✓（3 条） |
| H13 | 状态与内容一致 | 有未译段时 `status` 不得为 `success` | ✓（无未译段） |
| H14 | 脚本无第三方依赖 | `grep -h '^import\|^from' scripts/*.py` 仅标准库 | ✓ |

## 未覆盖项（诚实标注）

- **文笔**：脚本量不出"生硬/流畅"，只给句法与语域规范（`references/style-register.md`），由人判断。
- **术语的学科正确性**：表对不对由人负责；本作品只保证"表定了之后全篇一致"。
- **多语种自动识别**：不支持，按任务声明语向执行，识别不了的段标 `skipped`。
- **原文自身矛盾**：不统一，两处照译并标 `source_inconsistent`。
