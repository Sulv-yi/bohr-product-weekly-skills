# A/B 对照协议

题面要求「通过公平对照证明证据支撑质量的改善」。这个文件的用途是让对照**可被重跑**，
而不是让参赛者声明"我们提升了"。

## 1. 对照双方

| 组别 | 定义 | 输入 | 权限 |
|---|---|---|---|
| baseline | 不加载本 Skill 的 Agent，给定同一份 case 与任务说明 | 同一 `case.json`、同一材料 | 同样的文件读写与工具 |
| skill | 加载本 Skill 的 Agent | 同上 | 同上 |

两组必须用**同一 case**、同一字数范围、同一引用格式要求。
baseline 的产物见 `examples/baseline-*.json`；它是"认真做但不带方法"的对照，
**不得故意写错引用或留占位符来制造差距**——那属于稻草人，不是对照。

## 2. 评分口径

两组产物都过同一套脚本：

```bash
python eval/score_output.py --result <result.json> --case <case.json> \
    --draft <draft.md> --out <scorecard.json>
python eval/compare_ab.py baseline-scorecard.json scorecard.json --md ab-report.md
```

`score_output.py` 不输出总分，只输出每条 `pass/fail/n/a` 与指标值；
`compare_ab.py` 只输出 Δ 与增益是否成立。两者都不含人工加权。

## 3. 重复与取值

- 每组跑 3 次，取每项指标的**中位数**；三次差异超过 20% 的指标视为不稳定，
  在报告里单列，不参与增益判定。
- 温度、模型、上下文长度、请求预算必须一致；不一致时对照作废，重跑。
- 不同学科材料各跑一轮，用于检验稳定性；单学科结论不外推。

## 4. 增益判定（写死在代码里，不看自述）

**质量增益成立**，需同时满足：

1. Δ`locator_rate` ≥ 0；
2. Δ`hedge_alignment` ≥ 0；
3. 至少 2 项指标严格变好（候选：`claim_coverage`、`locator_rate`、`strength_rate`、
   `hedge_alignment`、`binding_rate`、`evidence_claim_coverage`）；
4. Δ`placeholder_count` ≤ 0（不能靠删内容或留空换指标）。

**效率增益成立**，需同时满足：

1. Δ`open_items` ≤ 0（人工待确认项不增加）；
2. Δ`binding_rate` ≥ 0（返工前置不以牺牲绑定为代价）。

## 5. 不可判定项的规则

- 材料缺失导致某指标无法计算 → 该指标判 `n/a`，**不判 pass**。
- 环境缺依赖（如无 pandoc 无法渲染 preview）→ 判 `n/a`，并在报告注明需在完整镜像内复核。
- 有任何一项变差 → 必须写进 `result.uncertainty`，并在 `ab-report.md` 的"变差项"里列出。
  不做选择性报告；也不允许把变差项从指标集里删掉。

## 6. 已知的对照局限

1. baseline 由同一创作者撰写，可能不自觉地向 skill 的写法靠拢，从而缩小差距；
2. 3 次取中位的样本量不足以做显著性检验，本协议不声称统计显著，只声称方向与幅度；
3. 固定案例只有 3 个，学科覆盖有限，结论只在"学术写作类材料"范围内成立。
