#!/usr/bin/env python3
"""A/B 对照协议：怎么比、比什么、什么算"更好"。

本协议先于对照结果写定，对照后不得修改；阈值只在 eval/rubric.json 里调整。

## 1. 两组条件

| 组 | 条件 | 说明 |
|---|---|---|
| baseline | 不加载本 Skill，同一模型按同一份 case 直接写开题报告 | 只给任务与材料，不给七要素清单、不给 plan 结构要求 |
| skill | 加载本 Skill，按 `SKILL.md` 第 0–8 步执行 | 七要素骨架 + plan 表 + 台账 + 门槛 |

两组的模型、材料、体裁、字数上限一致；差别只在有无 Skill。

## 2. 指标与方向

| 指标 | 方向 | 为什么选它 |
|---|---|---|
| `elements_ok` | 越高越好 | 七要素齐备度，缺节是硬伤 |
| `alignment_rate` | 越高越好 | 目标-路线-指标-成果的断裂直接伤"对得上" |
| `risk_complete` | 越高越好 | 风险四要素齐全率 |
| `risk_types` | 越高越好 | 覆盖的类型数（4 类） |
| `binding_rate` | 越高越好 | 论断挂引用率 |
| `total_chars` | 越高越好 | 篇幅（与要素门槛互相牵制，防注水） |
| `schedule_overlap` | 越低越好 | 里程碑重叠＝工作量重复计入 |
| `schedule_gaps` | 越低越好 | 空月数＝排期没排完 |
| `placeholder_count` | 越低越好 | 未写段与占位符 |

布尔项（`gap_specific` / `falsifiable` / `schedule_coverage` / `effort_ratio ≤1`）
不进 Δ 表，作为**否决项**：任一项在 skill 侧不成立，质量增益直接判不成立。

## 3. 判定规则（写死，不因结果好看而改）

- **质量增益成立** ⇐ Δ`alignment_rate` ≥ 0 且 Δ`risk_complete` ≥ 0
  且 **至少 3 项严格变好** 且 Δ`placeholder_count` ≤ 0。
- **效率增益成立** ⇐ Δ`schedule_overlap` ≤ 0 且 Δ空月数 ≤ 0。
  这两项就是人工返工量：重叠要人重排，空月要人补任务。
- **任何变差项必须写进 `result.uncertainty`**，不做选择性报告。

## 4. 执行

```bash
python eval/score_output.py --result examples/baseline-result.json --case examples/selftest-case.json \
    --text examples/baseline-proposal.md --out examples/baseline-scorecard.json

python eval/score_output.py --result examples/selftest-result.json --case examples/selftest-case.json \
    --text examples/selftest-proposal.md --baseline examples/baseline-scorecard.json \
    --out examples/scorecard.json

python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md
```

## 5. 重复性

平台每案例跑 3 次。判定"稳定提升"：3 次里 `elements_ok`、`alignment_rate`、
`risk_complete` 均不低于 baseline；`schedule_overlap` 与空月数均不高于 baseline。
任一次倒退即视为该指标不稳定，写入 `uncertainty` 并说明触发条件（学科/周期/材料完整度）。

## 6. 不允许的做法

- 不允许把 baseline 文本改写成自己的产物；
- 不允许虚增 `capacity_pm` 让 `effort_ratio` 变好看；
- 不允许对照后改 rubric 阈值使结论成立；
- 不允许只报变好项。
