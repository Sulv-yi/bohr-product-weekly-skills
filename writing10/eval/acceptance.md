# 验收表：什么算交付完成

## 硬门槛

| 编号 | 门槛 | 判据 | 复核命令 |
|---|---|---|---|
| H1 | 章节实体 | `chapter.md` 存在，总字数 ≥1200 | `validate_result.py --text` |
| H2 | 两节厚度 | 结果 ≥250、讨论 ≥300 | 同上 |
| H3 | 图表数据 | `figure_data` ≥2 行，含 n 与误差棒含义 | 同上（`figure_rows`） |
| H4 | 数值一致 | 结果段数值与图表同值 ≥90% | 同上（`fig_number_rate`） |
| H5 | 统计支撑 | 显著性措辞带统计量 ≥80% | 同上（`stats_support`） |
| H6 | 两节分离 | 结果段解释句 ≤2 | 同上（`leakage`） |
| H7 | 趋势边界 | 有小幅差异时必须写"未达显著" | 同上（`trend_boundary`） |
| H8 | 论断绑定 | 挂引用或图表编号 ≥60% | 同上（`binding_rate`） |
| H9 | 局限具体 | ≥3 条可检验线索，无套话 | 同上（`limitation_markers`） |
| H10 | 干净度 | 无 `【…】`/`TODO`/`待补` | 同上（`placeholder_count`） |

## 软性项

| 编号 | 项 | 期望 |
|---|---|---|
| S1 | 误差棒含义 | 写 SD / SEM / 95% CI 之一，不写"误差棒"了事 |
| S2 | 不一致文献 | 至少一处"与…不一致 + 可能原因" |
| S3 | 阴性结果 | 阴性指标照写，不隐藏 |
| S4 | 预览 | 有 pandoc 时产出 `preview.pdf`，无则 n/a |
| S5 | 对照报告 | `examples/ab-report.md` 存在并列出变差项 |

## 四问盲评表

| 性质 | 只看这一份文件就能判断 | 文件 |
|---|---|---|
| 读得准 | 正文每个数值是否来自图表数据 | `figure-audit.csv` |
| 分得清 | 结果段是否只写观察 | `selfcheck.md` 的泄漏清单 |
| 说得住 | "显著"是否都有统计量 | `selfcheck.md` 的统计支撑清单 |
| 核得了 | 数值与论断能否逐条回溯 | `figure-audit.csv` + 稿件引用编号 |

## 复核顺序

```bash
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-chapter.md
python scripts/build_outputs.py --result examples/selftest-result.json \
    --text examples/selftest-chapter.md --outdir /tmp/o10
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-chapter.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o10/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o10/card.json
```
