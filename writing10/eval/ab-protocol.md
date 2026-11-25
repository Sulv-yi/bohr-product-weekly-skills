# A/B 对照协议

## 1. 对照双方

| 组别 | 定义 | 输入 |
|---|---|---|
| baseline | 不加载本 Skill 的 Agent | 同一数据表、同一章节要求 |
| skill | 加载本 Skill 的 Agent | 同上 |

baseline 稿见 `examples/baseline-chapter.md`：认真写但不带方法（无 `figure_data`、
无数值出处、"显著"无统计量、局限写套话），**不得故意写错数值制造差距**。

## 2. 口径

```bash
python eval/score_output.py --result <r.json> --case <c.json> --text <chapter.md> --out <card.json>
python eval/compare_ab.py baseline-scorecard.json scorecard.json --md ab-report.md
```

## 3. 重复与取值

每组 3 次取中位数；差异 >20% 的指标视为不稳定，单列且不参与判定。
模型、温度、请求预算须一致，否则对照作废。

## 4. 增益判定（写死在代码里）

**质量增益**：Δ`fig_number_rate` ≥ 0 且 Δ`stats_support` ≥ 0，且至少 2 项严格变好
（候选：`fig_number_rate`、`stats_support`、`binding_rate`、`figure_rows`、
`results_chars`、`discussion_chars`、`limitation_markers`），且 Δ`leakage` ≤ 0。

**效率增益**：Δ`leakage` ≤ 0 且 Δ`binding_rate` ≥ 0。

## 5. 不可判定项

材料缺图 → 数值一致率判 `n/a`；无 pandoc → 预览判 `n/a`；二者都不判 pass。
任一项变差必须写进 `result.uncertainty` 并在报告里列出。

## 6. 已知局限

1. baseline 与 skill 同创作者，可能不自觉靠拢，缩小差距；
2. 3 次取中位不足以做显著性检验，只声称方向与幅度；
3. 固定案例只有 3 个，学科覆盖有限。
