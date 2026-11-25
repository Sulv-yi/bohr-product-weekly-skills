# A/B 对照协议

题面要求「对照是否公平：材料、章节模板、字数范围、引用格式、工具权限是否一致」。
本文件的用途是让对照可被重跑，而不是让参赛者声明"我们提升了"。

## 1. 对照双方

| 组别 | 定义 | 输入 | 权限 |
|---|---|---|---|
| baseline | 不加载本 Skill 的 Agent，给同一 case 与题目 | 同一材料、同一题目 | 同样的读写与工具权限 |
| skill | 加载本 Skill 的 Agent | 同上 | 同上 |

两组必须同材料、同章节要求、同字数范围、同引用格式。baseline 稿见
`examples/baseline-manuscript.md`：**认真写但不带方法**（章节缺失、无索引、无声明字段），
不得故意写错数值或留占位符来制造差距。

## 2. 评分口径

两组产物都过同一套脚本，指标定义写在 `scripts/sections_gate.py` 文件头：

```bash
python eval/score_output.py --result <result.json> --case <case.json> \
    --text <manuscript.md> --out <scorecard.json>
python eval/compare_ab.py baseline-scorecard.json scorecard.json --md ab-report.md
```

`score_output.py` 不输出总分；`compare_ab.py` 只输出 Δ 与增益是否成立。

## 3. 重复与取值

- 每组跑 3 次取中位数；三次差异 >20% 的指标视为不稳定，单列且不参与增益判定。
- 模型、温度、上下文长度、请求预算必须一致；不一致则对照作废重跑。
- 换学科材料各跑一轮检验稳定性；单学科结论不外推。

## 4. 增益判定（写死在代码里）

**质量增益**成立需同时满足：Δ`cite_resolved_rate` ≥ 0；Δ`section_coverage` ≥ 0；
至少 2 项指标严格变好（候选：`section_coverage`、`cite_resolved_rate`、`binding_rate`、
`material_index_count`、`num_trace_rate`、`fig_pairs`、`tab_pairs`、`ref_entries`）；
Δ`placeholder_count` ≤ 0。

**效率增益**成立需同时满足：Δ`material_index_count` ≥ 0；Δ`num_trace_rate` ≥ 0。

## 5. 不可判定项

- 材料缺失导致指标无法计算 → 判 `n/a`，不判 pass。
- 环境缺 pandoc 无法生成预览 → 判 `n/a`，注明需在完整镜像内复核。
- 任一项变差 → 必须写进 `result.uncertainty` 并在 `ab-report.md` 的「变差项」列出。

## 6. 已知局限

1. baseline 与 skill 由同一创作者完成，可能不自觉向 skill 写法靠拢，缩小差距；
2. 3 次取中位不足以做显著性检验，只声称方向与幅度，不声称统计显著；
3. 固定案例只有 3 个，学科覆盖有限，结论仅在学术论文写作范围内成立。
