# 评分维度对照

| 维度（分值） | 评分点 | 本包实现 | 复核方式 |
|---|---|---|---|
| 实际效果 40 | 任务完成度 15 | 字数 + 节数预算表 → `task_completion` | `validate_result.py` 首行 |
| | 结果正确性 15 | 数值/限定/限定语/越界/漂移五项 | `popularize_gate.retention / hedge_retention / strength_align / term_consistency` |
| | 结果完整性 5 | 类比 ≥2、图表全保留、受众与目的声明 | `result_completeness` |
| | 可核验性 5 | 溯源覆盖 + 改动账 | `trace_rate / changelog_rate` |
| 使用增益 25 | 质量增益 15 | 与 baseline 逐项 Δ，变好≥3 且变差=0 | `eval/compare_ab.py` |
| | 效率增益 5 | 越界断言、术语漂移、占位符三项返工量不高于基线 | `efficiency_gain` |
| | 增益可验证 5 | rubric + 协议 + 对照脚本三件套 | `eval/` |
| 创新增益 15 | 新增能力 5 | 改写类任务原稿没有的四类度量 | `popularize_gate.py` |
| | 方法改进 5 | 「读得懂·留得住·说得准·接得住」落成判定 | `validate_result.py` |
| | 创新证据 5 | 边界文档 + A/B 报告 | `references/innovation-boundary.md`、`examples/ab-report.md` |
| 可靠体验 10 | 易用性 3 | 预算表 + 最小示例 | `SKILL.md`、`examples/minimal-example.md` |
| | 稳定性 4 | 纯标准库、无网络依赖 | `scripts/*.py` |
| | 异常处理 3 | 异常矩阵 7 类 | `references/edge-cases.md` |
| 生态贡献 10 | 文档 3 | README + SCORING-MAP + 七篇 references | 本目录 |
| | 可复用 4 | 度量函数可单独 import 使用 | `popularize_gate.py` |
| | 分享 3 | 公开仓库链接 | `GITHUB_URL.txt` |
