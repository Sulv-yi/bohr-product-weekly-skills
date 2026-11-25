#!/usr/bin/env python3
"""A/B 对照协议：怎么比、比什么、什么算"更好"。

本协议先于对照结果写定，对照后不得修改；所有阈值只允许在 eval/rubric.json 里调整，
不允许在比对脚本里放宽。

## 1. 两组条件

| 组 | 条件 | 输入 | 说明 |
|---|---|---|---|
| baseline | 不加载本 Skill，同一模型直译 | 同一份 `case.json` + 材料 | 只要求"把材料译成目标语言"，不给术语表、不给段号要求 |
| skill | 加载本 Skill | 同一份 `case.json` + 材料 | 按 `SKILL.md` 第 0–6 步执行 |

两组的模型、语向、材料、输出形态完全一致；差别只在有无 Skill。

## 2. 指标与方向

| 指标 | 方向 | 为什么选它 |
|---|---|---|
| `pair_coverage` | 越高越好 | 漏译与合并段的直接度量 |
| `marker_keep` | 越高越好 | 引用/图表/公式/脚注丢失率 |
| `term_coverage` | 越高越好 | 术语表锁定译法的落地率 |
| `number_transfer_rate` | 越高越好 | 数值被取整/省译的比例 |
| `hedge_alignment` | 越高越好 | 情态强度是否被平移 |
| `target_chars` | 越高越好 | 篇幅（配合 `length_ratio` 防凑字） |
| `term_variant_leak` | 越低越好 | 术语漂移条数 = 人工统一译法的工作量 |
| `boundary_violation` | 越低越好 | 否定/情态/限定条件改动条数 |
| `sigfig_loss` | 越低越好 | 有效数字被削的条数 |
| `placeholder_count` | 越低越好 | 未译段与占位符 |

## 3. 判定规则（写死，不因结果好看而改）

- **质量增益成立** ⇐ Δ`term_coverage` ≥ 0 且 Δ`number_transfer_rate` ≥ 0
  且 **至少 3 项严格变好** 且 Δ`placeholder_count` ≤ 0。
- **效率增益成立** ⇐ Δ`term_variant_leak` ≤ 0 且 Δ`boundary_violation` ≤ 0。
  这两项就是人工返工量：漂移要人统一，边界要人核回原文。
- **任何一项变差都必须写进 `result.uncertainty`**，不做选择性报告。
  变差项存在不必然否决增益，但隐瞒变差项直接判本项不成立。

## 4. 执行

```bash
# baseline 侧评分卡
python eval/score_output.py --result examples/baseline-result.json --case examples/selftest-case.json \
    --text examples/baseline-bilingual.md --out examples/baseline-scorecard.json

# skill 侧评分卡（把 baseline 传进去，质量/效率增益才可判）
python eval/score_output.py --result examples/selftest-result.json --case examples/selftest-case.json \
    --text examples/selftest-bilingual.md --baseline examples/baseline-scorecard.json \
    --out examples/scorecard.json

# Δ 表
python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md
```

## 5. 重复性

平台对每个案例跑 3 次。判定"稳定提升"的口径：

- 3 次里 `term_coverage`、`number_transfer_rate` 均不低于 baseline；
- 3 次里 `term_variant_leak`、`boundary_violation` 均不高于 baseline；
- 任一次出现指标倒退，视为该指标不稳定，写入 `uncertainty` 并说明触发条件（篇幅/语向/文体）。

## 6. 不允许的做法

- 不允许把 baseline 的输出改写后再当自己的产物；
- 不允许为拉高 `target_chars` 加水词（`length_ratio` 与漏译检查会互相牵制）；
- 不允许在对照后改 rubric 阈值使结论"成立"；
- 不允许只报变好项。
