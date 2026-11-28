# A/B 对照结果（自动生成）

- baseline: `examples/baseline-scorecard.json`
- skill: `examples/scorecard.json`

| 指标 | baseline | skill | Δ | 方向 |
|---|---|---|---|---|
| element_coverage | 0.833 | 1.0 | +0.167 | higher |
| section_total | 886 | 937 | +51.000 | higher |
| param_rows | 0 | 9 | +9.000 | higher |
| param_source_rate | 0.0 | 1.0 | +1.000 | higher |
| param_body_alignment | 0.0 | 1.0 | +1.000 | higher |
| baseline_coverage | 0.333 | 1.0 | +0.667 | higher |
| repro_coverage | 0.5 | 1.0 | +0.500 | higher |
| placeholder_count | 0 | 0 | +0.000 | lower |
| errors_before_accept | 0 | 0 | +0.000 | lower |
| open_gaps | 0 | 3 | +3.000 | info |

- 质量增益成立: **True**
- 效率增益成立: **True**
- 变差项: 无

## 口径修订说明（2026-11-28）

原判定把「人工确认项条数」放进「越少越好」，导致如实标注的产物被判成效率变差：
Skill 侧把「需按目标期刊核术语」「本样例只做语言层处理」等真实不确定项写进 `uncertainty`，
基线一条都不写，于是基线「更优」。这是评价口径的错，不是产物的错，已改：

- 人工确认项 / 缺口条数改为**只展示、不判优劣**（表中 `direction: info`）；
- 效率增益改用 `errors_before_accept`（交付前必须消除的错误条数，取同一评分脚本的
  `errors` 列表长度），可确定性复现，不靠估时；
- 效率增益成立条件：技能侧 `errors_before_accept == 0` 且不多于基线，且质量门槛达标。

## 已知不足

- 本对照中基线与技能侧 `errors_before_accept` 都是 0，该指标在这份样例上**没有区分度**，
  效率增益实际由「零错误 + 质量门槛」共同成立。要压出真实差别，需要一份基线会触发校验
  错误的样例，而不是现在这份两侧都干净的样例。
- 对照只覆盖本地自测案例；平台固定案例未跑，理由见 `uncertainty`。
