# 评分维度 → 材料位置

| 维度（分值） | 评分点 | 本作品对应材料 | 可复核方式 |
|---|---|---|---|
| 实际效果 40 | 任务完成度 15 | `SKILL.md` 预算表 + `scripts/draft_bilingual.py` + `examples/selftest-bilingual.md` | 段覆盖 100%、段序保持（`validate_result.py`） |
| | 结果正确性 15 | `scripts/bilingual_gate.py`（数值按值比对、边界三类） | 数值落地 100%、量级错 0、边界改动 0 |
| | 结果完整性 5 | 标记归一化（`references/alignment.md` §4） | 标记保留 100%（引用/图表/公式/脚注） |
| | 结果可核验性 5 | `term-audit.csv` / `align-map.csv` / `number-audit.csv` | 每个数值一行、每个术语一段号清单 |
| 使用增益 25 | 质量增益 15 | `examples/ab-report.md`（基线 → 技能） | 6 项变好、0 项变差（`compare_ab.py`） |
| | 效率增益 5 | 术语漂移 24→0、边界改动 3→0 | 返工量直接按"错处条数"计 |
| | 增益可验证性 5 | `eval/rubric.json` + `eval/ab-protocol.md` + `eval/compare_ab.py` | 同口径重跑得同一结论 |
| 创新增益 15 | 新增能力 5 | 四把尺（术语/数值/标记/边界）落成四个比率 | 基础 Agent 不产出这些数 |
| | 方法改进 5 | 先建表后动笔 + 段号主键 + 标记归一化 | `references/` 三篇口径文档 |
| | 创新证据 5 | `references/innovation-boundary.md` + `examples/ab-report.md` | 与通用翻译工具逐项对比 |
| 可靠体验 10 | 调用与易用性 3 | `SKILL.md` 第 0–6 步 + `examples/minimal-example.md` | 按说明可独立跑通 |
| | 运行稳定性 4 | 脚本仅标准库；分块策略（`references/edge-cases.md`） | 换篇幅/语向不崩 |
| | 异常处理 3 | `references/edge-cases.md` 12 类异常矩阵 | 每类有落点字段 |
| 生态贡献 10 | 文档完整性 3 | `README.md` + 7 篇 `references/` | 用途/依赖/限制/维护齐全 |
| | 资源可复用性 4 | `examples/term-table.json`（可换领域）+ `bilingual_gate.py` | 术语表可直接改作他用 |
| | 分享推广价值 3 | `GITHUB_URL.txt` + `examples/` 全链示例 | 公开仓库可打开 |

## 硬门槛一览（与 `scripts/validate_result.py` 对齐）

| 指标 | 门槛 | 本次自测 |
|---|---|---|
| `pair_coverage` | ≥95% | 100% |
| `order_preserved` | true | true |
| `marker_keep` | ≥90% | 100% |
| `term_coverage` | ≥95% | 100% |
| `term_variant_leak` | 0 | 0 |
| `number_transfer_rate` | ≥95% | 100% |
| `magnitude_errors` | 0 | 0 |
| `boundary_violation` | ≤1 | 0 |
| `hedge_alignment` | ≥80% | 100% |
| `length_ratio` | ≥1.2 字/词 | 1.4 |

## 自测口径说明

`examples/` 下的自测材料与译稿用于验证工具链，**不是正式案例答案**；
`baseline-*` 是同题的一份直译产物，仅用于 A/B 对照。正式 3 个案例由平台运行时提供，
本作品不以任何形式预置其答案。
