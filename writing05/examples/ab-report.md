# A/B 对照结果（自动生成）

- baseline: `examples/baseline-scorecard.json`
- skill: `examples/scorecard.json`

| 指标 | baseline | skill | Δ | 方向 |
|---|---|---|---|---|
| claim_coverage | 0.0 | 1.0 | +1.000 | higher |
| locator_rate | 0.0 | 1.0 | +1.000 | higher |
| strength_rate | 0.0 | 1.0 | +1.000 | higher |
| hedge_alignment | 0.0 | 0.891 | +0.891 | higher |
| binding_rate | 1.0 | 1.0 | +0.000 | higher |
| evidence_claim_coverage | 0.0 | 1.0 | +1.000 | higher |
| evidence_rows | 0 | 46 | +46.000 | higher |
| source_count | 9 | 12 | +3.000 | higher |
| source_metadata_rate | 1.0 | 1.0 | +0.000 | higher |
| placeholder_count | 0 | 0 | +0.000 | lower |
| open_items | 0 | 0 | +0.000 | lower |

- 质量增益成立: **True**
- 效率增益成立: **True**
- 变差项: 无

> 两份评分卡由同一 `eval/score_output.py` 与同一 `eval/rubric.json` 生成；
> 差异只来自交付物本身。
