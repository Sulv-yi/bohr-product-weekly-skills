# 评分维度 → 材料位置

| 维度（分值） | 评分点 | 本作品对应材料 | 可复核方式 |
|---|---|---|---|
| 实际效果 40 | 任务完成度 15 | `SKILL.md` 预算表（七要素字数）+ `scripts/draft_outline.py` + `examples/selftest-proposal.md` | `element-map.csv` 7/7 且各节达标 |
| | 结果正确性 15 | `scripts/proposal_gate.py`（缺口 / 可证伪 / 排期 / 人力比） | 缺口具体、问题可证伪、工作量比 1.0、重叠 0 |
| | 结果完整性 5 | 四张台账 + 七要素与风险四类覆盖 | 风险 4/4 类，周期无空月 |
| | 结果可核验性 5 | `alignment.csv` / `schedule.csv` / `risk.csv` | 每个目标一行、每个里程碑一行、每条风险一行 |
| 使用增益 25 | 质量增益 15 | `examples/ab-report.md`（基线 → 技能） | 6 项变好、0 项变差 |
| | 效率增益 5 | 空月 4→0、重叠 1→0、要素 0/7→7/7 | 返工量按"缺项条数"计 |
| | 增益可验证性 5 | `eval/rubric.json` + `eval/ab-protocol.md` + `eval/compare_ab.py` | 同口径重跑得同一结论 |
| 创新增益 15 | 新增能力 5 | 四把尺（缺口/可证伪/对齐/排期/风险）落成布尔与比率 | 基础 Agent 不产出这些判定 |
| | 方法改进 5 | `plan` 结构表 + 正文同源校验 + 里程碑人月核算 | `references/` 五篇口径文档 |
| | 创新证据 5 | `references/innovation-boundary.md` + `examples/ab-report.md` | 与通用写作助手逐项对比 |
| 可靠体验 10 | 调用与易用性 3 | `SKILL.md` 第 0–8 步 + `examples/minimal-example.md` | 按说明可独立跑通 |
| | 运行稳定性 4 | 脚本仅标准库；周期/学科可换（`references/edge-cases.md`） | 换周期不崩，缺输入有处置 |
| | 异常处理 3 | `references/edge-cases.md` 12 类异常矩阵 | 每类有落点字段 |
| 生态贡献 10 | 文档完整性 3 | `README.md` + 7 篇 `references/` | 用途/依赖/限制/维护齐全 |
| | 资源可复用性 4 | `scripts/draft_outline.py`（骨架+plan 模板）+ `proposal_gate.py` | 换学科改节名正则即可 |
| | 分享推广价值 3 | `GITHUB_URL.txt` + `examples/` 全链示例 | 公开仓库可打开 |

## 硬门槛一览（与 `scripts/validate_result.py` 对齐）

| 指标 | 门槛 | 本次自测 |
|---|---|---|
| 七要素 | ≥6/7 | 7/7 |
| `gap_specific` | true | true |
| `falsifiable` | true | true |
| `alignment_rate` | ≥90% | 100% |
| `schedule_coverage` | true | true |
| `schedule_overlap` | 0 | 0 |
| `effort_ratio` | ≤1.0 | 1.0 |
| `risk_complete` | ≥90% | 100% |
| `risk_types` | 4 | 4 |
| `binding_rate` | ≥60% | 89% |

## 自测口径说明

`examples/` 下的材料、稿件与 `baseline-proposal.md` 用于验证工具链与做 A/B 对照，
**不是正式案例答案**。正式 3 个案例由平台运行时提供，本作品不预置其答案。
