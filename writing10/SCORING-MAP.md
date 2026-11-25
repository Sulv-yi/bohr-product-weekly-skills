# 评分点 → 证据位置对照表

## 实际效果（40）

| 评分点 | 分 | 对应产物 | 复核方式 |
|---|---|---|---|
| 任务完成度 | 15 | `chapter.md`（结果+讨论+局限） | 总字数 ≥1200、结果 ≥250、讨论 ≥300 |
| 结果正确性 | 15 | `figure-audit.csv` + 稿件 | 数值一致率 ≥90%、统计支撑 ≥80% |
| 结果完整性 | 5 | `figure_data` + 边界表述 | 图表 ≥2 行、有"未达显著"类边界 |
| 结果可核验性 | 5 | `figure-audit.csv` | 每个数值映射到图表字段；论断挂引用 ≥60% |

## 使用增益（25）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 质量增益 | 15 | `examples/ab-report.md`：数值一致率 0%→100%、统计支撑 0%→100% |
| 效率增益 | 5 | 逐值核对前置到脚本，减少回查 |
| 增益可验证性 | 5 | 同一 rubric + 同一脚本可重跑；无基线判 n/a |

## 创新增益（15）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 新增能力 | 5 | `results_gate.fig_number_rate`（逐值回溯）+ `stats_alignment`（显著性↔统计量） |
| 方法改进 | 5 | 两节分离用解释性措辞检出；局限用可检验线索替代套话 |
| 创新证据 | 5 | `references/innovation-boundary.md`（含做不到的 5 条） |

## 可靠体验（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 调用与易用性 | 3 | `SKILL.md` 八步 + `examples/minimal-example.md` |
| 运行稳定性 | 4 | 脚本仅标准库；缺字段不崩 |
| 异常处理 | 3 | `references/edge-cases.md` 七类 |

## 生态贡献（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 文档完整性 | 3 | `README.md` + `references/stats-language.md` |
| 资源可复用性 | 4 | `figure_data` 结构 + `figure-audit.csv` 可直接复用 |
| 分享推广价值 | 3 | `GITHUB_URL.txt` + `references/edge-cases.md` |

## 60 秒自查

```bash
cd <skill_dir>
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-chapter.md
python scripts/build_outputs.py --result examples/selftest-result.json \
    --text examples/selftest-chapter.md --outdir /tmp/o10
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-chapter.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o10/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o10/card.json
```

## 当前实测数值

| 指标 | 值 | 门槛 |
|---|---|---|
| 总字数 / 结果 / 讨论 | 1219 / 317 / 896 | 1200 / 250 / 300 |
| 图表数据行 | 3 | ≥2 |
| 数值一致率 | 100% | ≥90% |
| 统计支撑率 | 100% | ≥80% |
| 结果段解释句 | 0 | ≤2 |
| 论断绑定率 | 100% | ≥60% |
| 局限具体线索 | 6 条 | ≥3 |
| 占位符 | 0 | 0 |
