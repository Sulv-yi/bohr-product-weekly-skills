# A/B 对照结果（自动生成）

- baseline: `examples/baseline-scorecard.json`
- skill: `examples/scorecard.json`

| 指标 | baseline | skill | Δ | 方向 |
|---|---|---|---|---|
| pair_coverage | 1.0 | 1.0 | +0.000 | higher |
| marker_keep | 0.111 | 1.0 | +0.889 | higher |
| term_coverage | 0.368 | 1.0 | +0.632 | higher |
| number_transfer_rate | 0.625 | 1.0 | +0.375 | higher |
| hedge_alignment | 0.0 | 1.0 | +1.000 | higher |
| target_chars | 320 | 360 | +40.000 | higher |
| segments | 10 | 10 | +0.000 | higher |
| numbers_total | 24 | 24 | +0.000 | higher |
| term_variant_leak | 24 | 0 | -24.000 | lower |
| boundary_violation | 3 | 0 | -3.000 | lower |
| sigfig_loss | 4 | 0 | -4.000 | lower |
| magnitude_errors | 0 | 0 | +0.000 | lower |
| placeholder_count | 0 | 0 | +0.000 | lower |

- 质量增益成立: **True**
- 效率增益成立: **True**
- 变差项: 无
